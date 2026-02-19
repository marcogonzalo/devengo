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
  ClientUpdate,
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

  // Email editing states
  const [selectedClientForEmail, setSelectedClientForEmail] =
    React.useState<ClientWithMissingIds | null>(null);
  const [newEmail, setNewEmail] = React.useState("");
  const [showEmailConfirmation, setShowEmailConfirmation] =
    React.useState(false);
  const [isUpdatingEmail, setIsUpdatingEmail] = React.useState(false);
  const {
    isOpen: isEmailModalOpen,
    onOpen: onEmailModalOpen,
    onClose: onEmailModalClose,
  } = useDisclosure();

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
      const missingIdsByClient = missingIds.reduce(
        (acc, missing) => {
          if (!acc[missing.id]) {
            acc[missing.id] = [];
          }
          acc[missing.id].push(missing.system);
          return acc;
        },
        {} as Record<number, string[]>,
      );

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
        },
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
      client.identifier?.toLowerCase().includes(searchTerm.toLowerCase()),
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

  const handleEditEmail = (client: ClientWithMissingIds) => {
    setSelectedClientForEmail(client);
    setNewEmail(client.identifier);
    setShowEmailConfirmation(false);
    onEmailModalOpen();
  };

  const handleEmailChange = () => {
    if (!newEmail.trim()) {
      setError("Email cannot be empty");
      return;
    }

    if (newEmail === selectedClientForEmail?.identifier) {
      setError("New email is the same as current email");
      return;
    }

    setShowEmailConfirmation(true);
  };

  const handleConfirmEmailChange = async () => {
    if (!selectedClientForEmail) return;

    setIsUpdatingEmail(true);
    setError(null);

    try {
      const updateData = { identifier: newEmail.trim() };
      const response = await clientApi.updateClient(
        selectedClientForEmail.id,
        updateData,
      );

      if (response.error) {
        throw new Error(response.error);
      }

      // Refresh the client list
      await fetchClients();

      // Close modals and reset states
      onEmailModalClose();
      setSelectedClientForEmail(null);
      setNewEmail("");
      setShowEmailConfirmation(false);
    } catch (err) {
      console.error("Error updating client email:", err);
      setError(err instanceof Error ? err.message : "Failed to update email");
    } finally {
      setIsUpdatingEmail(false);
    }
  };

  const handleCancelEmailChange = () => {
    setShowEmailConfirmation(false);
    setNewEmail(selectedClientForEmail?.identifier || "");
  };

  const handleCloseEmailModal = () => {
    onEmailModalClose();
    setSelectedClientForEmail(null);
    setNewEmail("");
    setShowEmailConfirmation(false);
    setError(null);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size="lg" color="primary" />
      </div>
    );
  }

  if (error && clients.length === 0) {
    return (
      <div className="p-6">
        <div
          className="flex items-center gap-3 p-4 rounded-lg"
          style={{
            backgroundColor: "rgba(220,38,38,0.06)",
            border: "1px solid rgba(220,38,38,0.2)",
          }}
        >
          <Icon
            icon="lucide:alert-circle"
            width={18}
            height={18}
            style={{ color: "#dc2626" }}
          />
          <p className="text-sm" style={{ color: "#dc2626" }}>
            Error: {error}
          </p>
          <Button
            size="sm"
            variant="bordered"
            onPress={fetchClients}
            className="ml-auto"
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const needAttention = clients.filter(
    (c) => c.missingExternalIds.length > 0,
  ).length;
  const complete = clients.filter(
    (c) => c.missingExternalIds.length === 0,
  ).length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1
            className="text-xl font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            Client Management
          </h1>
          <p
            className="text-sm mt-0.5"
            style={{ color: "var(--muted-foreground)" }}
          >
            Manage client external IDs and contact information
          </p>
        </div>
        <Button
          size="sm"
          variant="bordered"
          onPress={fetchClients}
          startContent={
            <Icon icon="lucide:refresh-cw" width={14} height={14} />
          }
        >
          Refresh
        </Button>
      </div>

      {/* Stats row */}
      <div className="flex gap-4">
        <div
          className="flex items-center gap-2.5 px-4 py-3 rounded-lg"
          style={{
            backgroundColor: "rgba(220,38,38,0.06)",
            border: "1px solid rgba(220,38,38,0.15)",
          }}
        >
          <Icon
            icon="lucide:alert-triangle"
            width={16}
            height={16}
            style={{ color: "#dc2626" }}
          />
          <span className="text-sm font-medium" style={{ color: "#dc2626" }}>
            {needAttention} need attention
          </span>
        </div>
        <div
          className="flex items-center gap-2.5 px-4 py-3 rounded-lg"
          style={{
            backgroundColor: "rgba(22,163,74,0.06)",
            border: "1px solid rgba(22,163,74,0.15)",
          }}
        >
          <Icon
            icon="lucide:check-circle"
            width={16}
            height={16}
            style={{ color: "#16a34a" }}
          />
          <span className="text-sm font-medium" style={{ color: "#16a34a" }}>
            {complete} complete
          </span>
        </div>
      </div>

      {/* Search + table container */}
      <div
        className="rounded-xl overflow-hidden"
        style={{
          backgroundColor: "var(--card)",
          border: "1px solid var(--border)",
          boxShadow: "0 1px 3px 0 rgba(0,0,0,0.04)",
        }}
      >
        {/* Search bar */}
        <div
          className="px-4 py-3"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <Input
            placeholder="Search by name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            startContent={
              <Icon
                icon="lucide:search"
                width={16}
                height={16}
                style={{ color: "var(--muted-foreground)" }}
              />
            }
            variant="bordered"
            size="sm"
            className="max-w-sm"
          />
        </div>

        <Table aria-label="Clients table" removeWrapper>
          <TableHeader>
            <TableColumn
              className="text-xs font-semibold uppercase tracking-wider"
              style={{
                color: "var(--muted-foreground)",
                backgroundColor: "var(--card)",
              }}
            >
              Name
            </TableColumn>
            <TableColumn
              className="text-xs font-semibold uppercase tracking-wider"
              style={{
                color: "var(--muted-foreground)",
                backgroundColor: "var(--card)",
              }}
            >
              Email
            </TableColumn>
            <TableColumn
              className="text-xs font-semibold uppercase tracking-wider"
              style={{
                color: "var(--muted-foreground)",
                backgroundColor: "var(--card)",
              }}
            >
              Holded ID
            </TableColumn>
            <TableColumn
              className="text-xs font-semibold uppercase tracking-wider"
              style={{
                color: "var(--muted-foreground)",
                backgroundColor: "var(--card)",
              }}
            >
              4Geeks ID
            </TableColumn>
            <TableColumn
              className="text-xs font-semibold uppercase tracking-wider"
              style={{
                color: "var(--muted-foreground)",
                backgroundColor: "var(--card)",
              }}
            >
              Notion ID
            </TableColumn>
            <TableColumn
              className="text-xs font-semibold uppercase tracking-wider"
              style={{
                color: "var(--muted-foreground)",
                backgroundColor: "var(--card)",
              }}
            >
              Actions
            </TableColumn>
          </TableHeader>
          <TableBody>
            {filteredClients.map((client) => (
              <TableRow key={client.id}>
                <TableCell>
                  <span
                    className="text-sm font-medium"
                    style={{ color: "var(--foreground)" }}
                  >
                    {client.name || "—"}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <span
                      className="text-sm"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      {client.identifier}
                    </span>
                    <Button
                      isIconOnly
                      variant="light"
                      size="sm"
                      onPress={() => handleEditEmail(client)}
                      className="w-6 h-6 min-w-0"
                    >
                      <Icon icon="lucide:pencil" width={12} height={12} />
                    </Button>
                  </div>
                </TableCell>
                <TableCell>
                  {client.missingExternalIds.includes("holded") ? (
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: "rgba(220,38,38,0.08)",
                        color: "#dc2626",
                      }}
                    >
                      Missing
                    </span>
                  ) : (
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: "rgba(22,163,74,0.08)",
                        color: "#16a34a",
                      }}
                    >
                      Present
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  {client.missingExternalIds.includes("fourgeeks") ? (
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: "rgba(220,38,38,0.08)",
                        color: "#dc2626",
                      }}
                    >
                      Missing
                    </span>
                  ) : (
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: "rgba(22,163,74,0.08)",
                        color: "#16a34a",
                      }}
                    >
                      Present
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  {client.missingExternalIds.includes("notion") ? (
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: "rgba(220,38,38,0.08)",
                        color: "#dc2626",
                      }}
                    >
                      Missing
                    </span>
                  ) : (
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{
                        backgroundColor: "rgba(22,163,74,0.08)",
                        color: "#16a34a",
                      }}
                    >
                      Present
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="light"
                    color="primary"
                    onPress={() => handleEditClient(client)}
                    startContent={
                      <Icon icon="lucide:pencil" width={13} height={13} />
                    }
                  >
                    Edit
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {filteredClients.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-16 gap-2">
            <Icon
              icon="lucide:users"
              width={32}
              height={32}
              style={{ color: "var(--muted-foreground)", opacity: 0.4 }}
            />
            <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>
              No clients found
            </p>
          </div>
        )}
      </div>

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

      {/* Email Editing Modal */}
      <Modal
        isOpen={isEmailModalOpen}
        onClose={handleCloseEmailModal}
        size="md"
      >
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">
                <h3>Edit Client Email</h3>
                <p className="text-sm text-default-500">
                  {selectedClientForEmail?.name}
                </p>
              </ModalHeader>
              <ModalBody>
                <div className="space-y-4">
                  <div className="text-sm text-default-600">
                    <span className="font-medium">Current Email:</span>{" "}
                    {selectedClientForEmail?.identifier}
                  </div>

                  <Input
                    type="email"
                    label="New Email"
                    placeholder="Enter new email address"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    startContent={<Icon icon="lucide:mail" />}
                    isDisabled={isUpdatingEmail}
                  />

                  {error && (
                    <div className="flex items-center gap-2 text-danger text-sm">
                      <Icon icon="lucide:alert-circle" />
                      <span>{error}</span>
                    </div>
                  )}

                  {showEmailConfirmation && (
                    <div className="p-4 bg-warning-50 border border-warning-200 rounded-lg">
                      <div className="flex items-start gap-3">
                        <Icon
                          icon="lucide:alert-triangle"
                          className="text-warning-600 mt-0.5"
                        />
                        <div>
                          <h4 className="font-medium text-warning-800">
                            Confirm Email Change
                          </h4>
                          <p className="text-sm text-warning-700 mt-1">
                            Are you sure you want to change the email from{" "}
                            <span className="font-mono bg-warning-100 px-1 rounded">
                              {selectedClientForEmail?.identifier}
                            </span>{" "}
                            to{" "}
                            <span className="font-mono bg-warning-100 px-1 rounded">
                              {newEmail}
                            </span>
                            ?
                          </p>
                          <p className="text-xs text-warning-600 mt-2">
                            This action cannot be undone easily and may affect
                            client communications.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </ModalBody>
              <ModalFooter>
                {showEmailConfirmation ? (
                  <>
                    <Button
                      color="default"
                      variant="light"
                      onPress={handleCancelEmailChange}
                      isDisabled={isUpdatingEmail}
                    >
                      Cancel
                    </Button>
                    <Button
                      color="warning"
                      onPress={handleConfirmEmailChange}
                      isLoading={isUpdatingEmail}
                    >
                      Confirm Change
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      color="danger"
                      variant="light"
                      onPress={handleCloseEmailModal}
                      isDisabled={isUpdatingEmail}
                    >
                      Cancel
                    </Button>
                    <Button
                      color="primary"
                      onPress={handleEmailChange}
                      isDisabled={isUpdatingEmail}
                    >
                      Update Email
                    </Button>
                  </>
                )}
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </div>
  );
};

export default ClientManagement;
