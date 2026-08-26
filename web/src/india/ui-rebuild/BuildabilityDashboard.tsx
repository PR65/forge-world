import { FormEvent, useEffect, useMemo, useState, type CSSProperties } from "react";
import {
  BOTTOM_TABS,
  NAV_ITEMS,
  clampMapCoordinate,
  cleanDisplayText,
  cleanNarrative,
  deriveRequirementGroups,
  displayItemTitle,
  formatCount,
  hasUsableMapPosition,
  metricAriaLabel,
  metricDescription,
  metricDisplay,
  statusLabel,
  statusMix,
  statusTone,
  type StatusTone,
} from "./buildability-ui";
import type {
  BuildabilityBottleneck,
  BuildabilityDashboardProps,
  BuildabilityDomain,
  BuildabilityEvidence,
  BuildabilityItem,
  BuildabilityMapPoint,
  BuildabilityMetricInput,
  BuildabilityMode,
  BuildabilityNode,
  BuildabilityPathStep,
  BuildabilityRequirementGroup,
  BuildabilityTabId,
  BuildabilityViewModel,
} from "./buildability-types";
import "./buildability-dashboard.css";

const SUMMARY_METRICS: ReadonlyArray<{
  key: "available" | "partialOrImportDependent" | "missing" | "unknown";
  label: string;
  shortLabel: string;
  description: string;
  tone: StatusTone;
}> = [
  {
    key: "available",
    label: "Made in India",
    shortLabel: "Strong / available",
    description: "Strong or achievable",
    tone: "available",
  },
  {
    key: "partialOrImportDependent",
    label: "Import dependent",
    shortLabel: "Partial / import dependent",
    description: "Available with imports",
    tone: "partial",
  },
  {
    key: "missing",
    label: "Missing",
    shortLabel: "Missing",
    description: "Not available in the mapped state",
    tone: "missing",
  },
  {
    key: "unknown",
    label: "Unknown",
    shortLabel: "Unknown",
    description: "Insufficient mapped evidence",
    tone: "unknown",
  },
];

const EMPTY_DOMAINS: BuildabilityDomain[] = [];

function safeNarrative(value: string | null | undefined, fallback = "Not recorded yet."): string {
  return cleanNarrative(value, fallback);
}

function metricNumber(value: BuildabilityMetricInput): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "object" && value && typeof value.value === "number" && Number.isFinite(value.value)) return value.value;
  return null;
}

function metricHasValue(value: BuildabilityMetricInput): boolean {
  if (typeof value === "string") return Boolean(value.trim());
  if (typeof value === "number") return Number.isFinite(value);
  if (value && typeof value === "object") return Boolean(value.display?.trim()) || metricNumber(value) !== null;
  return false;
}

function statusDotLabel(tone: StatusTone): string {
  if (tone === "available") return "Strong / available";
  if (tone === "partial") return "Partial / import dependent";
  if (tone === "missing") return "Missing";
  if (tone === "conflicted") return "Conflicted";
  return "Unknown";
}

function ItemStatusDots({ item }: { item: BuildabilityItem }) {
  const tones = statusMix(item.statusMix, item.status);
  return (
    <span className="forge-status-dots" aria-label={`Status: ${tones.map(statusDotLabel).join(", ")}`}>
      {tones.map((tone, index) => (
        <span className={`forge-status-dot ${tone}`} key={`${tone}-${index}`} title={statusDotLabel(tone)} />
      ))}
    </span>
  );
}

function ForgeMark() {
  return (
    <svg className="forge-mark" viewBox="0 0 48 48" aria-hidden="true">
      <circle cx="24" cy="24" r="16" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="24" cy="24" r="8" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M24 2v8M24 38v8M2 24h8M38 24h8M8.4 8.4l5.7 5.7M33.9 33.9l5.7 5.7M39.6 8.4l-5.7 5.7M14.1 33.9l-5.7 5.7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M16 24l5 5 11-12" fill="none" stroke="#36d4ac" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Icon({ name }: { name: string }) {
  return <span className="forge-icon" aria-hidden="true">{name}</span>;
}

function LimitedData({ message, compact = false }: { message: string; compact?: boolean }) {
  return (
    <div className={`forge-limited-data ${compact ? "compact" : ""}`} role="status">
      <span className="forge-limited-mark" aria-hidden="true">—</span>
      <span><strong>Limited data</strong>{message ? <small>{message}</small> : null}</span>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="forge-error-state" role="alert">
      <span className="forge-error-mark" aria-hidden="true">!</span>
      <div>
        <strong>Analysis unavailable</strong>
        <p>{safeNarrative(message, "The buildability result could not be loaded.")}</p>
        {onRetry ? <button className="forge-secondary-button" type="button" onClick={onRetry}>Retry analysis</button> : null}
      </div>
    </div>
  );
}

function TopBar({
  query,
  activeMode,
  onQueryChange,
  onAnalyze,
  onModeChange,
  onUtilityAction,
}: Pick<BuildabilityDashboardProps, "query" | "activeMode" | "onQueryChange" | "onAnalyze" | "onModeChange" | "onUtilityAction">) {
  const [localQuery, setLocalQuery] = useState(query ?? "");
  useEffect(() => setLocalQuery(query ?? ""), [query]);
  const value = query ?? localQuery;
  const updateQuery = (next: string) => {
    if (query === undefined) setLocalQuery(next);
    onQueryChange?.(next);
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onAnalyze?.(value);
  };
  return (
    <header className="forge-topbar">
      <a className="forge-brand" href="/india" aria-label="FORGE India home">
        <span className="forge-brand-mark"><ForgeMark /></span>
        <span className="forge-brand-wordmark">FORGE <em>INDIA</em></span>
      </a>
      <nav className="forge-primary-nav" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
          <button
            className={activeMode === item || (!activeMode && item === "Analyze") ? "active" : ""}
            key={item}
            type="button"
            onClick={() => onModeChange?.(item as BuildabilityMode)}
          >
            {item}
          </button>
        ))}
      </nav>
      <form className="forge-global-search" role="search" onSubmit={submit}>
        <Icon name="⌕" />
        <label className="forge-visually-hidden" htmlFor="forge-global-search">Search FORGE India</label>
        <input
          id="forge-global-search"
          type="search"
          value={value}
          onChange={(event) => updateQuery(event.target.value)}
          placeholder="Describe an industrial product, system or objective…"
          autoComplete="off"
          spellCheck={false}
        />
        <kbd>⌘ K</kbd>
      </form>
      <div className="forge-utility-actions" aria-label="Utilities">
        <button type="button" aria-label="Notifications" onClick={() => onUtilityAction?.("notifications")}><Icon name="♧" /></button>
        <button type="button" aria-label="Help" onClick={() => onUtilityAction?.("help")}>?</button>
        <button className="forge-avatar" type="button" aria-label="Profile" onClick={() => onUtilityAction?.("profile")}>AR</button>
        <span className="forge-chevron" aria-hidden="true">⌄</span>
      </div>
    </header>
  );
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((value, index) => {
    const x = (index / (values.length - 1)) * 100;
    const y = 29 - ((value - min) / range) * 24;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg className="forge-sparkline" viewBox="0 0 100 32" preserveAspectRatio="none" aria-label="Index trend">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function DomainSidebar({
  domains = EMPTY_DOMAINS,
  activeDomainId,
  viewModel,
  onDomainSelect,
}: Pick<BuildabilityDashboardProps, "domains" | "activeDomainId" | "viewModel" | "onDomainSelect">) {
  const index = viewModel?.indiaIndex;
  return (
    <aside className="forge-sidebar" aria-label="Industrial domains">
      <div className="forge-sidebar-heading">Industrial domains</div>
      <nav className="forge-domain-list" aria-label="India industrial domains">
        {domains.length ? domains.map((domain, indexNumber) => {
          const active = domain.id === activeDomainId || (!activeDomainId && domain.name === viewModel?.domain);
          return (
            <button
              className={`forge-domain-button ${active ? "active" : ""}`}
              key={domain.id}
              type="button"
              onClick={() => onDomainSelect?.(domain)}
              aria-current={active ? "page" : undefined}
              title={domain.description ? safeNarrative(domain.description) : undefined}
            >
              <span className="forge-domain-order">{String(indexNumber + 1).padStart(2, "0")}</span>
              <span className="forge-domain-name">{cleanDisplayText(domain.shortName || domain.name, "Industrial domain")}</span>
              {domain.status ? <span className={`forge-domain-status ${statusTone(domain.status)}`} aria-hidden="true" /> : null}
            </button>
          );
        }) : <LimitedData compact message="The domain index is not available." />}
      </nav>
      <div className="forge-sidebar-index">
        <div className="forge-sidebar-index-head">
          <span>India industrial index</span>
          <span className="forge-info-icon" title="Provided by the current world-state snapshot" aria-label="Index context">i</span>
        </div>
        {index ? (
          <>
            <div className="forge-index-value">{metricDisplay(index.index)} <small>/100</small></div>
            {index.deltaLabel ? <div className="forge-index-delta">↗ {safeNarrative(index.deltaLabel)}</div> : null}
            {index.sparkline?.length ? <Sparkline values={index.sparkline} /> : null}
            {index.note ? <p>{safeNarrative(index.note)}</p> : null}
            {index.updatedLabel ? <small className="forge-index-updated">{safeNarrative(index.updatedLabel)}</small> : null}
          </>
        ) : (
          <LimitedData compact message="An overall index is not computed for this view." />
        )}
      </div>
    </aside>
  );
}

function AnalysisHero({
  viewModel,
  query,
  onQueryChange,
  onAnalyze,
}: Pick<BuildabilityDashboardProps, "viewModel" | "query" | "onQueryChange" | "onAnalyze">) {
  const [localQuery, setLocalQuery] = useState(query ?? viewModel?.title ?? "");
  useEffect(() => setLocalQuery(query ?? viewModel?.title ?? ""), [query, viewModel?.title]);
  const value = query ?? localQuery;
  const updateQuery = (next: string) => {
    if (query === undefined) setLocalQuery(next);
    onQueryChange?.(next);
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onAnalyze?.(value);
  };
  return (
    <section className="forge-panel forge-analysis-hero" aria-labelledby="forge-analysis-heading">
      <div className="forge-hero-grid" aria-hidden="true" />
      <div className="forge-hero-copy">
        <div className="forge-hero-kicker">India buildability analysis</div>
        <h1 id="forge-analysis-heading">Can India build this?</h1>
        <form className="forge-analysis-form" onSubmit={submit}>
          <Icon name="⌕" />
          <label className="forge-visually-hidden" htmlFor="forge-analysis-target">Product or industrial objective</label>
          <input
            id="forge-analysis-target"
            type="search"
            value={value}
            onChange={(event) => updateQuery(event.target.value)}
            placeholder="Describe a product, system or objective…"
            autoComplete="off"
            spellCheck={false}
          />
          {value ? <button className="forge-clear-search" type="button" onClick={() => updateQuery("")} aria-label="Clear product search">×</button> : null}
          <button className="forge-analyze-button" type="submit">Analyze buildability <span aria-hidden="true">→</span></button>
        </form>
        <div className="forge-analysis-meta">
          {viewModel?.category ? <span className="forge-chip">Category: {cleanDisplayText(viewModel.category, "Mapped category")}</span> : null}
          {viewModel?.complexity ? <span className="forge-chip">Complexity: <b>{cleanDisplayText(viewModel.complexity, "Not classified")}</b><i className={`forge-chip-dot ${statusTone(viewModel.complexity)}`} /></span> : null}
          {!viewModel && !value ? <span className="forge-hero-hint">Start with a physical product or objective.</span> : null}
        </div>
        {viewModel?.plainSummary ? <p className="forge-hero-summary">{safeNarrative(viewModel.plainSummary)}</p> : null}
      </div>
    </section>
  );
}

function MetricRing({
  label,
  shortLabel,
  description,
  value,
  tone,
}: {
  label: string;
  shortLabel: string;
  description: string;
  value: BuildabilityMetricInput;
  tone: StatusTone;
}) {
  const numeric = metricNumber(value);
  const progress = numeric === null ? 0 : Math.max(0, Math.min(100, numeric));
  const descriptionOverride = metricDescription(value);
  return (
    <div className={`forge-metric-ring ${tone} ${numeric === null ? "no-value" : ""}`}>
      <div
        className="forge-ring"
        style={{ "--forge-ring-progress": `${progress * 3.6}deg` } as CSSProperties}
        role="img"
        aria-label={metricAriaLabel(label, value)}
      >
        <span>{metricDisplay(value)}</span>
      </div>
      <strong>{label}</strong>
      <span className="forge-metric-short">{shortLabel}</span>
      <small>{descriptionOverride || description}</small>
    </div>
  );
}

function BuildabilitySummaryPanel({ viewModel }: { viewModel: BuildabilityViewModel | null }) {
  const buildability = viewModel?.buildability;
  const overall = buildability?.overallIndex;
  return (
    <section className="forge-panel forge-summary-panel" aria-labelledby="forge-summary-heading">
      <div className="forge-panel-heading">
        <div>
          <span className="forge-panel-kicker">India buildability summary</span>
          <h2 id="forge-summary-heading" className="forge-visually-hidden">India buildability summary</h2>
        </div>
        <button className="forge-panel-link" type="button" title="Status definitions">What do these mean? <span aria-hidden="true">ⓘ</span></button>
      </div>
      <div className="forge-summary-metrics">
        {SUMMARY_METRICS.map((metric) => (
          <MetricRing
            key={metric.key}
            label={metric.label}
            shortLabel={metric.shortLabel}
            description={metric.description}
            value={buildability?.[metric.key]}
            tone={metric.tone}
          />
        ))}
      </div>
      {metricHasValue(overall) ? (
        <div className="forge-overall-index">
          <span>Overall buildability index</span>
          <strong>{metricDisplay(overall)}</strong>
        </div>
      ) : null}
      {buildability?.assessedLabel ? <div className="forge-assessed-label">{safeNarrative(buildability.assessedLabel)}</div> : null}
    </section>
  );
}

function SystemCard({
  system,
  index,
  selected,
  onSelect,
}: {
  system: BuildabilityNode;
  index: number;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button className={`forge-system-card ${statusTone(system.status)} ${selected ? "selected" : ""}`} type="button" onClick={onSelect} aria-pressed={selected}>
      <span className="forge-system-order">{index + 1}</span>
      <strong>{displayItemTitle(system)}</strong>
      {system.subtitle ? <span>{safeNarrative(system.subtitle)}</span> : system.kind ? <span>{cleanDisplayText(system.kind)}</span> : null}
      <ItemStatusDots item={system} />
    </button>
  );
}

function RequirementCard({
  group,
  selected,
  onSelect,
}: {
  group: BuildabilityRequirementGroup;
  selected: boolean;
  onSelect: () => void;
}) {
  const count = typeof group.count === "number" ? group.count : group.items?.length;
  return (
    <button className={`forge-requirement-card ${statusTone(group.status)} ${selected ? "selected" : ""}`} type="button" onClick={onSelect} aria-pressed={selected}>
      <span className="forge-requirement-icon" aria-hidden="true">{group.icon || "◇"}</span>
      <strong>{displayItemTitle(group)}</strong>
      <span>{count === undefined ? "Mapped requirement" : count ? `${formatCount(count)} mapped` : "Not mapped yet"}</span>
      <ItemStatusDots item={group} />
    </button>
  );
}

function DecompositionPanel({
  viewModel,
  onSystemSelect,
  onItemSelect,
}: Pick<BuildabilityDashboardProps, "viewModel" | "onSystemSelect" | "onItemSelect">) {
  const [selectedSystemId, setSelectedSystemId] = useState<string | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const systems = viewModel?.majorSystems ?? [];
  const groups = useMemo(() => (viewModel ? deriveRequirementGroups(viewModel) : []), [viewModel]);
  const selectedSystem = systems.find((system, index) => (system.id || `system-${index}`) === selectedSystemId) ?? null;
  const selectedGroup = groups.find((group, index) => (group.id || `group-${index}`) === selectedGroupId) ?? null;
  const targetTitle = cleanDisplayText(viewModel?.title, "Product target");

  const chooseSystem = (system: BuildabilityNode, index: number) => {
    const nextId = system.id || `system-${index}`;
    setSelectedSystemId((current) => current === nextId ? null : nextId);
    setSelectedGroupId(null);
    onSystemSelect?.(system);
  };
  const chooseGroup = (group: BuildabilityRequirementGroup, index: number) => {
    const nextId = group.id || `group-${index}`;
    setSelectedGroupId((current) => current === nextId ? null : nextId);
    setSelectedSystemId(null);
  };

  return (
    <section className="forge-panel forge-decomposition-panel" aria-labelledby="forge-decomposition-heading">
      <div className="forge-panel-heading">
        <div>
          <span className="forge-panel-kicker">System decomposition</span>
          <h2 id="forge-decomposition-heading">{targetTitle}</h2>
        </div>
        <div className="forge-decomposition-controls">
          <span>View as: <b>Tree</b></span>
          <button type="button" aria-label="Expand decomposition" title="Expand decomposition">⛶</button>
        </div>
      </div>
      {systems.length ? (
        <>
          <div className="forge-system-root">{targetTitle}</div>
          <div className="forge-tree-connector" aria-hidden="true" />
          <div className="forge-system-row" role="list" aria-label="Major systems">
            {systems.map((system, index) => (
              <SystemCard
                key={system.id || `${system.title}-${index}`}
                system={system}
                index={index}
                selected={(system.id || `system-${index}`) === selectedSystemId}
                onSelect={() => chooseSystem(system, index)}
              />
            ))}
          </div>
          {selectedSystem ? (
            <div className="forge-decomposition-drilldown">
              <div><span className="forge-panel-kicker">Selected system</span><strong>{displayItemTitle(selectedSystem)}</strong></div>
              {selectedSystem.children?.length ? (
                <div className="forge-drilldown-items">
                  {selectedSystem.children.map((child, index) => (
                    <button key={child.id || `${child.title}-${index}`} type="button" onClick={() => onSystemSelect?.(child)}>
                      <span className={`forge-mini-status ${statusTone(child.status)}`} />
                      {displayItemTitle(child)}
                    </button>
                  ))}
                </div>
              ) : <small>No deeper system mapping is supplied.</small>}
            </div>
          ) : null}
        </>
      ) : <LimitedData compact message="Major systems are not mapped for this target yet." />}
      <div className="forge-requirements-heading">
        <span>Industrial requirements <small>(applied to each subsystem)</small></span>
      </div>
      {groups.length ? (
        <div className="forge-requirement-row" role="list" aria-label="Industrial requirement classes">
          {groups.map((group, index) => (
            <RequirementCard
              key={group.id || `${group.title}-${index}`}
              group={group}
              selected={(group.id || `group-${index}`) === selectedGroupId}
              onSelect={() => chooseGroup(group, index)}
            />
          ))}
        </div>
      ) : <LimitedData compact message="Industrial requirement classes are not mapped yet." />}
      {selectedGroup ? (
        <div className="forge-decomposition-drilldown forge-group-drilldown">
          <div><span className="forge-panel-kicker">{displayItemTitle(selectedGroup)}</span><strong>{selectedGroup.items?.length ? `${formatCount(selectedGroup.items.length)} mapped items` : "No mapped items"}</strong></div>
          {selectedGroup.items?.length ? (
            <div className="forge-drilldown-items">
              {selectedGroup.items.slice(0, 8).map((item, index) => (
                <button key={item.id || `${item.title}-${index}`} type="button" onClick={() => onItemSelect?.(item)}>
                  <span className={`forge-mini-status ${statusTone(item.status)}`} />
                  {displayItemTitle(item)}
                </button>
              ))}
            </div>
          ) : <small>Nothing is mapped in this class yet.</small>}
        </div>
      ) : null}
      <div className="forge-status-legend" aria-label="Buildability status legend">
        <span><i className="available" />Strong / available</span>
        <span><i className="partial" />Partial / import dependent</span>
        <span><i className="missing" />Missing</span>
        <span><i className="unknown" />Unknown</span>
      </div>
    </section>
  );
}

function BottlenecksPanel({
  bottlenecks = [],
  onSelect,
  onViewAll,
}: {
  bottlenecks?: BuildabilityBottleneck[];
  onSelect?: (bottleneck: BuildabilityBottleneck) => void;
  onViewAll?: () => void;
}) {
  const visible = bottlenecks.slice(0, 7);
  return (
    <section className="forge-panel forge-bottlenecks-panel" aria-labelledby="forge-bottlenecks-heading">
      <div className="forge-panel-heading">
        <h2 id="forge-bottlenecks-heading"><span className="forge-warning-icon" aria-hidden="true">△</span> Critical bottlenecks</h2>
        {bottlenecks.length > visible.length ? <button className="forge-panel-link" type="button" onClick={onViewAll}>View all ({formatCount(bottlenecks.length)}) <span aria-hidden="true">›</span></button> : null}
      </div>
      {visible.length ? (
        <ol className="forge-bottleneck-list">
          {visible.map((bottleneck, index) => (
            <li key={bottleneck.id || `${bottleneck.title}-${index}`}>
              <button type="button" onClick={() => onSelect?.(bottleneck)}>
                <span className="forge-bottleneck-rank">{bottleneck.rank ?? index + 1}</span>
                <span className="forge-bottleneck-title">{displayItemTitle(bottleneck)}{bottleneck.reason ? <small>{safeNarrative(bottleneck.reason)}</small> : null}</span>
                {bottleneck.impactLabel ? <span className={`forge-impact-label ${statusTone(bottleneck.status)}`}>{cleanDisplayText(bottleneck.impactLabel, "Priority")}</span> : null}
              </button>
            </li>
          ))}
        </ol>
      ) : <LimitedData compact message="No ranked bottlenecks are mapped for this target." />}
    </section>
  );
}

function LocalizationPanel({
  steps = [],
  onSelect,
  onViewAll,
}: {
  steps?: BuildabilityPathStep[];
  onSelect?: (step: BuildabilityPathStep) => void;
  onViewAll?: () => void;
}) {
  const visible = steps.slice(0, 4);
  return (
    <section className="forge-panel forge-localization-panel" aria-labelledby="forge-localization-heading">
      <div className="forge-panel-heading">
        <h2 id="forge-localization-heading"><span className="forge-path-icon" aria-hidden="true">↗</span> Localization path <small>— what India must build</small></h2>
        {steps.length > visible.length ? <button className="forge-panel-link" type="button" onClick={onViewAll}>View roadmap <span aria-hidden="true">⌄</span></button> : null}
      </div>
      {visible.length ? (
        <ol className="forge-localization-list">
          {visible.map((step, index) => (
            <li key={step.id || `${step.title}-${index}`}>
              <button type="button" onClick={() => onSelect?.(step)}>
                <span className="forge-path-step-number">{step.order ?? index + 1}</span>
                <span className="forge-path-title">{displayItemTitle(step)}{step.note ? <small>{safeNarrative(step.note)}</small> : null}</span>
                {step.timeLabel ? <span className="forge-path-time">{cleanDisplayText(step.timeLabel, "")}</span> : null}
              </button>
            </li>
          ))}
        </ol>
      ) : <LimitedData compact message="No making ladder is available for this target yet." />}
    </section>
  );
}

function CapabilityMapPanel({
  points = [],
  onPointSelect,
  onViewAll,
}: {
  points?: BuildabilityMapPoint[];
  onPointSelect?: (point: BuildabilityMapPoint) => void;
  onViewAll?: () => void;
}) {
  const plotted = points.filter((point) => hasUsableMapPosition(point.x, point.y));
  return (
    <section className="forge-panel forge-map-panel" aria-labelledby="forge-map-heading">
      <div className="forge-panel-heading">
        <h2 id="forge-map-heading">India capability map <span className="forge-info-icon" title="Only supplied geocoded points are plotted" aria-label="Map context">i</span></h2>
        {points.length ? <button className="forge-panel-link" type="button" onClick={onViewAll}>View full map <span aria-hidden="true">›</span></button> : null}
      </div>
      {plotted.length ? (
        <div className="forge-map-stage" aria-label={`${plotted.length} mapped capability locations`}>
          <svg className="forge-map-outline" viewBox="0 0 100 100" aria-hidden="true">
            <path d="M38 6 47 10 57 9 64 16 74 19 78 28 88 35 84 43 91 51 83 57 80 67 72 71 68 82 60 92 51 85 44 78 37 74 31 65 25 59 22 48 16 43 21 35 18 28 26 24 27 16 35 13Z" />
          </svg>
          <div className="forge-map-grid" aria-hidden="true" />
          {plotted.slice(0, 18).map((point, index) => (
            <button
              className={`forge-map-point ${statusTone(point.status)}`}
              key={point.id || `${point.label}-${index}`}
              style={{ left: `${clampMapCoordinate(point.x ?? 50)}%`, top: `${clampMapCoordinate(point.y ?? 50)}%` }}
              type="button"
              onClick={() => onPointSelect?.(point)}
              title={`${cleanDisplayText(point.label, "Mapped location")}${point.location ? ` · ${cleanDisplayText(point.location)}` : ""}`}
              aria-label={cleanDisplayText(point.label, "Mapped location")}
            />
          ))}
          <div className="forge-map-labels">
            {plotted.slice(0, 5).map((point, index) => <span key={point.id || `${point.label}-label-${index}`}>{cleanDisplayText(point.label, "Mapped location")}</span>)}
          </div>
          <div className="forge-map-legend"><span><i className="available" />Strong</span><span><i className="partial" />Emerging</span><span><i className="unknown" />Uncertain</span></div>
        </div>
      ) : (
        <LimitedData message={points.length ? "Geocoded positions are not plottable in this view." : "No geocoded capability records were supplied."} />
      )}
    </section>
  );
}

function FacilitiesPanel({ facilities, onSelect, onViewAll }: { facilities?: BuildabilityViewModel["facilities"]; onSelect?: (item: BuildabilityItem) => void; onViewAll?: () => void }) {
  const visible = facilities?.slice(0, 6) ?? [];
  return (
    <section className="forge-panel forge-facilities-panel" aria-labelledby="forge-facilities-heading">
      <div className="forge-panel-heading">
        <h2 id="forge-facilities-heading">Top potential facilities / suppliers <span className="forge-info-icon" title="Only supplied facility records are shown" aria-label="Facility context">i</span></h2>
        {facilities?.length ? <button className="forge-panel-link" type="button" onClick={onViewAll}>View all <span aria-hidden="true">›</span></button> : null}
      </div>
      {visible.length ? (
        <div className="forge-facility-table" role="table" aria-label="Potential facilities and suppliers">
          <div className="forge-facility-row forge-facility-header" role="row"><span>Facility / company</span><span>Location</span><span>Strength areas</span><span>Status</span></div>
          {visible.map((facility, index) => (
            <button className="forge-facility-row" key={facility.id || `${facility.title}-${index}`} type="button" onClick={() => onSelect?.(facility)} role="row">
              <strong>{displayItemTitle(facility)}</strong>
              <span>{facility.location ? cleanDisplayText(facility.location) : "—"}</span>
              <span>{facility.strengthAreas?.length ? facility.strengthAreas.slice(0, 2).map((area) => cleanDisplayText(area)).join(", ") : safeNarrative(facility.summary, "Not recorded")}</span>
              <span className={`forge-table-status ${statusTone(facility.status)}`}>{facility.statusLabel ? cleanDisplayText(facility.statusLabel) : statusLabel(facility.status)}</span>
            </button>
          ))}
        </div>
      ) : <LimitedData message="No useful facility or supplier records are available for this target." />}
    </section>
  );
}

function EvidencePanel({ evidence, onSelect, onViewAll }: { evidence?: BuildabilityEvidence[]; onSelect?: (evidence: BuildabilityEvidence) => void; onViewAll?: () => void }) {
  const visible = evidence?.slice(0, 4) ?? [];
  return (
    <section className="forge-panel forge-evidence-panel" aria-labelledby="forge-evidence-heading">
      <div className="forge-panel-heading">
        <h2 id="forge-evidence-heading">Evidence &amp; provenance <span className="forge-info-icon" title="Supporting records from the analysis" aria-label="Evidence context">i</span></h2>
        {evidence?.length ? <button className="forge-panel-link" type="button" onClick={onViewAll}>View all evidence <span aria-hidden="true">›</span></button> : null}
      </div>
      {visible.length ? (
        <div className="forge-evidence-list">
          {visible.map((item, index) => (
            <button className="forge-evidence-item" key={item.id || `${item.title}-${index}`} type="button" onClick={() => onSelect?.(item)}>
              <span className={`forge-evidence-state ${statusTone(item.epistemicClass)}`}>{cleanDisplayText(item.epistemicClass, "UNKNOWN")}</span>
              <span className="forge-evidence-copy"><strong>{cleanDisplayText(item.title, "Evidence record")}</strong><small>{item.source ? cleanDisplayText(item.source) : "Source not recorded"}{item.type ? ` · ${cleanDisplayText(item.type)}` : ""}</small></span>
              <span className="forge-evidence-meta">{item.confidenceLabel ? cleanDisplayText(item.confidenceLabel) : "—"}{item.updatedLabel ? <small>{cleanDisplayText(item.updatedLabel)}</small> : null}</span>
            </button>
          ))}
        </div>
      ) : <LimitedData message="No supporting evidence records are attached to this view." />}
    </section>
  );
}

function LowerPanels({
  viewModel,
  onMapPointSelect,
  onItemSelect,
  onEvidenceSelect,
  onPanelOpen,
}: Pick<BuildabilityDashboardProps, "viewModel" | "onMapPointSelect" | "onItemSelect" | "onEvidenceSelect" | "onPanelOpen">) {
  return (
    <div className="forge-lower-grid">
      <CapabilityMapPanel points={viewModel?.mapPoints} onPointSelect={onMapPointSelect} onViewAll={() => onPanelOpen?.("map")} />
      <FacilitiesPanel facilities={viewModel?.facilities} onSelect={onItemSelect} onViewAll={() => onPanelOpen?.("facilities")} />
      <EvidencePanel evidence={viewModel?.evidenceSummary} onSelect={onEvidenceSelect} onViewAll={() => onPanelOpen?.("evidence")} />
    </div>
  );
}

function tabDataAvailable(viewModel: BuildabilityViewModel | null, tab: BuildabilityTabId): boolean {
  if (!viewModel) return false;
  const values: Partial<Record<BuildabilityTabId, unknown[] | undefined>> = {
    systems: viewModel.majorSystems,
    components: viewModel.components,
    processes: viewModel.processes,
    equipment: viewModel.equipment,
    materials: viewModel.materials,
    facilities: viewModel.facilities,
    evidence: viewModel.evidenceSummary,
    imports: viewModel.imports,
  };
  return tab === "capacity" || tab === "research-tasks" ? false : Boolean(values[tab]?.length);
}

function BottomTabs({
  viewModel,
  activeTab,
  onTabSelect,
}: Pick<BuildabilityDashboardProps, "viewModel" | "activeTab" | "onTabSelect">) {
  const selected = activeTab ?? "systems";
  return (
    <nav className="forge-bottom-tabs" aria-label="Buildability detail views">
      {BOTTOM_TABS.map((tab) => {
        const limited = !tabDataAvailable(viewModel, tab.id);
        return (
          <button
            className={`${selected === tab.id ? "active" : ""} ${limited ? "limited" : ""}`}
            key={tab.id}
            type="button"
            onClick={() => onTabSelect?.(tab.id)}
            aria-current={selected === tab.id ? "page" : undefined}
            aria-label={`${tab.label}${limited ? " — limited data" : ""}`}
            title={limited ? `${tab.label}: limited data` : tab.label}
          >
            <span className="forge-tab-icon" aria-hidden="true">{tab.icon}</span>
            <span>{tab.label}</span>
            {limited ? <i aria-hidden="true" /> : null}
          </button>
        );
      })}
    </nav>
  );
}

export default function BuildabilityDashboard({
  viewModel,
  domains = EMPTY_DOMAINS,
  activeDomainId,
  query,
  loading = false,
  error = null,
  activeTab,
  activeMode = "Analyze",
  onQueryChange,
  onAnalyze,
  onDomainSelect,
  onModeChange,
  onTabSelect,
  onSystemSelect,
  onItemSelect,
  onBottleneckSelect,
  onPathSelect,
  onMapPointSelect,
  onEvidenceSelect,
  onPanelOpen,
  onUtilityAction,
  onRetry,
  className = "",
}: BuildabilityDashboardProps) {
  return (
    <div className={`forge-buildability-dashboard ${className}`.trim()}>
      <TopBar
        query={query}
        activeMode={activeMode}
        onQueryChange={onQueryChange}
        onAnalyze={onAnalyze}
        onModeChange={onModeChange}
        onUtilityAction={onUtilityAction}
      />
      <div className="forge-dashboard-body">
        <DomainSidebar domains={domains} activeDomainId={activeDomainId} viewModel={viewModel} onDomainSelect={onDomainSelect} />
        <main className="forge-dashboard-workspace" id="forge-dashboard-main">
          <div className="forge-dashboard-grid">
            <AnalysisHero viewModel={viewModel} query={query} onQueryChange={onQueryChange} onAnalyze={onAnalyze} />
            <BuildabilitySummaryPanel viewModel={viewModel} />
            <DecompositionPanel viewModel={viewModel} onSystemSelect={onSystemSelect} onItemSelect={onItemSelect} />
            <div className="forge-side-stack">
              <BottlenecksPanel bottlenecks={viewModel?.criticalBottlenecks} onSelect={onBottleneckSelect} onViewAll={() => onPanelOpen?.("bottlenecks")} />
              <LocalizationPanel steps={viewModel?.localizationPath} onSelect={onPathSelect} onViewAll={() => onPanelOpen?.("localization")} />
            </div>
            <LowerPanels viewModel={viewModel} onMapPointSelect={onMapPointSelect} onItemSelect={onItemSelect} onEvidenceSelect={onEvidenceSelect} onPanelOpen={onPanelOpen} />
          </div>
          {loading ? <div className="forge-refreshing" role="status"><span className="forge-spinner" /> Refreshing buildability analysis…</div> : null}
          {error && viewModel ? <div className="forge-inline-error" role="alert">{safeNarrative(error)} <button type="button" onClick={onRetry}>Retry</button></div> : null}
          {error && !viewModel ? <ErrorState message={error} onRetry={onRetry} /> : null}
        </main>
      </div>
      <BottomTabs viewModel={viewModel} activeTab={activeTab} onTabSelect={onTabSelect} />
    </div>
  );
}

export { BuildabilityDashboard };
