from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Item
from app.schemas import ItemCreate, ItemList, ItemRead, ItemUpdate

router = APIRouter(prefix="/api/items", tags=["items"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_or_404(session: Session, item_id: int) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.get("", response_model=ItemList)
def list_items(
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ItemList:
    limit = min(limit, settings.max_page_size)
    total = session.scalar(select(func.count()).select_from(Item)) or 0
    rows = session.scalars(
        select(Item).order_by(Item.created_at.desc(), Item.id.desc()).limit(limit).offset(offset)
    ).all()
    return ItemList(
        items=[ItemRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, session: SessionDep) -> Item:
    data = payload.model_dump()
    data["url"] = str(payload.url) if payload.url else None
    item = Item(**data)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, session: SessionDep) -> Item:
    return _get_or_404(session, item_id)


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(item_id: int, payload: ItemUpdate, session: SessionDep) -> Item:
    item = _get_or_404(session, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, str(value) if field == "url" and value is not None else value)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, session: SessionDep) -> Response:
    item = _get_or_404(session, item_id)
    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
