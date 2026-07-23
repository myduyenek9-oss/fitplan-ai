from pathlib import Path
import json
import tomllib

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "backend" / "pyproject.toml"


def _normalized_requirement_names(requirements: list[str]) -> set[str]:
    names: set[str] = set()
    for requirement in requirements:
        name = requirement.split(";", 1)[0].strip()
        name = name.split("[", 1)[0]
        for separator in ("<", ">", "=", "!", "~"):
            name = name.split(separator, 1)[0]
        names.add(name.strip().lower().replace("_", "-"))
    return names


def test_backend_pyproject_declares_required_runtime_and_test_dependencies():
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    runtime_dependencies = _normalized_requirement_names(pyproject["project"]["dependencies"])
    optional_dependencies = pyproject["project"].get("optional-dependencies", {})
    test_dependencies = _normalized_requirement_names(optional_dependencies.get("test", []))
    dev_dependencies = _normalized_requirement_names(optional_dependencies.get("dev", []))

    assert {
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "pydantic-settings",
        "httpx",
        "apscheduler",
        "psycopg",
    } <= runtime_dependencies
    assert {"pytest", "pytest-asyncio", "ruff"} <= (test_dependencies | dev_dependencies)


def test_verify_script_prefers_repository_venv_python_and_runs_ruff():
    script = (ROOT / "scripts" / "verify.ps1").read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in script
    assert "Test-Path" in script
    assert "python" in script
    assert "ruff" in script and "check" in script


def test_dev_script_prefers_repository_venv_python():
    script = (ROOT / "scripts" / "dev.ps1").read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in script
    assert "Test-Path" in script
    assert "python" in script
    assert "uvicorn" in script


def test_readme_documents_toolchain_and_package_manager_fallback():
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "sqlalchemy" in readme
    assert "alembic" in readme
    assert "pydantic-settings" in readme
    assert "apscheduler" in readme
    assert "psycopg" in readme
    assert "ruff" in readme
    assert "npm" in readme
    assert "pnpm" in readme
    assert "fallback" in readme


def test_verify_script_fails_immediately_on_native_command_errors():
    script = (ROOT / "scripts" / "verify.ps1").read_text(encoding="utf-8")

    assert "function Invoke-Native" in script
    assert "$LASTEXITCODE" in script
    assert "exit $exitCode" in script
    assert "Invoke-Native" in script and "pytest" in script
    assert "Invoke-Native" in script and "ruff" in script and "check" in script


def test_frontend_package_declares_pnpm_and_vite_node_engine():
    package_json = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))

    assert package_json["packageManager"].startswith("pnpm@")
    assert package_json["engines"]["node"] == "^20.19.0 || >=22.12.0"


def test_scripts_prefer_pnpm_and_validate_vite_node_version():
    verify_script = (ROOT / "scripts" / "verify.ps1").read_text(encoding="utf-8")
    dev_script = (ROOT / "scripts" / "dev.ps1").read_text(encoding="utf-8")

    assert verify_script.index("Get-Command pnpm") < verify_script.index("Get-Command npm")
    assert dev_script.index("Get-Command pnpm") < dev_script.index("Get-Command npm")
    assert "Assert-NodeVersion" in verify_script
    assert "Assert-NodeVersion" in dev_script
    assert "20.19" in verify_script and "22.12" in verify_script
    assert "20.19" in dev_script and "22.12" in dev_script
    assert "-NoProfile" in dev_script


def test_relative_sqlite_database_url_is_resolved_from_repository_root():
    from app.core.config import PROJECT_ROOT, resolve_database_url

    resolved_url = resolve_database_url("sqlite+pysqlite:///./fitplan-local.db")

    assert resolved_url.endswith("fitplan-local.db")
    assert str(PROJECT_ROOT) in resolved_url


def test_non_sqlite_database_url_is_not_changed():
    from app.core.config import resolve_database_url

    database_url = "postgresql+psycopg://fitplan:fitplan@localhost:5432/fitplan_ai"

    assert resolve_database_url(database_url) == database_url
