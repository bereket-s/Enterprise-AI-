from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class InventorySnapshot(Base, TenantMixin):
    """Current stock position for a product; refreshed each time inventory data is (re)uploaded."""

    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    current_stock: Mapped[int] = mapped_column(Integer)
    supplier_lead_time_days: Mapped[int] = mapped_column(Integer, default=14)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    product: Mapped["Product"] = relationship()


class ReorderRecommendation(Base, TenantMixin):
    __tablename__ = "reorder_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    expected_demand: Mapped[float] = mapped_column(Float)
    current_stock: Mapped[int] = mapped_column(Integer)
    safety_stock: Mapped[float] = mapped_column(Float)
    reorder_point: Mapped[float] = mapped_column(Float)
    recommended_order_qty: Mapped[float] = mapped_column(Float)
    stockout_probability: Mapped[float] = mapped_column(Float)
    risk_label: Mapped[str] = mapped_column(String(20))  # low | medium | high | critical
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    product: Mapped["Product"] = relationship()
