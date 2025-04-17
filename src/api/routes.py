from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from src.api.clients.endpoints.client import router as client_router
from src.api.invoices.endpoints.invoice import router as invoice_router
from src.api.services.endpoints.service import router as service_router
from src.api.services.endpoints.service_period import router as service_period_router
from src.api.services.endpoints.service_contract import router as service_contract_router
# from src.api.accrual.endpoints.accrual import router as accrual_router
from src.api.integrations.endpoints.holded import router as holded_router
from src.api.integrations.endpoints.fourgeeks import router as fourgeeks_router
from src.api.integrations.holded import HoldedClient, HoldedConfig
from src.api.integrations.fourgeeks import FourGeeksClient, FourGeeksConfig, FourGeeksCredentials

api_router = APIRouter(tags=["api"])

# Include all domain routers
api_router.include_router(invoice_router)
api_router.include_router(client_router)
api_router.include_router(holded_router)
api_router.include_router(fourgeeks_router)
api_router.include_router(service_router)
api_router.include_router(service_period_router)
api_router.include_router(service_contract_router)

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
