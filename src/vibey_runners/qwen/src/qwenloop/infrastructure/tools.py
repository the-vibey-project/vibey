# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Constrained local tool execution."""

import asyncio
import os
from pathlib import Path


class SandboxTools:
    def __init__(self, worktree: Path, *, allow_network: bool = False) -> None:
        self.worktree = worktree.resolve()
        self.allow_network = allow_network

    async def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        if name == "read_file":
            path = self._path(str(arguments.get("path", "")))
            try:
                return {"content": path.read_text(encoding="utf-8")[:200_000]}
            except (OSError, UnicodeDecodeError) as exc:
                return {"error": str(exc)}
        if name == "write_file":
            path = self._path(str(arguments.get("path", "")))
            content = str(arguments.get("content", ""))
            refusal = self._shrink_refusal(path, content, arguments.get("allow_shrink") is True)
            if refusal is not None:
                return {"error": refusal}
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            except OSError as exc:
                return {"error": str(exc)}
            return {"written": len(content)}
        if name == "edit_file":
            return self._edit(arguments)
        if name == "shell":
            argv = arguments.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                return {"error": "argv must be a non-empty string list"}
            if argv[0] in {"sudo", "rm", "shutdown", "reboot"}:
                return {"error": "command denied by policy"}
            env = {
                key: value
                for key, value in os.environ.items()
                if "KEY" not in key and "TOKEN" not in key
            }
            if not self.allow_network:
                env["QWENLOOP_NETWORK"] = "disabled"
            try:
                process = await asyncio.create_subprocess_exec(
                    *argv,
                    cwd=self.worktree,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    start_new_session=True,
                )
            except OSError as exc:
                return {"error": str(exc)}
            try:
                output, _ = await asyncio.wait_for(process.communicate(), timeout=120)
            except TimeoutError:
                process.kill()
                await process.wait()
                return {"error": "command timed out"}
            return {
                "exit_code": process.returncode,
                "output": output.decode(errors="replace")[-100_000:],
            }
        return {"error": f"unknown tool {name!r}"}

    def _edit(self, arguments: dict[str, object]) -> dict[str, object]:
        """Replace exactly one occurrence of `old_string` in an existing file.

        The targeted alternative to write_file: a small model cannot reproduce a long file
        byte for byte, and a whole-file rewrite that drops lines is the failure this exists
        to prevent (#346).
        """
        raw = str(arguments.get("path", ""))
        old = str(arguments.get("old_string", ""))
        new = str(arguments.get("new_string", ""))
        path = self._path(raw)
        if not old:
            return {"error": "old_string must not be empty; use write_file to create a file"}
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return {"error": f"cannot edit {raw}: {exc}; use write_file to create a new file"}
        count = text.count(old)
        if count == 0:
            return {
                "error": f"old_string not found in {raw}; read the file again and copy the text exactly"
            }
        if count > 1:
            return {
                "error": f"old_string matches {count} times in {raw}; include more surrounding lines"
            }
        try:
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
        except OSError as exc:
            return {"error": str(exc)}
        return {"replaced": 1, "path": raw}

    @staticmethod
    def _shrink_refusal(path: Path, content: str, allowed: bool) -> str | None:
        """Why a write would gut an existing file, or None when it may proceed."""
        if allowed or not path.is_file():
            return None
        try:
            before = path.read_text(encoding="utf-8").count("\n")
        except (OSError, UnicodeDecodeError):
            return None
        after = content.count("\n")
        if before < 40 or after * 2 >= before:
            return None
        return (
            f"write_file would remove {before - after} of {before} lines from {path.name}; use "
            "edit_file for a targeted change, or pass allow_shrink=true to replace the file"
        )

    def _path(self, raw: str) -> Path:
        target = (self.worktree / raw).resolve()
        if target != self.worktree and self.worktree not in target.parents:
            raise ValueError("path escapes the worktree")
        return target
