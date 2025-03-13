from typing import List, Optional
from pydantic import BaseModel

class HoldedContactSchema(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    tax_id: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class HoldedDocumentSchema(BaseModel):
    id: str
    number: str
    date: str
    due_date: Optional[str] = None
    total: float
    currency: str
    status: str
    type: str
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class HoldedPaginatedResponseSchema(BaseModel):
    data: List[dict]
    total: int
    page: int
    per_page: int
    total_pages: int 