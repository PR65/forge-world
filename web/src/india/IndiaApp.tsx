import {
  FormEvent,
  useCallback,
  useDeferredValue,
  useEffect,
  useRef,
  useState,
  startTransition,
  type MouseEvent as ReactMouseEvent,
} from "react";
import IndiaRecordView from "./IndiaRecordView";
import {
  fetchIndiaDiscover,
  fetchIndiaDomains,
  fetchIndiaRecord,
  fetchIndiaSummary,
  searchIndia,
} from "./india-api";
import {
  displayEpistemicClass,
  displayStatus,
  epistemicTone,
  firstSentence,
  formatCount,
  statusTone,
} from "./india-ui";
import type {
  IndiaDiscoverResult,
  IndiaDomain,
  IndiaLink,
  IndiaRecord,
  IndiaSearchResult,
  IndiaSummary,
} from "./india-types";
import "./india.css";

const DISCOVERY_PROMPTS = [
  { label: "Transformer", query: "transformer" },
  { label: "Packaging machine", query: "packaging machine" },
  { label: "Textile machine", query: "textile machine" },
  { label: "Pumps and valves", query: "pumps valves" },
];

const TAGLINE_WORDS = "Start with an object. Follow the chain. See what India can build next.".split(" ");

type LoadState = "idle" | "loading" | "ready" | "error";
type Route = {
  kind: "home" | "record" | "not-found";
  recordId: string | null;
  query: string;
  domain: string | null;
};

const HOME_PATHS = new Set(["/", "/india", "/india/"]);

function readRoute(): Route {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  const params = new URLSearchParams(window.location.search);
  const query = params.get("q") || "";
  const domain = params.get("domain") || null;
  const recordMatch = path.match(/^\/india\/records\/(.+)$/);
  if (recordMatch) {
    return { kind: "record", recordId: decodeURIComponent(recordMatch[1]), query, domain };
  }
  if (HOME_PATHS.has(path)) return { kind: "home", recordId: null, query, domain };
  return { kind: "not-found", recordId: null, query: "", domain: null };
}

function routeHref(route: Route): string {
  const path = route.kind === "record" && route.recordId
    ? `/india/records/${encodeURIComponent(route.recordId)}`
    : "/";
  const params = new URLSearchParams();
  if (route.query.trim()) params.set("q", route.query.trim());
  if (route.kind === "home" && route.domain) params.set("domain", route.domain);
  const suffix = params.toString();
  return suffix ? `${path}?${suffix}` : path;
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function recordHref(id: string): string {
  return `/india/records/${encodeURIComponent(id)}`;
}

function interceptRecordLink(event: ReactMouseEvent<HTMLAnchorElement>, onOpen: () => void) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  onOpen();
}

function upsertMeta(selector: string, attribute: string, value: string) {
  let node = document.head.querySelector<HTMLMetaElement>(selector);
  if (!node) {
    node = document.createElement("meta");
    const marker = selector.includes("property=\"") ? "property" : "name";
    const match = selector.match(new RegExp(`${marker}=\"([^\"]+)\"`));
    if (!match) return;
    node.setAttribute(attribute, match[1]);
    document.head.appendChild(node);
  }
  node.content = value;
}

function SearchBox({
  value,
  onChange,
  onSubmit,
  compact = false,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  compact?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
    inputRef.current?.focus();
  };
  return (
    <form className={`india-search ${compact ? "compact" : ""}`} onSubmit={submit} role="search">
      <label htmlFor={compact ? "india-search-compact" : "india-search-main"}>
        Search products, capabilities, machines, materials
      </label>
      <div className="india-search-row">
        <span className="india-search-mark" aria-hidden="true">⌕</span>
        <input
          ref={inputRef}
          id={compact ? "india-search-compact" : "india-search-main"}
          name="q"
          type="search"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Try transformer, CNC machine, bearings, textile machine…"
          autoComplete="off"
          spellCheck={false}
        />
        <button className="india-button primary" type="submit">Search atlas</button>
      </div>
      <p className="india-search-hint">Use a plain name. Results stay linked to their evidence state.</p>
    </form>
  );
}

function SearchResults({
  query,
  scopeLabel,
  state,
  error,
  results,
  onOpen,
  onRetry,
}: {
  query: string;
  scopeLabel: string | null;
  state: LoadState;
  error: string | null;
  results: IndiaSearchResult[];
  onOpen: (id: string) => void;
  onRetry: () => void;
}) {
  const term = query.trim();
  if (!term && !scopeLabel) return null;
  if (term.length === 1) {
    return <p className="india-search-message">Type at least two characters to search the atlas.</p>;
  }
  if (state === "loading") {
    return (
      <div className="india-result-skeleton" role="status" aria-label="Searching…">
        <span className="india-skeleton-line wide" />
        <span className="india-skeleton-line medium" />
        <span className="india-skeleton-line wide" />
      </div>
    );
  }
  if (state === "error") {
    return (
      <div className="india-state india-state-inline" role="alert">
        <span className="india-state-mark">!</span>
        <div>
          <strong>Search is unavailable</strong>
          <p>{error || "The India search endpoint did not return a result."}</p>
          <button className="india-button secondary" type="button" onClick={onRetry}>Retry search</button>
        </div>
      </div>
    );
  }
  if (!results.length) {
    return (
      <div className="india-empty-search">
        <strong>{scopeLabel ? `No mapped records in ${scopeLabel}.` : `No mapped record matches “${term}”.`}</strong>
        <span>{scopeLabel ? "Try a broader name or clear the domain filter." : "Try a broader object name, or browse a domain below."}</span>
      </div>
    );
  }
  return (
    <section className="india-results" aria-live="polite" aria-label="Search results">
      <div className="india-results-head">
        <span>{results.length} mapped result{results.length === 1 ? "" : "s"}{scopeLabel ? ` in ${scopeLabel}` : ""}</span>
        <span>Open a record to inspect its chain</span>
      </div>
      <ul>
        {results.slice(0, 50).map((result) => (
          <li key={result.record.id}>
            <a href={recordHref(result.record.id)} onClick={(event) => interceptRecordLink(event, () => onOpen(result.record.id))}>
              <span className="india-result-topline">
                <span className={`india-status tiny ${statusTone(result.record.indiaStatus)}`}>
                  {displayStatus(result.record.indiaStatus)}
                </span>
                <span className={`india-epistemic-chip ${epistemicTone(result.record.statusEpistemicClass)}`}>
                  {displayEpistemicClass(result.record.statusEpistemicClass)}
                </span>
              </span>
              <strong>{result.record.displayName}</strong>
              <span>{firstSentence(result.record.explanation)}</span>
              <small>{result.record.kind} · {result.record.category}</small>
              <span className="india-result-signal">
                {result.matchType ? `Match: ${result.matchType}` : null}
                {result.matchedOn.length ? ` · ${result.matchedOn.slice(0, 2).join(", ")}` : null}
              </span>
            </a>
          </li>
        ))}
      </ul>
      {results.length > 50 ? <p className="india-results-foot">Showing the first 50 matches. Refine the name to narrow the atlas.</p> : null}
    </section>
  );
}

function TaglineReveal() {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const words = Array.from(node.querySelectorAll<HTMLElement>("[data-tagline-word]"));
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add("is-visible");
      }),
      { threshold: 0.45 },
    );
    words.forEach((word) => observer.observe(word));
    return () => observer.disconnect();
  }, []);
  return (
    <section className="india-tagline" aria-label="Atlas principle">
      <p ref={ref}>
        {TAGLINE_WORDS.map((word, index) => (
          <span key={`${word}-${index}`} data-tagline-word style={{ transitionDelay: `${index * 36}ms` }}>
            {word}{index === TAGLINE_WORDS.length - 1 ? "" : " "}
          </span>
        ))}
      </p>
    </section>
  );
}

function DomainGrid({
  domains,
  activeDomain,
  state,
  error,
  onChoose,
  onRetry,
}: {
  domains: IndiaDomain[];
  activeDomain: string | null;
  state: LoadState;
  error: string | null;
  onChoose: (domain: IndiaDomain) => void;
  onRetry: () => void;
}) {
  if (state === "loading" && !domains.length) {
    return (
      <div className="india-domain-loading" role="status" aria-label="Loading domains…">
        {Array.from({ length: 6 }, (_, index) => <span className="india-skeleton-block" key={index} />)}
      </div>
    );
  }
  if (state === "error" && !domains.length) {
    return (
      <div className="india-state india-state-panel" role="alert">
        <span className="india-state-mark">!</span>
        <div>
          <strong>Domain browse is unavailable</strong>
          <p>{error || "The India domains endpoint did not respond."}</p>
          <button className="india-button secondary" type="button" onClick={onRetry}>Retry domains</button>
        </div>
      </div>
    );
  }
  if (!domains.length) {
    return (
      <div className="india-state india-state-panel">
        <span className="india-state-mark">12</span>
        <div>
          <strong>Domain browse is empty</strong>
          <p>The India domains endpoint returned no records. Search remains available while the registry is connected.</p>
        </div>
      </div>
    );
  }
  return (
    <div className="india-domain-grid">
      {domains.map((domain, index) => (
        <button
          className={`india-domain-card ${activeDomain === domain.id ? "active" : ""}`}
          type="button"
          key={domain.id}
          onClick={() => onChoose(domain)}
        >
          <span className="india-domain-number">{String(index + 1).padStart(2, "0")}</span>
          <span className="india-domain-copy">
            <strong>{domain.name}</strong>
            <span>{domain.description || "Open this domain to search its mapped capability records."}</span>
          </span>
          <span className="india-domain-foot">
            <span>{domain.recordCount === null ? "Count not recorded" : `${formatCount(domain.recordCount)} records`}</span>
            {domain.status ? <span className={`india-status tiny ${statusTone(domain.status)}`}>{displayStatus(domain.status)}</span> : null}
          </span>
        </button>
      ))}
      {state === "error" ? <p className="india-inline-warning" role="status">Some domain data could not refresh. <button type="button" onClick={onRetry}>Retry</button></p> : null}
    </div>
  );
}

function DiscoveryList({
  items,
  state,
  error,
  onOpen,
  onSearch,
  onRetry,
}: {
  items: IndiaDiscoverResult[];
  state: LoadState;
  error: string | null;
  onOpen: (id: string) => void;
  onSearch: (query: string) => void;
  onRetry: () => void;
}) {
  if (state === "loading" && !items.length) {
    return <div className="india-discovery-loading" role="status" aria-label="Loading discovery examples…">{Array.from({ length: 3 }, (_, index) => <span className="india-skeleton-block" key={index} />)}</div>;
  }
  if (state === "error" && !items.length) {
    return (
      <div className="india-state india-state-panel" role="alert">
        <span className="india-state-mark">!</span>
        <div>
          <strong>Discovery is unavailable</strong>
          <p>{error || "The India discovery endpoint did not respond."}</p>
          <button className="india-button secondary" type="button" onClick={onRetry}>Retry discovery</button>
        </div>
      </div>
    );
  }
  return (
    <div className="india-discovery-layout">
      <div className="india-discovery-list">
        {items.length ? items.slice(0, 6).map((item) => (
          <a className="india-discovery-card" href={recordHref(item.record.id)} key={item.record.id} onClick={(event) => interceptRecordLink(event, () => onOpen(item.record.id))}>
            <span className="india-discovery-rule" aria-hidden="true" />
            <span className="india-discovery-copy">
              <strong>{item.record.displayName}</strong>
              <span>{item.reason || firstSentence(item.record.explanation)}</span>
            </span>
            <span className="india-discovery-status">
              <span className={`india-status tiny ${statusTone(item.record.indiaStatus)}`}>{displayStatus(item.record.indiaStatus)}</span>
              <span className={`india-epistemic-chip ${epistemicTone(item.record.statusEpistemicClass)}`}>{displayEpistemicClass(item.record.statusEpistemicClass)}</span>
            </span>
          </a>
        )) : (
          <div className="india-empty-discovery">
            <strong>Discovery examples</strong>
            <p>Start with a concrete object and follow its dependencies into the industrial backbone.</p>
            <div className="india-prompt-list">
              {DISCOVERY_PROMPTS.map((prompt) => (
                <button type="button" key={prompt.query} onClick={() => onSearch(prompt.query)}>{prompt.label} <span aria-hidden="true">↗</span></button>
              ))}
            </div>
          </div>
        )}
      </div>
      <aside className="india-discovery-note">
        <div className="india-section-kicker">How to read this atlas</div>
        <p>India status is a broad prior, not a factory directory, qualified-supply claim, or production promise.</p>
        <p>Open any result to see what feeds it, what it enables, and which gaps remain explicit.</p>
      </aside>
    </div>
  );
}

function SummaryStrip({ summary, state }: { summary: IndiaSummary | null; state: LoadState }) {
  const statusEntries = Object.entries(summary?.directStatusCounts ?? summary?.statusCounts ?? {}).slice(0, 3);
  if (state === "loading" && !summary) {
    return <div className="india-summary-strip india-summary-loading" role="status" aria-label="Loading atlas coverage…">{Array.from({ length: 4 }, (_, index) => <span className="india-skeleton-block" key={index} />)}</div>;
  }
  return (
    <div className="india-summary-strip" aria-label="Atlas coverage">
      <div><strong>{formatCount(summary?.recordCount)}</strong><span>mapped records</span></div>
      <div><strong>{formatCount(summary?.directRecordCount)}</strong><span>direct records</span></div>
      <div><strong>{formatCount(summary?.domainCount)}</strong><span>industrial domains</span></div>
      <div><strong>{summary?.snapshot || "Not versioned"}</strong><span>registry snapshot</span></div>
      {statusEntries.length ? (
        <div className="india-summary-statuses">
          {statusEntries.map(([status, count]) => <span key={status}>{displayStatus(status)} · {formatCount(count)}</span>)}
        </div>
      ) : null}
    </div>
  );
}

function NotFoundPage({ onHome }: { onHome: () => void }) {
  return (
    <section className="india-not-found" aria-labelledby="india-not-found-title">
      <div className="india-section-kicker">FORGE INDIA / 404</div>
      <h1 id="india-not-found-title" tabIndex={-1}>This atlas path is not mapped.</h1>
      <p>The record or view you requested does not exist in this interface. Return to the atlas and start with an object.</p>
      <button className="india-button primary" type="button" onClick={onHome}>Return to the atlas</button>
    </section>
  );
}

function AtlasFooter() {
  return (
    <footer className="india-footer">
      <span>FORGE WORLD · India atlas</span>
      <span>Capability records are evidence backed and explicitly incomplete.</span>
      <nav aria-label="Atlas documentation">
        <a href="/docs/DATA_SOURCES.md">Data sources</a>
        <a href="/docs/DATA_RIGHTS.md">Data rights</a>
        <a href="/docs/FORGE_INDIA_V1_KNOWN_LIMITATIONS.md">Known limitations</a>
      </nav>
    </footer>
  );
}

export default function IndiaApp() {
  const [route, setRoute] = useState<Route>(() => readRoute());
  const [summary, setSummary] = useState<IndiaSummary | null>(null);
  const [domains, setDomains] = useState<IndiaDomain[]>([]);
  const [discover, setDiscover] = useState<IndiaDiscoverResult[]>([]);
  const [summaryState, setSummaryState] = useState<LoadState>("loading");
  const [domainsState, setDomainsState] = useState<LoadState>("loading");
  const [discoverState, setDiscoverState] = useState<LoadState>("loading");
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [domainsError, setDomainsError] = useState<string | null>(null);
  const [discoverError, setDiscoverError] = useState<string | null>(null);
  const [bootstrapRetry, setBootstrapRetry] = useState(0);
  const [query, setQuery] = useState(() => readRoute().query);
  const deferredQuery = useDeferredValue(query);
  const [searchResults, setSearchResults] = useState<IndiaSearchResult[]>([]);
  const [searchState, setSearchState] = useState<LoadState>("idle");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchRetry, setSearchRetry] = useState(0);
  const [selectedRecord, setSelectedRecord] = useState<IndiaRecord | null>(null);
  const [recordState, setRecordState] = useState<LoadState>("idle");
  const [recordError, setRecordError] = useState<string | null>(null);
  const [recordRetry, setRecordRetry] = useState(0);
  const [activeDomain, setActiveDomain] = useState<string | null>(() => readRoute().domain);
  const bootstrapRequest = useRef<AbortController | null>(null);
  const recordRequest = useRef<AbortController | null>(null);
  const detailPushed = useRef(false);

  const navigate = useCallback((next: Route, replace = false) => {
    const href = routeHref(next);
    if (replace) window.history.replaceState({ forgeIndia: true }, "", href);
    else window.history.pushState({ forgeIndia: true }, "", href);
    setRoute(next);
  }, []);

  useEffect(() => {
    window.history.replaceState({ ...window.history.state, forgeIndia: true }, "", window.location.href);
    const onPopState = () => {
      detailPushed.current = false;
      setRoute(readRoute());
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    setQuery(route.query);
    setActiveDomain(route.domain);
  }, [route.query, route.domain]);

  const loadBootstrap = useCallback(() => {
    bootstrapRequest.current?.abort();
    const controller = new AbortController();
    bootstrapRequest.current = controller;
    setSummaryState("loading");
    setDomainsState("loading");
    setDiscoverState("loading");
    setSummaryError(null);
    setDomainsError(null);
    setDiscoverError(null);
    void Promise.allSettled([
      fetchIndiaSummary(controller.signal),
      fetchIndiaDomains(controller.signal),
      fetchIndiaDiscover(controller.signal),
    ]).then(([summaryResult, domainsResult, discoverResult]) => {
      if (controller.signal.aborted) return;
      if (summaryResult.status === "fulfilled") {
        setSummary(summaryResult.value);
        setSummaryState("ready");
      } else {
        setSummaryState("error");
        setSummaryError(errorMessage(summaryResult.reason, "The summary endpoint did not respond."));
      }
      if (domainsResult.status === "fulfilled") {
        setDomains(domainsResult.value);
        setDomainsState("ready");
      } else {
        setDomainsState("error");
        setDomainsError(errorMessage(domainsResult.reason, "The domains endpoint did not respond."));
      }
      if (discoverResult.status === "fulfilled") {
        setDiscover(discoverResult.value);
        setDiscoverState("ready");
      } else {
        setDiscoverState("error");
        setDiscoverError(errorMessage(discoverResult.reason, "The discovery endpoint did not respond."));
      }
    });
    return controller;
  }, []);

  useEffect(() => {
    const controller = loadBootstrap();
    return () => controller.abort();
  }, [loadBootstrap, bootstrapRetry]);

  const searchDomain = route.kind === "home" ? route.domain : null;
  useEffect(() => {
    const term = deferredQuery.trim();
    if (!term && !searchDomain) {
      setSearchResults([]);
      setSearchState("idle");
      setSearchError(null);
      return;
    }
    if (term.length === 1) {
      setSearchResults([]);
      setSearchState("ready");
      setSearchError(null);
      return;
    }
    const controller = new AbortController();
    setSearchState("loading");
    setSearchError(null);
    const timer = window.setTimeout(() => {
      void searchIndia(term, controller.signal, { domain: searchDomain, limit: 50 }).then((results) => {
        if (controller.signal.aborted) return;
        startTransition(() => {
          setSearchResults(results);
          setSearchState("ready");
        });
      }).catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSearchState("error");
        setSearchError(errorMessage(error, "The search request failed."));
      });
    }, 160);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [deferredQuery, searchDomain, searchRetry]);

  useEffect(() => {
    recordRequest.current?.abort();
    const recordId = route.kind === "record" ? route.recordId : null;
    if (!recordId) {
      setSelectedRecord(null);
      setRecordState("idle");
      setRecordError(null);
      return;
    }
    const controller = new AbortController();
    recordRequest.current = controller;
    setSelectedRecord(null);
    setRecordState("loading");
    setRecordError(null);
    void fetchIndiaRecord(recordId, controller.signal).then((record) => {
      if (controller.signal.aborted) return;
      setSelectedRecord(record);
      setRecordState("ready");
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return;
      setRecordState("error");
      setRecordError(errorMessage(error, "The record request failed."));
    });
    return () => controller.abort();
  }, [route.kind, route.recordId, recordRetry]);

  useEffect(() => {
    const id = route.kind === "record" ? "india-detail-heading" : route.kind === "home" ? "india-title" : "india-not-found-title";
    const node = document.getElementById(id);
    if (!node) return;
    const frame = window.requestAnimationFrame(() => (node as HTMLElement).focus());
    return () => window.cancelAnimationFrame(frame);
  }, [route.kind, route.recordId]);

  useEffect(() => {
    const isRecord = route.kind === "record";
    const isNotFound = route.kind === "not-found";
    const name = isRecord ? selectedRecord?.displayName || route.recordId || "Record" : isNotFound ? "Page not found" : "FORGE INDIA — what can India build?";
    const description = isRecord
      ? selectedRecord?.explanation || "Inspect an evidence-backed FORGE INDIA capability record and its industrial chain."
      : isNotFound
        ? "The requested FORGE INDIA atlas path is not mapped."
        : "Search an evidence-backed field guide to products, capabilities, dependencies, and gaps in India's industrial system.";
    document.title = isRecord || isNotFound ? `${name} · FORGE INDIA` : name;
    upsertMeta('meta[name="description"]', "name", description);
    upsertMeta('meta[property="og:title"]', "property", document.title);
    upsertMeta('meta[property="og:description"]', "property", description);
    upsertMeta('meta[property="og:type"]', "property", "website");
    upsertMeta('meta[name="twitter:card"]', "name", "summary");
    let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.rel = "canonical";
      document.head.appendChild(canonical);
    }
    canonical.href = `${window.location.origin}${route.kind === "record" ? routeHref({ ...route, query: "", domain: null }) : "/"}`;
  }, [route, selectedRecord]);

  const onQueryChange = useCallback((value: string) => {
    setQuery(value);
    if (route.kind === "not-found") return;
    navigate({ ...route, query: value }, true);
  }, [navigate, route]);

  const openRecord = useCallback((id: string) => {
    if (!id) return;
    detailPushed.current = true;
    navigate({ kind: "record", recordId: id, query: "", domain: null });
  }, [navigate]);

  const openLink = useCallback((link: IndiaLink) => {
    if (link.id) openRecord(link.id);
  }, [openRecord]);

  const backToAtlas = useCallback(() => {
    if (detailPushed.current) {
      detailPushed.current = false;
      window.history.back();
      return;
    }
    navigate({ kind: "home", recordId: null, query: "", domain: null }, true);
  }, [navigate]);

  const chooseDomain = useCallback((domain: IndiaDomain) => {
    detailPushed.current = false;
    navigate({ kind: "home", recordId: null, query: "", domain: domain.id });
  }, [navigate]);

  const performSearch = useCallback(() => {
    if (!query.trim() && !activeDomain) return;
    detailPushed.current = false;
    navigate({ kind: "home", recordId: null, query: query.trim(), domain: activeDomain });
  }, [activeDomain, navigate, query]);

  const searchExamples = useCallback((term: string) => {
    detailPushed.current = false;
    navigate({ kind: "home", recordId: null, query: term, domain: null });
  }, [navigate]);

  const isDetail = route.kind === "record";
  const activeDomainName = domains.find((domain) => domain.id === activeDomain)?.name || null;
  const bootstrapErrors = [summaryError, domainsError, discoverError].filter(Boolean) as string[];
  const allBootstrapFailed = summaryState === "error" && domainsState === "error" && discoverState === "error";

  return (
    <div className="india-app">
      <a className="india-skip-link" href="#india-main">Skip to atlas</a>
      <header className="india-topbar">
        <div className="india-topbar-inner">
          <a className="india-brand" href="/" aria-label="FORGE India home" onClick={(event) => { event.preventDefault(); backToAtlas(); }}>
            <span className="india-brand-mark" aria-hidden="true">F</span>
            <span><strong>FORGE INDIA</strong><small>industrial field guide</small></span>
          </a>
          <nav aria-label="Atlas navigation">
            <a href="#domains" onClick={(event) => { if (isDetail) { event.preventDefault(); navigate({ kind: "home", recordId: null, query: "", domain: null }); } }}>12 domains</a>
            <a href="#discover" onClick={(event) => { if (isDetail) { event.preventDefault(); navigate({ kind: "home", recordId: null, query: "", domain: null }); } }}>Discovery</a>
          </nav>
          <span className="india-topbar-note">V1 · evidence stays visible</span>
        </div>
      </header>

      <main id="india-main" className="india-main">
        {route.kind === "not-found" ? <NotFoundPage onHome={() => navigate({ kind: "home", recordId: null, query: "", domain: null }, true)} /> : null}
        {!isDetail && route.kind === "home" ? (
          <>
            <section className="india-hero" aria-labelledby="india-title">
              <div className="india-hero-copy">
                <div className="india-eyebrow">FORGE INDIA / WHAT CAN INDIA BUILD?</div>
                <h1 id="india-title" tabIndex={-1}>Start with the object.<br /><span>See the industrial path.</span></h1>
                <p className="india-hero-lede">A readable atlas of products, capabilities, dependencies, and gaps. Search one thing, then follow the chain into the systems that make it possible.</p>
                <SearchBox value={query} onChange={onQueryChange} onSubmit={performSearch} />
                <SearchResults query={query} scopeLabel={activeDomainName} state={searchState} error={searchError} results={searchResults} onOpen={openRecord} onRetry={() => setSearchRetry((value) => value + 1)} />
              </div>
              <aside className="india-hero-note" aria-label="Atlas scope">
                <div className="india-scope-line"><span>01</span><p>Search a real object</p></div>
                <div className="india-scope-line"><span>02</span><p>Read its India status and epistemic class</p></div>
                <div className="india-scope-line"><span>03</span><p>Trace dependencies and next actions</p></div>
                <div className="india-scope-rule" />
                <p className="india-scope-foot">India status is a broad prior, not qualified supply. Unknown remains visible.</p>
              </aside>
            </section>

            <SummaryStrip summary={summary} state={summaryState} />

            {bootstrapErrors.length ? (
              <div className={`india-connection-note ${allBootstrapFailed ? "error" : ""}`} role={allBootstrapFailed ? "alert" : "status"}>
                <span>{allBootstrapFailed ? "Atlas connection" : "Partial atlas connection"}</span>
                <p>{bootstrapErrors.join(" ")}</p>
                <button type="button" onClick={() => setBootstrapRetry((value) => value + 1)}>Retry atlas data</button>
              </div>
            ) : null}

            <TaglineReveal />

            <section id="domains" className="india-section" aria-labelledby="domains-title">
              <div className="india-section-heading">
                <div>
                  <div className="india-section-kicker">Browse by field</div>
                  <h2 id="domains-title">Twelve domains, one connected atlas</h2>
                </div>
                <p>Choose a field to filter the mapped records. The same primitives can reappear across sectors.</p>
              </div>
              <DomainGrid domains={domains} activeDomain={activeDomain} state={domainsState} error={domainsError} onChoose={chooseDomain} onRetry={() => setBootstrapRetry((value) => value + 1)} />
            </section>

            <section id="discover" className="india-section india-discovery-section" aria-labelledby="discover-title">
              <div className="india-section-heading">
                <div>
                  <div className="india-section-kicker">Find the leverage</div>
                  <h2 id="discover-title">Start with a build question</h2>
                </div>
                <p>Discovery is a doorway into records, not a scorecard.</p>
              </div>
              <DiscoveryList items={discover} state={discoverState} error={discoverError} onOpen={openRecord} onSearch={searchExamples} onRetry={() => setBootstrapRetry((value) => value + 1)} />
            </section>
          </>
        ) : null}

        {isDetail ? (
          <section className="india-detail-stage" aria-labelledby="india-detail-heading">
            <div className="india-detail-toolbar">
              <div>
                <div className="india-eyebrow">FORGE INDIA / RECORD VIEW</div>
                <h1 id="india-detail-heading" tabIndex={-1}>Trace one capability</h1>
              </div>
              <SearchBox value={query} onChange={onQueryChange} onSubmit={performSearch} compact />
            </div>
            <SearchResults query={query} scopeLabel={null} state={searchState} error={searchError} results={searchResults} onOpen={openRecord} onRetry={() => setSearchRetry((value) => value + 1)} />
            <IndiaRecordView
              record={selectedRecord}
              loading={recordState === "loading"}
              error={recordError}
              onBack={backToAtlas}
              onRetry={() => setRecordRetry((value) => value + 1)}
              onNavigate={openLink}
            />
          </section>
        ) : null}
      </main>
      <AtlasFooter />
    </div>
  );
}
