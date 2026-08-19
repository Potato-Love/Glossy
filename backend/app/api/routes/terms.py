from typing import Annotated
from uuid import UUID

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db import DatabaseUnavailable
from app.repositories import TermRepository
from app.schemas import TermCreate, TermRead, TermUpdate

router = APIRouter(prefix="/terms", tags=["terms"])


@router.get("", response_model=list[TermRead])
async def list_terms(
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[TermRead]:
    try:
        return await TermRepository().list(q=q, limit=limit)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("", response_model=TermRead, status_code=status.HTTP_201_CREATED)
async def create_term(payload: TermCreate) -> TermRead:
    try:
        return await TermRepository().create(payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="Term source already exists") from exc


@router.patch("/{term_id}", response_model=TermRead)
async def update_term(term_id: UUID, payload: TermUpdate) -> TermRead:
    try:
        term = await TermRepository().update(term_id, payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="Term source already exists") from exc

    if term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return term


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_term(term_id: UUID) -> Response:
    try:
        deleted = await TermRepository().delete(term_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Term not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
