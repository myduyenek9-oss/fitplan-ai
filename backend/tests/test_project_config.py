from pathlib import Path
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
    assert "ruff check" in script


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
