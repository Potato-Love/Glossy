from __future__ import annotations

from uuid import UUID

from app.db import database
from app.schemas import (
    ContactCreate,
    ContactRead,
    ContactUpdate,
    MemoryCreate,
    MemoryRead,
    Purpose,
    SuggestionStatus,
    TargetLanguage,
    TermCreate,
    TermRead,
    TermSuggestionApprove,
    TermSuggestionCreate,
    TermSuggestionRead,
    TermSuggestionReject,
    TermUpdate,
    Tone,
)


class TermRepository:
    async def list(self, q: str | None, limit: int) -> list[TermRead]:
        rows = await database.fetch(
            """
            select id, source, target, mode, note, created_at, updated_at
            from terms
            where (
                $1::text is null
                or source ilike '%' || $1 || '%'
                or coalesce(target, '') ilike '%' || $1 || '%'
                or coalesce(note, '') ilike '%' || $1 || '%'
            )
            order by source asc
            limit $2
            """,
            q,
            limit,
        )
        return [TermRead.model_validate(dict(row)) for row in rows]

    async def create(self, payload: TermCreate) -> TermRead:
        row = await database.fetchrow(
            """
            insert into terms (source, target, mode, note)
            values ($1, $2, $3, $4)
            returning id, source, target, mode, note, created_at, updated_at
            """,
            payload.source,
            payload.target,
            payload.mode,
            payload.note,
        )
        return TermRead.model_validate(dict(row))

    async def update(self, term_id: UUID, payload: TermUpdate) -> TermRead | None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get(term_id)

        allowed_fields = ["source", "target", "mode", "note"]
        set_parts: list[str] = []
        values: list[object] = [term_id]
        for field in allowed_fields:
            if field in updates:
                values.append(updates[field])
                set_parts.append(f"{field} = ${len(values)}")

        query = f"""
            update terms
            set {", ".join(set_parts)}, updated_at = now()
            where id = $1
            returning id, source, target, mode, note, created_at, updated_at
        """
        row = await database.fetchrow(query, *values)
        return TermRead.model_validate(dict(row)) if row else None

    async def get(self, term_id: UUID) -> TermRead | None:
        row = await database.fetchrow(
            """
            select id, source, target, mode, note, created_at, updated_at
            from terms
            where id = $1
            """,
            term_id,
        )
        return TermRead.model_validate(dict(row)) if row else None

    async def delete(self, term_id: UUID) -> bool:
        deleted_id = await database.fetchval(
            "delete from terms where id = $1 returning id",
            term_id,
        )
        return deleted_id is not None


class ContactRepository:
    async def list(self, q: str | None, limit: int) -> list[ContactRead]:
        rows = await database.fetch(
            """
            select id, name, company, role, note, created_at, updated_at
            from contacts
            where (
                $1::text is null
                or name ilike '%' || $1 || '%'
                or coalesce(company, '') ilike '%' || $1 || '%'
                or coalesce(role, '') ilike '%' || $1 || '%'
                or coalesce(note, '') ilike '%' || $1 || '%'
            )
            order by name asc
            limit $2
            """,
            q,
            limit,
        )
        return [ContactRead.model_validate(dict(row)) for row in rows]

    async def create(self, payload: ContactCreate) -> ContactRead:
        row = await database.fetchrow(
            """
            insert into contacts (name, company, role, note)
            values ($1, $2, $3, $4)
            returning id, name, company, role, note, created_at, updated_at
            """,
            payload.name,
            payload.company,
            payload.role,
            payload.note,
        )
        return ContactRead.model_validate(dict(row))

    async def update(self, contact_id: UUID, payload: ContactUpdate) -> ContactRead | None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get(contact_id)

        allowed_fields = ["name", "company", "role", "note"]
        set_parts: list[str] = []
        values: list[object] = [contact_id]
        for field in allowed_fields:
            if field in updates:
                values.append(updates[field])
                set_parts.append(f"{field} = ${len(values)}")

        query = f"""
            update contacts
            set {", ".join(set_parts)}, updated_at = now()
            where id = $1
            returning id, name, company, role, note, created_at, updated_at
        """
        row = await database.fetchrow(query, *values)
        return ContactRead.model_validate(dict(row)) if row else None

    async def get(self, contact_id: UUID) -> ContactRead | None:
        row = await database.fetchrow(
            """
            select id, name, company, role, note, created_at, updated_at
            from contacts
            where id = $1
            """,
            contact_id,
        )
        return ContactRead.model_validate(dict(row)) if row else None

    async def delete(self, contact_id: UUID) -> bool:
        deleted_id = await database.fetchval(
            "delete from contacts where id = $1 returning id",
            contact_id,
        )
        return deleted_id is not None


class MemoryRepository:
    async def list(self, limit: int) -> list[MemoryRead]:
        rows = await database.fetch(
            """
            select
                id,
                source_text,
                source_language,
                target_language,
                tone,
                purpose,
                contact_id,
                result_text,
                created_at,
                updated_at
            from translation_memories
            order by updated_at desc
            limit $1
            """,
            limit,
        )
        return [MemoryRead.model_validate(dict(row)) for row in rows]

    async def find_match(
        self,
        source_text: str,
        target_language: TargetLanguage,
        tone: Tone,
        purpose: Purpose,
        contact_id: UUID | None,
    ) -> MemoryRead | None:
        row = await database.fetchrow(
            """
            select
                id,
                source_text,
                source_language,
                target_language,
                tone,
                purpose,
                contact_id,
                result_text,
                created_at,
                updated_at
            from translation_memories
            where source_text = $1
                and target_language = $2
                and tone = $3
                and purpose = $4
                and contact_id is not distinct from $5::uuid
            order by updated_at desc
            limit 1
            """,
            source_text,
            target_language,
            tone,
            purpose,
            contact_id,
        )
        return MemoryRead.model_validate(dict(row)) if row else None

    async def create(self, payload: MemoryCreate) -> MemoryRead:
        row = await database.fetchrow(
            """
            insert into translation_memories (
                source_text,
                source_language,
                target_language,
                tone,
                purpose,
                contact_id,
                result_text
            )
            values ($1, $2, $3, $4, $5, $6, $7)
            returning
                id,
                source_text,
                source_language,
                target_language,
                tone,
                purpose,
                contact_id,
                result_text,
                created_at,
                updated_at
            """,
            payload.source_text,
            payload.source_language,
            payload.target_language,
            payload.tone,
            payload.purpose,
            payload.contact_id,
            payload.result_text,
        )
        return MemoryRead.model_validate(dict(row))


class TermSuggestionRepository:
    async def list(
        self,
        status: SuggestionStatus | None,
        q: str | None,
        limit: int,
    ) -> list[TermSuggestionRead]:
        rows = await database.fetch(
            """
            select
                id,
                document_text,
                source,
                target,
                mode,
                reason,
                evidence,
                confidence,
                status,
                approved_term_id,
                created_at,
                updated_at
            from term_suggestions
            where (
                $1::text is null
                or status = $1
            )
            and (
                $2::text is null
                or source ilike '%' || $2 || '%'
                or coalesce(target, '') ilike '%' || $2 || '%'
                or coalesce(reason, '') ilike '%' || $2 || '%'
            )
            order by updated_at desc
            limit $3
            """,
            status,
            q,
            limit,
        )
        return [TermSuggestionRead.model_validate(dict(row)) for row in rows]

    async def create_many(
        self,
        suggestions: list[TermSuggestionCreate],
    ) -> list[TermSuggestionRead]:
        if not suggestions:
            return []

        pool = database.require_pool()
        rows = []
        async with pool.acquire() as connection, connection.transaction():
            for suggestion in suggestions:
                row = await connection.fetchrow(
                    """
                        insert into term_suggestions (
                            document_text,
                            source,
                            target,
                            mode,
                            reason,
                            evidence,
                            confidence
                        )
                        values ($1, $2, $3, $4, $5, $6, $7)
                        returning
                            id,
                            document_text,
                            source,
                            target,
                            mode,
                            reason,
                            evidence,
                            confidence,
                            status,
                            approved_term_id,
                            created_at,
                            updated_at
                        """,
                    suggestion.document_text,
                    suggestion.source,
                    suggestion.target,
                    suggestion.mode,
                    suggestion.reason,
                    suggestion.evidence,
                    suggestion.confidence,
                )
                rows.append(row)

        return [TermSuggestionRead.model_validate(dict(row)) for row in rows]

    async def get(self, suggestion_id: UUID) -> TermSuggestionRead | None:
        row = await database.fetchrow(
            """
            select
                id,
                document_text,
                source,
                target,
                mode,
                reason,
                evidence,
                confidence,
                status,
                approved_term_id,
                created_at,
                updated_at
            from term_suggestions
            where id = $1
            """,
            suggestion_id,
        )
        return TermSuggestionRead.model_validate(dict(row)) if row else None

    async def approve(
        self,
        suggestion_id: UUID,
        payload: TermSuggestionApprove,
    ) -> TermSuggestionRead | None:
        pool = database.require_pool()
        async with pool.acquire() as connection, connection.transaction():
            suggestion = await connection.fetchrow(
                """
                    select
                        id,
                        source,
                        target,
                        mode,
                        reason,
                        status,
                        approved_term_id
                    from term_suggestions
                    where id = $1
                    for update
                    """,
                suggestion_id,
            )
            if suggestion is None:
                return None
            if suggestion["status"] == "approved":
                return await self.get(suggestion_id)

            mode = payload.mode or suggestion["mode"]
            target = payload.target if payload.target is not None else suggestion["target"]
            note = payload.note or suggestion["reason"]
            if mode == "preserve":
                target = None

            existing_term = await connection.fetchrow(
                """
                    select id
                    from terms
                    where lower(source) = lower($1)
                    limit 1
                    """,
                suggestion["source"],
            )

            if existing_term is not None:
                term = await connection.fetchrow(
                    """
                        update terms
                        set target = $2,
                            mode = $3,
                            note = coalesce($4, note),
                            updated_at = now()
                        where id = $1
                        returning id
                        """,
                    existing_term["id"],
                    target,
                    mode,
                    note,
                )
            else:
                term = await connection.fetchrow(
                    """
                        insert into terms (source, target, mode, note)
                        values ($1, $2, $3, $4)
                        returning id
                        """,
                    suggestion["source"],
                    target,
                    mode,
                    note,
                )

            if term is None:
                return None

            row = await connection.fetchrow(
                """
                    update term_suggestions
                    set status = 'approved',
                        approved_term_id = $2,
                        target = $3,
                        mode = $4,
                        updated_at = now()
                    where id = $1
                    returning
                        id,
                        document_text,
                        source,
                        target,
                        mode,
                        reason,
                        evidence,
                        confidence,
                        status,
                        approved_term_id,
                        created_at,
                        updated_at
                    """,
                suggestion_id,
                term["id"],
                target,
                mode,
            )
            return TermSuggestionRead.model_validate(dict(row)) if row else None

    async def reject(
        self,
        suggestion_id: UUID,
        payload: TermSuggestionReject,
    ) -> TermSuggestionRead | None:
        current = await self.get(suggestion_id)
        if current is None:
            return None
        if current.status == "approved":
            return current

        row = await database.fetchrow(
            """
            update term_suggestions
            set status = 'rejected',
                reason = coalesce($2, reason),
                updated_at = now()
            where id = $1
            returning
                id,
                document_text,
                source,
                target,
                mode,
                reason,
                evidence,
                confidence,
                status,
                approved_term_id,
                created_at,
                updated_at
            """,
            suggestion_id,
            payload.reason,
        )
        return TermSuggestionRead.model_validate(dict(row)) if row else None
