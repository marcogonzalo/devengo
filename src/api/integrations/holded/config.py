import os
from pydantic import BaseModel, Field
from typing import Optional

class HoldedConfig(BaseModel):
    api_key: str = Field(..., default_factory=lambda: os.getenv("HOLDED_API_KEY"))
    base_url: str = "https://api.holded.com/api/invoicing/v1"
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.api_key:
            raise ValueError("HOLDED_API_KEY environment variable is required")