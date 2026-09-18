"""Import every model so Base.metadata sees all tables before create_all()."""
from app.models.audit import AuditLog  # noqa: F401
from app.models.bi import ForecastResult, Product, SalesTransaction  # noqa: F401
from app.models.copilot import ChatLog  # noqa: F401
from app.models.evaluation import ModelEvaluation  # noqa: F401
from app.models.fraud import FraudTransaction  # noqa: F401
from app.models.integration import (  # noqa: F401
    ApiKey,
    ConnectorInstance,
    DatabaseConnection,
    ScheduledJob,
    WebhookEndpoint,
)
from app.models.inventory import InventorySnapshot, ReorderRecommendation  # noqa: F401
from app.models.maintenance import Equipment  # noqa: F401
from app.models.model_registry import ModelVersion  # noqa: F401
from app.models.organization import ModuleEnablement, Organization  # noqa: F401
from app.models.usage import UsageMetric  # noqa: F401
from app.models.user import RoleEnum, User  # noqa: F401
from app.models.workforce import Employee, Goal, KPIWeightConfig, PerformanceScore  # noqa: F401
