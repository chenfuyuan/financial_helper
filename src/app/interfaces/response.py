from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="success", description="响应消息")
    data: DataT | None = Field(default=None, description="响应数据")

    @classmethod
    def success(cls, data: DataT | None = None, message: str = "success") -> "ApiResponse[DataT]":
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "error") -> "ApiResponse[DataT]":
        return cls(code=code, message=message, data=None)
