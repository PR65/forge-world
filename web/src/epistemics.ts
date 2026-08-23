export type EpistemicTone =
  | "unknown"
  | "conflicted"
  | "assumption"
  | "scenario"
  | "estimated"
  | "modelled"
  | "derived"
  | "reported"
  | "measured";

export function epistemicTone(value?: string | null): EpistemicTone {
  const upper = (value ?? "").trim().toUpperCase();
  if (!upper || upper.includes("UNKNOWN")) return "unknown";
  if (upper.includes("CONFLICT")) return "conflicted";
  if (upper.includes("ASSUMPTION")) return "assumption";
  if (upper.includes("SCENARIO")) return "scenario";
  if (upper.includes("ESTIMAT")) return "estimated";
  if (upper.includes("MODEL")) return "modelled";
  if (upper.includes("DERIVED")) return "derived";
  if (upper.includes("REPORTED")) return "reported";
  if (upper.includes("MEASURED")) return "measured";
  return "unknown";
}

export function epistemicLabel(value?: string | null): string {
  return value?.trim() || "UNKNOWN";
}

export function epistemicChipClass(value?: string | null): string {
  const tone = epistemicTone(value);
  if (tone === "unknown") return "unknown";
  if (tone === "conflicted") return "binding";
  if (tone === "assumption" || tone === "scenario" || tone === "estimated") return "warn";
  if (tone === "measured") return "ok";
  if (tone === "modelled" || tone === "derived") return "modelled";
  return "reported";
}
