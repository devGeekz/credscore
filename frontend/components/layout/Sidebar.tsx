"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/merchants", label: "Applicants" },
  { href: "/dashboard/reports", label: "Reports" },
  { href: "/dashboard/api-keys", label: "API keys" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex w-48 shrink-0 flex-col gap-1 border-r border-gray-200 bg-white p-4">
      {LINKS.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              active
                ? "bg-gray-900 text-white"
                : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
