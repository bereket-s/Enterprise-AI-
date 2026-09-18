from pydantic import BaseModel, ConfigDict


class IngestPreview(BaseModel):
    columns: list[str]
    suggested_mapping: dict[str, str | None]
    sample_rows: list[dict]


class IngestResult(BaseModel):
    products: int
    transactions_ingested: int


class TopProduct(BaseModel):
    sku: str
    name: str
    revenue: float


class KPISummary(BaseModel):
    total_revenue: float
    avg_daily_revenue: float
    trend_pct: float
    days_of_history: int = 0
    top_products: list[TopProduct] = []


class ForecastPoint(BaseModel):
    date: str
    actual: float | None = None
    predicted: float


class ForecastOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: int
    model_name: str
    horizon_days: int
    mae: float
    rmse: float
    mape: float
    forecast_points: list[dict]
