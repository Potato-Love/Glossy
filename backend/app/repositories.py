from __future__ import annotations

import json
from uuid import UUID

from app.db import database
from app.schemas import (
    ContactCreate,
    ContactRead,
    ContactUpdate,
    HistoryCreate,
    HistoryRead,
    HistoryUpdate,
    MemoryCreate,
    MemoryRead,
    Purpose,
    SuggestionStatus,
    StrategyPreferenceCreate,
    StrategyPreferenceRead,
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
    async def list(
        self,
        q: str | None,
        limit: int,
        team_key: str = "team-1",
        user_key: str | None = None,
        scopes: list[str] | None = None,
        source_language: str | None = None,
        target_language: str | None = None,
    ) -> list[TermRead]:
        active_scopes = scopes if scopes is not None else ["team", "personal"]
        rows = await database.fetch(
            """
            select
                id, source, target, mode, note, team_key, scope, owner_key,
                source_language, target_language, created_by_key, created_by_name,
                creation_method, translation_strategy, term_category, created_at, updated_at
            from terms
            where team_key = $1
            and scope = any($2::text[])
            and (scope = 'team' or owner_key = $3)
            and ($4::text is null or source_language = $4)
            and ($5::text is null or target_language = $5)
            and (
                $6::text is null
                or source ilike '%' || $6 || '%'
                or coalesce(target, '') ilike '%' || $6 || '%'
                or coalesce(note, '') ilike '%' || $6 || '%'
            )
            order by scope desc, source asc
            limit $7
            """,
            team_key,
            active_scopes,
            user_key,
            source_language,
            target_language,
            q,
            limit,
        )
        return [TermRead.model_validate(dict(row)) for row in rows]

    async def create(self, payload: TermCreate) -> TermRead:
        pool = database.require_pool()
        async with pool.acquire() as connection, connection.transaction():
            row = await connection.fetchrow(
                """
                insert into terms (
                    source, target, mode, note, team_key, scope, owner_key,
                    source_language, target_language, created_by_key, created_by_name,
                    creation_method, translation_strategy, term_category
                )
                values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                returning
                    id, source, target, mode, note, team_key, scope, owner_key,
                    source_language, target_language, created_by_key, created_by_name,
                    creation_method, translation_strategy, term_category, created_at, updated_at
                """,
                payload.source,
                payload.target,
                payload.mode,
                payload.note,
                payload.team_key,
                payload.scope,
                payload.owner_key,
                payload.source_language,
                payload.target_language,
                payload.created_by_key,
                payload.created_by_name,
                payload.creation_method,
                payload.translation_strategy,
                payload.term_category,
            )
            if payload.preference_scope is not None:
                if payload.translation_strategy == "custom" or payload.term_category == "other":
                    raise ValueError("This strategy and category cannot be remembered")
                preference = StrategyPreferenceCreate(
                    team_key=payload.team_key,
                    scope=payload.preference_scope,
                    owner_key=payload.created_by_key if payload.preference_scope == "personal" else None,
                    term_category=payload.term_category,
                    source_language=payload.source_language,
                    target_language=payload.target_language,
                    preferred_strategy=payload.translation_strategy,
                    created_by_key=payload.created_by_key,
                    created_by_name=payload.created_by_name,
                )
                await StrategyPreferenceRepository().upsert_with_connection(connection, preference)
        return TermRead.model_validate(dict(row))

    async def update(
        self, term_id: UUID, payload: TermUpdate, team_key: str | None = None,
        user_key: str | None = None,
    ) -> TermRead | None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get(term_id, team_key, user_key)

        allowed_fields = [
            "source", "target", "mode", "note", "creation_method",
            "source_language", "target_language", "translation_strategy", "term_category",
        ]
        set_parts: list[str] = []
        values: list[object] = [term_id, team_key, user_key]
        for field in allowed_fields:
            if field in updates:
                values.append(updates[field])
                set_parts.append(f"{field} = ${len(values)}")

        query = f"""
            update terms
            set {", ".join(set_parts)}, updated_at = now()
            where id = $1
              and ($2::text is null or team_key = $2)
              and ($3::text is null or scope = 'team' or owner_key = $3)
            returning
                id, source, target, mode, note, team_key, scope, owner_key,
                source_language, target_language, created_by_key, created_by_name,
                creation_method, translation_strategy, term_category, created_at, updated_at
        """
        row = await database.fetchrow(query, *values)
        return TermRead.model_validate(dict(row)) if row else None

    async def get(
        self, term_id: UUID, team_key: str | None = None, user_key: str | None = None,
    ) -> TermRead | None:
        row = await database.fetchrow(
            """
            select
                id, source, target, mode, note, team_key, scope, owner_key,
                source_language, target_language, created_by_key, created_by_name,
                creation_method, translation_strategy, term_category, created_at, updated_at
            from terms
            where id = $1
              and ($2::text is null or team_key = $2)
              and ($3::text is null or scope = 'team' or owner_key = $3)
            """,
            term_id,
            team_key,
            user_key,
        )
        return TermRead.model_validate(dict(row)) if row else None

    async def delete(
        self, term_id: UUID, team_key: str | None = None, user_key: str | None = None,
    ) -> bool:
        deleted_id = await database.fetchval(
            """
            delete from terms
            where id = $1
              and ($2::text is null or team_key = $2)
              and ($3::text is null or scope = 'team' or owner_key = $3)
            returning id
            """,
            term_id,
            team_key,
            user_key,
        )
        return deleted_id is not None


class ContactRepository:
    async def list(self, q: str | None, limit: int, team_key: str = "team-1") -> list[ContactRead]:
        rows = await database.fetch(
            """
            select
                id, name, company, role, country, tone_style, communication_preferences,
                note, team_key, created_by_key, created_by_name, created_at, updated_at
            from contacts
            where team_key = $1 and (
                $2::text is null
                or name ilike '%' || $2 || '%'
                or coalesce(company, '') ilike '%' || $2 || '%'
                or coalesce(role, '') ilike '%' || $2 || '%'
                or coalesce(country, '') ilike '%' || $2 || '%'
                or coalesce(communication_preferences, '') ilike '%' || $2 || '%'
            )
            order by name asc
            limit $3
            """,
            team_key,
            q,
            limit,
        )
        return [ContactRead.model_validate(dict(row)) for row in rows]

    async def create(self, payload: ContactCreate) -> ContactRead:
        row = await database.fetchrow(
            """
            insert into contacts (
                name, company, role, country, tone_style, communication_preferences,
                note, team_key, created_by_key, created_by_name
            )
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            returning
                id, name, company, role, country, tone_style, communication_preferences,
                note, team_key, created_by_key, created_by_name, created_at, updated_at
            """,
            payload.name,
            payload.company,
            payload.role,
            payload.country,
            payload.tone_style,
            payload.communication_preferences,
            payload.note,
            payload.team_key,
            payload.created_by_key,
            payload.created_by_name,
        )
        return ContactRead.model_validate(dict(row))

    async def update(
        self, contact_id: UUID, payload: ContactUpdate, team_key: str | None = None,
    ) -> ContactRead | None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get(contact_id, team_key)

        allowed_fields = [
            "name", "company", "role", "country", "tone_style",
            "communication_preferences", "note",
        ]
        set_parts: list[str] = []
        values: list[object] = [contact_id, team_key]
        for field in allowed_fields:
            if field in updates:
                values.append(updates[field])
                set_parts.append(f"{field} = ${len(values)}")

        query = f"""
            update contacts
            set {", ".join(set_parts)}, updated_at = now()
            where id = $1 and ($2::text is null or team_key = $2)
            returning
                id, name, company, role, country, tone_style, communication_preferences,
                note, team_key, created_by_key, created_by_name, created_at, updated_at
        """
        row = await database.fetchrow(query, *values)
        return ContactRead.model_validate(dict(row)) if row else None

    async def get(self, contact_id: UUID, team_key: str | None = None) -> ContactRead | None:
        row = await database.fetchrow(
            """
            select
                id, name, company, role, country, tone_style, communication_preferences,
                note, team_key, created_by_key, created_by_name, created_at, updated_at
            from contacts
            where id = $1 and ($2::text is null or team_key = $2)
            """,
            contact_id,
            team_key,
        )
        return ContactRead.model_validate(dict(row)) if row else None

    async def delete(self, contact_id: UUID, team_key: str | None = None) -> bool:
        deleted_id = await database.fetchval(
            "delete from contacts where id = $1 and ($2::text is null or team_key = $2) returning id",
            contact_id,
            team_key,
        )
        return deleted_id is not None


class HistoryRepository:
    async def list(
        self,
        team_id: str,
        user_id: str,
        scope: str,
        limit: int,
    ) -> list[HistoryRead]:
        rows = await database.fetch(
            """
            select
                id, team_id, user_id, executor_name, mode, source_language,
                target_language, source_text, translated_text, recipient_id,
                recipient_name, file_name, applied_terms, created_at, updated_at
            from translation_history
            where team_id = $1
              and ($2 = 'team' or user_id = $3)
            order by created_at desc
            limit $4
            """,
            team_id,
            scope,
            user_id,
            limit,
        )
        return [_history_from_row(row) for row in rows]

    async def create(self, payload: HistoryCreate) -> HistoryRead:
        row = await database.fetchrow(
            """
            insert into translation_history (
                team_id, user_id, executor_name, mode, source_language,
                target_language, source_text, translated_text, recipient_id,
                recipient_name, file_name, applied_terms
            )
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb)
            returning
                id, team_id, user_id, executor_name, mode, source_language,
                target_language, source_text, translated_text, recipient_id,
                recipient_name, file_name, applied_terms, created_at, updated_at
            """,
            payload.team_id,
            payload.user_id,
            payload.executor_name,
            payload.mode,
            payload.source_language,
            payload.target_language,
            payload.source_text,
            payload.translated_text,
            payload.recipient_id,
            payload.recipient_name,
            payload.file_name,
            json.dumps(payload.applied_terms, ensure_ascii=False),
        )
        return _history_from_row(row)

    async def update(
        self,
        history_id: UUID,
        payload: HistoryUpdate,
        team_id: str,
        user_id: str,
    ) -> HistoryRead | None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return await self.get(history_id, team_id, user_id)

        set_parts: list[str] = []
        values: list[object] = [history_id, team_id, user_id]
        if "translated_text" in updates:
            values.append(updates["translated_text"])
            set_parts.append(f"translated_text = ${len(values)}")
        if "applied_terms" in updates:
            values.append(json.dumps(updates["applied_terms"], ensure_ascii=False))
            set_parts.append(f"applied_terms = ${len(values)}::jsonb")

        row = await database.fetchrow(
            f"""
            update translation_history
            set {", ".join(set_parts)}, updated_at = now()
            where id = $1 and team_id = $2 and user_id = $3
            returning
                id, team_id, user_id, executor_name, mode, source_language,
                target_language, source_text, translated_text, recipient_id,
                recipient_name, file_name, applied_terms, created_at, updated_at
            """,
            *values,
        )
        return _history_from_row(row) if row else None

    async def get(self, history_id: UUID, team_id: str, user_id: str) -> HistoryRead | None:
        row = await database.fetchrow(
            """
            select
                id, team_id, user_id, executor_name, mode, source_language,
                target_language, source_text, translated_text, recipient_id,
                recipient_name, file_name, applied_terms, created_at, updated_at
            from translation_history
            where id = $1 and team_id = $2 and user_id = $3
            """,
            history_id,
            team_id,
            user_id,
        )
        return _history_from_row(row) if row else None

    async def delete(self, history_id: UUID, team_id: str, user_id: str) -> bool:
        deleted_id = await database.fetchval(
            """
            delete from translation_history
            where id = $1 and team_id = $2 and user_id = $3
            returning id
            """,
            history_id,
            team_id,
            user_id,
        )
        return deleted_id is not None


def _history_from_row(row) -> HistoryRead:
    data = dict(row)
    if isinstance(data.get("applied_terms"), str):
        data["applied_terms"] = json.loads(data["applied_terms"])
    return HistoryRead.model_validate(data)


class StrategyPreferenceRepository:
    async def list(
        self,
        team_key: str,
        user_key: str | None,
        scopes: list[str],
        source_language: str | None = None,
        target_language: str | None = None,
        effective: bool = False,
    ) -> list[StrategyPreferenceRead]:
        rows = await database.fetch(
            """
            select
                id, team_key, scope, owner_key, term_category, source_language,
                target_language, preferred_strategy, created_by_key, created_by_name,
                created_at, updated_at
            from strategy_preferences
            where team_key = $1
            and scope = any($2::text[])
            and (scope = 'team' or owner_key = $3)
            and ($4::text is null or source_language = $4)
            and ($5::text is null or target_language = $5)
            order by case when scope = 'personal' then 0 else 1 end, term_category
            """,
            team_key,
            scopes,
            user_key,
            source_language,
            target_language,
        )
        preferences = [StrategyPreferenceRead.model_validate(dict(row)) for row in rows]
        if not effective:
            return preferences

        resolved: dict[tuple[str, str, str], StrategyPreferenceRead] = {}
        for preference in preferences:
            key = (
                preference.term_category,
                preference.source_language,
                preference.target_language,
            )
            resolved.setdefault(key, preference)
        return list(resolved.values())

    async def upsert(self, payload: StrategyPreferenceCreate) -> StrategyPreferenceRead:
        pool = database.require_pool()
        async with pool.acquire() as connection, connection.transaction():
            row = await self.upsert_with_connection(connection, payload)
        return StrategyPreferenceRead.model_validate(dict(row))

    async def upsert_with_connection(self, connection, payload: StrategyPreferenceCreate):
        return await connection.fetchrow(
            """
            insert into strategy_preferences (
                team_key, scope, owner_key, term_category, source_language,
                target_language, preferred_strategy, created_by_key, created_by_name
            )
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            on conflict (
                team_key, scope, (coalesce(owner_key, '')), term_category,
                source_language, target_language
            ) do update set
                preferred_strategy = excluded.preferred_strategy,
                created_by_key = excluded.created_by_key,
                created_by_name = excluded.created_by_name,
                updated_at = now()
            returning
                id, team_key, scope, owner_key, term_category, source_language,
                target_language, preferred_strategy, created_by_key, created_by_name,
                created_at, updated_at
            """,
            payload.team_key,
            payload.scope,
            payload.owner_key if payload.scope == "personal" else None,
            payload.term_category,
            payload.source_language,
            payload.target_language,
            payload.preferred_strategy,
            payload.created_by_key,
            payload.created_by_name,
        )

    async def delete(self, preference_id: UUID, team_key: str, user_key: str) -> bool:
        deleted_id = await database.fetchval(
            """
            delete from strategy_preferences
            where id = $1
            and team_key = $2
            and (scope = 'team' or owner_key = $3)
            returning id
            """,
            preference_id,
            team_key,
            user_key,
        )
        return deleted_id is not None

class MemoryRepository:
    async def list(self, limit: int, team_key: str, user_key: str) -> list[MemoryRead]:
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
                team_key,
                user_key,
                created_at,
                updated_at
            from translation_memories
            where team_key = $1 and user_key = $2
            order by updated_at desc
            limit $3
            """,
            team_key,
            user_key,
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
        team_key: str,
        user_key: str,
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
                team_key,
                user_key,
                created_at,
                updated_at
            from translation_memories
            where source_text = $1
                and target_language = $2
                and tone = $3
                and purpose = $4
                and contact_id is not distinct from $5::uuid
                and team_key = $6
                and user_key = $7
            order by updated_at desc
            limit 1
            """,
            source_text,
            target_language,
            tone,
            purpose,
            contact_id,
            team_key,
            user_key,
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
                , team_key
                , user_key
            )
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            returning
                id,
                source_text,
                source_language,
                target_language,
                tone,
                purpose,
                contact_id,
                result_text,
                team_key,
                user_key,
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
            payload.team_key,
            payload.user_key,
        )
        return MemoryRead.model_validate(dict(row))


class TermSuggestionRepository:
    async def list(
        self,
        status: SuggestionStatus | None,
        q: str | None,
        limit: int,
        team_key: str = "team-1",
        source_language: str | None = None,
        target_language: str | None = None,
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
                team_key,
                created_by_key,
                created_by_name,
                source_language,
                target_language,
                creation_method,
                translation_strategy,
                term_category,
                created_at,
                updated_at
            from term_suggestions
            where team_key = $1
            and ($2::text is null or source_language = $2)
            and ($3::text is null or target_language = $3)
            and (
                $4::text is null
                or status = $4
            )
            and (
                $5::text is null
                or source ilike '%' || $5 || '%'
                or coalesce(target, '') ilike '%' || $5 || '%'
                or coalesce(reason, '') ilike '%' || $5 || '%'
            )
            order by updated_at desc
            limit $6
            """,
            team_key,
            source_language,
            target_language,
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
                existing_id = await connection.fetchval(
                    """
                    select id
                    from term_suggestions
                    where team_key = $1
                    and source_language = $2
                    and target_language = $3
                    and lower(source) = lower($4)
                    and status = 'pending'
                    order by updated_at desc
                    limit 1
                    """,
                    suggestion.team_key,
                    suggestion.source_language,
                    suggestion.target_language,
                    suggestion.source,
                )
                if existing_id is not None:
                    row = await connection.fetchrow(
                        """
                        update term_suggestions
                        set document_text = $2,
                            target = $3,
                            mode = $4,
                            reason = $5,
                            evidence = $6,
                            confidence = $7,
                            creation_method = $8,
                            translation_strategy = $9,
                            term_category = $10,
                            updated_at = now()
                        where id = $1
                        returning
                            id, document_text, source, target, mode, reason, evidence,
                            confidence, status, approved_term_id, team_key, created_by_key,
                            created_by_name, source_language, target_language, creation_method,
                            translation_strategy, term_category,
                            created_at, updated_at
                        """,
                        existing_id,
                        suggestion.document_text,
                        suggestion.target,
                        suggestion.mode,
                        suggestion.reason,
                        suggestion.evidence,
                        suggestion.confidence,
                        suggestion.creation_method,
                        suggestion.translation_strategy,
                        suggestion.term_category,
                    )
                else:
                    row = await connection.fetchrow(
                    """
                        insert into term_suggestions (
                            document_text,
                            source,
                            target,
                            mode,
                            reason,
                            evidence,
                            confidence,
                            team_key,
                            created_by_key,
                            created_by_name,
                            source_language,
                            target_language,
                            creation_method,
                            translation_strategy,
                            term_category
                        )
                        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
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
                            team_key,
                            created_by_key,
                            created_by_name,
                            source_language,
                            target_language,
                            creation_method,
                            translation_strategy,
                            term_category,
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
                        suggestion.team_key,
                        suggestion.created_by_key,
                        suggestion.created_by_name,
                        suggestion.source_language,
                        suggestion.target_language,
                        suggestion.creation_method,
                        suggestion.translation_strategy,
                        suggestion.term_category,
                    )
                rows.append(row)

        return [TermSuggestionRead.model_validate(dict(row)) for row in rows]

    async def get(
        self, suggestion_id: UUID, team_key: str | None = None,
    ) -> TermSuggestionRead | None:
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
                team_key,
                created_by_key,
                created_by_name,
                source_language,
                target_language,
                creation_method,
                translation_strategy,
                term_category,
                created_at,
                updated_at
            from term_suggestions
            where id = $1 and ($2::text is null or team_key = $2)
            """,
            suggestion_id,
            team_key,
        )
        return TermSuggestionRead.model_validate(dict(row)) if row else None

    async def approve(
        self,
        suggestion_id: UUID,
        payload: TermSuggestionApprove,
        team_key: str | None = None,
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
                        approved_term_id,
                        team_key,
                        created_by_key,
                        created_by_name,
                        source_language,
                        target_language,
                        creation_method,
                        translation_strategy,
                        term_category
                    from term_suggestions
                    where id = $1 and ($2::text is null or team_key = $2)
                    for update
                    """,
                suggestion_id,
                team_key,
            )
            if suggestion is None:
                return None
            if suggestion["status"] == "approved":
                return await self.get(suggestion_id, team_key)

            translation_strategy = payload.translation_strategy or (
                "preserve" if payload.mode == "preserve" else suggestion["translation_strategy"]
            )
            term_category = payload.term_category or suggestion["term_category"]
            mode = "preserve" if translation_strategy == "preserve" else (payload.mode or "translate")
            target = payload.target if payload.target is not None else suggestion["target"]
            note = payload.note or suggestion["reason"]
            if mode == "preserve":
                target = None
            was_edited = payload.target is not None or (
                payload.mode is not None and payload.mode != suggestion["mode"]
            )
            creation_method = payload.creation_method or (
                "direct_edit" if was_edited else suggestion["creation_method"]
            )

            existing_term = await connection.fetchrow(
                """
                    select id
                    from terms
                    where team_key = $1
                    and scope = $2
                    and coalesce(owner_key, '') = coalesce($3::text, '')
                    and source_language = $4
                    and target_language = $5
                    and lower(source) = lower($6)
                    limit 1
                    """,
                suggestion["team_key"],
                payload.scope,
                payload.created_by_key if payload.scope == "personal" else None,
                suggestion["source_language"],
                suggestion["target_language"],
                suggestion["source"],
            )

            if existing_term is not None:
                term = await connection.fetchrow(
                    """
                        update terms
                        set target = $2,
                            mode = $3,
                            note = coalesce($4, note),
                            creation_method = $5,
                            translation_strategy = $6,
                            term_category = $7,
                            updated_at = now()
                        where id = $1
                        returning id
                        """,
                    existing_term["id"],
                    target,
                    mode,
                    note,
                    creation_method,
                    translation_strategy,
                    term_category,
                )
            else:
                term = await connection.fetchrow(
                    """
                        insert into terms (
                            source, target, mode, note, team_key, scope, owner_key,
                            source_language, target_language, created_by_key,
                            created_by_name, creation_method, translation_strategy, term_category
                        )
                        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        returning id
                        """,
                    suggestion["source"],
                    target,
                    mode,
                    note,
                    suggestion["team_key"],
                    payload.scope,
                    payload.created_by_key if payload.scope == "personal" else None,
                    suggestion["source_language"],
                    suggestion["target_language"],
                    payload.created_by_key or suggestion["created_by_key"],
                    payload.created_by_name or suggestion["created_by_name"],
                    creation_method,
                    translation_strategy,
                    term_category,
                )

            if term is None:
                return None

            if payload.preference_scope is not None:
                preference = StrategyPreferenceCreate(
                    team_key=suggestion["team_key"],
                    scope=payload.preference_scope,
                    owner_key=(payload.created_by_key or suggestion["created_by_key"])
                    if payload.preference_scope == "personal" else None,
                    term_category=term_category,
                    source_language=suggestion["source_language"],
                    target_language=suggestion["target_language"],
                    preferred_strategy=translation_strategy,
                    created_by_key=payload.created_by_key or suggestion["created_by_key"],
                    created_by_name=payload.created_by_name or suggestion["created_by_name"],
                )
                await StrategyPreferenceRepository().upsert_with_connection(connection, preference)

            row = await connection.fetchrow(
                """
                    update term_suggestions
                    set status = 'approved',
                        approved_term_id = $2,
                        target = $3,
                        mode = $4,
                        creation_method = $5,
                        translation_strategy = $6,
                        term_category = $7,
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
                        team_key,
                        created_by_key,
                        created_by_name,
                        source_language,
                        target_language,
                        creation_method,
                        translation_strategy,
                        term_category,
                        created_at,
                        updated_at
                    """,
                suggestion_id,
                term["id"],
                target,
                mode,
                creation_method,
                translation_strategy,
                term_category,
            )
            return TermSuggestionRead.model_validate(dict(row)) if row else None

    async def reject(
        self,
        suggestion_id: UUID,
        payload: TermSuggestionReject,
        team_key: str | None = None,
    ) -> TermSuggestionRead | None:
        current = await self.get(suggestion_id, team_key)
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
            where id = $1 and ($3::text is null or team_key = $3)
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
                team_key,
                created_by_key,
                created_by_name,
                source_language,
                target_language,
                creation_method,
                translation_strategy,
                term_category,
                created_at,
                updated_at
            """,
            suggestion_id,
            payload.reason,
            team_key,
        )
        return TermSuggestionRead.model_validate(dict(row)) if row else None

    async def rejected_sources(
        self,
        team_key: str,
        source_language: str,
        target_language: str,
    ) -> set[str]:
        rows = await database.fetch(
            """
            select source
            from term_suggestions
            where team_key = $1
            and source_language = $2
            and target_language = $3
            and status = 'rejected'
            """,
            team_key,
            source_language,
            target_language,
        )
        return {str(row["source"]).casefold() for row in rows}
