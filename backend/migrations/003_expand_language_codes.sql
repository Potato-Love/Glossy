alter table translation_memories
    drop constraint if exists translation_memories_source_language_check;

alter table translation_memories
    add constraint translation_memories_source_language_check
    check (source_language in ('auto', 'ko', 'en', 'de', 'fr', 'ja', 'zh'));

alter table translation_memories
    drop constraint if exists translation_memories_target_language_check;

alter table translation_memories
    add constraint translation_memories_target_language_check
    check (target_language in ('ko', 'en', 'de', 'fr', 'ja', 'zh'));
