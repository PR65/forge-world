import { FormEvent, useMemo } from "react";
import {
  BuildPath,
  DiscoverSurface,
  IndustrialDecomposition,
  WhyInspector,
} from "./index";
import type { WhySelection } from "./index";
import {
  cleanDisplayText,
  cleanNarrative,
  displayItemTitle,
  statusLabel,
  statusTone,
} from "../ui-rebuild/buildability-ui";
import type {
  BuildabilityBottleneck,
  BuildabilityDomain,
  BuildabilityItem,
  BuildabilityPathStep,
  BuildabilityViewModel,
} from "../ui-rebuild/buildability-types";
import "./product-workbench.css";

export type ProductMode = "ANALYZE" | "BUILD" | "DISCOVER";

export interface ProductResolutionNotice {
  quality: "strong" | "nearest" | "unresolved";
  message: string;
  productQuery?: string | null;
  candidates?: string[];
}

export interface ProductWorkbenchProps {
  mode: ProductMode;
  query: string;
  objectiveText?: string | null;
  viewModel: BuildabilityViewModel | null;
  domains: BuildabilityDomain[];
  activeDomainId?: string | null;
  domainItems?: BuildabilityItem[];
  loading?: boolean;
  error?: string | null;
  resolution?: ProductResolutionNotice | null;
  selection?: WhySelection | null;
  addedItems?: BuildabilityItem[];
  onModeChange: (mode: ProductMode) => void;
  onQueryChange: (query: string) => void;
  onAnalyze: (query: string) => void;
  onDomainSelect?: (domain: BuildabilityDomain) => void;
  onSelectionChange: (selection: WhySelection | null) => void;
  onAddToBuildPath?: (item: BuildabilityItem) => void;
  onRemoveAddedItem?: (item: BuildabilityItem) => void;
  onGoDeeper?: (item: BuildabilityItem) => void;
  onCandidateSelect?: (candidate: string) => void;
  onRetry?: () => void;
}

const MODES: ProductMode[] = ["ANALYZE", "BUILD", "DISCOVER"];

function verdict(viewModel: BuildabilityViewModel): string {
  const tone = statusTone(viewModel.buildability.rootStatus);
  const title = cleanDisplayText(viewModel.title, "this product").toLowerCase();
  if (tone === "available") {
    return `India appears broadly positioned to manufacture ${title}, while objective-specific scale and qualification still require validation.`;
  }
  if (tone === "partial") {
    return `India appears capable of substantial local manufacture, but important requirements remain partial, import-dependent or unresolved.`;
  }
  if (tone === "missing") {
    return `The current map indicates a serious capability gap in the route to manufacture ${title} in India.`;
  }
  if (tone === "conflicted") {
    return `The available India status signals conflict, so the manufacturing position cannot yet be stated confidently.`;
  }
  return `FORGE can map the first-order manufacturing structure, but India’s current position remains substantially unknown.`;
}

function productItem(viewModel: BuildabilityViewModel): BuildabilityItem {
  return {
    title: viewModel.title,
    summary: viewModel.plainSummary,
    kind: viewModel.kind,
    category: viewModel.category,
    status: viewModel.buildability.rootStatus,
    statusLabel: viewModel.buildability.rootStatusLabel,
    epistemicClass: viewModel.buildability.rootEpistemicClass,
  };
}

function SearchBox({
  query,
  label,
  compact = false,
  onQueryChange,
  onAnalyze,
}: {
  query: string;
  label: string;
  compact?: boolean;
  onQueryChange: (query: string) => void;
  onAnalyze: (query: string) => void;
}) {
  function submit(event: FormEvent) {
    event.preventDefault();
    if (query.trim()) onAnalyze(query);
  }
  return (
    <form className={`fip-workbench-search${compact ? " is-compact" : ""}`} onSubmit={submit}>
      <label htmlFor={compact ? "fip-global-query" : "fip-objective-query"}>{label}</label>
      <div>
        <input
          autoComplete="off"
          id={compact ? "fip-global-query" : "fip-objective-query"}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="100 five-axis CNC machines per year in India"
          type="search"
          value={query}
        />
        <button type="submit">{compact ? "Search" : "Analyze"}</button>
      </div>
    </form>
  );
}

function ResolutionNotice({
  notice,
  onCandidateSelect,
}: {
  notice: ProductResolutionNotice;
  onCandidateSelect?: (candidate: string) => void;
}) {
  return (
    <section className={`fip-resolution fip-resolution--${notice.quality}`} role="status">
      <div>
        <strong>{notice.quality === "nearest" ? "Closest useful match" : notice.quality === "unresolved" ? "Exact product not mapped" : "Objective resolved"}</strong>
        <p>{cleanNarrative(notice.message, "The product match needs review.")}</p>
      </div>
      {notice.candidates?.length ? (
        <div className="fip-resolution__candidates">
          {notice.candidates.slice(0, 5).map((candidate, index) => (
            <button key={`${candidate}-${index}`} onClick={() => onCandidateSelect?.(candidate)} type="button">
              {cleanDisplayText(candidate, "Related industrial family")}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function Bottlenecks({
  items,
  onSelect,
}: {
  items: BuildabilityBottleneck[];
  onSelect: (item: BuildabilityBottleneck) => void;
}) {
  return (
    <section className="fip-workbench-panel fip-bottlenecks" aria-labelledby="fip-bottlenecks-title">
      <header>
        <p>Decision focus</p>
        <h2 id="fip-bottlenecks-title">Most important bottlenecks</h2>
      </header>
      {items.length ? (
        <ol>
          {items.slice(0, 7).map((item, index) => (
            <li key={`${item.title}-${index}`}>
              <button onClick={() => onSelect(item)} type="button">
                <span>{String(item.rank || index + 1).padStart(2, "0")}</span>
                <span>
                  <strong>{displayItemTitle(item).replace(/\s+Capability Remains Unknown\.?$/i, "")}</strong>
                  <small>{cleanNarrative(item.reason || item.summary || item.note, "Click to inspect why this requirement matters.")}</small>
                </span>
                <em className={`is-${statusTone(item.status)}`}>{statusLabel(item.status, item.statusLabel)}</em>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="fip-workbench-empty">No ranked bottlenecks are mapped. This is limited data, not proof that the route has no bottlenecks.</p>
      )}
    </section>
  );
}

function AnalyzeSurface({
  query,
  objectiveText,
  viewModel,
  loading,
  error,
  resolution,
  onQueryChange,
  onAnalyze,
  onSelectionChange,
  onCandidateSelect,
  onRetry,
}: Pick<ProductWorkbenchProps,
  "query" | "objectiveText" | "viewModel" | "loading" | "error" | "resolution" |
  "onQueryChange" | "onAnalyze" | "onSelectionChange" | "onCandidateSelect" | "onRetry"
>) {
  return (
    <main className="fip-workbench-main" id="fip-main">
      <section className="fip-objective">
        <p className="fip-objective__eyebrow">Analyze</p>
        <h1>What do you want to build?</h1>
        <SearchBox label="Product or manufacturing objective" onAnalyze={onAnalyze} onQueryChange={onQueryChange} query={query} />
        <div className="fip-objective__examples">Try: industrial freeze dryer · 50 railway traction motors · five-axis CNC machining centre</div>
      </section>

      {resolution && resolution.quality !== "strong" ? <ResolutionNotice notice={resolution} onCandidateSelect={onCandidateSelect} /> : null}
      {error ? (
        <section className="fip-workbench-error" role="alert">
          <div><strong>FORGE could not resolve this objective safely.</strong><p>{error}</p></div>
          {onRetry ? <button onClick={onRetry} type="button">Try again</button> : null}
        </section>
      ) : null}

      {viewModel ? (
        <>
          <section className="fip-answer-head">
            <div className="fip-answer-head__title">
              <p>{cleanDisplayText(viewModel.domain, "Industrial product")}</p>
              <h2>{cleanDisplayText(viewModel.title, "Selected industrial product")}</h2>
              {objectiveText && objectiveText.trim().toLowerCase() !== viewModel.title.trim().toLowerCase() ? <small>Objective: {objectiveText}</small> : null}
            </div>
            <div className="fip-answer-head__verdict">
              <span className={`is-${statusTone(viewModel.buildability.rootStatus)}`} />
              <p>{verdict(viewModel)}</p>
              <small>Basis: {cleanDisplayText(viewModel.buildability.rootEpistemicClass, "UNKNOWN")} · first-order national capability map</small>
            </div>
          </section>

          <div className="fip-analyze-grid" aria-busy={loading || undefined}>
            <IndustrialDecomposition
              onItemSelect={(value) => onSelectionChange({ kind: "item", value })}
              onProductSelect={() => onSelectionChange({ kind: "item", value: productItem(viewModel) })}
              onRequirementGroupSelect={(value) => onSelectionChange({ kind: "item", value })}
              onSystemSelect={(value) => onSelectionChange({ kind: "item", value })}
              viewModel={viewModel}
            />
            <Bottlenecks
              items={viewModel.criticalBottlenecks ?? []}
              onSelect={(value) => onSelectionChange({ kind: "bottleneck", value })}
            />
          </div>
        </>
      ) : loading ? (
        <section className="fip-workbench-loading" role="status">Resolving the objective and composing its industrial map…</section>
      ) : null}
    </main>
  );
}

export default function ProductWorkbench(props: ProductWorkbenchProps) {
  const requirements = useMemo(() => {
    if (!props.viewModel) return [];
    return [
      ...(props.viewModel.components ?? []),
      ...(props.viewModel.processes ?? []),
      ...(props.viewModel.equipment ?? []),
      ...(props.viewModel.materials ?? []),
      ...(props.viewModel.metrology ?? []),
      ...(props.viewModel.qualification ?? []),
      ...(props.viewModel.capabilities ?? []),
    ].slice(0, 12);
  }, [props.viewModel]);

  const selectItem = (value: BuildabilityItem) => props.onSelectionChange({ kind: "item", value });
  const selectStep = (value: BuildabilityPathStep) => props.onSelectionChange({ kind: "path", value });

  return (
    <div className="fip-workbench">
      <a className="fip-skip" href="#fip-main">Skip to analysis</a>
      <header className="fip-workbench-topbar">
        <a className="fip-workbench-brand" href="/india" aria-label="FORGE India home">
          <span aria-hidden="true">⌾</span><strong>FORGE <em>INDIA</em></strong>
        </a>
        <nav aria-label="Product modes">
          {MODES.map((mode) => (
            <button aria-current={props.mode === mode ? "page" : undefined} key={mode} onClick={() => props.onModeChange(mode)} type="button">{mode}</button>
          ))}
        </nav>
        <SearchBox compact label="Search FORGE India" onAnalyze={props.onAnalyze} onQueryChange={props.onQueryChange} query={props.query} />
      </header>

      {props.mode === "ANALYZE" ? <AnalyzeSurface {...props} /> : null}
      {props.mode === "BUILD" && props.viewModel ? (
        <main className="fip-workbench-main" id="fip-main">
          <BuildPath
            addedItems={props.addedItems}
            objective={props.objectiveText}
            onItemSelect={selectItem}
            onRemoveAddedItem={props.onRemoveAddedItem}
            onStepSelect={selectStep}
            viewModel={props.viewModel}
          />
        </main>
      ) : null}
      {props.mode === "BUILD" && !props.viewModel ? (
        <main className="fip-workbench-main" id="fip-main">
          <section className="fip-workbench-loading">
            <strong>Resolve a product before opening a build path.</strong>
            <p>BUILD only sequences requirements attached to a confirmed atlas product; it will not invent a plan from a weak match.</p>
            <button onClick={() => props.onModeChange("ANALYZE")} type="button">Return to Analyze</button>
          </section>
        </main>
      ) : null}
      {props.mode === "DISCOVER" ? (
        <main className="fip-workbench-main" id="fip-main">
          <DiscoverSurface
            activeDomainId={props.activeDomainId}
            domainItems={props.domainItems}
            domains={props.domains}
            onDomainSelect={props.onDomainSelect}
            onItemSelect={selectItem}
            onQueryChange={props.onQueryChange}
            onSearch={props.onAnalyze}
            query={props.query}
            viewModel={props.viewModel}
          />
        </main>
      ) : null}

      <WhyInspector
        evidence={props.viewModel?.evidenceSummary}
        onAddToBuildPath={props.onAddToBuildPath}
        onClose={() => props.onSelectionChange(null)}
        onGoDeeper={props.onGoDeeper}
        open={Boolean(props.selection)}
        requirements={requirements}
        selection={props.selection ?? null}
      />
    </div>
  );
}
