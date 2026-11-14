"""Isolated test execution. Primary: Daytona sandbox. Fallback: local temp venv."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config

INSTALL_CMD = "python -m pip install -q --disable-pip-version-check -r requirements.txt"
TEST_CMD = "python -m pytest -q -p no:cacheprovider --tb=short"


class DaytonaRunner:
    """Runs the target repo's test-suite inside a fresh Daytona sandbox."""

    label = "Daytona sandbox"

    def __init__(self):
        from daytona import CreateSandboxFromSnapshotParams, Daytona, DaytonaConfig

        self.daytona = Daytona(DaytonaConfig(api_key=config.DAYTONA_API_KEY))
        self.sandbox = self.daytona.create(
            CreateSandboxFromSnapshotParams(
                language="python",
                labels={"app": "kaizen"},
                auto_stop_interval=30,
                auto_delete_interval=60,
            ),
            timeout=180,
        )
        self.root = self.sandbox.get_user_home_dir().rstrip("/") + "/repo"
        self.id = self.sandbox.id

    def write_files(self, files: dict[str, str]):
        from daytona import FileUpload

        dirs = sorted({str(Path(self.root, p).parent) for p in files})
        self.sandbox.process.exec("mkdir -p " + " ".join(f"'{d}'" for d in dirs), timeout=30)
        self.sandbox.fs.upload_files(
            [FileUpload(source=c.encode(), destination=f"{self.root}/{p}") for p, c in files.items()]
        )

    def _exec(self, cmd: str, timeout: int) -> tuple[int, str]:
        r = self.sandbox.process.exec(cmd, cwd=self.root, timeout=timeout)
        return r.exit_code, r.result

    def install(self) -> tuple[int, str]:
        return self._exec(INSTALL_CMD, timeout=900)

    def run_tests(self) -> tuple[int, str]:
        return self._exec(TEST_CMD, timeout=300)

    def close(self):
        try:
            self.sandbox.delete()
        except Exception:
            pass


class LocalRunner:
    """Fallback when DAYTONA_API_KEY is missing: throwaway venv in a temp dir."""

    label = "local venv (fallback — set DAYTONA_API_KEY for sandboxing)"

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="kaizen-"))
        self.root = self.tmp / "repo"
        self.root.mkdir()
        self.id = str(self.tmp)
        subprocess.run([sys.executable, "-m", "venv", str(self.tmp / "venv")], check=True)
        self.py = str(self.tmp / "venv" / "bin" / "python")

    def write_files(self, files: dict[str, str]):
        for rel, content in files.items():
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)

    def _exec(self, cmd: str, timeout: int) -> tuple[int, str]:
        cmd = cmd.replace("python ", f"'{self.py}' ", 1)
        p = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)

    def install(self):
        return self._exec(INSTALL_CMD, timeout=900)

    def run_tests(self):
        return self._exec(TEST_CMD, timeout=300)

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def make_runner():
    if config.DAYTONA_API_KEY:
        return DaytonaRunner()
    if config.PUBLIC_MODE:  # never execute visitors' code on the host
        raise RuntimeError("PUBLIC_MODE requires DAYTONA_API_KEY: user code only runs in Daytona sandboxes")
    return LocalRunner()
