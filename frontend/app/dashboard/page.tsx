import { UploadStatementForm } from "@/components/merchants/UploadStatementForm";

export default function DashboardPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-sm text-gray-500">
          Stats, merchants, and reports land here in Phase 4.
        </p>
      </div>

      <UploadStatementForm />
    </div>
  );
}
