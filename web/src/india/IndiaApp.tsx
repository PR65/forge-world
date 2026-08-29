import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchIndiaDomains, searchIndia } from "./india-api";
import type { IndiaDomain } from "./india-types";
import ProductWorkbench from "./product-v1/ProductWorkbench";
import type { ProductMode, ProductResolutionNotice } from "./product-v1/ProductWorkbench";
import type { WhySelection } from "./product-v1";
import { resolveObjective } from "./product-v1/objective-api";
import { fetchBuildability } from "./ui-rebuild/buildability-api";
import type { BuildabilityDomain, BuildabilityItem, BuildabilityViewModel } from "./ui-rebuild/buildability-types";

const DEFAULT_OBJECTIVE = "industrial freeze dryer";
const DOMAIN_SHORT_NAMES: Record<string, string> = {
  "01": "Aerospace & Space", "02": "Defense & Strategic", "03": "Energy & Nuclear",
  "04": "Electronics & Semiconductors", "05": "Machines & Robotics", "06": "Materials & Chemicals",
  "07": "Medical & Scientific", "08": "Food & Agriculture", "09": "Transport & Mobility",
  "10": "Infrastructure & Heavy Industry", "11": "Consumer & Manufacturing", "12": "Foundational Capabilities",
};

interface Route { recordId: string | null; query: string | null; domainId: string | null; mode: ProductMode }

function publicDomains(domains: IndiaDomain[]): BuildabilityDomain[] {
  return domains.map((domain) => ({
    id: domain.id, name: domain.name, shortName: DOMAIN_SHORT_NAMES[domain.id] || domain.name,
    description: domain.description, recordCount: domain.recordCount, status: domain.status,
  }));
}

function readRoute(): Route {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const match = path.match(/^\/india\/records\/(.+)$/);
  const params = new URLSearchParams(window.location.search);
  const requestedMode = (params.get("mode") || "ANALYZE").toUpperCase();
  const mode: ProductMode = requestedMode === "BUILD" || requestedMode === "DISCOVER" ? requestedMode : "ANALYZE";
  return { recordId: match ? decodeURIComponent(match[1]) : null, query: params.get("q"), domainId: params.get("domain"), mode };
}

function updateUrl(mode: ProductMode, query: string, domainId: string | null, push: boolean) {
  const params = new URLSearchParams({ mode: mode.toLowerCase() });
  if (query.trim()) params.set("q", query.trim());
  if (mode === "DISCOVER" && domainId) params.set("domain", domainId);
  window.history[push ? "pushState" : "replaceState"]({ forgeIndia: true }, "", `/india?${params.toString()}`);
}

function errorText(error: unknown): string {
  return error instanceof Error && error.message ? error.message : "The industrial map could not be loaded.";
}

function updateMetadata(viewModel: BuildabilityViewModel | null, mode: ProductMode) {
  document.title = viewModel?.title ? `${viewModel.title} · ${mode} · FORGE INDIA` : `${mode} · FORGE INDIA`;
  const description = viewModel?.plainSummary || "A first-order map of what it takes to manufacture physical products in India.";
  let meta = document.head.querySelector<HTMLMetaElement>('meta[name="description"]');
  if (!meta) { meta = document.createElement("meta"); meta.name = "description"; document.head.appendChild(meta); }
  meta.content = description;
}

export default function IndiaApp() {
  const initialRoute = useMemo(readRoute, []);
  const [mode, setMode] = useState<ProductMode>(initialRoute.mode);
  const [query, setQuery] = useState(initialRoute.query || DEFAULT_OBJECTIVE);
  const [objectiveText, setObjectiveText] = useState(initialRoute.query || DEFAULT_OBJECTIVE);
  const [domains, setDomains] = useState<BuildabilityDomain[]>([]);
  const [activeDomainId, setActiveDomainId] = useState<string | null>(initialRoute.domainId);
  const [domainItems, setDomainItems] = useState<BuildabilityItem[]>([]);
  const [viewModel, setViewModel] = useState<BuildabilityViewModel | null>(null);
  const [resolution, setResolution] = useState<ProductResolutionNotice | null>(null);
  const [selection, setSelection] = useState<WhySelection | null>(null);
  const [addedItems, setAddedItems] = useState<BuildabilityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const domainRequest = useRef<AbortController | null>(null);
  const generation = useRef(0);

  const loadRecord = useCallback(async (recordId: string) => {
    request.current?.abort();
    const controller = new AbortController(); request.current = controller; const current = ++generation.current;
    setLoading(true); setError(null); setResolution(null);
    try {
      const next = await fetchBuildability(recordId, controller.signal);
      if (controller.signal.aborted || current !== generation.current) return;
      setViewModel(next); setQuery(next.title); setObjectiveText(next.title);
    } catch (cause) {
      if (!controller.signal.aborted && current === generation.current) setError(errorText(cause));
    } finally { if (!controller.signal.aborted && current === generation.current) setLoading(false); }
  }, []);

  const loadConfirmed = useCallback(async (title: string, push = true) => {
    const target = title.trim(); if (!target) return;
    request.current?.abort();
    const controller = new AbortController(); request.current = controller; const current = ++generation.current;
    setLoading(true); setError(null); setSelection(null);
    try {
      const resolved = await resolveObjective(target, controller.signal);
      const next = resolved.analysis;
      if (controller.signal.aborted || current !== generation.current) return;
      if (!resolved.canAnalyze || !next) throw new Error(`The confirmed family “${target}” could not be resolved safely.`);
      setViewModel(next); setQuery(target); setObjectiveText(target);
      setResolution({ quality: "strong", message: `Using the confirmed mapped product: ${next.title}.`, productQuery: target });
      setMode("ANALYZE"); updateUrl("ANALYZE", target, null, push);
    } catch (cause) {
      if (!controller.signal.aborted && current === generation.current) setError(errorText(cause));
    } finally { if (!controller.signal.aborted && current === generation.current) setLoading(false); }
  }, []);

  const analyze = useCallback(async (rawInput: string, push = true, targetMode: ProductMode = "ANALYZE") => {
    const target = rawInput.trim(); if (!target) return;
    request.current?.abort();
    const controller = new AbortController(); request.current = controller; const current = ++generation.current;
    setLoading(true); setError(null); setSelection(null); setQuery(target); setObjectiveText(target); setMode(targetMode);
    try {
      const resolved = await resolveObjective(target, controller.signal);
      if (controller.signal.aborted || current !== generation.current) return;
      const quality: ProductResolutionNotice["quality"] = resolved.canAnalyze ? "strong" : resolved.requiresConfirmation ? "nearest" : "unresolved";
      setResolution({
        quality, message: `${resolved.message} ${resolved.honestyNote}`.trim(), productQuery: resolved.objective.productQuery,
        candidates: resolved.candidates.map((candidate) => candidate.title),
      });
      if (!resolved.canAnalyze || !resolved.selected) { setViewModel(null); updateUrl(targetMode, target, null, push); return; }
      const next = resolved.analysis;
      if (!next) throw new Error("The resolved product did not return a composed industrial view.");
      setViewModel(next);
      const matchingDomain = domains.find((domain) => domain.name === next.domain);
      if (matchingDomain) setActiveDomainId(matchingDomain.id);
      updateUrl(targetMode, target, targetMode === "DISCOVER" ? activeDomainId : null, push);
    } catch (cause) {
      if (!controller.signal.aborted && current === generation.current) { setViewModel(null); setError(errorText(cause)); }
    } finally { if (!controller.signal.aborted && current === generation.current) setLoading(false); }
  }, [activeDomainId, domains]);

  useEffect(() => {
    const controller = new AbortController();
    void fetchIndiaDomains(controller.signal).then((rows) => setDomains(publicDomains(rows))).catch(() => setDomains([]));
    return () => controller.abort();
  }, []);

  // Catalog warm-up can outlast the lightweight domain request timeout on a
  // cold local server. Re-entering DISCOVER gets one fresh bounded attempt
  // instead of leaving a permanently blank domain section.
  useEffect(() => {
    if (mode !== "DISCOVER" || domains.length) return;
    const controller = new AbortController();
    void fetchIndiaDomains(controller.signal).then((rows) => setDomains(publicDomains(rows))).catch(() => undefined);
    return () => controller.abort();
  }, [domains.length, mode]);

  useEffect(() => {
    if (initialRoute.recordId) void loadRecord(initialRoute.recordId); else void analyze(initialRoute.query || DEFAULT_OBJECTIVE, false, initialRoute.mode);
    return () => request.current?.abort();
    // Initial navigation is captured once; popstate owns later routes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => updateMetadata(viewModel, mode), [mode, viewModel]);

  const browseDomain = useCallback(async (domainId: string) => {
    domainRequest.current?.abort();
    const controller = new AbortController(); domainRequest.current = controller;
    setDomainItems([]);
    try {
      const matches = await searchIndia("", controller.signal, { domain: domainId, limit: 12 });
      if (controller.signal.aborted) return;
      setDomainItems(matches.map(({ record }) => ({
        title: record.displayName || record.canonicalName,
        summary: record.explanation || record.use,
        kind: record.kind,
        category: record.category,
        status: record.indiaStatus,
        statusLabel: record.indiaStatus,
        epistemicClass: record.statusEpistemicClass,
      })));
    } catch {
      if (!controller.signal.aborted) setDomainItems([]);
    }
  }, []);

  useEffect(() => {
    if (mode === "DISCOVER" && activeDomainId) void browseDomain(activeDomainId);
    return () => domainRequest.current?.abort();
  }, [activeDomainId, browseDomain, mode]);

  useEffect(() => {
    const onPopState = () => {
      const next = readRoute(); setMode(next.mode); setActiveDomainId(next.domainId);
      if (next.recordId) void loadRecord(next.recordId); else if (next.query) void analyze(next.query, false, next.mode);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [analyze, loadRecord]);

  const changeMode = useCallback((next: ProductMode) => {
    setMode(next); setSelection(null); updateUrl(next, objectiveText || query, activeDomainId, true);
  }, [activeDomainId, objectiveText, query]);

  const chooseDomain = useCallback((domain: BuildabilityDomain) => {
    setActiveDomainId(domain.id); setMode("DISCOVER");
    updateUrl("DISCOVER", objectiveText || query, domain.id, true);
  }, [objectiveText, query]);

  const addToBuildPath = useCallback((item: BuildabilityItem) => {
    setAddedItems((current) => current.some((candidate) => candidate.title.toLowerCase() === item.title.toLowerCase()) ? current : [...current, item]);
    setSelection(null);
  }, []);
  const removeFromBuildPath = useCallback((item: BuildabilityItem) => {
    setAddedItems((current) => current.filter((candidate) => candidate.title.toLowerCase() !== item.title.toLowerCase()));
  }, []);

  return (
    <ProductWorkbench
      activeDomainId={activeDomainId} addedItems={addedItems} domainItems={domainItems} domains={domains} error={error} loading={loading}
      mode={mode} objectiveText={objectiveText} onAddToBuildPath={addToBuildPath}
      onAnalyze={(value) => void analyze(value)} onCandidateSelect={(value) => void loadConfirmed(value)}
      onDomainSelect={chooseDomain} onGoDeeper={(item) => void loadConfirmed(item.title)} onModeChange={changeMode}
      onQueryChange={setQuery} onRemoveAddedItem={removeFromBuildPath} onRetry={() => void analyze(objectiveText || query)}
      onSelectionChange={setSelection} query={query} resolution={resolution} selection={selection} viewModel={viewModel}
    />
  );
}
