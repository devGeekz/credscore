"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { fetchCurrentUser, logout } from "@/lib/auth";
import type { User } from "@/lib/types";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch(() => {
        // 401s already redirect to /login via the axios interceptor.
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
        <span className="text-lg font-semibold text-gray-900">CredScore</span>
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-sm text-gray-500">
              {user.name} · <span className="capitalize">{user.role}</span>
            </span>
          )}
          <button onClick={logout} className="text-sm font-medium text-gray-500 hover:text-gray-900">
            Sign out
          </button>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-57px)] flex-col sm:flex-row">
        <Sidebar />
        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
