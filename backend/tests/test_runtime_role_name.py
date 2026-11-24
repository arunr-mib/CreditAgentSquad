"""v2 runs beside v1 on one database server, so each needs its own runtime role: a login that is a
member of v1's role must not be able to write v2's tables, and the reverse."""
import pytest
from app.core import ledger
from app.core.config import get_settings


@pytest.fixture()
def settings_env(monkeypatch):
    def set_env(role, schema=None):
        for key, value in (("DB_RUNTIME_ROLE", role), ("DB_SCHEMA", schema)):
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
        get_settings.cache_clear()
    yield set_env
    get_settings.cache_clear()


def test_without_the_new_settings_v1s_role_and_schema_defaults_hold(settings_env):
    """v1 is deployed without DB_RUNTIME_ROLE: its role must stay squad_runtime. (v1's schema
    default, `squad`, is set by the Vercel entry point: tests/deploy/test_vercel_entry.py.)"""
    settings_env(None)
    assert ledger.runtime_role_name() == "squad_runtime" == ledger.RUNTIME_ROLE
    assert get_settings().db_runtime_role == "squad_runtime"


def test_the_runtime_role_comes_from_the_setting_and_the_grants_name_it(settings_env):
    settings_env("squad2_runtime")
    assert ledger.runtime_role_name() == "squad2_runtime"
    sql = ledger.runtime_role_sql(ledger.runtime_role_name(), schema="squad2")
    assert "GRANT SELECT, INSERT ON squad2.ledger_events TO squad2_runtime;" in sql
    assert "squad_runtime;" not in sql.replace("squad2_runtime", "")


def test_a_runtime_role_setting_that_is_not_a_plain_name_is_refused(settings_env):
    settings_env("squad2_runtime; DROP TABLE ledger_events")
    with pytest.raises(ValueError):
        ledger.runtime_role_name()


def test_downgrade_of_0003_refuses_a_schema_that_is_not_a_plain_name_before_touching_the_database(settings_env, monkeypatch):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0003_runtime_role_for_the_ledger.py"
    spec = importlib.util.spec_from_file_location("m0003", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    touched = []
    monkeypatch.setattr(module, "op", type("Op", (), {"get_bind": staticmethod(lambda: touched.append("bind")),
                                                      "execute": staticmethod(lambda sql: touched.append(sql))}))
    settings_env("squad2_runtime", schema="squad2; DROP TABLE ledger_events")
    with pytest.raises(ValueError):
        module.downgrade()
    assert touched == []
