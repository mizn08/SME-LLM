from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class DashboardKPIs(BaseModel):
    current_ratio: float
    days_cash_on_hand: float
    burn_rate_monthly_rm: float
    revenue_mtd_rm: float
    expense_mtd_rm: float
    net_operating_cash_rm: float


class MonthlySeriesPoint(BaseModel):
    month: str
    revenue_rm: float
    expense_rm: float


class ForecastMonth(BaseModel):
    month_offset: int
    projected_net_rm: float
    cumulative_net_rm: float


class DashboardResponse(BaseModel):
    sme_id: int
    business_name: str
    industry: str
    kpis: DashboardKPIs
    monthly_series: list[MonthlySeriesPoint]
    runway_days_est: float | None = None
    forecast_months: list[ForecastMonth] = []
    alerts: list[str] = []
    anomaly_count: int = 0
    health_score: int | None = None
    health_grade: str | None = None
    health_label: str | None = None


class PredictRequest(BaseModel):
    sme_id: int
    purchase_amount: float = Field(gt=0)
    purchase_category: str
    selected_bnpl_plan: Optional[str] = None


class ShapItem(BaseModel):
    feature: str
    value: float
    impact: float
    direction: str


class PredictResponse(BaseModel):
    prediction_id: int | None = None
    recommendation_type: str
    product_name: str
    explanation: str
    cash_preserved_rm: float
    additional_cost_rm: float
    confidence: float
    shap_values: list[ShapItem] = []
    ml_probability: float
    bandit_suggested_arm: str | None = None
    rl_suggested_action: str | None = None
    lead_scores: list["LeadScoreItem"] = []


class GovAidOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheme_name: str
    agency: str
    aid_type: str
    max_amount_rm: Optional[float]
    interest_rate_label: Optional[str]
    tenure_months: Optional[int]
    approval_speed_label: str
    requires_bumiputera: bool
    requires_veteran: bool
    industry_keywords: Optional[str]
    digitalisation_only: bool
    description: Optional[str]


class PredictionHistoryItem(BaseModel):
    id: int
    sme_id: int
    created_at: date
    recommendation_type: str
    product_name: str
    confidence: float
    purchase_amount: float


class PredictionDetailResponse(BaseModel):
    id: int
    sme_id: int
    created_at: str
    recommendation_type: str
    product_name: str
    explanation: str
    cash_preserved_rm: float
    additional_cost_rm: float
    confidence: float
    shap_values: list[ShapItem] = []
    request_payload: dict[str, Any]


class ChatRequest(BaseModel):
    sme_id: int
    message: str = Field(min_length=1, max_length=2000)
    persona: str | None = Field(
        default=None,
        description="Advisor tone: banker | towkay | mdec",
    )
    language: str | None = Field(default=None, description="en | ms (Bahasa Malaysia)")


class ChatSource(BaseModel):
    type: str | None = None
    snippet: str


class ChatResponse(BaseModel):
    sme_id: int
    message: str
    answer: str
    mode: str
    sources: list[ChatSource] = []
    language: str | None = None


class AgentAdviseRequest(BaseModel):
    sme_id: int
    purchase_amount: float = Field(gt=0)
    purchase_category: str
    goal: str | None = None


class AgentInsight(BaseModel):
    name: str
    insight: str


class AgentAdviseResponse(BaseModel):
    sme_id: int
    lead_agent: str
    summary: str
    agents: list[AgentInsight]
    recommendation: dict[str, Any] | None = None
    rag_snippet: str | None = None
    agent_trace: list[dict[str, Any]] = []


class ClusterInfo(BaseModel):
    sme_id: int
    cluster_id: int
    cluster_label: str


class AnomaliesBlock(BaseModel):
    anomalies: list[dict[str, Any]] = []
    method: str
    total_flagged: int | None = None
    message: str | None = None


class SmeInsightsResponse(BaseModel):
    sme_id: int
    cluster: ClusterInfo | None = None
    anomalies: AnomaliesBlock


class ClusterResponse(BaseModel):
    clusters: list[ClusterInfo]
    method: str
    n_clusters: int


class BanditArmStatOut(BaseModel):
    arm: str
    pulls: int
    total_reward: float | None = None
    avg_reward: float


class BanditStatsResponse(BaseModel):
    arms: list[BanditArmStatOut]
    suggestion: dict[str, Any]


class BanditFeedbackRequest(BaseModel):
    sme_id: int
    arm: str
    accepted: bool
    prediction_id: int | None = None
    reward: float | None = None


class RlhfPreferenceRequest(BaseModel):
    sme_id: int
    chosen: str
    rejected: str


class RlAdviseRequest(BaseModel):
    sme_id: int
    purchase_amount: float = Field(gt=0)
    action: str | None = None
    reward: float | None = None


class RlAdviseResponse(BaseModel):
    state: str
    action: str
    q_values: dict[str, float]
    bandit_suggestion: str
    policy: str


class CompareOption(BaseModel):
    type: str
    product_name: str
    additional_cost_rm: float
    cash_preserved_rm: float
    total_with_sst_rm: float
    suitability_score: float
    notes: str


class CompareRequest(BaseModel):
    sme_id: int
    purchase_amount: float = Field(gt=0)
    purchase_category: str
    include_sst: bool = False
    islamic_only: bool = False


class CompareResponse(BaseModel):
    sme_id: int
    purchase_amount_rm: float
    purchase_category: str
    include_sst: bool
    sst_estimated_rm: float
    ml_financing_probability: float
    recommended: dict[str, str]
    options: list[CompareOption]


class RequirementParseResponse(BaseModel):
    room_size: str | None = None
    budget: float | None = None
    currency: str = "RM"
    style: str | None = None
    explicit_constraints: list[str] = []
    location: str = "Kuala Lumpur"
    source_chars: int = 0


class QuoteLineItem(BaseModel):
    product_id: str
    product_name: str
    product_url: str
    quantity: int = Field(ge=1)
    unit_price_rm: float = Field(ge=0)
    weight_kg: float = Field(ge=0, default=0.0)
    compatible: bool = True
    compatibility_note: str = ""


class QuoteRequest(BaseModel):
    sme_id: int
    title: str = "Sales quote"
    location: str = "Kuala Lumpur"
    service_level: str = "standard"
    discount_rm: float = Field(default=0, ge=0)
    budget_rm: float | None = Field(default=None, gt=0)
    reasoning_summary: str = ""
    items: list[QuoteLineItem]


class QuoteBreakdown(BaseModel):
    subtotal_rm: float
    shipping_rm: float
    tax_rm: float
    discount_rm: float
    grand_total_rm: float
    tax_rate: float
    estimated_delivery_days: int


class QuoteResponse(BaseModel):
    quote_id: int
    sme_id: int
    title: str
    location: str
    items: list[QuoteLineItem]
    breakdown: QuoteBreakdown
    within_budget: bool | None = None
    reasoning_summary: str
    created_at: str


class QuoteHistoryItem(BaseModel):
    quote_id: int
    sme_id: int
    title: str
    location: str
    grand_total_rm: float
    estimated_delivery_days: int
    created_at: str


class BusinessValueMetrics(BaseModel):
    quotes_generated: int
    manual_quote_minutes_avg: int
    agent_quote_minutes_avg: int
    time_saved_minutes_total: int
    time_saved_minutes_per_quote: int
    cost_saved_rm: float
    success_rate: float
    within_budget_rate: float
    human_error_rate_benchmark: float
    hourly_rate_rm: float


class SalesAgentRunRequest(BaseModel):
    sme_id: int
    brief_text: str | None = Field(default=None, max_length=4000)
    requirements: dict[str, Any] | None = None
    location: str = "Kuala Lumpur"


class SalesAgentRunResponse(BaseModel):
    sme_id: int
    requirements: dict[str, Any]
    task_complete: bool
    agent_trace: list[dict[str, Any]] = []
    reasoning_summary: str = ""
    quote: QuoteResponse | None = None
    business_value: BusinessValueMetrics
    rag_answer: str | None = None
    rag_mode: str | None = None
    rag_sources: list[ChatSource] = []


class TokenRequest(BaseModel):
    username: str = "sme_demo"
    password: str



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    note: str | None = None


# ─── Feature: Proactive AI Nudges ───────────────────────────────────────────
class NudgeItem(BaseModel):
    severity: str          # critical | warning | info
    title: str
    body: str
    recommended_product: str | None = None
    action_label: str | None = None


class NudgeResponse(BaseModel):
    sme_id: int
    nudges: list[NudgeItem] = []


# ─── Feature: Lead Scoring ───────────────────────────────────────────────────
class LeadScoreItem(BaseModel):
    product_type: str      # bnpl | micro_credit | grant
    product_name: str
    score: int             # 0-100
    reasons: list[str] = []


class LeadScoreResponse(BaseModel):
    sme_id: int
    scores: list[LeadScoreItem] = []


# ─── Feature: Sales Pitch Generator ─────────────────────────────────────────
class PitchRequest(BaseModel):
    lang: str = "en"       # en | ms
    tone: str = "formal"   # formal | friendly


class PitchResponse(BaseModel):
    sme_id: int
    lang: str
    tone: str
    letter: str


# ─── Feature: Competitor Benchmarking ───────────────────────────────────────
class BenchmarkMetric(BaseModel):
    label: str
    sme_value: float
    industry_median: float
    industry_p25: float | None = None
    industry_p75: float | None = None
    percentile: int | None = None
    unit: str = ""


class BenchmarkResponse(BaseModel):
    sme_id: int
    industry: str
    metrics: list[BenchmarkMetric] = []
    summary: str


# ─── Feature: Weekly Digest ──────────────────────────────────────────────────
class DigestEvent(BaseModel):
    icon: str
    title: str
    detail: str
    amount_rm: float | None = None


class DigestResponse(BaseModel):
    sme_id: int
    week_label: str
    events: list[DigestEvent] = []
    summary: str


# ─── Feature: BNPL Repayment Simulator ──────────────────────────────────────
class RepaymentMonth(BaseModel):
    month: int
    payment_rm: float
    principal_rm: float
    interest_rm: float
    balance_rm: float


class BnplRepaymentRequest(BaseModel):
    amount_rm: float = Field(gt=0)
    annual_rate_pct: float = Field(ge=0, le=100, default=12.0)
    tenure_months: int = Field(ge=1, le=60, default=12)


class BnplRepaymentResponse(BaseModel):
    amount_rm: float
    annual_rate_pct: float
    tenure_months: int
    monthly_payment_rm: float
    total_interest_rm: float
    total_cost_rm: float
    schedule: list[RepaymentMonth] = []


# ─── Feature: Lender Directory ───────────────────────────────────────────────
class LenderItem(BaseModel):
    id: str
    name: str
    product_type: str      # bnpl | micro_credit | islamic
    max_amount_rm: float | None = None
    typical_rate_label: str
    min_revenue_rm: float | None = None
    bumiputera_preferred: bool = False
    islamic_compliant: bool = False
    apply_url: str
    notes: str = ""


class LenderDirectoryResponse(BaseModel):
    lenders: list[LenderItem] = []
    total: int


class MatchedLenderResponse(BaseModel):
    sme_id: int
    matched: list[LenderItem] = []


# ─── Feature: Grant Application Checklist ────────────────────────────────────
class ChecklistItem(BaseModel):
    document: str
    required: bool = True
    tip: str = ""


class GrantChecklistResponse(BaseModel):
    scheme_id: int
    scheme_name: str
    agency: str
    deadline_label: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    apply_url: str | None = None
    checklist: list[ChecklistItem] = []


# ─── Feature: Application Tracker ────────────────────────────────────────────
class ApplicationCreateRequest(BaseModel):
    sme_id: int
    product_name: str
    product_type: str      # bnpl | micro_credit | grant
    notes: str | None = None


class ApplicationUpdateRequest(BaseModel):
    status: str | None = None  # draft | submitted | under_review | approved | rejected
    notes: str | None = None


class ApplicationTrackerItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sme_id: int
    product_name: str
    product_type: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationTrackerResponse(BaseModel):
    sme_id: int
    applications: list[ApplicationTrackerItem] = []


# ─── Feature: Conversation Memory ────────────────────────────────────────────
class ChatMemoryTurn(BaseModel):
    role: str   # user | assistant
    text: str


class ChatWithMemoryRequest(BaseModel):
    sme_id: int
    message: str = Field(min_length=1, max_length=2000)
    persona: str | None = None
    language: str | None = None
    history: list[ChatMemoryTurn] = []


# ─── Feature: Guided Advisory ────────────────────────────────────────────────
class GuidedAdvisoryRequest(BaseModel):
    sme_id: int
    business_type: str
    goal: str              # expand | survive | digitalise | export | hire
    amount_rm: float
    timeline_months: int
    main_constraint: str   # cash | collateral | time | eligibility


class GuidedAdvisoryResponse(BaseModel):
    sme_id: int
    recommendation: str
    top_product: str
    top_product_type: str
    reasoning: list[str] = []
    next_steps: list[str] = []
    pitch_snippet: str


# ─── Feature: Spending Categories ────────────────────────────────────────────
class SpendingCategoryItem(BaseModel):
    category: str
    amount_rm: float
    pct: float


class SpendingCategoryResponse(BaseModel):
    sme_id: int
    categories: list[SpendingCategoryItem] = []
    total_expense_rm: float = 0


# ─── Feature: Application Draft ────────────────────────────────────────────────
class ApplicationDraftRequest(BaseModel):
    product_type: str = "bnpl"
    purchase_amount: float = 0
    purchase_category: str = "Equipment"


class ApplicationDraftResponse(BaseModel):
    sme_id: int
    draft: dict[str, Any]


# ─── Feature: Financing Timeline ─────────────────────────────────────────────
class TimelineItem(BaseModel):
    id: str
    kind: str          # prediction | application
    title: str
    subtitle: str
    status: str | None = None
    amount_rm: float | None = None
    created_at: str


class FinancingTimelineResponse(BaseModel):
    sme_id: int
    items: list[TimelineItem] = []


# ─── Feature: Bank Statement Summary ─────────────────────────────────────────
class BankStatementSummaryResponse(BaseModel):
    sme_id: int
    summary: str
    periods: list[dict[str, Any]] = []
    totals: dict[str, Any] = {}
    top_expense_categories: list[dict[str, Any]] = []


# ─── v5: Goals, SHAP explain ─────────────────────────────────────────────────
class GoalCreate(BaseModel):
    sme_id: int
    title: str
    target_amount_rm: float = Field(gt=0)
    current_amount_rm: float = 0
    deadline: date | None = None
    category: str = "savings"


class GoalOut(BaseModel):
    id: int
    sme_id: int
    title: str
    target_amount_rm: float
    current_amount_rm: float
    deadline: date | None = None
    category: str
    status: str
    progress_pct: float


class GoalProgressUpdate(BaseModel):
    current_amount_rm: float = Field(ge=0)


class ShapWaterfallItem(BaseModel):
    feature: str
    impact: float
    direction: str
    cumulative: float


class ShapExplainResponse(BaseModel):
    sme_id: int
    baseline: float
    prediction: float
    waterfall: list[ShapWaterfallItem] = []


# Resolve forward reference on PredictResponse
PredictResponse.model_rebuild()
