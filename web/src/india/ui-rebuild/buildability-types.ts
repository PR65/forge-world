/**
 * Public, human-facing data contracts for the FORGE India dashboard.
 *
 * These types intentionally contain presentation language rather than raw
 * IndiaRecord / graph primitives.  The composition layer owns the mapping
 * from the engine into this contract; the dashboard only renders this layer.
 */

export type BuildabilityStatus =
  | "available"
  | "partial"
  | "import-dependent"
  | "scale-limited"
  | "missing"
  | "unknown"
  | "conflicted"
  | (string & {});

export type BuildabilityMetricInput = BuildabilityMetric | number | string | null | undefined;

export interface BuildabilityMetric {
  /** A defensible numeric value from the composition layer, if one exists. */
  value?: number | null;
  /** Prefer this for values with a non-standard unit or declared precision. */
  display?: string | null;
  unit?: "percent" | "score" | "count" | "text";
  description?: string | null;
  epistemicClass?: string | null;
}

export interface BuildabilitySummary {
  available?: BuildabilityMetricInput;
  partialOrImportDependent?: BuildabilityMetricInput;
  missing?: BuildabilityMetricInput;
  unknown?: BuildabilityMetricInput;
  overallIndex?: BuildabilityMetricInput;
  assessedLabel?: string | null;
  evaluatedNodeCount?: number | null;
  rootStatus?: BuildabilityStatus | null;
  rootStatusLabel?: string | null;
  rootEpistemicClass?: string | null;
  overallIndexBasis?: string | null;
}

export interface BuildabilityItem {
  /** Used only for callback routing; never displayed by the dashboard. */
  id?: string | null;
  /** Human-facing title supplied by the composition layer. */
  title: string;
  subtitle?: string | null;
  summary?: string | null;
  note?: string | null;
  kind?: string | null;
  category?: string | null;
  status?: BuildabilityStatus | null;
  statusLabel?: string | null;
  statusMix?: Partial<Record<BuildabilityStatus, number>> | null;
  epistemicClass?: string | null;
  dataState?: string | null;
}

export interface BuildabilityNode extends BuildabilityItem {
  children?: BuildabilityNode[];
  requirementGroups?: BuildabilityRequirementGroup[];
}

export interface BuildabilityRequirementGroup extends BuildabilityItem {
  items?: BuildabilityItem[];
  count?: number | null;
  icon?: string | null;
}

export interface BuildabilityBottleneck extends BuildabilityItem {
  rank?: number | null;
  impactLabel?: string | null;
  reason?: string | null;
}

export interface BuildabilityPathStep extends BuildabilityItem {
  order?: number | null;
  timeLabel?: string | null;
  action?: string | null;
  required?: boolean | null;
  allowedActions?: string[];
}

export interface BuildabilityFacility extends BuildabilityItem {
  location?: string | null;
  strengthAreas?: string[];
  relevanceLabel?: string | null;
}

export interface BuildabilityMapPoint {
  /** Callback-only identity; never rendered. */
  id?: string | null;
  label: string;
  location?: string | null;
  /** Normalized coordinates (0–100) supplied by a geospatial adapter. */
  x?: number | null;
  y?: number | null;
  status?: BuildabilityStatus | null;
  note?: string | null;
}

export interface BuildabilityEvidence {
  /** Callback-only identity; never rendered. */
  id?: string | null;
  title: string;
  source?: string | null;
  type?: string | null;
  epistemicClass?: string | null;
  confidenceLabel?: string | null;
  updatedLabel?: string | null;
  summary?: string | null;
}

export interface BuildabilityDomain {
  id: string;
  name: string;
  shortName?: string | null;
  description?: string | null;
  recordCount?: number | null;
  status?: BuildabilityStatus | null;
}

export interface BuildabilitySidebarSummary {
  index?: BuildabilityMetricInput;
  deltaLabel?: string | null;
  note?: string | null;
  updatedLabel?: string | null;
  sparkline?: number[] | null;
}

export interface BuildabilityViewModel {
  title: string;
  domain?: string | null;
  kind?: string | null;
  category?: string | null;
  complexity?: string | null;
  plainSummary?: string | null;
  buildability: BuildabilitySummary;
  majorSystems?: BuildabilityNode[];
  requirements?: BuildabilityRequirementGroup[];
  criticalBottlenecks?: BuildabilityBottleneck[];
  localizationPath?: BuildabilityPathStep[];
  components?: BuildabilityItem[];
  processes?: BuildabilityItem[];
  equipment?: BuildabilityItem[];
  tooling?: BuildabilityItem[];
  materials?: BuildabilityItem[];
  metrology?: BuildabilityItem[];
  qualification?: BuildabilityItem[];
  capabilities?: BuildabilityItem[];
  upstream?: BuildabilityItem[];
  downstream?: BuildabilityItem[];
  unlocks?: BuildabilityItem[];
  related?: BuildabilityItem[];
  evidenceSummary?: BuildabilityEvidence[];
  facilities?: BuildabilityFacility[];
  mapPoints?: BuildabilityMapPoint[];
  imports?: BuildabilityItem[];
  indiaIndex?: BuildabilitySidebarSummary | null;
  optionalPanels?: Record<string, unknown> | null;
}

export type BuildabilityMode = "Analyze" | "Design" | "Execute" | "Discover" | "Learn";

export type BuildabilityTabId =
  | "systems"
  | "components"
  | "processes"
  | "equipment"
  | "materials"
  | "facilities"
  | "capacity"
  | "evidence"
  | "imports"
  | "research-tasks";

export type BuildabilityUtilityAction = "notifications" | "help" | "profile";

export interface BuildabilityDashboardProps {
  viewModel: BuildabilityViewModel | null;
  domains?: BuildabilityDomain[];
  activeDomainId?: string | null;
  query?: string;
  loading?: boolean;
  error?: string | null;
  activeTab?: BuildabilityTabId;
  activeMode?: BuildabilityMode;
  onQueryChange?: (query: string) => void;
  onAnalyze?: (query: string) => void;
  onDomainSelect?: (domain: BuildabilityDomain) => void;
  onModeChange?: (mode: BuildabilityMode) => void;
  onTabSelect?: (tab: BuildabilityTabId) => void;
  onSystemSelect?: (system: BuildabilityNode) => void;
  onItemSelect?: (item: BuildabilityItem) => void;
  onBottleneckSelect?: (bottleneck: BuildabilityBottleneck) => void;
  onPathSelect?: (step: BuildabilityPathStep) => void;
  onMapPointSelect?: (point: BuildabilityMapPoint) => void;
  onEvidenceSelect?: (evidence: BuildabilityEvidence) => void;
  onPanelOpen?: (panel: BuildabilityTabId | "map" | "facilities" | "bottlenecks" | "localization" | "evidence") => void;
  onUtilityAction?: (action: BuildabilityUtilityAction) => void;
  onRetry?: () => void;
  className?: string;
}
