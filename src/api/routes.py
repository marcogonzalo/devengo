from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

api_router = APIRouter(tags=["api"])

@api_router.route('/hello', methods=['POST', 'GET'])
def handle_hello(request: Request):

    response_body = {
        "message": "Hello! I'm a message that came from the backend, check the network tab on the google inspector and you will see the GET request"
    }
    return JSONResponse(content=response_body)
