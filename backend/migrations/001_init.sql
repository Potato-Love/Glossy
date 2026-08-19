create extension if not exists pgcrypto;

create table if not exists terms (
    id uuid primary key default gen_random_uuid(),
    source text not null check (char_length(source) between 1 and 120),
    target text,
    mode text not null default 'translate' check (mode in ('translate', 'preserve')),
    note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists contacts (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(name) between 1 and 120),
    company text,
    role text,
    note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists translation_memories (
    id uuid primary key default gen_random_uuid(),
    source_text text not null check (char_length(source_text) between 1 and 3000),
    source_language text not null default 'auto' check (source_language in ('auto', 'ko', 'en')),
    target_language text not null check (target_language in ('ko', 'en')),
    tone text not null check (tone in ('standard', 'polite', 'concise')),
    purpose text not null check (purpose in ('email', 'messenger', 'document', 'notice')),
    contact_id uuid references contacts(id) on delete set null,
    result_text text not null check (char_length(result_text) between 1 and 4000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists term_suggestions (
    id uuid primary key default gen_random_uuid(),
    document_text text not null check (char_length(document_text) between 1 and 10000),
    source text not null check (char_length(source) between 1 and 120),
    target text,
    mode text not null default 'preserve' check (mode in ('translate', 'preserve')),
    reason text,
    evidence text,
    confidence numeric(3,2) not null default 0.70 check (confidence between 0 and 1),
    status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
    approved_term_id uuid references terms(id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_terms_source on terms (lower(source));
create unique index if not exists idx_terms_source_unique on terms (lower(source));
create index if not exists idx_contacts_name on contacts (lower(name));
create unique index if not exists idx_contacts_name_unique on contacts (lower(name));
create index if not exists idx_translation_memories_lookup
    on translation_memories (target_language, tone, purpose, contact_id);
create index if not exists idx_term_suggestions_status
    on term_suggestions (status, updated_at desc);

create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists terms_set_updated_at on terms;
create trigger terms_set_updated_at
before update on terms
for each row execute function set_updated_at();

drop trigger if exists contacts_set_updated_at on contacts;
create trigger contacts_set_updated_at
before update on contacts
for each row execute function set_updated_at();

drop trigger if exists translation_memories_set_updated_at on translation_memories;
create trigger translation_memories_set_updated_at
before update on translation_memories
for each row execute function set_updated_at();

drop trigger if exists term_suggestions_set_updated_at on term_suggestions;
create trigger term_suggestions_set_updated_at
before update on term_suggestions
for each row execute function set_updated_at();
