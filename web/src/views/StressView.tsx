import type { SolveResponse } from "../types";
import type { Selection } from "../types";

export default function StressView({ resp, base, onSelect }: {
  resp: SolveResponse;
  base: SolveResponse | null;
  onSelect: (s: Selection) => void;
}) {
  const activeShocks = resp.shock_report.applied.length > 0;
  const worstYearR = resp.result.max_shortfall_year || Object.keys(resp.result.years)[0];
  const yr = resp.result.years[String(worstYearR)];
  const yrBase = base?.result.years[String(base.result.max_shortfall_year || worstYearR)];

  const items = new Map<string, { now: number; before: number; unknown: boolean }>();
  const maxV = Math.max(1);
  for (const g of yr?.shortfalls ?? []) {
    items.set(g.item, { now: g.shortfall, before: 0, unknown: g.unknown });
  }
  for (const g of yrBase?.shortfalls ?? []) {
    const e = items.get(g.item);
    if (e) e.before = g.shortfall;
    else items.set(g.item, { now: 0, before: g.shortfall, unknown: g.unknown });
  }
  const rows = [...items.entries()].sort((a, b) => Math.abs(b[1].now - b[1].before) - Math.abs(a[1].now - a[1].before)).slice(0, 12);
  const maxBar = Math.max(1, ...rows.map(([, v]) => Math.max(v.now, v.before)));

  return (
    <div style={{ padding: "20px 26px" }}>
      {!activeShocks && (
        <div className="flashnote">
          No shocks active. Toggle shock scenarios in the left rail — each re-run propagates
          constraint edits through the full pipeline (never hand-multiplied downstream).
        </div>
      )}
      <div className="grid2" style={{ marginTop: 14 }}>
        <div className="card">
          <h4>Shock propagation — shortfall by item (now vs unshocked baseline)</h4>
          {rows.length === 0 && (
            <div className="small">No shortfalls in either scenario.</div>
          )}
          {rows.map(([item, v]) => (
            <div key={item} style={{ marginBottom: 10, cursor: "pointer" }} onClick={() => onSelect({ kind: "item", id: item })}>
              <div className="bar-label" style={{ marginBottom: 3 }}>{item}</div>
              <div className="bar-track" style={{ height: 9, marginBottom: 2 }}>
                <div className="bar-fill" style={{ width: `${(v.before / maxBar) * 100}%`, background: "#3d5a70" }} />
              </div>
              <div className="bar-track" style={{ height: 9 }}>
                <div
                  className="bar-fill"
                  style={{
                    width: `${(v.now / maxBar) * 100}%`,
                    background: v.unknown ? "var(--violet)" : "linear-gradient(90deg,#b34a2c,var(--molten))",
                  }}
                />
              </div>
            </div>
          ))}
          <div className="legend" style={{ padding: "8px 0 0" }}>
            <span><span className="dot" style={{ background: "#3d5a70" }} />baseline</span>
            <span><span className="dot" style={{ background: "var(--molten)" }} />under shock</span>
          </div>
        </div>

        <div>
          <div className="card">
            <h4>Applied constraint edits</h4>
            {resp.shock_report.applied.length === 0 && (
              <div className="small">None — the solver ran on the unmodified world state.</div>
            )}
            {resp.shock_report.applied.map((a, i) => {
              const e = a as Record<string, unknown>;
              return (
                <div key={i} className="num small" style={{ padding: "4px 0", borderBottom: "1px solid var(--line)" }}>
                  <span style={{ color: "var(--molten)" }}>{String(e["edit"])}</span>{" "}
                  {Object.entries(e)
                    .filter(([k]) => k !== "edit" && k !== "shock")
                    .map(([k, v]) => `${k}=${String(v)}`)
                    .join("  ")}
                </div>
              );
            })}
            {resp.shock_report.rejected.length > 0 && (
              <>
                <h4 style={{ marginTop: 10 }}>Rejected / unmatched edits</h4>
                {resp.shock_report.rejected.map((r0, i) => (
                  <div key={i} className="num small" style={{ color: "var(--amber)" }}>⚠ {r0}</div>
                ))}
              </>
            )}
          </div>

          <div className="card" style={{ marginTop: 14 }}>
            <h4>Aggregate exposure</h4>
            <div className="kv">
              <span className="k">import value (worst yr)</span>
              <span className="v">${fmtM(yr?.import_value_usd)}</span>
              <span className="k">baseline import value</span>
              <span className="v">${fmtM(yrBase?.import_value_usd)}</span>
              <span className="k">domestic value (worst yr)</span>
              <span className="v">${fmtM(yr?.domestic_value_usd)}</span>
              <span className="k">total shortfall Δ</span>
              <span className="v">{fmtBig((yr?.total_shortfall ?? 0) - (yrBase?.total_shortfall ?? 0))}</span>
            </div>
            <div className="small" style={{ marginTop: 8 }}>
              Shocks edit constraints (eligibility, capacity, costs, project states); everything
              below them is recomputed — allocation, DVA, plan verification.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function fmtM(v?: number): string {
  if (!v) return "—";
  return (v / 1e6).toFixed(0) + "M";
}
function fmtBig(v: number): string {
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + "M";
  if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + "k";
  return v.toFixed(0);
}
