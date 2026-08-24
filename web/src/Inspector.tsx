import { useEffect, useMemo, useState } from "react";
import { fetchWorldEvidence } from "./api";
import type { EnvelopeYear, Selection, SolveResponse, WorldEvidenceRecord, WorldNode } from "./types";
import { epistemicChipClass, epistemicLabel } from "./epistemics";

export default function Inspector({ sel, resp, packDetail, onSelect, worldNode }: {
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
  worldNode?: WorldNode | null;
}) {
  const pg = resp?.proof_graph;
  const sid = sel?.id ?? "";
  const [worldEvidence, setWorldEvidence] = useState<WorldEvidenceRecord | null>(null);
  const [worldEvidenceLoading, setWorldEvidenceLoading] = useState(false);

  useEffect(() => {
    let active = true;
    if (sel?.kind !== "evidence" || !sid.startsWith("pack:")) {
      setWorldEvidence(null);
      setWorldEvidenceLoading(false);
      return () => { active = false; };
    }
    setWorldEvidence(null);
    setWorldEvidenceLoading(true);
    void fetchWorldEvidence(sid).then((record) => {
      if (!active) return;
      setWorldEvidence(record);
      setWorldEvidenceLoading(false);
    });
    return () => { active = false; };
  }, [sel?.kind, sid]);

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
  const localEvidenceId = sid.includes(":evidence:") ? sid.split(":evidence:").pop() ?? sid : sid;
  const localEvidence = packDetail?.evidence.filter((record) => record.claim_id === localEvidenceId) ?? [];

  return (
    <aside className="inspector" aria-label="WHY inspector">
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
          <div className="insp-title">{sel.kind === "item" ? sel.id : (worldNode?.name ?? sel.id) || "selection"}</div>
          <div className="insp-kind">{sel.kind}</div>
        </div>
      )}

      {(sel?.kind === "world" || sel?.kind === "capability") && worldNode && (
        <div className="insp-body">
          <div className="card" style={{ padding: 12 }}>
            <h4>World record</h4>
            <div className="kv">
              <span className="k">canonical id</span><span className="v">{worldNode.canonical_id ?? "UNKNOWN"}</span>
              <span className="k">kind</span><span className="v">{worldNode.kind}</span>
              <span className="k">epistemic class</span><span className="v"><EpistemicChip cls={worldNode.epistemic_class} /></span>
              <span className="k">pack</span><span className="v">{worldNode.pack_id ?? "UNKNOWN"}</span>
            </div>
            <div className="small inspector-why-note">WHY remains attached to the selected record. No capability is inferred from a label alone.</div>
          </div>
          <div className="card" style={{ padding: 12, marginTop: 12 }}>
            <h4>Registry metadata</h4>
            {Object.keys(worldNode.metadata).length === 0 ? <div className="small">UNKNOWN · no metadata returned.</div> : <div className="metadata-list">{Object.entries(worldNode.metadata).slice(0, 18).map(([key, value]) => <div className="metadata-row" key={key}><span>{key}</span><strong>{formatMetadata(value)}</strong></div>)}</div>}
          </div>
          <div className="card" style={{ padding: 12, marginTop: 12 }}>
            <h4>Evidence ids</h4>
            {worldNode.evidence_ids.length ? worldNode.evidence_ids.map((id) => <button type="button" className="evidence-link" key={id} onClick={() => onSelect({ kind: "evidence", id })}>{id} ↗</button>) : <div className="small">UNKNOWN · no evidence ids returned.</div>}
          </div>
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
                <button
                  type="button"
                  className="evidence-link"
                  style={{ marginTop: 4 }}
                  onClick={() => onSelect({ kind: "evidence", id: node.node_id.replace("ev.", "") })}
                >
                  open evidence record →
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {sel?.kind === "evidence" && (
        <div className="insp-body">
          {worldEvidenceLoading && <div className="small" role="status">Loading immutable evidence record…</div>}
          {worldEvidence && (
            <div className="ev-card">
              <span className={`ev-class ${worldEvidence.epistemic_class}`}>{worldEvidence.epistemic_class}</span>
              <div className="num small" style={{ marginTop: 6 }}>
                {worldEvidence.subject} · {worldEvidence.predicate}
              </div>
              <div className="ev-quote">{worldEvidence.value_text || "(qualitative claim)"}</div>
              {worldEvidence.quote_or_caveat && <div className="ev-caveat">⚠ {worldEvidence.quote_or_caveat}</div>}
              <div className="ev-src">
                {worldEvidence.source_snapshots.map((source) => (
                  <div key={source.snapshot_id || source.source_id}>
                    {formatMetadata(source.metadata.publisher)} — {formatMetadata(source.metadata.name)}
                    {source.url ? <>{" "}<a href={source.url} target="_blank" rel="noreferrer" style={{ color: "var(--steel)" }}>[link]</a></> : null}{" "}
                    · {source.license} · accessed {source.access_date || "UNKNOWN"}
                    <div>snapshot {source.content_hash.slice(0, 16)} · hash scope {source.hash_scope} · raw payload {source.raw_payload_stored ? "stored" : "not stored"}</div>
                  </div>
                ))}
                {worldEvidence.source_snapshots.length === 0 && <div>UNKNOWN · no source snapshot resolved.</div>}
              </div>
            </div>
          )}
          {!worldEvidence && !worldEvidenceLoading && localEvidence.map((e) => (
            <div key={e.claim_id} className="ev-card">
              <span className={`ev-class ${e.epistemic_class}`}>{e.epistemic_class}</span>
              <div className="num small" style={{ marginTop: 6 }}>
                {e.subject} · {e.predicate}
              </div>
              <div className="ev-quote">{e.value_text || "(qualitative claim)"}</div>
              {e.quote_or_caveat && <div className="ev-caveat">⚠ {e.quote_or_caveat}</div>}
              <div className="ev-src">
                {e.source_ids.map((sourceId) => {
                  const source = packDetail?.sources.find((candidate) => candidate.id === sourceId);
                  return source ? (
                    <div key={sourceId}>
                      {source.publisher} — {source.name}
                      {source.url ? <>{" "}<a href={source.url} target="_blank" rel="noreferrer" style={{ color: "var(--steel)" }}>[link]</a></> : null}{" "}
                      · {source.license} · accessed {source.access_date}
                    </div>
                  ) : <div key={sourceId}>{sourceId}</div>;
                })}
              </div>
              {Object.keys(e.confidence).length > 0 && (
                <div className="small" style={{ marginTop: 6 }}>
                  confidence:{" "}
                  {Object.entries(e.confidence)
                    .filter(([, value]) => value !== null)
                    .map(([key, value]) => `${key} ${((value as number) * 100).toFixed(0)}%`)
                    .join(" · ")}
                </div>
              )}
            </div>
          ))}
          {!worldEvidenceLoading && !worldEvidence && localEvidence.length === 0 && <div className="small">UNKNOWN · the selected evidence record was not returned.</div>}
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

function formatMetadata(value: unknown): string {
  if (value === null || value === undefined) return "UNKNOWN";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return "UNKNOWN";
  }
}

export function EpistemicChip({ cls }: { cls: string }) {
  return <span className={`chip ${epistemicChipClass(cls)}`}>{epistemicLabel(cls)}</span>;
}
