import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ObjectiveConfig,
  PackDetail,
  ProductMode,
  Selection,
  SolveResponse,
  WorldNode,
  WorldSlice,
} from "./types";
import {
  fetchPackDetailSafe,
  fetchPacksSafe,
  fetchWorldCapabilities,
  fetchWorldSlice,
  fetchWorldSummary,
  solveObjective,
} from "./api";
import Inspector from "./Inspector";
import ClockStrip from "./ClockStrip";
import ModeViews from "./ModeViews";
import ScenarioRail, { BranchHeader } from "./ScenarioRail";

const PRODUCT_MODES: ProductMode[] = ["ANALYZE", "DESIGN", "EXECUTE", "DISCOVER", "LEARN"];
const PACK_STARTING_OUTPUTS: Record<string, number> = {
  battery_gwh_india: 500000,
  cnc_machining_india: 100,
  humanoid_india: 1000000,
  nuclear_buildout_india: 1,
  smallsat_india: 50,
};

const DEFAULT_CONFIG: ObjectiveConfig = {
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
};

export default function App() {
  const [packList, setPackList] = useState<{ pack_id: string; title: string; variants: string[] }[]>([]);
  const [packDetail, setPackDetail] = useState<PackDetail | null>(null);
  const [cfg, setCfg] = useState<ObjectiveConfig>(DEFAULT_CONFIG);
  const [resp, setResp] = useState<SolveResponse | null>(null);
  const [compiledCfg, setCompiledCfg] = useState<ObjectiveConfig | null>(null);
  const [baseResp, setBaseResp] = useState<SolveResponse | null>(null);
  const [baseCfg, setBaseCfg] = useState<ObjectiveConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<ProductMode>("ANALYZE");
  const [sel, setSel] = useState<Selection | null>(null);
  const [nlText, setNlText] = useState("");
  const [nlNote, setNlNote] = useState<string | null>(null);
  const [worldSlice, setWorldSlice] = useState<WorldSlice | null>(null);
  const [worldSummary, setWorldSummary] = useState<Awaited<ReturnType<typeof fetchWorldSummary>>>(null);
  const [capabilities, setCapabilities] = useState<Awaited<ReturnType<typeof fetchWorldCapabilities>>>(null);
  const [worldLoading, setWorldLoading] = useState(true);
  const [packLoading, setPackLoading] = useState(true);
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true);
  const solveGeneration = useRef(0);
  const parseGeneration = useRef(0);
  const parseController = useRef<AbortController | null>(null);
  const cfgRef = useRef<ObjectiveConfig>(DEFAULT_CONFIG);
  const baseCfgRef = useRef<ObjectiveConfig | null>(null);
  cfgRef.current = cfg;
  baseCfgRef.current = baseCfg;

  const updateConfig = useCallback((patch: Partial<ObjectiveConfig>) => {
    if (typeof patch.packId === "string" && patch.packId !== cfgRef.current.packId) {
      solveGeneration.current += 1;
      parseGeneration.current += 1;
      parseController.current?.abort();
      setBusy(false);
      setResp(null);
      setCompiledCfg(null);
      setBaseResp(null);
      setBaseCfg(null);
      baseCfgRef.current = null;
      setSel(null);
      setPackDetail(null);
      setWorldSlice(null);
      const next = {
        ...cfgRef.current,
        ...patch,
        variantId: typeof patch.variantId === "string" ? patch.variantId : "",
        annualUnits: typeof patch.annualUnits === "number"
          ? patch.annualUnits
          : PACK_STARTING_OUTPUTS[patch.packId] ?? cfgRef.current.annualUnits,
        fundedProjects: patch.fundedProjects ? [...patch.fundedProjects] : [],
        shocks: patch.shocks ? [...patch.shocks] : [],
        assumptions: patch.assumptions ? { ...patch.assumptions } : {},
      };
      cfgRef.current = next;
      setCfg(next);
      return;
    }
    if (typeof patch.variantId === "string") {
      solveGeneration.current += 1;
      parseGeneration.current += 1;
      parseController.current?.abort();
      setBusy(false);
      setResp(null);
      setCompiledCfg(null);
      setSel(null);
    }
    const next = { ...cfgRef.current, ...patch };
    cfgRef.current = next;
    setCfg(next);
  }, []);

  const run = useCallback(async (override?: Partial<ObjectiveConfig>) => {
    const next = cloneConfig({ ...cfgRef.current, ...override });
    if (!next.packId || !next.variantId) {
      setErr("Select a loaded knowledge pack and reference architecture before compiling.");
      return;
    }
    if (!Number.isFinite(next.annualUnits) || next.annualUnits <= 0) {
      setErr("Annual output must be a finite number greater than zero.");
      return;
    }
    if (!next.geography.trim()) {
      setErr("Geography is required.");
      return;
    }
    const knownPack = packList.find((pack) => pack.pack_id === next.packId);
    if (knownPack && !knownPack.variants.includes(next.variantId)) {
      setErr(`Architecture '${next.variantId}' does not belong to '${next.packId}'.`);
      return;
    }
    const generation = solveGeneration.current + 1;
    solveGeneration.current = generation;
    setBusy(true);
    setErr(null);
    try {
      const result = await solveObjective(next);
      if (generation !== solveGeneration.current) return;
      setResp(result);
      setCompiledCfg(cloneConfig(next));
      const currentBase = baseCfgRef.current;
      const shouldCaptureBaseline = next.shocks.length === 0
        && next.fundedProjects.length === 0
        && (!currentBase || currentBase.packId !== next.packId);
      if (shouldCaptureBaseline) {
        const saved = cloneConfig(next);
        baseCfgRef.current = saved;
        setBaseResp(result);
        setBaseCfg(saved);
      }
    } catch (error) {
      if (generation !== solveGeneration.current) return;
      setErr(error instanceof Error ? error.message : String(error));
    } finally {
      if (generation === solveGeneration.current) setBusy(false);
    }
  }, [packList]);

  const applyNl = useCallback(async () => {
    if (!nlText.trim()) return;
    const generation = parseGeneration.current + 1;
    parseGeneration.current = generation;
    parseController.current?.abort();
    const controller = new AbortController();
    parseController.current = controller;
    const startedIdentity = configIdentity(cfgRef.current);
    setNlNote("Parsing into inspectable objective fields…");
    try {
      const response = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: nlText }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`parse: ${response.status}`);
      const parsed = await response.json() as {
        objective?: {
          variant_id?: string;
          annual_units?: number;
          geography?: string;
          deadline_year?: number;
          min_dva?: number;
          budget_usd?: number | null;
          funded_projects?: string[];
        };
        interpretations?: string[];
        unresolved?: string[];
        shocks?: string[];
      };
      if (generation !== parseGeneration.current || configIdentity(cfgRef.current) !== startedIdentity) {
        setNlNote("Parse result ignored because the scenario changed while parsing.");
        return;
      }
      if (parsed.objective) {
        const patch: Partial<ObjectiveConfig> = {};
        const parsedVariant = parsed.objective.variant_id;
        if (parsedVariant) {
          const parsedPack = packList.find((pack) => pack.variants.includes(parsedVariant));
          if (parsedPack) {
            patch.packId = parsedPack.pack_id;
            patch.variantId = parsedVariant;
          }
        }
        if (typeof parsed.objective.annual_units === "number") patch.annualUnits = parsed.objective.annual_units;
        if (typeof parsed.objective.geography === "string") patch.geography = parsed.objective.geography;
        if (typeof parsed.objective.deadline_year === "number") patch.deadlineYear = parsed.objective.deadline_year;
        if (typeof parsed.objective.min_dva === "number") patch.minDva = parsed.objective.min_dva;
        if (typeof parsed.objective.budget_usd === "number" || parsed.objective.budget_usd === null) patch.budgetUsd = parsed.objective.budget_usd;
        if (Array.isArray(parsed.objective.funded_projects)) patch.fundedProjects = parsed.objective.funded_projects;
        if (Array.isArray(parsed.shocks)) patch.shocks = parsed.shocks;
        updateConfig(patch);
        setNlNote(`${parsed.interpretations?.join(" · ") ?? "objective parsed"}${parsed.unresolved?.length ? ` | unresolved: ${parsed.unresolved.join(", ")}` : ""}`);
        void run(patch);
      } else {
        if (parsed.shocks?.length) updateConfig({ shocks: parsed.shocks });
        setNlNote(parsed.interpretations?.join(" · ") || "no interpretable objective found — edit fields below");
        if (parsed.shocks?.length) void run({ shocks: parsed.shocks });
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setNlNote("parse unavailable — edit fields directly below");
    }
  }, [nlText, packList, run, updateConfig]);

  useEffect(() => {
    let active = true;
    void fetchPacksSafe().then((packs) => {
      if (!active) return;
      setPackList(packs);
      setPackLoading(false);
      if (packs.length > 0 && !packs.some((pack) => pack.pack_id === cfg.packId)) updateConfig({ packId: packs[0].pack_id, variantId: "" });
    });
    void fetchWorldSummary().then((summary) => {
      if (active) setWorldSummary(summary);
    });
    void fetchWorldCapabilities().then((records) => {
      if (!active) return;
      setCapabilities(records);
      setCapabilitiesLoading(false);
    });
    return () => { active = false; };
    // Initial fetches are deliberately parallel; pack changes are handled below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let active = true;
    setWorldSlice(null);
    setWorldLoading(true);
    if (!cfg.packId || !cfg.variantId) return () => { active = false; };
    void fetchWorldSlice(cfg.packId, cfg.variantId, 6, 200).then((slice) => {
      if (!active) return;
      setWorldSlice(slice);
      setWorldLoading(false);
    });
    return () => { active = false; };
  }, [cfg.packId, cfg.variantId]);

  useEffect(() => {
    let active = true;
    void fetchPackDetailSafe(cfg.packId).then((detail) => {
      if (!active) return;
      setPackDetail(detail);
      if (detail) {
        setCfg((current) => {
          const next = {
            ...current,
          variantId: detail.variants.some((variant) => variant.id === current.variantId) ? current.variantId : detail.variants[0]?.id ?? "",
          shocks: current.shocks.filter((id) => detail.shocks.some((shock) => shock.id === id)),
          fundedProjects: current.fundedProjects.filter((id) => detail.projects.some((project) => project.id === id)),
          };
          cfgRef.current = next;
          return next;
        });
      } else {
        setWorldLoading(false);
      }
    });
    return () => { active = false; };
  }, [cfg.packId]);

  useEffect(() => {
    if (cfg.packId && cfg.variantId && !resp && !busy) void run();
    // Only bootstrap a run once the pack and architecture are known.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg.packId, cfg.variantId]);

  const isStale = Boolean(resp && (!compiledCfg || configIdentity(cfg) !== configIdentity(compiledCfg)));
  const activeResp = isStale ? null : resp;
  const effectiveWorld = useMemo(() => worldSlice ?? (activeResp ? deriveWorldSlice(activeResp, cfg.packId) : null), [worldSlice, activeResp, cfg.packId]);
  const worldSource = worldSlice ? "immutable baseline registry slice" : activeResp ? "run proof graph fallback" : worldLoading ? "registry loading" : "registry unavailable";
  const selectedWorldNode = useMemo(() => effectiveWorld?.nodes.find((node) => node.id === sel?.id) ?? null, [effectiveWorld, sel]);
  const inspectorWorldNode = useMemo(() => sel?.kind === "capability" ? capabilities?.find((node) => node.id === sel.id) ?? null : selectedWorldNode, [capabilities, sel, selectedWorldNode]);
  const unknownCount = activeResp?.result.blocking_unknowns.length ?? effectiveWorld?.nodes.filter((node) => node.epistemic_class.toUpperCase().includes("UNKNOWN")).length ?? 0;

  const chooseVariant = useCallback((variantId: string) => {
    updateConfig({ variantId });
  }, [updateConfig]);

  const applyPreset = useCallback((patch: Partial<ObjectiveConfig>) => {
    updateConfig(patch);
    void run(patch);
  }, [run, updateConfig]);

  const restoreBaseline = useCallback(() => {
    if (!baseCfg || !baseResp) return;
    solveGeneration.current += 1;
    parseGeneration.current += 1;
    parseController.current?.abort();
    setBusy(false);
    setErr(null);
    const restored = cloneConfig(baseCfg);
    cfgRef.current = restored;
    setCfg(restored);
    setResp(baseResp);
    setCompiledCfg(cloneConfig(baseCfg));
    setSel(null);
    setWorldSlice(null);
  }, [baseCfg, baseResp]);

  const canRestoreBaseline = Boolean(baseCfg && configIdentity(cfg) !== configIdentity(baseCfg));
  const comparisonBaseResp = baseCfg && baselineCoreIdentity(cfg) === baselineCoreIdentity(baseCfg)
    ? baseResp
    : null;
  const canRun = Boolean(
    packDetail
    && packDetail.pack_id === cfg.packId
    && packDetail.variants.some((variant) => variant.id === cfg.variantId)
    && Number.isFinite(cfg.annualUnits)
    && cfg.annualUnits > 0
    && cfg.geography.trim(),
  );

  return (
    <div className="workbench-app">
      <a className="skip-link" href="#workbench-main">Skip to workbench</a>
      <header className="workbench-topbar">
        <div className="brand-lockup">
          <div className="forge-mark" aria-hidden="true" />
          <div translate="no"><strong>FORGE WORLD</strong><span>industrial intelligence workbench</span></div>
        </div>
        <div className="topbar-state" role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          <span>{isStale ? "inputs changed · prior result hidden" : activeResp ? `run ${activeResp.run.run_id.slice(0, 12)}` : "run state awaiting compilation"}</span>
          {busy && <span className="spin" aria-label="compiling" />}
        </div>
      </header>

      <ScenarioRail
        cfg={cfg}
        packList={packList}
        packLoading={packLoading}
        packDetail={packDetail}
        nlText={nlText}
        nlNote={nlNote}
        busy={busy}
        canRun={canRun}
        error={err}
        onNlTextChange={setNlText}
        onConfigChange={updateConfig}
        onParse={() => void applyNl()}
        onRun={() => void run()}
        onPreset={applyPreset}
      />

      <main id="workbench-main" className="workbench-main" tabIndex={-1}>
        <nav className="product-mode-tabs" aria-label="FORGE product modes" role="tablist">
          {PRODUCT_MODES.map((item, index) => <button type="button" role="tab" id={`mode-tab-${item.toLowerCase()}`} aria-controls="mode-panel" aria-selected={mode === item} tabIndex={mode === item ? 0 : -1} className={mode === item ? "active" : ""} key={item} onClick={() => setMode(item)} onKeyDown={(event) => {
            let nextIndex = index;
            if (event.key === "ArrowRight") nextIndex = (index + 1) % PRODUCT_MODES.length;
            else if (event.key === "ArrowLeft") nextIndex = (index - 1 + PRODUCT_MODES.length) % PRODUCT_MODES.length;
            else if (event.key === "Home") nextIndex = 0;
            else if (event.key === "End") nextIndex = PRODUCT_MODES.length - 1;
            else return;
            event.preventDefault();
            const nextMode = PRODUCT_MODES[nextIndex];
            setMode(nextMode);
            document.getElementById(`mode-tab-${nextMode.toLowerCase()}`)?.focus();
          }}>{item}<span>{modeHint(item)}</span></button>)}
        </nav>
        <BranchHeader cfg={cfg} resp={activeResp} baseResp={baseResp} stale={isStale} canRestore={canRestoreBaseline} onRestore={restoreBaseline} />
        <ClockStrip deadlineYear={cfg.deadlineYear} resp={activeResp} unknownCount={unknownCount} worldSummary={worldSummary} />
        {isStale && <div className="stale-run-notice" role="status"><strong>RECOMPUTE PENDING</strong><span>The controls no longer match the compiled run. Prior numerical results are hidden until this branch is compiled.</span></div>}
        {capabilitiesLoading && mode === "DISCOVER" && <div className="loading-line" role="status">Loading canonical capability registry…</div>}
        <div id="mode-panel" className="workbench-stage" role="tabpanel" aria-labelledby={`mode-tab-${mode.toLowerCase()}`} key={`${mode}-${activeResp?.run.run_id ?? "pending"}`}>
          <ModeViews
            mode={mode}
            cfg={cfg}
            resp={activeResp}
            baseResp={comparisonBaseResp}
            world={effectiveWorld}
            worldSource={worldSource}
            packDetail={packDetail}
            capabilities={capabilitiesLoading ? null : capabilities}
            selectedWorldNode={inspectorWorldNode}
            onSelect={setSel}
            onSelectWorld={(node) => setSel({ kind: "world", id: node.id })}
            onVariant={chooseVariant}
          />
        </div>
      </main>

      <Inspector sel={sel} resp={activeResp} packDetail={packDetail} onSelect={setSel} worldNode={inspectorWorldNode} />
    </div>
  );
}

function cloneConfig(cfg: ObjectiveConfig): ObjectiveConfig {
  return {
    ...cfg,
    fundedProjects: [...cfg.fundedProjects],
    shocks: [...cfg.shocks],
    assumptions: Object.fromEntries(
      Object.entries(cfg.assumptions).map(([key, value]) => [key, [value[0], value[1]] as [number, number]]),
    ),
  };
}

function configIdentity(cfg: ObjectiveConfig): string {
  return JSON.stringify({
    packId: cfg.packId,
    variantId: cfg.variantId,
    annualUnits: cfg.annualUnits,
    geography: cfg.geography,
    deadlineYear: cfg.deadlineYear,
    minDva: cfg.minDva,
    budgetUsd: cfg.budgetUsd,
    fundedProjects: [...cfg.fundedProjects].sort(),
    shocks: [...cfg.shocks].sort(),
    assumptions: Object.entries(cfg.assumptions).sort(([left], [right]) => left.localeCompare(right)),
  });
}

function baselineCoreIdentity(cfg: ObjectiveConfig): string {
  return JSON.stringify({
    packId: cfg.packId,
    annualUnits: cfg.annualUnits,
    geography: cfg.geography,
    deadlineYear: cfg.deadlineYear,
    minDva: cfg.minDva,
    budgetUsd: cfg.budgetUsd,
    assumptions: Object.entries(cfg.assumptions).sort(([left], [right]) => left.localeCompare(right)),
  });
}

function modeHint(mode: ProductMode): string {
  if (mode === "ANALYZE") return "why";
  if (mode === "DESIGN") return "choose";
  if (mode === "EXECUTE") return "do";
  if (mode === "DISCOVER") return "reuse";
  return "learn";
}

function deriveWorldSlice(resp: SolveResponse, packId: string): WorldSlice {
  const nodes = new Map<string, WorldNode>();
  for (const node of resp.proof_graph.nodes) {
    const kind = node.kind.toUpperCase();
    nodes.set(node.node_id, {
      id: node.node_id,
      name: node.label,
      kind: node.kind,
      pack_id: packId,
      canonical_id: node.node_id,
      epistemic_class: kind.includes("EVIDENCE") ? "REPORTED" : kind.includes("ASSUMPTION") ? "ASSUMPTION" : kind.includes("UNKNOWN") ? "UNKNOWN" : "DERIVED",
      evidence_ids: node.sources,
      metadata: node.detail,
    });
  }
  const envByItem = new Map(resp.capacity_envelopes.map((item) => [item.item, item]));
  for (const item of resp.explosion.items) {
    if (nodes.has(item.item)) continue;
    const env = envByItem.get(item.item);
    nodes.set(item.item, {
      id: item.item,
      name: item.item,
      kind: item.depth === 0 ? "requirement" : item.depth === 1 ? "component" : item.depth === 2 ? "process" : "material",
      pack_id: packId,
      canonical_id: null,
      epistemic_class: env?.epistemic ?? (env ? "REPORTED" : "UNKNOWN"),
      evidence_ids: [],
      metadata: { unit: item.unit, recipe: item.recipe, annual_requirement: item.gross },
    });
  }
  const edges = resp.proof_graph.edges.map((edge) => ({ src: edge.from_id, relation: edge.relation, dst: edge.to_id, meta: {} }));
  const root = resp.proof_graph.nodes.find((node) => node.kind.toLowerCase() === "output")?.node_id ?? resp.proof_graph.nodes[0]?.node_id ?? resp.explosion.items[0]?.item ?? null;
  return { nodes: [...nodes.values()], edges, root, truncated: false };
}
