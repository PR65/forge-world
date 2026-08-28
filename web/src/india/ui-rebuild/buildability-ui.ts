import type {
  BuildabilityItem,
  BuildabilityMetricInput,
  BuildabilityRequirementGroup,
  BuildabilityStatus,
  BuildabilityTabId,
  BuildabilityViewModel,
} from "./buildability-types";

export const NAV_ITEMS = ["Analyze", "Design", "Execute", "Discover", "Learn"] as const;

export const BOTTOM_TABS: ReadonlyArray<{ id: BuildabilityTabId; label: string; icon: string }> = [
  { id: "systems", label: "Systems", icon: "◎" },
  { id: "components", label: "Components", icon: "◇" },
  { id: "processes", label: "Processes", icon: "⌁" },
  { id: "equipment", label: "Equipment", icon: "▣" },
  { id: "materials", label: "Materials", icon: "◈" },
  { id: "facilities", label: "Facilities", icon: "▥" },
  { id: "capacity", label: "Capacity", icon: "◒" },
  { id: "evidence", label: "Evidence", icon: "▤" },
  { id: "imports", label: "Imports", icon: "⇄" },
  { id: "research-tasks", label: "Research Tasks", icon: "⌕" },
];

const REQUIREMENT_DEFINITIONS = [
  { id: "components", label: "Components", icon: "◇", field: "components" as const },
  { id: "processes", label: "Processes", icon: "⌁", field: "processes" as const },
  { id: "equipment", label: "Machines & equipment", icon: "▣", field: "equipment" as const },
  { id: "tooling", label: "Tooling & jigs", icon: "⌘", field: "tooling" as const },
  { id: "materials", label: "Materials", icon: "◈", field: "materials" as const },
  { id: "metrology", label: "Metrology & testing", icon: "⌾", field: "metrology" as const },
  { id: "qualification", label: "Qualification & standards", icon: "◇", field: "qualification" as const },
] as const;

const INTERNAL_LABEL_PATTERN = /^(?:reference(?:\s+primitive)?|primitive|node|record|shared)(?::|\s+)?(?:node|record|primitive)?\s*\d+$/i;
const CANONICAL_LABEL_PATTERN = /^[a-z][a-z0-9]*(?::[a-z0-9_-]+){1,}$/i;
const ACRONYMS = new Set([
  "AI",
  "API",
  "ATC",
  "CNC",
  "DC",
  "ECIL",
  "HVAC",
  "IP",
  "MRI",
  "RF",
  "RFQ",
  "R&D",
  "SW",
  "UI",
  "VMC",
]);

function phraseCase(value: string): string {
  return value
    .split(" ")
    .filter(Boolean)
    .map((word) => {
      const normalized = word.replace(/^[^a-zA-Z0-9&]+|[^a-zA-Z0-9&]+$/g, "");
      if (!normalized) return word;
      if (ACRONYMS.has(normalized.toUpperCase())) return normalized.toUpperCase();
      if (/^[A-Z0-9&]{2,6}$/.test(normalized)) return normalized;
      return normalized.charAt(0).toUpperCase() + normalized.slice(1).toLowerCase();
    })
    .join(" ");
}

/**
 * Turn a safe presentation label into readable copy without ever exposing a
 * generated primitive/canonical identifier.  IDs still travel through the
 * callback-only fields, never through the visible label.
 */
export function cleanDisplayText(value: unknown, fallback = "Mapped requirement"): string {
  const rawValue = String(value ?? "").trim();
  if (!rawValue || INTERNAL_LABEL_PATTERN.test(rawValue)) return fallback;
  const raw = rawValue
    .replace(/^reference\s+primitive\s*:\s*/i, "")
    .replace(/^(?:(?:shared|reference|primitive|node|record)(?::|\s+))+/i, "")
    .trim();
  if (!raw) return fallback;

  const explicitPublicLabel = /^canonical specification owner qualification and effective capacity are unknown$/i.test(raw)
    ? "Detailed product requirements"
    : raw.replace(/\s+capability remains unknown\.?$/i, "");
  const presentationParts = explicitPublicLabel.split(/\s+[—–]\s+/);
  const generatedVariant = presentationParts.length > 1 && /(?:production scale|fixed[- ]floor|programmable control|heavy payload|compact reach|vision guided|standalone|configuration|duty)/i.test(presentationParts.slice(1).join(" "));
  const publicRaw = generatedVariant ? presentationParts[0].trim() : raw;
  const duplicateParts = publicRaw.split(/\s+[—–]\s+/);
  const suffix = duplicateParts.length > 1 ? duplicateParts[duplicateParts.length - 1].trim() : "";
  const prefix = duplicateParts.slice(0, -1).join(" — ").trim();
  const deduped = suffix && prefix.toLowerCase().includes(suffix.toLowerCase()) ? prefix : publicRaw;
  const words = deduped
    .replace(/[/:]+/g, " ")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!words) return fallback;

  const canonicalWords = CANONICAL_LABEL_PATTERN.test(raw)
    ? words.replace(/^(shared|reference|primitive|node|record)\s+/i, "")
    : words;
  return phraseCase(canonicalWords) || fallback;
}

export function displayItemTitle(item: Pick<BuildabilityItem, "title"> | null | undefined): string {
  return cleanDisplayText(item?.title, "Mapped requirement");
}

/** Sanitize narrative copy while preserving sentence casing and punctuation. */
export function cleanNarrative(value: unknown, fallback = "Not recorded yet."): string {
  const raw = String(value ?? "").trim();
  if (!raw || INTERNAL_LABEL_PATTERN.test(raw)) return fallback;
  if (/reference[- ]only bridge|source pack names a primitive|canonical v1 record/i.test(raw)) {
    return "No validated India capability or supply record is attached; status remains UNKNOWN.";
  }
  if (/readable bridge for a dependency named by a breadth domain pack/i.test(raw)) {
    return "Exact product detail is limited; this family bridge does not establish a producer or supply claim.";
  }
  return raw
    .replace(/\b(?:shared|reference|primitive|node|record):[a-z0-9:_-]+\b/gi, "mapped requirement")
    .replace(/\b[a-z][a-z0-9]*_[a-z0-9_]+\b/gi, (match) => cleanDisplayText(match, "mapped requirement"))
    .replace(/\s+/g, " ")
    .trim() || fallback;
}

export function displayStatus(status: BuildabilityStatus | string | null | undefined): string {
  const normalized = statusTone(status);
  if (normalized === "available") return "Strong / available";
  if (normalized === "partial") return "Partial / import dependent";
  if (normalized === "missing") return "Missing";
  if (normalized === "conflicted") return "Conflicted";
  return "Unknown";
}

export type StatusTone = "available" | "partial" | "missing" | "unknown" | "conflicted";

export function statusTone(status: BuildabilityStatus | string | null | undefined): StatusTone {
  const value = String(status ?? "").trim().toLowerCase().replace(/[_\s]+/g, "-");
  if (value.includes("conflict")) return "conflicted";
  if (value.includes("missing") || value.includes("gap") || value.includes("critical")) return "missing";
  if (
    value.includes("partial") ||
    value.includes("import") ||
    value.includes("dependent") ||
    value.includes("scale") ||
    value.includes("limited")
  ) return "partial";
  if (
    value.includes("available") ||
    value.includes("strong") ||
    value.includes("made") ||
    value.includes("local") ||
    value.includes("evidenced") ||
    value.includes("reported")
  ) return "available";
  return "unknown";
}

export function statusLabel(
  status: BuildabilityStatus | string | null | undefined,
  explicitLabel?: string | null,
): string {
  const explicit = cleanDisplayText(explicitLabel, "");
  return explicit || displayStatus(status);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 }).format(value);
}

function metricObject(value: BuildabilityMetricInput): {
  value?: number | null;
  display?: string | null;
  unit?: string;
  description?: string | null;
} | null {
  return typeof value === "object" && value !== null ? value : null;
}

export function metricDisplay(value: BuildabilityMetricInput, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "string") return value.trim() || fallback;
  if (typeof value === "number") return Number.isFinite(value) ? `${formatNumber(value)}%` : fallback;

  const explicit = value.display?.trim();
  if (explicit) return explicit;
  if (typeof value.value !== "number" || !Number.isFinite(value.value)) return fallback;
  if (value.unit === "count") return formatNumber(value.value);
  if (value.unit === "score") return `${formatNumber(value.value)} / 100`;
  if (value.unit === "text") return String(value.value);
  return `${formatNumber(value.value)}%`;
}

export function metricDescription(value: BuildabilityMetricInput): string | null {
  return metricObject(value)?.description?.trim() || null;
}

export function metricAriaLabel(label: string, value: BuildabilityMetricInput): string {
  const description = metricDescription(value);
  return description ? `${label}: ${metricDisplay(value)}. ${description}` : `${label}: ${metricDisplay(value)}`;
}

export function formatCount(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-IN").format(value);
}

function inferredGroupStatus(items: BuildabilityItem[]): BuildabilityStatus {
  if (!items.length) return "unknown";
  const tones = items.map((item) => statusTone(item.status));
  if (tones.includes("missing")) return "missing";
  if (tones.includes("partial")) return "partial";
  if (tones.includes("unknown")) return "unknown";
  if (tones.includes("conflicted")) return "conflicted";
  return "available";
}

/** Build the stable seven-card requirement row from the view model. */
export function deriveRequirementGroups(viewModel: BuildabilityViewModel): BuildabilityRequirementGroup[] {
  if (viewModel.requirements?.length) return viewModel.requirements;
  return REQUIREMENT_DEFINITIONS.map(({ id, label, icon, field }) => {
    const items = viewModel[field] ?? [];
    return {
      id,
      title: label,
      icon,
      items,
      count: items.length,
      status: inferredGroupStatus(items),
    };
  });
}

export function statusMix(statusMix: BuildabilityItem["statusMix"], status: BuildabilityStatus | null | undefined): StatusTone[] {
  if (statusMix) {
    const tones: StatusTone[] = [];
    Object.entries(statusMix).forEach(([key, count]) => {
      if (typeof count === "number" && count > 0) tones.push(statusTone(key));
    });
    if (tones.length) return tones.slice(0, 5);
  }
  return [statusTone(status)];
}

export function hasUsableMapPosition(x: number | null | undefined, y: number | null | undefined): boolean {
  return typeof x === "number" && Number.isFinite(x) && typeof y === "number" && Number.isFinite(y);
}

export function clampMapCoordinate(value: number): number {
  return Math.max(3, Math.min(97, value));
}
