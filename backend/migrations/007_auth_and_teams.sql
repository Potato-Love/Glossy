create table if not exists users (
    id text primary key default gen_random_uuid()::text,
    nickname text not null check (char_length(nickname) between 2 and 20),
    name text,
    organization text,
    position text,
    country text,
    profile_completed boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists idx_users_nickname_unique
    on users (lower(nickname));

create table if not exists teams (
    id text primary key default gen_random_uuid()::text,
    name text not null check (char_length(name) between 1 and 50),
    invite_code text not null,
    created_by_key text references users(id) on delete set null,
    is_legacy boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists idx_teams_invite_code_unique
    on teams (invite_code);

insert into teams (id, name, invite_code, is_legacy)
select distinct legacy_key, '기존 데이터', 'LEGACY-' || md5(legacy_key), true
from (
    select team_key as legacy_key from terms
    union select team_key from contacts
    union select team_key from term_suggestions
    union select team_key from strategy_preferences
) legacy
where legacy_key is not null and legacy_key <> ''
on conflict (id) do nothing;

create table if not exists team_memberships (
    team_id text not null references teams(id) on delete cascade,
    user_id text not null references users(id) on delete cascade,
    role text not null default 'member' check (role in ('owner', 'member')),
    created_at timestamptz not null default now(),
    primary key (team_id, user_id)
);

create index if not exists idx_team_memberships_user
    on team_memberships (user_id, created_at);

create table if not exists auth_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id text not null references users(id) on delete cascade,
    token_hash text not null unique,
    expires_at timestamptz not null,
    revoked_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists idx_auth_sessions_active
    on auth_sessions (token_hash, expires_at)
    where revoked_at is null;

alter table translation_memories
    add column if not exists team_key text not null default 'team-1',
    add column if not exists user_key text;

create index if not exists idx_translation_memories_team_user
    on translation_memories (team_key, user_key, created_at desc);

drop trigger if exists users_set_updated_at on users;
create trigger users_set_updated_at
before update on users
for each row execute function set_updated_at();

drop trigger if exists teams_set_updated_at on teams;
create trigger teams_set_updated_at
before update on teams
for each row execute function set_updated_at();
