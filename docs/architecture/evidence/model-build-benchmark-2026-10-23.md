# Can a Llama, or a model with no tool-calling, drive a BUILD run? (2026-10-23)

Evidence for [ADR-0093](../decisions/0093-local-model-families-are-named-and-measured-not-assumed.md), #1662.
The question was whether Llama "actually drives a BUILD run well", and whether the text tool-call
protocol makes the families without native tool-calling usable for BUILD.

## Method

One small, real task through the real `qwenloop` runner, on a fresh git repository per trial. The
plan asks for `slugify.py` (`slugify(text) -> str`, lowercase, runs of non-alphanumerics become one
hyphen, none at the ends) and `test_slugify.py` (at least four plain asserts), to be run until they
pass. **The result is verified by the harness, not by the model:** it imports `slugify.py` and checks
six cases the model never saw (`"Hello,  World!"`, `"  Already-slug  "`, `"A_B c"`, `"---"`,
`"Python 3.12"`, `""`). A model whose own tests pass and whose function is wrong counts as wrong; one
did exactly that. Cap: 25 turns and 420 seconds per trial. Ollama 0.40.9 on a 25.8 GB Apple machine.

Every model was run through a derived Ollama model with `num_ctx 32768`, the context the runner is
built for. This is not a detail: the first Llama run used Ollama's default 131,072-token context
for `llama3.1:8b`, a 23 GB footprint split 23% CPU / 77% GPU, and its first turn took 495 seconds.
That run was discarded as confounded.

## Results

| Configuration | Trials | Correct | Files made | Avg tool calls | Avg seconds |
|---|---|---|---|---|---|
| `gpt-oss:20b`, native (the default engine) | 3 | **1** | 3 | 15 | 91 |
| `llama3.1:8b`, native tool-calling | 3 | **0** | 3 | 19 | 328 |
| `llama3.1:8b`, text protocol | 5 valid | **0** | 2 | 2 to 22 | 327 to 420 |
| `deepseek-coder:1.3b`, `auto` (no tool-calling) | 3 | **0** | 0 | 0 | 142 |

Six Llama text trials were run. One crashed on the runner, not the model: Llama asked to read the
absolute path `/test_slugify.py` and a refused path ended the run. That was a runner bug, since fixed
for every tool (a refused call is now an answer), and the three trials after the fix are the three
that count with the first two. It is reported here as invalid, not hidden.

## What it shows

- **Llama 3.1 8B does not drive this task well.** It calls tools sensibly (`write_file`, `shell`,
  `edit_file`), but writes wrong code and does not notice, in one case passing its own wrong tests.
- **The text protocol works and does not help.** `auto` switched DeepSeek to it with the notice;
  Llama ran up to 22 tool calls through it; it is about twice as slow per turn; no outcome improved.
- **A 1.3B model never wrote a call the parser could recover**, in 8 turns, three times.
- **The default is weak too.** `gpt-oss:20b` was correct 1 time in 3, failing by an underscore bug,
  by running out of turns on a syntax error, and passing once. This task is not easy.

## Limits

One task, one machine, three trials per configuration. Differences this small are a rough signal,
not a ranking, and 0 of 5 does not prove a model cannot. It does show that a flag saying a model
*can* call tools is not evidence that it builds well, which is why `vibey models` reports only what
Ollama says and what a run shows.

## Reproducing

The harness, as run. It needs the `qwenloop` tenant on `PYTHONPATH` and the derived models above.

```python
import json, os, subprocess, sys, tempfile, time, pathlib, importlib.util

TENANT = "/Users/adam/git/vibey-storm/text-protocol/src/vibey_runners/qwen"
PLAN = """Create two files in the current directory.

1. slugify.py defining slugify(text: str) -> str. It lowercases the text, replaces every run of
   characters that are not letters or digits with a single hyphen, and removes hyphens from the
   start and end. slugify("Hello,  World!") returns "hello-world".
2. test_slugify.py with at least four assert statements about slugify, runnable with
   `python test_slugify.py` (plain asserts, no pytest, exit code 0 when they pass).

Run `python test_slugify.py` and fix anything until it passes. Then finish.
"""
CASES = [("Hello,  World!", "hello-world"), ("  Already-slug  ", "already-slug"), ("A_B c", "a-b-c"),
         ("---", ""), ("Python 3.12", "python-3-12"), ("", "")]

def run(model, protocol, max_turns, wall):
    work = pathlib.Path(tempfile.mkdtemp(prefix="bench-"))
    subprocess.run(["git", "init", "-q"], cwd=work); (work / "plan.md").write_text(PLAN)
    subprocess.run(["git", "add", "."], cwd=work); subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=b", "commit", "-qm", "i"], cwd=work)
    env = {**os.environ, "PYTHONPATH": f"{TENANT}/src", "QWENLOOP_MODEL": model}
    cfg = work / "cfg.toml"; cfg.write_text(f'tool_protocol = "{protocol}"\n')
    env["QWENLOOP_CONFIG"] = str(cfg)
    cmd = [sys.executable, "-c", "from qwenloop.cli.app import app; app()", "run", str(work / "plan.md"), "--cwd", str(work),
           "--backend", "openai-compat", "--base-url", "http://127.0.0.1:11434/v1", "--max-turns", str(max_turns)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=wall)
        code, err = p.returncode, p.stderr[-300:]
    except subprocess.TimeoutExpired:
        code, err = "timeout", ""
    secs = round(time.time() - t0)
    turns = calls = 0; names = {}
    for ev in work.glob(".qwenloop/runs/*/events.jsonl"):
        for line in ev.read_text().splitlines():
            e = json.loads(line)
            if e.get("type") == "turn.completed": turns += 1
            if e.get("type") == "tool.call": calls += 1; names[e["name"]] = names.get(e["name"], 0) + 1
    # independent verification
    ok_files = (work / "slugify.py").is_file() and (work / "test_slugify.py").is_file()
    correct = tests_pass = False; wrong = []
    if (work / "slugify.py").is_file():
        try:
            spec = importlib.util.spec_from_file_location("slugify_under_test", work / "slugify.py")
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            wrong = [(i, o, m.slugify(i)) for i, o in CASES if m.slugify(i) != o]
            correct = not wrong
        except Exception as ex:
            wrong = [("import", "ok", repr(ex)[:80])]
    if (work / "test_slugify.py").is_file():
        r = subprocess.run([sys.executable, "test_slugify.py"], cwd=work, capture_output=True, timeout=30)
        tests_pass = r.returncode == 0
        n_asserts = (work / "test_slugify.py").read_text().count("assert ")
    else:
        n_asserts = 0
    return dict(model=model, protocol=protocol, exit=code, secs=secs, turns=turns, tool_calls=calls, tools=names,
                files=ok_files, behaves=correct, own_tests_pass=tests_pass, asserts=n_asserts, wrong=wrong[:3], stderr=err.strip().splitlines()[-1:] , dir=str(work))

if __name__ == "__main__":
    model, protocol = sys.argv[1], sys.argv[2]
    print(json.dumps(run(model, protocol, int(sys.argv[3]), int(sys.argv[4]))))
```
