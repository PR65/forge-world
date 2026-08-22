import type { SolveResponse } from "../types";
import type { Selection } from "../types";

function fmt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "k";
  return n.toFixed(0);
}

const CLASS_COLOR: Record<string, string> = {
  FEASIBLE: "var(--green)",
  CONDITIONALLY_FEASIBLE: "var(--steel)",
  INFEASIBLE_UNDER_MODEL: "var(--molten)",
  NOT_ADJUDICABLE: "var(--violet)",
};

export default function VerdictView({ resp, onSelect }: {
  resp: SolveResponse;
  onSelect: (s: Selection) => void;
}) {
  const r = resp.result;
  const worstYear = r.max_shortfall_year || Number(Object.keys(r.years)[0]);
  const yr = r.years[String(worstYear)];
  const shortfalls = [...(yr?.shortfalls ?? [])].sort((a, b) => b.shortfall - a.shortfall).slice(0, 12);
  const maxShort = Math.max(1, ...shortfalls.map((s) => s.shortfall));

  return (
    <div>
      <div className="bigverdict">
        <div className="vclass">
          <span className="cls" style={{ color: CLASS_COLOR[r.result_class] }}>
            {r.result_class.replace(/_/g, " ")}
          </span>
          <span className="units">
            {resp.annual_units.toLocaleString()} units/yr · {resp.selected_variant} · by {resp.years[resp.years.length - 1]}
          </span>
        </div>
        <div className="verdict-sub">
          {r.result_class === "INFEASIBLE_UNDER_MODEL" && (
            <>Under the active constraints the model finds no admissible allocation. The binding
              gaps below are where qualified effective capacity falls short of gross requirements —
              click any item to descend into its evidence and derivation chain.</>
          )}
          {r.result_class === "CONDITIONALLY_FEASIBLE" && (
            <>An allocation exists only because of explicitly flagged conditions: unknown-capacity
              items are served by eligible imports and/or unproven projects are counted before
              qualification. Every condition is listed; none is silently assumed.</>
          )}
          {r.result_class === "FEASIBLE" && (
            <>The model found an allocation satisfying all constraints with the current
              evidenced state.</>
          )}
          {r.result_class === "NOT_ADJUDICABLE" && (
            <>Decision-critical capacity is UNKNOWN for some items and no eligible supply route
              exists under the scenario. The honest answer is refusal — resolve the blocking
              unknowns listed below.</>
          )}
        </div>

        <div className="chiprow">
          {resp.dva.fraction > 0 && (
            <span className="chip ok">DVA {(resp.dva.fraction * 100).toFixed(1)}%</span>
          )}
          {r.blocking_unknowns.slice(0, 4).map((u) => (
            <span key={u} className="chip unknown" onClick={() => onSelect({ kind: "item", id: u })}>
              UNKNOWN · {u}
            </span>
          ))}
          {r.binding_summary.slice(0, 3).map((b) => (
            <span key={b} className="chip binding">{b}</span>
          ))}
          {resp.explosion.mass_balance_warnings.slice(0, 2).map((w) => (
            <span key={w} className="chip warn">{w}</span>
          ))}
        </div>
      </div>

      <div className="grid2" style={{ padding: "0 26px 10px" }}>
        <div className="card">
          <h4>Binding gaps — worst year {worstYear}</h4>
          {shortfalls.length === 0 && (
            <div className="small">No shortfall in the worst modeled year.</div>
          )}
          {shortfalls.map((s) => (
            <div
              key={s.item}
              className="bar-row clickable"
              style={{ cursor: "pointer" }}
              onClick={() => onSelect({ kind: "item", id: s.item })}
            >
              <span className="bar-label" title={s.item}>{s.item}</span>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{
                    width: `${(s.shortfall / maxShort) * 100}%`,
                    background: s.unknown
                      ? "linear-gradient(90deg,#7c5cd6,var(--violet))"
                      : "linear-gradient(90deg,#b34a2c,var(--molten))",
                  }}
                />
              </div>
              <span className="bar-val num">
                {fmt(s.shortfall)}
                {s.unknown ? " ?cap" : ""}
              </span>
            </div>
          ))}
        </div>

        <div className="card">
          <h4>Transformation portfolio — verified through re-solve</h4>
          {resp.plan.actions.length === 0 && (
            <div className="small">No closure actions required (or none available in pack).</div>
          )}
          {resp.plan.actions.map((a) => (
            <div
              key={a.action_id}
              className="bar-row clickable"
              style={{ gridTemplateColumns: "230px 1fr 90px", cursor: "pointer" }}
              onClick={() => onSelect({ kind: "action", id: a.action_id })}
            >
              <span className="bar-label" title={a.label}>{a.kind} · {a.label}</span>
              <div style={{ color: "var(--ink-faint)", fontSize: 11 }}>{a.rationale}</div>
              <span className="bar-val num">
                {a.capex_usd > 0 ? `$${fmt(a.capex_usd)}` : "—"}
              </span>
            </div>
          ))}
          <div className="small" style={{ marginTop: 8 }}>
            Portfolio capex ${fmt(resp.plan.total_capex_usd)} → verified{" "}
            <b style={{ color: CLASS_COLOR[resp.plan.verified_result_class] ?? "var(--ink)" }}>
              {resp.plan.verified_result_class.replace(/_/g, " ")}
            </b>
            {resp.plan.remaining_shortfall > 0 && (
              <> · residual shortfall {fmt(resp.plan.remaining_shortfall)}</>
            )}
          </div>

          <h4 style={{ marginTop: 16 }}>What should we investigate next? (value of information)</h4>
          {[...resp.voi]
            .sort((a, b) => ({ HIGH: 0, MEDIUM: 1, LOW: 2 })[a.decision_impact] - ({ HIGH: 0, MEDIUM: 1, LOW: 2 })[b.decision_impact])
            .slice(0, 5)
            .map((t) => (
              <div
                key={t.unknown_id}
                className="bar-row clickable"
                style={{ gridTemplateColumns: "200px 80px 1fr", cursor: "pointer" }}
                onClick={() => onSelect({ kind: "item", id: t.unknown_id })}
              >
                <span className="bar-label">{t.unknown_id}</span>
                <span
                  className={`chip ${t.decision_impact === "HIGH" ? "binding" : t.decision_impact === "LOW" ? "" : "warn"}`}
                >
                  {t.decision_impact}
                </span>
                <span className="small" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {t.flip_behavior}
                </span>
              </div>
            ))}
        </div>
      </div>

      {r.required_relaxations.length > 0 && (
        <div className="card" style={{ margin: "0 26px 20px" }}>
          <h4>Infeasibility explanation — required relaxations</h4>
          {r.required_relaxations.slice(0, 8).map((x) => (
            <div key={x} className="num small" style={{ padding: "3px 0" }}>▸ {x}</div>
          ))}
          {r.closure_candidates.length > 0 && (
            <>
              <h4 style={{ marginTop: 12 }}>Candidate closure actions</h4>
              {r.closure_candidates.slice(0, 8).map((x) => (
                <div key={x} className="num small" style={{ padding: "3px 0" }}>→ {x}</div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
