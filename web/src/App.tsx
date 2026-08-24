import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type {
  CapabilityRecord,
  DesignComparison,
  ObjectiveConfig,
  OperationalCaseResponse,
  PackDetail,
  ResearchResolution,
  ScenarioPreset,
  Selection,
  SolveResponse,
  WorldSlice,
} from "./types";
import {
  compareArchitecture,
  fetchPackDetailSafe,
  fetchPacksSafe,
  fetchWorldCapabilities,
  fetchWorldSlice,
  resolveResearchTask,
  runOperationalCase,
} from "./api";
import Inspector from "./Inspector";
import {
  CaseOverview,
  ExecutionWorkspace,
  ResearchWorkspace,
} from "./OperationalPanels";
import type {
  CaseOverviewData,
  ExecutionWorkspaceData,
  ForgeAction,
  ForgeAlternative,
  ForgeDependency,
  ResearchResult,
  ResearchSubmission,
  ResearchWorkspaceData,
} from "./OperationalPanels";
import { CapabilityLeverage, ProgramTimeline } from "./InsightSurfaces";
import type {
  CapabilityLeverage as CapabilityLeverageView,
  ProgramTimeline as ProgramTimelineView,
} from "./InsightSurfaces";
import "./workbench-v2.css";

const AssemblySpace = lazy(() => import("./AssemblySpace"));

type Journey = "ANALYZE" | "DESIGN" | "EXECUTE" | "DISCOVER";
type Surface =
  | "overview"
  | "structure"
  | "why"
  | "timeline"
  | "research"
  | "design"
  | "execute"
  | "discover";
type Drawer = "scenario" | "why" | "learn" | null;

const PACK_STARTING_OUTPUTS: Record<string, number> = {
  battery_gwh_india: 500_000,
  cnc_machining_india: 100,
  humanoid_india: 1_000_000,
  nuclear_buildout_india: 1,
  smallsat_india: 50,
};

const DEFAULT_CONFIG: ObjectiveConfig = {
  packId: "cnc_machining_india",
  variantId: "cnc_vmc_100_per_year",
  annualUnits: 100,
  geography: "INDIA",
  deadlineYear: 2030,
  minDva: 0.7,
  budgetUsd: null,
  fundedProjects: [],
  shocks: [],
  assumptions: {},
  includeDeep: false,
};

const DEFAULT_QUESTIONS: Record<string, string> = {
  cnc_machining_india:
    "Can India manufacture 100 high-quality CNC machining centers per year by 2030 at at least 70% recursive domestic value?",
  humanoid_india:
    "Can humanity manufacture 1,000,000 humanoid robots per year by 2030, and what changes if China is excluded?",
  nuclear_buildout_india:
    "What industrial system and timeline would India need for a large multi-year nuclear buildout through 2047?",
  battery_gwh_india:
    "What would it take to build the selected battery manufacturing objective in India?",
  smallsat_india:
    "What limits the selected small-satellite production objective in India?",
};

export default function App() {
  const [packList, setPackList] = useState<
    { pack_id: string; title: string; variants: string[] }[]
  >([]);
  const [packDetail, setPackDetail] = useState<PackDetail | null>(null);
  const [cfg, setCfg] = useState<ObjectiveConfig>(DEFAULT_CONFIG);
  const [compiledCfg, setCompiledCfg] = useState<ObjectiveConfig | null>(null);
  const [caseData, setCaseData] = useState<OperationalCaseResponse | null>(
    null,
  );
  const [baseline, setBaseline] = useState<{
    cfg: ObjectiveConfig;
    data: OperationalCaseResponse;
  } | null>(null);
  const [worldSlice, setWorldSlice] = useState<WorldSlice | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilityRecord[] | null>(
    null,
  );
  const [question, setQuestion] = useState(
    DEFAULT_QUESTIONS[DEFAULT_CONFIG.packId],
  );
  const [parseNote, setParseNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [journey, setJourney] = useState<Journey>("ANALYZE");
  const [surface, setSurface] = useState<Surface>("overview");
  const [drawer, setDrawer] = useState<Drawer>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [designId, setDesignId] = useState<string>("");
  const [designResult, setDesignResult] = useState<DesignComparison | null>(
    null,
  );
  const [designBusy, setDesignBusy] = useState(false);
  const [researchResult, setResearchResult] = useState<ResearchResult | null>(
    null,
  );
  const [researchInitialTask, setResearchInitialTask] = useState<string | null>(
    null,
  );
  const cfgRef = useRef(cfg);
  const generation = useRef(0);
  const bootstrapKey = useRef("");
  cfgRef.current = cfg;

  const updateConfig = useCallback((patch: Partial<ObjectiveConfig>) => {
    const currentSnapshot = cfgRef.current;
    const packChanged =
      typeof patch.packId === "string" &&
      patch.packId !== currentSnapshot.packId;
    const next: ObjectiveConfig = {
      ...currentSnapshot,
      ...patch,
      variantId: packChanged
        ? typeof patch.variantId === "string"
          ? patch.variantId
          : ""
        : (patch.variantId ?? currentSnapshot.variantId),
      annualUnits:
        packChanged && typeof patch.annualUnits !== "number"
          ? (PACK_STARTING_OUTPUTS[patch.packId!] ??
            currentSnapshot.annualUnits)
          : (patch.annualUnits ?? currentSnapshot.annualUnits),
      fundedProjects: patch.fundedProjects
        ? [...patch.fundedProjects]
        : packChanged
          ? []
          : currentSnapshot.fundedProjects,
      shocks: patch.shocks
        ? [...patch.shocks]
        : packChanged
          ? []
          : currentSnapshot.shocks,
      assumptions: patch.assumptions
        ? { ...patch.assumptions }
        : packChanged
          ? {}
          : currentSnapshot.assumptions,
    };
    cfgRef.current = next;
    setCfg(next);
    if (packChanged && patch.packId) {
      setQuestion(
        DEFAULT_QUESTIONS[patch.packId] ??
          "Can this physical production objective happen, what blocks it, and what should we do next?",
      );
    }
  }, []);

  const runCase = useCallback(async (override?: Partial<ObjectiveConfig>) => {
    const next = cloneConfig({ ...cfgRef.current, ...override });
    if (!next.packId || !next.variantId) {
      setError(
        "Choose a knowledge pack and reference architecture before compiling the case.",
      );
      return;
    }
    if (!Number.isFinite(next.annualUnits) || next.annualUnits <= 0) {
      setError("Annual output must be greater than zero.");
      return;
    }
    const runGeneration = ++generation.current;
    cfgRef.current = next;
    setCfg(next);
    setBusy(true);
    setError(null);
    try {
      const data = await runOperationalCase(next);
      if (runGeneration !== generation.current) return;
      setCaseData(data);
      setCompiledCfg(cloneConfig(next));
      setDesignResult(null);
      setResearchResult(null);
      if (
        next.shocks.length === 0 &&
        Object.keys(next.assumptions).length === 0 &&
        next.fundedProjects.length === 0
      ) {
        setBaseline({ cfg: cloneConfig(next), data });
      }
    } catch (runError) {
      if (runGeneration !== generation.current) return;
      setError(runError instanceof Error ? runError.message : String(runError));
    } finally {
      if (runGeneration === generation.current) setBusy(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetchPacksSafe().then((packs) => {
      if (!active) return;
      setPackList(packs);
      if (
        packs.length &&
        !packs.some((pack) => pack.pack_id === cfgRef.current.packId)
      ) {
        updateConfig({
          packId: packs[0].pack_id,
          variantId: packs[0].variants[0] ?? "",
        });
      }
    });
    void fetchWorldCapabilities().then((records) => {
      if (active) setCapabilities(records);
    });
    return () => {
      active = false;
    };
  }, [updateConfig]);

  useEffect(() => {
    let active = true;
    setPackDetail(null);
    setWorldSlice(null);
    setCaseData(null);
    setCompiledCfg(null);
    setBaseline(null);
    setDesignResult(null);
    setResearchResult(null);
    bootstrapKey.current = "";
    void fetchPackDetailSafe(cfg.packId).then((detail) => {
      if (!active) return;
      setPackDetail(detail);
      if (!detail) return;
      const current = cfgRef.current;
      const next = {
        ...current,
        variantId: detail.variants.some(
          (variant) => variant.id === current.variantId,
        )
          ? current.variantId
          : (detail.variants[0]?.id ?? ""),
        shocks: current.shocks.filter((id) =>
          detail.shocks.some((shock) => shock.id === id),
        ),
        fundedProjects: current.fundedProjects.filter((id) =>
          detail.projects.some((project) => project.id === id),
        ),
      };
      cfgRef.current = next;
      setCfg(next);
    });
    return () => {
      active = false;
    };
  }, [cfg.packId]);

  useEffect(() => {
    if (
      !packDetail ||
      packDetail.pack_id !== cfg.packId ||
      !cfg.variantId ||
      busy ||
      caseData
    )
      return;
    const key = `${cfg.packId}:${cfg.variantId}`;
    if (bootstrapKey.current === key) return;
    bootstrapKey.current = key;
    void runCase();
  }, [busy, caseData, cfg.packId, cfg.variantId, packDetail, runCase]);

  useEffect(() => {
    let active = true;
    if (!cfg.packId || !cfg.variantId)
      return () => {
        active = false;
      };
    void fetchWorldSlice(cfg.packId, cfg.variantId, 8, 320).then((slice) => {
      if (active) setWorldSlice(slice);
    });
    return () => {
      active = false;
    };
  }, [cfg.packId, cfg.variantId, caseData?.registry_snapshot_id]);

  useEffect(() => {
    if (!drawer) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawer(null);
    };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [drawer]);

  const isStale = Boolean(
    caseData &&
      (!compiledCfg || configIdentity(cfg) !== configIdentity(compiledCfg)),
  );
  const activeCase = isStale ? null : caseData;
  const selectedWorldNode = useMemo(() => {
    if (!selection) return null;
    if (selection.kind === "capability")
      return capabilities?.find((node) => node.id === selection.id) ?? null;
    return (
      worldSlice?.nodes.find(
        (node) =>
          node.id === selection.id ||
          localId(node.id, cfg.packId) === selection.id,
      ) ?? null
    );
  }, [capabilities, cfg.packId, selection, worldSlice]);

  const assembly = useMemo(
    () => buildAssemblyData(activeCase?.analysis ?? null, worldSlice, cfg),
    [activeCase, cfg, worldSlice],
  );
  const caseOverview = useMemo(
    () => (activeCase ? adaptCaseOverview(activeCase, packDetail) : null),
    [activeCase, packDetail],
  );
  const execution = useMemo(
    () => (activeCase ? adaptExecution(activeCase) : null),
    [activeCase],
  );
  const research = useMemo(
    () => (activeCase ? adaptResearch(activeCase, researchInitialTask) : null),
    [activeCase, researchInitialTask],
  );
  const program = useMemo(
    () => (activeCase ? adaptProgram(activeCase) : null),
    [activeCase],
  );
  const discoverRows = useMemo(
    () => (activeCase ? adaptCapabilities(activeCase) : []),
    [activeCase],
  );

  const switchJourney = useCallback((next: Journey) => {
    setJourney(next);
    setSurface(
      next === "ANALYZE"
        ? "overview"
        : next === "DESIGN"
          ? "design"
          : next === "EXECUTE"
            ? "execute"
            : "discover",
    );
  }, []);

  const openWhy = useCallback(
    (itemId?: string) => {
      const id =
        itemId ||
        activeCase?.brief.top_bottlenecks[0]?.item_id ||
        cfg.variantId;
      if (id) setSelection({ kind: "item", id });
      setJourney("ANALYZE");
      setSurface("why");
    },
    [activeCase, cfg.variantId],
  );

  const openResearch = useCallback(
    (taskId?: string) => {
      setResearchInitialTask(
        taskId ?? activeCase?.research.tasks[0]?.id ?? null,
      );
      setJourney("ANALYZE");
      setSurface("research");
    },
    [activeCase],
  );

  const handleOverviewAction = useCallback(
    (action: ForgeAction) => {
      const key = (action.kind || action.id).toUpperCase();
      if (key.includes("WHY")) openWhy();
      else if (key.includes("RESEARCH")) openResearch();
      else if (key.includes("REDESIGN")) switchJourney("DESIGN");
      else if (key.includes("EXECUTE") || key.includes("PATH"))
        switchJourney("EXECUTE");
    },
    [openResearch, openWhy, switchJourney],
  );

  const handleAlternative = useCallback(
    (alternative: ForgeAlternative) => {
      setDesignId(alternative.id);
      switchJourney("DESIGN");
    },
    [switchJourney],
  );

  const handleDependency = useCallback(
    (dependency: ForgeDependency) => {
      setSelection({ kind: "item", id: dependency.id });
      openWhy(dependency.id);
    },
    [openWhy],
  );

  const runDesign = useCallback(async () => {
    if (!designId) return;
    setDesignBusy(true);
    setError(null);
    try {
      setDesignResult(await compareArchitecture(cfgRef.current, designId));
    } catch (designError) {
      setError(
        designError instanceof Error
          ? designError.message
          : String(designError),
      );
    } finally {
      setDesignBusy(false);
    }
  }, [designId]);

  const handleResearchSubmit = useCallback(
    async (submission: ResearchSubmission): Promise<ResearchResult> => {
      if (!activeCase)
        throw new Error("Compile an active case before capturing research.");
      const task = activeCase.research.tasks.find(
        (candidate) => candidate.id === submission.taskId,
      );
      if (!task)
        throw new Error(
          "The selected research task is no longer in the active run.",
        );
      const range = parseNumericRange(submission.capture.value);
      const capture: Record<string, unknown> = {
        source_id: `workbench-${task.target_entity_id}-${Date.now()}`,
        source_url: submission.capture.sourceUrl,
        publisher: submission.capture.publisher,
        license: submission.capture.license,
        source_type: submission.capture.sourceType,
        access_date: submission.capture.accessDate,
        document_date: submission.capture.accessDate,
        epistemic_class: submission.capture.epistemic,
        predicate: task.missing_variable,
        value_text: submission.capture.value,
        technical_scope: submission.capture.claim,
        quoted_extract: submission.capture.quote,
        caveat:
          submission.capture.caveat ||
          "Workbench research capture pending persistent repository review.",
      };
      if (range && task.missing_variable.includes("capacity")) {
        capture.capacity_range = range;
        capture.unit = submission.capture.unit || "pcs/year";
      }
      const resolution = await resolveResearchTask(
        cfgRef.current,
        task,
        capture,
        submission.reviewerId,
        submission.scenarioOverlayApproval.approved,
      );
      const record = resolution.evidence_record as
        | Record<string, unknown>
        | undefined;
      const result: ResearchResult = {
        status: String(resolution.reconciliation.status ?? "REVIEW_REQUIRED"),
        message: resolution.scenario_overlay
          ? "Evidence was captured, reconciled, and used in an explicit non-persistent scenario overlay."
          : "Evidence was captured and reconciled. The checked-in world remains unchanged pending repository review.",
        evidenceId:
          typeof record?.claim_id === "string" ? record.claim_id : null,
        epistemic: submission.capture.epistemic,
        reviewerNote: `Reviewer ${submission.reviewerId}; automatic overwrite disabled.`,
        nextStep: resolution.persistent_world_update.status,
      };
      setResearchResult(result);
      return result;
    },
    [activeCase],
  );

  const applyPreset = useCallback(
    (preset: ScenarioPreset) => {
      const patch: Partial<ObjectiveConfig> = {
        variantId: preset.variant_id ?? cfgRef.current.variantId,
        annualUnits: preset.annual_units ?? cfgRef.current.annualUnits,
        geography: preset.geography ?? cfgRef.current.geography,
        deadlineYear: preset.target_year ?? cfgRef.current.deadlineYear,
        minDva: preset.min_dva ?? cfgRef.current.minDva,
        shocks: preset.shock_ids ?? [],
      };
      if (preset.objective) setQuestion(preset.objective);
      setDrawer(null);
      void runCase(patch);
    },
    [runCase],
  );

  const parseAndRun = useCallback(async () => {
    if (!question.trim()) {
      void runCase();
      return;
    }
    setParseNote(
      "Interpreting the question into inspectable objective fields…",
    );
    try {
      const response = await fetch("/api/parse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: question }),
      });
      if (!response.ok) throw new Error(`parse ${response.status}`);
      const parsed = (await response.json()) as {
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
      const patch: Partial<ObjectiveConfig> = {};
      const variant = parsed.objective?.variant_id;
      if (variant) {
        const pack = packList.find((candidate) =>
          candidate.variants.includes(variant),
        );
        if (pack) {
          patch.packId = pack.pack_id;
          patch.variantId = variant;
        }
      }
      if (typeof parsed.objective?.annual_units === "number")
        patch.annualUnits = parsed.objective.annual_units;
      if (typeof parsed.objective?.geography === "string")
        patch.geography = parsed.objective.geography;
      if (typeof parsed.objective?.deadline_year === "number")
        patch.deadlineYear = parsed.objective.deadline_year;
      if (typeof parsed.objective?.min_dva === "number")
        patch.minDva = parsed.objective.min_dva;
      if (
        typeof parsed.objective?.budget_usd === "number" ||
        parsed.objective?.budget_usd === null
      )
        patch.budgetUsd = parsed.objective?.budget_usd;
      if (parsed.objective?.funded_projects)
        patch.fundedProjects = parsed.objective.funded_projects;
      if (parsed.shocks) patch.shocks = parsed.shocks;
      const note =
        parsed.interpretations?.join(" · ") ||
        "Question retained; using the visible objective fields.";
      setParseNote(
        `${note}${parsed.unresolved?.length ? ` · unresolved: ${parsed.unresolved.join(", ")}` : ""}`,
      );
      await runCase(patch);
    } catch {
      setParseNote(
        "The parser was unavailable; compiling the visible objective fields directly.",
      );
      await runCase();
    }
  }, [packList, question, runCase]);

  const restoreBaseline = useCallback(() => {
    if (!baseline) return;
    generation.current += 1;
    const restored = cloneConfig(baseline.cfg);
    cfgRef.current = restored;
    setCfg(restored);
    setCompiledCfg(cloneConfig(restored));
    setCaseData(baseline.data);
    setDesignResult(null);
    setResearchResult(null);
    setError(null);
    setDrawer(null);
  }, [baseline]);

  const canRestore = Boolean(
    baseline && configIdentity(cfg) !== configIdentity(baseline.cfg),
  );
  const runLabel = busy
    ? "Computing evidence-bounded case"
    : isStale
      ? "Inputs changed · recompute required"
      : activeCase
        ? `${activeCase.brief.result_class} · ${activeCase.analysis.run.run_id.slice(0, 11)}`
        : "Preparing industrial world";

  return (
    <div className="fw-app">
      <a className="skip-link" href="#forge-workspace">
        Skip to objective workspace
      </a>
      <header className="fw-topbar">
        <div className="fw-brand" translate="no">
          <span className="fw-brand-mark" aria-hidden="true" />
          <span className="fw-brand-copy">
            <strong>FORGE WORLD</strong>
            <span>industrial possibility engine</span>
          </span>
        </div>
        <div className="fw-run-state" role="status" aria-live="polite">
          <span
            className={`fw-state-light ${busy ? "busy" : isStale ? "stale" : activeCase ? "live" : ""}`}
            aria-hidden="true"
          />
          <span>{runLabel}</span>
        </div>
        <div className="fw-top-actions">
          <button
            className="fw-quiet-button"
            type="button"
            aria-label="Scenario controls"
            onClick={() => setDrawer("scenario")}
          >
            <span>Scenario</span> controls
          </button>
          <button
            className="fw-quiet-button"
            type="button"
            aria-label="Learn this view"
            onClick={() => setDrawer("learn")}
          >
            Learn <span>this view</span>
          </button>
        </div>
      </header>

      <div id="forge-workspace" className="fw-content">
        <ObjectiveComposer
          cfg={cfg}
          packList={packList}
          packDetail={packDetail}
          question={question}
          busy={busy}
          parseNote={parseNote}
          error={error}
          stale={isStale}
          onQuestion={setQuestion}
          onConfig={updateConfig}
          onRun={() => void parseAndRun()}
        />
        {!caseData && !busy && <EmptyWelcome />}
        {busy && !caseData && <LoadingState />}
        {caseData && (
          <section
            className="fw-workspace"
            aria-label="Compiled objective workspace"
          >
            <JourneyNav active={journey} onChange={switchJourney} />
            <SurfaceBar
              journey={journey}
              surface={surface}
              hasTimeline={Boolean(caseData.program.available)}
              runId={caseData.analysis.run.run_id}
              onChange={setSurface}
            />
            <div className="fw-stage">
              {busy && <LoadingState overlay />}
              {!busy && isStale && (
                <div className="fw-stage-inner">
                  <div className="fw-stale">
                    <strong>RECOMPUTE REQUIRED</strong>
                    <br />
                    The visible inputs no longer match the compiled case.
                    Numerical and causal surfaces are withheld until you compile
                    this branch.
                  </div>
                </div>
              )}
              {!busy && activeCase && (
                <div
                  className={`fw-stage-inner ${surface === "structure" ? "spatial" : ""}`}
                >
                  {surface === "overview" && caseOverview && (
                    <>
                      <CaseOverview
                        data={caseOverview}
                        onAction={handleOverviewAction}
                        onAlternative={handleAlternative}
                        onDependency={handleDependency}
                      />
                      <ReverseBoundary
                        data={activeCase}
                        onResearch={() => openResearch()}
                      />
                    </>
                  )}
                  {surface === "structure" && (
                    <Suspense fallback={<LoadingState compact />}>
                      <AssemblySpace
                        title={`${packDetail?.title ?? cfg.packId} · dependency assembly`}
                        nodes={assembly.nodes}
                        edges={assembly.edges}
                        selectedId={selection?.id ?? null}
                        onSelect={(id) => setSelection({ kind: "item", id })}
                      />
                    </Suspense>
                  )}
                  {surface === "why" && (
                    <WhySurface
                      data={activeCase}
                      selection={selection}
                      onSelect={setSelection}
                      onInspect={() => setDrawer("why")}
                    />
                  )}
                  {surface === "timeline" && <ProgramTimeline data={program} />}
                  {surface === "research" && (
                    <ResearchWorkspace
                      data={research}
                      onSubmit={handleResearchSubmit}
                      result={researchResult}
                    />
                  )}
                  {surface === "design" && (
                    <DesignSurface
                      data={activeCase}
                      selectedId={designId}
                      result={designResult}
                      busy={designBusy}
                      onSelect={setDesignId}
                      onCompare={() => void runDesign()}
                    />
                  )}
                  {surface === "execute" && execution && (
                    <ExecutionWorkspace
                      data={execution}
                      onAction={(action) =>
                        action.kind?.toUpperCase().includes("RESEARCH") &&
                        openResearch(action.id)
                      }
                      onWorkPackage={() => undefined}
                    />
                  )}
                  {surface === "discover" && (
                    <CapabilityLeverage
                      rows={discoverRows}
                      selectedCapabilityId={
                        selection?.kind === "capability" ? selection.id : null
                      }
                      onSelectCapability={(capability) => {
                        setSelection({ kind: "capability", id: capability.id });
                        setDrawer("why");
                      }}
                    />
                  )}
                </div>
              )}
            </div>
          </section>
        )}
      </div>

      {drawer === "scenario" && (
        <DrawerShell
          title="Scenario and branch controls"
          onClose={() => setDrawer(null)}
        >
          <ScenarioControls
            cfg={cfg}
            detail={packDetail}
            canRestore={canRestore}
            onConfig={updateConfig}
            onRun={() => void runCase()}
            onPreset={applyPreset}
            onRestore={restoreBaseline}
          />
        </DrawerShell>
      )}
      {drawer === "why" && (
        <DrawerShell
          title="WHY · evidence and causality"
          wide
          onClose={() => setDrawer(null)}
        >
          <Inspector
            sel={selection}
            resp={activeCase?.analysis ?? null}
            packDetail={packDetail}
            onSelect={setSelection}
            worldNode={selectedWorldNode}
          />
        </DrawerShell>
      )}
      {drawer === "learn" && (
        <DrawerShell title="Learn in context" onClose={() => setDrawer(null)}>
          <LearnPanel
            journey={journey}
            surface={surface}
            selection={selection}
          />
        </DrawerShell>
      )}
    </div>
  );
}

function ObjectiveComposer({
  cfg,
  packList,
  packDetail,
  question,
  busy,
  parseNote,
  error,
  stale,
  onQuestion,
  onConfig,
  onRun,
}: {
  cfg: ObjectiveConfig;
  packList: { pack_id: string; title: string; variants: string[] }[];
  packDetail: PackDetail | null;
  question: string;
  busy: boolean;
  parseNote: string | null;
  error: string | null;
  stale: boolean;
  onQuestion: (value: string) => void;
  onConfig: (patch: Partial<ObjectiveConfig>) => void;
  onRun: () => void;
}) {
  return (
    <section
      className="fw-objective-composer"
      aria-labelledby="objective-title"
    >
      <div className="fw-objective-main">
        <span className="fw-kicker">Start with a physical future</span>
        <h1 id="objective-title">
          Can this be built—<em>and what changes the answer?</em>
        </h1>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onRun();
          }}
        >
          <div className="fw-question-row">
            <label className="fw-visually-hidden" htmlFor="objective-question">
              Industrial objective
            </label>
            <textarea
              id="objective-question"
              value={question}
              onChange={(event) => onQuestion(event.target.value)}
              placeholder="Ask about a product, industrial buildout, capability, or constraint…"
            />
            <button
              className="fw-run-button"
              type="submit"
              disabled={busy || !cfg.variantId}
            >
              {busy ? "Computing…" : "Compile case"}
            </button>
          </div>
          <div className="fw-objective-fields">
            <label className="fw-field">
              <span>World pack</span>
              <select
                value={cfg.packId}
                onChange={(event) =>
                  onConfig({ packId: event.target.value, variantId: "" })
                }
              >
                {packList.map((pack) => (
                  <option value={pack.pack_id} key={pack.pack_id}>
                    {pack.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="fw-field">
              <span>Reference architecture</span>
              <select
                value={cfg.variantId}
                onChange={(event) =>
                  onConfig({ variantId: event.target.value })
                }
              >
                {packDetail?.variants.map((variant) => (
                  <option value={variant.id} key={variant.id}>
                    {variant.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="fw-field">
              <span>Annual output</span>
              <input
                type="number"
                min="1"
                value={cfg.annualUnits}
                onChange={(event) =>
                  onConfig({ annualUnits: Number(event.target.value) })
                }
              />
            </label>
            <label className="fw-field">
              <span>Geography</span>
              <input
                value={cfg.geography}
                onChange={(event) =>
                  onConfig({ geography: event.target.value })
                }
              />
            </label>
            <label className="fw-field">
              <span>By year</span>
              <input
                type="number"
                min="2026"
                max="2200"
                value={cfg.deadlineYear}
                onChange={(event) =>
                  onConfig({ deadlineYear: Number(event.target.value) })
                }
              />
            </label>
          </div>
        </form>
        {parseNote && (
          <div className="fw-parse-note" role="status">
            {parseNote}
          </div>
        )}
        {error && (
          <div className="fw-error" role="alert">
            {error}
          </div>
        )}
        {stale && !busy && (
          <div className="fw-stale" role="status">
            Inputs changed. Compile to replace the prior branch; its result is
            hidden to prevent stale conclusions.
          </div>
        )}
      </div>
    </section>
  );
}

function JourneyNav({
  active,
  onChange,
}: {
  active: Journey;
  onChange: (journey: Journey) => void;
}) {
  const rows: { id: Journey; n: string; title: string; hint: string }[] = [
    {
      id: "ANALYZE",
      n: "01",
      title: "Analyze",
      hint: "Can it happen—and why?",
    },
    {
      id: "DESIGN",
      n: "02",
      title: "Design",
      hint: "Rewrite the architecture",
    },
    {
      id: "EXECUTE",
      n: "03",
      title: "Execute",
      hint: "Turn analysis into work",
    },
  ];
  return (
    <nav className="fw-journey" aria-label="Objective journey">
      {rows.map((row) => (
        <button
          type="button"
          className={`fw-journey-button ${active === row.id ? "active" : ""}`}
          aria-current={active === row.id ? "step" : undefined}
          onClick={() => onChange(row.id)}
          key={row.id}
        >
          <b>{row.n}</b>
          <span>
            <strong>{row.title}</strong>
            <small>{row.hint}</small>
          </span>
        </button>
      ))}
      <span className="fw-journey-spacer" />
      <button
        type="button"
        className={`fw-journey-button discover ${active === "DISCOVER" ? "active" : ""}`}
        onClick={() => onChange("DISCOVER")}
      >
        <b>↗</b>
        <span>
          <strong>Discover</strong>
          <small>Invert the shared world model</small>
        </span>
      </button>
    </nav>
  );
}

function SurfaceBar({
  journey,
  surface,
  hasTimeline,
  runId,
  onChange,
}: {
  journey: Journey;
  surface: Surface;
  hasTimeline: boolean;
  runId: string;
  onChange: (surface: Surface) => void;
}) {
  const surfaces: { id: Surface; label: string }[] =
    journey === "ANALYZE"
      ? [
          { id: "overview", label: "Brief" },
          { id: "structure", label: "Assembly space" },
          { id: "why", label: "WHY" },
          ...(hasTimeline
            ? [{ id: "timeline" as Surface, label: "Program timeline" }]
            : []),
          { id: "research", label: "Research unknown" },
        ]
      : journey === "DESIGN"
        ? [
            { id: "design", label: "Architecture comparison" },
            { id: "structure", label: "Dependency space" },
          ]
        : journey === "EXECUTE"
          ? [
              { id: "execute", label: "Execution workspace" },
              { id: "research", label: "Evidence tasks" },
              { id: "structure", label: "Machine recursion" },
            ]
          : [
              { id: "discover", label: "Capability leverage" },
              { id: "structure", label: "Shared dependency space" },
            ];
  return (
    <div
      className="fw-surface-bar"
      role="tablist"
      aria-label={`${journey} surfaces`}
    >
      {surfaces.map((item) => (
        <button
          type="button"
          role="tab"
          aria-selected={surface === item.id}
          className={`fw-surface-button ${surface === item.id ? "active" : ""}`}
          onClick={() => onChange(item.id)}
          key={item.id}
        >
          {item.label}
        </button>
      ))}
      <span className="fw-compiled-tag">compiled {runId.slice(0, 14)}</span>
    </div>
  );
}

function ScenarioControls({
  cfg,
  detail,
  canRestore,
  onConfig,
  onRun,
  onPreset,
  onRestore,
}: {
  cfg: ObjectiveConfig;
  detail: PackDetail | null;
  canRestore: boolean;
  onConfig: (patch: Partial<ObjectiveConfig>) => void;
  onRun: () => void;
  onPreset: (preset: ScenarioPreset) => void;
  onRestore: () => void;
}) {
  return (
    <div>
      <div className="fw-advanced-grid">
        <label className="fw-field">
          <span>Minimum recursive DVA</span>
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={cfg.minDva}
            onChange={(event) =>
              onConfig({ minDva: Number(event.target.value) })
            }
          />
        </label>
        <label className="fw-field">
          <span>Budget USD</span>
          <input
            type="number"
            min="0"
            value={cfg.budgetUsd ?? ""}
            placeholder="UNKNOWN / unconstrained"
            onChange={(event) =>
              onConfig({
                budgetUsd:
                  event.target.value === "" ? null : Number(event.target.value),
              })
            }
          />
        </label>
      </div>
      <label className="fw-toggle-line">
        <input
          type="checkbox"
          checked={cfg.includeDeep}
          onChange={(event) => onConfig({ includeDeep: event.target.checked })}
        />
        <span>
          <strong>Deep planning analysis</strong>
          <br />
          Compute the larger planner/frontier surfaces for this branch. This can
          take longer.
        </span>
      </label>
      {detail?.shocks.length ? (
        <>
          <span className="fw-kicker">Causal shocks</span>
          <div className="fw-check-stack">
            {detail.shocks.map((shock) => (
              <label className="fw-check-card" key={shock.id}>
                <input
                  type="checkbox"
                  checked={cfg.shocks.includes(shock.id)}
                  onChange={(event) =>
                    onConfig({
                      shocks: event.target.checked
                        ? [...cfg.shocks, shock.id]
                        : cfg.shocks.filter((id) => id !== shock.id),
                    })
                  }
                />
                <span>
                  <strong>{shock.name}</strong>
                  <small>
                    {shock.description ||
                      "Propagates through declared world relationships."}
                  </small>
                </span>
              </label>
            ))}
          </div>
        </>
      ) : null}
      {detail?.scenario_presets?.length ? (
        <>
          <div style={{ height: 22 }} />
          <span className="fw-kicker">Declared scenarios</span>
          <div className="fw-preset-list">
            {detail.scenario_presets.map((preset) => (
              <button
                type="button"
                className="fw-preset-button"
                onClick={() => onPreset(preset)}
                key={preset.id}
              >
                <strong>{preset.name}</strong>
                <small>{preset.notes || preset.objective}</small>
              </button>
            ))}
          </div>
        </>
      ) : null}
      <div className="fw-overview-actions">
        <button
          type="button"
          className="fw-action-button primary"
          onClick={onRun}
        >
          Compile this branch
        </button>
        <button
          type="button"
          className="fw-action-button"
          disabled={!canRestore}
          onClick={onRestore}
        >
          Return to evidenced baseline
        </button>
      </div>
    </div>
  );
}

function DesignSurface({
  data,
  selectedId,
  result,
  busy,
  onSelect,
  onCompare,
}: {
  data: OperationalCaseResponse;
  selectedId: string;
  result: DesignComparison | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onCompare: () => void;
}) {
  const alternatives = data.brief.architecture_alternatives;
  return (
    <div className="fw-design-layout">
      <section className="fw-panel">
        <span className="fw-kicker">Dependency-graph rewrite</span>
        <h2>Choose an architecture alternative</h2>
        <p className="fw-panel-copy">
          FORGE validates the declared functional envelope, rewrites the
          dependency graph, re-explodes demand, and re-solves. No text-only
          recommendation is treated as a design change.
        </p>
        <div className="fw-choice-stack">
          {alternatives.length ? (
            alternatives.map((alternative) => (
              <button
                type="button"
                className={`fw-choice ${selectedId === alternative.id ? "active" : ""}`}
                onClick={() => onSelect(alternative.id)}
                key={alternative.id}
              >
                <strong>{alternative.name}</strong>
                <small>
                  replaces {alternative.replaces_part || "declared dependency"}{" "}
                  · {alternative.maturity || "maturity UNKNOWN"}
                </small>
                <span className="chip modelled">
                  {alternative.epistemic_class || "MODELLED"}
                </span>
              </button>
            ))
          ) : (
            <div className="fw-parse-note">
              No validated architecture rewrite is declared for this reference
              variant.
            </div>
          )}
        </div>
        <div className="fw-overview-actions">
          <button
            type="button"
            className="fw-action-button primary"
            disabled={!selectedId || busy}
            onClick={onCompare}
          >
            {busy ? "Re-solving…" : "Compare graph rewrite"}
          </button>
        </div>
      </section>
      <section className="fw-panel">
        <span className="fw-kicker">Computed delta</span>
        <h2>{result?.name || "Baseline versus alternative"}</h2>
        {!result && (
          <p className="fw-panel-copy">
            Select a declared alternative to see changed requirements,
            added/removed dependencies, bottlenecks, evidence, and qualification
            boundaries.
          </p>
        )}
        {result && !result.accepted && (
          <div className="fw-error">
            Rewrite rejected by the declared functional envelope:{" "}
            {result.reasons?.join(" · ") || "reason unavailable"}
          </div>
        )}
        {result?.accepted && result.graph_delta && (
          <>
            <p className="fw-panel-copy">{result.approval_boundary}</p>
            <div className="fw-delta-grid">
              <div className="fw-delta-card">
                <span>Added dependencies</span>
                <strong className="fw-positive">
                  +{result.graph_delta.added_dependencies.length}
                </strong>
              </div>
              <div className="fw-delta-card">
                <span>Removed dependencies</span>
                <strong className="fw-negative">
                  −{result.graph_delta.removed_dependencies.length}
                </strong>
              </div>
              <div className="fw-delta-card">
                <span>Resized requirements</span>
                <strong>{result.graph_delta.changed_demand.length}</strong>
              </div>
            </div>
            <ul className="fw-delta-list">
              {result.graph_delta.changed_demand.slice(0, 18).map((row) => (
                <li key={row.item_id}>
                  <span>
                    <strong>{row.name}</strong>
                    <br />
                    <small>
                      {row.change} · {row.unit}
                    </small>
                  </span>
                  <strong
                    className={row.delta > 0 ? "fw-positive" : "fw-negative"}
                  >
                    {row.delta > 0 ? "+" : ""}
                    {formatNumber(row.delta)}
                  </strong>
                </li>
              ))}
            </ul>
            <details className="op-disclosure">
              <summary>Requirement and binding changes</summary>
              <pre>
                {JSON.stringify(
                  {
                    requirements: result.requirements_change,
                    binding: result.binding_change,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </>
        )}
      </section>
    </div>
  );
}

function WhySurface({
  data,
  selection,
  onSelect,
  onInspect,
}: {
  data: OperationalCaseResponse;
  selection: Selection | null;
  onSelect: (selection: Selection) => void;
  onInspect: () => void;
}) {
  const selectedId =
    selection?.id ||
    data.brief.top_bottlenecks[0]?.item_id ||
    data.brief.target.variant_id;
  const proof = proofChain(data.analysis, selectedId);
  return (
    <div className="fw-why-layout">
      <section className="fw-panel">
        <span className="fw-kicker">Select a consequential dependency</span>
        <h2>Why does this conclusion hold?</h2>
        <div className="fw-choice-stack">
          {data.brief.top_bottlenecks.slice(0, 8).map((row) => (
            <button
              type="button"
              className={`fw-choice ${selectedId === row.item_id ? "active" : ""}`}
              onClick={() => onSelect({ kind: "item", id: row.item_id || "" })}
              key={row.item_id}
            >
              <strong>{row.name || row.item_id}</strong>
              <small>
                {String(row.status || "UNKNOWN")} ·{" "}
                {formatNumber(Number(row.demand_annual ?? 0))}{" "}
                {String(row.unit || "")}/yr
              </small>
            </button>
          ))}
        </div>
        {data.shock_impact && (
          <div className="fw-parse-note">
            Shock path reaches objective:{" "}
            {data.shock_impact.objective_reached_by_causal_path
              ? "YES"
              : "not established"}
            . Inventory posture: {data.shock_impact.inventory_posture}
          </div>
        )}
      </section>
      <section className="fw-panel">
        <span className="fw-kicker">Causal and evidence trace</span>
        <h2>{selectedId}</h2>
        {proof.length ? (
          <div className="fw-proof-list">
            {proof.map((node) => (
              <button
                type="button"
                className="fw-proof-row"
                key={node.node_id}
                onClick={() =>
                  onSelect({
                    kind: node.kind === "evidence" ? "evidence" : "proof",
                    id: node.node_id,
                  })
                }
              >
                <span>{node.kind}</span>
                <strong>{node.label}</strong>
              </button>
            ))}
          </div>
        ) : (
          <p className="fw-panel-copy">
            No proof node matched this local item id. Open the evidence
            inspector for its registry record, capacity envelope, and source
            links.
          </p>
        )}
        {data.shock_impact?.causal_paths?.[0] && (
          <>
            <h3 style={{ marginTop: 18 }}>Shock propagation</h3>
            <div className="fw-why-path">
              {data.shock_impact.causal_paths[0].map((node, index) => (
                <span key={node.entity_id} style={{ display: "contents" }}>
                  <span className="fw-why-node">
                    <strong>{node.name}</strong>
                    <small>{node.kind}</small>
                  </span>
                  {index < data.shock_impact!.causal_paths[0].length - 1 && (
                    <span className="fw-arrow">→</span>
                  )}
                </span>
              ))}
            </div>
          </>
        )}
        <div className="fw-overview-actions">
          <button
            className="fw-action-button primary"
            type="button"
            onClick={onInspect}
          >
            Open full WHY / evidence inspector
          </button>
        </div>
      </section>
    </div>
  );
}

function ReverseBoundary({
  data,
  onResearch,
}: {
  data: OperationalCaseResponse;
  onResearch: () => void;
}) {
  const reverse = data.reverse_buildability;
  const declared = reverse.declared_scenarios?.[0];
  const [lowCeiling, highCeiling] = declared?.ceiling_range_units_per_year ?? [
    null,
    null,
  ];
  return (
    <section className="fw-panel" style={{ marginTop: 14 }}>
      <span className="fw-kicker">Reverse buildability</span>
      <h2>
        {reverse.max_units_per_year === null
          ? "Current ceiling is not adjudicable"
          : `${formatNumber(reverse.max_units_per_year)} units/year under the stated world`}
      </h2>
      <p className="fw-panel-copy">
        {reverse.proof_status ||
          "UNKNOWNs remain UNKNOWN; a missing capacity observation is not converted into zero or an optimistic estimate."}
      </p>
      <div className="fw-overview-actions">
        <span className="chip unknown">{reverse.epistemic_class}</span>
        <span className="chip modelled">
          {reverse.algorithm || reverse.status}
        </span>
        <button type="button" className="fw-action-button" onClick={onResearch}>
          Resolve a binding unknown
        </button>
      </div>
      {declared && (
        <article className="fw-reverse-scenario" aria-label={declared.title}>
          <div className="fw-reverse-scenario-head">
            <div>
              <span className="fw-kicker">Declared planning envelope</span>
              <h3>{declared.title}</h3>
            </div>
            <div className="fw-overview-actions">
              <span className="chip warn">SCENARIO</span>
              <span className="chip modelled">NON-PERSISTENT</span>
            </div>
          </div>
          <div className="fw-reverse-ceiling">
            <span>Conditional ceiling range</span>
            <strong>
              {lowCeiling === null || highCeiling === null
                ? "UNKNOWN"
                : `${formatNumber(lowCeiling)}–${formatNumber(highCeiling)} units/year`}
            </strong>
            <small>
              within a {formatNumber(declared.search_upper_bound ?? 0)}-unit/year
              search bound · heuristic, not a global proof
            </small>
          </div>
          <p className="fw-panel-copy">
            {declared.description} This does not change the evidenced baseline,
            which remains {reverse.epistemic_class}.
          </p>
          {declared.binding_constraints?.length ? (
            <div className="fw-reverse-binding">
              <span className="fw-kicker">First binding constraint</span>
              <strong>{declared.binding_constraints[0]}</strong>
              {declared.ranked_interventions?.[0] && (
                <small>
                  Ranked intervention #1 · {declared.ranked_interventions[0].action}
                  {" · "}
                  {declared.ranked_interventions[0].item_id}
                </small>
              )}
            </div>
          ) : null}
          <details className="op-disclosure fw-reverse-assumptions">
            <summary>
              Inspect the complete assumption boundary (
              {declared.assumption_boundary.explicit_assumption_count} explicit +{" "}
              {declared.assumption_boundary.policy_generated_assumption_count}
              {" "}policy-generated)
            </summary>
            <div>
              <p>
                Capacity policy: {declared.assumption_boundary.capacity_policy} ·
                import policy: {declared.assumption_boundary.import_policy} ·
                baseline mutated: {declared.assumption_boundary.baseline_world_mutated ? "YES" : "NO"}
              </p>
              <ul>
                {declared.assumption_boundary.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
              <div className="fw-assumption-ledger">
                {declared.assumption_boundary.assumptions.map((assumption) => (
                  <div key={assumption.item_id}>
                    <strong>{assumption.item_id}</strong>
                    <span>
                      {formatNumber(assumption.range[0])}–
                      {formatNumber(assumption.range[1])} {assumption.unit}
                    </span>
                    <small>{assumption.basis}</small>
                  </div>
                ))}
              </div>
            </div>
          </details>
        </article>
      )}
    </section>
  );
}

function DrawerShell({
  title,
  wide = false,
  onClose,
  children,
}: {
  title: string;
  wide?: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const returnFocus =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const dialog = dialogRef.current;
    if (!dialog) return undefined;

    const focusableSelector =
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const focusable = () =>
      Array.from(dialog.querySelectorAll<HTMLElement>(focusableSelector)).filter(
        (element) => element.getClientRects().length > 0,
      );
    focusable()[0]?.focus();

    const trapFocus = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const controls = focusable();
      if (!controls.length) {
        event.preventDefault();
        return;
      }
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    dialog.addEventListener("keydown", trapFocus);
    return () => {
      dialog.removeEventListener("keydown", trapFocus);
      returnFocus?.focus();
    };
  }, []);

  return (
    <div
      className="fw-drawer-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside
        ref={dialogRef}
        className={`fw-drawer ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="fw-drawer-head">
          <strong>{title}</strong>
          <button
            type="button"
            className="fw-icon-button"
            aria-label="Close drawer"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <div className="fw-drawer-body">{children}</div>
      </aside>
    </div>
  );
}

function LearnPanel({
  journey,
  surface,
  selection,
}: {
  journey: Journey;
  surface: Surface;
  selection: Selection | null;
}) {
  const explanation =
    journey === "ANALYZE"
      ? "ANALYZE asks whether the physical future can happen under the selected evidence, geography, clocks, and constraints. A NOT_ADJUDICABLE result is useful when it names exactly what evidence is missing."
      : journey === "DESIGN"
        ? "DESIGN applies declared dependency-graph rewrites. Requirements and materials must actually change; passing a model envelope never replaces engineering approval."
        : journey === "EXECUTE"
          ? "EXECUTE converts one solver run into make/buy research, process routes, machinery, qualification gates, work packages, and near-term actions. Candidate suppliers are not automatically qualified."
          : "DISCOVER inverts the registry. Its leverage score is a transparent topology proxy for reuse and downstream reach—not NPV, investment return, or proof of intervention impact.";
  return (
    <div className="fw-learn-copy">
      <span className="fw-kicker">
        {journey} · {surface}
      </span>
      <h2>Read the model without losing its uncertainty.</h2>
      <p>{explanation}</p>
      {selection && (
        <p>
          The current context is <strong>{selection.id}</strong>. Open WHY to
          follow its model relationships and evidence records.
        </p>
      )}
      <div className="fw-legend">
        <div className="fw-legend-row">
          <span className="chip ok">MEASURED</span>
          <p>Directly measured within a declared scope and validity period.</p>
        </div>
        <div className="fw-legend-row">
          <span className="chip reported">REPORTED</span>
          <p>
            A source reports the claim; FORGE preserves its scope and caveat.
          </p>
        </div>
        <div className="fw-legend-row">
          <span className="chip modelled">MODELLED</span>
          <p>
            A transparent computation or declared model contract—not an
            observation.
          </p>
        </div>
        <div className="fw-legend-row">
          <span className="chip warn">ASSUMPTION</span>
          <p>
            An explicit input that can be changed and must not masquerade as
            fact.
          </p>
        </div>
        <div className="fw-legend-row">
          <span className="chip unknown">UNKNOWN</span>
          <p>
            Evidence is insufficient. UNKNOWN is never silently treated as zero
            or supply.
          </p>
        </div>
        <div className="fw-legend-row">
          <span className="chip binding">CONFLICTED</span>
          <p>Comparable evidence disagrees and requires reconciliation.</p>
        </div>
      </div>
    </div>
  );
}

function LoadingState({
  overlay = false,
  compact = false,
}: {
  overlay?: boolean;
  compact?: boolean;
}) {
  return (
    <div
      className="fw-loading"
      style={
        overlay
          ? {
              position: "absolute",
              inset: 0,
              zIndex: 5,
              background: "rgba(9,11,14,.88)",
            }
          : compact
            ? { minHeight: 320 }
            : undefined
      }
    >
      <span className="fw-loading-orbit" aria-hidden="true" />
      <strong>Compiling industrial argument</strong>
      <small>
        Exploding requirements, resolving evidence-bounded capacity, building
        research and execution paths, and preserving every UNKNOWN.
      </small>
    </div>
  );
}

function EmptyWelcome() {
  return (
    <section className="fw-empty-welcome">
      <div>
        <span className="fw-kicker">
          Industrial intelligence · synthesis · execution
        </span>
        <h2>Ask a physical question.</h2>
        <p>
          FORGE will decompose the product or programme, trace processes and
          machines upstream, separate evidence from assumptions, expose the
          blockers, and tell you what to investigate or do next.
        </p>
      </div>
    </section>
  );
}

function adaptCaseOverview(
  data: OperationalCaseResponse,
  detail: PackDetail | null,
): CaseOverviewData {
  const brief = data.brief;
  return {
    caseId: data.analysis.run.run_id,
    target: {
      title: detail?.title || brief.target.variant_id,
      description: brief.target.variant_id,
      quantity: brief.target.annual_units,
      unit: "units/year",
      geography: brief.target.geography,
      deadline: String(brief.target.deadline_year),
      constraints: [
        `≥ ${(brief.target.minimum_dva * 100).toFixed(0)}% recursive DVA`,
      ],
      status: brief.result_class,
      epistemic: "MODELLED",
    },
    conclusion: {
      verdict: brief.result_class,
      summary: brief.conclusion,
      rationale:
        brief.conditions.join(" · ") ||
        "Conclusion is bounded by the visible evidence and scenario.",
      status: brief.result_class,
      epistemic: "DERIVED",
    },
    confidence: {
      value: null,
      valueLabel: brief.important_unknowns.length
        ? `${brief.important_unknowns.length} decision-critical unknowns surfaced`
        : "No decision-critical unknown count returned",
      basis:
        "FORGE does not collapse multi-dimensional evidence quality into a decorative confidence percentage.",
      epistemic: brief.important_unknowns.length ? "UNKNOWN" : "DERIVED",
    },
    bottlenecks: brief.top_bottlenecks.map((row) => ({
      id: row.item_id || row.name || "bottleneck",
      title: row.name || row.item_id || "Unnamed dependency",
      summary: Array.isArray(row.reasons)
        ? row.reasons.join(" · ")
        : String(row.summary || ""),
      status: String(row.status || "BINDING"),
      epistemic: row.epistemic_class || "UNKNOWN",
      metric:
        row.demand_annual != null
          ? `${formatNumber(Number(row.demand_annual))} ${String(row.unit || "")}/yr`
          : null,
    })),
    unknowns: brief.important_unknowns.map((task) => ({
      id: task.id,
      title: task.title,
      summary: task.question,
      detail: task.decision,
      status: task.priority,
      epistemic: task.epistemic_class,
      metric: task.missing_variable,
    })),
    alternatives: brief.architecture_alternatives.map((row) => ({
      id: row.id,
      title: row.name,
      summary: `Replaces ${row.replaces_part || "declared dependency"}`,
      status: row.maturity || "UNKNOWN",
      epistemic: row.epistemic_class || "MODELLED",
      tradeoffs: Object.entries(row.performance_delta || {}).map(
        ([key, value]) => `${key}: ${String(value)}`,
      ),
      dependencyChanges: row.reasons || [],
    })),
    dependencies: brief.critical_dependencies.map((row) => ({
      id: row.item_id,
      title: row.name,
      summary: `${formatNumber(row.gross_annual)} ${row.unit}/yr`,
      detail: row.recipe_id || "No modeled route",
      status: `DEPTH ${row.depth}`,
      epistemic: row.epistemic_class,
      relation: "requires",
      impact: row.recipe_id,
    })),
    actions: brief.explore_actions.map((action) => ({
      id: action,
      title: action.replaceAll("_", " "),
      kind: action,
      status: "AVAILABLE",
      epistemic: "MODELLED",
      approvalRequired: action === "EXECUTE" || action === "REDESIGN",
    })),
  };
}

function adaptExecution(data: OperationalCaseResponse): ExecutionWorkspaceData {
  const execution = data.execution;
  return {
    title: `Execution path · ${data.brief.target.variant_id}`,
    phase: "MODEL-DERIVED / HUMAN APPROVAL REQUIRED",
    status: data.brief.result_class,
    epistemic: "MODELLED",
    makeBuy: execution.make_buy.map((row) => ({
      id: row.item_id,
      item: row.name,
      decision: row.posture,
      rationale: row.reason,
      supplier:
        [
          ...row.linked_supplier_candidates,
          ...row.candidate_supplier_countries,
        ].join(" · ") || "UNKNOWN",
      leadTime: "UNKNOWN",
      qualification: row.supplier_status,
      status: row.capacity_envelope.unknown
        ? "RESEARCH_REQUIRED"
        : "EVIDENCE_PRESENT",
      epistemic: row.epistemic_class,
      evidenceIds: row.evidence_ids,
    })),
    processRoutes: execution.process_routes.map((row) => ({
      id: row.recipe_id,
      title: row.route_name,
      summary: `${row.route_type} · maturity ${row.maturity}`,
      status: row.maturity,
      epistemic: row.epistemic_class,
      evidenceIds: row.evidence_ids,
      steps: row.steps.map((step) => ({
        id: step.id,
        title: step.name,
        detail: [
          step.equipment_ids.length
            ? `equipment: ${step.equipment_ids.join(", ")}`
            : "",
          step.cycle_time ? `cycle: ${step.cycle_time}` : "",
          step.environment,
        ]
          .filter(Boolean)
          .join(" · "),
        status:
          step.yield_fraction == null
            ? "YIELD UNKNOWN"
            : `YIELD ${step.yield_fraction}`,
        epistemic: step.yield_fraction == null ? "UNKNOWN" : "ASSUMPTION",
      })),
    })),
    machinery: execution.machinery_requirements.map((row) => ({
      id: row.equipment_id,
      title: row.name,
      purpose: `Supports ${row.supports_items.join(", ")}`,
      requirement:
        row.domestically_producible == null
          ? "Domestic producibility UNKNOWN"
          : row.domestically_producible
            ? "Domestic production route declared"
            : "External route declared",
      route: row.dominant_supplier_countries.join(", ") || "origin UNKNOWN",
      status:
        row.domestically_producible == null ? "RESEARCH_REQUIRED" : "DECLARED",
      epistemic: row.epistemic_class,
    })),
    qualifications: execution.qualification_tasks.map((row) => ({
      id: row.qualification_id,
      title: row.name,
      criterion:
        row.standard_ref || "Standard/signed acceptance criterion required",
      owner: row.qualifier || "Owner UNKNOWN",
      status: row.status,
      epistemic: row.epistemic_class,
      evidenceIds: row.evidence_ids,
    })),
    workPackages: execution.work_packages.map((row) => ({
      id: row.id,
      title: row.name,
      summary: row.phase,
      sequence: row.phase,
      deliverables: row.acceptance_criteria,
      dependencies: row.depends_on,
      nextAction: row.acceptance_criteria[0] || null,
      approvalRequired: row.human_approval_required,
      status: "PLANNED",
      epistemic: row.epistemic_class,
      evidenceIds: row.evidence_ids,
    })),
    nextActions: execution.next_actions.map((row) => ({
      id: row.task_id || row.qualification_id || row.title,
      title: row.title,
      summary: row.why_now,
      kind: row.action,
      status: "NEXT",
      epistemic: row.epistemic_class,
      approvalRequired: row.human_approval_required,
    })),
  };
}

function adaptResearch(
  data: OperationalCaseResponse,
  initialTaskId: string | null,
): ResearchWorkspaceData {
  return {
    title: `Resolve UNKNOWNs · ${data.brief.target.variant_id}`,
    initialTaskId,
    reviewers: [
      {
        id: "current-human-reviewer",
        name: "Current human reviewer",
        role: "Explicit evidence promotion and scenario approval",
        status: "REQUIRED",
        epistemic: "UNKNOWN",
      },
    ],
    tasks: data.research.tasks.map((task) => ({
      id: task.id,
      title: task.title,
      question: task.question,
      purpose: task.decision,
      status: "OPEN",
      priority: task.priority,
      epistemic: task.epistemic_class,
      requestedBy: data.analysis.run.run_id,
      expectedOutput: task.missing_variable,
      evidenceRequirements: task.source_plan,
      scenarioOverlay: task.missing_variable.includes("capacity")
        ? {
            id: `overlay:${task.id}`,
            title: "Optional capacity-range scenario overlay",
            description:
              "If a numeric range is captured and explicitly approved, FORGE may re-run this case without mutating the checked-in baseline.",
            assumptions: [
              "Range remains ASSUMPTION until persistent repository review",
              "Conflict reconciliation must pass",
            ],
            effects: [
              `Overrides ${task.target_entity_id} only for this scenario re-run`,
            ],
            epistemic: "ASSUMPTION",
            requiresHumanApproval: true,
          }
        : null,
    })),
  };
}

function adaptProgram(
  data: OperationalCaseResponse,
): ProgramTimelineView | null {
  const source = data.program;
  if (!source.available || !source.annual_projection.length) return null;
  const objective = source.objective || {};
  let priorOptimistic = Number(objective.existing_capacity_gw ?? 0);
  let priorConservative = priorOptimistic;
  const optimistic = source.annual_projection.map((row) => {
    const cumulative = row.commissioned_gw_optimistic;
    const point = {
      year: row.year,
      annualCapacity: Math.max(0, cumulative - priorOptimistic),
      cumulativeCapacity: cumulative,
      epistemic: row.epistemic_class,
    };
    priorOptimistic = cumulative;
    return point;
  });
  const conservative = source.annual_projection.map((row) => {
    const cumulative = row.commissioned_gw_conservative;
    const point = {
      year: row.year,
      annualCapacity: Math.max(0, cumulative - priorConservative),
      cumulativeCapacity: cumulative,
      epistemic: row.epistemic_class,
    };
    priorConservative = cumulative;
    return point;
  });
  return {
    objective: {
      id: String(objective.id || data.brief.target.variant_id),
      label: String(objective.id || "Declared programme scenario")
        .replace(/[_-]+/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase()),
      target:
        typeof objective.target_gw === "number" ? objective.target_gw : null,
      unit: "GWe",
      geography: data.brief.target.geography,
      deadlineYear: Number(
        objective.target_year || data.brief.target.deadline_year,
      ),
      basis: "STOCK",
      epistemic: String(
        objective.epistemic_class || source.epistemic_class || "SCENARIO",
      ),
      note: "Annual manufacturing flow and cumulative installed stock are displayed separately.",
    },
    tranches: (source.tranches || []).map((row) => {
      const window = Array.isArray(row.commissioning_window)
        ? row.commissioning_window
        : [];
      return {
        id: String(row.id || "tranche"),
        label: String(row.name || row.id || "Unnamed tranche"),
        startYear: Number(row.start_year || 0) || null,
        endYear: Number(window[1] || 0) || null,
        cumulativeCapacity:
          Number(row.units || 0) * Number(row.unit_capacity_gw || 0),
        status: String(row.phase || "UNKNOWN"),
        epistemic: String(row.epistemic_class || "SCENARIO"),
        note: String(row.notes || ""),
      };
    }),
    optimistic: {
      id: "optimistic",
      label: "Optimistic commissioning window",
      points: optimistic,
      epistemic: "SCENARIO",
      annualUnit: "GWe/year",
      cumulativeUnit: "GWe",
      note: "Earliest declared tranche dates; not a probability bound.",
    },
    conservative: {
      id: "conservative",
      label: "Conservative commissioning window",
      points: conservative,
      epistemic: "SCENARIO",
      annualUnit: "GWe/year",
      cumulativeUnit: "GWe",
      note: "Latest declared tranche dates; not a probability bound.",
    },
    gates: (source.system_gates || []).map((row) => ({
      id: String(row.id || "gate"),
      label: String(row.name || row.title || row.id || "Unnamed gate"),
      gateType: String(row.gate_type || row.type || "system"),
      year: typeof row.year === "number" ? row.year : null,
      status: String(row.status || "UNKNOWN"),
      state: String(row.status || "UNKNOWN"),
      epistemic: String(row.epistemic_class || "UNKNOWN"),
      detail: String(row.notes || row.description || ""),
      dependencies: Array.isArray(row.depends_on)
        ? row.depends_on.map(String)
        : [],
    })),
  };
}

function adaptCapabilities(
  data: OperationalCaseResponse,
): CapabilityLeverageView[] {
  return data.discover.capabilities.map((row) => ({
    id: row.capability_id,
    canonicalId: row.capability_id,
    name: row.name,
    kind: "canonical capability",
    epistemic: row.epistemic_class,
    leverageProxy: row.leverage_proxy,
    crossSectorReuse: row.cross_sector_reuse,
    crossSectorReuseLabels: row.mapped_pack_ids,
    downstreamUnlock: row.downstream_unlock_count,
    downstreamUnlockLabels: row.downstream_objective_ids,
    reverseReach: row.reverse_dependency_reach,
    evidenceGap: row.evidence_gap_fraction,
    evidenceGapLabel: `${(row.evidence_gap_fraction * 100).toFixed(0)}% unresolved mapped evidence`,
    taskCount: row.open_research_task_count,
    note: "Topology-derived leverage proxy; not economic option value, causal impact, qualified supply, or investment return.",
  }));
}

function buildAssemblyData(
  response: SolveResponse | null,
  world: WorldSlice | null,
  cfg: ObjectiveConfig,
) {
  if (!response) return { nodes: [], edges: [] };
  const names = new Map(
    (world?.nodes || []).map((node) => [
      localId(node.id, cfg.packId),
      node.name,
    ]),
  );
  const epistemic = new Map(
    response.capacity_envelopes.map((row) => [row.item, row.epistemic]),
  );
  const items = response.explosion.items
    .slice()
    .sort((a, b) => a.depth - b.depth || b.gross - a.gross)
    .slice(0, 96);
  const nodes = [
    {
      id: cfg.variantId,
      label:
        response.variants.find((variant) => variant.id === cfg.variantId)
          ?.name || cfg.variantId,
      kind: "product_variant",
      depth: 0,
      value: cfg.annualUnits,
      unit: "units/year",
      epistemicClass: "MODELLED",
    },
    ...items.map((item) => ({
      id: item.item,
      label: names.get(item.item) || item.item.replaceAll("_", " "),
      kind:
        item.depth <= 1
          ? "assembly"
          : item.depth === 2
            ? "component"
            : item.depth === 3
              ? "process input"
              : "upstream material/equipment",
      depth: item.depth + 1,
      value: item.gross,
      unit: item.unit,
      epistemicClass: epistemic.get(item.item) || "UNKNOWN",
    })),
  ];
  const ids = new Set(nodes.map((node) => node.id));
  const edges = (world?.edges || [])
    .map((edge) => ({
      src: localId(edge.src, cfg.packId),
      dst: localId(edge.dst, cfg.packId),
      relation: edge.relation,
    }))
    .filter((edge) => ids.has(edge.src) && ids.has(edge.dst));
  if (!edges.length)
    for (const item of items)
      if (item.depth === 1)
        edges.push({
          src: cfg.variantId,
          dst: item.item,
          relation: "requires",
        });
  return { nodes, edges };
}

function proofChain(response: SolveResponse, selectedId: string) {
  const nodes = new Map(
    response.proof_graph.nodes.map((node) => [node.node_id, node]),
  );
  const direct = nodes.has(selectedId)
    ? selectedId
    : response.capacity_envelopes.find((row) => row.item === selectedId)
        ?.proof ||
      response.proof_graph.nodes.find((node) => node.label.includes(selectedId))
        ?.node_id;
  if (!direct) return [];
  const seen = new Set<string>();
  const rows: SolveResponse["proof_graph"]["nodes"] = [];
  const visit = (id: string, depth: number) => {
    if (seen.has(id) || depth > 16 || rows.length >= 30) return;
    seen.add(id);
    const node = nodes.get(id);
    if (!node) return;
    rows.push(node);
    for (const edge of response.proof_graph.edges)
      if (edge.to_id === id) visit(edge.from_id, depth + 1);
  };
  visit(direct, 0);
  return rows.reverse();
}

function parseNumericRange(value: string): [number, number] | null {
  const numbers =
    value
      .match(/(?:^|[^A-Za-z])(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)/gi)
      ?.map((raw) => Number(raw.replace(/^[^\d-]+/, "")))
      .filter(Number.isFinite) ?? [];
  if (!numbers.length) return null;
  const lo = numbers[0];
  const hi = numbers.length > 1 ? numbers[1] : numbers[0];
  if (lo < 0 || hi < lo) return null;
  return [lo, hi];
}

function cloneConfig(cfg: ObjectiveConfig): ObjectiveConfig {
  return {
    ...cfg,
    fundedProjects: [...cfg.fundedProjects],
    shocks: [...cfg.shocks],
    assumptions: Object.fromEntries(
      Object.entries(cfg.assumptions).map(([key, value]) => [
        key,
        [value[0], value[1]] as [number, number],
      ]),
    ),
  };
}

function configIdentity(cfg: ObjectiveConfig): string {
  return JSON.stringify({
    ...cfg,
    fundedProjects: [...cfg.fundedProjects].sort(),
    shocks: [...cfg.shocks].sort(),
    assumptions: Object.entries(cfg.assumptions).sort(([left], [right]) =>
      left.localeCompare(right),
    ),
  });
}

function localId(id: string, packId: string): string {
  const prefix = `pack:${packId}:`;
  return id.startsWith(prefix) ? id.slice(prefix.length) : id;
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "UNKNOWN";
  return new Intl.NumberFormat(undefined, {
    notation: Math.abs(value) >= 10_000 ? "compact" : "standard",
    maximumFractionDigits: 2,
  }).format(value);
}
