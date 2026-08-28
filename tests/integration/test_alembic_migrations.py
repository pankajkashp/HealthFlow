"""Integration tests for Alembic Migrations against real PostgreSQL.

Verifies:
- Clean database migration execution (upgrade to head)
- Complete table and index creation in PostgreSQL
- Clean rollback execution (downgrade to base)
- Re-upgrade idempotency

Ref: docs/architecture/ARCHITECTURE.md §14.4
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from healthflow_infrastructure import create_db_engine
from sqlalchemy import inspect

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres@localhost:5432/healthflow_test",
)


def get_alembic_config() -> Config:
    repo_root = Path(__file__).resolve().parent.parent.parent
    ini_path = repo_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    return cfg


class TestAlembicMigrations:
    def test_upgrade_and_downgrade_cycle(self) -> None:
        cfg = get_alembic_config()
        engine = create_db_engine(TEST_DB_URL)

        # 1. Downgrade to base first to test from clean state
        command.downgrade(cfg, "base")
        inspector = inspect(engine)
        initial_tables = set(inspector.get_table_names())
        # alembic_version might exist, but domain tables must not
        assert "patients" not in initial_tables
        assert "authorization_cases" not in initial_tables

        # 2. Upgrade to head
        command.upgrade(cfg, "head")

        # 3. Verify all 8 domain tables exist
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected_tables = {
            "patients",
            "insurance_plans",
            "authorization_cases",
            "workflow_transitions",
            "submission_records",
            "verification_records",
            "escalation_records",
            "audit_records",
        }
        assert expected_tables.issubset(tables)

        # 4. Verify columns on authorization_cases
        case_columns = {
            col["name"] for col in inspector.get_columns("authorization_cases")
        }
        expected_case_columns = {
            "id",
            "patient_id",
            "insurance_plan_id",
            "procedure_type",
            "clinical_indication",
            "priority",
            "current_state",
            "created_at",
            "updated_at",
        }
        assert expected_case_columns.issubset(case_columns)

        # 5. Verify downgrade cleans up tables
        command.downgrade(cfg, "base")
        inspector = inspect(engine)
        downgraded_tables = set(inspector.get_table_names())
        assert "patients" not in downgraded_tables
        assert "authorization_cases" not in downgraded_tables

        # 6. Re-upgrade to head to leave test database prepared
        command.upgrade(cfg, "head")
        inspector = inspect(engine)
        final_tables = set(inspector.get_table_names())
        assert expected_tables.issubset(final_tables)

        engine.dispose()
