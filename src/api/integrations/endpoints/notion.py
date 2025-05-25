from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import JSONResponse
from src.api.integrations.notion import NotionClient, NotionConfig
from sqlmodel import Session
from src.api.common.utils.database import get_db
from src.api.clients.services.client_service import ClientService
from src.api.clients.schemas.client import ClientExternalIdCreate

router = APIRouter(prefix="/integrations/notion", tags=["integrations"])


def get_client_service(db: Session = Depends(get_db)):
    return ClientService(db)


@router.get("/test")
async def test_notion_integration(request: Request):
    """
    Test endpoint to verify Notion API integration is working correctly.
    It will attempt to fetch the current user (bot) info.
    """
    try:
        config = NotionConfig()
        client = NotionClient(config)
        user_info = await client.get_current_user()
        return JSONResponse(content={
            "status": "success",
            "message": "Notion integration is working correctly",
            "data": user_info
        })
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Notion integration test failed: {str(e)}")


@router.get("/page-id")
async def get_page_id(
    property_name: str = Query(...,
                               description="The property name to search for (e.g. 'Email')"),
    value: str = Query(..., description="The value to match for the property"),
    database_id: str = Query(
        None, description="The Notion database ID (optional, defaults to env)")
):
    """
    Get the Notion page ID from a database by searching for a page with a property matching the provided value.
    If database_id is not provided, uses the value from environment variables.
    """
    try:
        config = NotionConfig()
        db_id = database_id or config.database_id
        if not db_id:
            raise HTTPException(
                status_code=400, detail="No database_id provided and NOTION_DATABASE_ID is not set in environment.")
        client = NotionClient(config)
        page_id = await client.get_page_id(db_id, property_name, value)
        if not page_id:
            raise HTTPException(
                status_code=404, detail="Page not found for the given property and value.")
        return {"page_id": page_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get page ID: {str(e)}")


@router.post("/sync-page-ids-from-clients")
async def sync_page_ids_from_clients(
    database_id: str = Query(
        None, description="The Notion database ID (optional, defaults to env)"),
    client_service: ClientService = Depends(get_client_service),
):
    """
    Sync all Notion page IDs for registered clients as ClientExternalId with system = 'notion'.
    Only processes clients missing a Notion external ID. For each such client, requests their Notion page ID using their identifier (assumed to be email).
    Optionally filter Notion pages by a date property (on or after a given date) and sort the results (if supported by Notion API).
    """
    try:
        config = NotionConfig()
        db_id = database_id or config.database_id
        if not db_id:
            raise HTTPException(
                status_code=400, detail="No database_id provided and NOTION_DATABASE_ID is not set in environment.")
        notion_client = NotionClient(config)
        # Only get clients missing a Notion external ID
        clients = client_service.get_clients_with_no_external_id("notion")
        synced = []
        not_found = []
        for client in clients:
            identifier = client.identifier
            # Query Notion for this client's page ID by email
            try:
                page_id = await notion_client.get_page_id(db_id, "Email", identifier)
            except Exception as e:
                not_found.append({
                    "client_id": client.id,
                    "identifier": identifier,
                    "reason": f"Error querying Notion: {str(e)}"
                })
                continue
            if not page_id:
                not_found.append({
                    "client_id": client.id,
                    "identifier": identifier,
                    "reason": "No matching Notion page"
                })
                continue
            # Register new external ID
            external_id_data = ClientExternalIdCreate(
                system="notion", external_id=page_id)
            client_service.add_external_id(client.id, external_id_data)
            synced.append({
                "client_id": client.id,
                "identifier": identifier,
                "page_id": page_id,
                "created": True
            })
        return {
            "success": True,
            "linked": len(synced),
            "not_found": len(not_found),
            "not_found_details": not_found
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to sync Notion page IDs: {str(e)}")
