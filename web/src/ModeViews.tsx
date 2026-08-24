import { useId, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type {
  CapabilityRecord,
  ObjectiveConfig,
  PackDetail,
  ProductMode,
  Selection,
  SolveResponse,
  WorldNode,
  WorldSlice,
} from "./types";
import VerdictView from "./views/VerdictView";
import StrataView from "./views/StrataView";
import TimeView from "./views/TimeView";
import StressView from "./views/StressView";
import FrontierView from "./views/FrontierView";
import WorldPlane from "./WorldPlane";
import { epistemicChipClass, epistemicLabel, epistemicTone } from "./epistemics";

type AnalyzeLens = "plane" | "verdict" | "strata" | "time" | "stress" | "frontier";

interface ModeViewsProps {
  mode: ProductMode;
  cfg: ObjectiveConfig;
  resp: SolveResponse | null;
  baseResp: SolveResponse | null;
  world: WorldSlice | null;
  worldSource: string;
  packDetail: PackDetail | null;
  capabilities: CapabilityRecord[] | null;
  selectedWorldNode: WorldNode | null;
  onSelect: (selection: Selection) => void;
  onSelectWorld: (node: WorldNode) => void;
  onVariant: (variantId: string) => void;
}

export default function ModeViews(props: ModeViewsProps) {
  const { mode } = props;
  if (mode === "ANALYZE") return <AnalyzeMode {...props} />;
  if (mode === "DESIGN") return <DesignMode {...props} />;
  if (mode === "EXECUTE") return <ExecuteMode {...props} />;
  if (mode === "DISCOVER") return <DiscoverMode {...props} />;
  return <LearnMode {...props} />;
}

function AnalyzeMode({
  cfg,
  resp,
  baseResp,
  world,
  worldSource,
  selectedWorldNode,
  onSelect,
  onSelectWorld,
}: ModeViewsProps) {
  const [lens, setLens] = useState<AnalyzeLens>("plane");
  const blockers = resp?.result.binding_summary ?? [];
  const unknowns = resp?.result.blocking_unknowns ?? [];
  return (
    <div className="mode-view analyze-view">
      <ModeHeader
        mode="ANALYZE"
        question="Can this physical future happen?"
        detail="The solver, world slice, and proof graph stay in one debugger surface. Select a node to keep WHY in the inspector."
      />
      <div className="metric-strip" aria-label="Analyze summary">
        <Metric label="VERDICT" value={resp ? resp.result.result_class.replace(/_/g, " ") : "UNKNOWN"} tone={resp ? resultTone(resp.result.result_class) : "unknown"} />
        <Metric label="BLOCKERS" value={resp ? String(blockers.length) : "UNKNOWN"} detail={blockers[0] ?? "causal blockers not returned"} tone={blockers.length ? "binding" : "neutral"} />
        <Metric label="UNKNOWN" value={resp ? String(unknowns.length) : "UNKNOWN"} detail={unknowns[0] ?? "decision-sensitive unknowns not returned"} tone={unknowns.length ? "unknown" : "neutral"} />
        <Metric label="DVA" value={resp ? `${(resp.dva.fraction * 100).toFixed(1)}%` : "UNKNOWN"} detail="accounting result · not a supply verdict" tone="evidence" />
      </div>
      <WorldPlane world={world} selectedId={selectedWorldNode?.id} onSelect={onSelectWorld} sourceLabel={worldSource} title="Analyze the industrial world" />
      <LensBar value={lens} onChange={setLens} />
      <div className="analyze-lens-wrap">
        {lens === "plane" && <AnalyzePrompt blockers={blockers} unknowns={unknowns} resp={resp} />}
        {lens === "verdict" && (resp ? <VerdictView resp={resp} onSelect={onSelect} /> : <UnknownPanel title="Verdict unavailable" detail="Run compilation to populate the adjudication lens." />)}
        {lens === "strata" && (resp ? <StrataView resp={resp} onSelect={onSelect} /> : <UnknownPanel title="Dependency strata unavailable" detail="No solve response has been returned." />)}
        {lens === "time" && (resp ? <TimeView resp={resp} onSelect={onSelect} /> : <UnknownPanel title="Physical clock unavailable" detail="No capacity envelope has been returned." />)}
        {lens === "stress" && (resp ? <StressView resp={resp} base={baseResp} onSelect={onSelect} /> : <UnknownPanel title="Stress lab unavailable" detail="No scenario branch has been solved." />)}
        {lens === "frontier" && (resp ? <FrontierView resp={resp} onSelect={onSelect} /> : <UnknownPanel title="Frontier unavailable" detail="No re-solved frontier has been returned." />)}
      </div>
    </div>
  );
}

function DesignMode({
  cfg,
  resp,
  world,
  worldSource,
  packDetail,
  selectedWorldNode,
  onSelect,
  onSelectWorld,
  onVariant,
}: ModeViewsProps) {
  const variants = packDetail?.variants ?? [];
  const activeId = cfg.variantId || resp?.selected_variant || "";
  const active = variants.find((variant) => variant.id === activeId) ?? null;
  return (
    <div className="mode-view design-view">
      <ModeHeader
        mode="DESIGN"
        question="What architecture should we choose given industrial reality?"
        detail="Variants and substitutions are shown as graph edits only when the pack provides those records. Nothing here claims a redesign has been approved or qualified."
      />
      <WorldPlane world={world} selectedId={selectedWorldNode?.id} onSelect={onSelectWorld} sourceLabel={worldSource} title="Design dependency plane" />
      <section className="design-grid">
        <div className="card architecture-panel">
          <div className="section-heading-row">
            <div><span className="eyebrow">REFERENCE ARCHITECTURES</span><h3>Choose a branch to re-solve</h3></div>
            <span className="chip">{variants.length ? `${variants.length} returned` : "UNKNOWN"}</span>
          </div>
          {variants.length === 0 ? <UnknownPanel title="No architecture variants returned" detail="Design choice is UNKNOWN for this pack; the current solve input remains unchanged." compact /> : (
            <div className="architecture-list">
              {variants.map((variant) => {
                const isActive = variant.id === activeId;
                return (
                  <div key={variant.id} className={`architecture-card${isActive ? " is-active" : ""}`}>
                    <div className="architecture-card-top">
                      <div><span className="architecture-id">{variant.id}</span><h4>{variant.name}</h4></div>
                      <span className={`chip ${isActive ? "ok" : ""}`}>{isActive ? "CURRENT INPUT" : "ALTERNATIVE"}</span>
                    </div>
                    <p>{variant.notes || "No variant note returned — rationale UNKNOWN."}</p>
                    <div className="architecture-evidence">{variant.anchor_evidence.length ? `${variant.anchor_evidence.length} anchor evidence record${variant.anchor_evidence.length === 1 ? "" : "s"}` : "anchor evidence UNKNOWN"}</div>
                    {!isActive && <button type="button" className="btn" onClick={() => onVariant(variant.id)}>Use as scenario branch</button>}
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <div className="card substitution-panel">
          <div className="section-heading-row">
            <div><span className="eyebrow">GRAPH DIFF</span><h3>Substitutions in this pack</h3></div>
            <span className="chip">{packDetail?.substitutions.length ?? 0} candidates</span>
          </div>
          {(packDetail?.substitutions ?? []).length === 0 ? <UnknownPanel title="Substitution graph unavailable" detail="No substitution records are available for this pack." compact /> : (
            <div className="substitution-list">
              {packDetail!.substitutions.map((substitution) => (
                <div className="substitution-card" key={substitution.id}>
                  <div className="substitution-flow"><span>{substitution.replaces_part}</span><b>→</b><strong>{substitution.name}</strong></div>
                  <div className="substitution-meta"><span className="chip warn">{substitution.maturity || "MATURITY UNKNOWN"}</span><span className="small">candidate only · not applied to this run</span></div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
      {active && variants.length > 1 && <VariantDiff active={active} alternatives={variants.filter((variant) => variant.id !== active.id)} />}
    </div>
  );
}

function VariantDiff({ active, alternatives }: { active: PackDetail["variants"][number]; alternatives: PackDetail["variants"] }) {
  const activeBom = new Map((active.bom ?? []).map((part) => [part.part, part.qty]));
  return (
    <section className="card variant-diff">
      <div className="section-heading-row"><div><span className="eyebrow">TOP-LEVEL BOM DIFF</span><h3>Current architecture: {active.name}</h3></div><span className="small">top-level BOM fields only; nested deltas remain UNKNOWN</span></div>
      {active.bom?.length ? alternatives.map((variant) => {
        const otherBom = new Map((variant.bom ?? []).map((part) => [part.part, part.qty]));
        const added = [...otherBom.keys()].filter((part) => !activeBom.has(part));
        const removed = [...activeBom.keys()].filter((part) => !otherBom.has(part));
        const changed = [...otherBom.keys()]
          .filter((part) => activeBom.has(part) && activeBom.get(part) !== otherBom.get(part))
          .map((part) => `${part}: ${activeBom.get(part)} → ${otherBom.get(part)}`);
        return (
          <div key={variant.id} className="diff-row">
            <div className="diff-label"><strong>{variant.name}</strong><span className="small">{variant.id}</span></div>
            <div className="diff-values">
              <DiffValue label="added" values={added} tone="add" />
              <DiffValue label="removed" values={removed} tone="remove" />
              <DiffValue label="qty changed" values={changed} tone="change" />
              {!added.length && !removed.length && !changed.length && <span className="small">No BOM delta returned.</span>}
            </div>
          </div>
        );
      }) : <UnknownPanel title="BOM graph diff UNKNOWN" detail="This pack returned variants without BOM fields; no dependency rewrite is inferred." compact />}
    </section>
  );
}

function DiffValue({ label, values, tone }: { label: string; values: string[]; tone: "add" | "remove" | "change" }) {
  return <span className={`diff-value diff-${tone}`}><b>{label}</b>{values.length ? values.slice(0, 4).join(", ") : "—"}</span>;
}

function ExecuteMode({ resp, onSelect, cfg }: ModeViewsProps) {
  const actions = resp?.actions ?? [];
  const timeline = resp?.plan.timeline ?? [];
  const gates = actions.filter((action) => action.kind.toUpperCase().includes("QUALIFY"));
  const evidenceTasks = resp?.voi ?? [];
  return (
    <div className="mode-view execute-view">
      <ModeHeader mode="EXECUTE" question="We decided to build it. What is the next auditable work?" detail="This view surfaces solver-returned transformations, qualification gates, evidence tasks, and the physical clock. It does not mark approvals or vendor decisions." />
      <div className="metric-strip" aria-label="Execution summary">
        <Metric label="ACTIONS" value={resp ? String(actions.length) : "UNKNOWN"} detail="returned by the transformation planner" tone={actions.length ? "evidence" : "unknown"} />
        <Metric label="QUALIFICATION" value={resp ? String(gates.length) : "UNKNOWN"} detail={gates.length ? "explicit gates" : "no gate records returned"} tone={gates.length ? "binding" : "unknown"} />
        <Metric label="EVIDENCE TASKS" value={resp ? String(evidenceTasks.length) : "UNKNOWN"} detail="value-of-information queue" tone={evidenceTasks.length ? "unknown" : "neutral"} />
        <Metric label="DEADLINE" value={String(cfg.deadlineYear)} detail="scenario input, not a decision date" tone="evidence" />
      </div>
      <section className="card execute-plan-card">
        <div className="section-heading-row"><div><span className="eyebrow">TRANSFORMATION PLAN</span><h3>Sequenced work on the physical clock</h3></div><span className="chip">{resp?.plan.verified_result_class?.replace(/_/g, " ") ?? "UNKNOWN"}</span></div>
        {timeline.length === 0 ? <UnknownPanel title="No timeline returned" detail="Lead-time sequencing is UNKNOWN for this run." compact /> : <TimelineRows timeline={timeline} />}
      </section>
      <div className="execute-columns">
        <WorkQueue title="Qualification gates" eyebrow="QUALITY / ACCEPTANCE" empty="No explicit qualification gates returned; do not infer approval." items={gates.map((action) => ({ id: action.action_id, label: action.label, detail: `${action.kind} · ${action.rationale}`, selection: { kind: "action" as const, id: action.action_id } }))} onSelect={onSelect} />
        <WorkQueue title="Evidence tasks" eyebrow="RESEARCH / VOI" empty="No evidence tasks returned. Unknown status is preserved in the Inspector." items={evidenceTasks.map((task) => ({ id: task.unknown_id, label: task.unknown_id, detail: task.description, selection: { kind: "item" as const, id: task.unknown_id } }))} onSelect={onSelect} />
      </div>
      <section className="card action-list-card">
        <div className="section-heading-row"><div><span className="eyebrow">ACTION REGISTER</span><h3>Planner outputs</h3></div><span className="small">Click an action to inspect its rationale and evidence chain.</span></div>
        {actions.length === 0 ? <UnknownPanel title="Action register unavailable" detail="No transformations were returned by the active run." compact /> : actions.map((action) => <button className="action-row" type="button" key={action.action_id} onClick={() => onSelect({ kind: "action", id: action.action_id })}><span className="action-kind">{action.kind}</span><span className="action-label"><strong>{action.label}</strong><small>{action.rationale}</small></span><span className="action-capex">{action.capex_usd > 0 ? `$${formatCompact(action.capex_usd)}` : "CAPEX UNKNOWN"}</span></button>)}
      </section>
    </div>
  );
}

function TimelineRows({ timeline }: { timeline: SolveResponse["plan"]["timeline"] }) {
  const min = Math.min(...timeline.map((row) => row.start_year));
  const max = Math.max(...timeline.map((row) => row.online_latest), min + 1);
  const span = max - min;
  return <div className="timeline-rows">{timeline.map((row) => { const left = ((row.start_year - min) / span) * 100; const width = Math.max(4, ((row.online_latest - row.start_year) / span) * 100); return <div className="timeline-row" key={row.action}><div className="timeline-label"><strong>{row.kind}</strong><span>{row.action}</span></div><div className="timeline-track" aria-label={`${row.action}: starts ${row.start_year}, online ${row.online_earliest} to ${row.online_latest}`}><div className="timeline-bar" style={{ left: `${left}%`, width: `${width}%` }}><span>{row.online_earliest}–{row.online_latest}</span></div></div></div>; })}<div className="timeline-axis"><span>{min}</span><span>{max}</span></div></div>;
}

function WorkQueue({ title, eyebrow, empty, items, onSelect }: { title: string; eyebrow: string; empty: string; items: { id: string; label: string; detail: string; selection: Selection }[]; onSelect: (selection: Selection) => void }) {
  return <section className="card work-queue"><div className="section-heading-row"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div><span className="chip">{items.length || "UNKNOWN"}</span></div>{items.length === 0 ? <UnknownPanel title="Queue empty" detail={empty} compact /> : <div className="queue-items">{items.slice(0, 10).map((item) => <button type="button" className="queue-item" key={item.id} onClick={() => onSelect(item.selection)}><span className="queue-index">↳</span><span><strong>{item.label}</strong><small>{item.detail}</small></span></button>)}</div>}</section>;
}

function DiscoverMode({ capabilities, onSelect }: ModeViewsProps) {
  return (
    <div className="mode-view discover-view">
      <ModeHeader mode="DISCOVER" question="What should this industrial system become good at?" detail="Discovery starts with canonical capability reuse across checked-in packs. This alpha does not yet claim a calculated option-value or unlock ranking." />
      {capabilities === null ? <UnknownPanel title="Canonical capability registry unavailable" detail="GET /api/world/capabilities did not return a usable response. No option-value ranking is fabricated." /> : capabilities.length === 0 ? <UnknownPanel title="No capability records returned" detail="The registry answered without capability records. Cross-sector reuse and option value remain UNKNOWN." /> : (
        <section className="capability-grid" aria-label="Canonical capabilities">
          {capabilities.map((capability) => <CapabilityCard key={capability.id} capability={capability} onSelect={onSelect} />)}
        </section>
      )}
      {capabilities !== null && capabilities.length > 0 && <div className="discover-note"><span className="chip ok">CANONICAL REUSE MAP</span><span>A mapping is an explicit ontology link. It is not evidence of supply, readiness, qualification, capacity, or economic option value.</span></div>}
    </div>
  );
}

function CapabilityCard({ capability, onSelect }: { capability: CapabilityRecord; onSelect: (selection: Selection) => void }) {
  return <article className="capability-card"><div className="capability-card-top"><span className="eyebrow">{capability.kind}</span><span className={`chip ${epistemicChipClass(capability.epistemic_class)}`}>{epistemicLabel(capability.epistemic_class)}</span></div><h3>{capability.name}</h3><p className="canonical-id">{capability.canonical_id ?? capability.id}</p><div className="capability-facts"><span><b>mapped packs</b>{capability.mapped_pack_ids.length}</span><span><b>entity mappings</b>{capability.mapping_count}</span><span><b>attached evidence</b>{capability.evidence_ids.length}</span></div><div className="unlock-block"><span className="eyebrow">MAPPED PACK REUSE</span>{capability.mapped_pack_ids.length ? <div>{capability.mapped_pack_ids.map((packId) => <span className="unlock-chip" key={packId}>{packId}</span>)}</div> : <span className="small">No pack mappings declared.</span>}{capability.evidence_task_ids.length > 0 && <span className="small">{capability.evidence_task_ids.length} open evidence task{capability.evidence_task_ids.length === 1 ? "" : "s"}</span>}<button type="button" className="evidence-link capability-inspect" onClick={() => onSelect({ kind: "capability", id: capability.id })}>Inspect canonical record →</button></div></article>;
}

function LearnMode({ world, worldSource, selectedWorldNode, onSelectWorld, onSelect }: ModeViewsProps) {
  return <div className="mode-view learn-view"><ModeHeader mode="LEARN" question="What should I understand next, and why does it matter?" detail="Learning follows the selected world node from intuition to mechanism to expert detail. Stored text and evidence are shown; missing layers remain UNKNOWN." />{selectedWorldNode ? <LearnNode node={selectedWorldNode} onSelect={onSelect} /> : <div className="learn-select-state"><WorldPlane world={world} selectedId={undefined} onSelect={onSelectWorld} sourceLabel={worldSource} title="Select a node to learn" /><div className="card learn-empty"><span className="eyebrow">WHY</span><h3>Select any node in the plane.</h3><p>The explanation depth will follow the node's own evidence and metadata. No generic explanation is substituted for missing industrial knowledge.</p></div></div>}</div>;
}

function LearnNode({ node, onSelect }: { node: WorldNode; onSelect: (selection: Selection) => void }) {
  const [depth, setDepth] = useState<"WHY" | "MECHANISM" | "EXPERT">("WHY");
  const tabs = ["WHY", "MECHANISM", "EXPERT"] as const;
  const tabPrefix = `learn-depth-${useId().replace(/:/g, "")}`;
  const text = metadataText(node.metadata, depth);
  const why = metadataText(node.metadata, "WHY");
  const tone = epistemicTone(node.epistemic_class);
  return (
    <section className="learn-node">
      <div className="learn-node-head">
        <div>
          <span className="eyebrow">LEARNING NODE · {node.kind}</span>
          <h2>{node.name}</h2>
          <p>{node.canonical_id ?? node.id} · <span className={`status-text status-${tone}`}>{epistemicLabel(node.epistemic_class)}</span></p>
        </div>
        <span className={`chip ${node.evidence_ids.length ? "reported" : "unknown"}`}>{node.evidence_ids.length ? `${node.evidence_ids.length} evidence records` : "evidence UNKNOWN"}</span>
      </div>
      <div className="learn-tabs" role="tablist" aria-label="Explanation depth">
        {tabs.map((item, index) => (
          <button
            type="button"
            role="tab"
            id={`${tabPrefix}-tab-${item.toLowerCase()}`}
            aria-controls={`${tabPrefix}-panel`}
            aria-selected={depth === item}
            tabIndex={depth === item ? 0 : -1}
            className={depth === item ? "active" : ""}
            onClick={() => setDepth(item)}
            onKeyDown={(event) => {
              let nextIndex = index;
              if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
              else if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
              else if (event.key === "Home") nextIndex = 0;
              else if (event.key === "End") nextIndex = tabs.length - 1;
              else return;
              event.preventDefault();
              const next = tabs[nextIndex];
              setDepth(next);
              document.getElementById(`${tabPrefix}-tab-${next.toLowerCase()}`)?.focus();
            }}
            key={item}
          >
            {item}
          </button>
        ))}
      </div>
      <div id={`${tabPrefix}-panel`} role="tabpanel" aria-labelledby={`${tabPrefix}-tab-${depth.toLowerCase()}`} className="learn-content">
        <div className="learn-primary"><span className="eyebrow">{depth}</span><p>{text}</p></div>
        <aside className="learn-why"><span className="eyebrow">PERSISTENT WHY</span><p>{why}</p></aside>
      </div>
      {node.evidence_ids.length > 0
        ? <div className="learn-evidence"><span className="eyebrow">EVIDENCE TO INSPECT</span>{node.evidence_ids.map((id) => <button type="button" className="evidence-link" onClick={() => onSelect({ kind: "evidence", id })} key={id}>{id} ↗</button>)}</div>
        : <div className="learn-evidence"><span className="chip unknown">UNKNOWN · no evidence ids returned</span></div>}
    </section>
  );
}

function metadataText(metadata: Record<string, unknown>, depth: "WHY" | "MECHANISM" | "EXPERT"): string {
  const keys: Record<typeof depth, string[]> = { WHY: ["why", "explanation", "summary", "description"], MECHANISM: ["mechanism", "how", "physical_principle"], EXPERT: ["expert", "technical_detail", "specification", "notes"] };
  for (const key of keys[depth]) if (typeof metadata[key] === "string" && metadata[key]) return metadata[key] as string;
  return "UNKNOWN — this explanation layer was not returned by the registry. Inspect the evidence chain before making an inference.";
}

function AnalyzePrompt({ blockers, unknowns, resp }: { blockers: string[]; unknowns: string[]; resp: SolveResponse | null }) {
  return <section className="card analyze-prompt"><div className="section-heading-row"><div><span className="eyebrow">WHY THIS RUN LOOKS THIS WAY</span><h3>Start with the causal chain</h3></div><span className="chip">{resp ? "SOLVED STATE" : "AWAITING RUN"}</span></div><div className="why-grid"><div><span className="eyebrow">BLOCKERS</span>{blockers.length ? blockers.slice(0, 5).map((item) => <div className="why-item" key={item}><span className="node-status-dot node-status-conflicted" aria-hidden="true" />{item}</div>) : <p className="small">No binding summary returned.</p>}</div><div><span className="eyebrow">UNKNOWN THAT COULD FLIP THE ANSWER</span>{unknowns.length ? unknowns.slice(0, 5).map((item) => <div className="why-item" key={item}><span className="node-status-dot node-status-unknown" aria-hidden="true" />{item}</div>) : <p className="small">No blocking unknowns returned.</p>}</div></div><p className="small analyze-prompt-foot">Select a plane node, an existing lens, or a blocker to keep the proof chain in view.</p></section>;
}

function ModeHeader({ mode, question, detail }: { mode: ProductMode; question: string; detail: string }) {
  return <header className={`mode-header mode-header-${mode.toLowerCase()}`}><div><span className="eyebrow">FORGE {mode}</span><h2>{question}</h2><p>{detail}</p></div><span className="mode-glyph" aria-hidden="true">{mode.slice(0, 1)}</span></header>;
}

function Metric({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone: "evidence" | "binding" | "unknown" | "neutral" | "ok" }) {
  return <div className={`metric metric-${tone}`}><span className="eyebrow">{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>;
}

function LensBar({ value, onChange }: { value: AnalyzeLens; onChange: (value: AnalyzeLens) => void }) {
  const lenses: [AnalyzeLens, string][] = [["plane", "WORLD PLANE"], ["verdict", "VERDICT"], ["strata", "STRATA"], ["time", "TIME"], ["stress", "STRESS LAB"], ["frontier", "FRONTIER"]];
  return <nav className="lens-bar" aria-label="Analyze sub-lenses">{lenses.map(([id, label]) => <button type="button" key={id} className={value === id ? "active" : ""} aria-pressed={value === id} onClick={() => onChange(id)}>{label}</button>)}</nav>;
}

function UnknownPanel({ title, detail, compact = false }: { title: string; detail: string; compact?: boolean }) {
  return <div className={`unknown-panel${compact ? " compact" : ""}`} role="status"><span className="chip unknown">UNKNOWN</span><strong>{title}</strong><p>{detail}</p></div>;
}

function resultTone(result: string): "evidence" | "binding" | "unknown" | "neutral" | "ok" {
  if (result === "FEASIBLE") return "ok";
  if (result === "INFEASIBLE_UNDER_MODEL") return "binding";
  if (result === "NOT_ADJUDICABLE") return "unknown";
  return "evidence";
}

function formatCompact(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}k`;
  return value.toFixed(0);
}

export type { ModeViewsProps };
