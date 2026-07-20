import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, Table, Button, Popconfirm, Tag, Modal, Tabs, message, Alert } from "antd";
import type { ColumnsType } from "antd/es/table";
import { Link } from "@tanstack/react-router";
import { api } from "../../lib/api";

export const Route = createFileRoute("/_app/admin/")({
  component: AdminPage,
});

// ─── Types ────────────────────────────────────────────────────────────────────

interface AdminUserRow {
  id: number;
  email: string;
  role: string;
  participant_type: string;
  created_at: string;
  initiative_name?: string;
  initiative_status?: string;
  answer_count: number;
}

interface AdminInitiativeRow {
  id: number;
  user_email: string;
  name: string;
  participant_type: string;
  status: string;
  created_at: string;
  answer_count: number;
}

// ─── AdminPage ────────────────────────────────────────────────────────────────

function AdminPage() {
  const [messageApi, contextHolder] = message.useMessage();

  // ─── Data fetching ─────────────────────────────────────────────────────────

  const {
    data: users = [],
    isLoading: usersLoading,
    refetch: refetchUsers,
  } = useQuery<AdminUserRow[]>({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const res = await api.get<AdminUserRow[]>("/admin/users");
      return res.data;
    },
  });

  const {
    data: initiatives = [],
    isLoading: initiativesLoading,
    refetch: refetchInitiatives,
  } = useQuery<AdminInitiativeRow[]>({
    queryKey: ["admin-initiatives"],
    queryFn: async () => {
      const res = await api.get<AdminInitiativeRow[]>("/admin/initiatives");
      return res.data;
    },
  });

  // ─── Mutations ─────────────────────────────────────────────────────────────

  const deleteUserMutation = useMutation({
    mutationFn: (userId: number) => api.delete(`/admin/users/${userId}`),
    onSuccess: () => {
      void messageApi.success("User deleted");
      void refetchUsers();
    },
    onError: () => void messageApi.error("Failed to delete user"),
  });

  const deleteInitiativeMutation = useMutation({
    mutationFn: (initiativeId: number) =>
      api.delete(`/admin/initiatives/${initiativeId}`),
    onSuccess: () => {
      void messageApi.success("Initiative deleted");
      void refetchInitiatives();
    },
    onError: () => void messageApi.error("Failed to delete initiative"),
  });

  const resetDemoMutation = useMutation({
    mutationFn: () =>
      api.post<{ message: string; deleted_users: number }>("/admin/reset-demo"),
    onSuccess: (res) => {
      void messageApi.success(res.data.message);
      void refetchUsers();
      void refetchInitiatives();
    },
    onError: () => void messageApi.error("Reset failed"),
  });

  // ─── CSV Export ────────────────────────────────────────────────────────────

  const handleExport = async () => {
    try {
      const response = await api.get("/admin/export", { responseType: "blob" });
      const url = URL.createObjectURL(response.data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mami-dataset.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      void messageApi.error("Export failed");
    }
  };

  // ─── Reset Demo Confirmation ───────────────────────────────────────────────

  const handleResetDemo = () => {
    Modal.confirm({
      title: "Reset Demo Data",
      content:
        "Are you sure? This will permanently delete ALL non-admin users and their questionnaire data. This cannot be undone.",
      okText: "Reset Demo",
      okButtonProps: { danger: true },
      cancelText: "Cancel",
      onOk: () => resetDemoMutation.mutateAsync(),
    });
  };

  // ─── Table column definitions ──────────────────────────────────────────────

  const userColumns: ColumnsType<AdminUserRow> = [
    {
      title: "Email",
      dataIndex: "email",
      sorter: (a, b) => a.email.localeCompare(b.email),
    },
    {
      title: "Role",
      dataIndex: "role",
      render: (r: string) => (
        <Tag color={r === "ADMIN" ? "red" : "blue"}>{r}</Tag>
      ),
    },
    {
      title: "Actions",
      render: (_: unknown, record: AdminUserRow) =>
        record.role !== "ADMIN" ? (
          <Popconfirm
            title="Delete user?"
            description="Permanently deletes this user and all their data."
            okText="Delete"
            okButtonProps={{ danger: true }}
            cancelText="Cancel"
            onConfirm={() => deleteUserMutation.mutate(record.id)}
          >
            <Button danger size="small">
              Delete
            </Button>
          </Popconfirm>
        ) : (
          <span style={{ color: "#9CA3AF", fontSize: "0.75rem" }}>
            Protected
          </span>
        ),
    },
  ];

  const initiativeColumns: ColumnsType<AdminInitiativeRow> = [
    { title: "User", dataIndex: "user_email" },
    {
      title: "Initiative",
      dataIndex: "name",
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    { title: "Type", dataIndex: "participant_type" },
    {
      title: "Status",
      dataIndex: "status",
      render: (v: string) => (
        <Tag color={v === "submitted" ? "green" : "default"}>{v}</Tag>
      ),
    },
    { title: "Answers", dataIndex: "answer_count" },
    {
      title: "Created",
      dataIndex: "created_at",
      render: (v: string) => new Date(v).toLocaleDateString(),
    },
    {
      title: "Actions",
      render: (_: unknown, record: AdminInitiativeRow) => (
        <Popconfirm
          title="Delete questionnaire?"
          description="Permanently deletes this initiative and all its answers and evidence."
          okText="Delete"
          okButtonProps={{ danger: true }}
          cancelText="Cancel"
          onConfirm={() => deleteInitiativeMutation.mutate(record.id)}
        >
          <Button danger size="small">
            Delete
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // ─── Expandable row for Users tab ─────────────────────────────────────────

  const usersExpandable = {
    expandedRowRender: (record: AdminUserRow) => (
      <div
        style={{
          padding: "0.75rem 1.5rem",
          background: "#F9FAFB",
          borderRadius: "8px",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "0.5rem",
            fontSize: "0.875rem",
            color: "#374151",
          }}
        >
          <div>
            <strong>Participant type:</strong> {record.participant_type}
          </div>
          <div>
            <strong>Initiative name:</strong>{" "}
            {record.initiative_name ?? "No initiative yet"}
          </div>
          <div>
            <strong>Initiative status:</strong>{" "}
            {record.initiative_status ?? "—"}
          </div>
          <div>
            <strong>Answers saved:</strong> {record.answer_count}
          </div>
          <div>
            <strong>Registered:</strong>{" "}
            {new Date(record.created_at).toLocaleString()}
          </div>
        </div>
      </div>
    ),
    rowExpandable: () => true,
  };

  // ─── Tab definitions ───────────────────────────────────────────────────────

  const tabItems = [
    {
      key: "users",
      label: `Users (${users.length})`,
      children: (
        <Table
          dataSource={users}
          columns={userColumns}
          rowKey="id"
          loading={usersLoading}
          expandable={usersExpandable}
          pagination={{ pageSize: 25, showSizeChanger: false }}
          size="small"
          style={{ borderRadius: "8px", overflow: "hidden" }}
        />
      ),
    },
    {
      key: "questionnaires",
      label: `Questionnaires (${initiatives.length})`,
      children: (
        <Table
          dataSource={initiatives}
          columns={initiativeColumns}
          rowKey="id"
          loading={initiativesLoading}
          pagination={{ pageSize: 25, showSizeChanger: false }}
          size="small"
          style={{ borderRadius: "8px", overflow: "hidden" }}
        />
      ),
    },
    {
      key: "actions",
      label: "Actions",
      children: (
        <div style={{ padding: "2rem 0", maxWidth: "600px" }}>
          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              color: "#06004f",
              marginBottom: "1rem",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            Export Data
          </h3>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgba(6,0,79,0.6)",
              marginBottom: "1rem",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            Download the complete dataset (all users, initiatives, and
            questionnaire answers) as a CSV file.
          </p>
          <Button
            type="primary"
            onClick={handleExport}
            style={{
              marginBottom: "3rem",
              borderRadius: "8px",
              fontFamily: "'Rubik', sans-serif",
              fontWeight: 600,
            }}
          >
            Download CSV
          </Button>

          <h3
            style={{
              fontSize: "1rem",
              fontWeight: 600,
              color: "#B91C1C",
              marginBottom: "1rem",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            Reset Demo
          </h3>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgba(6,0,79,0.6)",
              marginBottom: "1rem",
              fontFamily: "'Rubik', sans-serif",
            }}
          >
            Delete all non-admin users and their data. Use this between demo
            runs to restore a clean state. Admin accounts are never deleted.
            This action cannot be undone.
          </p>
          <Alert
            type="warning"
            message="This action permanently deletes all non-admin user data and cannot be undone."
            style={{ marginBottom: "1rem", borderRadius: "8px" }}
            showIcon
          />
          <Button
            danger
            type="primary"
            size="large"
            loading={resetDemoMutation.isPending}
            onClick={handleResetDemo}
            style={{
              borderRadius: "8px",
              fontFamily: "'Rubik', sans-serif",
              fontWeight: 600,
            }}
          >
            Reset Demo Data
          </Button>
        </div>
      ),
    },
  ];

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
      {contextHolder}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
        }}
      >
        <h1
          style={{
            fontSize: "1.75rem",
            fontWeight: 700,
            color: "#06004f",
            margin: 0,
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          Admin Panel
        </h1>
        <Link to="/admin/heatmap">
          <Button
            type="default"
            style={{ fontFamily: "'Rubik', sans-serif", fontWeight: 500 }}
          >
            View Aggregated Heatmap &rarr;
          </Button>
        </Link>
      </div>
      <Card
        style={{
          borderRadius: "16px",
          boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
        }}
      >
        <Tabs items={tabItems} defaultActiveKey="users" />
      </Card>
    </div>
  );
}
