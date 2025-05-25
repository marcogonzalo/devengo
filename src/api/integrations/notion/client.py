import logging
import httpx
from fastapi import HTTPException
from .config import NotionConfig


class NotionClient:
    def __init__(self, config: NotionConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        self.base_url = config.base_url
        self._client = httpx.AsyncClient()

    async def get_current_user(self):
        try:
            response = await self._client.get(
                f"{self.base_url}/users/me",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"HTTP error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {e}")

    async def get_page_id(self, database_id: str, property_name: str, value: str):
        url = f"{self.base_url}/databases/{database_id}/query"
        # Infer property type
        if property_name.lower() == "email" or property_name.lower() == "e-mail" or property_name.lower().startswith("correo"):
            filter_payload = {
                "property": property_name,
                "email": {"equals": value}
            }
        else:
            filter_payload = {
                "property": property_name,
                "rich_text": {"equals": value}
            }
        payload = {"filter": filter_payload}
        try:
            response = await self._client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if not results:
                return None
            return results[0]["id"]
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"HTTP error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error: {e}")

    async def list_pages(self, database_id: str, on_or_after: str = None, date_property: str = "Created", sort_by: str = None, sort_direction: str = "descending"):
        """
        List all pages in a Notion database, returning their properties and IDs.
        Handles pagination. Optionally filter by a date property on or after a given date (YYYY-MM-DD).
        Optionally sort by a property (default: date_property, descending).
        """
        url = f"{self.base_url}/databases/{database_id}/query"
        all_results = []
        has_more = True
        next_cursor = None
        try:
            while has_more:
                payload = {}
                if on_or_after:
                    payload["filter"] = {
                        "property": date_property,
                        "date": {"on_or_after": on_or_after}
                    }
                # Add sorting
                sort_prop = sort_by or date_property
                if sort_prop:
                    payload["sorts"] = [{
                        "property": sort_prop,
                        "direction": sort_direction
                    }]
                if next_cursor:
                    payload["start_cursor"] = next_cursor
                response = await self._client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                all_results.extend(results)
                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor", None)
            return all_results
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in NotionClient list_pages: {e}")
            raise HTTPException(status_code=500, detail=f"HTTP error: {e}")
        except Exception as e:
            logging.error(
                f"Error occurred in NotionClient list_pages: {e}")
        finally:
            logging.info(
                f"Fetched {len(all_results)} pages, has more: {has_more}, next cursor: {next_cursor}")
            return all_results
