import { useEffect, useState } from "react";
import {
  Campaign,
  CampaignResponse,
  InvestigationCase,
  RelatedCasesResponse,
  checkApi,
  createReport,
  createInvestigation,
  fetchCampaigns,
  fetchRelationships,
} from "./api";
import { viewFromHash, type View } from "./routes";

const navItems: Array<{ id: View; label: string; eyebrow: string }> = [
  { id: "dashboard", label: "Dashboard", eyebrow: "Overview" },
  { id: "new", label: "New investigation", eyebrow: "Intake" },
  { id: "results", label: "Investigation results", eyebrow: "Analysis" },
  { id: "related", label: "Related cases", eyebrow: "Correlation" },
  { id: "campaign", label: "Campaign view", eyebrow: "Intelligence" },
  { id: "details", label: "Case details", eyebrow: "Evidence" },
];

function navigate(view: View) {
  window.location.hash = view;
}

export function App() {
  const [view, setView] = useState<View>(viewFromHash(window.location.hash));
  const [currentCase, setCurrentCase] = useState<InvestigationCase | null>(null);
  const [apiAvailable, setApiAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    const onHashChange = () => setView(viewFromHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    checkApi().then(setApiAvailable).catch(() => setApiAvailable(false));
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const title = navItems.find((item) => item.id === view)?.label ?? "Dashboard";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">M</div>
          <div>
            <p className="brand-name">MailTrace</p>
            <p className="brand-subtitle">Threat workbench</p>
          </div>
        </div>
        <div className="rail-label">Workspace</div>
        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map((item) => (
            <a
              className={`nav-item ${view === item.id ? "is-active" : ""}`}
              href={`#${item.id}`}
              key={item.id}
              aria-current={view === item.id ? "page" : undefined}
            >
              <span className="nav-indicator" aria-hidden="true" />
              <span>
                <strong>{item.label}</strong>
                <small>{item.eyebrow}</small>
              </span>
            </a>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className={`system-dot ${apiAvailable === false ? "is-offline" : ""}`} />
          <div>
            <p>Local analysis</p>
            <small>{apiAvailable === false ? "API unavailable" : "Ready for review"}</small>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <p className="breadcrumb">MailTrace / {title}</p>
            <h1>{title}</h1>
          </div>
          <div className="topbar-actions">
            <span className={`connection-state ${apiAvailable === false ? "is-offline" : ""}`}>
              <span className="status-dot" aria-hidden="true" />
              {apiAvailable === false ? "API unavailable" : "Local workspace"}
            </span>
            <button className="button button-primary" onClick={() => navigate("new")}>New investigation</button>
          </div>
        </header>

        <div className="content-wrap">
          {view === "dashboard" && <Dashboard apiAvailable={apiAvailable} onNew={() => navigate("new")} />}
          {view === "new" && (
            <NewInvestigation
              onCreated={(createdCase) => {
                setCurrentCase(createdCase);
                navigate("results");
              }}
            />
          )}
          {view === "results" && <InvestigationResults currentCase={currentCase} onNew={() => navigate("new")} />}
          {view === "related" && <RelatedCases currentCase={currentCase} />}
          {view === "campaign" && <CampaignView currentCase={currentCase} />}
          {view === "details" && <CaseDetails currentCase={currentCase} />}
        </div>
      </main>
    </div>
  );
}

function Dashboard({ apiAvailable, onNew }: { apiAvailable: boolean | null; onNew: () => void }) {
  return (
    <div className="page-stack">
      <section className="hero-strip">
        <div>
          <p className="section-kicker">Investigation workspace</p>
          <h2>Trace the signal. Preserve the evidence.</h2>
          <p className="hero-copy">Analyze controlled email evidence across headers, indicators, relationships, and response context.</p>
        </div>
        <button className="button button-light" onClick={onNew}>Start an investigation <span aria-hidden="true">-&gt;</span></button>
      </section>

      <section className="dashboard-grid">
        <Panel className="queue-panel">
          <SectionTitle eyebrow="Cases" title="Investigation queue" action="No live cases loaded" />
          <EmptyState
            title={apiAvailable === false ? "API connection unavailable" : "No investigations yet"}
            body={apiAvailable === false ? "Connect the FastAPI service to load saved investigations." : "Create a controlled .eml investigation to begin building evidence."}
            actionLabel="New investigation"
            onAction={onNew}
          />
        </Panel>
        <Panel className="readiness-panel">
          <SectionTitle eyebrow="System" title="Analysis readiness" />
          <div className="readiness-list">
            <Readiness label="Local parser" state="Ready" />
            <Readiness label="Deterministic rules" state="Ready" />
            <Readiness label="Threat intelligence" state="Optional" muted />
            <Readiness label="Explanation layer" state="Fallback available" muted />
          </div>
        </Panel>
      </section>

      <section className="capability-band">
        <div>
          <p className="section-kicker">Workbench map</p>
          <h2>One case, five evidence lanes.</h2>
        </div>
        <div className="lane-grid">
          <Lane number="01" title="Inspect" copy="Email, headers, URLs, and attachments" />
          <Lane number="02" title="Assess" copy="Evidence-backed risk and severity" />
          <Lane number="03" title="Correlate" copy="Indicators, related cases, campaigns" />
          <Lane number="04" title="Respond" copy="Recommendations and report output" />
        </div>
      </section>
    </div>
  );
}

function NewInvestigation({ onCreated }: { onCreated: (createdCase: InvestigationCase) => void }) {
  const [file, setFile] = useState<File | undefined>();
  const [pastedEmail, setPastedEmail] = useState("");
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canSubmit = Boolean(file || pastedEmail.trim());
  async function submit() {
    if (!canSubmit) return;
    setLoading(true);
    setError("");
    try {
      const result = await createInvestigation({ file, pastedEmail: file ? undefined : pastedEmail, title: title.trim() || undefined });
      onCreated(result);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "The investigation could not be created.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack narrow-page">
      <section className="intro-row">
        <div>
          <p className="section-kicker">Controlled intake</p>
          <h2>Open a new investigation</h2>
          <p>Bring one inert message into the workbench. Local parsing starts the case; external enrichment remains optional.</p>
        </div>
        <span className="safety-badge">Attachments stay inert</span>
      </section>

      <Panel className="intake-panel">
        <label className="field-label" htmlFor="case-title">Case title <span>Optional</span></label>
        <input id="case-title" className="text-input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Example: Suspicious invoice notice" />

        <div className="upload-grid">
          <label className={`dropzone ${file ? "has-file" : ""}`} htmlFor="eml-file">
            <input id="eml-file" type="file" accept=".eml,message/rfc822" onChange={(event) => setFile(event.target.files?.[0])} />
            <span className="dropzone-mark" aria-hidden="true">+</span>
            <strong>{file ? file.name : "Choose an .eml file"}</strong>
            <small>{file ? `${Math.ceil(file.size / 1024)} KB selected` : "RFC 5322 / MIME message"}</small>
          </label>
          <div className="or-divider" aria-hidden="true"><span>or</span></div>
          <div className="paste-panel">
            <label className="field-label" htmlFor="pasted-email">Paste email source <span>Fallback</span></label>
            <textarea id="pasted-email" value={pastedEmail} onChange={(event) => { setPastedEmail(event.target.value); setFile(undefined); }} placeholder="Paste the complete RFC 5322 message here..." rows={10} />
          </div>
        </div>

        <div className="intake-footer">
          <div className="boundary-note"><span aria-hidden="true">!</span><span>Do not paste live credentials or confidential messages.</span></div>
          <button className="button button-primary" disabled={!canSubmit || loading} onClick={submit}>{loading ? "Creating case..." : "Create investigation"}</button>
        </div>
        {error && <div className="error-banner" role="alert"><strong>Could not create investigation.</strong><span>{error}</span></div>}
      </Panel>
    </div>
  );
}

function InvestigationResults({ currentCase, onNew }: { currentCase: InvestigationCase | null; onNew: () => void }) {
  if (!currentCase) return <EmptyPage title="No investigation selected" body="Create or select a case before opening the results workspace." actionLabel="New investigation" onAction={onNew} />;
  const email = currentCase.email;
  return (
    <div className="page-stack">
      <section className="results-head">
        <div>
          <p className="section-kicker">Case {currentCase.id.slice(0, 8)}</p>
          <h2>{currentCase.title}</h2>
          <p className="muted-text">{currentCase.status} <span className="separator">/</span> Local analysis result</p>
        </div>
        <div className="result-actions">
          <span className="status-pill status-neutral">{currentCase.verdict || "INCONCLUSIVE"}</span>
          <button className="button button-secondary" onClick={() => exportReport(currentCase)}>Export report</button>
        </div>
      </section>

      <section className="summary-grid">
        <Panel className="summary-card summary-main"><p className="section-kicker">Threat summary</p><h3>{currentCase.summary || (currentCase.verdict === "INCONCLUSIVE" ? "Analysis is ready for review" : currentCase.verdict)}</h3><p className="muted-text">{currentCase.analysis?.explanation?.explanation || "Deterministic analysis result returned by the backend."}</p></Panel>
        <Panel className="summary-card score-card"><p className="section-kicker">Risk score</p><strong className="score-value">{typeof currentCase.risk_score === "number" ? currentCase.risk_score : "--"}</strong><span className="score-caption">{currentCase.severity || "Awaiting analysis"}</span></Panel>
        <Panel className="summary-card"><p className="section-kicker">Verdict</p><strong className="verdict-value">{currentCase.verdict || "INCONCLUSIVE"}</strong><span className="score-caption">Evidence-backed assessment</span></Panel>
      </section>

      <div className="results-grid">
        <Panel><SectionTitle eyebrow="Evidence" title="Findings" />{currentCase.analysis?.findings?.length ? <FindingList findings={currentCase.analysis.findings} /> : <EmptyState title="No findings available" body="The backend returned no deterministic findings." />}</Panel>
        <Panel><SectionTitle eyebrow="Message" title="Email preview" />{email ? <EmailPreview email={email} /> : <EmptyState title="Parsed email unavailable" body="The API did not return email details for this case." />}</Panel>
        <Panel className="wide-panel"><SectionTitle eyebrow="Detection" title="Malicious element highlights" />{currentCase.analysis?.findings?.length ? <FindingList findings={currentCase.analysis.findings} compact /> : <EmptyState title="No malicious elements reported" body="The backend returned no deterministic findings." />}</Panel>
        <Panel><SectionTitle eyebrow="Headers" title="Header / authentication analysis" />{email ? <HeaderPreview email={email} /> : <EmptyState title="No header data" body="Header evidence has not been returned." />}</Panel>
        <Panel><SectionTitle eyebrow="Indicators" title="URL / domain analysis" />{email?.urls.length ? <IndicatorList items={email.urls.map((url) => `${url.host} - ${url.value}`)} /> : <EmptyState title="No URLs extracted" body="No URL indicators are available for this case." />}</Panel>
        <Panel><SectionTitle eyebrow="Artifacts" title="Attachment analysis" />{email?.attachments.length ? <IndicatorList items={email.attachments.map((item) => `${item.filename} - ${item.sha256.slice(0, 12)}...`)} /> : <EmptyState title="No attachments" body="No attachment metadata is available." />}</Panel>
        <Panel><SectionTitle eyebrow="Infrastructure" title="Infrastructure intelligence" />{currentCase.analysis?.infrastructure ? <pre className="data-preview">{JSON.stringify(currentCase.analysis.infrastructure, null, 2)}</pre> : <EmptyState title="No enrichment data" body="Approximate infrastructure context is unavailable." />}</Panel>
        <Panel><SectionTitle eyebrow="Relationships" title="Related cases" />{currentCase.analysis?.relationships?.length ? <IndicatorList items={currentCase.analysis.relationships.map((item) => `${item.relationship_type} - ${item.target_case_id || item.source_case_id}`)} /> : <EmptyState title="No related cases" body="No stored relationships connect to this case." actionLabel="View related cases" onAction={() => navigate("related")} />}</Panel>
        <Panel className="wide-panel"><SectionTitle eyebrow="Campaign context" title="Campaign relationship graph" />{currentCase.analysis?.campaign ? <CampaignCard campaign={currentCase.analysis.campaign} /> : <GraphEmpty />}</Panel>
        <Panel><SectionTitle eyebrow="Explanation" title="Analyst explanation" />{currentCase.analysis?.explanation ? <div className="explanation-copy"><p>{currentCase.analysis.explanation.explanation}</p><small>{currentCase.analysis.explanation.source} / {currentCase.analysis.explanation.status}</small></div> : <EmptyState title="Explanation unavailable" body="The deterministic fallback was not returned." />}</Panel>
        <Panel><SectionTitle eyebrow="Response" title="Recommended response" />{currentCase.analysis?.recommendations?.length ? <IndicatorList items={currentCase.analysis.recommendations.map((item) => `${item.priority}: ${item.action} - ${item.reason}`)} /> : <EmptyState title="No recommendations" body="No evidence-backed recommendations were returned." />}</Panel>
      </div>
    </div>
  );
}

function RelatedCases({ currentCase }: { currentCase: InvestigationCase | null }) {
  const [data, setData] = useState<RelatedCasesResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { if (currentCase) fetchRelationships(currentCase.id).then(setData).catch((reason) => setError(reason instanceof Error ? reason.message : "API unavailable.")); }, [currentCase]);
  if (!currentCase) return <EmptyPage title="No investigation selected" body="Related cases are scoped to an investigation." actionLabel="Open an investigation" onAction={() => navigate("new")} />;
  return <div className="page-stack"><section className="intro-row"><div><p className="section-kicker">Correlation</p><h2>Related cases</h2><p>Shared indicators are evidence of a relationship, not proof of a common actor.</p></div><span className="safety-badge">Likely related</span></section><Panel>{error ? <UnavailableState message={error} /> : !data ? <LoadingState label="Loading relationships..." /> : data.related_cases.length === 0 ? <EmptyState title="No related cases" body="No stored relationships connect to this case yet." /> : <div className="relationship-list">{data.related_cases.map((item) => <div className="relationship-row" key={item.id}><div><strong>{item.id}</strong><small>{item.relationship_count} stored relationship{item.relationship_count === 1 ? "" : "s"}</small></div><span className="status-pill status-neutral">Likely related</span></div>)}</div>}</Panel></div>;
}

function CampaignView({ currentCase }: { currentCase: InvestigationCase | null }) {
  const [data, setData] = useState<CampaignResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { if (currentCase) fetchCampaigns(currentCase.id).then(setData).catch((reason) => setError(reason instanceof Error ? reason.message : "API unavailable.")); }, [currentCase]);
  if (!currentCase) return <EmptyPage title="No campaign context" body="Select an investigation to inspect possible campaign relationships." actionLabel="Open an investigation" onAction={() => navigate("new")} />;
  return <div className="page-stack"><section className="intro-row"><div><p className="section-kicker">Campaign intelligence</p><h2>Possible campaign view</h2><p>Connected components are grouped from deterministic shared indicators.</p></div><span className="safety-badge">Confidence-labeled</span></section><Panel>{error ? <UnavailableState message={error} /> : !data ? <LoadingState label="Loading campaign context..." /> : data.campaigns.length === 0 ? <EmptyState title="No possible campaign" body="This case is not currently connected to a stored strong-indicator component." /> : data.campaigns.map((campaign) => <CampaignCard campaign={campaign} key={campaign.id} />)}</Panel></div>;
}

function CaseDetails({ currentCase }: { currentCase: InvestigationCase | null }) {
  if (!currentCase) return <EmptyPage title="No case details" body="Create an investigation to inspect its case record." actionLabel="New investigation" onAction={() => navigate("new")} />;
  return <div className="page-stack"><section className="intro-row"><div><p className="section-kicker">Evidence record</p><h2>Case details</h2><p>Stored case metadata and parsed message references.</p></div><span className="status-pill status-neutral">{currentCase.status}</span></section><Panel><div className="detail-table"><Detail label="Case ID" value={currentCase.id} /><Detail label="Title" value={currentCase.title} /><Detail label="Status" value={currentCase.status} /><Detail label="Risk score" value={String(currentCase.risk_score ?? "--")} /><Detail label="Severity" value={currentCase.severity || "Awaiting analysis"} /><Detail label="Verdict" value={currentCase.verdict || "INCONCLUSIVE"} /><Detail label="Message ID" value={currentCase.email?.message_id || "Not returned"} /><Detail label="Raw content" value="Stored reference is protected by the API" /></div></Panel></div>;
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) { return <section className={`panel ${className}`}>{children}</section>; }
function SectionTitle({ eyebrow, title, action }: { eyebrow: string; title: string; action?: string }) { return <div className="section-title"><div><p className="section-kicker">{eyebrow}</p><h3>{title}</h3></div>{action && <span className="panel-action">{action}</span>}</div>; }
function EmptyState({ title, body, actionLabel, onAction }: { title: string; body: string; actionLabel?: string; onAction?: () => void }) { return <div className="empty-state"><div className="empty-mark" aria-hidden="true">/</div><strong>{title}</strong><p>{body}</p>{actionLabel && onAction && <button className="button button-secondary" onClick={onAction}>{actionLabel}</button>}</div>; }
function EmptyPage({ title, body, actionLabel, onAction }: { title: string; body: string; actionLabel: string; onAction: () => void }) { return <div className="page-stack"><Panel><EmptyState title={title} body={body} actionLabel={actionLabel} onAction={onAction} /></Panel></div>; }
function UnavailableState({ message }: { message: string }) { return <div className="unavailable-state"><strong>API unavailable</strong><p>{message}</p><span>Local UI state is preserved. Retry when the service is available.</span></div>; }
function LoadingState({ label }: { label: string }) { return <div className="loading-state"><span className="loader" aria-hidden="true" />{label}</div>; }
function Readiness({ label, state, muted = false }: { label: string; state: string; muted?: boolean }) { return <div className="readiness-row"><span className={`readiness-icon ${muted ? "is-muted" : ""}`} aria-hidden="true">{muted ? "-" : "+"}</span><span>{label}</span><strong>{state}</strong></div>; }
function Lane({ number, title, copy }: { number: string; title: string; copy: string }) { return <div className="lane"><span>{number}</span><strong>{title}</strong><small>{copy}</small></div>; }
function EmailPreview({ email }: { email: NonNullable<InvestigationCase["email"]> }) { return <div className="email-preview"><div><span>From</span><strong>{email.from || "Unknown"}</strong></div><div><span>To</span><strong>{email.to.join(", ") || "Unknown"}</strong></div><div><span>Subject</span><strong>{email.subject || "No subject"}</strong></div><div className="email-body"><span>Body</span><p>{email.body_text || "No plain-text body returned."}</p></div></div>; }
function HeaderPreview({ email }: { email: NonNullable<InvestigationCase["email"]> }) { return <div className="header-list">{email.received.length ? email.received.map((value) => <div key={value}><span>Received</span><code>{value}</code></div>) : <EmptyState title="No Received headers" body="No routing headers were returned." />}{email.authentication_results.map((value) => <div key={value}><span>Auth result</span><code>{value}</code></div>)}</div>; }
function IndicatorList({ items }: { items: string[] }) { return <ul className="indicator-list">{items.map((item) => <li key={item}><span className="list-dot" aria-hidden="true" />{item}</li>)}</ul>; }
function FindingList({ findings, compact = false }: { findings: NonNullable<InvestigationCase["analysis"]>["findings"]; compact?: boolean }) { return <div className="finding-list">{findings.map((finding) => <div className="finding-row" key={`${finding.rule_id}-${finding.title}`}><div><strong>{finding.title}</strong><small>{finding.rule_id} / {finding.category} / {finding.severity}</small>{!compact && <p>{finding.description}</p>}</div><span className="score-caption">+{finding.score_contribution}</span></div>)}</div>; }
function GraphEmpty() { return <div className="graph-empty"><div className="graph-node graph-node-main">Current case</div><div className="graph-line" /><div className="graph-node">No related nodes</div><p>Relationship edges appear when shared indicators are stored.</p></div>; }
function CampaignCard({ campaign }: { campaign: Campaign }) { return <div className="campaign-card"><div><span className="section-kicker">{campaign.wording}</span><h3>{campaign.name}</h3><p>{campaign.case_ids.length} connected cases with confidence {Math.round(campaign.confidence * 100)}%.</p></div><div className="campaign-graph">{campaign.case_ids.map((id, index) => <div className="graph-chip" key={id}><span className={index === 0 ? "chip-dot chip-dot-active" : "chip-dot"} />{id}</div>)}</div></div>; }
function Detail({ label, value }: { label: string; value: string }) { return <div className="detail-row"><span>{label}</span><strong>{value}</strong></div>; }
async function exportReport(caseData: InvestigationCase) { try { const report = await createReport(caseData.id, "pdf"); window.open(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"}/cases/${caseData.id}/report/${report.id}`, "_blank", "noopener,noreferrer"); } catch { /* The results screen remains usable when report generation is unavailable. */ } }
