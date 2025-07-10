import React from "react";
import {
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  Input,
  Button,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  useDisclosure,
  Chip,
  Spinner,
  Card,
  CardBody,
} from "@heroui/react";
import { Icon } from "@iconify/react";
import {
  clientApi,
  ClientRead,
  ClientMissingExternalId,
  ClientExternalIdCreate,
} from "../utils/api";

interface ClientWithMissingIds extends ClientRead {
  missingExternalIds: string[];
  externalIds: Record<string, string>;
}

const ClientManagement: React.FC = () => {
  const [clients, setClients] = React.useState<ClientWithMissingIds[]>([]);
  const [searchTerm, setSearchTerm] = React.useState("");
  const [selectedClient, setSelectedClient] =
    React.useState<ClientWithMissingIds | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [isUpdating, setIsUpdating] = React.useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Define the external ID systems we track
  const externalIdSystems = ["holded", "fourgeeks", "notion"];

  const fetchClients = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch all clients and missing external IDs in parallel
      const [clientsResponse, missingIdsResponse] = await Promise.all([
        clientApi.getClients(),
        clientApi.getClientsMissingExternalIds(),
      ]);

      if (clientsResponse.error) {
        throw new Error(clientsResponse.error);
      }

      if (missingIdsResponse.error) {
        throw new Error(missingIdsResponse.error);
      }

      const allClients = clientsResponse.data || [];
      const missingIds = missingIdsResponse.data || [];

      // Create a map of missing external IDs by client ID
      const missingIdsByClient = missingIds.reduce((acc, missing) => {
        if (!acc[missing.id]) {
          acc[missing.id] = [];
        }
        acc[missing.id].push(missing.system);
        return acc;
      }, {} as Record<number, string[]>);

      // Combine client data with missing external IDs information
      const clientsWithMissingIds: ClientWithMissingIds[] = allClients.map(
        (client) => {
          const missingExternalIds = missingIdsByClient[client.id] || [];
          const externalIds: Record<string, string> = {};

          // For each system, check if it's missing or present
          externalIdSystems.forEach((system) => {
            if (!missingExternalIds.includes(system)) {
              externalIds[system] = "Present"; // We don't have the actual ID in the response
            }
          });

          return {
            ...client,
            missingExternalIds,
            externalIds,
          };
        }
      );

      setClients(clientsWithMissingIds);
    } catch (err) {
      console.error("Error fetching clients:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch clients");
    } finally {
      setIsLoading(false);
    }
  };

  React.useEffect(() => {
    fetchClients();
  }, []);

  const filteredClients = clients.filter(
    (client) =>
      client.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      client.identifier?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleEditClient = (client: ClientWithMissingIds) => {
    setSelectedClient(client);
    onOpen();
  };

  const handleSaveClient = async (updatedClient: ClientWithMissingIds) => {
    if (!selectedClient) return;

    setIsUpdating(true);
    try {
      // Update external IDs that have been added
      const promises = externalIdSystems.map(async (system) => {
        const currentValue = updatedClient.externalIds[system];
        const wasEmpty = selectedClient.missingExternalIds.includes(system);

        if (wasEmpty && currentValue && currentValue !== "Present") {
          // Add the new external ID
          const externalIdData: ClientExternalIdCreate = {
            system,
            external_id: currentValue,
          };
          return clientApi.addExternalId(selectedClient.id, externalIdData);
        }
        return null;
      });

      const results = await Promise.all(promises);

      // Check for any errors
      const errors = results.filter((result) => result?.error);
      if (errors.length > 0) {
        throw new Error(errors[0]?.error || "Failed to update external IDs");
      }

      // Refresh the client list
      await fetchClients();
      onClose();
    } catch (err) {
      console.error("Error updating client:", err);
      setError(err instanceof Error ? err.message : "Failed to update client");
    } finally {
      setIsUpdating(false);
    }
  };

  const getSystemLabel = (system: string) => {
    switch (system) {
      case "holded":
        return "Holded ID";
      case "fourgeeks":
        return "4Geeks ID";
      case "notion":
        return "Notion ID";
      default:
        return `${system} ID`;
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size="lg" label="Loading clients..." />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-danger">
        <CardBody>
          <div className="flex items-center gap-2 text-danger">
            <Icon icon="lucide:alert-circle" />
            <span>Error: {error}</span>
          </div>
          <Button
            color="primary"
            variant="light"
            className="mt-2"
            onPress={fetchClients}
          >
            Retry
          </Button>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Client Management</h1>
          <p className="text-sm text-default-500 mt-1">
            <Icon icon="lucide:arrow-up" className="inline text-xs mr-1" />
            Clients with more missing external IDs are prioritized at the top by
            the API
          </p>
          <p className="text-sm text-default-400 mt-1">
            <Icon icon="lucide:filter" className="inline text-xs mr-1" />
            Only showing clients with active contracts or missing contracts
          </p>
        </div>
        <Button
          color="primary"
          variant="light"
          onPress={fetchClients}
          startContent={<Icon icon="lucide:refresh-cw" />}
        >
          Refresh
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
        <Input
          placeholder="Search clients by name or email..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          startContent={<Icon icon="lucide:search" />}
          className="max-w-sm"
        />

        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Icon icon="lucide:alert-triangle" className="text-danger" />
            <span className="text-default-600">
              {clients.filter((c) => c.missingExternalIds.length > 0).length}{" "}
              clients need attention
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Icon icon="lucide:check-circle" className="text-success" />
            <span className="text-default-600">
              {clients.filter((c) => c.missingExternalIds.length === 0).length}{" "}
              clients complete
            </span>
          </div>
        </div>
      </div>

      <Table aria-label="Clients table" removeWrapper>
        <TableHeader>
          <TableColumn>NAME</TableColumn>
          <TableColumn>EMAIL</TableColumn>
          <TableColumn>MISSING IDS</TableColumn>
          <TableColumn>HOLDED ID</TableColumn>
          <TableColumn>4GEEKS ID</TableColumn>
          <TableColumn>NOTION ID</TableColumn>
          <TableColumn>ACTIONS</TableColumn>
        </TableHeader>
        <TableBody>
          {filteredClients.map((client) => (
            <TableRow key={client.id}>
              <TableCell>
                <div className="font-medium">{client.name || "No name"}</div>
              </TableCell>
              <TableCell>
                <div className="text-sm text-default-600">
                  {client.identifier}
                </div>
              </TableCell>
              <TableCell>
                {client.missingExternalIds.length > 0 ? (
                  <div className="flex items-center gap-2">
                    <Chip
                      color="danger"
                      variant="flat"
                      size="sm"
                      startContent={
                        <Icon
                          icon="lucide:alert-triangle"
                          className="text-xs"
                        />
                      }
                    >
                      {client.missingExternalIds.length} missing
                    </Chip>
                  </div>
                ) : (
                  <Chip color="success" variant="flat" size="sm">
                    Complete
                  </Chip>
                )}
              </TableCell>
              <TableCell>
                {client.missingExternalIds.includes("holded") ? (
                  <Chip color="danger" variant="flat" size="sm">
                    Missing
                  </Chip>
                ) : (
                  <Chip color="success" variant="flat" size="sm">
                    Present
                  </Chip>
                )}
              </TableCell>
              <TableCell>
                {client.missingExternalIds.includes("fourgeeks") ? (
                  <Chip color="danger" variant="flat" size="sm">
                    Missing
                  </Chip>
                ) : (
                  <Chip color="success" variant="flat" size="sm">
                    Present
                  </Chip>
                )}
              </TableCell>
              <TableCell>
                {client.missingExternalIds.includes("notion") ? (
                  <Chip color="danger" variant="flat" size="sm">
                    Missing
                  </Chip>
                ) : (
                  <Chip color="success" variant="flat" size="sm">
                    Present
                  </Chip>
                )}
              </TableCell>
              <TableCell>
                <Button
                  color="primary"
                  variant="light"
                  size="sm"
                  onPress={() => handleEditClient(client)}
                  startContent={<Icon icon="lucide:edit" />}
                >
                  Edit
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {filteredClients.length === 0 && !isLoading && (
        <Card>
          <CardBody className="text-center py-8">
            <Icon
              icon="lucide:users"
              className="text-default-400 text-4xl mb-2"
            />
            <p className="text-default-500">No clients found</p>
          </CardBody>
        </Card>
      )}

      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <h3>Edit Client External IDs</h3>
                <p className="text-sm text-default-500">
                  {selectedClient?.name} - {selectedClient?.identifier}
                </p>
              </ModalHeader>
              <ModalBody>
                {selectedClient && (
                  <div className="space-y-4">
                    {externalIdSystems.map((system) => {
                      const isMissing =
                        selectedClient.missingExternalIds.includes(system);
                      const currentValue =
                        selectedClient.externalIds[system] || "";

                      return (
                        <Input
                          key={system}
                          label={getSystemLabel(system)}
                          placeholder={
                            isMissing
                              ? `Enter ${system} ID`
                              : "ID already present"
                          }
                          value={isMissing ? currentValue : "Present"}
                          onChange={(e) => {
                            if (isMissing) {
                              setSelectedClient({
                                ...selectedClient,
                                externalIds: {
                                  ...selectedClient.externalIds,
                                  [system]: e.target.value,
                                },
                              });
                            }
                          }}
                          isDisabled={!isMissing}
                          startContent={
                            <Icon
                              icon={isMissing ? "lucide:plus" : "lucide:check"}
                              className={
                                isMissing ? "text-danger" : "text-success"
                              }
                            />
                          }
                        />
                      );
                    })}
                  </div>
                )}
              </ModalBody>
              <ModalFooter>
                <Button color="danger" variant="light" onPress={onClose}>
                  Cancel
                </Button>
                <Button
                  color="primary"
                  onPress={() => handleSaveClient(selectedClient!)}
                  isLoading={isUpdating}
                >
                  Save Changes
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
