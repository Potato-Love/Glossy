alter table contacts
    add column if not exists team_key text not null default 'team-1',
    add column if not exists country text,
    add column if not exists tone_style text not null default 'polite_concise',
    add column if not exists communication_preferences text,
    add column if not exists created_by_key text not null default 'legacy',
    add column if not exists created_by_name text not null default '기존 데이터';

update contacts
set communication_preferences = note
where communication_preferences is null and note is not null;

alter table contacts drop constraint if exists contacts_tone_style_check;
alter table contacts add constraint contacts_tone_style_check
    check (tone_style in (
        'polite_concise',
        'friendly_professional',
        'formal_official',
        'warm_persuasive'
    ));

drop index if exists idx_contacts_name_unique;
create unique index if not exists idx_contacts_team_name_unique
    on contacts (team_key, lower(name));
create index if not exists idx_contacts_team_lookup
    on contacts (team_key, name);
