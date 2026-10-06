from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: HttpUrl | None = None
    note: str | None = Field(default=None, max_length=10_000)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    url: HttpUrl | None = None
    note: str | None = Field(default=None, max_length=10_000)


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class ItemList(BaseModel):
    items: list[ItemRead]
    total: int
    limit: int
    offset: int
