alter table terms
    add column if not exists translation_strategy text not null default 'custom',
    add column if not exists term_category text not null default 'other';

alter table terms drop constraint if exists terms_translation_strategy_check;
alter table terms add constraint terms_translation_strategy_check
    check (translation_strategy in ('preserve', 'transliteration', 'semantic_translation', 'custom'));
alter table terms drop constraint if exists terms_term_category_check;
alter table terms add constraint terms_term_category_check
    check (term_category in (
        'team_name', 'organization_name', 'brand_name', 'service_name', 'product_name',
        'project_name', 'person_name', 'acronym', 'technical_term', 'other'
    ));

update terms
set translation_strategy = case
    when mode = 'preserve' then 'preserve'
    when creation_method = 'transliteration' then 'transliteration'
    when creation_method = 'semantic_translation' then 'semantic_translation'
    else 'custom'
end
where translation_strategy = 'custom';

alter table term_suggestions
    add column if not exists translation_strategy text not null default 'semantic_translation',
    add column if not exists term_category text not null default 'other';

alter table term_suggestions drop constraint if exists term_suggestions_translation_strategy_check;
alter table term_suggestions add constraint term_suggestions_translation_strategy_check
    check (translation_strategy in ('preserve', 'transliteration', 'semantic_translation', 'custom'));
alter table term_suggestions drop constraint if exists term_suggestions_term_category_check;
alter table term_suggestions add constraint term_suggestions_term_category_check
    check (term_category in (
        'team_name', 'organization_name', 'brand_name', 'service_name', 'product_name',
        'project_name', 'person_name', 'acronym', 'technical_term', 'other'
    ));

update term_suggestions
set translation_strategy = case
    when mode = 'preserve' then 'preserve'
    when creation_method = 'transliteration' then 'transliteration'
    when creation_method = 'semantic_translation' then 'semantic_translation'
    else 'custom'
end
where translation_strategy = 'semantic_translation';

create table if not exists strategy_preferences (
    id uuid primary key default gen_random_uuid(),
    team_key text not null,
    scope text not null check (scope in ('team', 'personal')),
    owner_key text,
    term_category text not null check (term_category in (
        'team_name', 'organization_name', 'brand_name', 'service_name', 'product_name',
        'project_name', 'person_name', 'acronym', 'technical_term'
    )),
    source_language text not null check (source_language in ('auto', 'ko', 'en', 'de', 'fr', 'ja', 'zh')),
    target_language text not null check (target_language in ('ko', 'en', 'de', 'fr', 'ja', 'zh')),
    preferred_strategy text not null check (preferred_strategy in ('preserve', 'transliteration', 'semantic_translation')),
    created_by_key text not null,
    created_by_name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint strategy_preferences_personal_owner_check
        check (scope = 'team' or owner_key is not null)
);

create unique index if not exists idx_strategy_preferences_context_unique
    on strategy_preferences (
        team_key, scope, coalesce(owner_key, ''), term_category, source_language, target_language
    );
create index if not exists idx_strategy_preferences_lookup
    on strategy_preferences (team_key, source_language, target_language, scope, owner_key);

drop trigger if exists strategy_preferences_set_updated_at on strategy_preferences;
create trigger strategy_preferences_set_updated_at
before update on strategy_preferences
for each row execute function set_updated_at();
