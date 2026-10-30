from datetime import datetime

from app.schemas.common import CamelModel


class HealthStatus(CamelModel):
    status: str
    version: str
    timestamp: datetime
