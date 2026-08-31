import { useState, type MouseEvent as ReactMouseEvent } from "react";
import IndiaChainRibbon from "./IndiaChainRibbon";
import { displayEpistemicClass, displayStatus, epistemicTone, statusTone } from "./india-ui";
import type {
  IndiaDependencyGroupKey,
  IndiaLink,
  IndiaRecord,
} from "./india-types";

interface IndiaRecordViewProps {
  record: IndiaRecord | null;
  loading: boolean;
  error: string | null;
  onBack: () => void;
  onRetry: () => void;
  onNavigate: (link: IndiaLink) => void;
}

const DEPENDENCY_LABELS: Record<IndiaDependencyGroupKey, string> = {
  systems: "Major systems",
  materials: "Materials",
  processes: "Processes",
  equipment: "Equipment",
  capabilities: "Capabilities",
};

function MissingNote({ children }: { children: string }) {
  return <p className="india-missing-note">{children}</p>;
}

function recordHref(id: string): string {
  return `/india/records/${encodeURIComponent(id)}`;
}

function interceptRecordLink(event: ReactMouseEvent<HTMLAnchorElement>, onNavigate: () => void) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  onNavigate();
}

function LinkCluster({
  title,
  links,
  onNavigate,
}: {
  title: string;
  links: IndiaLink[];
  onNavigate: (link: IndiaLink) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const visibleLinks = expanded ? links : links.slice(0, 8);
  return (
    <section className="india-link-cluster">
      <h3>{title}</h3>
      {links.length ? (
        <div className="india-link-list">
          {visibleLinks.map((link, index) => link.id ? (
            <a
              className="india-related-link"
              href={recordHref(link.id)}
              key={`${link.id}-${index}`}
              onClick={(event) => interceptRecordLink(event, () => onNavigate(link))}
              title={link.note || link.label}
            >
              <span>{link.label}</span>
              {link.kind ? <small>{link.kind}</small> : null}
              {link.note ? <em>{link.note}</em> : null}
            </a>
          ) : (
            <span className="india-related-link unavailable" key={`${link.label}-${index}`} title={link.note || link.label}>
              <span>{link.label}</span>
              {link.kind ? <small>{link.kind}</small> : null}
              {link.note ? <em>{link.note}</em> : null}
            </span>
          ))}
          {links.length > visibleLinks.length ? <button className="india-disclosure-button" type="button" onClick={() => setExpanded(true)}>Show {links.length - visibleLinks.length} more connections</button> : null}
          {expanded && links.length > 8 ? <button className="india-disclosure-button" type="button" onClick={() => setExpanded(false)}>Show fewer connections</button> : null}
        </div>
      ) : (
        <MissingNote>Nothing is mapped in this direction yet.</MissingNote>
      )}
    </section>
  );
}

function RecordSkeleton() {
  return (
    <div className="india-record-skeleton" aria-label="Loading record" role="status">
      <span className="india-skeleton-line wide" />
      <span className="india-skeleton-line medium" />
      <div className="india-skeleton-grid">
        <span className="india-skeleton-block" />
        <span className="india-skeleton-block" />
      </div>
      <span className="india-skeleton-line wide" />
      <span className="india-skeleton-line wide" />
    </div>
  );
}

export default function IndiaRecordView({
  record,
  loading,
  error,
  onBack,
  onRetry,
  onNavigate,
}: IndiaRecordViewProps) {
  if (loading && !record) return <RecordSkeleton />;

  if (error && !record) {
    return (
      <section className="india-state india-state-error" role="alert">
        <span className="india-state-mark">!</span>
        <div>
          <h2>This record could not be opened</h2>
          <p>{error}</p>
          <button className="india-button primary" type="button" onClick={onRetry}>Retry record</button>
          <button className="india-button secondary" type="button" onClick={onBack}>
            Back to the atlas
          </button>
        </div>
      </section>
    );
  }

  if (!record) {
    return (
      <section className="india-state">
        <span className="india-state-mark">↳</span>
        <div>
          <h2>Choose a capability to inspect</h2>
          <p>Search the atlas or choose a domain to open an auditable record.</p>
        </div>
      </section>
    );
  }

  const dependencyEntries = Object.entries(record.dependencies) as [
    IndiaDependencyGroupKey,
    IndiaLink[],
  ][];

  return (
    <article className="india-record" aria-labelledby="india-record-title">
      <button className="india-back-button" type="button" onClick={onBack}>
        <span aria-hidden="true">←</span> Back to browse
      </button>

      <header className="india-record-header">
        <div className="india-record-kicker">
          {record.domainName || "India atlas"}
          <span aria-hidden="true">·</span>
          {record.category}
        </div>
        <h1 id="india-record-title">{record.displayName}</h1>
        <div className="india-record-meta">
          <span>{record.kind}</span>
          <span aria-hidden="true">·</span>
          <span>{record.id}</span>
        </div>
        <div className="india-status-row">
          <span className={`india-status ${statusTone(record.indiaStatus)}`}>
            India status: {displayStatus(record.indiaStatus)}
          </span>
          <span className={`india-epistemic-chip ${epistemicTone(record.statusEpistemicClass)}`}>
            {displayEpistemicClass(record.statusEpistemicClass)}
          </span>
          {record.isReferenceOnly ? <span className="india-reference-chip">Reference layer</span> : null}
          {record.aliases.length ? (
            <span className="india-aliases">Also known as {record.aliases.join(", ")}</span>
          ) : null}
        </div>
      </header>

      <IndiaChainRibbon record={record} onNavigate={onNavigate} />

      <div className="india-record-intro">
        <section>
          <div className="india-section-kicker">What it is</div>
          <p className="india-record-lede">{record.explanation}</p>
        </section>
        <section>
          <div className="india-section-kicker">Why it matters</div>
          <p className="india-record-lede">{record.use}</p>
        </section>
      </div>

      <section className="india-basis-card">
        <div>
          <div className="india-section-kicker">India status and basis</div>
          <strong>{displayStatus(record.indiaStatus)}</strong>
        </div>
        <div>
          <p>{record.statusBasis}</p>
          <p className="india-basis-note">This is a broad prior about the mapped record, not proof of qualified supply, effective capacity, or current availability.</p>
          {record.sourceSpec ? <p className="india-source-spec"><span>Source specification:</span> {record.sourceSpec}</p> : null}
        </div>
      </section>

      <section className="india-detail-section">
        <div className="india-section-heading">
          <div>
            <div className="india-section-kicker">Inputs to plan for</div>
            <h2>Grouped dependencies</h2>
          </div>
          <span className="india-section-aside">
            {dependencyEntries.reduce((total, [, links]) => total + links.length, 0)} mapped dependencies
          </span>
        </div>
        <div className="india-dependency-grid">
          {dependencyEntries.map(([key, links], index) => (
            <details className="india-dependency-card" key={key} open={index === 0}>
              <summary><span>{DEPENDENCY_LABELS[key]}</span><small>{links.length} mapped</small></summary>
              {links.length ? (
                <div className="india-compact-link-list">
                  {links.map((link, index) => link.id ? (
                    <a
                      href={recordHref(link.id)}
                      key={`${link.id}-${index}`}
                      onClick={(event) => interceptRecordLink(event, () => onNavigate(link))}
                    >
                      <span>{link.label}</span>
                      {link.kind ? <small>{link.kind}</small> : null}
                    </a>
                  ) : (
                    <span className="india-compact-link unavailable" key={`${link.label}-${index}`}>
                      <span>{link.label}</span>
                      {link.kind ? <small>{link.kind}</small> : null}
                    </span>
                  ))}
                </div>
              ) : (
                <MissingNote>Not mapped yet.</MissingNote>
              )}
            </details>
          ))}
        </div>
      </section>

      <div className="india-gap-grid">
        <section className="india-detail-section india-gap-card">
          <div className="india-section-kicker">Gaps to close</div>
          <h2>Capability gaps</h2>
          {record.gaps.length ? (
            <ul className="india-bullet-list">
              {record.gaps.map((gap, index) => <li key={`${gap}-${index}`}>{gap}</li>)}
            </ul>
          ) : (
            <MissingNote>No specific gap is recorded yet.</MissingNote>
          )}
        </section>
        <section className="india-detail-section india-import-card">
          <div className="india-section-kicker">Imports and exposure</div>
          <h2>Import notes</h2>
          {record.importNotes.length ? (
            <ul className="india-bullet-list">
              {record.importNotes.map((note, index) => <li key={`${note}-${index}`}>{note}</li>)}
            </ul>
          ) : (
            <MissingNote>No import note is recorded yet.</MissingNote>
          )}
        </section>
      </div>

      <section className="india-detail-section india-ladder-section">
        <div className="india-section-heading">
          <div>
            <div className="india-section-kicker">Make it here</div>
            <h2>First order making ladder</h2>
          </div>
          <span className="india-section-aside">Actions, not a capacity claim</span>
        </div>
        {record.makingLadder.length ? (
          <ol className="india-ladder">
            {record.makingLadder.map((step, index) => (
              <li key={`${step.step}-${index}`}>
                <span className="india-ladder-index">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{step.action}</strong>
                  <span>{step.note || step.step}</span>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <MissingNote>A making ladder is not recorded for this item yet.</MissingNote>
        )}
      </section>

      <div className="india-link-grid">
        <LinkCluster title="Upstream" links={record.upstream} onNavigate={onNavigate} />
        <LinkCluster title="Downstream" links={record.downstream} onNavigate={onNavigate} />
        <LinkCluster title="Unlocks" links={record.unlocks} onNavigate={onNavigate} />
        <LinkCluster title="Related records" links={record.related} onNavigate={onNavigate} />
      </div>

      {loading ? <p className="india-inline-loading" role="status">Refreshing this record…</p> : null}
    </article>
  );
}
