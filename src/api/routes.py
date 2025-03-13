from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from api.integrations.fourgeeks.client import FourGeeksCredentials
from src.api.integrations.holded import HoldedClient, HoldedConfig
from src.api.integrations.fourgeeks import FourGeeksClient, FourGeeksConfig

api_router = APIRouter(tags=["api"])

@api_router.route('/hello', methods=['POST', 'GET'])
def handle_hello(request: Request):

    response_body = {
        "message": "Hello! I'm a message that came from the backend, check the network tab on the google inspector and you will see the GET request"
    }
    return JSONResponse(content=response_body)

@api_router.route('/test-holded', methods=['GET'])
async def test_holded_integration(request: Request):
    """
    Test endpoint to verify Holded API integration is working correctly.
    It will attempt to fetch the first page of contacts and documents.
    """
    try:
        # Initialize Holded client
        config = HoldedConfig()
        client = HoldedClient(config)
        
        # Test contacts endpoint
        contacts_response = await client.list_contacts(page=1, per_page=1)
        
        # Test documents endpoint
        documents_response = await client.list_documents(starttmp=1648771199, endtmp=1743465599)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Holded integration is working correctly",
            "data": {
                "contacts": {
                    "total": len(contacts_response),
                },
                "documents": {
                    "total": len(documents_response),
                }
            }
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Holded integration test failed: {str(e)}"
        )

@api_router.route('/test-fourgeeks', methods=['GET'])
def test_fourgeeks_integration(request: Request):
    """
    Test endpoint to verify 4Geeks API integration is working correctly.
    It will attempt to authenticate and get a token.
    """
    try:
        # Initialize 4Geeks client
        config = FourGeeksConfig()
        client = FourGeeksClient(FourGeeksCredentials(
            username=config.username,
            password=config.password
        ))
        
        # Test authentication
        client.login()
        
        return JSONResponse(content={
            "status": "success",
            "message": "4Geeks integration is working correctly",
            "data": {
                "authenticated": True
            }
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"4Geeks integration test failed: {str(e)}"
        )
