from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

from asyncpg.exceptions import UniqueViolationError

from app.auth_schemas import TeamMemberRead, TeamRead, UserProfileUpdate, UserRead
from app.db import database


SESSION_DAYS = 7
INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _user_from_row(row) -> UserRead:
    return UserRead.model_validate(dict(row))


def _invite_code() -> str:
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))


class AuthRepository:
    async def create_user(self, nickname: str) -> UserRead:
        row = await database.fetchrow(
            """
            insert into users (nickname)
            values ($1)
            returning id, nickname, name, organization, position, country, profile_completed
            """,
            nickname,
        )
        return _user_from_row(row)

    async def get_user_by_nickname(self, nickname: str) -> UserRead | None:
        row = await database.fetchrow(
            """
            select id, nickname, name, organization, position, country, profile_completed
            from users
            where lower(nickname) = lower($1)
            """,
            nickname,
        )
        return _user_from_row(row) if row else None

    async def get_user_by_active_session(self, token_hash: str) -> UserRead | None:
        row = await database.fetchrow(
            """
            select u.id, u.nickname, u.name, u.organization, u.position, u.country,
                   u.profile_completed
            from auth_sessions s
            join users u on u.id = s.user_id
            where s.token_hash = $1
              and s.revoked_at is null
              and s.expires_at > now()
            """,
            token_hash,
        )
        return _user_from_row(row) if row else None

    async def create_session(self, user_id: str, token_hash: str) -> datetime:
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
        await database.fetchval(
            """
            insert into auth_sessions (user_id, token_hash, expires_at)
            values ($1, $2, $3)
            returning id
            """,
            user_id,
            token_hash,
            expires_at,
        )
        return expires_at

    async def revoke_session(self, token_hash: str) -> None:
        await database.fetchval(
            """
            update auth_sessions
            set revoked_at = coalesce(revoked_at, now())
            where token_hash = $1
            returning id
            """,
            token_hash,
        )

    async def update_profile(self, user_id: str, payload: UserProfileUpdate) -> UserRead:
        row = await database.fetchrow(
            """
            update users
            set name = $2,
                nickname = $3,
                organization = $4,
                position = $5,
                country = $6,
                profile_completed = true
            where id = $1
            returning id, nickname, name, organization, position, country, profile_completed
            """,
            user_id,
            payload.name,
            payload.nickname,
            payload.organization,
            payload.position,
            payload.country,
        )
        return _user_from_row(row)


class TeamRepository:
    async def list_for_user(self, user_id: str) -> list[TeamRead]:
        rows = await database.fetch(
            """
            select t.id, t.name, m.role,
                   case when m.role = 'owner' then t.invite_code else null end as invite_code,
                   count(all_members.user_id)::int as member_count
            from team_memberships m
            join teams t on t.id = m.team_id and not t.is_legacy
            left join team_memberships all_members on all_members.team_id = t.id
            where m.user_id = $1
            group by t.id, t.name, m.role, t.invite_code, m.created_at
            order by m.created_at, t.name
            """,
            user_id,
        )
        return [TeamRead.model_validate(dict(row)) for row in rows]

    async def get_role(self, team_id: str, user_id: str) -> str | None:
        return await database.fetchval(
            """
            select m.role
            from team_memberships m
            join teams t on t.id = m.team_id and not t.is_legacy
            where m.team_id = $1 and m.user_id = $2
            """,
            team_id,
            user_id,
        )

    async def create(self, name: str, user_id: str) -> TeamRead:
        pool = database.require_pool()
        for _ in range(5):
            code = _invite_code()
            try:
                async with pool.acquire() as connection, connection.transaction():
                    row = await connection.fetchrow(
                        """
                        insert into teams (name, invite_code, created_by_key)
                        values ($1, $2, $3)
                        returning id, name, invite_code
                        """,
                        name,
                        code,
                        user_id,
                    )
                    await connection.execute(
                        """
                        insert into team_memberships (team_id, user_id, role)
                        values ($1, $2, 'owner')
                        """,
                        row["id"],
                        user_id,
                    )
                return TeamRead(
                    id=row["id"], name=row["name"], role="owner",
                    invite_code=row["invite_code"], member_count=1,
                )
            except UniqueViolationError:
                continue
        raise RuntimeError("초대 코드를 생성하지 못했습니다.")

    async def join(self, invite_code: str, user_id: str) -> TeamRead | None:
        pool = database.require_pool()
        async with pool.acquire() as connection, connection.transaction():
            team = await connection.fetchrow(
                """
                select id, name, invite_code
                from teams
                where invite_code = $1 and not is_legacy
                """,
                invite_code,
            )
            if team is None:
                return None
            await connection.execute(
                """
                insert into team_memberships (team_id, user_id, role)
                values ($1, $2, 'member')
                on conflict (team_id, user_id) do nothing
                """,
                team["id"],
                user_id,
            )
            membership = await connection.fetchrow(
                """
                select role from team_memberships where team_id = $1 and user_id = $2
                """,
                team["id"],
                user_id,
            )
            count = await connection.fetchval(
                "select count(*) from team_memberships where team_id = $1",
                team["id"],
            )
        return TeamRead(
            id=team["id"], name=team["name"], role=membership["role"],
            invite_code=team["invite_code"] if membership["role"] == "owner" else None,
            member_count=count,
        )

    async def update_name(self, team_id: str, name: str) -> TeamRead:
        row = await database.fetchrow(
            """
            update teams set name = $2 where id = $1
            returning id, name, invite_code
            """,
            team_id,
            name,
        )
        count = await database.fetchval(
            "select count(*) from team_memberships where team_id = $1",
            team_id,
        )
        return TeamRead(
            id=row["id"], name=row["name"], role="owner",
            invite_code=row["invite_code"], member_count=count,
        )

    async def rotate_invite_code(self, team_id: str) -> TeamRead:
        for _ in range(5):
            try:
                row = await database.fetchrow(
                    """
                    update teams set invite_code = $2 where id = $1
                    returning id, name, invite_code
                    """,
                    team_id,
                    _invite_code(),
                )
                count = await database.fetchval(
                    "select count(*) from team_memberships where team_id = $1",
                    team_id,
                )
                return TeamRead(
                    id=row["id"], name=row["name"], role="owner",
                    invite_code=row["invite_code"], member_count=count,
                )
            except UniqueViolationError:
                continue
        raise RuntimeError("초대 코드를 재발급하지 못했습니다.")

    async def list_members(self, team_id: str) -> list[TeamMemberRead]:
        rows = await database.fetch(
            """
            select u.id, u.nickname, u.name, u.organization, u.position, m.role
            from team_memberships m
            join users u on u.id = m.user_id
            where m.team_id = $1
            order by case when m.role = 'owner' then 0 else 1 end, m.created_at
            """,
            team_id,
        )
        return [TeamMemberRead.model_validate(dict(row)) for row in rows]
