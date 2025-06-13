import React from 'react';
import { Table, TableHeader, TableColumn, TableBody, TableRow, TableCell, Input, Button, Modal, ModalContent, ModalHeader, ModalBody, ModalFooter, useDisclosure, Chip } from "@heroui/react";
import { Icon } from '@iconify/react';

interface Client {
  id: string;
  name: string;
  externalIds: {
    crm?: string;
    invoicing?: string;
  };
}

const ClientManagement: React.FC = () => {
  const [clients, setClients] = React.useState<Client[]>([
    { id: '1', name: 'Acme Corp', externalIds: { crm: 'CRM001', invoicing: 'INV001' } },
    { id: '2', name: 'TechStart Inc', externalIds: { crm: 'CRM002' } },
    { id: '3', name: 'Global Services Ltd', externalIds: { invoicing: 'INV003' } },
  ]);
  const [searchTerm, setSearchTerm] = React.useState('');
  const [selectedClient, setSelectedClient] = React.useState<Client | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  const filteredClients = clients.filter(client =>
    client.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleEditClient = (client: Client) => {
    setSelectedClient(client);
    onOpen();
  };

  const handleSaveClient = (updatedClient: Client) => {
    setClients(clients.map(c => c.id === updatedClient.id ? updatedClient : c));
    onClose();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Client Management</h1>
      <Input
        placeholder="Search clients..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        startContent={<Icon icon="lucide:search" />}
      />
      <Table aria-label="Clients table" removeWrapper>
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>CRM ID</TableColumn>
          <TableColumn>INVOICING ID</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody>
          {filteredClients.map((client) => (
            <TableRow key={client.id}>
              <TableCell>{client.name}</TableCell>
              <TableCell>
                {client.externalIds.crm ? (
                  client.externalIds.crm
                ) : (
                  <Chip color="danger" variant="flat">Missing</Chip>
                )}
              </TableCell>
              <TableCell>
                {client.externalIds.invoicing ? (
                  client.externalIds.invoicing
                ) : (
                  <Chip color="danger" variant="flat">Missing</Chip>
                )}
              </TableCell>
              <TableCell>
                <Button color="primary" variant="light" onPress={() => handleEditClient(client)}>
                  Edit
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">Edit Client External IDs</ModalHeader>
              <ModalBody>
                {selectedClient && (
                  <div className="space-y-4">
                    <Input
                      label="CRM ID"
                      placeholder="Enter CRM ID"
                      value={selectedClient.externalIds.crm || ''}
                      onChange={(e) => setSelectedClient({
                        ...selectedClient,
                        externalIds: { ...selectedClient.externalIds, crm: e.target.value }
                      })}
                    />
                    <Input
                      label="Invoicing ID"
                      placeholder="Enter Invoicing ID"
                      value={selectedClient.externalIds.invoicing || ''}
                      onChange={(e) => setSelectedClient({
                        ...selectedClient,
                        externalIds: { ...selectedClient.externalIds, invoicing: e.target.value }
                      })}
                    />
                  </div>
                )}
              </ModalBody>
              <ModalFooter>
                <Button color="danger" variant="light" onPress={onClose}>
                  Cancel
                </Button>
                <Button color="primary" onPress={() => handleSaveClient(selectedClient!)}>
                  Save
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
};

export default ClientManagement;
