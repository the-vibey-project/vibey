# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import subprocess
import tempfile
from pathlib import Path


def run_cmd(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)


def test_worktree_hooks_resolve_common_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 1. Initialize main repo
        run_cmd("git init", cwd=root)
        run_cmd("git config user.email 'test@example.com'", cwd=root)
        run_cmd("git config user.name 'Test User'", cwd=root)

        # 2. Create a dummy hook in .git/hooks/pre-push
        hooks_dir = root / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_file = hooks_dir / "pre-push"
        hook_file.write_text("#!/bin/sh\necho 'HOOK_EXECUTED'")
        hook_file.chmod(0o755)

        # 3. Create a linked worktree
        worktree_dir = root / "worktree"
        run_cmd(f"git worktree add {worktree_dir}", cwd=root)

        # 4. Setup .githooks in the worktree (simulating vibey-gh install)
        githooks_dir = worktree_dir / ".githooks"
        githooks_dir.mkdir(parents=True, exist_ok=True)

        shim_content = """#!/bin/sh
COMMON_DIR=$(git rev-parse --git-common-dir)
HOOK_PATH="$COMMON_DIR/hooks/pre-push"
if [ -x "$HOOK_PATH" ]; then
    exec "$HOOK_PATH" "$@"
else
    exit 0
fi
"""
        shim_file = githooks_dir / "pre-push.local"
        shim_file.write_text(shim_content)
        shim_file.chmod(0o755)

        # 5. Run the shim from the worktree
        res = run_cmd("./.githooks/pre-push.local", cwd=worktree_dir)

        assert res.returncode == 0
        assert "HOOK_EXECUTED" in res.stdout


def test_worktree_hooks_warning_when_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        run_cmd("git init", cwd=root)
        run_cmd("git config user.email 'test@example.com'", cwd=root)
        run_cmd("git config user.name 'Test User'", cwd=root)

        # Create worktree
        worktree_dir = root / "worktree"
        run_cmd(f"git worktree add {worktree_dir}", cwd=root)

        # Create .pre-commit-config.yaml INSIDE the worktree to trigger warning
        (worktree_dir / ".pre-commit-config.yaml").write_text("repos: []")

        # Setup shim with warning logic
        githooks_dir = worktree_dir / ".githooks"
        githooks_dir.mkdir(parents=True, exist_ok=True)

        shim_content = """#!/bin/sh
COMMON_DIR=$(git rev-parse --git-common-dir)
HOOK_PATH="$COMMON_DIR/hooks/pre-push"
if [ -x "$HOOK_PATH" ]; then
    exec "$HOOK_PATH" "$@"
elif [ -f ".pre-commit-config.yaml" ]; then
    echo "⚠️  Warning: pre-commit framework declared but hook not installed at $HOOK_PATH. Skipping pre-push gates."
    exit 0
else
    exit 0
fi
"""
        shim_file = githooks_dir / "pre-push.local"
        shim_file.write_text(shim_content)
        shim_file.chmod(0o755)

        # Run shim - should print warning
        res = run_cmd("./.githooks/pre-push.local", cwd=worktree_dir)

        assert res.returncode == 0
        assert "Warning: pre-commit framework declared" in res.stdout
