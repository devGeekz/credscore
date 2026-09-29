const CEDI = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  maximumFractionDigits: 0,
});

const CEDI_PRECISE = new Intl.NumberFormat("en-GH", {
  style: "currency",
  currency: "GHS",
  minimumFractionDigits: 2,
});

export function formatCedis(amount: number | null | undefined, precise = false): string {
  if (amount === null || amount === undefined) return "—";
  return (precise ? CEDI_PRECISE : CEDI).format(amount);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(1)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function riskLabel(tag: string | null | undefined): string {
  return tag ? tag.replace("_", " ") : "unscored";
}
