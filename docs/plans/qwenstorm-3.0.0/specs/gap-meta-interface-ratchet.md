## Title
test(meta): a ratchet that only lowers the count of classes without an interface beside them and of unexplained module functions

## Why
9.b (`src/vibey_tools/gh/docs/doctrines.md:349` at integration HEAD `4317cff6`): "every class has
its contract declared beside it — an interface in a mirrored `interfaces/` package … A bare
module-level function is the method of last resort … and its reason is written at the
definition … The existing tree, and every absorbed package, converges module by module as it is
touched". ADR-0016 (`docs/architecture/decisions/0016-classes-behind-interfaces.md`, "New
enforcement") says the check "that every class module has a matching interface module belongs
with the agent-surface parity test — a repo-introspecting static test". Nothing counts either
today (gap N5, `issue-audit/gaps.md:743-747`). So convergence is unmeasured, and a new unfaced
class merges silently.

The shape is `fakes-registry`'s patching ratchet (`specs/fakes-registry.md:114-133`): an AST
count per file, a committed JSON baseline of the non-zero files, a test that fails when any
count differs in either direction, and a `__main__` guard that prints the baseline. A decrease
must be written down, which is the ratchet. An increase is a 9.b violation that the change must
fix: add the interface or write the reason. Raising the baseline to fit is not a fix.

Measured at `4317cff6` with the rules below: 675 files count something, with 897 classes and
2085 module functions in total. These numbers are for orientation only: the committed baseline is
whatever the implemented counter prints.

## Required behaviour
1. New `tests/meta/test_interface_ratchet.py` (provenance header; module docstring citing 9.b,
   ADR-0016 and this shape, stating the rules below, and giving the reason its helpers are module
   functions: pytest collects functions, and a `__main__` guard needs one). Public helpers:
   - `scanned_files(root: Path) -> list[str]`: from `git ls-files src` run in `root`, every path
     ending `.py`, minus:
     - paths with a directory component in
       `SKIPPED_DIRECTORIES = frozenset({"tests", "test", "interfaces", "__pycache__"})`;
     - paths whose name is `conftest.py`;
     - paths whose name ends `_interface.py`.
     The result is sorted.
   - `count_file(root: Path, relative: str) -> tuple[int, int]`: `(unfaced classes, unexplained functions)`.
   - `count_tree(root: Path) -> dict[str, dict[str, int]]`: `{path: {"classes": c, "functions": f}}`
     for every scanned file with `c + f > 0`.
   - `BASELINE = Path(__file__).with_name("interface_ratchet_baseline.json")`.
2. **Classes.** Only top-level `ast.ClassDef` nodes in the module body count. A base's name is
   `Name.id`, or `Attribute.attr`, or, for a `Subscript`, its value's name.
   - Not counted, as interfaces themselves: a class whose name ends in `Interface`, or with a
     base named `Protocol` or `ABC`.
   - **Faced**, so not counted: a class `C` in `D/x.py` where either
     - (a) a top-level class named `f"{C}Interface"` is defined in any `*.py` directly under
       `D/interfaces/`, `__init__.py` included, or in `D/x_interface.py`
       (for example `src/vibey/bootstrap_interface.py`); or
     - (b) one of its base names was imported by an `ast.ImportFrom` anywhere in the module
       whose `module` has a dotted component `interfaces`, or whose last component ends
       `_interface` (for example `class Pipeline(PipelineInterface)` in
       `src/vibey_tools/gh/vibey_gh/feasibility.py`).
   - Every other class counts, whatever it is: a dataclass, an enum or an exception. 9.b says
     "every class".
3. **Functions.** Only top-level `FunctionDef` and `AsyncFunctionDef` nodes count.
   - A function is **explained**, so not counted, when
     `MARK = re.compile(r"module-level|module function|bare function|ADR-0016|\b9\.b\b", re.IGNORECASE)`
     matches any of:
     - (a) its docstring;
     - (b) the contiguous comment lines (lines that start with `#` after `lstrip()`)
       immediately above its first decorator, or above its `def` line when it has none;
     - (c) the comment lines from its `def` line through the fourth line of its body
       (`lines[node.lineno - 1 : node.body[0].lineno + 3]`).
   - Existing reasons that pass: `src/vibey/cli/ledger_search.py:275`,
     `src/vibey/infrastructure/db/migrator.py:285`, `src/vibey/domain/plan.py:197`,
     `src/vibey_tools/skills/tools/check_links.py:261`.
4. **The baseline** `tests/meta/interface_ratchet_baseline.json` holds
   `json.dumps(count_tree(REPO), indent=1, sort_keys=True) + "\n"`. It is generated once by the
   module's `if __name__ == "__main__":` guard, which prints exactly that:
   `uv run python -m tests.meta.test_interface_ratchet > tests/meta/interface_ratchet_baseline.json`.
   Commit the output unedited.

## Where to change
- New: `tests/meta/test_interface_ratchet.py`, `tests/meta/interface_ratchet_baseline.json`.
- Style to copy: `tests/meta/test_protected_paths_agree.py:20-50` (`REPO`, `git ls-files`).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_interface_ratchet.py` passes.
- [ ] Regenerating the baseline with the `__main__` command gives no `git diff`.
- [ ] By hand (then revert):
  - adding `class Probe:\n    def run(self) -> None: ...` to `src/vibey/domain/phase.py` fails
    `test_counts_equal_the_baseline`, naming that file and printing its corrected entry;
  - adding `src/vibey/domain/interfaces/probe_interface.py` with `class ProbeInterface(Protocol)`
    makes it pass again.
- [ ] The scan finishes in under 10 seconds (`pytest --durations=5`).

## Tests to write first (TDD)
In `tests/meta/test_interface_ratchet.py`. The unit tests build small trees under `tmp_path`
and call `count_file(tmp_path, "pkg/x.py")` directly:
- `test_a_class_without_an_interface_is_counted`
- `test_a_class_with_its_interface_beside_it_is_not_counted` (`pkg/interfaces/x_interface.py`
  declares `XInterface`; also the `__init__.py` form and the `pkg/x_interface.py` form)
- `test_a_class_subclassing_an_imported_interface_is_not_counted`
  (`from pkg.interfaces.y_interface import YInterface` and a relative `from .interfaces import YInterface`)
- `test_protocols_abcs_and_interface_named_classes_are_not_counted`
- `test_a_dataclass_an_enum_and_an_exception_are_counted`
- `test_a_function_with_a_written_reason_is_not_counted` (parametrized: docstring, comment
  above, comment above a decorator, comment inside the body)
- `test_a_function_without_a_reason_is_counted`; `test_nested_classes_and_functions_are_not_counted`
- `test_scanned_files_skip_tests_interfaces_and_conftest`: over a `tmp_path` git repository
  (`git init`, then add files).
- `test_counts_equal_the_baseline`: `count_tree(REPO) == json.loads(BASELINE.read_text())`. On a
  difference it lists every changed file, with the baseline and the actual counts. It then says:
  a lower count is recorded by lowering that entry in the same change; a higher count is fixed
  by adding the interface beside the class, or writing the reason at the function (9.b). It
  prints the corrected JSON entries.
- `test_the_baseline_is_sorted_and_positive`: the keys are sorted, each value has exactly the
  keys `classes` and `functions` as non-negative ints, and each entry's sum is positive.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run python -m tests.meta.test_interface_ratchet | diff - tests/meta/interface_ratchet_baseline.json

## Out of scope
- Converging any module. Later lanes lower the baseline as they add interfaces.
- `scripts/`, `deploy/` and `tests/` (production code under `src/` only), and `tui/`'s floor
  exemption (the count is about 9.b, not coverage).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `test(meta): a ratchet on classes without interfaces and unexplained module functions`. Do not push.

## Lane card
- **Depends on:** nothing. It is independent of `fakes-registry`: it reuses the shape, not the code.
- **Kind:** a test lane: one meta-test and its baseline.
- **Note for later lanes:** once this lands, any lane that adds a class without an interface, or
  a module function without a reason, fails `tests/meta`. It must add the interface or the reason.
  A lane whose spec knowingly adds an interface-less value class must say so and update this
  baseline in its own diff, where the reviewer sees it.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
