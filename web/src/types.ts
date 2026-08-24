export type ResultClass =
  | "FEASIBLE"
  | "CONDITIONALLY_FEASIBLE"
  | "INFEASIBLE_UNDER_MODEL"
  | "NOT_ADJUDICABLE";

export type ProductMode =
  | "ANALYZE"
  | "DESIGN"
  | "EXECUTE"
  | "DISCOVER"
  | "LEARN";

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
  variants: {
    id: string;
    name: string;
    notes: string;
    anchor_evidence: string[];
  }[];
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
  includeDeep: boolean;
}

export interface Selection {
  kind: "item" | "proof" | "action" | "evidence" | "world" | "capability";
  id: string;
}

/**
 * Canonical registry records are deliberately small at the shell boundary.
 * The registry can add richer fields in metadata without forcing the workbench
 * to invent a domain-specific schema.
 */
export interface WorldNode {
  id: string;
  name: string;
  kind: string;
  pack_id?: string | null;
  canonical_id?: string | null;
  epistemic_class: string;
  evidence_ids: string[];
  metadata: Record<string, unknown>;
}

export interface WorldEdge {
  src: string;
  relation: string;
  dst: string;
  meta: Record<string, unknown>;
}

export interface WorldSlice {
  nodes: WorldNode[];
  edges: WorldEdge[];
  root: string | null;
  truncated: boolean;
}

export interface WorldSummary {
  nodes: number;
  edges: number;
  capabilities: number;
  packs: number;
  snapshot_id?: string | null;
  hash?: string | null;
  epistemic_counts?: Record<string, number>;
  unavailable?: boolean;
}

export interface CapabilityRecord extends WorldNode {
  mapping_count: number;
  mapped_pack_ids: string[];
  mapped_entity_ids: string[];
  evidence_task_ids: string[];
}

export interface WorldEvidenceRecord {
  evidence_id: string;
  local_claim_id: string;
  pack_id: string | null;
  subject: string;
  predicate: string;
  epistemic_class: string;
  value_text: string;
  quote_or_caveat: string;
  source_ids: string[];
  confidence: Record<string, number | null>;
  source_snapshots: {
    snapshot_id: string;
    source_id: string;
    content_hash: string;
    hash_scope: string;
    raw_payload_stored: boolean;
    access_date: string;
    license: string;
    storage_posture: string;
    url: string;
    metadata: Record<string, unknown>;
  }[];
}

export interface PackDetail {
  pack_id: string;
  title: string;
  id_scope: "pack_local_with_registry_ids";
  variants: {
    id: string;
    name: string;
    notes: string;
    anchor_evidence: string[];
    functional_requirements?: unknown[];
    bom?: { part: string; qty: number }[];
  }[];
  shocks: { id: string; name: string; description: string }[];
  substitutions: {
    id: string;
    name: string;
    replaces_part: string;
    maturity: string;
  }[];
  projects: {
    id: string;
    name: string;
    item_id: string;
    state: string;
    state_date: string;
    design_capacity: string | null;
    commission_window_years: number[];
    notes: string;
    evidence_ids: string[];
    registry_evidence_ids: string[];
    epistemic_class: string;
    epistemic_role: string | null;
    control_role: "context" | "scenario" | "fundable";
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
    registry_evidence_id: string;
  }[];
  sources: {
    id: string;
    name: string;
    publisher: string;
    url: string;
    license: string;
    access_date: string;
    registry_source_id: string;
  }[];
  scenario_presets: ScenarioPreset[];
  research_tasks: ResearchTask[];
  execution_model: Record<string, unknown>;
  program_model: Record<string, unknown>;
  reverse_buildability_scenarios: Record<string, unknown>[];
  supplier_links: Record<string, unknown>[];
  facilities: {
    id: string;
    name: string;
    country: string;
    geo_id: string;
    lat: number | null;
    lon: number | null;
    owner_org: string;
    operator_org: string;
    status: string;
    notes: string;
    evidence_ids: string[];
  }[];
  organizations: {
    id: string;
    name: string;
    org_type: string;
    countries: string[];
    notes: string;
    evidence_ids: string[];
  }[];
}

export interface ScenarioPreset {
  id: string;
  name: string;
  objective?: string;
  geography?: string;
  variant_id?: string;
  annual_units?: number;
  target_year?: number;
  min_dva?: number;
  shock_ids?: string[];
  substitution_ids?: string[];
  epistemic_class?: string;
  notes?: string;
}

export interface ResearchTask {
  id: string;
  title: string;
  target_entity_id: string;
  target_name?: string;
  missing_variable: string;
  question: string;
  decision: string;
  decision_sensitivity?: number | null;
  priority: string;
  source_plan: string[];
  capture_fields: string[];
  workflow: string[];
  epistemic_class: string;
  persistent_world_mutation: boolean;
}

export interface CaseBrief {
  target: {
    pack_id: string;
    variant_id: string;
    annual_units: number;
    geography: string;
    deadline_year: number;
    minimum_dva: number;
  };
  conclusion: string;
  result_class: ResultClass;
  top_bottlenecks: {
    item_id?: string;
    name?: string;
    summary?: string;
    epistemic_class?: string;
    [key: string]: unknown;
  }[];
  important_unknowns: ResearchTask[];
  architecture_alternatives: {
    id: string;
    name: string;
    replaces_part?: string;
    maturity?: string;
    reasons?: string[];
    performance_delta?: Record<string, unknown>;
    epistemic_class?: string;
  }[];
  critical_dependencies: {
    item_id: string;
    name: string;
    gross_annual: number;
    unit: string;
    depth: number;
    recipe_id: string;
    epistemic_class: string;
  }[];
  conditions: string[];
  required_relaxations: string[];
  explore_actions: string[];
}

export interface MakeBuyRow {
  item_id: string;
  name: string;
  specification: string;
  demand_annual: number;
  unit: string;
  posture: string;
  reason: string;
  capacity_envelope: {
    lo: number | null;
    hi: number | null;
    unknown: boolean;
    epistemic: string;
    unknown_reasons: string[];
  };
  candidate_supplier_countries: string[];
  linked_supplier_candidates: string[];
  capability_claim_candidates: Record<string, unknown>[];
  supplier_status: string;
  epistemic_class: string;
  evidence_ids: string[];
  human_approval_required: boolean;
}

export interface ProcessRouteRow {
  item_id: string;
  recipe_id: string;
  route_name: string;
  route_type: string;
  maturity: string;
  steps: {
    id: string;
    name: string;
    equipment_ids: string[];
    resource_ids: string[];
    cycle_time: string | null;
    yield_fraction: number | null;
    environment: string;
    labor_skills: string[];
  }[];
  required_qualification_ids: string[];
  evidence_ids: string[];
  epistemic_class: string;
}

export interface QualificationTask {
  qualification_id: string;
  item_id: string;
  name: string;
  qualifier: string;
  standard_ref: string;
  status: string;
  latency_months: number[];
  evidence_ids: string[];
  epistemic_class: string;
  human_approval_required: boolean;
}

export interface WorkPackage {
  id: string;
  name: string;
  phase: string;
  entity_ids?: string[];
  depends_on: string[];
  acceptance_criteria: string[];
  epistemic_class: string;
  evidence_ids?: string[];
  human_approval_required: boolean;
}

export interface ExecutionPlan {
  objective: Record<string, string | number>;
  make_buy: MakeBuyRow[];
  process_routes: ProcessRouteRow[];
  machinery_requirements: {
    equipment_id: string;
    name: string;
    domestically_producible: boolean | null;
    dominant_supplier_countries: string[];
    epistemic_class: string;
    supports_items: string[];
  }[];
  qualification_tasks: QualificationTask[];
  work_packages: WorkPackage[];
  critical_path_candidates: QualificationTask[];
  next_actions: {
    action: string;
    task_id?: string;
    qualification_id?: string;
    title: string;
    why_now: string;
    epistemic_class: string;
    human_approval_required: boolean;
  }[];
  approval_boundary: string;
}

export interface ReverseBuildability {
  status?: string;
  max_units_per_year: number | null;
  epistemic_class: string;
  binding_constraints?: string[];
  blocking_unknowns?: string[];
  interventions: (string | Record<string, unknown>)[];
  algorithm?: string;
  proof_status?: string;
  declared_scenarios?: DeclaredReverseScenario[];
  [key: string]: unknown;
}

export interface ReverseBindingShortfall {
  rank: number;
  item_id: string;
  first_binding_year: number;
  peak_shortfall: number;
  unit: string;
  demand_at_peak: number;
  domestic_used_at_peak: number;
  imports_used_at_peak: number;
  service_deficit_share: number;
  epistemic_class: string;
  action: string;
}

export interface DeclaredReverseScenario {
  scenario_id: string;
  title: string;
  description: string;
  status: string;
  epistemic_class: "SCENARIO" | string;
  max_units_per_year: number | null;
  search_upper_bound?: number;
  ceiling_range_units_per_year: [number | null, number | null];
  binding_constraints?: string[];
  ranked_interventions?: ReverseBindingShortfall[];
  proof_status?: string;
  assumption_boundary: {
    persistent: boolean;
    baseline_world_mutated: boolean;
    capacity_policy: string;
    basis_units_per_year: number;
    headroom_multiplier: number;
    import_policy: string;
    explicit_assumption_count: number;
    policy_generated_assumption_count: number;
    assumptions: {
      item_id: string;
      range: [number, number];
      unit: string;
      basis: string;
      rationale: string;
      epistemic_class: string;
    }[];
    notes: string[];
  };
}

export interface ShockImpact {
  shock_ids: string[];
  baseline: Record<string, unknown>;
  shocked: Record<string, unknown>;
  deadline_shortfall_vectors: {
    baseline: Record<string, number>;
    shocked: Record<string, number>;
  };
  deadline_shortfall_delta_by_unit: Record<string, number>;
  deadline_normalized_deficit_delta: number;
  deadline_shortfall_delta: number | null;
  deadline_shortfall_delta_unit: "pcs" | null;
  deadline_shortfall_delta_semantics: string;
  directly_affected_entity_ids: string[];
  affected_origins: string[];
  objective_reached_by_causal_path: boolean;
  causal_paths: { entity_id: string; name: string; kind: string }[][];
  applied_edits: Record<string, unknown>[];
  rejected_edits: string[];
  inventory_posture: string;
  epistemic_class: string;
}

export interface ProgramProjection {
  available: boolean;
  projection_type: string;
  objective?: Record<string, unknown>;
  tranches?: Record<string, unknown>[];
  system_gates?: Record<string, unknown>[];
  annual_projection: {
    year: number;
    commissioned_gw_optimistic: number;
    commissioned_gw_conservative: number;
    commissioned_units_optimistic: number;
    commissioned_units_conservative: number;
    epistemic_class: string;
  }[];
  projects?: Record<string, unknown>[];
  target_gap_gw_optimistic?: number | null;
  target_gap_gw_conservative?: number | null;
  epistemic_class?: string;
  limitations: string[];
}

export interface CapabilityLeverageRow {
  capability_id: string;
  name: string;
  mapped_pack_ids: string[];
  mapped_entity_count: number;
  downstream_objective_ids: string[];
  downstream_unlock_count: number;
  reverse_dependency_reach: number;
  cross_sector_reuse: number;
  evidence_gap_fraction: number;
  closure_readiness_proxy: number;
  open_research_task_count: number;
  leverage_proxy: number;
  epistemic_class: string;
}

export interface DiscoverResponse {
  metric: string;
  formula: string;
  not_claimed: string[];
  registry_snapshot_id: string;
  capabilities: CapabilityLeverageRow[];
}

export interface DesignComparison {
  substitution_id: string;
  name?: string;
  accepted: boolean;
  reasons?: string[];
  functional_envelope?: Record<string, unknown>;
  requirements_change?: Record<string, unknown>;
  transition_months?: number[];
  maturity?: string;
  graph_delta?: {
    added_dependencies: string[];
    removed_dependencies: string[];
    changed_demand: {
      item_id: string;
      name: string;
      baseline_gross_annual: number;
      alternative_gross_annual: number;
      delta: number;
      unit: string;
      change: string;
    }[];
  };
  baseline?: Record<string, unknown>;
  alternative?: Record<string, unknown>;
  binding_change?: { unknowns_added: string[]; unknowns_removed: string[] };
  evidence_ids?: string[];
  epistemic_class: string;
  approval_boundary?: string;
}

export interface ResearchResolution {
  source_snapshot: Record<string, unknown>;
  observation: Record<string, unknown>;
  evidence_record?: Record<string, unknown>;
  promotion: Record<string, unknown>;
  reconciliation: Record<string, unknown>;
  scenario_overlay: Record<string, unknown> | null;
  rerun: Record<string, unknown> | null;
  persistent_world_update: { status: string; [key: string]: unknown };
}

export interface OperationalCaseResponse {
  brief: CaseBrief;
  analysis: SolveResponse;
  research: { tasks: ResearchTask[]; count: number };
  execution: ExecutionPlan;
  reverse_buildability: ReverseBuildability;
  shock_impact: ShockImpact | null;
  program: ProgramProjection;
  discover: DiscoverResponse;
  registry_snapshot_id: string;
}
