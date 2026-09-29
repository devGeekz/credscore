import { riskLabel } from "@/lib/format";
import type { RiskTag } from "@/lib/reports";

const STYLES: Record<string, string> = {
  strong: "bg-green-100 text-green-800",
  moderate: "bg-amber-100 text-amber-800",
  high_risk: "bg-red-100 text-red-800",
  unscored: "bg-gray-100 text-gray-600",
};

export function RiskBadge({ tag }: { tag: RiskTag | null | undefined }) {
  const key = tag ?? "unscored";
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STYLES[key]}`}
    >
      {riskLabel(tag)}
    </span>
  );
}
