alter table terms
    add column if not exists team_key text not null default 'team-1',
    add column if not exists scope text not null default 'team',
    add column if not exists owner_key text,
    add column if not exists source_language text not null default 'ko',
    add column if not exists target_language text not null default 'en',
    add column if not exists created_by_key text not null default 'legacy',
    add column if not exists created_by_name text not null default '기존 데이터',
    add column if not exists creation_method text not null default 'manual';

alter table terms drop constraint if exists terms_scope_check;
alter table terms add constraint terms_scope_check
    check (scope in ('team', 'personal'));
alter table terms drop constraint if exists terms_personal_owner_check;
alter table terms add constraint terms_personal_owner_check
    check (scope = 'team' or owner_key is not null);
alter table terms drop constraint if exists terms_source_language_check;
alter table terms add constraint terms_source_language_check
    check (source_language in ('auto', 'ko', 'en', 'de', 'fr', 'ja', 'zh'));
alter table terms drop constraint if exists terms_target_language_check;
alter table terms add constraint terms_target_language_check
    check (target_language in ('ko', 'en', 'de', 'fr', 'ja', 'zh'));
alter table terms drop constraint if exists terms_creation_method_check;
alter table terms add constraint terms_creation_method_check
    check (creation_method in ('manual', 'transliteration', 'semantic_translation', 'direct_edit'));

drop index if exists idx_terms_source_unique;
create unique index if not exists idx_terms_context_source_unique
    on terms (
        team_key,
        scope,
        coalesce(owner_key, ''),
        source_language,
        target_language,
        lower(source)
    );
create index if not exists idx_terms_translation_context
    on terms (team_key, source_language, target_language, scope, owner_key);

alter table term_suggestions
    add column if not exists team_key text not null default 'team-1',
    add column if not exists created_by_key text not null default 'legacy',
    add column if not exists created_by_name text not null default '기존 데이터',
    add column if not exists source_language text not null default 'ko',
    add column if not exists target_language text not null default 'en',
    add column if not exists creation_method text not null default 'semantic_translation';

alter table term_suggestions drop constraint if exists term_suggestions_source_language_check;
alter table term_suggestions add constraint term_suggestions_source_language_check
    check (source_language in ('auto', 'ko', 'en', 'de', 'fr', 'ja', 'zh'));
alter table term_suggestions drop constraint if exists term_suggestions_target_language_check;
alter table term_suggestions add constraint term_suggestions_target_language_check
    check (target_language in ('ko', 'en', 'de', 'fr', 'ja', 'zh'));
alter table term_suggestions drop constraint if exists term_suggestions_creation_method_check;
alter table term_suggestions add constraint term_suggestions_creation_method_check
    check (creation_method in ('manual', 'transliteration', 'semantic_translation', 'direct_edit'));

create index if not exists idx_term_suggestions_team_status
    on term_suggestions (
        team_key,
        source_language,
        target_language,
        status,
        lower(source)
    );
