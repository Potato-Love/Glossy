create table if not exists translation_history (
    id uuid primary key default gen_random_uuid(),
    team_id text not null references teams(id) on delete cascade,
    user_id text not null references users(id) on delete cascade,
    executor_name text not null check (char_length(executor_name) between 1 and 120),
    mode text not null check (mode in ('text', 'document', 'image')),
    source_language text not null check (source_language in ('auto', 'ko', 'en', 'de', 'fr', 'ja', 'zh')),
    target_language text not null check (target_language in ('ko', 'en', 'de', 'fr', 'ja', 'zh')),
    source_text text not null check (char_length(source_text) between 1 and 10000),
    translated_text text not null check (char_length(translated_text) between 1 and 20000),
    recipient_id uuid references contacts(id) on delete set null,
    recipient_name text,
    file_name text,
    applied_terms jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_translation_history_team_created
    on translation_history (team_id, created_at desc);

create index if not exists idx_translation_history_user_created
    on translation_history (team_id, user_id, created_at desc);

drop trigger if exists translation_history_set_updated_at on translation_history;
create trigger translation_history_set_updated_at
before update on translation_history
for each row execute function set_updated_at();
