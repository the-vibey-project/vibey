* **A plan can no longer verify a TypeScript file with pytest, and a Node repository gets Node
  house rules:** the planner for a Next.js repository wrote `pytest -q
  tests/__tests__/ministry.test.ts`, which cannot pass, and the plan check (which only looks for
  files nothing provides) accepted it. The engine was then told to "keep every test under tests/"
  and spent all sixteen turns of its first item searching for a directory the repository does not
  have, writing no code. Decompose now rejects, and re-asks with the file named, a pytest command
  pointed at a `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` or `.cjs` file. The house rules given to every
  implement session now follow the checkout: a `package.json` with no `pyproject.toml` gets
  rules that put tests in the repository's own `__tests__` directories and run its npm scripts;
  everything else sees the unchanged Python rules.
