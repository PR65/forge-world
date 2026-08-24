import { useId, useMemo, useState } from "react";
import type { CSSProperties, KeyboardEvent } from "react";
import "./insight-surfaces.css";

/**
 * The labels intentionally mirror FORGE's canonical epistemic classes. A
 * string escape hatch keeps this boundary usable while the registry evolves.
 */
export type InsightEpistemicClass =
  | "MEASURED"
  | "REPORTED"
  | "DERIVED"
  | "ESTIMATED"
  | "MODELLED"
  | "ASSUMPTION"
  | "SCENARIO"
  | "UNKNOWN"
  | "CONFLICTED"
  | (string & {});

export type ObjectiveBasis = "FLOW" | "STOCK" | "MIXED" | "UNKNOWN";

export interface ScenarioObjective {
  /** Stable objective identity, when the scenario registry provides one. */
  id?: string | null;
  label: string;
  /** Target value. Keep null when the target was not adjudicated. */
  target?: number | null;
  /** A source-provided target string can retain units or qualification text. */
  targetLabel?: string | null;
  unit?: string | null;
  geography?: string | null;
  deadlineYear?: number | null;
  basis?: ObjectiveBasis;
  epistemic?: InsightEpistemicClass;
  note?: string | null;
}

export interface ProgramTranche {
  id: string;
  label: string;
  startYear?: number | null;
  endYear?: number | null;
  /** Annual output / throughput represented by this tranche. */
  annualCapacity?: number | null;
  /** Cumulative installed or delivered stock represented by this tranche. */
  cumulativeCapacity?: number | null;
  /** Aliases accepted at the shell boundary for registry adapters. */
  annual?: number | null;
  cumulative?: number | null;
  status?: string | null;
  epistemic?: InsightEpistemicClass;
  note?: string | null;
}

export interface CapacitySeriesPoint {
  year: number;
  annualCapacity?: number | null;
  cumulativeCapacity?: number | null;
  /** Aliases accepted when the solver emits shorter field names. */
  annual?: number | null;
  cumulative?: number | null;
  epistemic?: InsightEpistemicClass;
}

export interface CapacityScenarioSeries {
  id?: string | null;
  label?: string | null;
  points: readonly CapacitySeriesPoint[];
  epistemic?: InsightEpistemicClass;
  annualUnit?: string | null;
  cumulativeUnit?: string | null;
  note?: string | null;
}

export interface SystemGate {
  id: string;
  label: string;
  gateType?: string | null;
  year?: number | null;
  status?: string | null;
  /** A gate can be open, in progress, closed, blocked, or unresolved. */
  state?: string | null;
  epistemic?: InsightEpistemicClass;
  detail?: string | null;
  dependencies?: readonly string[];
}

/**
 * Program timeline data is deliberately a data contract, not a demo fixture.
 * All arrays may be empty; the component then renders an explicit UNKNOWN
 * state rather than inventing a curve or gate.
 */
export interface ProgramTimeline {
  objective?: ScenarioObjective | null;
  /** Alias accepted when an API calls the field scenarioObjective. */
  scenarioObjective?: ScenarioObjective | null;
  tranches?: readonly ProgramTranche[];
  optimistic?: CapacityScenarioSeries | null;
  conservative?: CapacityScenarioSeries | null;
  /** Legacy/adapter shape: separate annual and cumulative arrays. */
  optimisticAnnual?: readonly CapacitySeriesPoint[];
  optimisticCumulative?: readonly CapacitySeriesPoint[];
  conservativeAnnual?: readonly CapacitySeriesPoint[];
  conservativeCumulative?: readonly CapacitySeriesPoint[];
  gates?: readonly SystemGate[];
  /** Alias useful when a backend names the field after the UI section. */
  systemGates?: readonly SystemGate[];
}

export interface ProgramTimelineProps {
  data?: ProgramTimeline | null;
  timeline?: ProgramTimeline | null;
  /** Direct props are supported so the component can sit at an API boundary. */
  objective?: ScenarioObjective | null;
  scenarioObjective?: ScenarioObjective | null;
  tranches?: readonly ProgramTranche[] | null;
  optimistic?: CapacityScenarioSeries | null;
  conservative?: CapacityScenarioSeries | null;
  gates?: readonly SystemGate[] | null;
  systemGates?: readonly SystemGate[] | null;
  className?: string;
  onSelectTranche?: (tranche: ProgramTranche) => void;
  onSelectGate?: (gate: SystemGate) => void;
}

export type RegistryMetric = number | readonly string[] | null | undefined;
export type EvidenceGapMetric = number | string | null | undefined;

/**
 * A registry-derived structural reach row. The fields are intentionally
 * counts/links and not dollars, returns, or a claim of economic option value.
 */
export interface CapabilityLeverage {
  id: string;
  name: string;
  canonicalId?: string | null;
  canonical_id?: string | null;
  kind?: string | null;
  epistemic?: InsightEpistemicClass;
  epistemicClass?: InsightEpistemicClass;
  epistemic_class?: InsightEpistemicClass;
  /** Structural proxy supplied by the registry/solver; no economic meaning. */
  leverageProxy?: number | null;
  leverage_proxy?: number | null;
  leverageProxyUnit?: string | null;
  leverage_proxy_unit?: string | null;
  crossSectorReuse?: RegistryMetric;
  cross_sector_reuse?: RegistryMetric;
  crossSectorReuseLabels?: readonly string[];
  downstreamUnlock?: RegistryMetric;
  downstream_unlock?: RegistryMetric;
  downstreamUnlockLabels?: readonly string[];
  reverseReach?: RegistryMetric;
  reverse_reach?: RegistryMetric;
  reverseReachLabels?: readonly string[];
  evidenceGap?: EvidenceGapMetric;
  evidence_gap?: EvidenceGapMetric;
  evidenceGapLabel?: string | null;
  taskCount?: number | null;
  task_count?: number | null;
  evidenceTaskCount?: number | null;
  evidenceTaskIds?: readonly string[];
  evidence_task_ids?: readonly string[];
  evidenceIds?: readonly string[];
  evidence_ids?: readonly string[];
  mappingCount?: number | null;
  mapping_count?: number | null;
  mappedPackIds?: readonly string[];
  mapped_pack_ids?: readonly string[];
  mappedEntityIds?: readonly string[];
  mapped_entity_ids?: readonly string[];
  note?: string | null;
  metadata?: Readonly<Record<string, unknown>>;
}

/** Friendly aliases for callers that name the registry result a row/record. */
export type CapabilityLeverageRow = CapabilityLeverage;
export type CapabilityLeverageRecord = CapabilityLeverage;

export interface CapabilityLeverageProps {
  rows?: readonly CapabilityLeverage[] | null;
  records?: readonly CapabilityLeverage[] | null;
  capabilities?: readonly CapabilityLeverage[] | null;
  data?: readonly CapabilityLeverage[] | null;
  selectedCapabilityId?: string | null;
  className?: string;
  /** Called after a row is selected, including keyboard selection. */
  onSelectCapability?: (capability: CapabilityLeverage) => void;
  /** Alias for hosts that use the shorter selection callback name. */
  onSelect?: (capability: CapabilityLeverage) => void;
}

export interface InsightSurfacesProps {
  timeline?: ProgramTimeline | null;
  capabilities?: readonly CapabilityLeverage[] | null;
  onSelectCapability?: (capability: CapabilityLeverage) => void;
  onSelectTranche?: (tranche: ProgramTranche) => void;
  onSelectGate?: (gate: SystemGate) => void;
}

type TimelineMetric = "annualCapacity" | "cumulativeCapacity";
type SeriesKey = "optimistic" | "conservative";

interface NormalizedTimeline {
  objective: ScenarioObjective;
  tranches: readonly ProgramTranche[];
  optimistic: CapacityScenarioSeries;
  conservative: CapacityScenarioSeries;
  gates: readonly SystemGate[];
}

interface ChartSeries {
  key: SeriesKey;
  series: CapacityScenarioSeries;
  className: string;
  label: string;
}

interface ChartGeometry {
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
}

const CHART_GEOMETRY: ChartGeometry = {
  width: 920,
  height: 262,
  left: 58,
  right: 24,
  top: 22,
  bottom: 36,
};

const FLOW_LABEL = "ANNUAL FLOW";
const STOCK_LABEL = "CUMULATIVE STOCK";

function classNames(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function finiteYear(value: number | null | undefined): value is number {
  return finiteNumber(value) && Number.isInteger(value);
}

function formatNumber(value: number | null | undefined, maximumFractionDigits = 1): string {
  if (!finiteNumber(value)) return "UNKNOWN";
  return value.toLocaleString(undefined, { maximumFractionDigits });
}

function formatCapacity(value: number | null | undefined, unit?: string | null): string {
  if (!finiteNumber(value)) return "UNKNOWN";
  const absolute = Math.abs(value);
  let formatted: string;
  if (absolute >= 1_000_000_000) formatted = `${(value / 1_000_000_000).toFixed(1)}B`;
  else if (absolute >= 1_000_000) formatted = `${(value / 1_000_000).toFixed(1)}M`;
  else if (absolute >= 1_000) formatted = `${(value / 1_000).toFixed(1)}k`;
  else formatted = value.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return unit ? `${formatted} ${unit}` : formatted;
}

function normalizedEpistemic(value: InsightEpistemicClass | null | undefined, fallback: InsightEpistemicClass = "UNKNOWN"): string {
  const normalized = typeof value === "string" ? value.trim().toUpperCase() : "";
  return normalized || fallback;
}

function epistemicClass(value: InsightEpistemicClass | null | undefined, fallback = "UNKNOWN"): string {
  return `insight-epistemic-${normalizedEpistemic(value, fallback).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function EpistemicChip({ value, fallback = "UNKNOWN" }: { value?: InsightEpistemicClass | null; fallback?: InsightEpistemicClass }): JSX.Element {
  const label = normalizedEpistemic(value, fallback);
  return <span className={classNames("insight-chip", epistemicClass(value, fallback))} aria-label={`Epistemic class: ${label}`}>{label}</span>;
}

function ScenarioChip(): JSX.Element {
  return <span className="insight-chip insight-chip-scenario" aria-label="Scenario context">SCENARIO</span>;
}

function UnknownLabel({ detail }: { detail?: string }): JSX.Element {
  return <span className="insight-unknown" title={detail}>{detail ? "UNKNOWN" : "UNKNOWN"}</span>;
}

function EmptyState({ title, detail, compact = false }: { title: string; detail: string; compact?: boolean }): JSX.Element {
  return (
    <div className={classNames("insight-empty", compact && "insight-empty-compact")} role="status">
      <span className="insight-chip insight-epistemic-unknown">UNKNOWN</span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

function getAnnual(point: CapacitySeriesPoint | null | undefined): number | null {
  if (!point) return null;
  const value = point.annualCapacity ?? point.annual;
  return finiteNumber(value) ? value : null;
}

function getCumulative(point: CapacitySeriesPoint | null | undefined): number | null {
  if (!point) return null;
  const value = point.cumulativeCapacity ?? point.cumulative;
  return finiteNumber(value) ? value : null;
}

function getTrancheAnnual(tranche: ProgramTranche): number | null {
  const value = tranche.annualCapacity ?? tranche.annual;
  return finiteNumber(value) ? value : null;
}

function getTrancheCumulative(tranche: ProgramTranche): number | null {
  const value = tranche.cumulativeCapacity ?? tranche.cumulative;
  return finiteNumber(value) ? value : null;
}

function seriesHasKnownValue(series: CapacityScenarioSeries): boolean {
  return series.points.some((point) => finiteNumber(getAnnual(point)) || finiteNumber(getCumulative(point)));
}

function normalizeSeries(series: CapacityScenarioSeries | null | undefined, label: string): CapacityScenarioSeries {
  const points = Array.isArray(series?.points) ? series.points : [];
  const fallbackEpistemic: InsightEpistemicClass = seriesHasKnownValue({ points }) ? "MODELLED" : "UNKNOWN";
  return {
    ...(series ?? {}),
    label: series?.label?.trim() || label,
    points,
    epistemic: series?.epistemic ?? fallbackEpistemic,
  };
}

function mergeSeriesParts(
  series: CapacityScenarioSeries | null | undefined,
  annualPoints: readonly CapacitySeriesPoint[] | undefined,
  cumulativePoints: readonly CapacitySeriesPoint[] | undefined,
  label: string,
): CapacityScenarioSeries {
  if (series) return normalizeSeries(series, label);
  const byYear = new Map<number, CapacitySeriesPoint>();
  (annualPoints ?? []).forEach((point) => byYear.set(point.year, { ...byYear.get(point.year), ...point }));
  (cumulativePoints ?? []).forEach((point) => byYear.set(point.year, { ...byYear.get(point.year), ...point }));
  return normalizeSeries({ label, points: [...byYear.values()] }, label);
}

function normalizeTimeline(data: ProgramTimeline | null | undefined): NormalizedTimeline | null {
  if (!data) return null;
  const objective = data.objective ?? data.scenarioObjective;
  if (!objective) return null;
  return {
    objective,
    tranches: Array.isArray(data.tranches) ? data.tranches : [],
    optimistic: mergeSeriesParts(data.optimistic, data.optimisticAnnual, data.optimisticCumulative, "Optimistic"),
    conservative: mergeSeriesParts(data.conservative, data.conservativeAnnual, data.conservativeCumulative, "Conservative"),
    gates: Array.isArray(data.gates) ? data.gates : Array.isArray(data.systemGates) ? data.systemGates : [],
  };
}

function timelineFromProps(props: ProgramTimelineProps): NormalizedTimeline | null {
  const supplied = props.data ?? props.timeline;
  if (supplied) return normalizeTimeline(supplied);
  const objective = props.objective ?? props.scenarioObjective;
  if (!objective) return null;
  return {
    objective,
    tranches: props.tranches ?? [],
    optimistic: normalizeSeries(props.optimistic, "Optimistic"),
    conservative: normalizeSeries(props.conservative, "Conservative"),
    gates: props.gates ?? props.systemGates ?? [],
  };
}

function collectYears(timeline: NormalizedTimeline): number[] {
  const years = [
    ...timeline.optimistic.points.map((point) => point.year),
    ...timeline.conservative.points.map((point) => point.year),
    ...timeline.tranches.flatMap((tranche) => [tranche.startYear, tranche.endYear]),
    ...timeline.gates.map((gate) => gate.year),
    timeline.objective.deadlineYear,
  ].filter(finiteYear);
  return [...new Set(years)].sort((a, b) => a - b);
}

function yearDomain(years: readonly number[]): { min: number; max: number } {
  if (years.length === 0) return { min: 0, max: 1 };
  if (years.length === 1) return { min: years[0] - 1, max: years[0] + 1 };
  return { min: years[0], max: years[years.length - 1] };
}

function xForYear(year: number, domain: { min: number; max: number }, geometry: ChartGeometry): number {
  const width = geometry.width - geometry.left - geometry.right;
  return geometry.left + ((year - domain.min) / Math.max(1, domain.max - domain.min)) * width;
}

function valueForMetric(point: CapacitySeriesPoint, metric: TimelineMetric): number | null {
  return metric === "annualCapacity" ? getAnnual(point) : getCumulative(point);
}

function yForValue(value: number, maxValue: number, geometry: ChartGeometry): number {
  const chartHeight = geometry.height - geometry.top - geometry.bottom;
  return geometry.top + chartHeight - (value / Math.max(1, maxValue)) * chartHeight;
}

function pathForSeries(
  series: CapacityScenarioSeries,
  metric: TimelineMetric,
  domain: { min: number; max: number },
  maxValue: number,
  geometry: ChartGeometry,
): string | null {
  let path = "";
  let open = false;
  const points = [...series.points].sort((a, b) => a.year - b.year);
  points.forEach((point) => {
    const value = valueForMetric(point, metric);
    if (finiteNumber(value) && finiteYear(point.year)) {
      const x = xForYear(point.year, domain, geometry).toFixed(2);
      const y = yForValue(value, maxValue, geometry).toFixed(2);
      path += `${open ? "L" : "M"}${x},${y} `;
      open = true;
    } else {
      open = false;
    }
  });
  return path.trim() || null;
}

function chartTicks(years: readonly number[]): number[] {
  if (years.length <= 5) return [...years];
  const count = 5;
  return Array.from({ length: count }, (_, index) => years[Math.round((index * (years.length - 1)) / (count - 1))]);
}

function numericMetricValues(series: readonly CapacityScenarioSeries[], metric: TimelineMetric): number[] {
  return series.flatMap((candidate) => candidate.points.map((point) => valueForMetric(point, metric)).filter(finiteNumber));
}

function objectiveTargetForMetric(objective: ScenarioObjective, metric: TimelineMetric): number | null {
  if (!finiteNumber(objective.target)) return null;
  const basis = objective.basis ?? "UNKNOWN";
  const isFlow = metric === "annualCapacity";
  if (basis === "MIXED" || (basis === "FLOW" && isFlow) || (basis === "STOCK" && !isFlow)) return objective.target;
  return null;
}

function CapacityChart({
  chartId,
  metric,
  years,
  objective,
  series,
}: {
  chartId: string;
  metric: TimelineMetric;
  years: readonly number[];
  objective: ScenarioObjective;
  series: readonly ChartSeries[];
}): JSX.Element {
  const geometry = CHART_GEOMETRY;
  const domain = yearDomain(years);
  const values = numericMetricValues(series.map((item) => item.series), metric);
  const target = objectiveTargetForMetric(objective, metric);
  const maxValue = Math.max(0, ...values, ...(finiteNumber(target) ? [target] : []));
  const title = metric === "annualCapacity" ? FLOW_LABEL : STOCK_LABEL;
  const unit = metric === "annualCapacity" ? series[0]?.series.annualUnit : series[0]?.series.cumulativeUnit;
  const chartTitleId = `${chartId}-title`;
  const chartDescriptionId = `${chartId}-description`;
  const ticks = chartTicks(years);
  const yTicks = [0, 0.25, 0.5, 0.75, 1];
  const hasKnownValues = values.length > 0;

  return (
    <figure className="insight-capacity-chart" aria-labelledby={chartTitleId}>
      <div className="insight-chart-heading">
        <div>
          <span className="insight-eyebrow">{title}</span>
          <h3 id={chartTitleId}>{metric === "annualCapacity" ? "Annual capacity path" : "Cumulative capacity stock"}</h3>
        </div>
        <span className="insight-chart-unit">{unit ? `unit · ${unit}` : "unit · UNKNOWN"}</span>
      </div>
      <div className="insight-chart-legend" aria-label={`${title} series legend`}>
        {series.map((item) => {
          const fallback = seriesHasKnownValue(item.series) ? "MODELLED" : "UNKNOWN";
          return (
            <span className="insight-chart-legend-item" key={item.key}>
              <span className={classNames("insight-legend-line", item.className)} aria-hidden="true" />
              <span>{item.series.label || item.label}</span>
              <EpistemicChip value={item.series.epistemic} fallback={fallback} />
            </span>
          );
        })}
        {finiteNumber(objectiveTargetForMetric(objective, metric)) && <span className="insight-chart-target-key"><span aria-hidden="true" />SCENARIO TARGET</span>}
        {finiteYear(objective.deadlineYear) && <span className="insight-chart-deadline-key"><span aria-hidden="true" />DEADLINE</span>}
      </div>
      {!hasKnownValues ? (
        <div className="insight-chart-empty" role="status">
          <EpistemicChip value="UNKNOWN" />
          <strong>No {title.toLowerCase()} values returned.</strong>
          <span>The registry/solver did not provide a plottable series for this metric.</span>
        </div>
      ) : (
        <svg
          className="insight-chart-svg"
          viewBox={`0 0 ${geometry.width} ${geometry.height}`}
          role="img"
          aria-labelledby={`${chartTitleId} ${chartDescriptionId}`}
        >
          <desc id={chartDescriptionId}>
            {title} scenario chart with optimistic and conservative series. Missing points are left unplotted and remain UNKNOWN.
          </desc>
          <g className="insight-chart-grid" aria-hidden="true">
            {yTicks.map((ratio) => {
              const y = yForValue(maxValue * ratio, maxValue, geometry);
              return <line key={`y-${ratio}`} x1={geometry.left} x2={geometry.width - geometry.right} y1={y} y2={y} />;
            })}
          </g>
          <g className="insight-chart-axis" aria-hidden="true">
            <line x1={geometry.left} x2={geometry.left} y1={geometry.top} y2={geometry.height - geometry.bottom} />
            <line x1={geometry.left} x2={geometry.width - geometry.right} y1={geometry.height - geometry.bottom} y2={geometry.height - geometry.bottom} />
            {yTicks.map((ratio) => {
              const value = maxValue * ratio;
              const y = yForValue(value, maxValue, geometry);
              return <text key={`ylabel-${ratio}`} x={geometry.left - 9} y={y + 3} textAnchor="end">{formatCapacity(value, unit)}</text>;
            })}
            {ticks.map((year) => {
              const x = xForYear(year, domain, geometry);
              return <text key={`xlabel-${year}`} x={x} y={geometry.height - 12} textAnchor="middle">{year}</text>;
            })}
          </g>
          {finiteYear(objective.deadlineYear) && (
            <g className="insight-chart-deadline" aria-label={`Scenario deadline ${objective.deadlineYear}`}>
              <line x1={xForYear(objective.deadlineYear, domain, geometry)} x2={xForYear(objective.deadlineYear, domain, geometry)} y1={geometry.top} y2={geometry.height - geometry.bottom} />
              <text x={xForYear(objective.deadlineYear, domain, geometry) + 5} y={geometry.top + 12}>DEADLINE</text>
            </g>
          )}
          {finiteNumber(target) && (
            <g className="insight-chart-target" aria-label={`Scenario target ${formatCapacity(target, unit)}`}>
              <line x1={geometry.left} x2={geometry.width - geometry.right} y1={yForValue(target, maxValue, geometry)} y2={yForValue(target, maxValue, geometry)} />
              <text x={geometry.width - geometry.right - 4} y={yForValue(target, maxValue, geometry) - 6} textAnchor="end">TARGET · {formatCapacity(target, unit)}</text>
            </g>
          )}
          {series.map((item) => {
            const path = pathForSeries(item.series, metric, domain, maxValue, geometry);
            const points = [...item.series.points].sort((a, b) => a.year - b.year);
            return (
              <g className={classNames("insight-series", item.className)} key={item.key}>
                {path && <path className="insight-series-path" d={path} />}
                {points.map((point, index) => {
                  const value = valueForMetric(point, metric);
                  if (!finiteNumber(value) || !finiteYear(point.year)) return null;
                  const x = xForYear(point.year, domain, geometry);
                  const y = yForValue(value, maxValue, geometry);
                  const pointEpistemic = normalizedEpistemic(point.epistemic, normalizedEpistemic(item.series.epistemic, "MODELLED"));
                  return (
                    <circle
                      className="insight-series-point"
                      cx={x}
                      cy={y}
                      r="4"
                      tabIndex={0}
                      key={`${item.key}-${point.year}-${index}`}
                      aria-label={`${item.series.label || item.label}, ${point.year}: ${formatCapacity(value, unit)}, ${pointEpistemic}`}
                    >
                      <title>{`${point.year}: ${formatCapacity(value, unit)} · ${pointEpistemic}`}</title>
                    </circle>
                  );
                })}
              </g>
            );
          })}
        </svg>
      )}
    </figure>
  );
}

function metricBasisLabel(metric: TimelineMetric): string {
  return metric === "annualCapacity" ? "annual flow" : "cumulative stock";
}

function tranchePosition(
  tranche: ProgramTranche,
  domain: { min: number; max: number },
): { left: number; width: number } | null {
  if (!finiteYear(tranche.startYear)) return null;
  const start = tranche.startYear;
  const end = finiteYear(tranche.endYear) ? Math.max(start, tranche.endYear) : start;
  const span = Math.max(1, domain.max - domain.min);
  return {
    left: Math.max(0, Math.min(100, ((start - domain.min) / span) * 100)),
    width: Math.max(2, Math.min(100, ((end - start || 1) / span) * 100)),
  };
}

function TrancheLane({
  tranches,
  years,
  onSelect,
}: {
  tranches: readonly ProgramTranche[];
  years: readonly number[];
  onSelect?: (tranche: ProgramTranche) => void;
}): JSX.Element {
  const domain = yearDomain(years);
  if (tranches.length === 0) {
    return <EmptyState title="No program tranches returned" detail="The scenario contains no tranche schedule. Timeline sequencing remains UNKNOWN." compact />;
  }
  return (
    <div className="insight-tranche-list" aria-label="Program tranches">
      {tranches.map((tranche) => {
        const position = tranchePosition(tranche, domain);
        const annual = getTrancheAnnual(tranche);
        const cumulative = getTrancheCumulative(tranche);
        const fallback = finiteNumber(annual) || finiteNumber(cumulative) ? "MODELLED" : "UNKNOWN";
        const rowContent = (
          <>
            <span className="insight-tranche-label">
              <strong>{tranche.label}</strong>
              <span>{tranche.startYear ?? "UNKNOWN"}{finiteYear(tranche.endYear) ? `–${tranche.endYear}` : " · end UNKNOWN"}</span>
            </span>
            <span className="insight-tranche-track" aria-hidden="true">
              {position ? <span className="insight-tranche-bar" style={{ "--insight-tranche-left": `${position.left}%`, "--insight-tranche-width": `${position.width}%` } as CSSProperties} /> : <span className="insight-tranche-unknown-bar">UNKNOWN WINDOW</span>}
            </span>
            <span className="insight-tranche-capacity">
              <span>{finiteNumber(annual) ? `${formatCapacity(annual)} / yr` : finiteNumber(cumulative) ? `${formatCapacity(cumulative)} stock` : "capacity UNKNOWN"}</span>
              <EpistemicChip value={tranche.epistemic} fallback={fallback} />
            </span>
          </>
        );
        return onSelect ? (
          <button type="button" className="insight-tranche-row" key={tranche.id} onClick={() => onSelect(tranche)} aria-label={`Select tranche ${tranche.label}`}>
            {rowContent}
          </button>
        ) : (
          <div className="insight-tranche-row insight-tranche-row-static" key={tranche.id}>{rowContent}</div>
        );
      })}
      <div className="insight-lane-axis" aria-hidden="true"><span>{years[0] ?? "UNKNOWN"}</span><span>{years.length ? years[years.length - 1] : "UNKNOWN"}</span></div>
    </div>
  );
}

function gateStateLabel(gate: SystemGate): string {
  return gate.state?.trim().toUpperCase() || gate.status?.trim().toUpperCase() || "UNKNOWN";
}

function GateList({ gates, onSelect }: { gates: readonly SystemGate[]; onSelect?: (gate: SystemGate) => void }): JSX.Element {
  if (gates.length === 0) {
    return <EmptyState title="No system gates returned" detail="No qualification, supply, infrastructure, or other gate records were supplied for this scenario." compact />;
  }
  return (
    <div className="insight-gate-list" aria-label="System gates">
      {gates.map((gate) => {
        const state = gateStateLabel(gate);
        const content = (
          <>
            <span className="insight-gate-marker" aria-hidden="true" />
            <span className="insight-gate-main"><strong>{gate.label}</strong><span>{gate.gateType || "gate type UNKNOWN"}{gate.detail ? ` · ${gate.detail}` : ""}</span></span>
            <span className="insight-gate-meta"><span>{finiteYear(gate.year) ? gate.year : "year UNKNOWN"}</span><span className={classNames("insight-gate-state", `insight-gate-state-${state.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`)}>{state}</span><EpistemicChip value={gate.epistemic} fallback="UNKNOWN" /></span>
          </>
        );
        return onSelect ? <button type="button" className="insight-gate-row" key={gate.id} onClick={() => onSelect(gate)} aria-label={`Select system gate ${gate.label}`}>{content}</button> : <div className="insight-gate-row insight-gate-row-static" key={gate.id}>{content}</div>;
      })}
    </div>
  );
}

function ObjectiveDetails({ objective }: { objective: ScenarioObjective }): JSX.Element {
  const targetText = objective.targetLabel?.trim() || (finiteNumber(objective.target) ? formatCapacity(objective.target, objective.unit) : "UNKNOWN");
  const basis = objective.basis ?? "UNKNOWN";
  return (
    <dl className="insight-objective-details">
      <div><dt>target</dt><dd>{targetText}</dd></div>
      <div><dt>geography</dt><dd>{objective.geography?.trim() || "UNKNOWN"}</dd></div>
      <div><dt>deadline</dt><dd>{finiteYear(objective.deadlineYear) ? objective.deadlineYear : "UNKNOWN"}</dd></div>
      <div><dt>quantity basis</dt><dd><span className={classNames("insight-basis-chip", `insight-basis-${basis.toLowerCase()}`)}>{basis}</span></dd></div>
    </dl>
  );
}

/**
 * Program capacity is presented as two separate semantic charts: annual
 * output is a flow, while cumulative output is a stock. The distinction is
 * intentionally repeated beside the charts and in the data table.
 */
export function ProgramTimeline(props: ProgramTimelineProps): JSX.Element {
  const timeline = useMemo(() => timelineFromProps(props), [props.data, props.timeline, props.objective, props.scenarioObjective, props.tranches, props.optimistic, props.conservative, props.gates, props.systemGates]);
  const rootId = useId().replace(/:/g, "");
  const [selectedTrancheId, setSelectedTrancheId] = useState<string | null>(null);
  const [selectedGateId, setSelectedGateId] = useState<string | null>(null);

  if (!timeline) {
    return <section className={classNames("insight-surface", "insight-program-timeline", props.className)} aria-labelledby={`${rootId}-empty-title`}><EmptyState title="Program timeline unavailable" detail="No scenario objective was supplied. Annual flow, cumulative stock, tranches, and system gates remain UNKNOWN." /></section>;
  }

  const { objective, tranches, optimistic, conservative, gates } = timeline;
  const years = collectYears(timeline);
  const series: readonly ChartSeries[] = [
    { key: "optimistic", series: optimistic, className: "insight-series-optimistic", label: "Optimistic" },
    { key: "conservative", series: conservative, className: "insight-series-conservative", label: "Conservative" },
  ];
  const selectedTranche = tranches.find((tranche) => tranche.id === selectedTrancheId) ?? null;
  const selectedGate = gates.find((gate) => gate.id === selectedGateId) ?? null;
  const objectiveEpistemic = objective.epistemic ?? "SCENARIO";

  const selectTranche = (tranche: ProgramTranche) => {
    setSelectedTrancheId(tranche.id);
    props.onSelectTranche?.(tranche);
  };
  const selectGate = (gate: SystemGate) => {
    setSelectedGateId(gate.id);
    props.onSelectGate?.(gate);
  };

  return (
    <section className={classNames("insight-surface", "insight-program-timeline", props.className)} aria-labelledby={`${rootId}-title`}>
      <header className="insight-surface-header">
        <div className="insight-header-copy">
          <div className="insight-chip-row"><ScenarioChip /><EpistemicChip value={objectiveEpistemic} fallback="SCENARIO" /><span className="insight-chip insight-chip-modelled">PROGRAM TIMELINE</span></div>
          <h2 id={`${rootId}-title`}>{objective.label}</h2>
          <p>Scenario capacity path for the stated objective. Values are shown as returned by the model or registry; missing evidence remains UNKNOWN.</p>
        </div>
        <div className="insight-header-aside"><span className="insight-eyebrow">SCENARIO OBJECTIVE</span><strong>{objective.id || "objective identity UNKNOWN"}</strong></div>
      </header>

      <div className="insight-objective-band">
        <ObjectiveDetails objective={objective} />
        <div className="insight-flow-stock-note" role="note">
          <span className="insight-flow-stock-icon" aria-hidden="true">↕</span>
          <div><strong>FLOW ≠ STOCK</strong><span>Annual capacity is a flow per year. Cumulative capacity is a stock accumulated across years; it is not another annual rate.</span></div>
        </div>
        {objective.note && <p className="insight-objective-note">{objective.note}</p>}
      </div>

      <div className="insight-chart-grid-wrap" aria-label="Scenario capacity charts">
        <CapacityChart chartId={`${rootId}-flow`} metric="annualCapacity" years={years} objective={objective} series={series} />
        <CapacityChart chartId={`${rootId}-stock`} metric="cumulativeCapacity" years={years} objective={objective} series={series} />
      </div>

      <div className="insight-program-columns">
        <section className="insight-panel" aria-labelledby={`${rootId}-tranches`}>
          <div className="insight-panel-heading"><div><span className="insight-eyebrow">EXECUTION SEQUENCE</span><h3 id={`${rootId}-tranches`}>Program tranches</h3></div><span className="insight-count-chip">{tranches.length || "UNKNOWN"}</span></div>
          <TrancheLane tranches={tranches} years={years} onSelect={props.onSelectTranche ? selectTranche : undefined} />
          {selectedTranche && <div className="insight-selection-detail" role="status"><span className="insight-eyebrow">SELECTED TRANCHE</span><strong>{selectedTranche.label}</strong><span>{selectedTranche.note || selectedTranche.status || "Detail UNKNOWN — inspect the source record before treating this tranche as committed."}</span></div>}
        </section>
        <section className="insight-panel" aria-labelledby={`${rootId}-gates`}>
          <div className="insight-panel-heading"><div><span className="insight-eyebrow">SYSTEM CLOSURE</span><h3 id={`${rootId}-gates`}>System gates</h3></div><span className="insight-count-chip">{gates.length || "UNKNOWN"}</span></div>
          <GateList gates={gates} onSelect={props.onSelectGate ? selectGate : undefined} />
          {selectedGate && <div className="insight-selection-detail" role="status"><span className="insight-eyebrow">SELECTED GATE</span><strong>{selectedGate.label}</strong><span>{selectedGate.detail || selectedGate.dependencies?.join(" · ") || "Gate detail UNKNOWN — no causal evidence was returned."}</span></div>}
        </section>
      </div>

      <section className="insight-panel insight-program-table-panel" aria-labelledby={`${rootId}-series-table`}>
        <div className="insight-panel-heading"><div><span className="insight-eyebrow">SERIES REGISTER</span><h3 id={`${rootId}-series-table`}>Annual flow / cumulative stock values</h3></div><span className="insight-small-note">SCENARIO · MODELLED where supplied · UNKNOWN where absent</span></div>
        <CapacityTable optimistic={optimistic} conservative={conservative} unit={objective.unit} years={years} />
      </section>
    </section>
  );
}

function pointByYear(series: CapacityScenarioSeries, year: number): CapacitySeriesPoint | null {
  return series.points.find((point) => point.year === year) ?? null;
}

function CapacityCell({ value, unit, epistemic }: { value: number | null; unit?: string | null; epistemic?: InsightEpistemicClass }): JSX.Element {
  if (!finiteNumber(value)) return <UnknownLabel detail="No capacity value was returned for this year." />;
  return <span className="insight-capacity-cell"><strong>{formatCapacity(value, unit)}</strong><EpistemicChip value={epistemic} fallback="MODELLED" /></span>;
}

function CapacityTable({
  optimistic,
  conservative,
  unit,
  years,
}: {
  optimistic: CapacityScenarioSeries;
  conservative: CapacityScenarioSeries;
  unit?: string | null;
  years: readonly number[];
}): JSX.Element {
  if (years.length === 0) return <EmptyState title="No series years returned" detail="The timeline has no year-indexed values to tabulate." compact />;
  return (
    <div className="insight-table-scroll">
      <table className="insight-data-table">
        <caption className="insight-visually-hidden">Scenario capacity table. Annual values are flows and cumulative values are stocks.</caption>
        <thead><tr><th scope="col">YEAR</th><th scope="col">OPTIMISTIC · FLOW</th><th scope="col">CONSERVATIVE · FLOW</th><th scope="col">OPTIMISTIC · STOCK</th><th scope="col">CONSERVATIVE · STOCK</th></tr></thead>
        <tbody>
          {years.map((year) => {
            const optimisticPoint = pointByYear(optimistic, year);
            const conservativePoint = pointByYear(conservative, year);
            return (
              <tr key={year}>
                <th scope="row">{year}</th>
                <td><CapacityCell value={getAnnual(optimisticPoint)} unit={optimistic.annualUnit || unit} epistemic={optimisticPoint?.epistemic ?? optimistic.epistemic} /></td>
                <td><CapacityCell value={getAnnual(conservativePoint)} unit={conservative.annualUnit || unit} epistemic={conservativePoint?.epistemic ?? conservative.epistemic} /></td>
                <td><CapacityCell value={getCumulative(optimisticPoint)} unit={optimistic.cumulativeUnit || unit} epistemic={optimisticPoint?.epistemic ?? optimistic.epistemic} /></td>
                <td><CapacityCell value={getCumulative(conservativePoint)} unit={conservative.cumulativeUnit || unit} epistemic={conservativePoint?.epistemic ?? conservative.epistemic} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function capabilityEpistemic(row: CapabilityLeverage): InsightEpistemicClass | undefined {
  return row.epistemic ?? row.epistemicClass ?? row.epistemic_class;
}

function capabilityProxy(row: CapabilityLeverage): number | null {
  const value = row.leverageProxy ?? row.leverage_proxy;
  return finiteNumber(value) ? value : null;
}

function capabilityProxyUnit(row: CapabilityLeverage): string | null | undefined {
  return row.leverageProxyUnit ?? row.leverage_proxy_unit;
}

function capabilityCanonicalId(row: CapabilityLeverage): string {
  return row.canonicalId || row.canonical_id || row.id;
}

function capabilityMetric(row: CapabilityLeverage, camel: RegistryMetric, snake: RegistryMetric, fallback?: RegistryMetric): RegistryMetric {
  if (camel !== undefined && camel !== null) return camel;
  if (snake !== undefined && snake !== null) return snake;
  return fallback;
}

function capabilityCrossSectorReuse(row: CapabilityLeverage): RegistryMetric {
  return capabilityMetric(row, row.crossSectorReuse, row.cross_sector_reuse, row.mappedPackIds ?? row.mapped_pack_ids);
}

function capabilityCrossSectorLabels(row: CapabilityLeverage): readonly string[] | undefined {
  return row.crossSectorReuseLabels ?? row.mappedPackIds ?? row.mapped_pack_ids;
}

function capabilityDownstreamUnlock(row: CapabilityLeverage): RegistryMetric {
  return capabilityMetric(row, row.downstreamUnlock, row.downstream_unlock, row.mappedEntityIds ?? row.mapped_entity_ids);
}

function capabilityDownstreamLabels(row: CapabilityLeverage): readonly string[] | undefined {
  return row.downstreamUnlockLabels ?? row.mappedEntityIds ?? row.mapped_entity_ids;
}

function metricCount(value: RegistryMetric): number | null {
  if (finiteNumber(value)) return value;
  if (Array.isArray(value)) return value.length;
  return null;
}

function metricLabels(value: RegistryMetric, labels?: readonly string[]): string[] {
  const candidates = labels?.length ? labels : Array.isArray(value) ? value : [];
  return candidates.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function metricSummary(value: RegistryMetric, labels: readonly string[] | undefined, noun: string): { primary: string; detail: string } {
  const count = metricCount(value);
  if (!finiteNumber(count)) return { primary: "UNKNOWN", detail: `${noun} UNKNOWN` };
  const names = metricLabels(value, labels);
  return { primary: formatNumber(count, 0), detail: names.length ? names.slice(0, 3).join(" · ") : `${noun} linked` };
}

function evidenceGapSummary(row: CapabilityLeverage): { primary: string; detail: string } {
  const gap = row.evidenceGap ?? row.evidence_gap;
  if (typeof row.evidenceGapLabel === "string" && row.evidenceGapLabel.trim()) return { primary: row.evidenceGapLabel.trim(), detail: "registry evidence gap" };
  if (typeof gap === "string" && gap.trim()) return { primary: gap.trim(), detail: "registry evidence gap" };
  if (finiteNumber(gap)) return { primary: formatNumber(gap, 0), detail: "open evidence gaps" };
  return { primary: "UNKNOWN", detail: "evidence gap UNKNOWN" };
}

function taskCount(row: CapabilityLeverage): number | null {
  const ids = row.evidenceTaskIds ?? row.evidence_task_ids;
  if (finiteNumber(row.taskCount)) return row.taskCount;
  if (finiteNumber(row.task_count)) return row.task_count;
  if (finiteNumber(row.evidenceTaskCount)) return row.evidenceTaskCount;
  if (Array.isArray(ids)) return ids.length;
  return null;
}

function proxyValueLabel(value: number | null | undefined, unit?: string | null): string {
  if (!finiteNumber(value)) return "UNKNOWN";
  const suffix = unit?.trim();
  return suffix ? `${formatNumber(value)} ${suffix}` : formatNumber(value);
}

function proxyFallback(row: CapabilityLeverage): InsightEpistemicClass {
  const epistemic = capabilityEpistemic(row);
  if (epistemic) return epistemic;
  return finiteNumber(capabilityProxy(row)) ? "MODELLED" : "UNKNOWN";
}

function selectRowWithKeyboard(event: KeyboardEvent<HTMLTableRowElement>, onSelect: () => void): void {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onSelect();
  }
}

function LeverageDetail({ row }: { row: CapabilityLeverage }): JSX.Element {
  const sectors = metricSummary(capabilityCrossSectorReuse(row), capabilityCrossSectorLabels(row), "cross-sector reuse");
  const unlocks = metricSummary(capabilityDownstreamUnlock(row), capabilityDownstreamLabels(row), "downstream unlock");
  const reverse = metricSummary(row.reverseReach ?? row.reverse_reach, undefined, "reverse reach");
  const evidence = evidenceGapSummary(row);
  const tasks = taskCount(row);
  return (
    <aside className="insight-leverage-detail" aria-label={`Details for ${row.name}`}>
      <div className="insight-detail-header"><div><span className="insight-eyebrow">SELECTED CAPABILITY</span><h3>{row.name}</h3><span className="insight-detail-id">{capabilityCanonicalId(row)}</span></div><EpistemicChip value={capabilityEpistemic(row)} fallback={proxyFallback(row)} /></div>
      <div className="insight-detail-metrics">
        <div><span>structural leverage proxy</span><strong>{proxyValueLabel(capabilityProxy(row), capabilityProxyUnit(row))}</strong></div>
        <div><span>cross-sector reuse links</span><strong>{sectors.primary}</strong><small>{sectors.detail}</small></div>
        <div><span>downstream unlock links</span><strong>{unlocks.primary}</strong><small>{unlocks.detail}</small></div>
        <div><span>reverse reach links</span><strong>{reverse.primary}</strong><small>{reverse.detail}</small></div>
        <div><span>evidence gap</span><strong>{evidence.primary}</strong><small>{evidence.detail}</small></div>
        <div><span>evidence tasks</span><strong>{finiteNumber(tasks) ? formatNumber(tasks, 0) : "UNKNOWN"}</strong></div>
      </div>
      <p className="insight-detail-caveat">Structural registry reach only. This is not economic option value, ROI, investment ranking, supply, qualification, or capacity.</p>
      {row.note && <p className="insight-detail-note">{row.note}</p>}
    </aside>
  );
}

/**
 * Capability discovery is intentionally a registry surface, not an
 * investment-ranking surface. Every row comes from the supplied data array.
 */
export function CapabilityLeverage(props: CapabilityLeverageProps): JSX.Element {
  const supplied = props.rows ?? props.records ?? props.capabilities ?? props.data;
  const [localSelectedId, setLocalSelectedId] = useState<string | null>(null);
  const rootId = useId().replace(/:/g, "");
  const rows = supplied ?? [];
  const hasRegistryResponse = supplied !== undefined && supplied !== null;
  const selectedId = props.selectedCapabilityId ?? localSelectedId;
  const selected = rows.find((row) => row.id === selectedId) ?? null;
  const maxProxy = useMemo(() => {
    const values = rows.map((row) => capabilityProxy(row)).filter(finiteNumber);
    return Math.max(0, ...values);
  }, [rows]);

  const select = (row: CapabilityLeverage) => {
    setLocalSelectedId(row.id);
    props.onSelectCapability?.(row);
    props.onSelect?.(row);
  };

  return (
    <section className={classNames("insight-surface", "insight-capability-leverage", props.className)} aria-labelledby={`${rootId}-title`}>
      <header className="insight-surface-header">
        <div className="insight-header-copy">
          <div className="insight-chip-row"><span className="insight-chip insight-chip-discover">DISCOVER</span><span className="insight-chip insight-chip-registry">CANONICAL REGISTRY</span><span className="insight-chip insight-epistemic-modelled">STRUCTURAL PROXY</span></div>
          <h2 id={`${rootId}-title`}>Capability leverage surfaces</h2>
          <p>Explore explicit registry links from capabilities to sectors, downstream nodes, reverse-buildability reach, evidence gaps, and research tasks.</p>
        </div>
        <div className="insight-header-aside"><span className="insight-eyebrow">ROWS RETURNED</span><strong>{hasRegistryResponse ? rows.length : "UNKNOWN"}</strong></div>
      </header>

      <div className="insight-leverage-caveat" role="note"><span className="insight-chip insight-chip-warning">NO ECONOMIC OPTION VALUE CLAIM</span><p>“Leverage proxy” is a structural, registry-derived diagnostic. Cross-sector reuse and unlock links do not establish economic option value, investment return, supply, qualification, or industrial capacity.</p></div>

      {!hasRegistryResponse ? <EmptyState title="Canonical capability registry unavailable" detail="No registry response was supplied. Structural leverage, reuse, unlock, reverse reach, evidence gaps, and task counts remain UNKNOWN." /> : rows.length === 0 ? <EmptyState title="No capability rows returned" detail="The registry response was empty. No demonstration records are fabricated, so all cross-sector relationships remain UNKNOWN." /> : (
        <>
          <div className="insight-table-scroll">
            <table className="insight-data-table insight-leverage-table">
              <caption className="insight-visually-hidden">Registry-derived capability leverage rows. Select a row for details.</caption>
              <thead><tr><th scope="col">CAPABILITY</th><th scope="col">LEVERAGE PROXY</th><th scope="col">CROSS-SECTOR REUSE</th><th scope="col">DOWNSTREAM UNLOCK</th><th scope="col">REVERSE REACH</th><th scope="col">EVIDENCE GAP</th><th scope="col">TASKS</th></tr></thead>
              <tbody>
                {rows.map((row) => {
                  const sectors = metricSummary(capabilityCrossSectorReuse(row), capabilityCrossSectorLabels(row), "reuse links");
                  const unlocks = metricSummary(capabilityDownstreamUnlock(row), capabilityDownstreamLabels(row), "unlock links");
                  const reverse = metricSummary(row.reverseReach ?? row.reverse_reach, undefined, "reverse links");
                  const evidence = evidenceGapSummary(row);
                  const tasks = taskCount(row);
                  const proxy = capabilityProxy(row);
                  const barWidth = finiteNumber(proxy) && maxProxy > 0 ? Math.max(0, Math.min(100, (proxy / maxProxy) * 100)) : 0;
                  const isSelected = selectedId === row.id;
                  return (
                    <tr
                      key={row.id}
                      className={classNames("insight-leverage-row", isSelected && "is-selected")}
                      tabIndex={0}
                      role="button"
                      aria-selected={isSelected}
                      aria-label={`Select capability ${row.name}`}
                      onClick={() => select(row)}
                      onKeyDown={(event) => selectRowWithKeyboard(event, () => select(row))}
                    >
                      <th scope="row"><span className="insight-capability-name">{row.name}</span><span className="insight-capability-id">{capabilityCanonicalId(row)}</span>{row.kind && <span className="insight-capability-kind">{row.kind}</span>}</th>
                      <td><span className="insight-proxy-cell"><span className="insight-proxy-value">{proxyValueLabel(proxy, capabilityProxyUnit(row))}</span><span className="insight-proxy-bar" aria-hidden="true"><span style={{ "--insight-proxy-width": `${barWidth}%` } as CSSProperties} /></span><EpistemicChip value={capabilityEpistemic(row)} fallback={proxyFallback(row)} /></span></td>
                      <td><span className="insight-metric-cell"><strong>{sectors.primary}</strong><small>{sectors.detail}</small></span></td>
                      <td><span className="insight-metric-cell"><strong>{unlocks.primary}</strong><small>{unlocks.detail}</small></span></td>
                      <td><span className="insight-metric-cell"><strong>{reverse.primary}</strong><small>{reverse.detail}</small></span></td>
                      <td><span className="insight-metric-cell insight-evidence-gap"><strong>{evidence.primary}</strong><small>{evidence.detail}</small></span></td>
                      <td><span className="insight-metric-cell"><strong>{finiteNumber(tasks) ? formatNumber(tasks, 0) : <UnknownLabel />}</strong><small>{finiteNumber(tasks) ? "evidence tasks" : "task count UNKNOWN"}</small></span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="insight-table-note">Bars are relative only to the returned rows in this view. They are not normalized across runs and do not represent economic value.</p>
          {selected && <LeverageDetail row={selected} />}
        </>
      )}
    </section>
  );
}

/** Optional composition for hosts that want both surfaces in one region. */
export function InsightSurfaces({ timeline, capabilities, onSelectCapability, onSelectTranche, onSelectGate }: InsightSurfacesProps): JSX.Element {
  return (
    <div className="insight-surfaces">
      {timeline !== undefined && <ProgramTimeline data={timeline} onSelectTranche={onSelectTranche} onSelectGate={onSelectGate} />}
      {capabilities !== undefined && <CapabilityLeverage data={capabilities} onSelectCapability={onSelectCapability} />}
      {timeline === undefined && capabilities === undefined && <EmptyState title="Insight surfaces awaiting data" detail="Supply a scenario timeline or canonical capability registry rows to begin exploration." />}
    </div>
  );
}

export default InsightSurfaces;
