import { useCallback, useEffect, useMemo, useState } from "react";
import type { ObjectiveConfig, Selection, SolveResponse } from "./types";
import { fetchPackDetail, fetchPacks, solveObjective } from "./api";
import type { PackDetail } from "./types";
import VerdictView from "./views/VerdictView";
import StrataView from "./views/StrataView";
import TimeView from "./views/TimeView";
import StressView from "./views/StressView";
import FrontierView from "./views/FrontierView";
import Inspector from "./Inspector";

const PRESETS: { name: string; note: string; patch: Partial<ObjectiveConfig> }[] = [
  {
    name: "Flagship baseline",
    note: "1M HV-2 humanoids/yr by 2030 · ≥70% DVA",
    patch: { annualUnits: 1000000, minDva: 0.7, deadlineYear: 2030, shocks: [], budgetUsd: null },
  },
  {
    name: "REE export shock",
    note: "Chinese magnet exports −80% against the baseline",
    patch: { annualUnits: 1000000, minDva: 0.7, deadlineYear: 2030, shocks: ["shk_cn_ree_minus80"] },
  },
  {
    name: "Imported-kit assembly",
    note: "Same target, no localization requirement (assembly-only definition)",
    patch: { annualUnits: 1000000, minDva: 0.0, deadlineYear: 2030, shocks: [] },
  },
  {
    name: "Near-total closure",
    note: "95% domestic value addition",
    patch: { annualUnits: 1000000, minDva: 0.95, deadlineYear: 2030, shocks: [] },
  },
];

export default function App() {
  const [packList, setPackList] = useState<{ pack_id: string; title: string; variants: string[] }[]>([]);
  const [packDetail, setPackDetail] = useState<PackDetail | null>(null);
  const [cfg, setCfg] = useState<ObjectiveConfig>({
    packId: "humanoid_india",
    variantId: "",
    annualUnits: 1000000,
    geography: "INDIA",
    deadlineYear: 2030,
    minDva: 0.7,
    budgetUsd: null,
    fundedProjects: [],
    shocks: [],
    assumptions: {},
  });
  const [resp, setResp] = useState<SolveResponse | null>(null);
  const [baseResp, setBaseResp] = useState<SolveResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState("verdict");
  const [sel, setSel] = useState<Selection | null>(null);
  const [nlText, setNlText] = useState("");
  const [nlNote, setNlNote] = useState<string | null>(null);

  const applyNl = async () => {
    if (!nlText.trim()) return;
    try {
      const r = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: nlText }),
      });
      const j = await r.json();
      if (j.objective) {
        const patch: Partial<ObjectiveConfig> = {
          annualUnits: j.objective.annual_units,
          deadlineYear: j.objective.deadline_year,
          minDva: j.objective.min_dva,
        };
        if (j.objective.budget_usd) patch.budgetUsd = j.objective.budget_usd;
        setCfg((c) => ({ ...c, ...patch }));
        setNlNote(
          (j.interpretations ?? []).join(" · ") +
            (j.unresolved?.length ? ` | unresolved: ${j.unresolved.join(", ")}` : "")
        );
        void run(patch);
      } else {
        setCfg((c) => ({
          ...c,
          shocks: j.shocks?.length ? j.shocks : c.shocks,
        }));
        setNlNote(
          (j.interpretations ?? []).join(" · ") ||
            "no interpretable objective found — edit fields below"
        );
        if (j.shocks?.length) void run({ shocks: j.shocks });
      }
    } catch {
      setNlNote("parse failed — edit fields directly below");
    }
  };

  useEffect(() => {
    fetchPacks().then((ps) => {
      setPackList(ps);
      const first = ps[0];
      if (first && !cfg.variantId) {
        return fetchPackDetail(first.pack_id).then((d) => {
          setPackDetail(d);
          setCfg((c) => ({ ...c, packId: first.pack_id, variantId: d.variants[0]?.id ?? "" }));
        });
      }
    }).catch((e) => setErr(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (cfg.packId) {
      fetchPackDetail(cfg.packId).then((d) => {
        setPackDetail(d);
        setCfg((c) => ({
          ...c,
          variantId: d.variants.some((v) => v.id === c.variantId) ? c.variantId : d.variants[0]?.id ?? "",
          shocks: c.shocks.filter((s) => d.shocks.some((ds) => ds.id === s)),
          fundedProjects: c.fundedProjects.filter((p) => d.projects.some((dp) => dp.id === p)),
        }));
      });
    }
  }, [cfg.packId]);

  const run = useCallback(
    async (override?: Partial<ObjectiveConfig>) => {
      setBusy(true);
      setErr(null);
      try {
        const c = { ...cfg, ...override };
        const r = await solveObjective(c);
        setResp(r);
        if (!override?.shocks || override.shocks.length === 0) setBaseResp(r);
      } catch (e) {
        setErr(String(e));
      } finally {
        setBusy(false);
      }
    },
    [cfg]
  );

  useEffect(() => {
    if (cfg.packId && cfg.variantId && !resp && !busy) void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg.packId, cfg.variantId]);

  const applyPreset = (patch: Partial<ObjectiveConfig>) => {
    setCfg((c) => ({ ...c, ...patch }));
    void run(patch);
  };

  const modes = useMemo(
    () => [
      ["verdict", "VERDICT"],
      ["strata", "STRATA"],
      ["time", "TIME"],
      ["stress", "STRESS LAB"],
      ["frontier", "FRONTIER"],
    ],
    []
  );

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="forge-mark" />
          FORGE&nbsp;WORLD
          <span className="sub">// industrial buildability compiler</span>
        </div>
        <div className="runmeta">
          {resp && (
            <>
              <span><b>{resp.result.result_class}</b></span>
              <span>DVA <b>{(resp.dva.fraction * 100).toFixed(1)}%</b></span>
              <span>run <b>{resp.run.run_id}</b></span>
              <span>pack v{resp.run.pack_version}</span>
            </>
          )}
          {busy && <span className="spin" />}
        </div>
      </header>

      <aside className="rail">
        <div className="section">
          <h3>Physical objective</h3>
          <label className="field">Describe it in plain language (rule-based parse)</label>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              type="text"
              placeholder='e.g. "1 million humanoids a year by 2030"'
              value={nlText}
              onChange={(e) => setNlText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void applyNl();
              }}
            />
            <button className="btn" onClick={() => void applyNl()}>Parse</button>
          </div>
          {nlNote && <div className="small" style={{ marginTop: 6, color: "var(--steel)" }}>{nlNote}</div>}

          <label className="field">Domain knowledge pack</label>
          <select
            value={cfg.packId}
            onChange={(e) => setCfg((c) => ({ ...c, packId: e.target.value }))}
          >
            {packList.map((p) => (
              <option key={p.pack_id} value={p.pack_id}>{p.title}</option>
            ))}
          </select>

          <label className="field">Reference architecture</label>
          <select
            value={cfg.variantId}
            onChange={(e) => setCfg((c) => ({ ...c, variantId: e.target.value }))}
          >
            {(packDetail?.variants ?? []).map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          {packDetail?.variants.find((v) => v.id === cfg.variantId)?.notes && (
            <div className="small" style={{ marginTop: 6, lineHeight: 1.45 }}>
              {packDetail.variants.find((v) => v.id === cfg.variantId)!.notes.slice(0, 260)}
              {(packDetail.variants.find((v) => v.id === cfg.variantId)!.notes.length > 260) ? "…" : ""}
            </div>
          )}

          <label className="field">Annual output target</label>
          <input
            type="number"
            value={cfg.annualUnits}
            min={1}
            step={10000}
            onChange={(e) => setCfg((c) => ({ ...c, annualUnits: Number(e.target.value) }))}
          />

          <label className="field">
            Minimum domestic value addition: <b className="num">{(cfg.minDva * 100).toFixed(0)}%</b>
          </label>
          <input
            type="range"
            min={0}
            max={0.99}
            step={0.05}
            value={cfg.minDva}
            onChange={(e) => setCfg((c) => ({ ...c, minDva: Number(e.target.value) }))}
          />

          <label className="field">Deadline year: <b className="num">{cfg.deadlineYear}</b></label>
          <input
            type="range"
            min={2027}
            max={2035}
            step={1}
            value={cfg.deadlineYear}
            onChange={(e) => setCfg((c) => ({ ...c, deadlineYear: Number(e.target.value) }))}
          />
        </div>

        <div className="section">
          <h3>Evidenced projects to fund</h3>
          {(packDetail?.projects ?? []).map((p) => (
            <label key={p.id} className="checkrow" title={`${p.item_id} · ${p.design_capacity ?? "?"}`}>
              <input
                type="checkbox"
                checked={cfg.fundedProjects.includes(p.id)}
                onChange={(e) =>
                  setCfg((c) => ({
                    ...c,
                    fundedProjects: e.target.checked
                      ? [...c.fundedProjects, p.id]
                      : c.fundedProjects.filter((x) => x !== p.id),
                  }))
                }
              />
              <span className="lbl">{p.name}</span>
              <span className={`statepill ${p.state}`}>{p.state.replace(/_/g, " ")}</span>
            </label>
          ))}
          {(packDetail?.projects?.length ?? 0) === 0 && (
            <div className="small">No evidenced projects in this pack.</div>
          )}
        </div>

        <div className="section">
          <h3>Shock scenarios</h3>
          {(packDetail?.shocks ?? []).map((s) => (
            <label key={s.id} className="checkrow" title={s.description}>
              <input
                type="checkbox"
                checked={cfg.shocks.includes(s.id)}
                onChange={(e) =>
                  setCfg((c) => ({
                    ...c,
                    shocks: e.target.checked
                      ? [...c.shocks, s.id]
                      : c.shocks.filter((x) => x !== s.id),
                  }))
                }
              />
              <span className="lbl">{s.name}</span>
            </label>
          ))}
          {(packDetail?.shocks?.length ?? 0) === 0 && (
            <div className="small">No defined shocks in this pack.</div>
          )}
        </div>

        <div className="section">
          <h3>Scenario presets</h3>
          {PRESETS.map((p) => (
            <button
              key={p.name}
              className="btn"
              style={{ width: "100%", marginBottom: 6, textAlign: "left" }}
              onClick={() => applyPreset(p.patch)}
              title={p.note}
            >
              {p.name}
            </button>
          ))}
        </div>

        <div className="section">
          <button className="btn primary" disabled={busy} onClick={() => void run()}>
            {busy ? "Compiling buildability…" : "Run buildability compilation"}
          </button>
          {err && <div style={{ color: "var(--red)", marginTop: 8 }}>{err}</div>}
        </div>
      </aside>

      <main className="stage">
        <nav className="modes">
          {modes.map(([id, label]) => (
            <div
              key={id}
              className={`mode ${mode === id ? "active" : ""}`}
              onClick={() => setMode(id)}
            >
              {label}
            </div>
          ))}
        </nav>
        <div className="stagewrap fadein" key={mode + (resp?.run.run_id ?? "")}>
          {!resp ? (
            <div className="bigverdict small">Loading model state…</div>
          ) : mode === "verdict" ? (
            <VerdictView resp={resp} onSelect={setSel} />
          ) : mode === "strata" ? (
            <StrataView resp={resp} onSelect={setSel} />
          ) : mode === "time" ? (
            <TimeView resp={resp} onSelect={setSel} />
          ) : mode === "stress" ? (
            <StressView resp={resp} base={baseResp} onSelect={setSel} />
          ) : (
            <FrontierView resp={resp} onSelect={setSel} />
          )}
        </div>
      </main>

      <Inspector sel={sel} resp={resp} packDetail={packDetail} onSelect={setSel} />
    </div>
  );
}
