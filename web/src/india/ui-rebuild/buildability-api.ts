import type {
  BuildabilityBottleneck,
  BuildabilityEvidence,
  BuildabilityItem,
  BuildabilityPathStep,
  BuildabilityViewModel,
} from "./buildability-types";

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

function array(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function item(value: unknown): BuildabilityItem {
  const source = object(value);
  return {
    title: text(source.title) || text(source.name) || text(source.label) || "Mapped requirement",
    subtitle: text(source.subtitle) || text(source.role) || null,
    summary: text(source.summary) || text(source.detail) || text(source.purpose) || null,
    note: text(source.note) || text(source.basis) || text(source.condition) || null,
    kind: text(source.kind) || null,
    category: text(source.category) || null,
    status: text(source.status) || "UNKNOWN",
    statusLabel: text(source.status_label) || text(source.statusLabel) || null,
  };
}

function items(value: unknown): BuildabilityItem[] {
  return array(value).map(item);
}

function bottlenecks(value: unknown): BuildabilityBottleneck[] {
  return array(value).map((entry, index) => {
    const source = object(entry);
    const base = item(entry);
    return {
      ...base,
      // Recorded gap detail is the actual bottleneck; the source product name is context.
      title: text(source.detail) || base.title,
      rank: number(source.rank) ?? index + 1,
      impactLabel: text(source.impact_label) || text(source.severity) || null,
      reason: null,
    };
  });
}

function path(value: unknown): BuildabilityPathStep[] {
  return array(value).map((entry, index) => {
    const source = object(entry);
    return {
      ...item(entry),
      title: text(source.phase) || text(source.action) || `Step ${index + 1}`,
      summary: text(source.purpose) || null,
      note: null,
      order: number(source.sequence) ?? index + 1,
      timeLabel: text(source.time_label) || null,
    };
  });
}

function evidence(value: unknown): BuildabilityEvidence[] {
  return array(value).map((entry) => {
    const source = object(entry);
    return {
      title: text(source.title) || text(source.label) || "Evidence state",
      source: text(source.source) || null,
      type: text(source.type) || null,
      epistemicClass: text(source.epistemic_class) || text(source.epistemicClass) || null,
      confidenceLabel: text(source.confidence_label) || null,
      updatedLabel: text(source.updated_label) || null,
      summary: text(source.summary) || null,
    };
  });
}

function percentage(count: unknown, total: number | null) {
  const value = number(count);
  if (value === null || total === null || total <= 0) return null;
  return {
    value: Math.round((value / total) * 1000) / 10,
    unit: "percent" as const,
  };
}

export function normalizeBuildabilityViewModel(value: unknown): BuildabilityViewModel {
  const source = object(value);
  const buildability = object(source.buildability);
  const total = number(buildability.evaluated_node_count);
  return {
    title: text(source.title) || "Selected industrial product",
    domain: text(source.domain) || null,
    kind: text(source.kind) || null,
    category: text(source.category) || null,
    complexity: text(source.complexity) || null,
    plainSummary: text(source.plain_summary) || text(source.plainSummary) || null,
    buildability: {
      available: percentage(buildability.available, total),
      partialOrImportDependent: percentage(buildability.partial_or_import_dependent, total),
      missing: percentage(buildability.missing, total),
      unknown: percentage(buildability.unknown, total),
      overallIndex: null,
      assessedLabel: total === null ? null : `${total.toLocaleString("en-IN")} mapped requirements assessed`,
    },
    majorSystems: items(source.major_systems),
    criticalBottlenecks: bottlenecks(source.critical_bottlenecks),
    localizationPath: path(source.localization_path),
    components: items(source.components),
    processes: items(source.processes),
    equipment: items(source.equipment),
    tooling: items(source.tooling),
    materials: items(source.materials),
    metrology: items(source.metrology),
    qualification: items(source.qualification),
    upstream: items(source.upstream),
    downstream: items(source.downstream),
    unlocks: items(source.unlocks),
    related: items(source.related),
    evidenceSummary: evidence(source.evidence_summary),
    facilities: items(source.facilities),
    mapPoints: [],
    imports: items(source.imports),
    indiaIndex: null,
  };
}

async function fetchJson(pathname: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(pathname, { signal });
  if (!response.ok) {
    const detail = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(detail?.detail || `Buildability request failed (${response.status}).`);
  }
  return response.json();
}

export async function fetchBuildability(recordId: string, signal?: AbortSignal): Promise<BuildabilityViewModel> {
  const payload = await fetchJson(`/api/india/buildability/${encodeURIComponent(recordId)}`, signal);
  return normalizeBuildabilityViewModel(payload);
}

export async function analyzeBuildability(query: string, signal?: AbortSignal): Promise<BuildabilityViewModel> {
  const params = new URLSearchParams({ q: query.trim() });
  const payload = await fetchJson(`/api/india/buildability?${params.toString()}`, signal);
  return normalizeBuildabilityViewModel(payload);
}
