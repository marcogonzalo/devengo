import os
from pydantic import BaseModel

class HoldedConfig(BaseModel):
    api_key: str = os.getenv("HOLDED_API_KEY")
    base_url: str = "https://api.holded.com/api/invoicing/v1"