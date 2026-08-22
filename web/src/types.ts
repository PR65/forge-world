export type ResultClass =
  | "FEASIBLE"
  | "CONDITIONALLY_FEASIBLE"
  | "INFEASIBLE_UNDER_MODEL"
  | "NOT_ADJUDICABLE";

export interface ItemGap {
  item: string;
  demand: number;
  domestic_used: number;
  imports_used: number;
  shortfall: number;
  unknown: boolean;
}

export interface YearResult {
  total_shortfall: number;
  shortfalls: ItemGap[];
  import_value_usd: number;
  domestic_value_usd: number;
}

export interface SolveResultJ {
  result_class: ResultClass;
  blocking_unknowns: string[];
  conditional_reasons: string[];
  binding_summary: string[];
  required_relaxations: string[];
  closure_candidates: string[];
  max_shortfall_item: string;
  max_shortfall_year: number;
  years: Record<string, YearResult>;
}

export interface EnvelopeYear {
  lo: number | null;
  hi: number | null;
  unknown: boolean;
  projects_only: boolean;
  epistemic?: string;
  reasons: string[];
}

export interface EnvelopeRow {
  item: string;
  kind: string;
  demand_annual: number;
  gross_demand_annual: number;
  unit: string;
  suppliers: string[];
  concentration_hhi: number | null;
  epistemic: string;
  by_year: Record<string, EnvelopeYear>;
  proof?: string;
}

export interface ExplosionItem {
  item: string;
  net: number;
  gross: number;
  unit: string;
  depth: number;
  recipe: string;
}

export interface PlanAction {
  action_id: string;
  kind: string;
  label: string;
  capex_usd: number;
  lead_time_years: number[];
  rationale: string;
}

export interface PlanTimelineRow {
  action: string;
  kind: string;
  start_year: number;
  online_earliest: number;
  online_latest: number;
  capex_musd: number;
}

export interface PlanJ {
  actions: PlanAction[];
  total_capex_usd: number;
  verified_result_class: string;
  remaining_shortfall: number;
  timeline: PlanTimelineRow[];
  notes: string[];
}

export interface VoiTask {
  unknown_id: string;
  description: string;
  decision_impact: "HIGH" | "MEDIUM" | "LOW";
  flip_behavior: string;
  next_evidence: string[];
}

export interface FrontierPoint {
  dva_target: number;
  feasible: boolean;
  result_class: string;
  min_capex_musd: number | null;
  earliest_full_year: number | null;
  binding: string[];
}

export interface ProofNode {
  node_id: string;
  kind: string;
  label: string;
  detail: Record<string, unknown>;
  sources: string[];
}

export interface ProofEdge {
  from_id: string;
  to_id: string;
  relation: string;
}

export interface ProofGraphJ {
  nodes: ProofNode[];
  edges: ProofEdge[];
}

export interface RunInfo {
  run_id: string;
  pack_id: string;
  pack_version: string;
  created_at: string;
  input_hash: string;
  solver_version: string;
  assumptions: string[];
}

export interface PackSummary {
  pack_id: string;
  title: string;
  version: string;
  geography_focus: string;
  sources: number;
  evidence: number;
  entities: number;
  edges: number;
  entity_kinds: Record<string, number>;
  variants: string[];
}

export interface SolveResponse {
  run: RunInfo;
  pack: PackSummary;
  variants: { id: string; name: string; notes: string; anchor_evidence: string[] }[];
  selected_variant: string;
  annual_units: number;
  years: number[];
  explosion: { items: ExplosionItem[]; mass_balance_warnings: string[] };
  capacity_envelopes: EnvelopeRow[];
  result: SolveResultJ;
  dva: {
    fraction: number;
    total_cost_usd: number;
    imported_cost_usd: number;
    assumptions: string[];
  };
  actions: PlanAction[];
  plan: PlanJ;
  voi: VoiTask[];
  shock_report: { applied: unknown[]; rejected: string[] };
  frontier: FrontierPoint[];
  reverse: {
    max_units_per_year: number;
    class_at_max: string;
    max_units_localized_at_dva: number;
    class_localized: string;
    dva_reference: number;
  } | null;
  proof_graph: ProofGraphJ;
  crosswalks: {
    from_class: string;
    from_code: string;
    to_entity: string;
    confidence: number;
    note: string;
  }[];
}

export interface ObjectiveConfig {
  packId: string;
  variantId: string;
  annualUnits: number;
  geography: string;
  deadlineYear: number;
  minDva: number;
  budgetUsd: number | null;
  fundedProjects: string[];
  shocks: string[];
  assumptions: Record<string, [number, number]>;
}

export interface Selection {
  kind: "item" | "proof" | "action" | "evidence";
  id: string;
}

export interface PackDetail {
  pack_id: string;
  title: string;
  variants: {
    id: string;
    name: string;
    notes: string;
    anchor_evidence: string[];
    functional_requirements?: unknown[];
    bom?: { part: string; qty: number }[];
  }[];
  shocks: { id: string; name: string; description: string }[];
  substitutions: { id: string; name: string; replaces_part: string; maturity: string }[];
  projects: {
    id: string;
    name: string;
    item_id: string;
    state: string;
    state_date: string;
    design_capacity: string | null;
    commission_window_years: number[];
  }[];
  evidence: {
    claim_id: string;
    subject: string;
    predicate: string;
    epistemic_class: string;
    value_text: string;
    source_ids: string[];
    quote_or_caveat: string;
    confidence: Record<string, number | null>;
  }[];
  sources: {
    id: string;
    name: string;
    publisher: string;
    url: string;
    license: string;
    access_date: string;
  }[];
}
