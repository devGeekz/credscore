"use client";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-md rounded-lg border border-red-200 bg-white p-6 text-center">
      <h2 className="text-base font-semibold text-gray-900">Something went wrong</h2>
      <p className="mt-1 break-words text-sm text-gray-500">{error.message}</p>
      <button
        onClick={reset}
        className="mt-4 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
      >
        Try again
      </button>
    </div>
  );
}
