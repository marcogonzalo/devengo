import logging
import httpx
from typing import Dict
from fastapi import HTTPException
from api.integrations.holded.config import HoldedConfig


class HoldedClient:
    def __init__(self, config: HoldedConfig):
        self.config = config
        self.headers = {
            "key": config.api_key,
            "Content-Type": "application/json"
        }
        self._client = httpx.AsyncClient()

    async def list_contacts(self, page: int = 1, per_page: int = 50) -> Dict:
        """
        List all contacts from Holded.

        Args:
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            Dict containing the contacts data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.base_url}/contacts",
                    headers=self.headers,
                    params={"page": page, "per_page": per_page}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in HoldedClient list_contacts: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in HoldedClient list_contacts: {e}")
        except Exception as e:
            logging.error(f"Error occurred in HoldedClient list_contacts: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in HoldedClient list_contacts: {e}")

    async def get_contact(self, contact_id: str) -> Dict:
        """
        Get a specific contact by ID.

        Args:
            contact_id: The ID of the contact to retrieve

        Returns:
            Dict containing the contact data
        """
        try:
            response = await self._client.get(
                f"{self.config.base_url}/contacts/{contact_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in HoldedClient get_contact: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in HoldedClient get_contact: {e}")
        except Exception as e:
            logging.error(f"Error occurred in HoldedClient get_contact: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in HoldedClient get_contact: {e}")

    async def list_documents(self, document_type: str = "invoice", page: int = 1, per_page: int = 50,
                             starttmp: int = None, endtmp: int = None, contactid: str = None,
                             paid: int = None, billed: int = None, sort: str = 'created-asc') -> Dict:
        """
        List all documents from Holded. 
        Suggest to use starttmp and endtmp to filter by date.

        Args:
            document_type: The type of document to retrieve.
            page: Page number for pagination
            per_page: Number of items per page
            starttmp: Starting timestamp
            endtmp: Ending timestamp
            contactid: Filtering by contact Id
            paid: Filtering by paid status. 0 = not paid, 1 = paid, 2 = partially paid
            billed: Filtering by billed status. 0 = not billed, 1 = billed
            sort: Sort documents. Options: created-asc or created-desc

        Returns:
            Dict containing the documents data.
            Limited to 500 documents per request.
        """

        # Validate document_type
        valid_document_types = [
            "invoice", "salesreceipt", "creditnote", "salesorder",
            "proform", "waybill", "estimate", "purchase",
            "purchaseorder", "purchaserefund"
        ]
        if document_type not in valid_document_types:
            raise HTTPException(
                status_code=400, detail="Invalid document type"
            )

        # Validate page
        if not isinstance(page, int) or page < 1:
            raise HTTPException(
                status_code=400, detail="Page must be a positive integer"
            )

        # Validate per_page
        if not isinstance(per_page, int) or per_page < 1:
            raise HTTPException(
                status_code=400, detail="per_page must be a positive integer"
            )

        # Validate timestamps
        if starttmp and not isinstance(starttmp, int):
            raise HTTPException(
                status_code=400, detail="starttmp must be a integer"
            )
        if endtmp and not isinstance(endtmp, int):
            raise HTTPException(
                status_code=400, detail="endtmp must be a integer"
            )

        # Validate contactid
        if contactid and not isinstance(contactid, str):
            raise HTTPException(
                status_code=400, detail="contactid must be a string"
            )

        # Validate paid
        if paid and paid not in ["0", "1", "2"]:
            raise HTTPException(
                status_code=400, detail="paid must be 0 = not paid, 1 = paid, 2 = partially paid"
            )

        # Validate billed
        if billed and billed not in ["0", "1"]:
            raise HTTPException(
                status_code=400, detail="billed must be 0 = not billed, 1 = billed"
            )

        # Validate sort
        if sort and sort not in ["created-asc", "created-desc"]:
            raise HTTPException(
                status_code=400, detail="sort must be 'created-asc' or 'created-desc'"
            )

        params = {
            "page": page,
            "per_page": per_page,
            "starttmp": starttmp,
            "endtmp": endtmp,
            "contactid": contactid,
            "paid": paid,
            "billed": billed,
            "sort": sort
        }

        # Remove any parameters that are None
        params = {k: v for k, v in params.items() if v is not None}

        try:
            response = await self._client.get(
                f"{self.config.base_url}/documents/{document_type}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in HoldedClient list_documents: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in HoldedClient list_documents: {e}")
        except Exception as e:
            logging.error(
                f"Error occurred in HoldedClient list_documents: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in HoldedClient list_documents: {e}")

    async def get_document(self, document_id: str) -> Dict:
        """
        Get a specific document by ID.

        Args:
            document_id: The ID of the document to retrieve

        Returns:
            Dict containing the document data
        """
        try:
            response = await self._client.get(
                f"{self.config.base_url}/documents/{document_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in HoldedClient get_document: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in HoldedClient get_document: {e}")
        except Exception as e:
            logging.error(f"Error occurred in HoldedClient get_document: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in HoldedClient get_document: {e}")

    async def list_income_accounts(self) -> Dict:
        """
        List all expenses accounts from Holded.

        Returns:
            Dict containing the expenses accounts data
        """
        try:
            response = await self._client.get(
                f"{self.config.base_url}/saleschannels",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in HoldedClient list_income_accounts: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in HoldedClient list_income_accounts: {e}")
        except Exception as e:
            logging.error(
                f"Error occurred in HoldedClient list_income_accounts: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in HoldedClient list_income_accounts: {e}")

    async def list_expenses_accounts(self) -> Dict:
        """
        List all expenses accounts from Holded.

        Returns:
            Dict containing the expenses accounts data
        """
        try:
            response = await self._client.get(
                f"{self.config.base_url}/expensesaccounts",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error occurred in HoldedClient list_expenses_accounts: {e}")
            raise HTTPException(
                status_code=500, detail=f"HTTP error occurred in HoldedClient list_expenses_accounts: {e}")
        except Exception as e:
            logging.error(
                f"Error occurred in HoldedClient list_expenses_accounts: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error occurred in HoldedClient list_expenses_accounts: {e}")
