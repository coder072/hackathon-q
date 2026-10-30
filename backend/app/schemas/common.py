from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """JSON 필드는 camelCase, 파이썬 속성은 snake_case."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class ApiResponse[T](CamelModel):
    success: bool = True
    data: T
    request_id: str | None = None
