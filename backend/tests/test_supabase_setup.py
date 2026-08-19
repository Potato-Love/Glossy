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
        settings = Settings(_env_file=None, OPENAI_API_KEY="sk-proj-replace-me")

        self.assertIsNone(settings.openai_api_key)

    def test_describe_connection_url_detects_pooler_modes(self) -> None:
        self.assertIn(
            "transaction pooler",
            describe_connection_url(
                "postgresql://postgres.ref:pw@aws-0.ap.pooler.supabase.com:6543/postgres"
            ),
        )
        self.assertIn(
            "session pooler",
            describe_connection_url(
                "postgresql://postgres.ref:pw@aws-0.ap.pooler.supabase.com:5432/postgres"
            ),
        )
        self.assertIn(
            "direct",
            describe_connection_url("postgresql://postgres:pw@db.ref.supabase.co:5432/postgres"),
        )

    def test_seed_migration_is_opt_in(self) -> None:
        without_seed = [path.name for path in migration_files(include_seed=False)]
        with_seed = [path.name for path in migration_files(include_seed=True)]

        self.assertIn("001_init.sql", without_seed)
        self.assertIn("003_expand_language_codes.sql", without_seed)
        self.assertNotIn("002_seed_demo.sql", without_seed)
        self.assertIn("002_seed_demo.sql", with_seed)

    def test_checksum_is_stable(self) -> None:
        self.assertEqual(checksum_sql("select 1;"), checksum_sql("select 1;"))


if __name__ == "__main__":
    unittest.main()
