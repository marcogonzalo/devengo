#!/usr/bin/env python3
"""
Script to fix cohort-service compatibility issues and populate service_type field
"""

import sys
import os
sys.path.append('/app')

from sqlmodel import Session, select
from src.api.common.utils.database import engine
from src.api.services.models.service import Service
from src.api.services.models.service_contract import ServiceContract
from src.api.services.models.service_period import ServicePeriod
from src.api.services.utils import (
    get_service_type_from_service_name, 
    get_service_type_from_service_name,
    validate_service_period_compatibility
)
from src.api.clients.models.client import Client
from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.accruals.models.contract_accrual import ContractAccrual
from src.api.invoices.models.invoice import Invoice


def populate_service_service_types(db: Session):
    """
    Populate the service_type field for all services based on their names
    """
    print("🔧 Populating service program types...")
    
    services = db.exec(select(Service)).all()
    updated_count = 0
    
    for service in services:
        service_type = get_service_type_from_service_name(service.name)
        if service_type != "UNKNOWN":
            service.service_type = service_type
            db.add(service)
            updated_count += 1
            print(f"  ✅ Service '{service.name}' → {service_type}")
        else:
            print(f"  ⚠️  Service '{service.name}' → UNKNOWN (needs manual review)")
    
    db.commit()
    print(f"📊 Updated {updated_count} services with program types")


def find_compatibility_issues(db: Session):
    """
    Find and report cohort-service compatibility issues
    """
    print("🔍 Analyzing cohort-service compatibility issues...")
    
    # Get all service periods with their contracts and services
    stmt = (
        select(ServicePeriod, ServiceContract, Service, Client)
        .join(ServiceContract, ServicePeriod.contract_id == ServiceContract.id)
        .join(Service, ServiceContract.service_id == Service.id)
        .join(Client, ServiceContract.client_id == Client.id)
    )
    
    results = db.exec(stmt).all()
    
    issues = []
    
    for period, contract, service, client in results:
        cohort_slug = period.external_id or period.name
        if not cohort_slug:
            continue
            
        cohort_service_type = get_service_type_from_service_name(cohort_slug)
        service_service_type = service.service_type or get_service_type_from_service_name(service.name)
        
        if cohort_service_type != service_service_type and cohort_service_type != "UNKNOWN":
            issues.append({
                'client_name': client.name,
                'contract_id': contract.id,
                'service_name': service.name,
                'service_service_type': service_service_type,
                'cohort_slug': cohort_slug,
                'cohort_service_type': cohort_service_type,
                'period_id': period.id
            })
    
    if issues:
        print(f"❌ Found {len(issues)} compatibility issues:")
        for issue in issues:
            print(f"  🔴 {issue['client_name']} | Contract {issue['contract_id']}")
            print(f"      Service: {issue['service_name']} ({issue['service_service_type']})")
            print(f"      Cohort: {issue['cohort_slug']} ({issue['cohort_service_type']})")
            print(f"      Period ID: {issue['period_id']}")
            print()
    else:
        print("✅ No compatibility issues found!")
    
    return issues


def suggest_corrections(db: Session, issues: list):
    """
    Suggest corrections for compatibility issues
    """
    if not issues:
        return
    
    print("💡 Suggested corrections:")
    print("=" * 50)
    
    for issue in issues:
        cohort_service_type = issue['cohort_service_type']
        
        # Find services with matching program type
        matching_services = db.exec(
            select(Service).where(Service.service_type == cohort_service_type)
        ).all()
        
        if matching_services:
            print(f"🔧 Client: {issue['client_name']}")
            print(f"   Problem: Cohort '{issue['cohort_slug']}' ({cohort_service_type}) assigned to")
            print(f"            Service '{issue['service_name']}' ({issue['service_service_type']})")
            print(f"   Solutions:")
            for service in matching_services:
                print(f"     • Move to service: '{service.name}' (ID: {service.id})")
            print(f"   SQL to fix:")
            if matching_services:
                correct_service = matching_services[0]
                print(f"     UPDATE servicecontract SET service_id = {correct_service.id} WHERE id = {issue['contract_id']};")
            print()


def apply_corrections(db: Session, issues: list, apply_fixes: bool = False):
    """
    Apply automatic corrections for compatibility issues
    """
    if not issues or not apply_fixes:
        return
    
    print("🛠️  Applying automatic corrections...")
    
    for issue in issues:
        cohort_service_type = issue['cohort_service_type']
        
        # Find the best matching service
        matching_services = db.exec(
            select(Service).where(Service.service_type == cohort_service_type)
        ).all()
        
        if matching_services:
            correct_service = matching_services[0]  # Use the first matching service
            
            # Update the contract to use the correct service
            contract = db.get(ServiceContract, issue['contract_id'])
            if contract:
                old_service_id = contract.service_id
                contract.service_id = correct_service.id
                db.add(contract)
                
                print(f"✅ Fixed Contract {issue['contract_id']}: {issue['client_name']}")
                print(f"   Service: {issue['service_name']} → {correct_service.name}")
                print(f"   Cohort: {issue['cohort_slug']} ({cohort_service_type})")
    
    if apply_fixes:
        db.commit()
        print("💾 All corrections applied and saved!")


def main():
    """
    Main function to run the compatibility fix script
    """
    with Session(engine) as db:
        print("🚀 Starting cohort-service compatibility fix...")
        print("=" * 60)
        
        # Step 1: Populate service program types
        populate_service_service_types(db)
        print()
        
        # Step 2: Find compatibility issues
        issues = find_compatibility_issues(db)
        print()
        
        # Step 3: Suggest corrections
        suggest_corrections(db, issues)
        
        # Step 4: Ask user if they want to apply fixes
        if issues:
            response = input("Do you want to apply the suggested corrections? (y/N): ").lower()
            if response in ['y', 'yes']:
                apply_corrections(db, issues, apply_fixes=True)
                print()
                print("🔍 Re-checking for remaining issues...")
                remaining_issues = find_compatibility_issues(db)
                if not remaining_issues:
                    print("🎉 All compatibility issues resolved!")
            else:
                print("ℹ️  No corrections applied. You can run this script again later.")


if __name__ == "__main__":
    main() 