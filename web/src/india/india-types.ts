export type IndiaStatus = string;

export interface IndiaLink {
  id: string | null;
  label: string;
  kind?: string;
  note?: string;
}

export interface IndiaDependencyGroups {
  systems: IndiaLink[];
  materials: IndiaLink[];
  processes: IndiaLink[];
  equipment: IndiaLink[];
  capabilities: IndiaLink[];
}

export interface IndiaMakingStep {
  step: string;
  action: string;
  note?: string;
}

export interface IndiaRecord {
  id: string;
  canonicalName: string;
  aliases: string[];
  kind: string;
  category: string;
  explanation: string;
  use: string;
  indiaStatus: IndiaStatus;
  statusBasis: string;
  domainId: string | null;
  domainName: string | null;
  dependencies: IndiaDependencyGroups;
  gaps: string[];
  importNotes: string[];
  makingLadder: IndiaMakingStep[];
  upstream: IndiaLink[];
  downstream: IndiaLink[];
  unlocks: IndiaLink[];
  related: IndiaLink[];
}

export interface IndiaDomain {
  id: string;
  name: string;
  description: string;
  recordCount: number | null;
  status: IndiaStatus | null;
}

export interface IndiaSummary {
  recordCount: number | null;
  domainCount: number | null;
  snapshot: string | null;
  statusCounts: Record<string, number>;
}

export interface IndiaSearchResult {
  record: IndiaRecord;
  score: number | null;
  matchedOn: string[];
}

export interface IndiaDiscoverResult {
  record: IndiaRecord;
  reason: string;
  rank: number | null;
}

export interface IndiaBootstrap {
  summary: IndiaSummary | null;
  domains: IndiaDomain[];
  discover: IndiaDiscoverResult[];
}

export type IndiaDependencyGroupKey = keyof IndiaDependencyGroups;
