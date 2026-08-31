import { normalizeBuildabilityViewModel } from "../ui-rebuild/buildability-api";
import type { BuildabilityViewModel } from "../ui-rebuild/buildability-types";

type JsonObject = Record<string, unknown>;

function object(value: unknown): JsonObject {
  return value && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : {};
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function number(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function bool(value: unknown): boolean {
  return value === true;
}

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export interface ObjectiveContext {
  rawInput: string;
  productQuery: string;
  quantity: number | null;
  quantityText: string;
  quantityUnit: string;
  quantityIsApproximate: boolean;
  cadence: string;
  cadenceLabel: string;
  geography: string;
  geographyLabel: string;
  deadlineYear: number | null;
  modifiers: string[];
  constraints: string[];
}

export interface ObjectiveCandidate {
  title: string;
  domain: string;
  kind: string;
  summary: string;
  status: string;
  statusLabel: string;
  epistemicClass: string;
  matchBasis: string;
}

export interface ObjectiveResolution {
  objective: ObjectiveContext;
  classification: "EXACT" | "STRONG" | "NEAREST" | "UNRESOLVED";
  canAnalyze: boolean;
  requiresConfirmation: boolean;
  message: string;
  honestyNote: string;
  selected: ObjectiveCandidate | null;
  nearest: ObjectiveCandidate | null;
  candidates: ObjectiveCandidate[];
  analysis: BuildabilityViewModel | null;
}

export interface ObjectiveDemandLine {
  node_id: string;
  label: string;
  quantity: number | null;
  unit: string | null;
  quantity_state: string;
  coefficient_state: string | string[] | null;
}

export interface ObjectiveGapLine {
  node_id: string;
  label: string;
  required: number | null;
  capacity_lo: number | null;
  capacity_hi: number | null;
  gap_lo: number | null;
  gap_hi: number | null;
  coverage_ratio_lo: number | null;
  coverage_ratio_hi: number | null;
  unit: string | null;
  state: string;
}

export interface ObjectiveCompilation {
  schema_version: string;
  result_class: string;
  resolved_objective: Record<string, unknown>;
  demand_ledger: ObjectiveDemandLine[];
  capacity_ledger: Array<{
    node_id: string;
    label: string;
    capacity_lo: number | null;
    capacity_hi: number | null;
    unit: string | null;
    state: string;
    epistemic_class: string;
  }>;
  gap_ledger: ObjectiveGapLine[];
  bottlenecks: Array<{ node_id: string; label: string; reason: string; criticality: number }>;
  closure_actions: Array<{ id: string; category: string; label: string; reason: string }>;
  verification_frontier: Array<{ id: string; question: string; reason: string }>;
}

function candidate(value: unknown): ObjectiveCandidate | null {
  const source = object(value);
  const title = text(source.title);
  if (!title) return null;
  return {
    title,
    domain: text(source.domain),
    kind: text(source.kind),
    summary: text(source.summary),
    status: text(source.status) || "UNKNOWN",
    statusLabel: text(source.status_label) || "Unknown",
    epistemicClass: text(source.epistemic_class) || "UNKNOWN",
    matchBasis: text(source.match_basis) || "Atlas result",
  };
}

export async function resolveObjective(query: string, signal?: AbortSignal): Promise<ObjectiveResolution> {
  const params = new URLSearchParams({ q: query.trim() });
  const response = await fetch(`/api/india/resolve?${params.toString()}`, { signal });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || `Objective resolution failed (${response.status}).`);
  }
  const payload = object(await response.json());
  const objective = object(payload.objective);
  const resolution = object(payload.resolution);
  const selected = candidate(resolution.selected);
  const nearest = candidate(resolution.nearest);
  const candidates = array(resolution.candidates).map(candidate).filter((value): value is ObjectiveCandidate => Boolean(value));
  const classification = text(resolution.classification).toUpperCase();
  const analysisSource = object(resolution.analysis);
  return {
    objective: {
      rawInput: text(objective.raw_input) || query.trim(),
      productQuery: text(objective.product_query) || query.trim(),
      quantity: number(objective.quantity),
      quantityText: text(objective.quantity_text),
      quantityUnit: text(objective.quantity_unit),
      quantityIsApproximate: bool(objective.quantity_is_approximate),
      cadence: text(objective.cadence),
      cadenceLabel: text(objective.cadence_label),
      geography: text(objective.geography),
      geographyLabel: text(objective.geography_label),
      deadlineYear: number(objective.deadline_year),
      modifiers: array(objective.modifiers).map(text).filter(Boolean),
      constraints: array(objective.constraints).map(text).filter(Boolean),
    },
    classification: ["EXACT", "STRONG", "NEAREST", "UNRESOLVED"].includes(classification)
      ? classification as ObjectiveResolution["classification"]
      : "UNRESOLVED",
    canAnalyze: bool(resolution.can_analyze),
    requiresConfirmation: bool(resolution.requires_confirmation),
    message: text(resolution.message),
    honestyNote: text(resolution.honesty_note),
    selected,
    nearest,
    candidates,
    analysis: text(analysisSource.title) ? normalizeBuildabilityViewModel(analysisSource) : null,
  };
}

export async function compileObjective(
  context: ObjectiveContext,
  signal?: AbortSignal,
): Promise<ObjectiveCompilation> {
  if (context.quantity === null) throw new Error("A quantity is required for objective compilation.");
  const period = ({ PER_MONTH: "month", PER_WEEK: "week", PER_DAY: "day" } as const)[context.cadence as "PER_MONTH" | "PER_WEEK" | "PER_DAY"] || "year";
  const response = await fetch("/api/india/objective/compile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      objective: "manufacture",
      product: context.productQuery,
      quantity: context.quantity,
      unit: "units",
      period,
      geography: context.geography || "INDIA",
      target_year: context.deadlineYear || 2030,
      constraints: context.constraints.map((value) => ({ kind: "text", value })),
    }),
    signal,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || `Objective compilation failed (${response.status}).`);
  }
  return await response.json() as ObjectiveCompilation;
}
