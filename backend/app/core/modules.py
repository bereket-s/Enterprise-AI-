"""Canonical registry of platform modules.

Adding a new module to the platform means adding one entry here plus its
router/service/ml package — the rest of the platform (onboarding, module
toggles, sidebar, RBAC) reads from this registry instead of hard-coding
module names anywhere else.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleDef:
    key: str
    name: str
    description: str
    maturity: str  # "production" | "prototype"


MODULE_REGISTRY: list[ModuleDef] = [
    ModuleDef(
        key="bi_forecasting",
        name="Business Intelligence & Forecasting",
        description="Sales/revenue KPIs, trend analysis, demand forecasting.",
        maturity="production",
    ),
    ModuleDef(
        key="inventory",
        name="Inventory & Procurement Optimization",
        description="Demand-driven reorder points, safety stock, purchase recommendations.",
        maturity="production",
    ),
    ModuleDef(
        key="fraud",
        name="Fraud & Anomaly Detection",
        description="Transaction risk scoring with an investigation workflow.",
        maturity="production",
    ),
    ModuleDef(
        key="maintenance",
        name="Predictive Maintenance",
        description="Equipment failure-risk prediction from sensor readings.",
        maturity="prototype",
    ),
    ModuleDef(
        key="workforce",
        name="Employee Performance & Workforce Intelligence",
        description="Configurable KPI scoring, goals, attrition risk, benchmarking.",
        maturity="production",
    ),
]

MODULE_KEYS = [m.key for m in MODULE_REGISTRY]


def is_valid_module(key: str) -> bool:
    return key in MODULE_KEYS
