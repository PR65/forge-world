import type { IndiaLink, IndiaRecord } from "./india-types";

interface IndiaChainRibbonProps {
  record: IndiaRecord;
  onNavigate: (link: IndiaLink) => void;
}

interface RibbonNode {
  label: string;
  links: IndiaLink[];
  tone: "upstream" | "current" | "downstream" | "unlock";
}

function RibbonLinks({
  links,
  onNavigate,
}: {
  links: IndiaLink[];
  onNavigate: (link: IndiaLink) => void;
}) {
  if (!links.length) return <span className="india-ribbon-empty">Not mapped yet</span>;
  return (
    <div className="india-ribbon-links">
      {links.slice(0, 4).map((link, index) => (
        <button
          className="india-ribbon-link"
          type="button"
          key={`${link.id ?? link.label}-${index}`}
          onClick={() => onNavigate(link)}
          disabled={!link.id}
          title={link.note || link.label}
        >
          {link.label}
        </button>
      ))}
      {links.length > 4 ? (
        <span className="india-ribbon-more">+{links.length - 4} more</span>
      ) : null}
    </div>
  );
}

export default function IndiaChainRibbon({
  record,
  onNavigate,
}: IndiaChainRibbonProps) {
  const nodes: RibbonNode[] = [
    { label: "Upstream", links: record.upstream, tone: "upstream" },
    {
      label: record.canonicalName,
      links: [],
      tone: "current",
    },
    { label: "Downstream", links: record.downstream, tone: "downstream" },
    { label: "Unlocks", links: record.unlocks, tone: "unlock" },
  ];

  return (
    <section className="india-ribbon" aria-labelledby="india-chain-title">
      <div className="india-section-kicker" id="india-chain-title">
        Capability chain
      </div>
      <div className="india-ribbon-track" role="list" aria-label="Capability chain">
        {nodes.map((node, index) => (
          <div className={`india-ribbon-node ${node.tone}`} role="listitem" key={node.label}>
            <div className="india-ribbon-node-head">
              <span>{node.label}</span>
              {node.tone === "current" ? <b aria-label="Current record">●</b> : null}
            </div>
            {node.tone === "current" ? (
              <strong>{record.kind}</strong>
            ) : (
              <RibbonLinks links={node.links} onNavigate={onNavigate} />
            )}
            {index < nodes.length - 1 ? <span className="india-ribbon-arrow" aria-hidden="true">→</span> : null}
          </div>
        ))}
      </div>
      <p className="india-ribbon-note">
        Follow the physical path from what feeds a capability to what it makes possible.
      </p>
    </section>
  );
}

