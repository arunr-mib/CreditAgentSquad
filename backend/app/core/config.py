"""Application settings, read from environment variables (and `.env` when present)."""
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# The largest document a person may upload. Larger files are refused before they are stored.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "local" is a developer's machine. Anything else is treated as a deployment, where the safe
    # choices are the defaults: the session cookie is sent over HTTPS only and the interactive
    # API documentation is not served. An unset value therefore fails safe.
    squad_env: str = "production"

    # The application connects as a login that is a member of `squad_runtime` and owns no table,
    # so it cannot switch off the ledger's append-only guard. Migrations and the owner-only
    # commands in `app.cli` use `migration_database_url`, the owner's connection. A local
    # development database may use one role for both.
    database_url: str = "postgresql+psycopg://squad:squad@localhost:5432/credit_agent_squad"
    migration_database_url: str = ""
    test_database_url: str = "postgresql+psycopg://squad:squad@localhost:5432/credit_agent_squad_test"
    session_secret: str = "change-me"
    session_hours: int = 12
    file_store_dir: str = "./var/files"
    # A read-only folder of document files to fall back on when a document's own file is missing
    # from the file store: a host whose disk does not persist ships the synthetic documents with
    # the deployment. Files are matched by content hash, never by name.
    file_fallback_dir: str = ""
    # Hosting on a shared database server: keep every table in this schema, and open a
    # connection per request instead of keeping a pool (serverless functions do not live long).
    db_schema: str = ""
    db_pool: str = ""  # "" = the default pool; "null" = no pool
    # The role the serving login is a member of (`app.core.ledger`). v1 uses the default; a second
    # deployment on the same server (v2: `squad2_runtime`) needs its own, or each could write the other's tables.
    db_runtime_role: str = "squad_runtime"

    # Leave unset to follow `squad_env`; set to override it.
    session_cookie_secure: bool | None = None
    api_docs_enabled: bool | None = None
    # Sign-in is refused for an account after this many failures inside the window.
    login_max_failures: int = 5
    login_lockout_minutes: int = 15

    # How much a document reading is trusted before a person has looked at it.
    #   assisted   every reading of statements, a compliance certificate or a borrowing base
    #              certificate is confirmed by a person before the cycle goes on, even when it
    #              passed every check. This is the default.
    #   automatic  a reading that passes every check is used without a person. Choose this only
    #              once measured accuracy on the bank's own documents justifies it.
    extraction_autonomy: str = "assisted"

    # Model access for the product's agents. The app never reads ANTHROPIC_BASE_URL from the
    # host environment: the base URL is set explicitly so a developer shell cannot redirect it.
    # SQUAD_ANTHROPIC_API_KEY is read first: a cloud coding session keeps ANTHROPIC_API_KEY for its
    # own use and does not pass it to commands, so the product's key goes under its own name there.
    anthropic_api_key: str = Field(default="", validation_alias=AliasChoices("SQUAD_ANTHROPIC_API_KEY",
                                                                              "ANTHROPIC_API_KEY"))
    squad_anthropic_base_url: str = "https://api.anthropic.com"
    squad_model: str = "claude-opus-5-5"
    squad_llm_mode: str = "recorded"  # recorded | live | record
    squad_recordings_dir: str = "./evals/recordings"

    @property
    def is_local(self) -> bool:
        return self.squad_env.strip().lower() == "local"

    @property
    def cookie_secure(self) -> bool:
        return (not self.is_local) if self.session_cookie_secure is None else self.session_cookie_secure

    @property
    def serve_api_docs(self) -> bool:
        return self.is_local if self.api_docs_enabled is None else self.api_docs_enabled

    @property
    def owner_database_url(self) -> str:
        return self.migration_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
