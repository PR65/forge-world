import { useEffect, useId, useMemo, useState } from "react";
import type { FormEvent } from "react";
import "./operational-panels.css";

/**
 * These are intentionally small shell contracts.  The API adapter can map a
 * richer registry/run response into them without coupling this UI to the
 * solver's internal types.
 */
export type ForgeStatus = string;

export type ForgeEpistemic =
  | "MEASURED"
  | "REPORTED"
  | "DERIVED"
  | "ESTIMATED"
  | "MODELLED"
  | "ASSUMPTION"
  | "SCENARIO"
  | "UNKNOWN"
  | "CONFLICTED"
  | (string & {});

export interface ForgeTarget {
  title: string;
  description?: string | null;
  quantity?: string | number | null;
  unit?: string | null;
  geography?: string | null;
  deadline?: string | null;
  constraints?: string[];
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface ForgeConclusion {
  verdict?: string | null;
  summary?: string | null;
  rationale?: string | null;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface ForgeConfidence {
  value?: number | null;
  valueLabel?: string | null;
  basis?: string | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface ForgeItem {
  id: string;
  title: string;
  summary?: string | null;
  detail?: string | null;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  owner?: string | null;
  metric?: string | null;
  evidenceIds?: string[];
  note?: string | null;
}

export interface ForgeAlternative extends ForgeItem {
  tradeoffs?: string[];
  dependencyChanges?: string[];
}

export interface ForgeDependency extends ForgeItem {
  relation?: string | null;
  upstream?: string | null;
  impact?: string | null;
}

export interface ForgeAction extends ForgeItem {
  kind?: string | null;
  due?: string | null;
  rationale?: string | null;
  approvalRequired?: boolean;
  dependencies?: string[];
}

export interface CaseOverviewData {
  caseId?: string | null;
  target?: ForgeTarget | null;
  conclusion?: ForgeConclusion | null;
  confidence?: ForgeConfidence | null;
  bottlenecks?: ForgeItem[];
  unknowns?: ForgeItem[];
  alternatives?: ForgeAlternative[];
  dependencies?: ForgeDependency[];
  actions?: ForgeAction[];
}

export interface CaseOverviewProps {
  data?: CaseOverviewData | null;
  onAction?: (action: ForgeAction) => void;
  onAlternative?: (alternative: ForgeAlternative) => void;
  onDependency?: (dependency: ForgeDependency) => void;
  className?: string;
}

export type MakeBuyKind = string;

export interface MakeBuyDecision {
  id: string;
  item: string;
  decision: MakeBuyKind;
  rationale?: string | null;
  supplier?: string | null;
  leadTime?: string | null;
  qualification?: string | null;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface ProcessStep {
  id: string;
  title: string;
  detail?: string | null;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface ProcessRoute {
  id: string;
  title: string;
  summary?: string | null;
  steps?: ProcessStep[];
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface MachineryNeed {
  id: string;
  title: string;
  purpose?: string | null;
  requirement?: string | null;
  route?: string | null;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface QualificationGate {
  id: string;
  title: string;
  criterion?: string | null;
  owner?: string | null;
  evidenceIds?: string[];
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
}

export interface WorkPackage {
  id: string;
  title: string;
  summary?: string | null;
  sequence?: string | null;
  owner?: string | null;
  deliverables?: string[];
  dependencies?: string[];
  nextAction?: string | null;
  approvalRequired?: boolean;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  evidenceIds?: string[];
}

export interface ExecutionWorkspaceData {
  title?: string | null;
  phase?: string | null;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
  makeBuy?: MakeBuyDecision[];
  processRoutes?: ProcessRoute[];
  machinery?: MachineryNeed[];
  qualifications?: QualificationGate[];
  workPackages?: WorkPackage[];
  nextActions?: ForgeAction[];
}

export interface ExecutionWorkspaceProps {
  data?: ExecutionWorkspaceData | null;
  onAction?: (action: ForgeAction) => void;
  onWorkPackage?: (workPackage: WorkPackage) => void;
  className?: string;
}

export type ResearchTaskStatus = string;

export interface ScenarioOverlay {
  id: string;
  title: string;
  description?: string | null;
  assumptions?: string[];
  effects?: string[];
  epistemic?: ForgeEpistemic | null;
  requiresHumanApproval?: boolean;
}

export interface ResearchTask {
  id: string;
  title: string;
  question: string;
  purpose?: string | null;
  status?: ResearchTaskStatus | null;
  priority?: string | null;
  epistemic?: ForgeEpistemic | null;
  requestedBy?: string | null;
  expectedOutput?: string | null;
  evidenceRequirements?: string[];
  scenarioOverlay?: ScenarioOverlay | null;
}

export interface ResearchReviewer {
  id: string;
  name: string;
  role?: string | null;
  status?: ForgeStatus | null;
  epistemic?: ForgeEpistemic | null;
}

export type ResearchSourceType = string;

export interface ResearchCapture {
  claim: string;
  value: string;
  epistemic: ForgeEpistemic;
  publisher: string;
  license: string;
  sourceUrl: string;
  sourceType: ResearchSourceType;
  accessDate: string;
  unit?: string;
  quote?: string;
  caveat?: string;
}

export interface ResearchSubmission {
  taskId: string;
  capture: ResearchCapture;
  reviewerId: string;
  scenarioOverlayApproval: {
    approved: boolean;
    overlayId?: string;
    note?: string;
  };
}

export interface ResearchResult {
  status: ForgeStatus;
  message: string;
  evidenceId?: string | null;
  epistemic?: ForgeEpistemic | null;
  reviewerNote?: string | null;
  nextStep?: string | null;
}

export interface ResearchWorkspaceData {
  title?: string | null;
  tasks?: ResearchTask[];
  reviewers?: ResearchReviewer[];
  initialTaskId?: string | null;
  result?: ResearchResult | null;
}

export type ResearchSubmitHandler = (
  submission: ResearchSubmission,
) => void | ResearchResult | Promise<void | ResearchResult>;

export interface ResearchWorkspaceProps {
  data?: ResearchWorkspaceData | null;
  onSubmit?: ResearchSubmitHandler;
  result?: ResearchResult | null;
  className?: string;
}

type ChipTone = "ok" | "warn" | "danger" | "unknown" | "neutral" | "accent";

function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

function safeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function label(value?: string | null): string {
  return value?.trim() || "UNKNOWN";
}

function chipTone(
  value?: string | null,
  kind: "status" | "epistemic" = "status",
): ChipTone {
  const normalized = (value ?? "").toUpperCase().replace(/[\s-]+/g, "_");
  if (!normalized || normalized.includes("UNKNOWN")) return "unknown";
  if (kind === "epistemic") {
    if (normalized.includes("CONFLICT")) return "danger";
    if (
      normalized.includes("ASSUMPTION") ||
      normalized.includes("SCENARIO") ||
      normalized.includes("ESTIMAT")
    )
      return "warn";
    if (normalized.includes("MEASURED")) return "ok";
    if (normalized.includes("DERIVED") || normalized.includes("MODEL"))
      return "accent";
    return "neutral";
  }
  if (
    normalized.includes("BLOCK") ||
    normalized.includes("FAIL") ||
    normalized.includes("REJECT") ||
    normalized.includes("CONFLICT")
  )
    return "danger";
  if (
    normalized.includes("RISK") ||
    normalized.includes("WARN") ||
    normalized.includes("PENDING") ||
    normalized.includes("OPEN") ||
    normalized.includes("DRAFT")
  )
    return "warn";
  if (
    normalized.includes("READY") ||
    normalized.includes("APPROV") ||
    normalized.includes("COMPLETE") ||
    normalized.includes("MATURE") ||
    normalized.includes("DONE")
  )
    return "ok";
  return "neutral";
}

function Chip({
  value,
  kind = "status",
  prefix,
}: {
  value?: string | null;
  kind?: "status" | "epistemic";
  prefix?: string;
}): JSX.Element {
  const text = label(value);
  return (
    <span className={cx("op-chip", `op-chip-${chipTone(value, kind)}`)}>
      {prefix ? `${prefix} · ` : ""}
      {text}
    </span>
  );
}

function EvidenceLine({ ids }: { ids?: string[] }): JSX.Element | null {
  if (!ids?.length) return null;
  return (
    <div className="op-evidence-line">
      <span className="op-eyebrow">EVIDENCE IDS</span>
      <span>{ids.join(" · ")}</span>
    </div>
  );
}

function EmptyState({
  title,
  detail,
  compact = false,
}: {
  title: string;
  detail: string;
  compact?: boolean;
}): JSX.Element {
  return (
    <div
      className={cx("op-empty", compact && "op-empty-compact")}
      role="status"
    >
      <Chip value="UNKNOWN" kind="epistemic" />
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  count,
}: {
  eyebrow: string;
  title: string;
  count?: number;
}): JSX.Element {
  return (
    <div className="op-section-heading">
      <div>
        <span className="op-eyebrow">{eyebrow}</span>
        <h3>{title}</h3>
      </div>
      {typeof count === "number" && <span className="op-count">{count}</span>}
    </div>
  );
}

function SurfaceHeader({
  eyebrow,
  title,
  detail,
  status,
  epistemic,
}: {
  eyebrow: string;
  title: string;
  detail?: string | null;
  status?: string | null;
  epistemic?: ForgeEpistemic | null;
}): JSX.Element {
  return (
    <header className="op-surface-header">
      <div>
        <span className="op-eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {detail && <p>{detail}</p>}
      </div>
      <div className="op-header-chips">
        <Chip value={status} prefix="STATUS" />
        {epistemic && (
          <Chip value={epistemic} kind="epistemic" prefix="EPISTEMIC" />
        )}
      </div>
    </header>
  );
}

function TargetBlock({ target }: { target?: ForgeTarget | null }): JSX.Element {
  if (!target)
    return (
      <EmptyState
        title="Target not returned"
        detail="The active run did not provide an objective interpretation. No target is inferred."
        compact
      />
    );
  const facts: Array<[string, string | number | null | undefined]> = [
    ["quantity", target.quantity],
    ["unit", target.unit],
    ["geography", target.geography],
    ["deadline", target.deadline],
  ];
  return (
    <div className="op-target-block">
      <div className="op-target-title">
        <h3>{target.title || "Untitled target"}</h3>
        <div className="op-chip-row">
          <Chip value={target.status} prefix="STATUS" />
          {target.epistemic && (
            <Chip
              value={target.epistemic}
              kind="epistemic"
              prefix="EPISTEMIC"
            />
          )}
        </div>
      </div>
      {target.description && <p className="op-lede">{target.description}</p>}
      <div className="op-fact-grid">
        {facts
          .filter(
            ([, value]) =>
              value !== undefined &&
              value !== null &&
              String(value).trim() !== "",
          )
          .map(([key, value]) => (
            <div className="op-fact" key={key}>
              <span className="op-eyebrow">{key}</span>
              <strong>
                {typeof value === "number" ? value.toLocaleString() : value}
              </strong>
            </div>
          ))}
      </div>
      {target.constraints?.length ? (
        <div className="op-inline-list">
          <span className="op-eyebrow">CONSTRAINTS</span>
          {target.constraints.map((constraint) => (
            <span className="op-inline-token" key={constraint}>
              {constraint}
            </span>
          ))}
        </div>
      ) : null}
      <EvidenceLine ids={target.evidenceIds} />
    </div>
  );
}

function ConclusionBlock({
  conclusion,
}: {
  conclusion?: ForgeConclusion | null;
}): JSX.Element {
  if (!conclusion)
    return (
      <EmptyState
        title="Conclusion not returned"
        detail="No verdict was supplied by the active run. Do not upgrade UNKNOWN to a yes/no answer."
        compact
      />
    );
  return (
    <div className="op-conclusion-block">
      <div className="op-conclusion-top">
        <div>
          <span className="op-eyebrow">CONCLUSION</span>
          <h3>{conclusion.verdict || "UNKNOWN"}</h3>
        </div>
        <div className="op-chip-row">
          <Chip value={conclusion.status} prefix="STATUS" />
          {conclusion.epistemic && (
            <Chip
              value={conclusion.epistemic}
              kind="epistemic"
              prefix="EPISTEMIC"
            />
          )}
        </div>
      </div>
      {conclusion.summary && <p className="op-lede">{conclusion.summary}</p>}
      {conclusion.rationale && (
        <details className="op-disclosure">
          <summary>Why this conclusion</summary>
          <p>{conclusion.rationale}</p>
        </details>
      )}
      <EvidenceLine ids={conclusion.evidenceIds} />
    </div>
  );
}

function ConfidenceBlock({
  confidence,
}: {
  confidence?: ForgeConfidence | null;
}): JSX.Element {
  if (!confidence)
    return (
      <EmptyState
        title="Confidence not returned"
        detail="No confidence basis was supplied. Confidence remains UNKNOWN."
        compact
      />
    );
  const display =
    confidence.valueLabel ||
    (typeof confidence.value === "number" &&
    Number.isFinite(confidence.value) &&
    confidence.value >= 0 &&
    confidence.value <= 1
      ? `${Math.round(confidence.value * 100)}%`
      : "UNKNOWN");
  return (
    <div className="op-confidence-block">
      <div className="op-confidence-value">
        <span className="op-eyebrow">MODEL CONFIDENCE</span>
        <strong>{display}</strong>
      </div>
      <div className="op-chip-row">
        <Chip
          value={confidence.epistemic}
          kind="epistemic"
          prefix="EPISTEMIC"
        />
      </div>
      {confidence.basis && <p>{confidence.basis}</p>}
      <EvidenceLine ids={confidence.evidenceIds} />
    </div>
  );
}

function ItemDisclosure({
  item,
  variant = "item",
  onSelect,
}: {
  item: ForgeItem;
  variant?: "item" | "alternative" | "dependency";
  onSelect?: () => void;
}): JSX.Element {
  const hasDepth = Boolean(
    item.summary ||
      item.detail ||
      item.owner ||
      item.metric ||
      item.note ||
      item.evidenceIds?.length ||
      (variant === "alternative" &&
        ((item as ForgeAlternative).tradeoffs?.length ||
          (item as ForgeAlternative).dependencyChanges?.length)) ||
      (variant === "dependency" &&
        ((item as ForgeDependency).relation ||
          (item as ForgeDependency).upstream ||
          (item as ForgeDependency).impact)),
  );
  const title = (
    <>
      <span className="op-row-title">{item.title}</span>
      <span className="op-row-chips">
        <Chip value={item.status} />
        {item.epistemic && <Chip value={item.epistemic} kind="epistemic" />}
      </span>
    </>
  );
  const body = (
    <div className="op-row-body">
      {item.summary && <p>{item.summary}</p>}
      {item.detail && <p>{item.detail}</p>}
      <div className="op-meta-grid">
        {item.owner && (
          <span>
            <b>owner</b>
            {item.owner}
          </span>
        )}
        {item.metric && (
          <span>
            <b>metric</b>
            {item.metric}
          </span>
        )}
        {variant === "dependency" && (item as ForgeDependency).relation && (
          <span>
            <b>relation</b>
            {(item as ForgeDependency).relation}
          </span>
        )}
        {variant === "dependency" && (item as ForgeDependency).upstream && (
          <span>
            <b>upstream</b>
            {(item as ForgeDependency).upstream}
          </span>
        )}
        {variant === "dependency" && (item as ForgeDependency).impact && (
          <span>
            <b>impact</b>
            {(item as ForgeDependency).impact}
          </span>
        )}
      </div>
      {variant === "alternative" && (
        <>
          <StringList
            label="tradeoffs"
            values={(item as ForgeAlternative).tradeoffs}
          />
          <StringList
            label="dependency changes"
            values={(item as ForgeAlternative).dependencyChanges}
          />
        </>
      )}{" "}
      {item.note && <p className="op-note">{item.note}</p>}
      <EvidenceLine ids={item.evidenceIds} />
    </div>
  );
  if (!hasDepth)
    return onSelect ? (
      <button type="button" className="op-row op-row-button" onClick={onSelect}>
        {title}
      </button>
    ) : (
      <div className="op-row">{title}</div>
    );
  return (
    <details className="op-disclosure op-row">
      <summary onClick={onSelect}>{title}</summary>
      {body}
    </details>
  );
}

function StringList({
  label: listLabel,
  values,
}: {
  label: string;
  values?: string[];
}): JSX.Element | null {
  if (!values?.length) return null;
  return (
    <div className="op-string-list">
      <b>{listLabel}</b>
      <ul>
        {values.map((value) => (
          <li key={value}>{value}</li>
        ))}
      </ul>
    </div>
  );
}

function ProgressiveList<T extends ForgeItem>({
  items,
  limit,
  label: moreLabel,
  renderItem,
}: {
  items: T[];
  limit: number;
  label: string;
  renderItem: (item: T) => React.ReactNode;
}): JSX.Element {
  const visible = items.slice(0, limit);
  const remaining = items.slice(limit);
  return (
    <>
      {visible.map(renderItem)}
      {remaining.length > 0 && (
        <details className="op-disclosure op-more">
          <summary>
            View {remaining.length} more {moreLabel}
          </summary>
          <div className="op-row-list">{remaining.map(renderItem)}</div>
        </details>
      )}
    </>
  );
}

function ForgeActionRow({
  action,
  onSelect,
}: {
  action: ForgeAction;
  onSelect?: () => void;
}): JSX.Element {
  const content = (
    <>
      <div className="op-action-main">
        <span className="op-row-title">{action.title}</span>
        <span className="op-row-subtitle">
          {action.kind || "ACTION"}
          {action.rationale ? ` · ${action.rationale}` : ""}
        </span>
      </div>
      <div className="op-row-chips">
        <Chip value={action.status} />
        {action.epistemic && <Chip value={action.epistemic} kind="epistemic" />}
        {action.approvalRequired && (
          <span className="op-approval-flag">HUMAN APPROVAL</span>
        )}
      </div>
    </>
  );
  if (!onSelect)
    return (
      <div className="op-action-row">
        {content}
        {action.due && <span className="op-action-due">{action.due}</span>}
      </div>
    );
  return (
    <button
      className="op-action-row op-action-button"
      type="button"
      onClick={onSelect}
    >
      {content}
      {action.due && <span className="op-action-due">{action.due}</span>}
    </button>
  );
}

export function CaseOverview({
  data,
  onAction,
  onAlternative,
  onDependency,
  className,
}: CaseOverviewProps): JSX.Element {
  const rootId = safeId(useId());
  if (!data)
    return (
      <section
        className={cx("op-surface op-case-overview", className)}
        aria-labelledby={`${rootId}-title`}
      >
        <SurfaceHeader
          eyebrow="ANALYZE / CASE"
          title="Case overview"
          detail="No operational case data is attached to this view."
        />
        <EmptyState
          title="Case overview unavailable"
          detail="The active run did not return an overview. No conclusion, bottleneck, or action is fabricated."
        />
      </section>
    );
  const bottlenecks = data.bottlenecks ?? [];
  const unknowns = data.unknowns ?? [];
  const alternatives = data.alternatives ?? [];
  const dependencies = data.dependencies ?? [];
  const actions = data.actions ?? [];
  return (
    <section
      className={cx("op-surface op-case-overview", className)}
      aria-labelledby={`${rootId}-title`}
    >
      <div id={`${rootId}-title`} className="op-visually-hidden">
        FORGE case overview
      </div>
      <SurfaceHeader
        eyebrow={
          data.caseId ? `ANALYZE / CASE ${data.caseId}` : "ANALYZE / CASE"
        }
        title={data.target?.title || "Case overview"}
        detail="A compact read of the objective, current conclusion, decision-sensitive gaps, and available actions."
        status={data.conclusion?.status}
        epistemic={data.conclusion?.epistemic}
      />
      <div className="op-case-lead">
        <section
          className="op-panel op-target-panel"
          aria-labelledby={`${rootId}-target`}
        >
          <SectionHeading eyebrow="OBJECTIVE" title="Target" />
          <div id={`${rootId}-target`}>
            <TargetBlock target={data.target} />
          </div>
        </section>
        <section
          className="op-panel op-conclusion-panel"
          aria-labelledby={`${rootId}-conclusion`}
        >
          <SectionHeading eyebrow="MODEL OUTPUT" title="Conclusion" />
          <div id={`${rootId}-conclusion`}>
            <ConclusionBlock conclusion={data.conclusion} />
          </div>
        </section>
        <section
          className="op-panel op-confidence-panel"
          aria-labelledby={`${rootId}-confidence`}
        >
          <SectionHeading eyebrow="TRACEABILITY" title="Confidence" />
          <div id={`${rootId}-confidence`}>
            <ConfidenceBlock confidence={data.confidence} />
          </div>
        </section>
      </div>
      <div className="op-case-grid">
        <section className="op-panel" aria-labelledby={`${rootId}-bottlenecks`}>
          <SectionHeading
            eyebrow="CONSTRAINTS"
            title="Top bottlenecks"
            count={bottlenecks.length}
          />
          <div id={`${rootId}-bottlenecks`}>
            {bottlenecks.length ? (
              <div className="op-row-list">
                <ProgressiveList
                  items={bottlenecks}
                  limit={5}
                  label="bottlenecks"
                  renderItem={(item) => (
                    <ItemDisclosure key={item.id} item={item} />
                  )}
                />
              </div>
            ) : (
              <EmptyState
                title="No bottlenecks returned"
                detail="Binding constraints are UNKNOWN for this case."
                compact
              />
            )}
          </div>
        </section>
        <section className="op-panel" aria-labelledby={`${rootId}-unknowns`}>
          <SectionHeading
            eyebrow="RESEARCH FRONTIER"
            title="Important unknowns"
            count={unknowns.length}
          />
          <div id={`${rootId}-unknowns`}>
            {unknowns.length ? (
              <div className="op-row-list">
                <ProgressiveList
                  items={unknowns}
                  limit={5}
                  label="unknowns"
                  renderItem={(item) => (
                    <ItemDisclosure key={item.id} item={item} />
                  )}
                />
              </div>
            ) : (
              <EmptyState
                title="No unknowns returned"
                detail="The run did not identify decision-sensitive unknowns."
                compact
              />
            )}
          </div>
        </section>
      </div>
      <div className="op-case-grid op-case-lower">
        <section
          className="op-panel"
          aria-labelledby={`${rootId}-alternatives`}
        >
          <SectionHeading
            eyebrow="DESIGN SPACE"
            title="Alternatives"
            count={alternatives.length}
          />
          <div id={`${rootId}-alternatives`}>
            {alternatives.length ? (
              <details className="op-disclosure op-collection">
                <summary>
                  Inspect {alternatives.length} architecture option
                  {alternatives.length === 1 ? "" : "s"}
                </summary>
                <div className="op-row-list">
                  {alternatives.map((item) => (
                    <ItemDisclosure
                      key={item.id}
                      item={item}
                      variant="alternative"
                      onSelect={
                        onAlternative ? () => onAlternative(item) : undefined
                      }
                    />
                  ))}
                </div>
              </details>
            ) : (
              <EmptyState
                title="No alternatives returned"
                detail="The active run did not provide an architecture comparison."
                compact
              />
            )}
          </div>
        </section>
        <section
          className="op-panel"
          aria-labelledby={`${rootId}-dependencies`}
        >
          <SectionHeading
            eyebrow="CAUSAL GRAPH"
            title="Dependencies"
            count={dependencies.length}
          />
          <div id={`${rootId}-dependencies`}>
            {dependencies.length ? (
              <details className="op-disclosure op-collection">
                <summary>
                  Inspect {dependencies.length} dependency link
                  {dependencies.length === 1 ? "" : "s"}
                </summary>
                <div className="op-row-list">
                  {dependencies.map((item) => (
                    <ItemDisclosure
                      key={item.id}
                      item={item}
                      variant="dependency"
                      onSelect={
                        onDependency ? () => onDependency(item) : undefined
                      }
                    />
                  ))}
                </div>
              </details>
            ) : (
              <EmptyState
                title="No dependencies returned"
                detail="Dependency edges are UNKNOWN for this case."
                compact
              />
            )}
          </div>
        </section>
      </div>
      <section
        className="op-panel op-action-panel"
        aria-labelledby={`${rootId}-actions`}
      >
        <SectionHeading
          eyebrow="WHAT TO DO NEXT"
          title="Actions"
          count={actions.length}
        />
        <div id={`${rootId}-actions`}>
          {actions.length ? (
            <div className="op-action-list">
              <ProgressiveList
                items={actions}
                limit={6}
                label="actions"
                renderItem={(action) => (
                  <ForgeActionRow
                    key={action.id}
                    action={action}
                    onSelect={onAction ? () => onAction(action) : undefined}
                  />
                )}
              />
            </div>
          ) : (
            <EmptyState
              title="No actions returned"
              detail="No transformation or research action was supplied. The next move is UNKNOWN."
              compact
            />
          )}
        </div>
        {actions.some((action) => action.approvalRequired) && (
          <p className="op-boundary-note">
            <strong>Human decision boundary.</strong> Actions marked HUMAN
            APPROVAL are surfaced for review only; this panel never executes
            them or changes the modeled world.
          </p>
        )}
      </section>
    </section>
  );
}

function MakeBuyRegister({ items }: { items: MakeBuyDecision[] }): JSX.Element {
  if (!items.length)
    return (
      <EmptyState
        title="Make / buy register empty"
        detail="No sourcing decision was returned. Do not infer a make, buy, license, or partner path."
        compact
      />
    );
  return (
    <div className="op-register-list">
      {items.map((item) => (
        <details className="op-disclosure op-register-row" key={item.id}>
          <summary>
            <span className="op-register-item">{item.item}</span>
            <span className="op-row-chips">
              <span
                className={cx(
                  "op-decision",
                  `op-decision-${chipTone(item.decision)}`,
                )}
              >
                {label(item.decision)}
              </span>
              <Chip value={item.status} />
              {item.epistemic && (
                <Chip value={item.epistemic} kind="epistemic" />
              )}
            </span>
          </summary>
          <div className="op-register-body">
            {item.rationale && <p>{item.rationale}</p>}
            <div className="op-meta-grid">
              {item.supplier && (
                <span>
                  <b>supplier / source</b>
                  {item.supplier}
                </span>
              )}
              {item.leadTime && (
                <span>
                  <b>lead time</b>
                  {item.leadTime}
                </span>
              )}
              {item.qualification && (
                <span>
                  <b>qualification</b>
                  {item.qualification}
                </span>
              )}
            </div>
            <EvidenceLine ids={item.evidenceIds} />
          </div>
        </details>
      ))}
    </div>
  );
}

function ProcessRouteList({ routes }: { routes: ProcessRoute[] }): JSX.Element {
  if (!routes.length)
    return (
      <EmptyState
        title="No process routes returned"
        detail="The process plan is UNKNOWN; no route is inferred from the product target."
        compact
      />
    );
  return (
    <div className="op-route-list">
      {routes.map((route) => (
        <details className="op-disclosure op-route" key={route.id}>
          <summary>
            <span>
              <span className="op-row-title">{route.title}</span>
              {route.summary && (
                <span className="op-row-subtitle">{route.summary}</span>
              )}
            </span>
            <span className="op-row-chips">
              <Chip value={route.status} />
              {route.epistemic && (
                <Chip value={route.epistemic} kind="epistemic" />
              )}
            </span>
          </summary>
          <div className="op-route-body">
            {route.steps?.length ? (
              <ol className="op-step-list">
                {route.steps.map((step) => (
                  <li key={step.id}>
                    <div>
                      <strong>{step.title}</strong>
                      {step.detail && <p>{step.detail}</p>}
                    </div>
                    <span className="op-row-chips">
                      <Chip value={step.status} />
                      {step.epistemic && (
                        <Chip value={step.epistemic} kind="epistemic" />
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState
                title="Route steps not returned"
                detail="This route has no declared process sequence."
                compact
              />
            )}
            <EvidenceLine ids={route.evidenceIds} />
          </div>
        </details>
      ))}
    </div>
  );
}

function MachineryList({
  machinery,
}: {
  machinery: MachineryNeed[];
}): JSX.Element {
  if (!machinery.length)
    return (
      <EmptyState
        title="Machinery requirements empty"
        detail="No equipment requirement was returned. Availability and capacity remain UNKNOWN."
        compact
      />
    );
  return (
    <div className="op-machinery-list">
      {machinery.map((item) => (
        <details className="op-disclosure op-machinery-row" key={item.id}>
          <summary>
            <span className="op-row-title">{item.title}</span>
            <span className="op-row-chips">
              <Chip value={item.status} />
              {item.epistemic && (
                <Chip value={item.epistemic} kind="epistemic" />
              )}
            </span>
          </summary>
          <div className="op-row-body">
            {item.purpose && <p>{item.purpose}</p>}
            <div className="op-meta-grid">
              {item.requirement && (
                <span>
                  <b>requirement</b>
                  {item.requirement}
                </span>
              )}
              {item.route && (
                <span>
                  <b>route</b>
                  {item.route}
                </span>
              )}
            </div>
            <EvidenceLine ids={item.evidenceIds} />
          </div>
        </details>
      ))}
    </div>
  );
}

function QualificationList({
  qualifications,
}: {
  qualifications: QualificationGate[];
}): JSX.Element {
  if (!qualifications.length)
    return (
      <EmptyState
        title="Qualification gates empty"
        detail="No acceptance or certification gate was returned. Qualification is not assumed."
        compact
      />
    );
  return (
    <div className="op-qualification-list">
      {qualifications.map((item) => (
        <details className="op-disclosure op-qualification-row" key={item.id}>
          <summary>
            <span className="op-row-title">{item.title}</span>
            <span className="op-row-chips">
              <Chip value={item.status} />
              {item.epistemic && (
                <Chip value={item.epistemic} kind="epistemic" />
              )}
            </span>
          </summary>
          <div className="op-row-body">
            {item.criterion && <p>{item.criterion}</p>}
            <div className="op-meta-grid">
              {item.owner && (
                <span>
                  <b>owner</b>
                  {item.owner}
                </span>
              )}
            </div>
            <EvidenceLine ids={item.evidenceIds} />
          </div>
        </details>
      ))}
    </div>
  );
}

function WorkPackageList({
  packages,
  onSelect,
}: {
  packages: WorkPackage[];
  onSelect?: (workPackage: WorkPackage) => void;
}): JSX.Element {
  if (!packages.length)
    return (
      <EmptyState
        title="Work package register empty"
        detail="No executable work packages were returned. Sequence and ownership remain UNKNOWN."
        compact
      />
    );
  return (
    <div className="op-work-package-list">
      {packages.map((item) => {
        const content = (
          <>
            <div className="op-work-package-main">
              <span className="op-row-title">{item.title}</span>
              {item.summary && (
                <span className="op-row-subtitle">{item.summary}</span>
              )}
            </div>
            <div className="op-row-chips">
              <Chip value={item.sequence} prefix="SEQ" />
              <Chip value={item.status} />
              {item.approvalRequired && (
                <span className="op-approval-flag">HUMAN APPROVAL</span>
              )}
            </div>
          </>
        );
        return (
          <div className="op-work-package-row" key={item.id}>
            {onSelect ? (
              <button
                type="button"
                className="op-work-package-button"
                onClick={() => onSelect(item)}
              >
                {content}
              </button>
            ) : (
              content
            )}
            <details className="op-disclosure op-work-package-detail">
              <summary>Work package detail</summary>
              <div className="op-row-body">
                {item.nextAction && (
                  <p>
                    <b>next action</b> {item.nextAction}
                  </p>
                )}
                <div className="op-meta-grid">
                  {item.owner && (
                    <span>
                      <b>owner</b>
                      {item.owner}
                    </span>
                  )}
                  {item.dependencies?.length ? (
                    <span>
                      <b>dependencies</b>
                      {item.dependencies.join(" · ")}
                    </span>
                  ) : null}
                </div>
                <StringList label="deliverables" values={item.deliverables} />
                <EvidenceLine ids={item.evidenceIds} />
              </div>
            </details>
          </div>
        );
      })}
    </div>
  );
}

export function ExecutionWorkspace({
  data,
  onAction,
  onWorkPackage,
  className,
}: ExecutionWorkspaceProps): JSX.Element {
  const rootId = safeId(useId());
  if (!data)
    return (
      <section
        className={cx("op-surface op-execution-workspace", className)}
        aria-labelledby={`${rootId}-title`}
      >
        <SurfaceHeader
          eyebrow="EXECUTE / WORKSPACE"
          title="Execution workspace"
          detail="No operational execution data is attached to this view."
        />
        <EmptyState
          title="Execution plan unavailable"
          detail="The active run did not return routes, equipment, qualification gates, or work packages."
        />
      </section>
    );
  const makeBuy = data.makeBuy ?? [];
  const routes = data.processRoutes ?? [];
  const machinery = data.machinery ?? [];
  const qualifications = data.qualifications ?? [];
  const workPackages = data.workPackages ?? [];
  const actions = data.nextActions ?? [];
  return (
    <section
      className={cx("op-surface op-execution-workspace", className)}
      aria-labelledby={`${rootId}-title`}
    >
      <div id={`${rootId}-title`} className="op-visually-hidden">
        FORGE execution workspace
      </div>
      <SurfaceHeader
        eyebrow="EXECUTE / WORKSPACE"
        title={data.title || "Execution workspace"}
        detail="Turn an accepted architecture into traceable routes, qualification gates, work packages, and next actions."
        status={data.status}
        epistemic={data.epistemic}
      />
      <div className="op-execution-lead">
        <section
          className="op-panel op-work-package-panel"
          aria-labelledby={`${rootId}-packages`}
        >
          <SectionHeading
            eyebrow="SEQUENCED WORK"
            title="Work packages"
            count={workPackages.length}
          />
          <div id={`${rootId}-packages`}>
            <WorkPackageList packages={workPackages} onSelect={onWorkPackage} />
          </div>
        </section>
        <section
          className="op-panel op-next-actions-panel"
          aria-labelledby={`${rootId}-next`}
        >
          <SectionHeading
            eyebrow="IMMEDIATE NEXT"
            title="Next actions"
            count={actions.length}
          />
          <div id={`${rootId}-next`}>
            {actions.length ? (
              <div className="op-action-list">
                <ProgressiveList
                  items={actions}
                  limit={5}
                  label="next actions"
                  renderItem={(action) => (
                    <ForgeActionRow
                      key={action.id}
                      action={action}
                      onSelect={onAction ? () => onAction(action) : undefined}
                    />
                  )}
                />
              </div>
            ) : (
              <EmptyState
                title="No next actions returned"
                detail="The execution queue is UNKNOWN; no action is auto-generated."
                compact
              />
            )}
          </div>
        </section>
      </div>
      <div className="op-execution-folds">
        <details className="op-fold">
          <summary>
            <span>
              <span className="op-eyebrow">SOURCING</span>
              <strong>Make / buy register</strong>
            </span>
            <span className="op-count">{makeBuy.length}</span>
          </summary>
          <MakeBuyRegister items={makeBuy} />
        </details>
        <details className="op-fold">
          <summary>
            <span>
              <span className="op-eyebrow">PROCESS PLAN</span>
              <strong>Process routes</strong>
            </span>
            <span className="op-count">{routes.length}</span>
          </summary>
          <ProcessRouteList routes={routes} />
        </details>
        <details className="op-fold">
          <summary>
            <span>
              <span className="op-eyebrow">EQUIPMENT</span>
              <strong>Machinery requirements</strong>
            </span>
            <span className="op-count">{machinery.length}</span>
          </summary>
          <MachineryList machinery={machinery} />
        </details>
        <details className="op-fold">
          <summary>
            <span>
              <span className="op-eyebrow">ACCEPTANCE</span>
              <strong>Qualification gates</strong>
            </span>
            <span className="op-count">{qualifications.length}</span>
          </summary>
          <QualificationList qualifications={qualifications} />
        </details>
      </div>
      {(actions.some((action) => action.approvalRequired) ||
        workPackages.some((item) => item.approvalRequired)) && (
        <p className="op-boundary-note">
          <strong>Human decision boundary.</strong> Qualification, supplier, and
          work-package decisions remain with the responsible reviewer. This
          workspace only records and surfaces returned data.
        </p>
      )}
    </section>
  );
}

interface CaptureDraft {
  claim: string;
  value: string;
  epistemic: ForgeEpistemic | "";
  sourceUrl: string;
  sourceType: string;
  publisher: string;
  license: string;
  unit: string;
  accessDate: string;
  quote: string;
  caveat: string;
  reviewerId: string;
  overlayNote: string;
}

const EMPTY_CAPTURE: CaptureDraft = {
  claim: "",
  value: "",
  epistemic: "",
  sourceUrl: "",
  sourceType: "",
  publisher: "",
  license: "",
  unit: "pcs/year",
  accessDate: "",
  quote: "",
  caveat: "",
  reviewerId: "",
  overlayNote: "",
};

function TaskCard({
  task,
  selected,
  onSelect,
}: {
  task: ResearchTask;
  selected: boolean;
  onSelect: () => void;
}): JSX.Element {
  const taskId = safeId(task.id);
  return (
    <article
      className={cx("op-task-card", selected && "op-task-card-selected")}
    >
      <button
        className="op-task-select"
        type="button"
        aria-pressed={selected}
        onClick={onSelect}
      >
        <span className="op-task-select-mark" aria-hidden="true">
          {selected ? "●" : "○"}
        </span>
        <span>
          <strong>{task.title}</strong>
          <span className="op-row-subtitle">{task.question}</span>
        </span>
        <span className="op-row-chips">
          <Chip value={task.priority} prefix="PRIORITY" />
          <Chip value={task.status} />
          <Chip value={task.epistemic} kind="epistemic" />
        </span>
      </button>
      {(task.purpose ||
        task.expectedOutput ||
        task.evidenceRequirements?.length ||
        task.scenarioOverlay) && (
        <details className="op-disclosure op-task-detail">
          <summary>Task brief</summary>
          <div id={`${taskId}-brief`} className="op-row-body">
            {task.purpose && <p>{task.purpose}</p>}
            {task.expectedOutput && (
              <p>
                <b>expected output</b> {task.expectedOutput}
              </p>
            )}
            <StringList
              label="evidence requirements"
              values={task.evidenceRequirements}
            />
            {task.scenarioOverlay && (
              <ScenarioOverlayCard overlay={task.scenarioOverlay} compact />
            )}
          </div>
        </details>
      )}
    </article>
  );
}

function ScenarioOverlayCard({
  overlay,
  compact = false,
}: {
  overlay: ScenarioOverlay;
  compact?: boolean;
}): JSX.Element {
  return (
    <div
      className={cx("op-overlay-card", compact && "op-overlay-card-compact")}
    >
      <div className="op-overlay-heading">
        <span className="op-eyebrow">SCENARIO OVERLAY</span>
        <Chip value={overlay.epistemic || "SCENARIO"} kind="epistemic" />
        <span className="op-approval-flag">
          {overlay.requiresHumanApproval === false
            ? "REVIEW FLAG"
            : "APPROVAL REQUIRED"}
        </span>
      </div>
      <strong>{overlay.title}</strong>
      {overlay.description && <p>{overlay.description}</p>}
      <StringList label="assumptions" values={overlay.assumptions} />
      <StringList label="model effects" values={overlay.effects} />
    </div>
  );
}

function CaptureField({
  id,
  label: fieldLabel,
  hint,
  children,
  required = false,
}: {
  id: string;
  label: string;
  hint?: string;
  children: React.ReactNode;
  required?: boolean;
}): JSX.Element {
  return (
    <div className="op-field">
      <label htmlFor={id}>
        {fieldLabel}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {hint && (
        <span className="op-field-hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
      {children}
    </div>
  );
}

function ResearchResultPanel({
  result,
}: {
  result?: ResearchResult | null;
}): JSX.Element | null {
  if (!result) return null;
  return (
    <section className="op-result" aria-live="polite">
      <div className="op-result-heading">
        <span className="op-eyebrow">CAPTURE RESULT</span>
        <div className="op-chip-row">
          <Chip value={result.status} />
          {result.epistemic && (
            <Chip value={result.epistemic} kind="epistemic" />
          )}
        </div>
      </div>
      <p>{result.message}</p>
      <div className="op-meta-grid">
        {result.evidenceId && (
          <span>
            <b>evidence id</b>
            {result.evidenceId}
          </span>
        )}
        {result.reviewerNote && (
          <span>
            <b>reviewer note</b>
            {result.reviewerNote}
          </span>
        )}
        {result.nextStep && (
          <span>
            <b>next step</b>
            {result.nextStep}
          </span>
        )}
      </div>
    </section>
  );
}

function ResearchWorkspaceBase({
  data,
  onSubmit,
  result,
  className,
}: ResearchWorkspaceProps): JSX.Element {
  const rootId = safeId(useId());
  const tasks = data?.tasks ?? [];
  const reviewers = data?.reviewers ?? [];
  const initialTaskId =
    data?.initialTaskId && tasks.some((task) => task.id === data.initialTaskId)
      ? data.initialTaskId
      : (tasks[0]?.id ?? null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(
    initialTaskId,
  );
  const [draft, setDraft] = useState<CaptureDraft>(EMPTY_CAPTURE);
  const [overlayApproved, setOverlayApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [localResult, setLocalResult] = useState<ResearchResult | null>(null);
  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId) ?? null,
    [tasks, selectedTaskId],
  );
  const selectedOverlay = selectedTask?.scenarioOverlay ?? null;
  const overlayRequiresApproval = Boolean(
    selectedOverlay && selectedOverlay.requiresHumanApproval !== false,
  );
  const resultToShow = result ?? data?.result ?? localResult;
  const formId = `${rootId}-capture-form`;

  useEffect(() => {
    if (!selectedTaskId || !tasks.some((task) => task.id === selectedTaskId)) {
      setSelectedTaskId(initialTaskId);
      setDraft(EMPTY_CAPTURE);
      setOverlayApproved(false);
    }
  }, [initialTaskId, selectedTaskId, tasks]);

  function selectTask(id: string): void {
    setSelectedTaskId(id);
    setDraft(EMPTY_CAPTURE);
    setOverlayApproved(false);
    setError(null);
    setSubmitted(false);
    setLocalResult(null);
  }

  function updateDraft<K extends keyof CaptureDraft>(
    field: K,
    value: CaptureDraft[K],
  ): void {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);
    setSubmitted(false);
    if (!selectedTask) {
      setError("Select a research task before submitting a capture.");
      return;
    }
    if (!onSubmit) {
      setError("Submit callback unavailable; no evidence capture was sent.");
      return;
    }
    if (
      !draft.claim.trim() ||
      !draft.value.trim() ||
      !draft.epistemic ||
      !draft.sourceUrl.trim() ||
      !draft.sourceType ||
      !draft.accessDate ||
      !draft.reviewerId
    ) {
      setError(
        "Complete the required claim, value, epistemic class, source, access date, and reviewer fields. Publisher and license are supplied by the enclosing evidence boundary.",
      );
      return;
    }
    if (!event.currentTarget.checkValidity()) {
      setError(
        "Check the source URL and required fields before submitting the capture.",
      );
      return;
    }
    if (overlayRequiresApproval && !overlayApproved) {
      setError(
        "Explicit human approval is required before this scenario overlay can accompany the submission.",
      );
      return;
    }
    const submission: ResearchSubmission = {
      taskId: selectedTask.id,
      capture: {
        claim: draft.claim.trim(),
        value: draft.value.trim(),
        epistemic: draft.epistemic,
        publisher: draft.publisher.trim(),
        license: draft.license.trim(),
        sourceUrl: draft.sourceUrl.trim(),
        sourceType: draft.sourceType,
        accessDate: draft.accessDate,
        unit: draft.unit.trim() || undefined,
        quote: draft.quote.trim(),
        caveat: draft.caveat.trim(),
      },
      reviewerId: draft.reviewerId,
      scenarioOverlayApproval: selectedOverlay
        ? {
            approved: overlayApproved,
            overlayId: selectedOverlay.id,
            note: draft.overlayNote.trim() || undefined,
          }
        : { approved: false },
    };
    setBusy(true);
    try {
      const callbackResult = await onSubmit(submission);
      if (callbackResult) setLocalResult(callbackResult);
      setSubmitted(true);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Evidence capture could not be submitted.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!data)
    return (
      <section
        className={cx("op-surface op-research-workspace", className)}
        aria-labelledby={`${rootId}-title`}
      >
        <SurfaceHeader
          eyebrow="RESEARCH / EVIDENCE"
          title="Research workspace"
          detail="No research queue is attached to this view."
        />
        <EmptyState
          title="Research workspace unavailable"
          detail="No structured research tasks or reviewer list was returned."
        />
      </section>
    );

  return (
    <section
      className={cx("op-surface op-research-workspace", className)}
      aria-labelledby={`${rootId}-title`}
    >
      <div id={`${rootId}-title`} className="op-visually-hidden">
        FORGE research workspace
      </div>
      <SurfaceHeader
        eyebrow="RESEARCH / EVIDENCE"
        title={data.title || "Research workspace"}
        detail="Resolve a decision-sensitive unknown with typed evidence capture, reviewer assignment, and an explicit scenario boundary."
        status={selectedTask?.status}
        epistemic={selectedTask?.epistemic}
      />
      <div className="op-research-grid">
        <aside
          className="op-panel op-task-rail"
          aria-labelledby={`${rootId}-tasks`}
        >
          <SectionHeading
            eyebrow="VALUE OF INFORMATION"
            title="Structured tasks"
            count={tasks.length}
          />
          <div id={`${rootId}-tasks`} className="op-task-list">
            {tasks.length ? (
              tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  selected={selectedTask?.id === task.id}
                  onSelect={() => selectTask(task.id)}
                />
              ))
            ) : (
              <EmptyState
                title="No research tasks returned"
                detail="The evidence queue is UNKNOWN; no task is invented."
                compact
              />
            )}
          </div>
        </aside>
        <div
          className="op-panel op-capture-panel"
          aria-labelledby={`${rootId}-capture`}
        >
          <SectionHeading
            eyebrow="EVIDENCE CAPTURE"
            title={selectedTask ? selectedTask.title : "Select a task"}
          />
          <div id={`${rootId}-capture`}>
            {selectedTask ? (
              <>
                <div className="op-selected-question">
                  <span className="op-eyebrow">QUESTION</span>
                  <p>{selectedTask.question}</p>
                  {selectedTask.requestedBy && (
                    <span className="op-row-subtitle">
                      requested by {selectedTask.requestedBy}
                    </span>
                  )}
                </div>
                {selectedOverlay && (
                  <ScenarioOverlayCard overlay={selectedOverlay} />
                )}
                <form
                  id={formId}
                  className="op-capture-form"
                  onSubmit={(event) => void handleSubmit(event)}
                  noValidate
                >
                  <div className="op-form-grid">
                    <CaptureField
                      id={`${rootId}-claim`}
                      label="Claim"
                      hint="One falsifiable statement about the selected task."
                      required
                    >
                      <textarea
                        id={`${rootId}-claim`}
                        value={draft.claim}
                        onChange={(event) =>
                          updateDraft("claim", event.target.value)
                        }
                        rows={3}
                        required
                      />
                    </CaptureField>
                    <CaptureField
                      id={`${rootId}-value`}
                      label="Observed or reported value"
                      hint="Keep the source's wording and units where relevant."
                      required
                    >
                      <textarea
                        id={`${rootId}-value`}
                        value={draft.value}
                        onChange={(event) =>
                          updateDraft("value", event.target.value)
                        }
                        rows={3}
                        required
                      />
                    </CaptureField>
                    <CaptureField
                      id={`${rootId}-epistemic`}
                      label="Epistemic class"
                      hint="Do not upgrade UNKNOWN without evidence."
                      required
                    >
                      <select
                        id={`${rootId}-epistemic`}
                        value={draft.epistemic}
                        onChange={(event) =>
                          updateDraft(
                            "epistemic",
                            event.target.value as ForgeEpistemic,
                          )
                        }
                        required
                      >
                        <option value="">Choose a class</option>
                        {[
                          "MEASURED",
                          "REPORTED",
                          "DERIVED",
                          "ESTIMATED",
                          "MODELLED",
                          "ASSUMPTION",
                          "SCENARIO",
                          "UNKNOWN",
                          "CONFLICTED",
                        ].map((value) => (
                          <option value={value} key={value}>
                            {value}
                          </option>
                        ))}
                      </select>
                    </CaptureField>
                    <CaptureField
                      id={`${rootId}-source-type`}
                      label="Source type"
                      hint="Use the strongest available source class."
                      required
                    >
                      <select
                        id={`${rootId}-source-type`}
                        value={draft.sourceType}
                        onChange={(event) =>
                          updateDraft("sourceType", event.target.value)
                        }
                        required
                      >
                        <option value="">Choose a source type</option>
                        {[
                          "OFFICIAL_RECORD",
                          "REGULATORY",
                          "COMPANY_FILING",
                          "STANDARD",
                          "TECHNICAL_PAPER",
                          "DATASET",
                          "TRADE_RECORD",
                          "SECONDARY_REPORT",
                          "OTHER",
                        ].map((value) => (
                          <option value={value} key={value}>
                            {value.replace(/_/g, " ")}
                          </option>
                        ))}
                      </select>
                    </CaptureField>
                    <CaptureField
                      id={`${rootId}-source-url`}
                      label="Source URL or locator"
                      required
                    >
                      <input
                        id={`${rootId}-source-url`}
                        type="url"
                        value={draft.sourceUrl}
                        onChange={(event) =>
                          updateDraft("sourceUrl", event.target.value)
                        }
                        placeholder="https://…"
                        required
                      />
                    </CaptureField>
                    <CaptureField
                      id={`${rootId}-access-date`}
                      label="Access date"
                      hint="ISO 8601 date (YYYY-MM-DD)."
                      required
                    >
                      <input
                        id={`${rootId}-access-date`}
                        type="text"
                        inputMode="numeric"
                        pattern="[0-9]{4}-[0-9]{2}-[0-9]{2}"
                        placeholder="YYYY-MM-DD"
                        value={draft.accessDate}
                        onChange={(event) =>
                          updateDraft("accessDate", event.target.value)
                        }
                        required
                      />
                    </CaptureField>
                    <CaptureField
                      id={`${rootId}-quote`}
                      label="Quote or extract"
                      hint="Optional; preserve a short auditable excerpt."
                    >
                      <textarea
                        id={`${rootId}-quote`}
                        value={draft.quote}
                        onChange={(event) =>
                          updateDraft("quote", event.target.value)
                        }
                        rows={3}
                      />
                    </CaptureField>
                    <CaptureField
                      id={`${rootId}-caveat`}
                      label="Caveat or scope note"
                      hint="Name limits, conflicts, or missing context."
                    >
                      <textarea
                        id={`${rootId}-caveat`}
                        value={draft.caveat}
                        onChange={(event) =>
                          updateDraft("caveat", event.target.value)
                        }
                        rows={3}
                      />
                    </CaptureField>
                  </div>
                  <div className="op-review-block">
                    <div className="op-review-heading">
                      <span className="op-eyebrow">REVIEWER</span>
                      <strong>Who will review this capture?</strong>
                    </div>
                    {reviewers.length ? (
                      <div className="op-review-options">
                        {reviewers.map((reviewer) => (
                          <label
                            className={cx(
                              "op-review-option",
                              draft.reviewerId === reviewer.id &&
                                "op-review-option-selected",
                            )}
                            key={reviewer.id}
                          >
                            <input
                              type="radio"
                              name={`${rootId}-reviewer`}
                              value={reviewer.id}
                              checked={draft.reviewerId === reviewer.id}
                              onChange={(event) =>
                                updateDraft("reviewerId", event.target.value)
                              }
                              required
                            />
                            <span>
                              <strong>{reviewer.name}</strong>
                              <small>{reviewer.role || "role UNKNOWN"}</small>
                            </span>
                            <span className="op-row-chips">
                              <Chip value={reviewer.status} />
                              {reviewer.epistemic && (
                                <Chip
                                  value={reviewer.epistemic}
                                  kind="epistemic"
                                />
                              )}
                            </span>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <EmptyState
                        title="No reviewers returned"
                        detail="A human reviewer is required; submission is unavailable until one is supplied."
                        compact
                      />
                    )}
                  </div>
                  {selectedOverlay && (
                    <div
                      className={cx(
                        "op-approval-block",
                        overlayApproved && "op-approval-block-approved",
                      )}
                    >
                      <div>
                        <span className="op-eyebrow">
                          HUMAN APPROVAL BOUNDARY
                        </span>
                        <strong>
                          Approve scenario overlay for this submission
                        </strong>
                        <p>
                          This records your explicit approval for reviewer
                          consideration. It does not apply the overlay, mutate
                          baseline evidence, or change the modeled world.
                        </p>
                      </div>
                      <label className="op-approval-check">
                        <input
                          type="checkbox"
                          checked={overlayApproved}
                          onChange={(event) =>
                            setOverlayApproved(event.target.checked)
                          }
                          aria-describedby={`${rootId}-approval-note`}
                        />
                        <span>
                          I have reviewed the overlay assumptions and approve
                          attaching it to this evidence capture.
                        </span>
                      </label>
                      <CaptureField
                        id={`${rootId}-overlay-note`}
                        label="Approval note"
                        hint="Optional rationale for the reviewer."
                      >
                        <textarea
                          id={`${rootId}-overlay-note`}
                          value={draft.overlayNote}
                          onChange={(event) =>
                            updateDraft("overlayNote", event.target.value)
                          }
                          rows={2}
                        />
                      </CaptureField>
                    </div>
                  )}
                  {error && (
                    <p className="op-form-error" role="alert">
                      {error}
                    </p>
                  )}
                  {submitted && !resultToShow && (
                    <p className="op-form-status" role="status">
                      Capture submitted; awaiting the adapter's persisted
                      result.
                    </p>
                  )}
                  <div className="op-form-actions">
                    <button
                      type="submit"
                      className="op-submit-button"
                      disabled={busy || !reviewers.length}
                    >
                      {busy ? "SUBMITTING…" : "SUBMIT FOR REVIEW"}
                    </button>
                    <span className="op-form-note">
                      Required fields are sent exactly as captured; no evidence
                      class is inferred.
                    </span>
                  </div>
                </form>
              </>
            ) : (
              <EmptyState
                title="Select a research task"
                detail="Choose a structured task to open its typed capture form."
              />
            )}
          </div>
        </div>
      </div>
      <ResearchResultPanel result={resultToShow} />
    </section>
  );
}

/**
 * The evidence boundary owns source identity and rights metadata. Keeping these
 * fields outside the claim body prevents a reported observation from being
 * promoted with an implicit or invented license.
 */
export function ResearchWorkspace(props: ResearchWorkspaceProps): JSX.Element {
  const boundaryId = safeId(useId());
  const [reviewer, setReviewer] = useState("");
  const [publisher, setPublisher] = useState("");
  const [license, setLicense] = useState("");
  const [unit, setUnit] = useState("pcs/year");

  const submit: ResearchSubmitHandler | undefined = props.onSubmit
    ? async (submission) => {
        if (!reviewer.trim() || !publisher.trim() || !license.trim()) {
          throw new Error(
            "Reviewer identity, publisher, and source license/rights posture are required at the evidence boundary.",
          );
        }
        return props.onSubmit?.({
          ...submission,
          reviewerId: reviewer.trim(),
          capture: {
            ...submission.capture,
            publisher: publisher.trim(),
            license: license.trim(),
            unit: unit.trim() || undefined,
          },
        });
      }
    : undefined;

  return (
    <div className="op-research-boundary">
      <section
        className="op-panel op-source-boundary"
        aria-label="Evidence source boundary"
      >
        <SectionHeading
          eyebrow="EVIDENCE BOUNDARY"
          title="Source identity and review authority"
        />
        <p className="op-row-subtitle" id={`${boundaryId}-title`}>
          These fields apply to the selected capture. FORGE will not infer
          source rights or reviewer identity.
        </p>
        <div className="op-form-grid">
          <CaptureField
            id={`${boundaryId}-reviewer`}
            label="Reviewer identity"
            hint="Named person or controlled review role."
            required
          >
            <input
              id={`${boundaryId}-reviewer`}
              value={reviewer}
              onChange={(event) => setReviewer(event.target.value)}
              required
            />
          </CaptureField>
          <CaptureField
            id={`${boundaryId}-publisher`}
            label="Publisher / issuing organization"
            required
          >
            <input
              id={`${boundaryId}-publisher`}
              value={publisher}
              onChange={(event) => setPublisher(event.target.value)}
              required
            />
          </CaptureField>
          <CaptureField
            id={`${boundaryId}-license`}
            label="License or rights posture"
            hint="State the actual reuse/reference terms; do not guess."
            required
          >
            <input
              id={`${boundaryId}-license`}
              value={license}
              onChange={(event) => setLicense(event.target.value)}
              placeholder="e.g. public record; reference-only"
              required
            />
          </CaptureField>
          <CaptureField
            id={`${boundaryId}-unit`}
            label="Capacity unit"
            hint="Used only when the captured value contains a numeric capacity range."
          >
            <input
              id={`${boundaryId}-unit`}
              value={unit}
              onChange={(event) => setUnit(event.target.value)}
            />
          </CaptureField>
        </div>
      </section>
      <ResearchWorkspaceBase {...props} onSubmit={submit} />
    </div>
  );
}
