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
