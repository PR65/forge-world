import { useId, useMemo, useState } from "react";
import type { SolveResponse } from "../types";
import type { Selection } from "../types";

export default function TimeView({ resp, onSelect }: {
  resp: SolveResponse;
  onSelect: (s: Selection) => void;
}) {
  const years = resp.years;
  const [item, setItem] = useState<string>("");
  const bandId = `capacity-band-${useId().replace(/:/g, "")}`;

  const shortfallItems = useMemo(() => {
    const m = new Map<string, number>();
    for (const y of Object.values(resp.result.years))
      for (const s of y.shortfalls) m.set(s.item, Math.max(m.get(s.item) ?? 0, s.shortfall));
    return [...m.entries()].sort((a, b) => b[1] - a[1]).map((e) => e[0]);
  }, [resp]);

  const selected = item || shortfallItems[0] || resp.capacity_envelopes[0]?.item || "";
  const env = resp.capacity_envelopes.find((e) => e.item === selected);

  const W = 860, H = 240, PAD = 46;
  const vals: number[] = [];
  if (env) {
    for (const y of years) {
      const e = env.by_year[String(y)];
      if (e?.lo !== null && e?.lo !== undefined) vals.push(e.lo);
      if (e?.hi !== null && e?.hi !== undefined) vals.push(e.hi);
    }
  }
  const gross = env ? env.gross_demand_annual : 0;
  const unknownYears = env
    ? years.filter((year) => {
      const point = env.by_year[String(year)];
      return point?.unknown || point?.lo === null || point?.hi === null;
    })
    : [];
  const maxV = Math.max(gross, ...vals, 1);

  const x = (i: number) => PAD + (i * (W - PAD - 16)) / Math.max(years.length - 1, 1);
  const yv = (v: number) => H - 30 - (v / maxV) * (H - 60);

  return (
    <div className="legacy-view">
      <div className="grid2 time-grid">
        <div className="card">
          <h4>Capacity vs requirement through time</h4>
          <label className="sr-only" htmlFor="time-envelope-item">Capacity-envelope item</label>
          <select
            id="time-envelope-item"
            name="time-envelope-item"
            autoComplete="off"
            value={selected}
            onChange={(e) => setItem(e.target.value)}
            style={{ marginBottom: 10, maxWidth: 420 }}
          >
            {(shortfallItems.length > 0 ? shortfallItems : resp.capacity_envelopes.map((e) => e.item))
              .map((it) => (
                <option key={it} value={it}>{it}</option>
              ))}
          </select>
          {env ? (
            <svg className="frontier-svg" width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Capacity envelope and gross annual requirement for ${selected}`}>
              <defs>
                <linearGradient id={bandId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(110,166,200,0.35)" />
                  <stop offset="100%" stopColor="rgba(110,166,200,0.08)" />
                </linearGradient>
              </defs>
              {[0.25, 0.5, 0.75, 1].map((f) => (
                <g key={f}>
                  <line className="axis" x1={PAD} x2={W - 16} y1={yv(maxV * f)} y2={yv(maxV * f)} strokeDasharray="2 4" />
                  <text x={8} y={yv(maxV * f) + 3}>{fmtAxis(maxV * f)}</text>
                </g>
              ))}
              {(() => {
                const segments: { lo: string[]; hi: string[] }[] = [];
                let current: { lo: string[]; hi: string[] } | null = null;
                years.forEach((yy, i) => {
                  const e = env.by_year[String(yy)];
                  const lo = e?.lo;
                  const hi = e?.hi;
                  if (hi === null || hi === undefined || lo === null || lo === undefined) {
                    current = null;
                    return;
                  }
                  if (!current) {
                    current = { lo: [], hi: [] };
                    segments.push(current);
                  }
                  current.hi.push(`${x(i)},${yv(hi)}`);
                  current.lo.push(`${x(i)},${yv(lo)}`);
                });
                const grossY = yv(gross);
                return (
                  <>
                    {segments.map((segment, index) => (
                      <path
                        key={index}
                        d={`M${segment.hi.join("L")}L${[...segment.lo].reverse().join("L")}Z`}
                        fill={`url(#${bandId})`}
                        stroke="none"
                      />
                    ))}
                    {years.map((year, index) => {
                      if (!unknownYears.includes(year)) return null;
                      return (
                        <g key={`unknown-${year}`}>
                          <line x1={x(index)} x2={x(index)} y1={24} y2={H - 30} stroke="var(--violet)" strokeDasharray="3 4" opacity={0.7} />
                          <circle cx={x(index)} cy={24} r={3} fill="var(--violet)"><title>{`${year}: capacity UNKNOWN`}</title></circle>
                        </g>
                      );
                    })}
                    <line x1={PAD} x2={W - 16} y1={grossY} y2={grossY} stroke="#ff6a3d" strokeWidth={1.6} strokeDasharray="6 4" />
                    <text x={W - 120} y={grossY - 6} fill="#ff6a3d">gross requirement</text>
                  </>
                );
              })()}
              {years.map((yy, i) => (
                <text key={yy} x={x(i) - 12} y={H - 8}>{yy}</text>
              ))}
            </svg>
          ) : (
            <div className="small">No envelope data.</div>
          )}
          <div className="small" style={{ marginTop: 6 }}>
            Band = domestic qualified effective-capacity envelope (lo–hi across evidence and
            unproven projects). Dashed = gross annual requirement incl. yield losses.
            {unknownYears.length > 0 && (
              <span style={{ color: "var(--violet)" }}> Capacity is UNKNOWN in {unknownYears.join(", ")}; gaps are not connected or interpolated.</span>
            )}
          </div>
        </div>

        <div className="card">
          <h4>Project pipeline (state machines)</h4>
          {resp.capacity_envelopes
            .flatMap((e) => (e.suppliers.length ? [] : [e]))
            .slice(0, 0).length === 0 && null}
          <ProjectList resp={resp} onSelect={onSelect} />
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h4>Transformation plan — sequenced on the physical clock</h4>
        {resp.plan.timeline.length === 0 && <div className="small">No actions required.</div>}
        {resp.plan.timeline.map((row) => {
          const span = Math.max(...resp.plan.timeline.map((t) => t.online_latest)) - Math.min(...resp.plan.timeline.map((t) => t.start_year)) + 2;
          const t0 = Math.min(...resp.plan.timeline.map((t) => t.start_year));
          const left = ((row.start_year - t0) / span) * 100;
          const wEarly = ((row.online_earliest - row.start_year) / span) * 100;
          const wLate = ((row.online_latest - row.start_year) / span) * 100;
          const kindColor: Record<string, string> = {
            FUND_PROJECT: "linear-gradient(90deg,#3d5a70,var(--steel))",
            QUALIFY: "linear-gradient(90deg,#8a6d2b,var(--amber))",
            SUBSTITUTE: "linear-gradient(90deg,#5a3d8a,var(--violet))",
            RESEARCH: "linear-gradient(90deg,#556,var(--ink-faint))",
            STOCKPILE: "linear-gradient(90deg,#2b6d5a,var(--green))",
          };
          return (
            <div key={row.action} className="gantt-row">
              <span className="bar-label" title={row.action}>{row.kind} · {row.action.length > 34 ? row.action.slice(0, 33) + "…" : row.action}</span>
              <div className="gantt-track">
                <div
                  className="gantt-bar"
                  style={{
                    left: `${left}%`,
                    width: `${Math.max(wLate, 3)}%`,
                    background: kindColor[row.kind] ?? "var(--steel-dim)",
                  }}
                  title={`${row.start_year} → online ${row.online_earliest}–${row.online_latest}`}
                >
                  {row.capex_musd > 0 ? `$${row.capex_musd.toFixed(0)}M` : ""}
                </div>
                <div
                  className="gantt-bar"
                  style={{ left: `${left + wEarly}%`, width: `${Math.max(wLate - wEarly, 0.5)}%`, background: "rgba(255,255,255,0.08)" }}
                />
              </div>
            </div>
          );
        })}
        <div className="small" style={{ marginTop: 6 }}>
          Bright segment = optimistic→pessimistic online window (lead-time distributions).
          Verified portfolio result: <b>{resp.plan.verified_result_class.replace(/_/g, " ")}</b>.
        </div>
      </div>
    </div>
  );
}

function ProjectList({ resp, onSelect }: { resp: SolveResponse; onSelect: (s: Selection) => void }) {
  const seen = new Set<string>();
  const rows: { id: string; label: string; state: string; cap: string | null; window: string }[] = [];
  const envByItem = new Map(resp.capacity_envelopes.map((e) => [e.item, e]));
  for (const e of resp.capacity_envelopes) {
    for (const [yy, ey] of Object.entries(e.by_year)) {
      if (ey.projects_only && !seen.has(e.item)) {
        seen.add(e.item);
        rows.push({
          id: e.item,
          label: e.item,
          state: "project-only",
          cap: fmtAxis(ey.hi ?? 0),
          window: `from ${yy}`,
        });
      }
    }
  }
  if (rows.length === 0)
    return (
      <div className="small">
        No items currently depend on unproven projects for their optimistic envelope.
      </div>
    );
  return (
    <>
      {rows.map((r) => (
        <button
          type="button"
          key={r.id}
          className="bar-row clickable data-button"
          style={{ gridTemplateColumns: "150px 90px 1fr" }}
          onClick={() => onSelect({ kind: "item", id: r.id })}
        >
          <span className="bar-label">{r.label}</span>
          <span className="chip warn">{r.state}</span>
          <span className="bar-val num">{r.cap} @ {r.window}</span>
        </button>
      ))}
    </>
  );
}

function fmtAxis(v: number): string {
  if (v >= 1e9) return (v / 1e9).toFixed(1) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(0) + "k";
  return v.toFixed(0);
}
