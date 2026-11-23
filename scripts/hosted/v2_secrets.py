"""Make v2's database passwords and session secret in this process and nowhere else.

    python scripts/hosted/v2_secrets.py --project-dir .vercel-build-v2 --ref <supabase ref> \
        --pooler-host aws-0-us-east-1.pooler.supabase.com [--alter] [--overwrite]

Puts MIGRATION_DATABASE_URL (squad2_app), DATABASE_URL (squad2_web) and SESSION_SECRET on the linked
Vercel project's production environment through `vercel env add` on standard input (marked
sensitive), then prints the SQL that creates the roles with SCRAM-SHA-256 verifiers only. Pass that
SQL to the Supabase MCP tool `execute_sql` in the same session; do not save it.

The pooler host is not known for certain (candidates: aws-0-us-east-1.pooler.supabase.com and
aws-1-us-east-1.pooler.supabase.com). If the first host is wrong, run again with the other host and
`--alter`: new passwords, the variables overwritten (`vercel env add --force`), and ALTER ROLE
statements instead of CREATE. `--overwrite` alone overwrites the variables after a run that stopped
part-way (no role was created then: the SQL is printed only after all three variables are set).

No value is printed or written to a file."""
import argparse
import base64
import hashlib
import hmac
import re
import secrets
import shlex
import string
import subprocess
import sys

ALPHABET = string.ascii_letters + string.digits  # placed in a URL: letters and digits only
HOST = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+")


def new_password(length: int = 40) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def scram_verifier(password: str, salt: bytes | None = None, iterations: int = 4096) -> str:
    """PostgreSQL's stored form: SCRAM-SHA-256$<iterations>:<salt>$<StoredKey>:<ServerKey>."""
    salt = salt if salt is not None else secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    stored = hashlib.sha256(hmac.new(salted, b"Client Key", "sha256").digest()).digest()
    server = hmac.new(salted, b"Server Key", "sha256").digest()

    def b64(raw: bytes) -> str:
        return base64.b64encode(raw).decode()

    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored)}:{b64(server)}"


def role_sql(owner_verifier: str, web_verifier: str, alter: bool = False) -> str:
    verb = "ALTER" if alter else "CREATE"
    lines = [] if alter else ["CREATE ROLE squad2_runtime NOLOGIN;"]
    lines += [f"{verb} ROLE squad2_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{owner_verifier}';",
              f"{verb} ROLE squad2_web LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{web_verifier}';"]
    if not alter:
        lines += ["GRANT squad2_runtime TO squad2_web;",
                  "GRANT CREATE ON DATABASE postgres TO squad2_app;"]  # its migration creates schema squad2
    return "\n".join(lines)


def connection_url(role: str, ref: str, password: str, host: str) -> str:
    """The Supabase session pooler's form: user `<role>.<project ref>`, port 5432, TLS required."""
    if not HOST.fullmatch(host):
        raise ValueError("the pooler host must be a plain host name, without port, user or path")
    return f"postgresql+psycopg://{role}.{ref}:{password}@{host}:5432/postgres?sslmode=require"


def put(vercel: list[str], project_dir: str, name: str, value: str, force: bool) -> None:
    args = [*vercel, "env", "add", name, "--environment", "production", "--sensitive",
            "--token", "proxy-injected", *(["--force"] if force else [])]
    done = subprocess.run(args, input=value + "\n", text=True, capture_output=True, cwd=project_dir)
    if done.returncode != 0:
        reason = (done.stderr or done.stdout).replace(value, "<value>")[-400:]
        sys.exit(f"vercel env add {name} failed ({done.returncode}); no role SQL was printed. "
                 f"Rerun with --overwrite once the cause is fixed. {reason}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--pooler-host", required=True)
    parser.add_argument("--vercel", default="npx --yes vercel@66.0.0")
    parser.add_argument("--alter", action="store_true", help="retry: new passwords, ALTER ROLE, overwrite")
    parser.add_argument("--overwrite", action="store_true", help="overwrite variables a stopped run left")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]{1,40}", args.ref):
        sys.exit("the project ref is letters and digits only")
    vercel = shlex.split(args.vercel)
    force = args.alter or args.overwrite
    owner, web = new_password(), new_password()
    urls = [("MIGRATION_DATABASE_URL", connection_url("squad2_app", args.ref, owner, args.pooler_host)),
            ("DATABASE_URL", connection_url("squad2_web", args.ref, web, args.pooler_host))]
    for name, value in [*urls, ("SESSION_SECRET", secrets.token_urlsafe(48))]:
        put(vercel, args.project_dir, name, value, force)
    print(role_sql(scram_verifier(owner), scram_verifier(web), alter=args.alter))
    return 0


if __name__ == "__main__":
    sys.exit(main())
