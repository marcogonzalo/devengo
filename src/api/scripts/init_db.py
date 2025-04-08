from src.api.accrual.models.accrual import AccrualPeriod, AccrualClassDistribution
from src.api.services.models.service import Service, ServiceEnrollment
from src.api.invoices.models.invoice import Invoice, InvoiceAccrual
from src.api.clients.models.client import Client, ClientExternalId
from src.api.common.utils.database import engine
from sqlmodel import SQLModel
import os
import sys

# Add the parent directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


# Import all models to register them with SQLModel


def init_db():
    """Initialize the database by creating all tables"""
    print("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    init_db()
