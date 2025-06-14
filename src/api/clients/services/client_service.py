from typing import List, Optional, Dict
from sqlmodel import Session, select
from src.api.clients.models.client import Client, ClientExternalId
from src.api.clients.schemas.client import ClientCreate, ClientUpdate, ClientExternalIdCreate


class ClientService:
    def __init__(self, db: Session):
        self.db = db

    def create_client(self, client_data: ClientCreate) -> Client:
        """Create a new client"""
        client = Client(name=client_data.name)
        client.identifier = client_data.identifier  # This will encrypt the identifier

        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def get_client(self, client_id: int) -> Optional[Client]:
        """Get a client by ID"""
        return self.db.get(Client, client_id)

    def get_client_by_identifier(self, identifier: str) -> Optional[Client]:
        """Get a client by identifier (decrypted)"""
        # This is inefficient as we need to decrypt each record to check
        # In a real-world scenario, we might want to use a hash or other indexable value
        clients = self.db.exec(select(Client)).all()
        for client in clients:
            if client.identifier == identifier:
                return client
        return None

    def get_clients(self, skip: int = 0, limit: int = 100) -> List[Client]:
        """Get a list of clients"""
        return self.db.exec(select(Client).offset(skip).limit(limit)).all()

    def get_clients_with_no_external_id(self, system: str) -> List[Client]:
        """Get a list of clients that don't have an external ID for a specific system"""
        # Get all clients
        all_clients = self.db.exec(select(Client)).all()

        # Get all clients that have an external ID for the specified system
        clients_with_external_id = set()
        external_ids = self.db.exec(select(ClientExternalId).where(
            ClientExternalId.system == system)).all()

        for ext_id in external_ids:
            clients_with_external_id.add(ext_id.client_id)

        # Filter clients that don't have the external ID
        return [client for client in all_clients if client.id not in clients_with_external_id]

    def update_client(self, client_id: int, client_data: ClientUpdate) -> Optional[Client]:
        """Update a client"""
        client = self.db.get(Client, client_id)
        if not client:
            return None

        client_data_dict = client_data.model_dump(exclude_unset=True)

        # Handle encrypted fields separately
        if "identifier" in client_data_dict:
            client.identifier = client_data_dict.pop("identifier")

        # Update other fields
        for key, value in client_data_dict.items():
            setattr(client, key, value)

        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def delete_client(self, client_id: int) -> bool:
        """Delete a client"""
        client = self.db.get(Client, client_id)
        if not client:
            return False

        self.db.delete(client)
        self.db.commit()
        return True

    def add_external_id(self, client_id: int, external_id_data: ClientExternalIdCreate) -> ClientExternalId:
        """Add an external ID to a client"""
        external_id = ClientExternalId(
            client_id=client_id,
            system=external_id_data.system
        )
        # This will encrypt the external ID
        external_id.external_id = external_id_data.external_id

        self.db.add(external_id)
        self.db.commit()
        self.db.refresh(external_id)
        return external_id

    def get_client_by_external_id(self, system: str, external_id: str) -> Optional[Client]:
        """Get a client by external ID"""
        # This is inefficient as we need to decrypt each record to check
        external_ids = self.db.exec(select(ClientExternalId).where(
            ClientExternalId.system == system)).all()

        for ext_id in external_ids:
            if ext_id.external_id == external_id:
                return ext_id.client

        return None
    
    def get_client_external_id(self, client_id: int, system: str) -> Optional[ClientExternalId]:
        """Get a client external ID"""
        return self.db.exec(select(ClientExternalId).where(
            ClientExternalId.client_id == client_id,
            ClientExternalId.system == system
        )).first()

    def get_clients_missing_external_id(self) -> List[dict]:
        # Example: define the systems you care about
        systems = ["holded", "fourgeeks", "notion"]
        all_clients = self.db.exec(select(Client)).all()
        result = []
        for client in all_clients:
            for system in systems:
                if not client.get_external_id(system):
                    result.append({
                        "id": client.id,
                        "name": client.name,
                        "identifier": client.identifier,
                        "system": system
                    })
        return result   