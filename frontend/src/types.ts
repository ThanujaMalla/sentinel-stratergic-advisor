export interface Person {
  name: string;
  summary: string;
  influenceScore: number;
  tags: string[];
}

export interface Entity {
  name: string;
  role: string;
  period: string;
  notes: string;
}

export interface Event {
  id: string;
  title: string;
  date: string;
  description: string;
  category: 'Politics' | 'Business' | 'Legal' | 'Media' | 'Other';
  sentiment: 'Positive' | 'Negative' | 'Neutral';
  confidence: string;
  source: string;
  sourceType: string;
  link?: string;
}

export interface Article {
  id: string;
  title: string;
  source: string;
  date: string;
  summary: string;
  sentiment: number; // -1 to 1
  keywords: string[];
  entities: string[];
  url: string;
}

export interface ArchiveEvent {
  id: number;
  date: string;
  source: string;
  headline: string;
  url: string;
  summary: string;
  category: string;
  confidence: string;
  sourceType: string;
}

export interface DashboardData {
  subject: string;
  eventCount: number;
  netSentiment: string;
  totalFundraising: string;
  electoralResult: string;

  phases: Array<{ id: string, title: string, years: string, score: string, scoreClass: string, color: string, sentPos: number, sentNeg: number, sentNeu: number, summary: string }>;
  orgs: Array<{ name: string, role: string, dot: string }>;
  coverageVolume: Array<{ label: string, count: number, pct: number, color: string }>;
  timeline: Array<{ date: string, color: string, text: string, url?: string, tags: Array<{ label: string, cls: string }> }>;
  outlets: Array<{ name: string, tone: string, toneCls: string, score: string, scoreColor: string, url?: string }>;
  inflections: Array<{ event: string, date: string, shift: string, shiftColor: string, driver: string }>;
  fundraisingLog: Array<{ year: string, candidate: string, amount: string, amountColor: string, method: string }>;
  fundAssessments: Array<{ title: string, priority: string, priCls: string, body: string }>;
  fundScenarios: Array<{ title: string, body: string, range: string }>;
  campaignPostMortem: Array<{ title: string, body: string }>;
  campaignStrategies: Array<{ severity: string, severityColor: string, cls: string, title: string, body: string }>;
  networkTier1: Array<{ name: string, rel: string, strength: string, strengthColor: string, dot: string }>;
  mediaNetwork: Array<{ name: string, rel: string, dot: string }>;
  communityNetwork: Array<{ name: string, rel: string, dot: string }>;
  riskMetrics: Array<{ val: string, valColor: string, label: string, delta: string }>;
  risks: Array<{ severity: string, severityColor: string, cls: string, title: string, body: string }>;
  contributions: Array<{ year: string, recipient: string, amount: string, office: string }>;
  courtRecords: Array<{ date: string, caseNumber: string, court: string, title: string, status: string, summary: string }>;
  broadcastAppearances: Array<{ date: string, network: string, program: string, title: string, summary: string, url?: string }>;
  summary: string;
  sentiment: {
    positive: number;
    negative: number;
    neutral: number;
  };
  peakPositive: { score: string, date: string, event: string };
  peakNegative: { score: string, date: string, event: string };
  fullArchive?: ArchiveEvent[];
}
