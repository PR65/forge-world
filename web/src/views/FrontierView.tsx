import { useEffect, useState } from "react";
import type { Selection, SolveResponse } from "../types";

interface OptionRow {
  investment_id: string;
  label: string;
  kind: string;
  capex_musd: number | null;
  lead_years: number[];
  per_objective: Record<string, number>;
  total_relief: number;
  explanation: string;
}

export default function FrontierView({ resp, onSelect }: {
  resp: SolveResponse;
  onSelect: (s: Selection) => void;
}) {
  const [options, setOptions] = useState<OptionRow[] | null>(null);
  useEffect(() => {
    fetch("/api/optionvalue")
      .then((r) => r.json())
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);
  const pts = resp.frontier;
  const W = 640, H = 260, PAD = 52;
  const xs = pts.map((p) => p.dva_target);
  const minX = Math.min(...xs, 0);
  const maxX = Math.max(...xs, 1);
  const x = (v: number) => PAD + ((v - minX) / Math.max(maxX - minX, 0.01)) * (W - PAD - 24);

  return (
    <div style={{ padding: "20px 26px" }}>
      <div className="grid2" style={{ gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
        <div className="card">
          <h4>Industrial closure frontier — localization vs feasibility</h4>
          <svg className="frontier-svg" width={W} height={H}>
            <defs>
              <linearGradient id="cliffgrad" x1="0" y1="1" x2="0" y2="0">
                <stop offset="0%" stopColor="rgba(255,106,61,0.03)" />
                <stop offset="100%" stopColor="rgba(255,106,61,0.22)" />
              </linearGradient>
            </defs>
            <line className="axis" x1={PAD} y1={H - 34} x2={W - 20} y2={H - 34} />
            <line className="axis" x1={PAD} y1={16} x2={PAD} y2={H - 34} />
            <text x={PAD - 40} y={30}>FEASIBLE</text>
            <text x={PAD - 48} y={H - 44}>INFEASIBLE</text>
            {pts.map((p) => (
              <g key={p.dva_target}>
                <circle
                  cx={x(p.dva_target)}
                  cy={p.feasible ? 34 : H - 50}
                  r={7}
                  fill={p.feasible ? "var(--green)" : "var(--molten)"}
                  fillOpacity={0.9}
                  style={{ cursor: "pointer" }}
                  onClick={() => onSelect({ kind: "proof", id: "" })}
                />
                <text x={x(p.dva_target) - 12} y={H - 18}>{(p.dva_target * 100).toFixed(0)}%</text>
              </g>
            ))}
            {(() => {
              const firstBad = pts.find((p) => !p.feasible);
              if (!firstBad) return null;
              const cx = x(firstBad.dva_target);
              return <rect className="cliff" x={cx} y={14} width={Math.max(W - 24 - cx, 0)} height={H - 48} />;
            })()}
          </svg>
          <div className="small" style={{ marginTop: 4 }}>
            Each point is a full re-solve with the domestic-share constraint pinned to the axis
            value. The shaded region is where the objective stops closing — the cliff is measured,
            not drawn.
          </div>
          {pts.some((p) => p.binding.length > 0 && !p.feasible) && (
            <>
              <h4 style={{ marginTop: 10 }}>What binds at the cliff</h4>
              {pts.filter((p) => !p.feasible).slice(0, 1).flatMap((p) => p.binding.slice(0, 4)).map((b) => (
                <div key={b} className="num small" style={{ padding: "2px 0" }}>▸ {b}</div>
              ))}
            </>
          )}
        </div>

        <div>
          <div className="card">
            <h4>Reverse buildability — maximum achievable output</h4>
            {resp.reverse ? (
              <>
                <div style={{ display: "flex", gap: 26, marginTop: 6 }}>
                  <div>
                    <div className="small">no localization constraint</div>
                    <div className="bignum" style={{ color: "var(--steel)" }}>
                      {(resp.reverse.max_units_per_year / 1000).toFixed(0)}k
                    </div>
                    <span className={`chip ${resp.reverse.class_at_max === "CONDITIONALLY_FEASIBLE" ? "warn" : "ok"}`}>
                      {resp.reverse.class_at_max.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div>
                    <div className="small">
                      at ≥{(resp.reverse.dva_reference * 100).toFixed(0)}% DVA
                    </div>
                    <div
                      className="bignum"
                      style={{ color: resp.reverse.max_units_localized_at_dva > 0 ? "var(--green)" : "var(--molten)" }}
                    >
                      {(resp.reverse.max_units_localized_at_dva / 1000).toFixed(0)}k
                    </div>
                    <span className={`chip ${resp.reverse.class_localized === "INFEASIBLE_UNDER_MODEL" ? "binding" : "ok"}`}>
                      {resp.reverse.class_localized.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>
                <div className="small" style={{ marginTop: 10 }}>
                  The dual problem: given current capability and evidenced projects, how much
                  output can be reached at all — and how much of it can be domestically owned?
                </div>
              </>
            ) : (
              <div className="small">Reverse query unavailable.</div>
            )}
          </div>

          <div className="card" style={{ marginTop: 14 }}>
            <h4>Classification crosswalks (confidence-bearing)</h4>
            <table className="data">
              <thead>
                <tr><th>code</th><th>entity</th><th className="r">conf</th></tr>
              </thead>
              <tbody>
                {resp.crosswalks.map((c) => (
                  <tr key={c.from_class + c.from_code}>
                    <td>{c.from_class} {c.from_code}</td>
                    <td>{c.to_entity}</td>
                    <td className="r">{c.confidence.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="small" style={{ marginTop: 8 }}>
              Trade codes never silently become engineering capabilities; every mapping carries its
              confidence and note.
            </div>
          </div>

          <div className="card" style={{ marginTop: 14 }}>
            <h4>Option value — which evidenced investments unlock the most futures?</h4>
            {!options && <div className="small">Measuring marginal relief across domain objectives…</div>}
            {options && options.length === 0 && (
              <div className="small">No evidenced investments available.</div>
            )}
            {options && options.slice(0, 5).map((o) => {
              const maxRelief = Math.max(...options.map((x) => x.total_relief), 0.001);
              return (
                <div key={o.investment_id} style={{ marginBottom: 9 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span className="bar-label" title={o.label}>{o.label}</span>
                    <span className="num small">{(o.total_relief * 100).toFixed(1)}%</span>
                  </div>
                  <div className="bar-track" style={{ height: 10, marginTop: 3 }}>
                    <div
                      className="bar-fill"
                      style={{
                        width: `${(o.total_relief / maxRelief) * 100}%`,
                        background: "linear-gradient(90deg,#5a3d8a,var(--violet))",
                      }}
                    />
                  </div>
                  <div className="small" style={{ marginTop: 2 }}>{o.explanation}</div>
                </div>
              );
            })}
            {options && (
              <div className="small">
                Measured as reduction of normalized infeasibility at each objective's deadline,
                through full re-solves — never centrality alone.
              </div>
            )}
          </div>

          <div className="card" style={{ marginTop: 14 }}>
            <h4>Run provenance</h4>
            <div className="kv">
              <span className="k">run id</span><span className="v">{resp.run.run_id}</span>
              <span className="k">input hash</span><span className="v">{resp.run.input_hash.slice(0, 16)}…</span>
              <span className="k">solver</span><span className="v">{resp.run.solver_version}</span>
              <span className="k">created</span><span className="v">{resp.run.created_at}</span>
            </div>
            <div className="small" style={{ marginTop: 6 }}>
              Same inputs reproduce this result byte-for-byte.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
