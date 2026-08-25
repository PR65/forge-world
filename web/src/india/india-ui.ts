import type { IndiaStatus } from "./india-types";

export function displayStatus(status: IndiaStatus | null | undefined): string {
  const value = String(status || "UNKNOWN")
    .trim()
    .replaceAll("_", " ")
    .replaceAll("-", " ");
  return value || "UNKNOWN";
}

export function statusTone(status: IndiaStatus | null | undefined): string {
  const value = displayStatus(status).toLowerCase();
  if (value.includes("evidenced") || value.includes("measured")) return "positive";
  if (value.includes("reported") || value.includes("partial")) return "caution";
  if (value.includes("import") || value.includes("dependent")) return "import";
  if (value.includes("conflict")) return "conflict";
  return "unknown";
}

export function formatCount(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Not counted";
  return new Intl.NumberFormat("en-IN").format(value);
}

export function firstSentence(value: string): string {
  const clean = value.trim();
  if (!clean) return "Not recorded yet.";
  const match = clean.match(/^(.+?[.!?])(?:\s|$)/);
  return match?.[1] ?? clean;
}

