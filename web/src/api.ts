import type {
  CapabilityRecord,
  DesignComparison,
  DiscoverResponse,
  ObjectiveConfig,
  OperationalCaseResponse,
  PackDetail,
  ProgramProjection,
  ResearchResolution,
  ResearchTask,
  SolveResponse,
  WorldEvidenceRecord,
  WorldNode,
  WorldSlice,
  WorldSummary,
} from "./types";

function objectiveBody(cfg: ObjectiveConfig) {
  return {
    pack_id: cfg.packId,
    variant_id: cfg.variantId,
    annual_units: cfg.annualUnits,
    geography: cfg.geography,
    deadline_year: cfg.deadlineYear,
    min_dva: cfg.minDva,
    budget_usd: cfg.budgetUsd,
    funded_projects: cfg.fundedProjects,
    shocks: cfg.shocks,
    analyst_capacity_assumptions: Object.fromEntries(
      Object.entries(cfg.assumptions).map(([key, value]) => [key, value]),
    ),
    include_deep: cfg.includeDeep,
  };
}

async function jsonOrError<T>(response: Response, label: string): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${label}: ${response.status} ${text.slice(0, 300)}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchPacks(): Promise<
  { pack_id: string; title: string; variants: string[] }[]
> {
  const r = await fetch("/api/packs");
  if (!r.ok) throw new Error(`packs: ${r.status}`);
  return r.json();
}

export async function fetchPackDetail(id: string): Promise<PackDetail> {
  const r = await fetch(`/api/packs/${id}`);
  if (!r.ok) throw new Error(`pack: ${r.status}`);
  return r.json();
}

export async function solveObjective(
  cfg: ObjectiveConfig,
): Promise<SolveResponse> {
  const r = await fetch("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(objectiveBody(cfg)),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`solve failed: ${r.status} ${t.slice(0, 200)}`);
  }
  return r.json();
}

export async function runOperationalCase(
  cfg: ObjectiveConfig,
): Promise<OperationalCaseResponse> {
  const response = await fetch("/api/workbench/case", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(objectiveBody(cfg)),
  });
  return jsonOrError<OperationalCaseResponse>(response, "operational case");
}

export async function compareArchitecture(
  cfg: ObjectiveConfig,
  substitutionId: string,
): Promise<DesignComparison> {
  const response = await fetch("/api/design/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...objectiveBody(cfg),
      substitution_id: substitutionId,
    }),
  });
  return jsonOrError<DesignComparison>(response, "design comparison");
}

export async function resolveResearchTask(
  cfg: ObjectiveConfig,
  task: ResearchTask,
  capture: Record<string, unknown>,
  reviewer: string,
  approveForScenario: boolean,
): Promise<ResearchResolution> {
  const response = await fetch("/api/research/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      objective: objectiveBody(cfg),
      task,
      capture,
      reviewer,
      approve_for_scenario: approveForScenario,
    }),
  });
  return jsonOrError<ResearchResolution>(response, "research resolution");
}

export async function fetchCapabilityLeverage(
  limit = 50,
): Promise<DiscoverResponse> {
  const response = await fetch(
    `/api/discover/capabilities?limit=${encodeURIComponent(String(limit))}`,
  );
  return jsonOrError<DiscoverResponse>(response, "capability leverage");
}

export async function fetchProgram(packId: string): Promise<ProgramProjection> {
  const response = await fetch(`/api/program/${encodeURIComponent(packId)}`);
  return jsonOrError<ProgramProjection>(response, "program timeline");
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((v): v is string => typeof v === "string")
    : [];
}

function asCount(value: unknown): number {
  return typeof value === "number"
    ? value
    : Array.isArray(value)
      ? value.length
      : 0;
}

function normalizeNode(value: unknown, index: number): WorldNode | null {
  const raw = asRecord(value);
  if (!raw) return null;
  const id = asString(raw.id, `world-node-${index}`);
  const metadata = asRecord(raw.metadata) ?? {};
  return {
    id,
    name: asString(raw.name, asString(raw.label, id)),
    kind: asString(raw.kind, "unknown"),
    pack_id: typeof raw.pack_id === "string" ? raw.pack_id : null,
    canonical_id:
      typeof raw.canonical_id === "string" ? raw.canonical_id : null,
    epistemic_class: asString(raw.epistemic_class, "UNKNOWN"),
    evidence_ids: asStringArray(raw.evidence_ids),
    metadata,
  };
}

function normalizeSlice(value: unknown): WorldSlice | null {
  const raw = asRecord(value);
  if (!raw) return null;
  const nodeValues = Array.isArray(raw.nodes) ? raw.nodes : [];
  const nodes = nodeValues
    .map(normalizeNode)
    .filter((n): n is WorldNode => n !== null);
  const edgeValues = Array.isArray(raw.edges) ? raw.edges : [];
  const edges = edgeValues.flatMap((value) => {
    const edge = asRecord(value);
    if (!edge) return [];
    const src = asString(edge.src);
    const dst = asString(edge.dst);
    if (!src || !dst) return [];
    return [
      {
        src,
        relation: asString(edge.relation, "depends_on"),
        dst,
        meta: asRecord(edge.meta) ?? {},
      },
    ];
  });
  return {
    nodes,
    edges,
    root: typeof raw.root === "string" ? raw.root : null,
    truncated: raw.truncated === true,
  };
}

/** World endpoints are an optional surface during the registry rollout. */
export async function fetchWorldSummary(): Promise<WorldSummary | null> {
  try {
    const r = await fetch("/api/world/summary");
    if (!r.ok) return null;
    const raw = asRecord(await r.json());
    if (!raw) return null;
    return {
      nodes: asCount(raw.nodes) || asCount(raw.node_count),
      edges: asCount(raw.edges) || asCount(raw.edge_count),
      capabilities: asCount(raw.capabilities) || asCount(raw.capability_count),
      packs: asCount(raw.packs) || asCount(raw.pack_count),
      snapshot_id: typeof raw.snapshot_id === "string" ? raw.snapshot_id : null,
      hash: typeof raw.hash === "string" ? raw.hash : null,
      epistemic_counts: asRecord(raw.epistemic_counts) as
        | Record<string, number>
        | undefined,
    };
  } catch {
    return null;
  }
}

export async function fetchWorldSlice(
  packId?: string,
  root?: string,
  depth = 2,
  limit = 100,
): Promise<WorldSlice | null> {
  try {
    const params = new URLSearchParams({
      depth: String(depth),
      limit: String(limit),
    });
    if (packId) params.set("pack_id", packId);
    if (root) params.set("root", root);
    const r = await fetch(`/api/world/slice?${params.toString()}`);
    if (!r.ok) return null;
    return normalizeSlice(await r.json());
  } catch {
    return null;
  }
}

export async function fetchWorldCapabilities(): Promise<
  CapabilityRecord[] | null
> {
  try {
    const r = await fetch("/api/world/capabilities");
    if (!r.ok) return null;
    const value = await r.json();
    const values = Array.isArray(value)
      ? value
      : (asRecord(value)?.capabilities ?? asRecord(value)?.nodes);
    if (!Array.isArray(values)) return [];
    return values
      .map(normalizeNode)
      .filter((n): n is WorldNode => n !== null)
      .map((n) => {
        return {
          ...n,
          mapping_count: asCount(n.metadata.mapping_count),
          mapped_pack_ids: asStringArray(n.metadata.mapped_pack_ids),
          mapped_entity_ids: asStringArray(n.metadata.mapped_entity_ids),
          evidence_task_ids: asStringArray(n.metadata.evidence_task_ids),
        };
      });
  } catch {
    return null;
  }
}

export async function fetchWorldEvidence(
  evidenceId: string,
): Promise<WorldEvidenceRecord | null> {
  try {
    const r = await fetch(
      `/api/world/evidence/${encodeURIComponent(evidenceId)}`,
    );
    if (!r.ok) return null;
    const raw = asRecord(await r.json());
    if (!raw) return null;
    const sourceSnapshots = (
      Array.isArray(raw.source_snapshots) ? raw.source_snapshots : []
    ).flatMap((value) => {
      const source = asRecord(value);
      if (!source) return [];
      return [
        {
          snapshot_id: asString(source.snapshot_id),
          source_id: asString(source.source_id),
          content_hash: asString(source.content_hash),
          hash_scope: asString(source.hash_scope, "UNKNOWN"),
          raw_payload_stored: source.raw_payload_stored === true,
          access_date: asString(source.access_date),
          license: asString(source.license, "UNSPECIFIED"),
          storage_posture: asString(source.storage_posture, "UNKNOWN"),
          url: asString(source.url),
          metadata: asRecord(source.metadata) ?? {},
        },
      ];
    });
    const confidence = Object.fromEntries(
      Object.entries(asRecord(raw.confidence) ?? {}).filter(
        ([, value]) => value === null || typeof value === "number",
      ),
    ) as Record<string, number | null>;
    return {
      evidence_id: asString(raw.evidence_id, evidenceId),
      local_claim_id: asString(raw.local_claim_id),
      pack_id: typeof raw.pack_id === "string" ? raw.pack_id : null,
      subject: asString(raw.subject),
      predicate: asString(raw.predicate),
      epistemic_class: asString(raw.epistemic_class, "UNKNOWN"),
      value_text: asString(raw.value_text),
      quote_or_caveat: asString(raw.quote_or_caveat),
      source_ids: asStringArray(raw.source_ids),
      confidence,
      source_snapshots: sourceSnapshots,
    };
  } catch {
    return null;
  }
}

export async function searchWorld(
  query: string,
  packId?: string,
): Promise<WorldNode[]> {
  if (!query.trim()) return [];
  try {
    const params = new URLSearchParams({ q: query.trim() });
    if (packId) params.set("pack_id", packId);
    const r = await fetch(`/api/world/search?${params.toString()}`);
    if (!r.ok) return [];
    const value = await r.json();
    const values = Array.isArray(value)
      ? value
      : (asRecord(value)?.nodes ?? asRecord(value)?.results);
    if (!Array.isArray(values)) return [];
    return values.map(normalizeNode).filter((n): n is WorldNode => n !== null);
  } catch {
    return [];
  }
}

export async function fetchPacksSafe(): Promise<
  { pack_id: string; title: string; variants: string[] }[]
> {
  try {
    return await fetchPacks();
  } catch {
    return [];
  }
}

export async function fetchPackDetailSafe(
  id: string,
): Promise<PackDetail | null> {
  try {
    return await fetchPackDetail(id);
  } catch {
    return null;
  }
}
