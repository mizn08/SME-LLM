from datetime import date
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


class ChatSource(BaseModel):
    type: str | None = None
    snippet: str


class ChatResponse(BaseModel):
    sme_id: int
    message: str
    answer: str
    mode: str
    sources: list[ChatSource] = []


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


class TokenRequest(BaseModel):
    username: str = "sme_demo"
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    note: str | None = None
