import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchIndiaDomains, searchIndia } from "./india-api";
import type { IndiaDomain } from "./india-types";
import BuildabilityDashboard from "./ui-rebuild/BuildabilityDashboard";
import { analyzeBuildability, fetchBuildability } from "./ui-rebuild/buildability-api";
import type {
  BuildabilityDomain,
  BuildabilityItem,
  BuildabilityMode,
  BuildabilityTabId,
  BuildabilityViewModel,
} from "./ui-rebuild/buildability-types";

const DEFAULT_QUERY = "MRI machine";
const DOMAIN_SHORT_NAMES: Record<string, string> = {
  "01": "Aerospace & Space",
  "02": "Defense & Strategic",
  "03": "Energy & Nuclear",
  "04": "Electronics & Semiconductors",
  "05": "Machines & Robotics",
  "06": "Materials & Chemicals",
  "07": "Medical & Scientific",
  "08": "Food & Agriculture",
  "09": "Transport & Mobility",
  "10": "Infrastructure & Heavy Industry",
  "11": "Consumer & Manufacturing",
  "12": "Foundational Capabilities",
};
type Route = { recordId: string | null; domainId: string | null };

function readRoute(): Route {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const match = path.match(/^\/india\/records\/(.+)$/);
  return {
    recordId: match ? decodeURIComponent(match[1]) : null,
    domainId: new URLSearchParams(window.location.search).get("domain"),
  };
}

function recordHref(recordId: string): string {
  return `/india/records/${encodeURIComponent(recordId)}`;
}

function publicDomains(domains: IndiaDomain[]): BuildabilityDomain[] {
  return domains.map((domain) => ({
    id: domain.id,
    name: domain.name,
    shortName: DOMAIN_SHORT_NAMES[domain.id] || domain.name,
    description: domain.description,
    recordCount: domain.recordCount,
    status: domain.status,
  }));
}

function errorText(error: unknown): string {
  return error instanceof Error && error.message ? error.message : "The buildability analysis could not be loaded.";
}

function updateMetadata(viewModel: BuildabilityViewModel | null) {
  document.title = viewModel?.title ? `${viewModel.title} · FORGE INDIA` : "FORGE INDIA · What can India build?";
  const description = viewModel?.plainSummary || "Explore what India can build, what it depends on, and what must be localized next.";
  let meta = document.head.querySelector<HTMLMetaElement>('meta[name="description"]');
  if (!meta) {
    meta = document.createElement("meta");
    meta.name = "description";
    document.head.appendChild(meta);
  }
  meta.content = description;
}

export default function IndiaApp() {
  const initialRoute = useMemo(readRoute, []);
  const [route, setRoute] = useState<Route>(initialRoute);
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [domains, setDomains] = useState<BuildabilityDomain[]>([]);
  const [activeDomainId, setActiveDomainId] = useState<string | null>(initialRoute.domainId);
  const [viewModel, setViewModel] = useState<BuildabilityViewModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<BuildabilityMode>("Analyze");
  const [activeTab, setActiveTab] = useState<BuildabilityTabId>("systems");
  const request = useRef<AbortController | null>(null);

  const load = useCallback(async (target: { recordId?: string | null; query?: string }, push = false) => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    try {
      const next = target.recordId
        ? await fetchBuildability(target.recordId, controller.signal)
        : await analyzeBuildability(target.query || DEFAULT_QUERY, controller.signal);
      if (controller.signal.aborted) return;
      setViewModel(next);
      setQuery(next.title);
      const matchingDomain = domains.find((domain) => domain.name === next.domain);
      if (matchingDomain) setActiveDomainId(matchingDomain.id);
      if (push && target.recordId) {
        window.history.pushState({ forgeIndia: true }, "", recordHref(target.recordId));
        setRoute({ recordId: target.recordId, domainId: null });
      }
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorText(cause));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [domains]);

  useEffect(() => {
    const controller = new AbortController();
    void fetchIndiaDomains(controller.signal)
      .then((rows) => setDomains(publicDomains(rows)))
      .catch(() => setDomains([]));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    void load(initialRoute.recordId ? { recordId: initialRoute.recordId } : { query: DEFAULT_QUERY });
    return () => request.current?.abort();
    // Initial load is stable; explicit navigation owns subsequent requests.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => updateMetadata(viewModel), [viewModel]);

  useEffect(() => {
    const onPopState = () => {
      const next = readRoute();
      setRoute(next);
      setActiveDomainId(next.domainId);
      void load(next.recordId ? { recordId: next.recordId } : { query: DEFAULT_QUERY });
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [load]);

  const analyze = useCallback(async (term: string) => {
    const target = term.trim();
    if (!target) return;
    const searchTarget = target.replace(/\bcentres?\b/gi, (word) => word.toLowerCase().endsWith("s") ? "centers" : "center");
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    try {
      const matches = await searchIndia(searchTarget, controller.signal, { domain: activeDomainId, limit: 8 });
      const credible = matches.filter((match) => !["fuzzy", "related"].includes((match.matchType || "").toLowerCase()));
      const selected = credible.find((match) => !match.record.isReferenceOnly) || credible[0];
      if (!selected?.record.id) throw new Error(`No mapped industrial product matches “${target}”.`);
      const next = await fetchBuildability(selected.record.id, controller.signal);
      if (controller.signal.aborted) return;
      setViewModel(next);
      setQuery(next.title);
      window.history.pushState({ forgeIndia: true }, "", recordHref(selected.record.id));
      setRoute({ recordId: selected.record.id, domainId: null });
      const matchingDomain = domains.find((domain) => domain.name === next.domain);
      if (matchingDomain) setActiveDomainId(matchingDomain.id);
    } catch (cause) {
      if (!controller.signal.aborted) setError(errorText(cause));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [activeDomainId, domains]);

  const chooseDomain = useCallback((domain: BuildabilityDomain) => {
    setActiveDomainId(domain.id);
    const params = new URLSearchParams({ domain: domain.id });
    window.history.replaceState({ forgeIndia: true }, "", `/india?${params.toString()}`);
    setRoute({ recordId: null, domainId: domain.id });
  }, []);

  const followItem = useCallback((item: BuildabilityItem) => {
    if (item.title) void analyze(item.title);
  }, [analyze]);

  const retry = useCallback(() => {
    void load(route.recordId ? { recordId: route.recordId } : { query: query || DEFAULT_QUERY });
  }, [load, query, route.recordId]);

  return (
    <BuildabilityDashboard
      viewModel={viewModel}
      domains={domains}
      activeDomainId={activeDomainId}
      query={query}
      loading={loading}
      error={error}
      activeMode={activeMode}
      activeTab={activeTab}
      onQueryChange={setQuery}
      onAnalyze={(term) => void analyze(term)}
      onDomainSelect={chooseDomain}
      onModeChange={setActiveMode}
      onTabSelect={setActiveTab}
      onSystemSelect={followItem}
      onItemSelect={followItem}
      onBottleneckSelect={followItem}
      onPathSelect={() => setActiveTab("systems")}
      onEvidenceSelect={() => setActiveTab("evidence")}
      onPanelOpen={(panel) => {
        if (panel === "map" || panel === "facilities") setActiveTab("facilities");
        else if (panel === "evidence") setActiveTab("evidence");
        else if (panel === "bottlenecks" || panel === "localization") setActiveTab("systems");
        else setActiveTab(panel);
      }}
      onRetry={retry}
    />
  );
}
