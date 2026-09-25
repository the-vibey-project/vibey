# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""descriptor + effort + isolation -> command line. The only place a
RunSpec's abstract intent becomes a concrete argv for a specific vendor
binary -- and, as a template, for a caller that launches the runner itself."""

from typing import Final

from vibey.application.dto import RunSpec
from vibey.domain.engine import EngineDescriptor
from vibey.infrastructure.engines.interfaces.argv_interface import RunArgvTemplateInterface

BINARY: Final = "{binary}"
PLAN_FLAG: Final = "{plan_flag?}"
PLAN: Final = "{plan}"
RUN_ID: Final = "{run_id}"
EFFORT_ARGV: Final = "{effort_argv...}"
CWD: Final = "{cwd}"


class RunArgvTemplate:
    """`build_argv`'s `run` command line with its per-run values left as placeholders, for a
    caller that starts a runner itself -- the VS Code extension, through `vibey loops`.

    It makes `build_argv`'s two per-engine choices: `{plan_flag?}` is there only when the
    descriptor has a plan flag (the caller puts that flag in its place), and the `--cwd`
    pair only when the runner takes one. `{effort_argv...}` stands for the chosen effort's
    argv, which may be empty. Isolation flags are not in it: at worktree isolation, where a
    run in the caller's own checkout is, no descriptor has any.
    """

    def template(self, descriptor: EngineDescriptor) -> tuple[str, ...]:
        argv = [BINARY, "run"]
        if descriptor.plan_flag is not None:
            argv.append(PLAN_FLAG)
        argv.extend([PLAN, "--run-id", RUN_ID, EFFORT_ARGV])
        if descriptor.supports_cwd_flag:
            argv.extend(["--cwd", CWD])
        return tuple(argv)


RUN_ARGV_TEMPLATE: Final[RunArgvTemplateInterface] = RunArgvTemplate()


def build_argv(descriptor: EngineDescriptor, spec: RunSpec) -> tuple[str, ...]:
    verb = "resume" if spec.session_id is not None else "run"

    argv: list[str] = [descriptor.binary, verb]
    if spec.session_id is not None:
        argv.append(spec.session_id)
        if descriptor.resume_run_id_flag is not None:
            argv.extend([descriptor.resume_run_id_flag, str(spec.run_id)])
    else:
        plan_path = spec.worktree_path / ".vibey" / "plans" / f"{spec.run_id}.md"
        if descriptor.plan_flag is not None:
            argv.append(descriptor.plan_flag)
        argv.append(str(plan_path))
        argv.extend(["--run-id", str(spec.run_id)])

    argv.extend(descriptor.invoke(spec.effort).argv)
    argv.extend(descriptor.isolation_flags.get(spec.isolation, ()))
    if descriptor.supports_cwd_flag:
        argv.extend(["--cwd", str(spec.worktree_path)])

    return tuple(argv)
