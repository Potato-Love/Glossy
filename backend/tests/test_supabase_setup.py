import unittest

from app.core.config import Settings
from scripts.apply_migrations import checksum_sql, migration_files
from scripts.check_db import describe_connection_url


class SupabaseSetupTest(unittest.TestCase):
    def test_statement_cache_defaults_to_supabase_pooler_safe_value(self) -> None:
        settings = Settings(_env_file=None)

        self.assertEqual(settings.db_statement_cache_size, 0)
        self.assertEqual(settings.database_ssl_mode, "require")
        self.assertEqual(settings.max_image_bytes, 4 * 1024 * 1024)

    def test_cors_origins_accepts_comma_separated_env_value(self) -> None:
        settings = Settings(
            _env_file=None,
            CORS_ORIGINS="http://localhost:5173,https://glossy-prototype.vercel.app",
        )

        self.assertEqual(
            settings.cors_origins,
            ["http://localhost:5173", "https://glossy-prototype.vercel.app"],
        )

    def test_openai_placeholder_is_not_treated_as_configured(self) -> None:
        settings = Settings(_env_file=None, OPENAI_API_KEY="replace-with-openai-api-key")

        self.assertIsNone(settings.openai_api_key)

    def test_describe_connection_url_detects_pooler_modes(self) -> None:
        self.assertIn(
            "transaction pooler",
            describe_connection_url(
                "postgresql://postgres.ref@aws-0.ap.pooler.supabase.com:6543/postgres"
            ),
        )
        self.assertIn(
            "session pooler",
            describe_connection_url(
                "postgresql://postgres.ref@aws-0.ap.pooler.supabase.com:5432/postgres"
            ),
        )
        self.assertIn(
            "direct",
            describe_connection_url("postgresql://postgres@db.ref.supabase.co:5432/postgres"),
        )

    def test_migration_files_only_include_schema_migrations(self) -> None:
        files = [path.name for path in migration_files()]

        self.assertIn("001_init.sql", files)
        self.assertIn("003_expand_language_codes.sql", files)
        self.assertIn("004_glossary_context.sql", files)
        self.assertIn("005_translation_strategy_preferences.sql", files)
        self.assertIn("006_recipient_translation_context.sql", files)
        self.assertIn("007_auth_and_teams.sql", files)
        self.assertIn("008_translation_history.sql", files)
        self.assertFalse(any("seed" in filename.lower() for filename in files))

    def test_checksum_is_stable(self) -> None:
        self.assertEqual(checksum_sql("select 1;"), checksum_sql("select 1;"))


if __name__ == "__main__":
    unittest.main()
