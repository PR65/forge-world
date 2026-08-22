import { useEffect, useRef } from "react";
import type { SolveResponse } from "../types";
import type { Selection } from "../types";

interface Node {
  id: string;
  label: string;
  demand: number;
  unit: string;
  col: number;
  status: "binding" | "unknown" | "import" | "domestic" | "ok";
  suppliers: string[];
}

const COL_W = 300;
const NODE_H = 34;
const NODE_GAP = 7;

export default function StrataView({ resp, onSelect }: {
  resp: SolveResponse;
  onSelect: (s: Selection) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  const year = String(resp.years[Math.min(resp.years.length - 1, 4)]);
  const envByItem = new Map(resp.capacity_envelopes.map((e) => [e.item, e]));
  const shortByItem = new Map<string, number>();
  for (const y of Object.values(resp.result.years)) {
    for (const s of y.shortfalls) {
      shortByItem.set(s.item, Math.max(shortByItem.get(s.item) ?? 0, s.shortfall));
    }
  }

  const nodes: Node[] = resp.explosion.items.map((it) => {
    const env = envByItem.get(it.item);
    const shortfall = shortByItem.get(it.item) ?? 0;
    let status: Node["status"] = "ok";
    const yEnv = env?.by_year[year];
    if (shortfall > 0) status = yEnv?.unknown ? "unknown" : "binding";
    else if ((env?.suppliers.length ?? 0) > 0) status = "import";
    else if ((yEnv?.lo ?? 0) > 0) status = "domestic";
    return {
      id: it.item,
      label: it.item,
      demand: it.net,
      unit: it.unit,
      col: Math.min(it.depth, 3),
      status,
      suppliers: env?.suppliers ?? [],
    };
  });

  const cols = new Map<number, Node[]>();
  for (const n of nodes) {
    if (!cols.has(n.col)) cols.set(n.col, []);
    cols.get(n.col)!.push(n);
  }
  for (const list of cols.values()) {
    list.sort((a, b) => b.demand - a.demand);
  }

  const colHeights = [...cols.keys()].map((c) => cols.get(c)!.length * (NODE_H + NODE_GAP));
  const height = Math.max(420, ...colHeights) + 40;
  const width = Math.max(900, (Math.max(...cols.keys()) + 1) * COL_W + 60);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    const ctx = canvas.getContext("2d")!;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const colors: Record<Node["status"], string> = {
      binding: "#ff6a3d",
      unknown: "#b18cff",
      import: "#ffb454",
      domestic: "#6ea6c8",
      ok: "#55c98d",
    };

    const colKeys = [...cols.keys()].sort((a, b) => a - b);
    const positions = new Map<string, { x: number; y: number; w: number }>();
    colKeys.forEach((c) => {
      const list = cols.get(c)!;
      const x = 30 + c * COL_W;
      list.forEach((n, i) => {
        positions.set(n.id, { x, y: 26 + i * (NODE_H + NODE_GAP), w: COL_W - 46 });
      });
    });

    ctx.font = "10px Consolas, monospace";
    colKeys.forEach((c) => {
      const names = ["SYSTEM", "COMPONENTS", "SUB-COMPONENTS", "MATERIALS / INPUTS"];
      ctx.fillStyle = "#6b7480";
      ctx.fillText(names[c] ?? `LAYER ${c}`, 30 + c * COL_W, 14);
    });

    const byId = new Map(nodes.map((n) => [n.id, n]));
    resp.explosion.items.forEach((it) => {
      if (!it.recipe) return;
      const from = positions.get(it.item);
      if (!from) return;
      ctx.strokeStyle = "rgba(110,166,200,0.14)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(from.x + from.w, from.y + NODE_H / 2);
      ctx.bezierCurveTo(from.x + from.w + 60, from.y + NODE_H / 2, from.x + from.w + 60, from.y + NODE_H / 2, from.x + from.w + 60, from.y + NODE_H / 2);
      ctx.stroke();
    });

    for (const [id, p] of positions) {
      const n = byId.get(id)!;
      const c = colors[n.status];
      const maxDemand = Math.max(...nodes.map((x) => x.demand), 1);
      const wScale = 0.55 + 0.45 * Math.min(1, Math.log10(1 + n.demand) / Math.log10(1 + maxDemand));
      const w = p.w * wScale;

      ctx.fillStyle = "rgba(255,255,255,0.03)";
      roundRect(ctx, p.x, p.y, p.w, NODE_H, 7);
      ctx.fill();

      ctx.fillStyle = c + (n.status === "binding" ? "" : "cc");
      roundRect(ctx, p.x, p.y, 4, NODE_H, 2);
      ctx.fill();

      ctx.strokeStyle = n.status === "binding" ? "rgba(255,106,61,0.5)" : "rgba(255,255,255,0.06)";
      roundRect(ctx, p.x, p.y, p.w, NODE_H, 7);
      ctx.stroke();

      ctx.fillStyle = "#e9e6df";
      ctx.font = "11px 'Segoe UI', sans-serif";
      const label = n.label.length > 30 ? n.label.slice(0, 29) + "…" : n.label;
      ctx.fillText(label, p.x + 12, p.y + 14);

      ctx.fillStyle = "#9aa3ad";
      ctx.font = "9.5px Consolas, monospace";
      const d = fmtDemand(n.demand) + " " + n.unit + "/yr";
      ctx.fillText(d, p.x + 12, p.y + 27);
      if (n.suppliers.length > 0) {
        ctx.fillStyle = "#6b7480";
        const sup = "⟵ " + n.suppliers.slice(0, 2).join("/");
        ctx.fillText(sup, p.x + p.w - ctx.measureText(sup).width - 10, p.y + 27);
      }

      if (n.status === "binding") {
        const t = Date.now() / 600;
        ctx.strokeStyle = `rgba(255,106,61,${0.25 + 0.2 * Math.sin(t)})`;
        roundRect(ctx, p.x - 2, p.y - 2, p.w + 4, NODE_H + 4, 9);
        ctx.stroke();
      }
    }

    canvas.onclick = (ev) => {
      const rect = canvas.getBoundingClientRect();
      const mx = ev.clientX - rect.left;
      const my = ev.clientY - rect.top;
      for (const [id, p] of positions) {
        if (mx >= p.x && mx <= p.x + p.w && my >= p.y && my <= p.y + NODE_H) {
          onSelect({ kind: "item", id });
          return;
        }
      }
    };
  }, [resp, height, width]);

  return (
    <div ref={wrapRef} style={{ padding: 12 }}>
      <div className="legend">
        <span><span className="dot" style={{ background: "#ff6a3d" }} />binding gap</span>
        <span><span className="dot" style={{ background: "#b18cff" }} />unknown capacity</span>
        <span><span className="dot" style={{ background: "#ffb454" }} />import-dependent</span>
        <span><span className="dot" style={{ background: "#6ea6c8" }} />domestic capacity</span>
        <span><span className="dot" style={{ background: "#55c98d" }} />satisfied</span>
        <span style={{ marginLeft: "auto" }}>node width ∝ log demand · click to inspect · year {year}</span>
      </div>
      <canvas ref={canvasRef} style={{ cursor: "crosshair" }} />
    </div>
  );
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function fmtDemand(n: number): string {
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + "k";
  return n.toFixed(0);
}
