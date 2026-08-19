from typing import Annotated
from uuid import UUID

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.db import DatabaseUnavailable
from app.repositories import ContactRepository
from app.schemas import ContactCreate, ContactRead, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactRead])
async def list_contacts(
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ContactRead]:
    try:
        return await ContactRepository().list(q=q, limit=limit)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
async def create_contact(payload: ContactCreate) -> ContactRead:
    try:
        return await ContactRepository().create(payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="Contact name already exists") from exc


@router.patch("/{contact_id}", response_model=ContactRead)
async def update_contact(contact_id: UUID, payload: ContactUpdate) -> ContactRead:
    try:
        contact = await ContactRepository().update(contact_id, payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="Contact name already exists") from exc

    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: UUID) -> Response:
    try:
        deleted = await ContactRepository().delete(contact_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
