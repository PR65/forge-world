import { useEffect, useId, useMemo, useState } from "react";
import type { WorldEdge, WorldNode, WorldSlice } from "./types";
import { epistemicTone } from "./epistemics";

interface WorldPlaneProps {
  world: WorldSlice | null;
  selectedId?: string;
  onSelect: (node: WorldNode) => void;
  sourceLabel?: string;
  title?: string;
}

interface Position {
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
}

const NODE_WIDTH = 228;
const NODE_HEIGHT = 68;
const X_GAP = 86;
const Y_GAP = 14;
const MAX_VISIBLE_NODES = 72;

/**
 * A semantic 2D plane: columns show dependency distance, while every node
 * remains a keyboard-addressable DOM/SVG control. It intentionally has no
 * geographic projection or 3D affordance.
 */
export default function WorldPlane({
  world,
  selectedId,
  onSelect,
  sourceLabel = "registry slice",
  title = "World plane",
}: WorldPlaneProps) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("ALL");
  const instanceId = useId().replace(/:/g, "");
  const titleId = `world-plane-title-${instanceId}`;
  const descriptionId = `world-plane-description-${instanceId}`;
  const statusId = `world-plane-status-${instanceId}`;
  const arrowId = `world-arrow-${instanceId}`;
  const isLoading = sourceLabel.toLowerCase().includes("loading");
  const worldIdentity = `${world?.root ?? "none"}:${world?.nodes[0]?.pack_id ?? "none"}`;

  useEffect(() => {
    setQuery("");
    setKind("ALL");
  }, [worldIdentity]);

  const kinds = useMemo(() => {
    if (!world) return [];
    return [...new Set(world.nodes.map((n) => n.kind).filter(Boolean))].sort();
  }, [world]);

  const filtered = useMemo(() => {
    if (!world) return [];
    const normalized = query.trim().toLowerCase();
    return world.nodes.filter((node) => {
      const inKind = kind === "ALL" || node.kind === kind;
      const inQuery = !normalized || [node.name, node.id, node.canonical_id ?? "", node.kind]
        .some((value) => value.toLowerCase().includes(normalized));
      return inKind && inQuery;
    });
  }, [world, query, kind]);

  const graph = useMemo(() => {
    if (!world) return null;
    return layoutGraph(world.nodes, world.edges, world.root, filtered);
  }, [world, filtered]);

  if (!world) {
    return (
      <section className="world-plane card" aria-labelledby={titleId}>
        <div className="plane-head">
          <div>
            <span className="eyebrow">SEMANTIC PLANE</span>
            <h2 id={titleId}>{title}</h2>
          </div>
          <span className={`chip ${isLoading ? "" : "unknown"}`}>{isLoading ? "LOADING · registry…" : "UNKNOWN · registry unavailable"}</span>
        </div>
        <div className="plane-empty" role="status">
          <strong>{isLoading ? "Loading the bounded world slice…" : "The world registry did not answer."}</strong>
          <span>{isLoading ? "The plane will remain empty until a registry response arrives." : "Nothing is being inferred from its absence. Run state and proof records remain available in the other lenses."}</span>
        </div>
      </section>
    );
  }

  const visibleNodes = graph?.nodes ?? [];
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = world.edges.filter((edge) => visibleIds.has(edge.src) && visibleIds.has(edge.dst));
  const hasSearch = query.trim().length > 0 || kind !== "ALL";
  const showingText = hasSearch
    ? `${filtered.length} matching node${filtered.length === 1 ? "" : "s"} · ${visibleNodes.length} shown`
    : `${world.nodes.length} nodes`;
  const displayCapped = filtered.length > MAX_VISIBLE_NODES;

  return (
    <section className="world-plane card" aria-labelledby={titleId}>
      <div className="plane-head">
        <div>
          <span className="eyebrow">SEMANTIC PLANE · 2D DEPENDENCY SPACE</span>
          <h2 id={titleId}>{title}</h2>
          <p className="plane-subtitle">{showingText} · edges preserve the registry relation, not a geographic claim</p>
          {sourceLabel.toLowerCase().includes("baseline") && <p className="plane-subtitle">Scenario shocks and funding deltas are not overlaid on this immutable registry slice; inspect the solved branch lenses for their effects.</p>}
        </div>
        <div className="plane-meta">
          <span className="chip">{sourceLabel}</span>
          {world.truncated && <span className="chip warn">TRUNCATED · lazy slice</span>}
          {displayCapped && <span className="chip warn">VIEW CAP {MAX_VISIBLE_NODES} · FILTER TO REFINE</span>}
        </div>
      </div>

      <div className="plane-controls">
        <label className="plane-search">
          <span className="sr-only">Search world nodes</span>
          <input
            type="search"
            name="world-node-search"
            autoComplete="off"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Find a component, process, capability…"
            aria-describedby={statusId}
          />
        </label>
        <label className="plane-kind">
          <span className="sr-only">Filter world node kind</span>
          <select name="world-node-kind" autoComplete="off" value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="ALL">all kinds</option>
            {kinds.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <span id={statusId} className="small" role="status">{visibleNodes.length} shown · click or tab to inspect</span>
      </div>

      {visibleNodes.length === 0 ? (
        <div className="plane-empty" role="status">
          <strong>No nodes match this view.</strong>
          <span>Clear the search or kind filter. Empty results are not treated as missing capability.</span>
        </div>
      ) : (
        <>
          <div className="plane-scroll" tabIndex={0} aria-label="Scrollable world plane">
            <svg
              className="world-svg"
              role="group"
              aria-labelledby={`${titleId} ${descriptionId}`}
              viewBox={`0 0 ${graph?.width ?? 920} ${graph?.height ?? 420}`}
              preserveAspectRatio="xMinYMin meet"
            >
              <desc id={descriptionId}>
                A two-dimensional dependency graph. Columns represent distance from the selected root, not physical geography.
              </desc>
              <defs>
                <marker id={arrowId} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                  <path d="M0,0 L7,3.5 L0,7 z" fill="var(--line2)" />
                </marker>
              </defs>
              <g className="plane-columns" aria-hidden="true">
                {Array.from({ length: (graph?.maxDepth ?? 0) + 1 }, (_, depth) => (
                  <g key={depth}>
                    <line x1={24 + depth * (NODE_WIDTH + X_GAP)} y1={34} x2={24 + depth * (NODE_WIDTH + X_GAP)} y2={(graph?.height ?? 420) - 18} />
                    <text x={32 + depth * (NODE_WIDTH + X_GAP)} y={20}>DEPTH {depth}</text>
                  </g>
                ))}
              </g>
              <g className="plane-edges" aria-hidden="true">
                {visibleEdges.map((edge) => {
                  const from = graph?.positions.get(edge.src);
                  const to = graph?.positions.get(edge.dst);
                  if (!from || !to) return null;
                  const x1 = from.x + from.width;
                  const y1 = from.y + from.height / 2;
                  const x2 = to.x;
                  const y2 = to.y + to.height / 2;
                  const bend = Math.max(26, Math.abs(x2 - x1) / 2);
                  return (
                    <path
                      key={`${edge.src}:${edge.relation}:${edge.dst}`}
                      d={`M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`}
                      markerEnd={`url(#${arrowId})`}
                    >
                      <title>{`${edge.src} ${edge.relation} ${edge.dst}`}</title>
                    </path>
                  );
                })}
              </g>
              <g className="plane-nodes">
                {visibleNodes.map((node) => {
                  const position = graph?.positions.get(node.id);
                  if (!position) return null;
                  const state = nodeState(node);
                  const selected = selectedId === node.id;
                  return (
                    <g
                      key={node.id}
                      className={`world-node world-node-${state}${selected ? " is-selected" : ""}`}
                      transform={`translate(${position.x}, ${position.y})`}
                      role="button"
                      tabIndex={0}
                      aria-pressed={selected}
                      aria-label={`${node.name}, ${node.kind}, evidence state ${node.epistemic_class}`}
                      onClick={() => onSelect(node)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onSelect(node);
                        }
                      }}
                    >
                      <rect className="world-node-bg" width={position.width} height={position.height} rx={9} />
                      <rect className="world-node-rule" width={4} height={position.height} rx={2} />
                      <text className="world-node-kind" x={14} y={17}>{node.kind.toUpperCase()}</text>
                      <text className="world-node-name" x={14} y={37}>{shorten(node.name, 31)}</text>
                      <text className="world-node-status" x={14} y={55}>{node.epistemic_class.toUpperCase()}</text>
                      {node.evidence_ids.length > 0 && <text className="world-node-evidence" x={position.width - 12} y={55} textAnchor="end">{node.evidence_ids.length} EVIDENCE</text>}
                      <title>{`${node.name} · ${node.kind} · ${node.epistemic_class}`}</title>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>
          <div className="world-node-list" aria-label="World node list">
            {visibleNodes.slice(0, 18).map((node) => (
              <button
                type="button"
                className={`world-list-item${selectedId === node.id ? " selected" : ""}`}
                key={node.id}
                onClick={() => onSelect(node)}
              >
                <span className={`node-status-dot node-status-${nodeState(node)}`} aria-hidden="true" />
                <span className="world-list-copy">
                  <strong>{node.name}</strong>
                  <small>{node.kind} · {node.epistemic_class}</small>
                </span>
                <span className="world-list-arrow" aria-hidden="true">↗</span>
              </button>
            ))}
            {visibleNodes.length > 18 && <span className="small world-list-more">{visibleNodes.length - 18} more nodes available in the plane</span>}
          </div>
        </>
      )}
    </section>
  );
}

function layoutGraph(nodes: WorldNode[], edges: WorldEdge[], root: string | null, filtered: WorldNode[]) {
  const filteredIds = new Set(filtered.map((node) => node.id));
  const candidates = [
    ...(root && filteredIds.has(root) ? filtered.filter((node) => node.id === root) : []),
    ...filtered.filter((node) => node.id !== root),
  ].slice(0, MAX_VISIBLE_NODES);
  const candidateIds = new Set(candidates.map((node) => node.id));
  const neighbors = new Map<string, string[]>();
  for (const node of candidates) neighbors.set(node.id, []);
  for (const edge of edges) {
    if (!candidateIds.has(edge.src) || !candidateIds.has(edge.dst)) continue;
    neighbors.get(edge.src)?.push(edge.dst);
    neighbors.get(edge.dst)?.push(edge.src);
  }

  const rootId = root && candidateIds.has(root) ? root : candidates[0]?.id;
  const depths = new Map<string, number>();
  if (rootId) {
    depths.set(rootId, 0);
    const queue = [rootId];
    while (queue.length) {
      const id = queue.shift()!;
      const depth = depths.get(id) ?? 0;
      for (const neighbor of neighbors.get(id) ?? []) {
        if (!depths.has(neighbor)) {
          depths.set(neighbor, Math.min(depth + 1, 4));
          queue.push(neighbor);
        }
      }
    }
  }
  for (const node of candidates) if (!depths.has(node.id)) depths.set(node.id, 0);

  const columns = new Map<number, WorldNode[]>();
  for (const node of candidates) {
    const depth = depths.get(node.id) ?? 0;
    const column = columns.get(depth) ?? [];
    column.push(node);
    columns.set(depth, column);
  }
  for (const column of columns.values()) column.sort((a, b) => a.name.localeCompare(b.name));
  if (rootId) {
    const column = columns.get(0) ?? [];
    column.sort((a, b) => (a.id === rootId ? -1 : b.id === rootId ? 1 : a.name.localeCompare(b.name)));
  }

  const positions = new Map<string, Position>();
  let maxRows = 1;
  let maxDepth = 0;
  for (const [depth, column] of columns) {
    maxDepth = Math.max(maxDepth, depth);
    maxRows = Math.max(maxRows, column.length);
    column.forEach((node, row) => {
      positions.set(node.id, {
        x: 24 + depth * (NODE_WIDTH + X_GAP),
        y: 48 + row * (NODE_HEIGHT + Y_GAP),
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        depth,
      });
    });
  }
  return {
    nodes: candidates,
    positions,
    width: 48 + (maxDepth + 1) * (NODE_WIDTH + X_GAP),
    height: Math.max(420, 86 + maxRows * (NODE_HEIGHT + Y_GAP)),
    maxDepth,
  };
}

function nodeState(node: WorldNode): "unknown" | "conflicted" | "uncertain" | "evidenced" | "neutral" {
  const tone = epistemicTone(node.epistemic_class);
  if (tone === "unknown") return "unknown";
  if (tone === "conflicted") return "conflicted";
  if (["assumption", "scenario", "estimated"].includes(tone)) return "uncertain";
  if (tone === "measured" || tone === "reported") return "evidenced";
  return "neutral";
}

function shorten(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}
