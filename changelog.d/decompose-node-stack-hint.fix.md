* **The local DECOMPOSE prompt knows a Node repository:** its base prompt says "prefer one pytest
  suite under tests/", which is right for Python and wrong elsewhere. On a Node project (a
  `package.json` and no `pyproject.toml` in the checkout) the plan for the ministry section came
  back verifying with `pytest -q tests/__tests__/*.test.ts` and `node -e "require('./src/lib/x')"`
  on a TypeScript file, neither of which can pass, and the plan was accepted and built before
  verification found out. The prompt now tells the planner to verify with the project's npm
  scripts, never pytest, and that `node` runs only `.js` and `.mjs`. Python repositories and a
  plan with no checkout see the unchanged prompt.
