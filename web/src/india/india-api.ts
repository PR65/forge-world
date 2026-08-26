import type {
  IndiaBootstrap,
  IndiaDependencyGroupKey,
  IndiaDependencyGroups,
  IndiaDiscoverResult,
  IndiaDomain,
  IndiaLink,
  IndiaMakingStep,
  IndiaRecord,
  IndiaSearchResult,
  IndiaStatus,
  IndiaSummary,
} from "./india-types";

type JsonObject = Record<string, unknown>;

const DEPENDENCY_KEYS: IndiaDependencyGroupKey[] = [
  "systems",
  "materials",
  "processes",
  "equipment",
  "capabilities",
];

const RESULT_KEYS = ["results", "records", "items", "nodes", "matches"];

function asObject(value: unknown): JsonObject | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonObject)
    : null;
}

function readObject(value: unknown, keys: string[]): JsonObject | null {
  const source = asObject(value);
  if (!source) return null;
  for (const key of keys) {
    const found = asObject(source[key]);
    if (found) return found;
  }
  return null;
}

function readValue(source: JsonObject | null, keys: string[]): unknown {
  if (!source) return undefined;
  for (const key of keys) {
    if (source[key] !== undefined && source[key] !== null) return source[key];
  }
  return undefined;
}

function readString(
  source: JsonObject | null,
  keys: string[],
  fallback = "",
): string {
  const value = readValue(source, keys);
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function readNumber(
  source: JsonObject | null,
  keys: string[],
): number | null {
  const value = readValue(source, keys);
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function readStringArray(source: JsonObject | null, keys: string[]): string[] {
  const value = readValue(source, keys);
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (typeof item === "string" && item.trim()) return [item.trim()];
    const itemObject = asObject(item);
    const label = readString(itemObject, ["label", "name", "title", "text"]);
    return label ? [label] : [];
  });
}

function arrayValue(value: unknown): unknown[] {
  if (Array.isArray(value)) return value;
  const object = asObject(value);
  if (!object) return [];
  for (const key of RESULT_KEYS) {
    if (Array.isArray(object[key])) return object[key] as unknown[];
  }
  return [];
}

function readArray(source: JsonObject | null, keys: string[]): unknown[] {
  for (const key of keys) {
    const value = readValue(source, [key]);
    const array = arrayValue(value);
    if (array.length || Array.isArray(value)) return array;
  }
  return [];
}

function normalizeLink(value: unknown, index: number): IndiaLink | null {
  if (typeof value === "string" && value.trim()) {
    return { id: value.trim(), label: value.trim() };
  }
  const source = asObject(value);
  if (!source) return null;
  const label = readString(
    source,
    ["label", "name", "canonical_name", "title", "text", "id"],
    `Linked capability ${index + 1}`,
  );
  const id = readString(source, ["id", "record_id", "canonical_id", "slug"]);
  return {
    id: id || null,
    label,
    kind: readString(source, ["kind", "type", "category"]) || undefined,
    note: readString(source, ["note", "explanation", "reason"]) || undefined,
  };
}

function normalizeLinks(values: unknown[]): IndiaLink[] {
  return values
    .map(normalizeLink)
    .filter((value): value is IndiaLink => value !== null);
}

function emptyDependencies(): IndiaDependencyGroups {
  return {
    systems: [],
    materials: [],
    processes: [],
    equipment: [],
    capabilities: [],
  };
}

function normalizeDependencies(source: JsonObject | null): IndiaDependencyGroups {
  const dependencies =
    readObject(source, ["dependencies", "dependency_groups", "dependencyGroups"]) ??
    source;
  const output = emptyDependencies();
  let foundGroup = false;

  for (const key of DEPENDENCY_KEYS) {
    const values = readArray(dependencies, [
      key,
      `${key}_dependencies`,
      `${key}Dependencies`,
    ]);
    if (values.length) foundGroup = true;
    output[key] = normalizeLinks(values);
  }

  if (!foundGroup) {
    const generic = readArray(source, ["dependencies", "requires", "inputs"]);
    output.systems = normalizeLinks(generic);
  }
  return output;
}

function normalizeLadder(values: unknown[]): IndiaMakingStep[] {
  return values.flatMap((value, index) => {
    if (typeof value === "string" && value.trim()) {
      return [{ step: `Step ${index + 1}`, action: value.trim() }];
    }
    const source = asObject(value);
    if (!source) return [];
    const action = readString(
      source,
      ["action", "description", "name", "label", "text"],
      `Define making step ${index + 1}`,
    );
    return [
      {
        step: readString(source, ["step", "stage", "id"], `Step ${index + 1}`),
        action,
        note: readString(source, ["note", "purpose", "basis", "explanation", "condition"]) || undefined,
      },
    ];
  });
}

export function normalizeRecord(value: unknown, index = 0): IndiaRecord {
  const source = asObject(value) ?? {};
  const id = readString(
    source,
    ["id", "record_id", "canonical_id", "slug"],
    `india-record-${index + 1}`,
  );
  const canonicalName = readString(
    source,
    ["canonical_name", "canonicalName"],
  );
  const displayName = readString(
    source,
    ["display_name", "displayName", "family_label", "familyLabel", "name", "title", "label"],
    canonicalName || id,
  );
  const ladder = normalizeLadder(
    readArray(source, ["making_ladder", "makingLadder", "ladder", "making_steps"]),
  );
  return {
    id,
    canonicalName: canonicalName || displayName,
    displayName,
    aliases: readStringArray(source, ["aliases", "alias"]),
    kind: readString(source, ["kind", "type"], "capability"),
    category: readString(source, ["category", "sector", "family"], "Uncategorised"),
    explanation: readString(
      source,
      ["explanation", "description", "what_it_is", "summary"],
      "No plain language explanation is recorded yet.",
    ),
    use: readString(
      source,
      ["use", "uses", "application", "applications", "why_it_matters"],
      "Use is not recorded yet.",
    ),
    indiaStatus: readString(
      source,
      ["india_status", "indiaStatus", "status", "availability"],
      "UNKNOWN",
    ),
    statusEpistemicClass: readString(
      source,
      [
        "status_epistemic_class",
        "statusEpistemicClass",
        "status_epistemic",
        "epistemic_class",
        "epistemicClass",
        "epistemic",
      ],
      "UNKNOWN",
    ),
    statusBasis: readString(
      source,
      ["status_basis", "statusBasis", "basis", "evidence_basis"],
      "Basis is not recorded yet.",
    ),
    sourceSpec: readString(source, ["source_spec", "sourceSpec", "source", "provenance"]) || null,
    isReferenceOnly: Boolean(readValue(source, ["is_reference_only", "isReferenceOnly", "reference_only"])),
    domainId: readString(source, ["domain_id", "domainId"]) || null,
    domainName: readString(source, ["domain_name", "domainName", "domain"]) || null,
    dependencies: normalizeDependencies(source),
    gaps: readStringArray(source, ["gaps", "gap_notes", "capability_gaps"]),
    importNotes: readStringArray(source, ["import_notes", "importNotes", "imports", "import_dependencies"]),
    makingLadder: ladder,
    upstream: normalizeLinks(readArray(source, ["upstream", "upstream_links", "upstream_records"])),
    downstream: normalizeLinks(readArray(source, ["downstream", "downstream_links", "downstream_records"])),
    unlocks: normalizeLinks(readArray(source, ["unlocks", "unlocked_by", "option_value"])),
    related: normalizeLinks(readArray(source, ["related", "related_records", "see_also"])),
  };
}

function normalizeStatus(value: unknown): IndiaStatus | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export function normalizeDomain(value: unknown, index = 0): IndiaDomain {
  const source = asObject(value) ?? {};
  const id = readString(source, ["id", "domain_id", "slug"], `domain-${index + 1}`);
  return {
    id,
    name: readString(source, ["name", "title", "label", "canonical_name"], id),
    description: readString(source, ["description", "summary", "explanation"]),
    recordCount: readNumber(source, ["record_count", "recordCount", "count", "records"]),
    status: normalizeStatus(readValue(source, ["status", "india_status"])),
  };
}

export function normalizeSummary(value: unknown): IndiaSummary {
  const raw = asObject(value) ?? {};
  const source = readObject(raw, ["summary", "data"]) ?? raw;
  const counts = asObject(readValue(source, [
    "direct_status_counts",
    "directStatusCounts",
    "status_counts",
    "statusCounts",
    "statuses",
  ]));
  const statusCounts: Record<string, number> = {};
  for (const [key, count] of Object.entries(counts ?? {})) {
    if (typeof count === "number" && Number.isFinite(count)) statusCounts[key] = count;
  }
  const readCounts = (keys: string[]): Record<string, number> => {
    const object = asObject(readValue(source, keys));
    const output: Record<string, number> = {};
    for (const [key, count] of Object.entries(object ?? {})) {
      if (typeof count === "number" && Number.isFinite(count)) output[key] = count;
    }
    return output;
  };
  return {
    recordCount: readNumber(source, ["record_count", "recordCount", "records", "count"]),
    directRecordCount: readNumber(source, ["direct_record_count", "directRecordCount", "owned_record_count", "ownedRecordCount"]),
    referenceRecordCount: readNumber(source, ["reference_record_count", "referenceRecordCount", "shared_source_record_count", "sharedSourceRecordCount"]),
    domainCount: readNumber(source, ["domain_count", "domainCount", "domains"]),
    snapshot: readString(source, ["snapshot", "snapshot_id", "snapshotId", "version"]) || null,
    statusCounts,
    directStatusCounts: readCounts(["direct_status_counts", "directStatusCounts", "owned_status_counts", "ownedStatusCounts"]),
    statusEpistemicCounts: readCounts(["status_epistemic_counts", "statusEpistemicCounts", "epistemic_counts", "epistemicCounts"]),
  };
}

function unwrapArray(value: unknown, keys = RESULT_KEYS): unknown[] {
  if (Array.isArray(value)) return value;
  const source = asObject(value);
  if (!source) return [];
  for (const key of keys) {
    if (Array.isArray(source[key])) return source[key] as unknown[];
  }
  const nested = asObject(source.data);
  if (nested) return unwrapArray(nested, keys);
  return [];
}

function unwrapRecord(value: unknown): unknown {
  const source = asObject(value);
  if (!source) return value;
  if (source.record ?? source.item ?? source.result) return source.record ?? source.item ?? source.result;
  return asObject(source.data) ? unwrapRecord(source.data) : value;
}

function endpointError(label: string, response: Response): Error {
  return new Error(`${label} is unavailable (${response.status})`);
}

async function fetchJson<T>(path: string, label: string, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15_000);
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  try {
    const response = await fetch(path, { signal: controller.signal });
    if (!response.ok) throw endpointError(label, response);
    return (await response.json()) as T;
  } catch (error) {
    if (signal?.aborted) throw error;
    if (controller.signal.aborted) throw new Error(`${label} timed out. Please try again.`);
    throw error;
  } finally {
    window.clearTimeout(timeout);
    signal?.removeEventListener("abort", abort);
  }
}

export async function fetchIndiaSummary(signal?: AbortSignal): Promise<IndiaSummary> {
  return normalizeSummary(await fetchJson("/api/india/summary", "India summary", signal));
}

export async function fetchIndiaDomains(signal?: AbortSignal): Promise<IndiaDomain[]> {
  const payload = await fetchJson<unknown>("/api/india/domains", "India domains", signal);
  return unwrapArray(payload, ["domains", ...RESULT_KEYS]).map(normalizeDomain);
}

export async function fetchIndiaDiscover(signal?: AbortSignal): Promise<IndiaDiscoverResult[]> {
  const payload = await fetchJson<unknown>("/api/india/discover", "India discovery", signal);
  return unwrapArray(payload, ["discoveries", "recommendations", ...RESULT_KEYS]).flatMap(
    (value, index) => {
      const source = asObject(value);
      const rawRecord = source?.record ?? source?.item ?? value;
      const record = normalizeRecord(rawRecord, index);
      return [
        {
          record,
          reason: readString(source, ["reason", "rationale", "why", "explanation", "basis"]),
          rank: readNumber(source, ["rank", "score", "priority"]),
        },
      ];
    },
  );
}

export async function fetchIndiaBootstrap(signal?: AbortSignal): Promise<IndiaBootstrap> {
  const [summary, domains, discover] = await Promise.all([
    fetchIndiaSummary(signal),
    fetchIndiaDomains(signal),
    fetchIndiaDiscover(signal),
  ]);
  return { summary, domains, discover };
}

export async function searchIndia(
  query: string,
  signal?: AbortSignal,
  options: {
    domain?: string | null;
    kind?: string | null;
    status?: string | null;
    limit?: number;
  } = {},
): Promise<IndiaSearchResult[]> {
  const params = new URLSearchParams({ q: query.trim() });
  if (options.domain) params.set("domain", options.domain);
  if (options.kind) params.set("kind", options.kind);
  if (options.status) params.set("status", options.status);
  if (options.limit) params.set("limit", String(options.limit));
  const path = `/api/india/search?${params.toString()}`;
  const payload = await fetchJson<unknown>(path, "India search", signal);
  return unwrapArray(payload).flatMap((value, index) => {
    const source = asObject(value);
    const record = normalizeRecord(source?.record ?? source?.item ?? value, index);
    const queryValue = query.trim().toLowerCase();
    const displayName = record.displayName.toLowerCase();
    const canonical = record.canonicalName.toLowerCase();
    const aliases = record.aliases.map((alias) => alias.toLowerCase());
    const matchedOn = readStringArray(source, ["matched_on", "matchedOn", "fields"]);
    const matchType = readString(source, ["match_type", "matchType", "match", "result_type"])
      || (queryValue && displayName === queryValue ? "exact name"
        : queryValue && displayName.includes(queryValue) ? "name"
          : queryValue && canonical.includes(queryValue) ? "canonical name"
          : queryValue && aliases.some((alias) => alias.includes(queryValue)) ? "alias"
            : queryValue && [record.category, record.domainName, record.kind].some((field) => field?.toLowerCase().includes(queryValue)) ? "family"
              : "related")
      || null;
    return [
      {
        record,
        score: readNumber(source, ["score", "rank", "relevance"]),
        matchedOn: matchedOn.length ? matchedOn : matchType ? [matchType] : [],
        matchType,
      },
    ];
  });
}

export async function fetchIndiaRecord(
  id: string,
  signal?: AbortSignal,
): Promise<IndiaRecord> {
  const payload = await fetchJson<unknown>(
    `/api/india/records/${encodeURIComponent(id)}`,
    "India record",
    signal,
  );
  return normalizeRecord(unwrapRecord(payload));
}
