from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class DeploymentPipelineTests(unittest.TestCase):
    def test_workflow_builds_frontend_on_runner_and_uploads_archive(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")

        self.assertIn("actions/checkout@v4", workflow)
        self.assertIn("pnpm/action-setup@v4", workflow)
        self.assertIn("actions/setup-node@v4", workflow)
        self.assertIn("pnpm --dir frontend run build", workflow)
        self.assertIn("tar -czf", workflow)
        self.assertIn("scp", workflow)
        self.assertIn("PREBUILT_FRONTEND_ARCHIVE", workflow)
        self.assertIn("FORCE_DEPLOY=1", workflow)

    def test_server_uses_prebuilt_frontend_without_node_build(self) -> None:
        script = (ROOT / "scripts/deploy-production.sh").read_text(encoding="utf-8")
        override = (ROOT / "infra/docker-compose.prebuilt.yml").read_text(encoding="utf-8")
        runtime_dockerfile = (ROOT / "frontend/Dockerfile.runtime").read_text(encoding="utf-8")
        runtime_dockerignore = (ROOT / "frontend/Dockerfile.runtime.dockerignore").read_text(encoding="utf-8")

        self.assertIn("PREBUILT_FRONTEND_ARCHIVE", script)
        self.assertIn("docker-compose.prebuilt.yml", script)
        self.assertIn("build backend", script)
        self.assertIn("build web", script)
        self.assertIn("frontend/Dockerfile.runtime", override)
        self.assertNotIn("FROM node", runtime_dockerfile)
        self.assertIn("COPY frontend/dist", runtime_dockerfile)
        self.assertIn("!frontend/dist/**", runtime_dockerignore)


if __name__ == "__main__":
    unittest.main()

