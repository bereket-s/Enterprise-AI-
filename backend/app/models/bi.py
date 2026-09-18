from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class Product(Base, TenantMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100), default="general")

    transactions: Mapped[list["SalesTransaction"]] = relationship(back_populates="product")


class SalesTransaction(Base, TenantMixin):
    __tablename__ = "sales_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    customer_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="transactions")

    @property
    def revenue(self) -> float:
        return self.quantity * self.unit_price


class ForecastResult(Base, TenantMixin):
    """Persisted output of a forecasting run, kept for the report's evaluation chapter."""

    __tablename__ = "forecast_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(50), default="company")  # "company" or a product sku
    model_name: Mapped[str] = mapped_column(String(100))
    horizon_days: Mapped[int] = mapped_column(Integer)
    mae: Mapped[float] = mapped_column(Float)
    rmse: Mapped[float] = mapped_column(Float)
    mape: Mapped[float] = mapped_column(Float)
    forecast_points: Mapped[list] = mapped_column(JSON)  # [{date, predicted, actual?}]
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
