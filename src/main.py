import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.routes import api_router

app = FastAPI(
    title="Devengo",
    description="Accrual accounting software",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add all endpoints from the API with an "api" prefix
app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Serve static files from the public directory
app.mount("/public", StaticFiles(directory="public"), name="public")

# Serve index.html for all other routes to support client-side routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse("public/index.html")

# this only runs if `$ python src/main.py` is executed
if __name__ == '__main__':
    import uvicorn
    PORT = int(os.environ.get('PORT', 3001))
    uvicorn.run("main:app", host='0.0.0.0', port=PORT, reload=True)