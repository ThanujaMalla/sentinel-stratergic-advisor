import React, { useState, useEffect, useRef } from "react";
import { DashboardData } from "./types.ts";
import { X, ExternalLink, Loader2, Download, FileText, Printer, Shield, Globe, Award, AlertTriangle, TrendingUp, Users, BookOpen } from "lucide-react";

export default function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [activePhase, setActivePhase] = useState('phase-overview');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [transcriptQuery, setTranscriptQuery] = useState('');
  const [isSearchingTranscripts, setIsSearchingTranscripts] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [viewMode, setViewMode] = useState<'dashboard' | 'report'>('dashboard');
  const reportRef = useRef<HTMLDivElement>(null);

  // Handle URL parameters for automatic search and printing
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    const print = params.get('print');
    
    if (q && !data && !loading && !error) {
      setQuery(q);
      const triggerSearch = async () => {
        setLoading(true);
        setError(null);
        try {
          const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
          if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.error || "Failed to fetch raw data");
          }
          const synthesizedData = await res.json();
          setData(synthesizedData);
          if (print === 'true') {
            setActiveTab('report');
          }
        } catch (err: any) {
          console.error("Auto-search error:", err);
          setError(err.message || "Automatic search failed.");
        } finally {
          setLoading(false);
        }
      };
      triggerSearch();
    }
  }, []);


  useEffect(() => {
  if (!isGeneratingReport) {
    setPdfLoadingStep(0);
    return;
  }

  const steps = [
    "Collecting archive records...",
    "Building strategic sections...",
    "Rendering PDF layout...",
    "Finalizing download..."
  ];

  const interval = window.setInterval(() => {
    setPdfLoadingStep((prev) => (prev + 1) % steps.length);
  }, 1200);

  return () => window.clearInterval(interval);
}, [isGeneratingReport]);


  // Auto-trigger print if requested via URL
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const print = params.get('print');
    if (print === 'true' && data && activeTab === 'report' && !isGeneratingReport) {
      handleExportPDF();
      // Clean up URL
      const newUrl = window.location.origin + window.location.pathname + window.location.search.replace(/[?&]print=true/, '');
      window.history.replaceState({}, '', newUrl);
    }
  }, [data, activeTab]);

  const handleTranscriptSearch = async () => {
    if (!transcriptQuery || !data) return;
    setIsSearchingTranscripts(true);
    try {
      const res = await fetch(`/api/transcripts?subject=${encodeURIComponent(data.subject)}&query=${encodeURIComponent(transcriptQuery)}`);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Failed to fetch broadcast transcripts");
      }
      const results = await res.json();
      // For now, we just prepend these to the existing appearances or show them separately
      // In a real app, we might want to re-run the Gemini synthesis on these new results
      // But for this prototype, we'll just alert or show them
      console.log("Transcript Search Results:", results);
      // We can update the data state if we want to show them in the UI
      const newAppearances = results.map(r => ({
        date: r.date || 'Unknown',
        network: r.network || 'Unknown',
        program: 'Recovered Segment',
        title: r.title || 'Untitled',
        summary: r.snippet || 'No summary available.',
        url: r.url
      }));
      
      setData({
        ...data,
        broadcastAppearances: [...newAppearances, ...data.broadcastAppearances]
      });
      setTranscriptQuery('');
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearchingTranscripts(false);
    }
  };
  const [drilldownArticles, setDrilldownArticles] = useState<any[]>([]);
  const [drilldownLoading, setDrilldownLoading] = useState(false);
  const [pdfLoadingStep, setPdfLoadingStep] = useState(0);

  const handleBack = () => {
    setData(null);
    setQuery("");
    setActiveTab('overview');
    setActivePhase('phase-overview');
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const handleDrilldown = async (category: string) => {
    if (!data) return;
    setSelectedCategory(category);
    setDrilldownLoading(true);
    try {
      const res = await fetch(`/api/drilldown?subject=${encodeURIComponent(data.subject)}&category=${encodeURIComponent(category)}`);
      const articles = await res.json();
      setDrilldownArticles(articles);
    } catch (err) {
      console.error("Drilldown fetch error:", err);
    } finally {
      setDrilldownLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!data) return;
    
    // Exporting the Media Archive as CSV
    const archive = data.fullArchive || [];
    if (archive.length === 0) {
      alert("No archive data available to export.");
      return;
    }

    const headers = ["ID", "Date", "Source", "Headline", "Summary", "Category", "Confidence"];
    const rows = archive.map(ev => [
      ev.id,
      ev.date,
      ev.source,
      `"${ev.headline.replace(/"/g, '""')}"`,
      `"${ev.summary.replace(/"/g, '""')}"`,
      ev.category,
      ev.confidence
    ]);

    const csvContent = [headers, ...rows].map(e => e.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `Sentinel_Archive_${data.subject.replace(/\s+/g, '_')}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportPDF = async () => {
    if (!data?.subject) return;
    setIsGeneratingReport(true);

    try {
      const res = await fetch(`/api/export/pdf?subject=${encodeURIComponent(data.subject)}`);
      if (!res.ok) {
        let message = "Failed to generate PDF from backend.";
        try {
          const errData = await res.json();
          message = errData.detail || errData.error || message;
        } catch {
          // keep fallback message
        }
        throw new Error(message);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Sentinel_Consolidated_Report_${data.subject.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error("PDF export failed:", err);
      alert(err?.message || "Failed to generate PDF. Please try again.");
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const executePrint = () => {
    try {
      // For the AI Studio environment, window.print() is often the most reliable 
      // if the user has opened the app in a new tab. 
      // We'll trigger it and the user can use the browser's print dialog.
      window.print();
    } catch (e) {
      console.error("Print failed:", e);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || "Failed to fetch dashboard data");
      }
      const synthesizedData = await res.json();
      setData(synthesizedData);
    } catch (err: any) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const sendPrompt = (text: string) => {
    console.log("Prompt sent:", text);
    // In a real app, this would trigger an action
  };

  const [scanStep, setScanStep] = React.useState(0);
  const scanNodes = [
    "INITIALIZING SENTINEL STRATEGIC ADVISOR...",
    "ANALYZING FACTIVA MEDIA TRENDS...",
    "MAPPING LEXISNEXIS LEGAL LANDSCAPE...",
    "EVALUATING PACER JUDICIAL PRECEDENTS...",
    "AUDITING NYC CAMPAIGN FINANCE BOARD DATA...",
    "PROCESSING EL DIARIO MULTICULTURAL INSIGHTS...",
    "SYNTHESIZING CROSS-NODE SENTIMENT...",
    "EXTRACTING DIGITAL FOOTPRINT SIGNAL...",
    "GENERATING STRATEGIC POSITIONING...",
    "FINALIZING PLAYBOOK..."
  ];

  React.useEffect(() => {
    let interval: any;
    if (loading) {
      setScanStep(0);
      interval = setInterval(() => {
        setScanStep(prev => (prev + 1) % scanNodes.length);
      }, 800);
    }
    return () => clearInterval(interval);
  }, [loading]);

  if (!data) {
    return (
      <div className={`psi theme-${theme}`} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <div style={{ position: 'absolute', top: '20px', right: '20px' }}>
          <button 
            onClick={toggleTheme}
            style={{ padding: '8px 12px', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: '10px', cursor: 'pointer', textTransform: 'uppercase' }}
          >
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
        </div>
        <div className="scan-container" style={{ width: '100%', maxWidth: '600px', padding: '40px', border: '1px solid var(--border-color)', background: 'var(--bg-panel)', position: 'relative', overflow: 'hidden' }}>
          <div className="scan-line"></div>
          <div style={{ marginBottom: '30px', fontFamily: 'IBM Plex Mono', color: 'var(--text-accent)', fontSize: '20px', letterSpacing: '0.2em', textAlign: 'center', fontWeight: 'bold' }}>
            SENTINEL STRATEGIC ADVISOR v5.0
          </div>
          
          {!loading ? (
            <>
              <div style={{ color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: '11px', marginBottom: '20px', textAlign: 'center', lineHeight: '1.6' }}>
                SYSTEM READY. STANDING BY FOR CANDIDATE INITIALIZATION.<br/>
                STRATEGIC NODES: FACTIVA | LEXISNEXIS | PACER | NYCCFB | EL DIARIO
              </div>
              <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0', width: '100%' }}>
                <input 
                  type="text" 
                  value={query} 
                  onChange={e => setQuery(e.target.value)} 
                  placeholder="ENTER CANDIDATE NAME..."
                  style={{ flex: 1, padding: '14px 20px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', color: 'var(--text-accent)', fontFamily: 'IBM Plex Mono', outline: 'none', fontSize: '14px' }}
                />
                <button type="submit" disabled={loading} style={{ padding: '0 30px', background: 'var(--text-accent)', color: 'var(--bg-input)', border: 'none', cursor: 'pointer', fontFamily: 'IBM Plex Mono', fontWeight: 'bold', fontSize: '12px', letterSpacing: '0.1em' }}>
                  SEARCH
                </button>
              </form>
            </>
          ) : (
            <div style={{ padding: '20px 0' }}>
              <div className="terminal-loader">
                <div className="terminal-header">
                  <span className="dot red"></span>
                  <span className="dot yellow"></span>
                  <span className="dot green"></span>
                  <span className="terminal-title">STRATEGIC_ANALYSIS_IN_PROGRESS</span>
                </div>
                <div className="terminal-body">
                  <div className="terminal-text">
                    <span className="prompt">{'>'}</span> {scanNodes[scanStep]}
                  </div>
                  <div className="progress-bar-container">
                    <div className="progress-bar" style={{ width: `${((scanStep + 1) / scanNodes.length) * 100}%` }}></div>
                  </div>
                  <div className="terminal-subtext">
                    NODE_ID: {Math.random().toString(16).substring(2, 10).toUpperCase()}<br/>
                    LATENCY: {Math.floor(Math.random() * 50) + 10}ms<br/>
                    ENCRYPTION: AES-256-GCM
                  </div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div style={{ marginTop: '20px', fontFamily: 'IBM Plex Mono', color: '#ef4444', fontSize: '11px', textAlign: 'center', border: '1px solid rgba(239,68,68,0.3)', padding: '10px', background: 'rgba(239,68,68,0.05)' }}>
              CRITICAL_FAILURE: {error.toUpperCase()}
            </div>
          )}
        </div>
        <div style={{ marginTop: '20px', fontFamily: 'IBM Plex Mono', color: 'var(--text-dim)', fontSize: '9px', letterSpacing: '0.3em' }}>
          PROPRIETARY INTELLIGENCE SYSTEM // LEVEL 5 CLEARANCE REQUIRED
        </div>
      </div>
    );
  }

  return (
    <div className={`psi theme-${theme}`}>
      <div className="psi-topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <button 
            onClick={handleBack}
            className="psi-btn-secondary"
          >
            ← Back
          </button>
          <div className="psi-topbar-title">SENTINEL STRATEGIC INTELLIGENCE &nbsp;/&nbsp; CANDIDATE: {data.subject.toUpperCase()}</div>
        </div>
        <div className="psi-topbar-meta">
          <button 
            onClick={() => {
              console.log("Brief button clicked");
              handleExportPDF();
            }}
            className="psi-btn-secondary no-print"
            title="Export Strategic Brief (PDF)"
            style={{ 
              position: 'relative', 
              zIndex: 101, 
              cursor: 'pointer',
              padding: '6px 12px',
              background: 'var(--text-accent)',
              color: 'var(--bg-panel)',
              border: 'none',
              fontWeight: 'bold'
            }}
          >
            <Printer size={14} style={{ marginRight: '6px' }} /> EXPORT BRIEF (PDF)
          </button>
          <button 
            onClick={handleExportCSV}
            className="psi-btn-secondary no-print"
            title="Export Data Dump (CSV)"
          >
            <Download size={12} /> Data
          </button>
          <button 
            onClick={toggleTheme}
            className="no-print"
            style={{ padding: '4px 8px', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono', fontSize: '10px', cursor: 'pointer', textTransform: 'uppercase' }}
          >
            {theme === 'dark' ? 'Light' : 'Dark'}
          </button>
          <span className="psi-status-text"><span className="psi-status-dot"></span>STRATEGIC MONITORING ACTIVE</span>
          <span className="psi-status-text">{data.eventCount} DATA POINTS &nbsp;|&nbsp; 1989–2026</span>
          <span className="psi-classify">STRATEGIC PLAYBOOK</span>
        </div>
      </div>

      <div className="psi-nav">
        <div className={`psi-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Strategic Overview</div>
        <div className={`psi-tab ${activeTab === 'sentiment' ? 'active' : ''}`} onClick={() => setActiveTab('sentiment')}>Messaging Sentiment</div>
        <div className={`psi-tab ${activeTab === 'fundraising' ? 'active' : ''}`} onClick={() => setActiveTab('fundraising')}>Financial Strategy</div>
        <div className={`psi-tab ${activeTab === 'campaign' ? 'active' : ''}`} onClick={() => setActiveTab('campaign')}>Campaign Playbook</div>
        <div className={`psi-tab ${activeTab === 'network' ? 'active' : ''}`} onClick={() => setActiveTab('network')}>Coalition Network</div>
        <div className={`psi-tab ${activeTab === 'risk' ? 'active' : ''}`} onClick={() => setActiveTab('risk')}>Vulnerability Assessment</div>
        {data.fullArchive && (
          <div className={`psi-tab ${activeTab === 'archive' ? 'active' : ''}`} onClick={() => setActiveTab('archive')}>Media Archive</div>
        )}
        <div className={`psi-tab ${activeTab === 'report' ? 'active' : ''}`} onClick={() => setActiveTab('report')}>Professional Report</div>
      </div>

      <div className="psi-body">
        <div className="psi-sidebar">
          <div className="psi-section-label">Phase Analysis</div>
          <div className={`psi-entity-item ${activePhase === 'phase-overview' ? 'active' : ''}`} onClick={() => setActivePhase('phase-overview')}>
            <div style={{float: 'right', fontSize: '10px', fontFamily: 'monospace'}} className="score-high">▲ ACTIVE</div>
            <div className="psi-entity-name">Full Career Arc</div>
            <div className="psi-entity-role">1989 → 2026</div>
          </div>
          {data.phases.map((phase) => (
            <div key={phase.id} className={`psi-entity-item ${activePhase === phase.id ? 'active' : ''}`} onClick={() => setActivePhase(phase.id)}>
              <span className={`psi-entity-score ${phase.scoreClass}`}>{phase.score}</span>
              <div className="psi-entity-name">{phase.title}</div>
              <div className="psi-entity-role">{phase.years}</div>
            </div>
          ))}

          <div className="psi-section-label" style={{marginTop: '8px'}}>Key Orgs</div>
          {data.orgs.map((org, i) => (
            <div key={i} className="psi-entity-item">
              <span className="psi-entity-score" style={{color: org.dot}}>●</span>
              <div className="psi-entity-name">{org.name}</div>
              <div className="psi-entity-role">{org.role}</div>
            </div>
          ))}
        </div>

        <div className="psi-main">

          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div id="tab-overview" className="view-panel active">
              <div className="psi-metrics">
                <div className="psi-metric">
                  <div className="psi-metric-val">{data.eventCount}</div>
                  <div className="psi-metric-label">Verified Events</div>
                  <div className="psi-metric-delta delta-up">▲ 37yr span</div>
                </div>
                <div className="psi-metric">
                  <div className="psi-metric-val">{data.netSentiment}</div>
                  <div className="psi-metric-label">Net Sentiment Score</div>
                  <div className="psi-metric-delta delta-up">▲ Positive lean</div>
                </div>
                <div className="psi-metric">
                  <div className="psi-metric-val">{data.totalFundraising}</div>
                  <div className="psi-metric-label">Documented Fundraising</div>
                  <div className="psi-metric-delta delta-up">Pioneer-level contributor</div>
                </div>
                <div className="psi-metric">
                  <div className="psi-metric-val">{data.electoralResult}</div>
                  <div className="psi-metric-label">2021 Primary Vote Share</div>
                  <div className="psi-metric-delta delta-down">▼ Lost to Sliwa</div>
                </div>
              </div>

              <div className="psi-grid-2">
                <div className="psi-panel">
                  <div className="psi-panel-header">
                    <span className="psi-panel-title">Career Phase Sequence</span>
                  </div>
                  <div className="psi-panel-body">
                    {data.phases.map((phase, i) => (
                      <div key={phase.id} className={`psi-phase-block ph${i + 1}`}>
                        <div className="psi-phase-title">{phase.title.split('—')[1]?.trim() || phase.title}</div>
                        <div className="psi-phase-years">{phase.years.split('·')[0].trim()} · Sentiment {phase.score}</div>
                        <div className="psi-phase-desc">{phase.summary}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="psi-panel">
                  <div className="psi-panel-header">
                    <span className="psi-panel-title">Coverage Volume by Theme</span>
                  </div>
                  <div className="psi-panel-body">
                    {data.coverageVolume.map((item, i) => (
                      <div 
                        key={i} 
                        className="psi-bar-row" 
                        onClick={() => handleDrilldown(item.label)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className="psi-bar-label">{item.label}</div>
                        <div className="psi-bar-track">
                          <div className="psi-bar-fill" style={{width: `${item.pct}%`, background: item.color}}></div>
                        </div>
                        <div className="psi-bar-val">{item.count}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="psi-panel">
                <div className="psi-panel-header"><span className="psi-panel-title">Peak Coverage Events — Intelligence Timeline</span></div>
                <div className="psi-panel-body psi-timeline">
                  {data.timeline.map((item, i) => (
                    <div key={i} className="psi-tl-item">
                      <div className="psi-tl-marker" style={{background: item.color}}></div>
                      <div className="psi-tl-content">
                        <div className="psi-tl-date">{item.date}</div>
                        <div className="psi-tl-text">
                          {item.url ? (
                            <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ color: '#4a9eff', textDecoration: 'none', borderBottom: '1px dotted #4a9eff' }}>{item.text}</a>
                          ) : (
                            item.text
                          )}
                        </div>
                        <div className="psi-tl-tags">
                          {item.tags.map((tag, j) => (
                            <span key={j} className={`psi-tag ${tag.cls}`}>{tag.label}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{marginTop: '8px'}}>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Give me a deep analysis of Fernando Mateo\'s media strategy across all six phases of his career')}>↗ Deep career analysis</span>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('What are the most significant gaps in Fernando Mateo\'s media archive and how should they be filled?')}>↗ Archive gap analysis</span>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Build a comprehensive entity relationship map for Fernando Mateo including all political, business, and media connections')}>↗ Full entity map</span>
              </div>
            </div>
          )}

          {/* SENTIMENT TAB */}
          {activeTab === 'sentiment' && (
            <div id="tab-sentiment" className="view-panel active">
              <div className="psi-sentiment-layout">
                <div className="psi-sentiment-sidebar">
                  <div className="psi-section-label">Phase Analysis</div>
                  {data.phases.map((phase) => (
                    <div 
                      key={phase.id} 
                      className={`psi-phase-list-item ${activePhase === phase.id ? 'active' : ''}`}
                      onClick={() => setActivePhase(phase.id)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div className="psi-entity-name">{phase.title}</div>
                        {activePhase === phase.id ? (
                          <span style={{ fontSize: '9px', color: '#22c55e', fontWeight: 'bold' }}>▲ ACTIVE</span>
                        ) : (
                          <span className="psi-entity-score">{phase.score}</span>
                        )}
                      </div>
                      <div className="psi-entity-role">{phase.years}</div>
                    </div>
                  ))}

                  <div className="psi-section-label" style={{ marginTop: '20px' }}>Key Orgs</div>
                  {data.orgs.map((org, i) => (
                    <div key={i} className="psi-entity-item">
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <div className="psi-entity-name">{org.name}</div>
                        <div className="psi-status-dot" style={{ background: org.dot, animation: 'none' }}></div>
                      </div>
                      <div className="psi-entity-role">{org.role}</div>
                    </div>
                  ))}
                </div>

                <div className="psi-sentiment-main">
                  <div className="psi-metrics" style={{ gridTemplateColumns: '1fr 1fr' }}>
                    <div className="psi-metric">
                      <div className="psi-metric-val" style={{color: '#22c55e'}}>{data.peakPositive.score}</div>
                      <div className="psi-metric-label">Peak Positive Score</div>
                      <div className="psi-metric-delta">{data.peakPositive.date} — {data.peakPositive.event}</div>
                    </div>
                    <div className="psi-metric">
                      <div className="psi-metric-val" style={{color: '#ef4444'}}>{data.peakNegative.score}</div>
                      <div className="psi-metric-label">Peak Negative Score</div>
                      <div className="psi-metric-delta">{data.peakNegative.date} — {data.peakNegative.event}</div>
                    </div>
                  </div>

                  <div className="psi-panel">
                    <div className="psi-panel-header"><span className="psi-panel-title">Sentiment by Phase</span></div>
                    <div className="psi-panel-body">
                      {data.phases.map((phase, i) => (
                        <div key={phase.id} style={{marginBottom: i === data.phases.length - 1 ? '0' : '20px'}}>
                          <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '6px'}}>
                            <span style={{fontSize: '12px', color: '#d1d5db', fontWeight: '500'}}>{phase.title}</span>
                            <span style={{fontFamily: 'monospace', fontSize: '12px', color: phase.color, fontWeight: 'bold'}}>{phase.score}</span>
                          </div>
                          <div className="psi-sent-bar" style={{ height: '10px' }}>
                            <div className="sb-pos" style={{width: `${phase.sentPos}%`}}></div>
                            <div className="sb-neg" style={{width: `${phase.sentNeg}%`}}></div>
                            <div className="sb-neu" style={{width: `${phase.sentNeu}%`}}></div>
                          </div>
                          <div className="psi-sent-labels" style={{ marginTop: '6px' }}>
                            <span>{phase.sentPos}% positive</span>
                            <span>{phase.sentNeg}% neg</span>
                            <span>{phase.sentNeu}% neutral</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="psi-panel">
                    <div className="psi-panel-header"><span className="psi-panel-title">Key Sentiment Inflection Events</span></div>
                    <div className="psi-panel-body">
                      <table className="psi-table">
                        <thead>
                          <tr><th>Event</th><th>Date</th><th>Shift</th><th>Driver</th></tr>
                        </thead>
                        <tbody>
                          {data.inflections.map((inf, i) => (
                            <tr key={i}>
                              <td>{inf.event}</td>
                              <td style={{fontFamily: 'monospace'}}>{inf.date}</td>
                              <td style={{fontFamily: 'monospace', color: inf.shiftColor}}>{inf.shift}</td>
                              <td>{inf.driver}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{marginTop: '8px'}}>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Perform a deep sentiment analysis of Fernando Mateo\'s media coverage from the racial profiling controversy in 2010 — what was the long-term reputational impact?')}>↗ 2010 controversy deep dive</span>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Compare Fernando Mateo\'s sentiment trajectory to other NYC civic figures who made mayoral runs — what patterns emerge?')}>↗ Comparative sentiment analysis</span>
              </div>
            </div>
          )}

          {/* FUNDRAISING TAB */}
          {activeTab === 'fundraising' && (
            <div id="tab-fundraising" className="view-panel active">
              <div className="psi-metrics">
                <div className="psi-metric">
                  <div className="psi-metric-val" style={{color: '#4a9eff'}}>{data.totalFundraising}</div>
                  <div className="psi-metric-label">Total Documented Raised</div>
                  <div className="psi-metric-delta">Federal + state verified</div>
                </div>
                <div className="psi-metric">
                  <div className="psi-metric-val">$100K+</div>
                  <div className="psi-metric-label">Bush-Cheney '04 Pioneer</div>
                  <div className="psi-metric-delta">Official FEC record</div>
                </div>
                <div className="psi-metric">
                  <div className="psi-metric-val">$400K</div>
                  <div className="psi-metric-label">Pataki Re-election</div>
                  <div className="psi-metric-delta">"Fiesta Pataki" 2002</div>
                </div>
                <div className="psi-metric">
                  <div className="psi-metric-val" style={{color: '#ef4444'}}>$18.8K</div>
                  <div className="psi-metric-label">Illegal Straw Donation</div>
                  <div className="psi-metric-delta">De Blasio 2016 — admitted</div>
                </div>
              </div>

              <div className="psi-grid-2">
                <div className="psi-panel">
                  <div className="psi-panel-header"><span className="psi-panel-title">Fundraising Event Log</span></div>
                  <div className="psi-panel-body">
                    <table className="psi-table">
                      <thead>
                        <tr><th>Year</th><th>Candidate / Cause</th><th>Amount</th><th>Method</th></tr>
                      </thead>
                      <tbody>
                        {data.fundraisingLog.map((log, i) => (
                          <tr key={i}>
                            <td>{log.year}</td>
                            <td>{log.candidate}</td>
                            <td style={{fontFamily: 'monospace', color: log.amountColor}}>{log.amount}</td>
                            <td>{log.method}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="psi-panel">
                  <div className="psi-panel-header"><span className="psi-panel-title">Fundraising Intelligence Assessment</span></div>
                  <div className="psi-panel-body">
                    {data.fundAssessments.map((item, i) => (
                      <div key={i} className="psi-strategy-card">
                        <div className="psi-strategy-title">{item.title} <span className={`psi-strategy-priority ${item.priCls}`}>{item.priority}</span></div>
                        <div className="psi-strategy-body">{item.body}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="psi-panel">
                <div className="psi-panel-header">
                  <span className="psi-panel-title">Campaign Finance Deep Dive — NYC CFB Records</span>
                </div>
                <div className="psi-panel-body">
                  <div style={{ marginBottom: '15px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono' }}>
                    REPORTED INDIVIDUAL CONTRIBUTIONS BY {data.subject.toUpperCase()} TO NYC CANDIDATES
                  </div>
                  <table className="psi-table">
                    <thead>
                      <tr><th>Year</th><th>Recipient Candidate</th><th>Office Sought</th><th>Amount</th></tr>
                    </thead>
                    <tbody>
                      {data.contributions && data.contributions.length > 0 ? (
                        data.contributions.map((c, i) => (
                          <tr key={i}>
                            <td style={{ fontFamily: 'monospace' }}>{c.year}</td>
                            <td>{c.recipient}</td>
                            <td>{c.office}</td>
                            <td style={{ fontFamily: 'monospace', color: 'var(--text-accent)' }}>{c.amount}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '20px' }}>
                            NO INDIVIDUAL CONTRIBUTIONS FOUND IN NYCCFB RECORDS FOR THIS CANDIDATE.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="psi-panel">
                <div className="psi-panel-header"><span className="psi-panel-title">Fundraising Capacity Model — Future Projections</span></div>
                <div className="psi-panel-body psi-grid-3">
                  {data.fundScenarios.map((item, i) => (
                    <div key={i} className="psi-strategy-card">
                      <div className="psi-strategy-title">{item.title}</div>
                      <div className="psi-strategy-body" style={{color: '#9ca3af'}}>
                        {item.body} Estimated: <span style={{color: '#4a9eff', fontFamily: 'monospace'}}>{item.range}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{marginTop: '8px'}}>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Design a compliant fundraising strategy for Fernando Mateo to support Andrew Cuomo\'s 2025 NYC mayoral campaign, leveraging his bodega and taxi networks')}>↗ Cuomo fundraising strategy</span>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('What are the legal guardrails Fernando Mateo must follow in bundled fundraising given his 2016 straw donor admission?')}>↗ Compliance framework</span>
              </div>
            </div>
          )}

          {/* CAMPAIGN STRATEGY TAB */}
          {activeTab === 'campaign' && (
            <div id="tab-campaign" className="view-panel active">
              <div className="psi-panel">
                <div className="psi-panel-header"><span className="psi-panel-title">2021 Mayoral Campaign — Post-Mortem</span></div>
                <div className="psi-panel-body">
                  <div className="psi-grid-3" style={{marginBottom: '14px'}}>
                    {data.campaignPostMortem.map((item, i) => (
                      <div key={i} className="psi-strategy-card">
                        <div className="psi-strategy-title">{item.title}</div>
                        <div className="psi-strategy-body">{item.body}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="psi-panel">
                <div className="psi-panel-header"><span className="psi-panel-title">Future Campaign Strategy Recommendations</span></div>
                <div className="psi-panel-body">
                  {data.campaignStrategies.map((item, i) => (
                    <div key={i} className={`psi-risk-item ${item.cls}`}>
                      <div className="psi-risk-label" style={{color: item.severityColor, fontSize: '9px', writingMode: 'vertical-rl', transform: 'rotate(180deg)', letterSpacing: '0.1em', padding: '0 4px'}}>PRIORITY {i+1}</div>
                      <div className="psi-risk-body">
                        <div className="psi-risk-title">{item.title}</div>
                        {item.body}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{marginTop: '8px'}}>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Design a full campaign strategy for Fernando Mateo to run for New York State Assembly or City Council in 2027, incorporating lessons from the 2021 mayoral loss')}>↗ 2027 down-ballot strategy</span>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('How should Fernando Mateo use his WABC radio show to build political influence over the next 18 months?')}>↗ Radio political playbook</span>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('What would a Bodega Alliance PAC look like structurally and legally, and how could it maximize political impact?')}>↗ PAC formation analysis</span>
              </div>
            </div>
          )}

          {/* NETWORK TAB */}
          {activeTab === 'network' && (
            <div id="tab-network" className="view-panel active">
              <div className="psi-panel">
                <div className="psi-panel-header"><span className="psi-panel-title">Political Network — Tier 1 (Direct Relationships)</span></div>
                <div className="psi-panel-body">
                  {data.networkTier1.map((item, i) => (
                    <div key={i} className="psi-network-item">
                      <div className="psi-network-dot" style={{background: item.dot}}></div>
                      <div style={{flex: 1}}>
                        <div className="psi-network-name">{item.name}</div>
                        <div className="psi-network-rel">{item.rel}</div>
                      </div>
                      <div className="psi-network-strength" style={{color: item.strengthColor}}>{item.strength}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="psi-grid-2">
                <div className="psi-panel">
                  <div className="psi-panel-header"><span className="psi-panel-title">Media Network</span></div>
                  <div className="psi-panel-body">
                    {data.mediaNetwork.map((item, i) => (
                      <div key={i} className="psi-network-item">
                        <div className="psi-network-dot" style={{background: item.dot}}></div>
                        <div style={{flex: 1}}><div className="psi-network-name">{item.name}</div><div className="psi-network-rel">{item.rel}</div></div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="psi-panel">
                  <div className="psi-panel-header"><span className="psi-panel-title">Community / Organizational Network</span></div>
                  <div className="psi-panel-body">
                    {data.communityNetwork.map((item, i) => (
                      <div key={i} className="psi-network-item">
                        <div className="psi-network-dot" style={{background: item.dot}}></div>
                        <div style={{flex: 1}}><div className="psi-network-name">{item.name}</div><div className="psi-network-rel">{item.rel}</div></div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div style={{marginTop: '8px'}}>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Map the full network of individuals connected to Fernando Mateo through the de Blasio fundraising scandal — Rechnitz, Reichberg, Astorino connections')}>↗ de Blasio network deep dive</span>
              </div>
            </div>
          )}

          {/* RISK TAB */}
          {activeTab === 'risk' && (
            <div id="tab-risk" className="view-panel active">
              <div className="psi-metrics">
                {data.riskMetrics.map((item, i) => (
                  <div key={i} className="psi-metric">
                    <div className="psi-metric-val" style={{color: item.valColor}}>{item.val}</div>
                    <div className="psi-metric-label">{item.label}</div>
                    <div className="psi-metric-delta">{item.delta}</div>
                  </div>
                ))}
              </div>

              <div className="psi-panel">
                <div className="psi-panel-header"><span className="psi-panel-title">Risk Register — All Identified Exposures</span></div>
                <div className="psi-panel-body">
                  {data.risks.map((item, i) => (
                    <div key={i} className={`psi-risk-item ${item.cls}`}>
                      <div className="psi-risk-label" style={{color: item.severityColor, writingMode: 'vertical-rl', transform: 'rotate(180deg)', fontSize: '9px', letterSpacing: '0.1em', padding: '0 4px'}}>{item.severity}</div>
                      <div className="psi-risk-body">
                        <div className="psi-risk-title">{item.title}</div>
                        {item.body}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="psi-panel">
                <div className="psi-panel-header">
                  <span className="psi-panel-title">Court Record Search — PACER / NYSCEF / NYSFTD Litigation</span>
                </div>
                <div className="psi-panel-body">
                  <div style={{ marginBottom: '15px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono' }}>
                    SYSTEM SEARCH RESULTS: FEDERAL (PACER) & STATE (NYSCEF) LITIGATION HISTORY
                  </div>
                  <table className="psi-table">
                    <thead>
                      <tr><th>Date</th><th>Case Number</th><th>Court</th><th>Title</th><th>Status</th></tr>
                    </thead>
                    <tbody>
                      {data.courtRecords && data.courtRecords.length > 0 ? (
                        data.courtRecords.map((record, i) => (
                          <React.Fragment key={i}>
                            <tr>
                              <td style={{ fontFamily: 'monospace' }}>{record.date}</td>
                              <td style={{ fontFamily: 'monospace', color: 'var(--text-accent)' }}>{record.caseNumber}</td>
                              <td>{record.court}</td>
                              <td style={{ fontWeight: '600' }}>{record.title}</td>
                              <td><span className={`psi-tag ${record.status.toLowerCase().includes('closed') ? 'tag-neu' : 'tag-neg'}`}>{record.status}</span></td>
                            </tr>
                            <tr>
                              <td colSpan={5} style={{ padding: '8px 15px', fontSize: '11px', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.02)' }}>
                                <span style={{ color: 'var(--text-accent)', marginRight: '8px' }}>SUMMARY:</span> {record.summary}
                              </td>
                            </tr>
                          </React.Fragment>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '20px' }}>
                            NO RELEVANT COURT RECORDS FOUND IN PACER OR NYSCEF FOR THIS CANDIDATE.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div style={{marginTop: '8px'}}>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Create a comprehensive opposition research brief against Fernando Mateo for a hypothetical future NYC campaign opponent')}>↗ Opposition research brief</span>
                <span className="psi-prompt-btn" onClick={() => sendPrompt('Design a crisis communications plan for Fernando Mateo to address the 2010 racial profiling controversy proactively before a future campaign launch')}>↗ Crisis comms strategy</span>
              </div>
            </div>
          )}

          {/* REPORT TAB */}
          {activeTab === 'report' && (
            <div id="tab-report" className="view-panel active report-tab-visible" style={{ display: 'block' }}>
              <div style={{ 
                background: 'white', 
                color: 'black', 
                padding: '50px', 
                maxWidth: '850px', 
                margin: '0 auto', 
                boxShadow: '0 0 20px rgba(0,0,0,0.5)',
                fontFamily: 'IBM Plex Sans, sans-serif'
              }}>
                <div style={{ borderBottom: '3px solid black', paddingBottom: '20px', marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <div>
                    <div style={{ fontSize: '10px', letterSpacing: '0.2em', fontWeight: 'bold', color: '#666' }}>SENTINEL STRATEGIC ADVISORY</div>
                    <div style={{ fontSize: '28px', fontWeight: 'bold', marginTop: '5px' }}>STRATEGIC INTELLIGENCE BRIEF</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '10px', fontWeight: 'bold' }}>CONFIDENTIAL // EYES ONLY</div>
                    <div style={{ fontSize: '10px', color: '#666' }}>REF: {data.subject.toUpperCase().replace(/\s+/g, '-')}-2026</div>
                  </div>
                </div>

                <div style={{ marginBottom: '30px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '10px', fontSize: '12px', marginBottom: '5px' }}>
                    <div style={{ fontWeight: 'bold', color: '#666' }}>SUBJECT:</div>
                    <div style={{ fontWeight: 'bold' }}>{data.subject.toUpperCase()}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '10px', fontSize: '12px', marginBottom: '5px' }}>
                    <div style={{ fontWeight: 'bold', color: '#666' }}>DATE:</div>
                    <div>APRIL 13, 2026</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '10px', fontSize: '12px', marginBottom: '5px' }}>
                    <div style={{ fontWeight: 'bold', color: '#666' }}>CLASSIFICATION:</div>
                    <div style={{ color: '#dc2626', fontWeight: 'bold' }}>HIGH-PRIORITY ADVISORY</div>
                  </div>
                </div>

                <div style={{ marginBottom: '30px' }}>
                  <h3 style={{ fontSize: '14px', borderBottom: '1px solid #eee', paddingBottom: '5px', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>I. Executive Summary</h3>
                  <p style={{ fontSize: '13px', lineHeight: '1.6', color: '#333' }}>{data.summary}</p>
                </div>

                <div style={{ marginBottom: '30px' }}>
                  <h3 style={{ fontSize: '14px', borderBottom: '1px solid #eee', paddingBottom: '5px', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>II. Key Strategic Risks</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    {data.risks.map((risk, i) => (
                      <div key={i} style={{ border: '1px solid #eee', padding: '10px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 'bold', marginBottom: '4px' }}>{risk.title}</div>
                        <div style={{ fontSize: '11px', color: '#666' }}>{risk.body}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: '30px' }}>
                  <h3 style={{ fontSize: '14px', borderBottom: '1px solid #eee', paddingBottom: '5px', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>III. Media Sentiment Analysis</h3>
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                    <div style={{ flex: 1, background: '#f9fafb', padding: '15px', textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#16a34a' }}>{data.sentiment?.positive || 0}%</div>
                      <div style={{ fontSize: '9px', color: '#666', textTransform: 'uppercase' }}>Positive Coverage</div>
                    </div>
                    <div style={{ flex: 1, background: '#f9fafb', padding: '15px', textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc2626' }}>{data.sentiment?.negative || 0}%</div>
                      <div style={{ fontSize: '9px', color: '#666', textTransform: 'uppercase' }}>Negative Coverage</div>
                    </div>
                    <div style={{ flex: 1, background: '#f9fafb', padding: '15px', textAlign: 'center' }}>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#6b7280' }}>{data.sentiment?.neutral || 0}%</div>
                      <div style={{ fontSize: '9px', color: '#666', textTransform: 'uppercase' }}>Neutral Coverage</div>
                    </div>
                  </div>
                </div>

                <div style={{ pageBreakBefore: 'always', paddingTop: '20px' }}>
                  <h3 style={{ fontSize: '14px', borderBottom: '1px solid #eee', paddingBottom: '5px', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.1em' }}>IV. Master Chronological Table</h3>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px' }}>
                    <thead>
                      <tr style={{ background: '#f3f4f6' }}>
                        <th style={{ border: '1px solid #d1d5db', padding: '6px', textAlign: 'left' }}>Date</th>
                        <th style={{ border: '1px solid #d1d5db', padding: '6px', textAlign: 'left' }}>Source</th>
                        <th style={{ border: '1px solid #d1d5db', padding: '6px', textAlign: 'left' }}>Headline</th>
                        <th style={{ border: '1px solid #d1d5db', padding: '6px', textAlign: 'left' }}>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.fullArchive?.slice(0, 25).map((ev) => (
                        <tr key={ev.id}>
                          <td style={{ border: '1px solid #d1d5db', padding: '6px' }}>{ev.date}</td>
                          <td style={{ border: '1px solid #d1d5db', padding: '6px' }}>{ev.source}</td>
                          <td style={{ border: '1px solid #d1d5db', padding: '6px' }}>{ev.headline}</td>
                          <td style={{ border: '1px solid #d1d5db', padding: '6px' }}>{ev.confidence}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {data.fullArchive && data.fullArchive.length > 25 && (
                    <div style={{ fontSize: '9px', color: '#999', marginTop: '10px', fontStyle: 'italic' }}>
                      * Table truncated for brief summary. Full archive contains {data.fullArchive.length} events.
                    </div>
                  )}
                </div>

                <div style={{ marginTop: '50px', borderTop: '1px solid #000', paddingTop: '10px', fontSize: '9px', color: '#999', textAlign: 'center' }}>
                  SENTINEL STRATEGIC ADVISORY // GENERATED VIA PROPRIETARY INTELLIGENCE ENGINE // NO UNAUTHORIZED DISTRIBUTION
                </div>
              </div>
              
              <div className="no-print" style={{ textAlign: 'center', marginTop: '20px' }}>
                <button 
                  onClick={handleExportPDF}
                  className="psi-btn-secondary"
                  style={{ padding: '10px 20px', fontSize: '12px' }}
                >
                  <Printer size={16} style={{ marginRight: '8px' }} /> PRINT THIS REPORT
                </button>
              </div>
            </div>
          )}

          {/* ARCHIVE TAB */}
          {activeTab === 'archive' && (
            <div id="tab-archive" className="view-panel active">
              <div className="psi-panel">
                <div className="psi-panel-header">
                  <span className="psi-panel-title">Broadcast Transcript Database — CNN / FOX / MSNBC</span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input 
                      type="text" 
                      placeholder="Deep search transcripts..." 
                      value={transcriptQuery}
                      onChange={(e) => setTranscriptQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleTranscriptSearch()}
                      style={{ 
                        background: 'rgba(255,255,255,0.05)', 
                        border: '1px solid var(--border-color)', 
                        color: 'white', 
                        fontSize: '10px', 
                        padding: '4px 8px',
                        width: '150px',
                        fontFamily: 'IBM Plex Mono'
                      }}
                    />
                    <button 
                      onClick={handleTranscriptSearch}
                      disabled={isSearchingTranscripts}
                      style={{ 
                        background: 'var(--text-accent)', 
                        border: 'none', 
                        color: 'black', 
                        fontSize: '10px', 
                        padding: '4px 8px', 
                        cursor: 'pointer',
                        fontFamily: 'IBM Plex Mono',
                        fontWeight: '600'
                      }}
                    >
                      {isSearchingTranscripts ? 'SEARCHING...' : 'SEARCH'}
                    </button>
                  </div>
                </div>
                <div className="psi-panel-body">
                  <div style={{ marginBottom: '15px', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono' }}>
                    RECOVERED TV APPEARANCES FROM NATIONAL BROADCAST DATABASES (LEXISNEXIS / NEXIS UNI)
                  </div>
                  <div className="psi-grid-2">
                    {data.broadcastAppearances && data.broadcastAppearances.length > 0 ? (
                      data.broadcastAppearances.map((app, i) => (
                        <div key={i} className="psi-strategy-card" style={{ borderLeft: '3px solid var(--text-accent)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span style={{ fontFamily: 'IBM Plex Mono', fontSize: '10px', color: 'var(--text-accent)' }}>{app.network}</span>
                            <span style={{ fontFamily: 'IBM Plex Mono', fontSize: '10px', color: 'var(--text-muted)' }}>{app.date}</span>
                          </div>
                          <div className="psi-strategy-title" style={{ fontSize: '13px', marginBottom: '4px' }}>{app.program}: {app.title}</div>
                          <div className="psi-strategy-body" style={{ fontSize: '11px', lineHeight: '1.4' }}>{app.summary}</div>
                          {app.url && (
                            <a href={app.url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-block', marginTop: '8px', fontSize: '10px', color: 'var(--text-accent)', textDecoration: 'none', borderBottom: '1px dotted var(--text-accent)' }}>
                              VIEW TRANSCRIPT ↗
                            </a>
                          )}
                        </div>
                      ))
                    ) : (
                      <div style={{ gridColumn: 'span 2', textAlign: 'center', color: 'var(--text-dim)', padding: '40px', border: '1px dashed var(--border-color)' }}>
                        NO ADDITIONAL BROADCAST TRANSCRIPTS RECOVERED FOR THIS CANDIDATE.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {data.fullArchive && (
                <div className="psi-panel">
                  <div className="psi-panel-header">
                    <span className="psi-panel-title">Master Chronological Table — {data.fullArchive.length} Discrete Events</span>
                  </div>
                  <div className="psi-panel-body" style={{ overflowX: 'auto' }}>
                    {Object.entries(
                      data.fullArchive.reduce((acc, ev) => {
                        const match = ev.date.match(/\b(19|20)\d{2}\b/);
                        const year = match ? parseInt(match[0], 10) : null;
                        const decadeStart = year ? Math.floor(year / 10) * 10 : null;
                        const decade = decadeStart ? `${decadeStart}–${decadeStart + 9}` : 'Unknown Date';
                        if (!acc[decade]) acc[decade] = [];
                        acc[decade].push(ev);
                        return acc;
                      }, {} as Record<string, NonNullable<typeof data.fullArchive>>)
                    ).sort(([a], [b]) => a.localeCompare(b)).map(([decade, events]) => (
                      <div key={decade} style={{ marginBottom: '40px' }}>
                        <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '15px', color: 'var(--text-bright)', borderBottom: '2px solid var(--border-color)', paddingBottom: '5px' }}>{decade}</h3>
                        <table className="psi-table archive-table" style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid var(--border-color)' }}>
                          <thead>
                            <tr>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>ID</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>Date</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>Source</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>Headline / Title</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>URL</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>Summary</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>Category</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>Confidence</th>
                              <th style={{ border: '1px solid var(--border-color)', textAlign: 'center' }}>Source Type</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(events as any[]).map((ev) => (
                              <tr key={ev.id}>
                                <td style={{ border: '1px solid var(--border-color)', textAlign: 'center', color: 'var(--text-bright)', fontSize: '11px', fontWeight: 'bold' }}>{ev.id}</td>
                                <td style={{ border: '1px solid var(--border-color)', textAlign: 'center', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: '11px', fontWeight: 'bold', color: 'var(--text-bright)' }}>{ev.date}</td>
                                <td style={{ border: '1px solid var(--border-color)', textAlign: 'center', fontSize: '11px', fontWeight: '500', color: 'var(--text-bright)' }}>{ev.source}</td>
                                <td style={{ border: '1px solid var(--border-color)', fontWeight: '500', fontSize: '11px', color: 'var(--text-bright)' }}>{ev.headline}</td>
                                <td style={{ border: '1px solid var(--border-color)', fontSize: '11px', textAlign: 'center' }}>
                                  <a href={ev.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-bright)', textDecoration: 'underline', fontWeight: '500' }}>
                                    {ev.url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                                  </a>
                                </td>
                                <td style={{ border: '1px solid var(--border-color)', fontSize: '11px', color: 'var(--text-bright)' }}>{ev.summary}</td>
                                <td style={{ border: '1px solid var(--border-color)', fontSize: '11px', color: 'var(--text-bright)' }}>{ev.category}</td>
                                <td style={{ border: '1px solid var(--border-color)', fontSize: '11px', fontWeight: '500', color: 'var(--text-bright)' }}>{ev.confidence}</td>
                                <td style={{ border: '1px solid var(--border-color)', fontSize: '11px', color: 'var(--text-bright)' }}>{ev.sourceType}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      
      <div className="watermark">SENTINEL STRATEGIC ADVISOR — {data.subject.toUpperCase()} — GENERATED 2026 — CONFIDENTIAL ADVISORY</div>

      {/* GENERATING REPORT OVERLAY */}
      {isGeneratingReport && (
  <div
    className="no-print"
    style={{
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.72)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999,
      padding: "16px",
      backdropFilter: "blur(4px)",
    }}
  >
    <div
      style={{
        width: "min(92vw, 420px)",
        background: "var(--bg-panel)",
        border: "1px solid var(--border-color)",
        borderRadius: "18px",
        padding: "clamp(18px, 3vw, 28px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "14px",
        boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
      }}
    >
      <div
  style={{
    position: "relative",
    width: "clamp(56px, 12vw, 78px)",
    height: "clamp(56px, 12vw, 78px)",
  }}
>
  {/* Static gray ring */}
  <div
    style={{
      position: "absolute",
      inset: 0,
      borderRadius: "50%",
      border: "4px solid rgba(255,255,255,0.12)",
    }}
  />

  {/* Rotating blue arc */}
  <div
    style={{
      position: "absolute",
      inset: 0,
      borderRadius: "50%",
      border: "4px solid transparent",
      borderTop: "4px solid var(--text-accent)",
      borderRight: "4px solid var(--text-accent)",
      animation: "spin 0.9s linear infinite",
    }}
  />
</div>

      <div
        style={{
          fontFamily: "IBM Plex Mono",
          fontSize: "clamp(13px, 2.5vw, 15px)",
          color: "var(--text-bright)",
          fontWeight: 600,
          letterSpacing: "0.12em",
          textAlign: "center",
        }}
      >
        GENERATING PDF
      </div>

      <div
        style={{
          fontFamily: "IBM Plex Mono",
          fontSize: "clamp(10px, 2vw, 11px)",
          color: "var(--text-muted)",
          textAlign: "center",
          minHeight: "16px",
        }}
      >
        {[
          "Collecting archive records...",
          "Building strategic sections...",
          "Rendering PDF layout...",
          "Finalizing download..."
        ][pdfLoadingStep]}
      </div>

      <div
        style={{
          width: "100%",
          height: "8px",
          borderRadius: "999px",
          background: "rgba(255,255,255,0.08)",
          overflow: "hidden",
          marginTop: "4px",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${((pdfLoadingStep + 1) / 4) * 100}%`,
            background: "var(--text-accent)",
            transition: "width 0.45s ease",
            borderRadius: "999px",
          }}
        />
      </div>

      <div
        style={{
          fontFamily: "IBM Plex Mono",
          fontSize: "10px",
          color: "var(--text-dim)",
          textAlign: "center",
          lineHeight: 1.5,
        }}
      >
        Please wait while the report is prepared.
      </div>
    </div>
  </div>
)}

      {/* DRILLDOWN MODAL */}
      {selectedCategory && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'rgba(0,0,0,0.85)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            background: 'var(--bg-panel)',
            border: '1px solid var(--border-color)',
            width: '100%',
            maxWidth: '800px',
            maxHeight: '80vh',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{
              padding: '15px 20px',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ fontFamily: 'IBM Plex Mono', fontSize: '12px', color: 'var(--text-accent)', letterSpacing: '0.1em' }}>
                DRILLDOWN: {selectedCategory.toUpperCase()}
              </div>
              <button 
                onClick={() => setSelectedCategory(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>
            <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
              {drilldownLoading ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px', gap: '15px' }}>
                  <Loader2 className="animate-spin" style={{ color: 'var(--text-accent)' }} size={32} />
                  <div style={{ fontFamily: 'IBM Plex Mono', fontSize: '11px', color: 'var(--text-muted)' }}>FETCHING SOURCE ARTICLES...</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  {drilldownArticles.length > 0 ? (
                    drilldownArticles.map((art, i) => (
                      <div key={i} style={{ padding: '15px', border: '1px solid var(--border-color)', background: 'var(--bg-app)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                          <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-bright)', flex: 1 }}>{art.title}</div>
                          {art.url && (
                            <a href={art.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--text-accent)', marginLeft: '10px' }}>
                              <ExternalLink size={14} />
                            </a>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: '15px', fontFamily: 'IBM Plex Mono', fontSize: '10px', color: 'var(--text-dim)', marginBottom: '10px' }}>
                          <span>{art.source}</span>
                          <span>{new Date(art.date).toLocaleDateString()}</span>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                          {art.summary || art.snippet || "No summary available."}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-dim)', fontFamily: 'IBM Plex Mono', fontSize: '11px' }}>
                      NO SPECIFIC ARTICLES FOUND FOR THIS CATEGORY.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
