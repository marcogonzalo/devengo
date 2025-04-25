from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from src.api.clients.endpoints.client import router as client_router
from src.api.invoices.endpoints.invoice import router as invoice_router
from src.api.services.endpoints.service import router as service_router
from src.api.services.endpoints.service_period import router as service_period_router
from src.api.services.endpoints.service_contract import router as service_contract_router
from src.api.accruals.endpoints.accrued_period import router as accrual_router
from src.api.accruals.endpoints.period_processor import router as period_processor_router
from src.api.integrations.endpoints.holded import router as holded_router
from src.api.integrations.endpoints.fourgeeks import router as fourgeeks_router

api_router = APIRouter()

# Include all domain routers
api_router.include_router(invoice_router)
api_router.include_router(client_router)
api_router.include_router(holded_router)
api_router.include_router(fourgeeks_router)
api_router.include_router(service_router)
api_router.include_router(service_period_router)
api_router.include_router(service_contract_router)
api_router.include_router(accrual_router)
api_router.include_router(period_processor_router)

@api_router.route('/hello', methods=['POST', 'GET'])
def handle_hello(request: Request):
    response_body = {
        "message": "Hello! I'm a message that came from the backend, check the network tab on the google inspector and you will see the GET request"
    }
    return JSONResponse(content=response_body)
