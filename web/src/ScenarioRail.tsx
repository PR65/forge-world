import { useEffect, useState } from "react";
import type { ObjectiveConfig, PackDetail, SolveResponse } from "./types";

interface PackListItem {
  pack_id: string;
  title: string;
  variants: string[];
}

interface ScenarioRailProps {
  cfg: ObjectiveConfig;
  packList: PackListItem[];
  packLoading: boolean;
  packDetail: PackDetail | null;
  nlText: string;
  nlNote: string | null;
  busy: boolean;
  canRun: boolean;
  error: string | null;
  onNlTextChange: (value: string) => void;
  onConfigChange: (patch: Partial<ObjectiveConfig>) => void;
  onParse: () => void;
  onRun: () => void;
  onPreset: (patch: Partial<ObjectiveConfig>) => void;
}

export default function ScenarioRail({
  cfg,
  packList,
  packLoading,
  packDetail,
  nlText,
  nlNote,
  busy,
  canRun,
  error,
  onNlTextChange,
  onConfigChange,
  onParse,
  onRun,
  onPreset,
}: ScenarioRailProps) {
  const [annualDraft, setAnnualDraft] = useState(String(cfg.annualUnits));
  useEffect(() => setAnnualDraft(String(cfg.annualUnits)), [cfg.annualUnits]);
  const parsedAnnual = Number(annualDraft);
  const annualValid = annualDraft.trim() !== "" && Number.isFinite(parsedAnnual) && parsedAnnual > 0;
  const activeVariant = packDetail?.variants.find((variant) => variant.id === cfg.variantId);
  const isHumanoidPack = cfg.packId.toLowerCase().includes("humanoid");
  const hasReeShock = packDetail?.shocks.some((shock) => shock.id === "shk_cn_ree_minus80") ?? false;
  return (
    <aside className="scenario-rail" aria-label="Scenario controls">
      <div className="rail-intro">
        <span className="eyebrow">SCENARIO RAIL</span>
        <h1>Compile a physical future.</h1>
        <p>Every change below creates a new solve input. Baseline evidence stays visible while this branch is explored.</p>
      </div>

      <div className="rail-section">
        <div className="rail-section-label">Objective</div>
        <label className="field" htmlFor="objective-language">Describe it in plain language</label>
        <div className="parse-row">
          <input
            id="objective-language"
            name="objective-language"
            type="text"
            autoComplete="off"
            placeholder="e.g. “100 CNC machines by 2030”…"
            value={nlText}
            onChange={(event) => onNlTextChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onParse();
            }}
          />
          <button className="btn" type="button" onClick={onParse}>Parse</button>
        </div>
        {nlNote && <div className="parse-note" role="status">{nlNote}</div>}

        <label className="field" htmlFor="pack-select">Domain knowledge pack</label>
        <select id="pack-select" name="pack" autoComplete="off" value={cfg.packId} onChange={(event) => onConfigChange({ packId: event.target.value })}>
          {packList.length === 0 && <option value={cfg.packId}>{packLoading ? "Loading pack catalog…" : "UNKNOWN · no packs returned"}</option>}
          {packList.map((pack) => <option key={pack.pack_id} value={pack.pack_id}>{pack.title}</option>)}
        </select>

        <label className="field" htmlFor="variant-select">Reference architecture</label>
        <select id="variant-select" name="variant" autoComplete="off" value={cfg.variantId} onChange={(event) => onConfigChange({ variantId: event.target.value })}>
          {(packDetail?.variants ?? []).length === 0 && <option value="">UNKNOWN · no variants returned</option>}
          {(packDetail?.variants ?? []).map((variant) => <option key={variant.id} value={variant.id}>{variant.name}</option>)}
        </select>
        {activeVariant?.notes && <div className="field-note">{activeVariant.notes.slice(0, 240)}{activeVariant.notes.length > 240 ? "…" : ""}</div>}

        <div className="rail-grid">
          <div>
            <label className="field" htmlFor="annual-units">Annual output</label>
            <input
              id="annual-units"
              name="annual-units"
              autoComplete="off"
              inputMode="decimal"
              type="number"
              min={1}
              step={1}
              value={annualDraft}
              aria-invalid={!annualValid}
              aria-describedby={!annualValid ? "annual-units-error" : undefined}
              onChange={(event) => {
                const draft = event.target.value;
                setAnnualDraft(draft);
                const next = Number(draft);
                if (draft.trim() && Number.isFinite(next) && next > 0) {
                  onConfigChange({ annualUnits: next });
                }
              }}
            />
            {!annualValid && <span id="annual-units-error" className="field-error" role="alert">Enter an annual output greater than zero.</span>}
          </div>
          <div>
            <label className="field" htmlFor="geography">Geography</label>
            <input id="geography" name="geography" autoComplete="off" type="text" value={cfg.geography} onChange={(event) => onConfigChange({ geography: event.target.value })} />
          </div>
        </div>

        <label className="field" htmlFor="min-dva">Minimum domestic value addition <b className="num">{(cfg.minDva * 100).toFixed(0)}%</b></label>
        <input id="min-dva" name="minimum-dva" type="range" min={0} max={0.99} step={0.05} value={cfg.minDva} onChange={(event) => onConfigChange({ minDva: Number(event.target.value) })} />

        <label className="field" htmlFor="deadline-year">Physical deadline <b className="num">{cfg.deadlineYear}</b></label>
        <input id="deadline-year" name="deadline-year" type="range" min={new Date().getFullYear()} max={new Date().getFullYear() + 12} step={1} value={cfg.deadlineYear} onChange={(event) => onConfigChange({ deadlineYear: Number(event.target.value) })} />
      </div>

      <div className="rail-section">
        <div className="rail-section-label">World edits</div>
        <details open>
          <summary>Project / scenario inputs <span className="summary-count">{cfg.fundedProjects.length}</span></summary>
          <div className="rail-detail-body">
            {(packDetail?.projects ?? []).map((project) => (
              <label key={project.id} className="checkrow" title={`${project.item_id} · ${project.design_capacity ?? "UNKNOWN capacity"} · ${project.epistemic_class}`}>
                <input
                  type="checkbox"
                  name="funded-project"
                  value={project.id}
                  disabled={project.control_role === "context"}
                  checked={cfg.fundedProjects.includes(project.id)}
                  onChange={(event) => onConfigChange({ fundedProjects: event.target.checked ? [...cfg.fundedProjects, project.id] : cfg.fundedProjects.filter((id) => id !== project.id) })}
                />
                <span className="lbl">{project.name}</span>
                <span className={`statepill ${project.state}`}>{project.control_role === "context" ? "CONTEXT ONLY" : project.epistemic_role === "SCENARIO" ? "SCENARIO" : project.state.replace(/_/g, " ")}</span>
              </label>
            ))}
            {(packDetail?.projects?.length ?? 0) === 0 && <div className="small">No evidenced projects returned for this pack.</div>}
          </div>
        </details>
        <details>
          <summary>Inject a shock <span className="summary-count">{cfg.shocks.length}</span></summary>
          <div className="rail-detail-body">
            {(packDetail?.shocks ?? []).map((shock) => (
              <label key={shock.id} className="checkrow" title={shock.description}>
                <input
                  type="checkbox"
                  name="shock"
                  value={shock.id}
                  checked={cfg.shocks.includes(shock.id)}
                  onChange={(event) => onConfigChange({ shocks: event.target.checked ? [...cfg.shocks, shock.id] : cfg.shocks.filter((id) => id !== shock.id) })}
                />
                <span className="lbl">{shock.name}</span>
              </label>
            ))}
            {(packDetail?.shocks?.length ?? 0) === 0 && <div className="small">No defined shocks in this pack.</div>}
          </div>
        </details>
      </div>

      <div className="rail-section">
        <div className="rail-section-label">Pack presets</div>
        {isHumanoidPack ? (
          <div className="preset-list">
            <button type="button" className="btn rail-action" onClick={() => onPreset({ annualUnits: 1000000, minDva: 0.7, deadlineYear: 2030, shocks: [], fundedProjects: [], budgetUsd: null })}>Flagship baseline <span>1M · 70% DVA</span></button>
            <button type="button" className="btn rail-action" disabled={!hasReeShock} title={hasReeShock ? "Apply the evidenced shock record" : "This pack does not return the REE shock record"} onClick={() => onPreset({ annualUnits: 1000000, minDva: 0.7, deadlineYear: 2030, shocks: ["shk_cn_ree_minus80"], fundedProjects: [] })}>REE export shock <span>{hasReeShock ? "constraint branch" : "UNKNOWN shock"}</span></button>
            <button type="button" className="btn rail-action" onClick={() => onPreset({ annualUnits: 1000000, minDva: 0, deadlineYear: 2030, shocks: [], fundedProjects: [] })}>Imported-kit assembly <span>0% DVA</span></button>
            <button type="button" className="btn rail-action" onClick={() => onPreset({ annualUnits: 1000000, minDva: 0.95, deadlineYear: 2030, shocks: [], fundedProjects: [] })}>Near-total closure <span>95% DVA</span></button>
          </div>
        ) : (
          <div className="small">No generic presets are authored for this pack. Configure the objective explicitly; unknowns stay unknown.</div>
        )}
      </div>

      <div className="rail-section rail-run-section">
        <button type="button" className="btn primary run-button" disabled={busy || !canRun || !annualValid} onClick={onRun}>
          {busy ? "Compiling buildability…" : "Run buildability compilation"}
        </button>
        {error && <div className="rail-error" role="alert">{error}</div>}
      </div>
    </aside>
  );
}

export function BranchHeader({ cfg, resp, baseResp, stale = false, canRestore = false, onRestore }: { cfg: ObjectiveConfig; resp: SolveResponse | null; baseResp: SolveResponse | null; stale?: boolean; canRestore?: boolean; onRestore?: () => void }) {
  const architectureBranched = Boolean(baseResp && baseResp.run.pack_id === cfg.packId && baseResp.selected_variant !== cfg.variantId);
  const declaredEditCount = cfg.shocks.length + cfg.fundedProjects.length + (architectureBranched ? 1 : 0);
  const editCount = declaredEditCount + (canRestore && declaredEditCount === 0 ? 1 : 0);
  const branchActive = editCount > 0;
  const branchName = branchActive ? `${editCount} scenario edit${editCount === 1 ? "" : "s"}` : "baseline inputs";
  return (
    <div className="branch-header" role="status">
      <div className="branch-mark" aria-hidden="true"><span /></div>
      <div className="branch-copy">
        <span className="eyebrow">SCENARIO BRANCH</span>
        <strong>{branchName}</strong>
        <span className="small">{baseResp ? `baseline ${baseResp.run.run_id.slice(0, 12)} preserved` : "baseline run not yet available"}</span>
      </div>
      <div className="branch-meta">
        {canRestore && onRestore && <button type="button" className="text-button branch-restore" onClick={onRestore}>Restore baseline</button>}
        <span className={`chip ${stale || branchActive ? "warn" : "ok"}`}>{stale ? "RECOMPUTE" : branchActive ? "BRANCHED" : "BASELINE"}</span>
        <span className="small">{stale ? "compiled result withheld" : resp ? `run ${resp.run.run_id.slice(0, 12)}` : "no run"}</span>
      </div>
    </div>
  );
}

// Kept as an explicit type assertion boundary for future pack-specific controls.
export type ScenarioPatch = Partial<ObjectiveConfig>;
