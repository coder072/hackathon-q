# 모델을 추가하면 여기서 import 해서 Alembic(migrations/env.py)이 인식하도록 한다.
from app.models.analysis_session import AnalysisSession

__all__ = ["AnalysisSession"]
