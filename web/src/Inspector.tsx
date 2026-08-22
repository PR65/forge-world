import { useMemo } from "react";
import type { EnvelopeYear, Selection, SolveResponse } from "./types";

export default function Inspector({ sel, resp, packDetail, onSelect }: {
  sel: Selection | null;
  resp: SolveResponse | null;
  packDetail: {
    evidence: {
      claim_id: string; subject: string; predicate: string; epistemic_class: string;
      value_text: string; source_ids: string[]; quote_or_caveat: string;
      confidence: Record<string, number | null>;
    }[];
    sources: { id: string; name: string; publisher: string; url: string; license: string; access_date: string }[];
  } | null;
  onSelect: (s: Selection) => void;
}) {
  const pg = resp?.proof_graph;
  const sid = sel?.id ?? "";

  const sub = useMemo(() => {
    if (!pg || !sid) return null;
    const nodeId =
      sel?.kind === "proof"
        ? sid
        : resp?.capacity_envelopes.find((e) => e.item === sid)?.proof ??
          resp?.explosion.items.find((i) => i.item === sid)?.item;
    if (!nodeId) return null;
    const nodes = new Map(pg.nodes.map((n) => [n.node_id, n]));
    if (!nodes.has(nodeId)) return null;
    const seen = new Set<string>();
    const chain: { node: (typeof pg.nodes)[number]; depth: number }[] = [];
    const walk = (id: string, depth: number) => {
      if (seen.has(id) || depth > 24) return;
      seen.add(id);
      const n = nodes.get(id);
      if (!n) return;
      chain.push({ node: n, depth });
      for (const e of pg.edges) {
        if (e.to_id === id) walk(e.from_id, depth + 1);
      }
    };
    walk(nodeId, 0);
    chain.reverse();
    return { chain, rootId: nodeId };
  }, [pg, sid, sel?.kind, resp]);

  const env = sid ? resp?.capacity_envelopes.find((e) => e.item === sid) ?? null : null;
  const expl = sid ? resp?.explosion.items.find((i) => i.item === sid) ?? null : null;
  const voi = sid ? resp?.voi.find((v) => v.unknown_id === sid) ?? null : null;
  const action = sid ? resp?.actions.find((a) => a.action_id === sid) ?? null : null;
  const evidenceRecs = useMemo(() => {
    if (!sub || !packDetail) return [];
    const ids = new Set(sub.chain.filter((c) => c.node.kind === "evidence").map((c) => c.node.node_id.replace("ev.", "")));
    return packDetail.evidence.filter((e) => ids.has(e.claim_id));
  }, [sub, packDetail]);

  return (
    <aside className="inspector">
      {!sel && (
        <div className="insp-head">
          <div className="insp-title">Inspector</div>
          <div className="insp-kind">select any node, gap, action or chart point</div>
          <div className="small" style={{ marginTop: 10, lineHeight: 1.6 }}>
            Every consequential number in FORGE traces through a derivation DAG to immutable
            evidence records. The inspector renders that chain — nothing in the model is
            authoritative without it.
          </div>
        </div>
      )}

      {sel && (
        <div className="insp-head">
          <div className="insp-title">{sel.kind === "item" ? sel.id : sel.id || "selection"}</div>
          <div className="insp-kind">{sel.kind}</div>
        </div>
      )}

      {env && (
        <div className="insp-body">
          <div className="card" style={{ padding: 12 }}>
            <h4>Capacity envelope by year</h4>
            <table className="data">
              <thead>
                <tr><th>yr</th><th className="r">lo</th><th className="r">hi</th><th>src</th></tr>
              </thead>
              <tbody>
                {(Object.entries(env.by_year) as [string, EnvelopeYear][]).map(([y, e]) => (
                  <tr key={y}>
                    <td>{y}</td>
                    <td className="r">{fmt(e.lo)}</td>
                    <td className="r" style={{ color: e.projects_only ? "var(--amber)" : undefined }}>{fmt(e.hi)}</td>
                    <td>{e.unknown ? <span className="chip unknown">UNKNOWN</span> : e.projects_only ? <span className="chip warn">projects</span> : <EpistemicChip cls={e.epistemic ?? ""} />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {env.suppliers.length > 0 && (
              <div className="small" style={{ marginTop: 8 }}>
                Supplier origins: {env.suppliers.join(", ")}
                {env.concentration_hhi !== null && <> · HHI≈{env.concentration_hhi.toFixed(2)}</>}
              </div>
            )}
            {env.by_year[Object.keys(env.by_year)[0]]?.reasons?.length > 0 && (
              <div className="small" style={{ color: "var(--violet)", marginTop: 6 }}>
                {env.by_year[Object.keys(env.by_year)[0]].reasons.join(" · ")}
              </div>
            )}
          </div>

          {expl && (
            <div className="card" style={{ padding: 12, marginTop: 12 }}>
              <h4>Annual requirement</h4>
              <div className="kv">
                <span className="k">net</span><span className="v">{fmt(expl.net)} {expl.unit}/yr</span>
                <span className="k">gross (yield-adj.)</span><span className="v">{fmt(expl.gross)} {expl.unit}/yr</span>
                <span className="k">route</span><span className="v">{expl.recipe || "import-only / no recipe"}</span>
              </div>
            </div>
          )}

          {voi && (
            <div className="card" style={{ padding: 12, marginTop: 12 }}>
              <h4>Value of information</h4>
              <span className={`chip ${voi.decision_impact === "HIGH" ? "binding" : voi.decision_impact === "LOW" ? "" : "warn"}`}>
                {voi.decision_impact} decision impact
              </span>
              <div className="small" style={{ marginTop: 8 }}>{voi.flip_behavior}</div>
              <h4 style={{ marginTop: 10 }}>Next evidence to collect</h4>
              {voi.next_evidence.map((n) => (
                <div key={n} className="small" style={{ padding: "2px 0" }}>▸ {n}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {action && (
        <div className="insp-body">
          <div className="card" style={{ padding: 12 }}>
            <h4>Action</h4>
            <div className="kv">
              <span className="k">kind</span><span className="v">{action.kind}</span>
              <span className="k">capex</span><span className="v">{action.capex_usd > 0 ? "$" + fmt(action.capex_usd) : "—"}</span>
              <span className="k">lead time</span><span className="v">{action.lead_time_years[0]}–{action.lead_time_years[1]} yr</span>
            </div>
            <div className="small" style={{ marginTop: 8 }}>{action.rationale}</div>
          </div>
        </div>
      )}

      {sub && (
        <div className="insp-body">
          <h3 style={{ margin: "0 0 10px", fontSize: 10, letterSpacing: "0.2em", color: "var(--ink-faint)", textTransform: "uppercase" }}>
            Proof chain ({sub.chain.length} nodes)
          </h3>
          {sub.chain.map(({ node }) => (
            <div key={node.node_id} className={`proof-step ${node.kind}`} style={{ marginBottom: 6 }}>
              <span className="proof-kind">{node.kind}</span>
              <div className="proof-label small">{node.label}</div>
              {node.sources.length > 0 && (
                <div className="ev-src">sources: {node.sources.join(", ")}</div>
              )}
              {node.kind === "evidence" && (
                <div
                  style={{ cursor: "pointer", marginTop: 4 }}
                  onClick={() => onSelect({ kind: "evidence", id: node.node_id.replace("ev.", "") })}
                >
                  <span className="chip">open evidence record →</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {sel?.kind === "evidence" && packDetail && (
        <div className="insp-body">
          {packDetail.evidence
            .filter((e) => e.claim_id === sel.id)
            .map((e) => (
              <div key={e.claim_id} className="ev-card">
                <span className={`ev-class ${e.epistemic_class}`}>{e.epistemic_class}</span>
                <div className="num small" style={{ marginTop: 6 }}>
                  {e.subject} · {e.predicate}
                </div>
                <div className="ev-quote">{e.value_text || "(qualitative claim)"}</div>
                {e.quote_or_caveat && <div className="ev-caveat">⚠ {e.quote_or_caveat}</div>}
                <div className="ev-src">
                  {e.source_ids.map((sid) => {
                    const s = packDetail.sources.find((x) => x.id === sid);
                    return s ? (
                      <div key={sid}>
                        {s.publisher} — {s.name}
                        {s.url ? (
                          <>
                            {" "}
                            <a href={s.url} target="_blank" rel="noreferrer" style={{ color: "var(--steel)" }}>[link]</a>
                          </>
                        ) : null}{" "}
                        · {s.license} · accessed {s.access_date}
                      </div>
                    ) : (
                      <div key={sid}>{sid}</div>
                    );
                  })}
                </div>
                {Object.keys(e.confidence).length > 0 && (
                  <div className="small" style={{ marginTop: 6 }}>
                    confidence:{" "}
                    {Object.entries(e.confidence)
                      .filter(([, v]) => v !== null)
                      .map(([k, v]) => `${k} ${((v as number) * 100).toFixed(0)}%`)
                      .join(" · ")}
                  </div>
                )}
              </div>
            ))}
        </div>
      )}
    </aside>
  );
}

function fmt(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "k";
  return n.toFixed(0);
}

export function EpistemicChip({ cls }: { cls: string }) {
  const upper = cls.toUpperCase();
  if (upper.includes("MEASURED"))
    return <span className="chip ok">MEASURED</span>;
  if (upper.includes("ESTIMATED") || upper.includes("ASSUMPTION"))
    return <span className="chip warn" title="Order-of-magnitude planning estimate, not a measured capacity">{cls}</span>;
  if (upper.includes("REPORTED"))
    return <span className="chip">{cls}</span>;
  if (upper.includes("PROJECT"))
    return <span className="chip warn">projects only</span>;
  return <span className="chip">{cls || "reported"}</span>;
}
