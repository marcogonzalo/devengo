#!/usr/bin/env python3
"""
Script to update existing services with service_type based on their names
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from sqlmodel import Session, select
from src.api.common.utils.database import engine
from src.api.services.models.service import Service
from src.api.services.utils import get_service_type_from_service_name

# Import all models to avoid circular import issues
from src.api.services.models import service, service_contract, service_period
from src.api.clients.models import client
from src.api.accruals.models import accrued_period, contract_accrual
from src.api.invoices.models import invoice


def update_existing_services_service_type():
    """
    Update existing services that don't have service_type assigned
    """
    print("🔧 Updating existing services with service_type...")
    
    with Session(engine) as db:
        # Get all services without service_type or with UNKNOWN service_type
        services = db.exec(
            select(Service).where(
                (Service.service_type.is_(None)) | 
                (Service.service_type == "UNKNOWN")
            )
        ).all()
        
        if not services:
            print("✅ All services already have valid service_type assigned!")
            return
        
        print(f"📊 Found {len(services)} services that need service_type assignment")
        
        updated_count = 0
        for service in services:
            old_service_type = service.service_type
            new_service_type = get_service_type_from_service_name(service.name)
            
            if new_service_type != "UNKNOWN":
                service.service_type = new_service_type
                db.add(service)
                updated_count += 1
                print(f"  ✅ Service '{service.name}' → {old_service_type or 'None'} → {new_service_type}")
            else:
                print(f"  ⚠️  Service '{service.name}' → Could not determine service_type (keeping {old_service_type or 'None'})")
        
        if updated_count > 0:
            db.commit()
            print(f"💾 Updated {updated_count} services with service_type")
        else:
            print("ℹ️  No services needed updates")


if __name__ == "__main__":
    update_existing_services_service_type() 