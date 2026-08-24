import type { SolveResponse, WorldSummary } from "./types";

interface ClockStripProps {
  deadlineYear: number;
  resp: SolveResponse | null;
  unknownCount: number;
  worldSummary: WorldSummary | null;
}

/** Three clocks stay visible because physical progress, evidence, and decisions do not share a timeline. */
export default function ClockStrip({ deadlineYear, resp, unknownCount, worldSummary }: ClockStripProps) {
  const horizon = resp?.years?.[resp.years.length - 1] ?? deadlineYear;
  const snapshot = worldSummary?.snapshot_id?.replace("registry-snapshot:", "") ?? worldSummary?.hash?.slice(0, 16);
  const registryUnknown = worldSummary?.epistemic_counts?.UNKNOWN ?? 0;
  const evidenceValue = !resp
    ? (worldSummary ? "run not compiled" : "UNKNOWN")
    : unknownCount > 0
      ? `${unknownCount} run-blocking UNKNOWN`
      : registryUnknown > 0
        ? `0 run blockers · ${registryUnknown} registry UNKNOWN`
        : "no blockers flagged";
  return (
    <section className="clock-strip" aria-label="Industrial clocks">
      <div className="clock-intro">
        <span className="eyebrow">WORLD CLOCKS</span>
        <span className="clock-caption">separate the thing, the proof, and the decision</span>
      </div>
      <div className="clock-track" role="list">
        <Clock
          tone="physical"
          label="PHYSICAL"
          value={horizon ? `through ${horizon}` : "UNKNOWN"}
          detail={`target horizon ${deadlineYear}`}
          status={resp ? "modelled" : "scenario"}
        />
        <Clock
          tone="evidence"
          label="EVIDENCE"
          value={evidenceValue}
          detail={worldSummary ? `${worldSummary.nodes.toLocaleString()} nodes · ${registryUnknown} UNKNOWN · snapshot ${snapshot ?? "UNKNOWN"}` : "registry status UNKNOWN"}
          status={unknownCount > 0 || registryUnknown > 0 ? "unknown" : worldSummary ? "reported" : "unknown"}
        />
        <Clock
          tone="decision"
          label="DECISION"
          value="not recorded"
          detail={resp ? `run ${resp.run.run_id.slice(0, 12)}` : "awaiting a run"}
          status="unknown"
        />
      </div>
    </section>
  );
}

function Clock({
  tone,
  label,
  value,
  detail,
  status,
}: {
  tone: "physical" | "evidence" | "decision";
  label: string;
  value: string;
  detail: string;
  status: "modelled" | "reported" | "scenario" | "unknown";
}) {
  return (
    <div className={`clock clock-${tone}`} role="listitem">
      <span className="clock-marker" aria-hidden="true" />
      <div>
        <div className="clock-label">{label}</div>
        <div className="clock-value">{value}</div>
        <div className="clock-detail">{detail} · <span className={`status-text status-${status}`}>{status.toUpperCase()}</span></div>
      </div>
    </div>
  );
}
