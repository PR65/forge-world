import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  cleanDisplayText,
  cleanNarrative,
  deriveRequirementGroups,
  displayItemQualifier,
  displayItemTitle,
  statusLabel,
  statusTone,
} from "../ui-rebuild/buildability-ui";
import type {
  BuildabilityBottleneck,
  BuildabilityDomain,
  BuildabilityEvidence,
  BuildabilityItem,
  BuildabilityNode,
  BuildabilityPathStep,
  BuildabilityRequirementGroup,
  BuildabilityViewModel,
} from "../ui-rebuild/buildability-types";
import "./product-surfaces.css";

export type WhySelection =
  | { kind: "item"; value: BuildabilityItem }
  | { kind: "bottleneck"; value: BuildabilityBottleneck }
  | { kind: "path"; value: BuildabilityPathStep };

function keyFor(item: BuildabilityItem, index = 0): string {
  return String(item.id || `${item.kind || "item"}-${item.title}-${index}`);
}

function safeTitle(item: Pick<BuildabilityItem, "title">): string {
  return displayItemTitle(item).replace(/\s+Capability Remains Unknown\.?$/i, "");
}

function safeCopy(value: string | null | undefined, fallback: string): string {
  return cleanNarrative(value, fallback);
}

function Status({ item, compact = false, showUnknown = false }: { item: BuildabilityItem; compact?: boolean; showUnknown?: boolean }) {
  const tone = statusTone(item.status);
  if (tone === "unknown" && !showUnknown) return null;
  return (
    <span className={`fip-status fip-status--${tone} ${compact ? "fip-status--compact" : ""}`}>
      <span aria-hidden="true" className="fip-status__dot" />
      {statusLabel(item.status, item.statusLabel)}
    </span>
  );
}

function Empty({ children }: { children: string }) {
  return <p className="fip-empty">{children}</p>;
}

export interface IndustrialDecompositionProps {
  viewModel: BuildabilityViewModel;
  selectedSystemKey?: string | null;
  maxSystems?: number;
  maxGroups?: number;
  maxItemsPerGroup?: number;
  onProductSelect?: (product: BuildabilityItem) => void;
  onSystemSelect?: (system: BuildabilityNode) => void;
  onRequirementGroupSelect?: (group: BuildabilityRequirementGroup) => void;
  onItemSelect?: (item: BuildabilityItem) => void;
}

/**
 * A bounded semantic plane: product -> major systems -> important requirement
 * classes. It intentionally never renders the complete graph at once.
 */
export function IndustrialDecomposition({
  viewModel,
  selectedSystemKey,
  maxSystems = 7,
  maxGroups = 5,
  maxItemsPerGroup = 4,
  onProductSelect,
  onSystemSelect,
  onRequirementGroupSelect,
  onItemSelect,
}: IndustrialDecompositionProps) {
  const systems = viewModel.majorSystems ?? [];
  const groups = useMemo(() => deriveRequirementGroups(viewModel), [viewModel]);
  const [localSystemKey, setLocalSystemKey] = useState<string | null>(null);
  const [hoveredSystemKey, setHoveredSystemKey] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"STRUCTURE" | "BUILDABILITY">("STRUCTURE");
  const [showAllSystems, setShowAllSystems] = useState(false);
  const [showAllGroups, setShowAllGroups] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (selectedSystemKey !== undefined) return;
    if (localSystemKey && !systems.some((system, index) => keyFor(system, index) === localSystemKey)) {
      setLocalSystemKey(null);
    }
  }, [localSystemKey, selectedSystemKey, systems]);

  const activeSystemKey = selectedSystemKey === undefined ? localSystemKey : selectedSystemKey;
  const selectedSystem = systems.find((system, index) => keyFor(system, index) === activeSystemKey) ?? null;
  const visibleSystems = showAllSystems ? systems : systems.slice(0, maxSystems);
  const systemGroups = (selectedSystem?.requirementGroups?.length ? selectedSystem.requirementGroups : groups)
    .filter((group) => (group.items?.length ?? group.count ?? 0) > 0);
  const visibleGroups = showAllGroups ? systemGroups : systemGroups.slice(0, maxGroups);

  function selectSystem(system: BuildabilityNode, index: number) {
    setLocalSystemKey(keyFor(system, index));
    onSystemSelect?.(system);
  }

  function toggleGroup(group: BuildabilityRequirementGroup, index: number) {
    const groupKey = keyFor(group, index);
    setExpandedGroups((current) => {
      const next = new Set(current);
      next.has(groupKey) ? next.delete(groupKey) : next.add(groupKey);
      return next;
    });
    onRequirementGroupSelect?.(group);
  }

  return (
    <section className="fip-surface fip-decomposition" aria-labelledby="fip-decomposition-title">
      <header className="fip-section-head">
        <div>
          <p className="fip-eyebrow">Industrial decomposition</p>
          <h2 id="fip-decomposition-title">What has to work together</h2>
        </div>
        <div className="fip-decomposition__controls" aria-label="Decomposition view">
          {(["STRUCTURE", "BUILDABILITY"] as const).map((mode) => (
            <button aria-pressed={viewMode === mode} key={mode} onClick={() => setViewMode(mode)} type="button">
              {mode === "STRUCTURE" ? "Structure" : "Buildability"}
            </button>
          ))}
        </div>
      </header>

      <div className={`fip-decomposition__plane is-${viewMode.toLowerCase()}`}>
        <button
          aria-pressed={!selectedSystem}
          className={`fip-root-node ${!selectedSystem ? "is-active" : ""}`}
          type="button"
          onClick={() => {
            setLocalSystemKey(null);
            onProductSelect?.({ title: viewModel.title, kind: viewModel.kind, summary: viewModel.plainSummary });
          }}
        >
          <span>{cleanDisplayText(viewModel.kind, "Product")}</span>
          <strong>{cleanDisplayText(viewModel.title, "Selected product")}</strong>
          {viewModel.qualifier ? <em>{cleanDisplayText(viewModel.qualifier, "")}</em> : null}
          <small>{safeCopy(viewModel.plainSummary, "A first-order industrial product map.")}</small>
        </button>

        <div className="fip-decomposition__axis" aria-hidden="true"><span /></div>

        {systems.length ? (
          <div className="fip-system-grid" aria-label="Major systems">
            {visibleSystems.map((system, index) => {
              const systemKey = keyFor(system, index);
              const active = selectedSystem === system;
              return (
                <button
                  aria-pressed={active}
                  className={`fip-system-node is-${statusTone(system.status)} ${active ? "is-active" : ""} ${hoveredSystemKey && hoveredSystemKey !== systemKey ? "is-dimmed" : ""}`}
                  key={systemKey}
                  onClick={() => selectSystem(system, index)}
                  onMouseEnter={() => setHoveredSystemKey(systemKey)}
                  onMouseLeave={() => setHoveredSystemKey(null)}
                  type="button"
                >
                  <span className="fip-system-node__number">{String(index + 1).padStart(2, "0")}</span>
                  <strong>{safeTitle(system)}</strong>
                  {displayItemQualifier(system) ? <small>{displayItemQualifier(system)}</small> : null}
                  {viewMode === "BUILDABILITY" ? <Status compact item={system} /> : null}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="fip-architecture-gap">
            <strong>Detailed subsystem architecture is not yet mapped for this product.</strong>
            <p>The manufacturing requirements below remain useful, but they are not being presented as physical components.</p>
          </div>
        )}

        {systems.length > maxSystems ? (
          <button className="fip-text-action" type="button" onClick={() => setShowAllSystems((value) => !value)}>
            {showAllSystems ? "Show fewer systems" : `Show ${systems.length - maxSystems} more systems`}
          </button>
        ) : null}

        <div className="fip-requirements-head">
          <div>
            {selectedSystem ? <button className="fip-back-action" onClick={() => setLocalSystemKey(null)} type="button">← Back to product</button> : <span>Important industrial requirements</span>}
            <strong>{selectedSystem ? safeTitle(selectedSystem) : "Product-wide requirements"}</strong>
          </div>
          <small>Open a class to see mapped processes, equipment, materials and capabilities.</small>
        </div>

        {visibleGroups.length ? (
          <div className="fip-requirement-list">
            {visibleGroups.map((group, groupIndex) => {
              const groupKey = keyFor(group, groupIndex);
              const items = group.items ?? [];
              const expanded = expandedGroups.has(groupKey);
              const visibleItems = expanded ? items : items.slice(0, maxItemsPerGroup);
              return (
                <article className={`fip-requirement-group ${expanded ? "is-expanded" : ""}`} key={groupKey}>
                  <button
                    aria-expanded={expanded}
                    className="fip-requirement-group__head"
                    onClick={() => toggleGroup(group, groupIndex)}
                    type="button"
                  >
                    <span>
                      <strong>{safeTitle(group)}</strong>
                      <small>{items.length || group.count || 0} mapped</small>
                    </span>
                    {viewMode === "BUILDABILITY" ? <Status compact item={group} /> : null}
                    <span aria-hidden="true" className="fip-chevron">{expanded ? "−" : "+"}</span>
                  </button>
                  {expanded ? (
                    items.length ? (
                      <div className="fip-requirement-items">
                        {visibleItems.map((item, itemIndex) => (
                          <button key={keyFor(item, itemIndex)} onClick={() => onItemSelect?.(item)} type="button">
                            <span><strong>{safeTitle(item)}</strong>{displayItemQualifier(item) ? <small>{displayItemQualifier(item)}</small> : null}</span>
                            {viewMode === "BUILDABILITY" ? <Status compact item={item} /> : null}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <Empty>No detailed requirements are mapped in this class yet.</Empty>
                    )
                  ) : null}
                </article>
              );
            })}
          </div>
        ) : (
          <Empty>Industrial requirement classes are not yet mapped for this product.</Empty>
        )}

        {systemGroups.length > maxGroups ? (
          <button className="fip-text-action" type="button" onClick={() => setShowAllGroups((value) => !value)}>
            {showAllGroups ? "Show fewer requirement classes" : `Show all ${systemGroups.length} requirement classes`}
          </button>
        ) : null}
      </div>
    </section>
  );
}

function selectionItem(selection: WhySelection): BuildabilityItem {
  return selection.value;
}

function isCompositionNote(value: string | null | undefined): boolean {
  return /derived from|recorded gap categor|no separate subsystem record|navigation grouping|typed requirements/i.test(value || "");
}

function whyMatters(selection: WhySelection): string {
  const item = selectionItem(selection);
  if (selection.kind === "bottleneck") {
    return safeCopy(selection.value.reason || item.summary || item.note, "This requirement sits on an important dependency path for the current objective.");
  }
  const detail = !isCompositionNote(item.summary) ? item.summary : !isCompositionNote(item.note) ? item.note : null;
  return safeCopy(detail, `${safeTitle(item)} is a major requirement in the manufacturing route; failure to source, make or qualify it constrains the finished product.`);
}

function difficultyFor(selection: WhySelection): string {
  const item = selectionItem(selection);
  const tone = statusTone(item.status);
  if (item.note && !isCompositionNote(item.note)) return safeCopy(item.note, "The detailed difficulty is not recorded.");
  if (tone === "missing") return "The mapped state does not show this requirement as available in India.";
  if (tone === "partial") return "The mapped state indicates a partial, scale-limited or import-dependent capability.";
  if (tone === "available") return "The capability appears broadly available, but objective-specific scale and qualification are not established here.";
  if (tone === "conflicted") return "The mapped evidence conflicts, so the capability position cannot be stated cleanly.";
  return "FORGE knows this dependency belongs in the route, but its exact India status at the required specification is not yet verified.";
}

function firstActionFor(selection: WhySelection): string {
  const item = selectionItem(selection);
  if (selection.kind === "path") {
    return safeCopy(item.summary || item.note, "Use this stage to define the next bounded localization action.");
  }
  const tone = statusTone(item.status);
  if (tone === "missing" || tone === "unknown" || tone === "conflicted") {
    return `Resolve what ${safeTitle(item)} actually requires in India before committing it to the manufacturing plan.`;
  }
  if (tone === "partial") return `Separate what can be sourced now for ${safeTitle(item)} from what must be localized or qualified next.`;
  return `Confirm objective-specific scale, specification and qualification for ${safeTitle(item)} before relying on it.`;
}

export interface WhyDrawerProps {
  open: boolean;
  selection: WhySelection | null;
  requirements?: BuildabilityItem[];
  evidence?: BuildabilityEvidence[];
  onClose: () => void;
  onGoDeeper?: (item: BuildabilityItem) => void;
  onAddToBuildPath?: (item: BuildabilityItem) => void;
}

export function WhyDrawer({
  open,
  selection,
  requirements = [],
  evidence = [],
  onClose,
  onGoDeeper,
  onAddToBuildPath,
}: WhyDrawerProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (event.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>('button, [href], input, summary, [tabindex]:not([tabindex="-1"])'))
          .filter((element) => !element.hasAttribute("disabled"));
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    requestAnimationFrame(() => dialogRef.current?.querySelector<HTMLElement>("button")?.focus());
    return () => { window.removeEventListener("keydown", onKeyDown); previousFocus?.focus(); };
  }, [onClose, open]);

  if (!open || !selection) return null;
  const item = selectionItem(selection);

  return (
    <div className="fip-drawer-layer">
      <button aria-label="Close WHY inspector" className="fip-drawer-scrim" onClick={onClose} type="button" />
      <aside aria-labelledby="fip-why-title" aria-modal="true" className="fip-why" ref={dialogRef} role="dialog">
        <header className="fip-why__head">
          <div>
            <p className="fip-eyebrow">Why</p>
            <h2 id="fip-why-title">{safeTitle(item)}</h2>
          </div>
          <button aria-label="Close WHY inspector" className="fip-icon-action" onClick={onClose} type="button">×</button>
        </header>

        <Status item={item} />

        <div className="fip-why__section">
          <h3>Why it matters</h3>
          <p>{whyMatters(selection)}</p>
        </div>

        <div className="fip-why__section">
          <h3>Requires</h3>
          {requirements.length ? (
            <div className="fip-why__requirements">
              {requirements.slice(0, 8).map((requirement, index) => (
                <button key={keyFor(requirement, index)} onClick={() => onGoDeeper?.(requirement)} type="button">
                  {safeTitle(requirement)}
                </button>
              ))}
            </div>
          ) : (
            <Empty>No deeper requirements are exposed for this selection yet.</Empty>
          )}
        </div>

        <div className="fip-why__section">
          <h3>{statusTone(item.status) === "unknown" ? "What remains uncertain" : "Main industrial difficulty"}</h3>
          <p>{difficultyFor(selection)}</p>
        </div>

        <div className="fip-why__section">
          <h3>Possible first action</h3>
          <p>{firstActionFor(selection)}</p>
        </div>

        <details className="fip-evidence-details">
          <summary>Evidence / basis</summary>
          {evidence.length ? (
            <ul>
              {evidence.slice(0, 6).map((entry, index) => (
                <li key={`${entry.title}-${index}`}>
                  <strong>{cleanDisplayText(entry.title, "Evidence state")}</strong>
                  <span>{safeCopy(entry.summary || entry.epistemicClass, "No further evidence note is exposed.")}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p>Detailed evidence is not exposed for this selection. Treat the stated status as a first-order map, not supplier or capacity proof.</p>
          )}
        </details>

        <footer className="fip-why__actions">
          <button className="fip-button fip-button--secondary" onClick={() => onGoDeeper?.(item)} type="button">Go deeper</button>
          <button className="fip-button" onClick={() => onAddToBuildPath?.(item)} type="button">Add to build path</button>
        </footer>
      </aside>
    </div>
  );
}

export interface BuildPathSurfaceProps {
  viewModel: BuildabilityViewModel;
  objective?: string | null;
  addedItems?: BuildabilityItem[];
  onStepSelect?: (step: BuildabilityPathStep) => void;
  onItemSelect?: (item: BuildabilityItem) => void;
  onRemoveAddedItem?: (item: BuildabilityItem) => void;
}

function firstNames(items: BuildabilityItem[], limit = 2): string {
  return items.slice(0, limit).map((item) => safeTitle(item)).join(" and ");
}

/** Compose a product-specific staged path from the current presentation graph. */
function specificBuildPath(viewModel: BuildabilityViewModel): BuildabilityPathStep[] {
  const mapped = (viewModel.localizationPath ?? []).filter((step) => safeTitle(step) && (step.summary || step.note));
  if (mapped.length) return mapped.slice(0, 6);
  const product = cleanDisplayText(viewModel.title, "the selected product");
  const all = [
    ...(viewModel.majorSystems ?? []), ...(viewModel.components ?? []), ...(viewModel.processes ?? []),
    ...(viewModel.equipment ?? []), ...(viewModel.materials ?? []), ...(viewModel.capabilities ?? []),
  ];
  const available = all.filter((item) => statusTone(item.status) === "available");
  const constrained = all.filter((item) => ["partial", "missing"].includes(statusTone(item.status)));
  const quality = [...(viewModel.metrology ?? []), ...(viewModel.qualification ?? [])];
  const route: BuildabilityPathStep[] = [];

  route.push({
    title: available.length ? `Begin with ${firstNames(available)}` : `Establish local integration for ${product}`,
    summary: available.length
      ? `Use the mapped local base around ${firstNames(available, 3)} while keeping the initial product boundary narrow.`
      : `Start with assembly, controls integration and inspection around ${product}; the map does not yet prove a fully local subsystem base.`,
    action: "BUILD", order: 1, status: available[0]?.status || "UNKNOWN", statusLabel: available[0]?.statusLabel || "Unknown",
  });
  if (constrained.length) route.push({
    title: `Source ${firstNames(constrained)} initially`,
    summary: `Keep ${firstNames(constrained, 3)} outside the first localization boundary while local integration and testing mature.`,
    action: "IMPORT", order: route.length + 1, status: constrained[0].status, statusLabel: constrained[0].statusLabel,
  });
  route.push({
    title: quality.length ? `Integrate and qualify with ${firstNames(quality)}` : `Create an integration and acceptance test for ${product}`,
    summary: quality.length
      ? `Build the assembly, inspection and validation route around ${firstNames(quality, 3)} before claiming production readiness.`
      : "Define product-specific inspection, acceptance and qualification gates; these are not yet separated in the mapped record.",
    action: "QUALIFY", order: route.length + 1, status: quality[0]?.status || "UNKNOWN", statusLabel: quality[0]?.statusLabel || "Unknown",
  });
  return route.slice(0, 6);
}

export function BuildPathSurface({
  viewModel,
  objective,
  addedItems = [],
  onStepSelect,
  onItemSelect,
  onRemoveAddedItem,
}: BuildPathSurfaceProps) {
  const steps = specificBuildPath(viewModel);
  const typedRequirements = [
    ...(viewModel.majorSystems ?? []), ...(viewModel.components ?? []), ...(viewModel.processes ?? []),
    ...(viewModel.equipment ?? []), ...(viewModel.materials ?? []), ...(viewModel.capabilities ?? []),
  ];
  const explicitImports = (viewModel.imports ?? []).filter((item) => safeTitle(item).toLowerCase() !== "mapped requirement");
  const imports = explicitImports.length
    ? explicitImports
    : typedRequirements.filter((item) => ["partial", "missing"].includes(statusTone(item.status))).slice(0, 7);
  const laterCapabilities = [...(viewModel.metrology ?? []), ...(viewModel.qualification ?? []), ...(viewModel.equipment ?? [])]
    .filter((item) => statusTone(item.status) !== "available")
    .slice(0, 6);

  return (
    <section className="fip-build" aria-labelledby="fip-build-title">
      <header className="fip-mode-intro">
        <p className="fip-eyebrow">Build</p>
        <h1 id="fip-build-title">How could I start making this?</h1>
        <p>{safeCopy(objective, `A first-order localization path for ${cleanDisplayText(viewModel.title, "this product")}.`)}</p>
      </header>

      <div className="fip-build__grid">
        <section className="fip-surface fip-build__path" aria-labelledby="fip-path-title">
          <header className="fip-section-head">
            <div>
              <p className="fip-eyebrow">Staged pathway</p>
              <h2 id="fip-path-title">Start practical. Localize selectively.</h2>
            </div>
          </header>
          {steps.length ? (
            <ol className="fip-path-list">
              {steps.map((step, index) => (
                <li key={keyFor(step, index)}>
                  <button onClick={() => onStepSelect?.(step)} type="button">
                    <span className="fip-path-list__number">{String(step.order || index + 1).padStart(2, "0")}</span>
                    <span className="fip-path-list__copy">
                      <strong>{safeTitle(step)}</strong>
                      <small>{safeCopy(step.summary || step.note, "No more specific action is mapped for this stage.")}</small>
                    </span>
                    <Status compact item={step} />
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <Empty>A product-specific localization path is not mapped yet.</Empty>
          )}
        </section>

        <aside className="fip-build__rail">
          <section className="fip-surface fip-build__boundary">
            <p className="fip-eyebrow">Initial sourcing boundary</p>
            <h2>Likely imported or unresolved first</h2>
            {imports.length ? (
              <div className="fip-compact-list">
                {imports.slice(0, 7).map((item, index) => (
                  <button key={keyFor(item, index)} onClick={() => onItemSelect?.(item)} type="button">
                    <span>{safeTitle(item)}</span>
                    <Status compact item={item} />
                  </button>
                ))}
              </div>
            ) : (
              <Empty>No explicit import boundary is recorded. This does not prove full local availability.</Empty>
            )}
          </section>

          {(viewModel.frontierQuestions ?? []).length ? (
            <section className="fip-surface fip-build__boundary fip-build__questions">
              <p className="fip-eyebrow">Questions to verify</p>
              <h2>Before committing the route</h2>
              <ul>
                {(viewModel.frontierQuestions ?? []).slice(0, 5).map((item, index) => (
                  <li key={`${item.question}-${index}`}>{safeCopy(item.question, "Verify the mapped requirement.")}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="fip-surface fip-build__boundary">
            <p className="fip-eyebrow">Develop later</p>
            <h2>Harder enabling capabilities</h2>
            {laterCapabilities.length ? (
              <div className="fip-compact-list">
                {laterCapabilities.map((item, index) => (
                  <button key={keyFor(item, index)} onClick={() => onItemSelect?.(item)} type="button">
                    <span>{safeTitle(item)}</span>
                    <Status compact item={item} />
                  </button>
                ))}
              </div>
            ) : (
              <Empty>No later-stage enabling capability has been separated from the mapped path.</Empty>
            )}
          </section>

          {addedItems.length ? (
            <section className="fip-surface fip-build__boundary">
              <p className="fip-eyebrow">Your working path</p>
              <h2>Added from WHY</h2>
              <div className="fip-compact-list">
                {addedItems.map((item, index) => (
                  <button key={keyFor(item, index)} onClick={() => onRemoveAddedItem?.(item)} type="button">
                    <span>{safeTitle(item)}</span>
                    <small>Remove</small>
                  </button>
                ))}
              </div>
            </section>
          ) : null}
        </aside>
      </div>

      <p className="fip-caveat">This is a first-order manufacturing path. It does not establish exact cost, schedule, supplier qualification, facility capacity or production feasibility.</p>
    </section>
  );
}

interface RelationshipSectionProps {
  title: string;
  description: string;
  items: BuildabilityItem[];
  onItemSelect?: (item: BuildabilityItem) => void;
}

function RelationshipSection({ title, description, items, onItemSelect }: RelationshipSectionProps) {
  if (!items.length) return null;
  return (
    <section className="fip-relationship">
      <header>
        <h3>{title}</h3>
        <p>{description}</p>
      </header>
      <div className="fip-relationship__items">
          {items.slice(0, 10).map((item, index) => (
            <button key={keyFor(item, index)} onClick={() => onItemSelect?.(item)} type="button">
              <span>{safeTitle(item)}</span>
              <Status compact item={item} />
            </button>
          ))}
      </div>
    </section>
  );
}

export interface DiscoverSurfaceProps {
  viewModel?: BuildabilityViewModel | null;
  domains: BuildabilityDomain[];
  activeDomainId?: string | null;
  query?: string;
  domainItems?: BuildabilityItem[];
  onQueryChange?: (query: string) => void;
  onSearch?: (query: string) => void;
  onDomainSelect?: (domain: BuildabilityDomain) => void;
  onItemSelect?: (item: BuildabilityItem) => void;
}

export function DiscoverSurface({
  viewModel,
  domains,
  activeDomainId,
  query = "",
  domainItems = [],
  onQueryChange,
  onSearch,
  onDomainSelect,
  onItemSelect,
}: DiscoverSurfaceProps) {
  const [localQuery, setLocalQuery] = useState(query);

  useEffect(() => setLocalQuery(query), [query]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const next = localQuery.trim();
    if (next) onSearch?.(next);
  }

  function changeQuery(value: string) {
    setLocalQuery(value);
    onQueryChange?.(value);
  }

  const families = viewModel?.related ?? [];

  return (
    <section className="fip-discover" aria-labelledby="fip-discover-title">
      <header className="fip-mode-intro fip-mode-intro--discover">
        <p className="fip-eyebrow">Discover</p>
        <h1 id="fip-discover-title">Explore the industrial capability universe</h1>
        <p>Move from products to their upstream requirements, adjacent families and downstream possibilities.</p>
        <form className="fip-discover-search" onSubmit={submit}>
          <label className="fip-visually-hidden" htmlFor="fip-discover-query">Search products and capabilities</label>
          <input
            id="fip-discover-query"
            onChange={(event) => changeQuery(event.target.value)}
            placeholder="Search products, machines, processes or materials"
            type="search"
            value={localQuery}
          />
          <button className="fip-button" type="submit">Explore</button>
        </form>
      </header>

      <section className="fip-surface fip-domain-section" aria-labelledby="fip-domains-title">
        <header className="fip-section-head">
          <div>
            <p className="fip-eyebrow">12 domains</p>
            <h2 id="fip-domains-title">Browse by industrial domain</h2>
          </div>
          <p className="fip-section-note">The domains share one connected industrial graph.</p>
        </header>
        <div className="fip-domain-grid">
          {domains.map((domain, index) => (
            <button
              aria-pressed={activeDomainId === domain.id}
              className={activeDomainId === domain.id ? "is-active" : ""}
              key={domain.id}
              onClick={() => onDomainSelect?.(domain)}
              type="button"
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{cleanDisplayText(domain.shortName || domain.name, `Domain ${index + 1}`)}</strong>
              <small>{`Products, processes and capabilities across ${cleanDisplayText(domain.shortName || domain.name, "this industrial domain")}.`}</small>
              {typeof domain.recordCount === "number" ? <em>{domain.recordCount.toLocaleString("en-IN")} mapped</em> : null}
            </button>
          ))}
        </div>
        {activeDomainId ? (
          <div className="fip-domain-results">
            <header>
              <h3>Selected domain</h3>
              <p>Representative mapped products and capabilities. Choose one to analyze its industrial route.</p>
            </header>
            {domainItems.length ? (
              <div>
                {domainItems.slice(0, 12).map((item, index) => (
                  <button key={keyFor(item, index)} onClick={() => onItemSelect?.(item)} type="button">
                    <strong>{safeTitle(item)}</strong>
                    {displayItemQualifier(item) ? <span>{displayItemQualifier(item)}</span> : null}
                    <small>{safeCopy(item.summary, item.kind || "Mapped industrial record")}</small>
                    <Status compact item={item} />
                  </button>
                ))}
              </div>
            ) : <Empty>Loading representative records for this domain…</Empty>}
          </div>
        ) : null}
      </section>

      {viewModel ? (
        <section className="fip-surface fip-discover-context" aria-labelledby="fip-context-title">
          <header className="fip-section-head">
            <div>
              <p className="fip-eyebrow">Current context</p>
              <h2 id="fip-context-title">{cleanDisplayText(viewModel.title, "Selected industrial product")}</h2>
              {viewModel.qualifier ? <span className="fip-public-qualifier">{cleanDisplayText(viewModel.qualifier, "")}</span> : null}
            </div>
            <p className="fip-section-note">{safeCopy(viewModel.plainSummary, "Explore the mapped industrial relationships around this product.")}</p>
          </header>

          {families.length ? (
            <div className="fip-family-row" aria-label="Related families">
              {families.slice(0, 8).map((item, index) => (
                <button key={keyFor(item, index)} onClick={() => onItemSelect?.(item)} type="button">{safeTitle(item)}</button>
              ))}
            </div>
          ) : null}

          <div className="fip-relationship-grid">
            <RelationshipSection description="Capabilities and inputs this product relies on." items={viewModel.upstream ?? []} onItemSelect={onItemSelect} title="Depends on" />
            <RelationshipSection description="Products and systems that use this capability." items={viewModel.downstream ?? []} onItemSelect={onItemSelect} title="Used by" />
            <RelationshipSection description="Industrial possibilities opened by mastering it." items={viewModel.unlocks ?? []} onItemSelect={onItemSelect} title="What this unlocks" />
            <RelationshipSection description="Nearby products, processes and capabilities." items={viewModel.related ?? []} onItemSelect={onItemSelect} title="Related" />
          </div>
        </section>
      ) : (
        <section className="fip-surface fip-discover-context">
          <Empty>Choose a domain or search for an industrial product to explore its connected capability world.</Empty>
        </section>
      )}
    </section>
  );
}

/** Product-workbench naming aliases retained at the composition boundary. */
export const WhyInspector = WhyDrawer;
export const BuildPath = BuildPathSurface;
export type WhyInspectorProps = WhyDrawerProps;
export type BuildPathProps = BuildPathSurfaceProps;
