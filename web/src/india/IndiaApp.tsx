import {
  FormEvent,
  useCallback,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
  startTransition,
} from "react";
import IndiaRecordView from "./IndiaRecordView";
import {
  fetchIndiaDiscover,
  fetchIndiaDomains,
  fetchIndiaRecord,
  fetchIndiaSummary,
  searchIndia,
} from "./india-api";
import { displayStatus, firstSentence, formatCount, statusTone } from "./india-ui";
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
  state,
  error,
  results,
  onOpen,
}: {
  query: string;
  state: LoadState;
  error: string | null;
  results: IndiaSearchResult[];
  onOpen: (id: string) => void;
}) {
  const term = query.trim();
  if (!term) return null;
  if (term.length < 2) {
    return <p className="india-search-message">Type at least two characters to search the atlas.</p>;
  }
  if (state === "loading") {
    return (
      <div className="india-result-skeleton" role="status" aria-label="Searching">
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
        </div>
      </div>
    );
  }
  if (!results.length) {
    return (
      <div className="india-empty-search">
        <strong>No mapped record matches “{term}”.</strong>
        <span>Try a broader object name, or browse a domain below.</span>
      </div>
    );
  }
  return (
    <section className="india-results" aria-live="polite" aria-label="Search results">
      <div className="india-results-head">
        <span>{results.length} mapped result{results.length === 1 ? "" : "s"}</span>
        <span>Open a record to inspect its chain</span>
      </div>
      <ul>
        {results.slice(0, 32).map((result) => (
          <li key={result.record.id}>
            <button type="button" onClick={() => onOpen(result.record.id)}>
              <span className={`india-status tiny ${statusTone(result.record.indiaStatus)}`}>
                {displayStatus(result.record.indiaStatus)}
              </span>
              <strong>{result.record.canonicalName}</strong>
              <span>{firstSentence(result.record.explanation)}</span>
              <small>{result.record.kind} · {result.record.category}</small>
            </button>
          </li>
        ))}
      </ul>
      {results.length > 32 ? <p className="india-results-foot">Showing the first 32 matches. Refine the name to narrow the atlas.</p> : null}
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
  onChoose,
}: {
  domains: IndiaDomain[];
  activeDomain: string | null;
  onChoose: (domain: IndiaDomain) => void;
}) {
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
    </div>
  );
}

function DiscoveryList({
  items,
  onOpen,
  onSearch,
}: {
  items: IndiaDiscoverResult[];
  onOpen: (id: string) => void;
  onSearch: (query: string) => void;
}) {
  return (
    <div className="india-discovery-layout">
      <div className="india-discovery-list">
        {items.length ? items.slice(0, 6).map((item) => (
          <button className="india-discovery-card" type="button" key={item.record.id} onClick={() => onOpen(item.record.id)}>
            <span className="india-discovery-rule" aria-hidden="true" />
            <span className="india-discovery-copy">
              <strong>{item.record.canonicalName}</strong>
              <span>{item.reason || firstSentence(item.record.explanation)}</span>
            </span>
            <span className={`india-status tiny ${statusTone(item.record.indiaStatus)}`}>{displayStatus(item.record.indiaStatus)}</span>
          </button>
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
        <p>India status is a broad evidence label, not a factory directory or a promise of qualified supply.</p>
        <p>Open any result to see what feeds it, what it enables, and which gaps remain explicit.</p>
      </aside>
    </div>
  );
}

function SummaryStrip({ summary }: { summary: IndiaSummary | null }) {
  const statusEntries = Object.entries(summary?.statusCounts ?? {}).slice(0, 3);
  return (
    <div className="india-summary-strip" aria-label="Atlas coverage">
      <div><strong>{formatCount(summary?.recordCount)}</strong><span>mapped records</span></div>
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

export default function IndiaApp() {
  const [summary, setSummary] = useState<IndiaSummary | null>(null);
  const [domains, setDomains] = useState<IndiaDomain[]>([]);
  const [discover, setDiscover] = useState<IndiaDiscoverResult[]>([]);
  const [bootstrapState, setBootstrapState] = useState<LoadState>("loading");
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [searchResults, setSearchResults] = useState<IndiaSearchResult[]>([]);
  const [searchState, setSearchState] = useState<LoadState>("idle");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<IndiaRecord | null>(null);
  const [recordState, setRecordState] = useState<LoadState>("idle");
  const [recordError, setRecordError] = useState<string | null>(null);
  const [activeDomain, setActiveDomain] = useState<string | null>(null);
  const recordRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setBootstrapState("loading");
    void Promise.allSettled([
      fetchIndiaSummary(controller.signal),
      fetchIndiaDomains(controller.signal),
      fetchIndiaDiscover(controller.signal),
    ]).then((results) => {
      if (controller.signal.aborted) return;
      const [summaryResult, domainsResult, discoverResult] = results;
      const failures: string[] = [];
      if (summaryResult.status === "fulfilled") setSummary(summaryResult.value);
      else failures.push(summaryResult.reason instanceof Error ? summaryResult.reason.message : "Summary unavailable");
      if (domainsResult.status === "fulfilled") setDomains(domainsResult.value);
      else failures.push(domainsResult.reason instanceof Error ? domainsResult.reason.message : "Domains unavailable");
      if (discoverResult.status === "fulfilled") setDiscover(discoverResult.value);
      else failures.push(discoverResult.reason instanceof Error ? discoverResult.reason.message : "Discovery unavailable");
      if (failures.length === 3) {
        setBootstrapState("error");
        setBootstrapError("The India atlas endpoints did not respond. Start the API and reload this page.");
      } else {
        setBootstrapState("ready");
        setBootstrapError(failures.length ? failures.join(" ") : null);
      }
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const term = deferredQuery.trim();
    if (!term) {
      setSearchResults([]);
      setSearchState("idle");
      setSearchError(null);
      return;
    }
    if (term.length < 2) {
      setSearchResults([]);
      setSearchState("ready");
      return;
    }
    const controller = new AbortController();
    setSearchState("loading");
    setSearchError(null);
    const timer = window.setTimeout(() => {
      void searchIndia(term, controller.signal).then((results) => {
        if (controller.signal.aborted) return;
        startTransition(() => {
          setSearchResults(results);
          setSearchState("ready");
        });
      }).catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSearchState("error");
        setSearchError(error instanceof Error ? error.message : "The search request failed.");
      });
    }, 160);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [deferredQuery]);

  const searchIndex = useMemo(
    () => new Map(searchResults.map((result) => [result.record.id, result])),
    [searchResults],
  );

  const openRecord = useCallback((id: string) => {
    if (!id) return;
    recordRequest.current?.abort();
    const controller = new AbortController();
    recordRequest.current = controller;
    setSelectedId(id);
    setSelectedRecord(searchIndex.get(id)?.record ?? null);
    setRecordState("loading");
    setRecordError(null);
    void fetchIndiaRecord(id, controller.signal).then((record) => {
      if (!controller.signal.aborted) {
        setSelectedRecord(record);
        setRecordState("ready");
      }
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setRecordState("error");
        setRecordError(error instanceof Error ? error.message : "The record request failed.");
      }
    });
  }, [searchIndex]);

  const openLink = useCallback((link: IndiaLink) => {
    if (link.id) openRecord(link.id);
  }, [openRecord]);

  const backToAtlas = useCallback(() => {
    recordRequest.current?.abort();
    setSelectedId(null);
    setSelectedRecord(null);
    setRecordState("idle");
    setRecordError(null);
  }, []);

  const chooseDomain = useCallback((domain: IndiaDomain) => {
    setActiveDomain(domain.id);
    setSelectedId(null);
    setSelectedRecord(null);
    setQuery(domain.name);
  }, []);

  const performSearch = useCallback(() => {
    if (!query.trim()) return;
    setSelectedId(null);
    setSelectedRecord(null);
    setRecordState("idle");
  }, [query]);

  const searchExamples = useCallback((term: string) => {
    setSelectedId(null);
    setSelectedRecord(null);
    setActiveDomain(null);
    setQuery(term);
  }, []);

  const isDetail = Boolean(selectedId);

  return (
    <div className="india-app">
      <a className="india-skip-link" href="#india-main">Skip to atlas</a>
      <header className="india-topbar">
        <div className="india-topbar-inner">
          <a className="india-brand" href="/" aria-label="FORGE India home">
            <span className="india-brand-mark" aria-hidden="true">F</span>
            <span><strong>FORGE INDIA</strong><small>industrial field guide</small></span>
          </a>
          <nav aria-label="Atlas navigation">
            <a href="#domains">12 domains</a>
            <a href="#discover">Discovery</a>
          </nav>
          <span className="india-topbar-note">V1 · evidence stays visible</span>
        </div>
      </header>

      <main id="india-main" className="india-main">
        {!isDetail ? (
          <>
            <section className="india-hero" aria-labelledby="india-title">
              <div className="india-hero-copy">
                <div className="india-eyebrow">FORGE INDIA / WHAT CAN INDIA BUILD?</div>
                <h1 id="india-title">Start with the object.<br /><span>See the industrial path.</span></h1>
                <p className="india-hero-lede">A readable atlas of products, capabilities, dependencies, and gaps. Search one thing, then follow the chain into the systems that make it possible.</p>
                <SearchBox value={query} onChange={setQuery} onSubmit={performSearch} />
                <SearchResults query={query} state={searchState} error={searchError} results={searchResults} onOpen={openRecord} />
              </div>
              <aside className="india-hero-note" aria-label="Atlas scope">
                <div className="india-scope-line"><span>01</span><p>Search a real object</p></div>
                <div className="india-scope-line"><span>02</span><p>Read its India status and basis</p></div>
                <div className="india-scope-line"><span>03</span><p>Trace dependencies and next actions</p></div>
                <div className="india-scope-rule" />
                <p className="india-scope-foot">No directory claims. No silent substitution. Unknown remains visible.</p>
              </aside>
            </section>

            <SummaryStrip summary={summary} />

            {bootstrapError ? (
              <div className={`india-connection-note ${bootstrapState === "error" ? "error" : ""}`} role={bootstrapState === "error" ? "alert" : "status"}>
                <span>{bootstrapState === "error" ? "Atlas connection" : "Partial atlas connection"}</span>
                <p>{bootstrapError}</p>
              </div>
            ) : null}

            <TaglineReveal />

            <section id="domains" className="india-section" aria-labelledby="domains-title">
              <div className="india-section-heading">
                <div>
                  <div className="india-section-kicker">Browse by field</div>
                  <h2 id="domains-title">Twelve domains, one connected atlas</h2>
                </div>
                <p>Choose a field to start a search. The same primitives can reappear across sectors.</p>
              </div>
              {bootstrapState === "loading" && !domains.length ? (
                <div className="india-domain-loading" role="status" aria-label="Loading domains">
                  {Array.from({ length: 6 }, (_, index) => <span className="india-skeleton-block" key={index} />)}
                </div>
              ) : <DomainGrid domains={domains} activeDomain={activeDomain} onChoose={chooseDomain} />}
            </section>

            <section id="discover" className="india-section india-discovery-section" aria-labelledby="discover-title">
              <div className="india-section-heading">
                <div>
                  <div className="india-section-kicker">Find the leverage</div>
                  <h2 id="discover-title">Start with a build question</h2>
                </div>
                <p>Discovery is a doorway into records, not a scorecard.</p>
              </div>
              <DiscoveryList items={discover} onOpen={openRecord} onSearch={searchExamples} />
            </section>

            <footer className="india-footer">
              <span>FORGE WORLD · India atlas</span>
              <span>Capability records are evidence backed and explicitly incomplete.</span>
            </footer>
          </>
        ) : (
          <section className="india-detail-stage" aria-labelledby="india-detail-heading">
            <div className="india-detail-toolbar">
              <div>
                <div className="india-eyebrow">FORGE INDIA / RECORD VIEW</div>
                <h1 id="india-detail-heading">Trace one capability</h1>
              </div>
              <SearchBox value={query} onChange={setQuery} onSubmit={performSearch} compact />
            </div>
            {query.trim() ? <SearchResults query={query} state={searchState} error={searchError} results={searchResults} onOpen={openRecord} /> : null}
            <IndiaRecordView record={selectedRecord} loading={recordState === "loading"} error={recordError} onBack={backToAtlas} onNavigate={openLink} />
          </section>
        )}
      </main>
    </div>
  );
}

