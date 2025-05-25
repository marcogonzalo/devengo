import os
from pydantic import BaseModel


class NotionConfig(BaseModel):
    access_token: str = os.getenv("NOTION_ACCESS_TOKEN")
    base_url: str = "https://api.notion.com/v1"
    database_id: str = os.getenv("NOTION_DATABASE_ID")
