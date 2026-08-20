from typing import Annotated
from uuid import UUID

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db import DatabaseUnavailable
from app.auth import CurrentTeam
from app.repositories import ContactRepository
from app.schemas import (
    ContactCreate,
    ContactExtractionRequest,
    ContactExtractionResponse,
    ContactRead,
    ContactUpdate,
)
from app.services.openai_contact_extraction import ContactExtractionService
from app.services.openai_translation import TranslationProviderUnavailable

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactRead])
async def list_contacts(
    context: CurrentTeam,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    team_key: Annotated[str, Query(min_length=1, max_length=120)] = "team-1",
) -> list[ContactRead]:
    try:
        return await ContactRepository().list(q=q, limit=limit, team_key=context.team_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(payload: ContactCreate, context: CurrentTeam) -> ContactRead:
    payload = payload.model_copy(update={
        "team_key": context.team_id,
        "created_by_key": context.user.id,
        "created_by_name": context.user.nickname,
    })
    try:
        return await ContactRepository().create(payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="같은 팀에 동일한 이름의 수신자가 이미 있습니다.") from exc


@router.post("/extract", response_model=ContactExtractionResponse)
async def extract_contact(
    payload: ContactExtractionRequest,
    context: CurrentTeam,
) -> ContactExtractionResponse:
    del context
    try:
        return await ContactExtractionService().extract(payload)
    except TranslationProviderUnavailable as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(contact_id: UUID, payload: ContactUpdate, context: CurrentTeam) -> ContactRead:
    try:
        contact = await ContactRepository().update(contact_id, payload, context.team_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="같은 팀에 동일한 이름의 수신자가 이미 있습니다.") from exc

    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: UUID, context: CurrentTeam) -> Response:
    try:
        deleted = await ContactRepository().delete(contact_id, context.team_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
