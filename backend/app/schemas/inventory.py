from pydantic import BaseModel


class ReorderRecommendationOut(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    expected_demand: float
    current_stock: int
    safety_stock: float
    reorder_point: float
    recommended_order_qty: float
    stockout_probability: float
    risk_label: str
