// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** GitClient against real git in scratch repositories, and a scripted git for what real git rarely says. */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { beforeAll, describe, expect, it } from 'vitest';
import { GitClient, GitError } from '../../src/core/git';
import { NodeProcessRunner } from '../../src/core/process-runner';
import { FakeProcessRunner, scratch } from './helpers';

const runner = new NodeProcessRunner();
let environment: Record<string, string> = {};

/** Plain git for setting a scene; the client under test is only ever GitClient. */
async function sh(cwd: string, ...args: string[]): Promise<string> {
  const result = await runner.run('git', ['-C', cwd, ...args], { env: environment });
  if (result.code !== 0) {
    throw new Error(`git ${args.join(' ')}: ${result.stderr}`);
  }
  return result.stdout;
}

async function repository(): Promise<string> {
  const directory = scratch('vibey-git-');
  await sh(directory, 'init', '-q', '-b', 'main');
  fs.writeFileSync(path.join(directory, 'README.md'), 'hello\n');
  await sh(directory, 'add', 'README.md');
  await sh(directory, 'commit', '-q', '-m', 'first');
  return directory;
}

function hook(directory: string, name: string, script: string): void {
  const file = path.join(directory, '.git', 'hooks', name);
  fs.writeFileSync(file, `#!/bin/sh\n${script}\n`);
  fs.chmodSync(file, 0o755);
}

beforeAll(() => {
  // No global or system config: this computer's own hooksPath, signing or aliases stay out.
  environment = {
    PATH: process.env.PATH ?? '',
    HOME: scratch('vibey-git-home-'),
    GIT_CONFIG_NOSYSTEM: '1',
    GIT_AUTHOR_NAME: 'Vibey Test',
    GIT_AUTHOR_EMAIL: 'test@example.invalid',
    GIT_COMMITTER_NAME: 'Vibey Test',
    GIT_COMMITTER_EMAIL: 'test@example.invalid',
  };
});

describe('GitClient, against real git', () => {
  const git = (): GitClient => new GitClient(runner, 'git', environment);

  it('reads its version, the top of a repository, commits and the checked-out branch', async () => {
    const repo = await repository();
    fs.mkdirSync(path.join(repo, 'docs'));
    expect(await git().version()).toMatch(/^git version \d/);
    expect(await git().toplevel(path.join(repo, 'docs'))).toBe(repo);
    const sha = await git().resolveCommit(repo, 'HEAD');
    expect(sha).toMatch(/^[0-9a-f]{40}$/);
    expect(await git().head(repo)).toBe(sha);
    expect(await git().currentBranch(repo)).toBe('main');
    await sh(repo, 'checkout', '-q', '--detach');
    expect(await git().currentBranch(repo)).toBeUndefined();
  });

  it("fails with git's own words, or its exit code when it says nothing", async () => {
    const outside = scratch();
    await expect(git().toplevel(outside)).rejects.toThrow(/^git -C .* rev-parse --show-toplevel failed: fatal: not a git repository/);
    const repo = await repository();
    const error = await git()
      .resolveCommit(repo, 'no-such-ref')
      .catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(GitError);
    expect((error as GitError).message).toBe(`git -C ${repo} rev-parse --verify --quiet no-such-ref^{commit} failed: exit 1`);
    expect((error as GitError).args).toContain('no-such-ref^{commit}');
    expect((error as GitError).result.code).toBe(1);
  });

  it('lists what is not committed, leaving out run records and a rename\'s old path', async () => {
    const repo = await repository();
    fs.mkdirSync(path.join(repo, '.qwenloop', 'runs', 'r1'), { recursive: true });
    fs.writeFileSync(path.join(repo, '.qwenloop', 'runs', 'r1', 'events.jsonl'), '{}\n');
    fs.writeFileSync(path.join(repo, 'new.txt'), 'new\n');
    await sh(repo, 'mv', 'README.md', 'GUIDE.md');
    expect([...(await git().uncommitted(repo))].sort()).toEqual(['GUIDE.md', 'new.txt']);
    expect([...(await git().uncommitted(repo, []))].sort()).toEqual(['.qwenloop/runs/r1/events.jsonl', 'GUIDE.md', 'new.txt']);
    expect([...(await git().uncommitted(repo, ['new.txt']))].sort()).toEqual(['.qwenloop/runs/r1/events.jsonl', 'GUIDE.md']);
  });

  it('makes a worktree on a branch of its own, and removes both', async () => {
    const repo = await repository();
    const worktree = path.join(scratch(), 'task');
    const base = await git().head(repo);
    await git().addWorktree(repo, worktree, 'vibey/task-0123abcd', base);
    expect(await git().branchExists(repo, 'vibey/task-0123abcd')).toBe(true);
    expect(await git().branchExists(repo, 'vibey/no-such-branch')).toBe(false);
    expect(await git().currentBranch(worktree)).toBe('vibey/task-0123abcd');
    expect(await git().head(worktree)).toBe(base);
    await git().removeWorktree(repo, worktree);
    expect(fs.existsSync(worktree)).toBe(false);
    await git().deleteBranch(repo, 'vibey/task-0123abcd');
    expect(await git().branchExists(repo, 'vibey/task-0123abcd')).toBe(false);
  });

  it('commits the work but never the run records or attachments, and says when there was nothing', async () => {
    const repo = await repository();
    const exclude = ['.qwenloop', '.vibey-attachments'];
    fs.writeFileSync(path.join(repo, 'a.txt'), 'a\n');
    fs.mkdirSync(path.join(repo, '.qwenloop', 'runs', 'r1'), { recursive: true });
    fs.writeFileSync(path.join(repo, '.qwenloop', 'runs', 'r1', 'events.jsonl'), '{}\n');
    fs.mkdirSync(path.join(repo, '.vibey-attachments'));
    fs.writeFileSync(path.join(repo, '.vibey-attachments', 'notes.txt'), 'pasted\n');
    expect(await git().commitAll(repo, 'docs: add a', exclude)).toEqual({ committed: true });
    expect((await sh(repo, 'show', '--name-only', '--format=%s', 'HEAD')).trim().split('\n')).toEqual(['docs: add a', '', 'a.txt']);
    expect(await git().uncommitted(repo, exclude)).toEqual([]);
    expect(await git().commitAll(repo, 'docs: again', exclude)).toEqual({ committed: false });
    fs.writeFileSync(path.join(repo, 'b.txt'), 'b\n');
    expect(await git().commitAll(repo, 'docs: add b')).toEqual({ committed: true });
  });

  it('commits in a repository whose .gitignore holds .qwenloop/, and the commit holds neither runner directory', async () => {
    const repo = await repository();
    fs.writeFileSync(path.join(repo, '.gitignore'), '.qwenloop/\n');
    await sh(repo, 'add', '.gitignore');
    await sh(repo, 'commit', '-q', '-m', 'chore: ignore run records');
    fs.mkdirSync(path.join(repo, '.qwenloop', 'runs', 'r1'), { recursive: true });
    fs.writeFileSync(path.join(repo, '.qwenloop', 'runs', 'r1', 'events.jsonl'), '{}\n');
    fs.mkdirSync(path.join(repo, '.vibey-attachments'));
    fs.writeFileSync(path.join(repo, '.vibey-attachments', 'notes.txt'), 'pasted\n');
    fs.mkdirSync(path.join(repo, 'docs'));
    fs.writeFileSync(path.join(repo, 'docs', 'install.md'), '# Install\n');
    expect(await git().commitAll(repo, 'docs: add the install guide', ['.qwenloop', '.vibey-attachments'])).toEqual({ committed: true });
    expect((await sh(repo, 'show', '--name-only', '--format=', 'HEAD')).trim().split('\n')).toEqual(['docs/install.md']);
    expect(await sh(repo, 'status', '--porcelain', '--untracked-files=all')).toBe('?? .vibey-attachments/notes.txt\n');
  });

  it("commits only the task's paths, and leaves every other change uncommitted and named", async () => {
    const repo = await repository();
    fs.mkdirSync(path.join(repo, 'docs', 'guides'), { recursive: true });
    fs.writeFileSync(path.join(repo, 'docs', 'guides', 'install.md'), '# Install\n');
    fs.writeFileSync(path.join(repo, 'pyproject.toml'), '[project]\nname = "x"\n');
    fs.writeFileSync(path.join(repo, 'uv.lock'), 'version = 1\n');
    fs.writeFileSync(path.join(repo, 'notes[1].md'), 'a file named like a glob\n');
    const outcome = await git().commitAll(repo, 'docs: install', ['.qwenloop'], ['docs/**/*.md']);
    expect(outcome).toEqual({ committed: true, outOfScope: ['notes[1].md', 'pyproject.toml', 'uv.lock'] });
    expect((await sh(repo, 'show', '--name-only', '--format=', 'HEAD')).trim()).toBe('docs/guides/install.md');
    expect([...(await git().uncommitted(repo))].sort()).toEqual(['notes[1].md', 'pyproject.toml', 'uv.lock']);
    // Every change in scope: the commit is the task's, and nothing is left out.
    fs.writeFileSync(path.join(repo, 'docs', 'guides', 'install.md'), '# Install, step by step\n');
    expect(await git().commitAll(repo, 'docs: again', ['.qwenloop'], ['docs/', '*.md', 'pyproject.toml', 'uv.lock'])).toEqual({ committed: true });
    fs.writeFileSync(path.join(repo, 'notes[1].md'), 'changed\n');
    fs.writeFileSync(path.join(repo, 'pyproject.toml'), '[project]\nname = "y"\n');
    // Nothing in scope changed: nothing is committed, and what changed is still named.
    fs.writeFileSync(path.join(repo, 'uv.lock'), 'version = 2\n');
    expect(await git().commitAll(repo, 'docs: once more', ['.qwenloop'], ['docs/'])).toEqual({ committed: false, outOfScope: ['notes[1].md', 'pyproject.toml', 'uv.lock'] });
  });

  it('keeps nothing out when told to keep nothing out', async () => {
    const repo = await repository();
    fs.mkdirSync(path.join(repo, '.qwenloop'));
    fs.writeFileSync(path.join(repo, '.qwenloop', 'kept.json'), '{}\n');
    expect(await git().commitAll(repo, 'chore: keep everything', [])).toEqual({ committed: true });
    expect((await sh(repo, 'show', '--name-only', '--format=', 'HEAD')).trim()).toBe('.qwenloop/kept.json');
  });

  it("runs the repository's hooks, and reports a refusal in git's words rather than bypassing it", async () => {
    const repo = await repository();
    hook(repo, 'pre-commit', 'echo "no commits today" >&2\nexit 1');
    fs.writeFileSync(path.join(repo, 'a.txt'), 'a\n');
    expect(await git().commitAll(repo, 'docs: add a')).toEqual({ committed: false, error: 'no commits today' });
    expect((await sh(repo, 'log', '--format=%s')).trim()).toBe('first');
  });

  it('commits once more after a hook that fixes files and asks for them to be staged', async () => {
    const repo = await repository();
    hook(repo, 'pre-commit', 'if [ ! -f fixed.txt ]; then echo fixed > fixed.txt; echo "reformatted; stage and commit again" >&2; exit 1; fi\nexit 0');
    fs.writeFileSync(path.join(repo, 'a.txt'), 'a\n');
    expect(await git().commitAll(repo, 'docs: add a')).toEqual({ committed: true });
    expect((await sh(repo, 'show', '--name-only', '--format=', 'HEAD')).trim().split('\n').sort()).toEqual(['a.txt', 'fixed.txt']);
  });

  it('reads the changes between two commits: files with their status, the stat and the diff', async () => {
    const repo = await repository();
    fs.writeFileSync(path.join(repo, 'gone.txt'), 'bye\n');
    fs.writeFileSync(path.join(repo, 'moved.txt'), 'a line long enough that git sees the rename\n');
    await sh(repo, 'add', '.');
    await sh(repo, 'commit', '-q', '-m', 'second');
    const base = await git().head(repo);
    fs.writeFileSync(path.join(repo, 'README.md'), 'hello again\n');
    fs.writeFileSync(path.join(repo, 'added.txt'), 'new\n');
    fs.rmSync(path.join(repo, 'gone.txt'));
    await sh(repo, 'mv', 'moved.txt', 'renamed.txt');
    await sh(repo, 'add', '-A');
    await sh(repo, 'commit', '-q', '-m', 'third');
    const head = await git().head(repo);
    expect(await git().changedFiles(repo, base, head)).toEqual([
      { status: 'M', path: 'README.md' },
      { status: 'A', path: 'added.txt' },
      { status: 'D', path: 'gone.txt' },
      { status: 'R', path: 'renamed.txt' },
    ]);
    expect(await git().diffStat(repo, base, head)).toMatch(/4 files changed/);
    expect(await git().diff(repo, base, head)).toContain('+hello again');
  });

  it('merges a branch, undoes a conflict, and will not merge into a checkout with uncommitted changes', async () => {
    const repo = await repository();
    const worktree = path.join(scratch(), 'feature');
    await git().addWorktree(repo, worktree, 'feature', 'HEAD');
    fs.writeFileSync(path.join(worktree, 'feature.txt'), 'feature\n');
    await git().commitAll(worktree, 'feat: add the feature');
    expect(await git().merge(repo, 'feature', 'Merge the feature')).toMatchObject({ ok: true });
    expect(fs.existsSync(path.join(repo, 'feature.txt'))).toBe(true);

    fs.writeFileSync(path.join(worktree, 'README.md'), 'theirs\n');
    await git().commitAll(worktree, 'docs: theirs');
    fs.writeFileSync(path.join(repo, 'README.md'), 'ours\n');
    await git().commitAll(repo, 'docs: ours');
    const conflict = await git().merge(repo, 'feature', 'Merge the feature again');
    expect(conflict).toMatchObject({ ok: false, reason: 'conflict', conflicts: ['README.md'] });
    expect(conflict.ok ? '' : conflict.detail).toContain('CONFLICT');
    expect(await sh(repo, 'status', '--porcelain')).toBe('');
    expect(fs.readFileSync(path.join(repo, 'README.md'), 'utf8')).toBe('ours\n');

    fs.writeFileSync(path.join(repo, 'README.md'), 'unsaved work\n');
    expect(await git().merge(repo, 'feature', 'm')).toEqual({
      ok: false,
      reason: 'dirty',
      detail: 'Your branch has uncommitted changes. Commit or stash them, then apply again.',
      conflicts: [],
    });
    await sh(repo, 'checkout', '--', 'README.md');
    const failed = await git().merge(repo, 'no-such-branch', 'm');
    expect(failed).toMatchObject({ ok: false, reason: 'failed', conflicts: [] });
    expect(failed.ok ? '' : failed.detail).toContain('no-such-branch');
  });
});

describe('GitClient, with a scripted git', () => {
  it('reports a git that could not start', async () => {
    const git = new GitClient(new FakeProcessRunner().on(['rev-parse'], { code: null, error: 'spawn git ENOENT' }), '/no/git', {});
    await expect(git.toplevel('/x')).rejects.toThrow('git -C /x rev-parse --show-toplevel failed: spawn git ENOENT');
  });

  it('passes its environment and a timeout to every git it runs', async () => {
    const runner = new FakeProcessRunner().on(['--version'], { stdout: 'git version 2.47.0\n' });
    expect(await new GitClient(runner, '/usr/bin/git', { PATH: '/usr/bin' }).version()).toBe('git version 2.47.0');
    expect(runner.calls[0]).toEqual({ command: '/usr/bin/git', args: ['--version'], options: { env: { PATH: '/usr/bin' }, timeoutMs: 120_000 } });
  });

  it('reports the last refusal when a second attempt finds nothing left to commit', async () => {
    let staged = 0;
    const runner = new FakeProcessRunner()
      .on(['diff', '--cached', '--quiet'], () => ({ code: staged++ === 0 ? 1 : 0 }))
      .on(['commit'], { code: 1, error: 'killed' });
    expect(await new GitClient(runner, 'git', {}).commitAll('/w', 'm')).toEqual({ committed: false, error: 'killed' });
    const silent = new FakeProcessRunner().on(['diff', '--cached', '--quiet'], { code: 1 }).on(['commit'], { code: 1 });
    expect(await new GitClient(silent, 'git', {}).commitAll('/w', 'm')).toEqual({ committed: false, error: 'exit 1' });
    expect(silent.calls.filter((call) => call.args.includes('commit'))).toHaveLength(2);
    // A hook that refuses twice, with changes outside the scope: both are reported.
    const scoped = new FakeProcessRunner()
      .on(['--name-only', '--no-renames'], { stdout: 'docs/a.md\0uv.lock\0' })
      .on(['diff', '--cached', '--quiet'], { code: 1 })
      .on(['commit'], { code: 1, stderr: 'hook said no' });
    expect(await new GitClient(scoped, 'git', {}).commitAll('/w', 'm', ['.qwenloop'], ['docs/'])).toEqual({ committed: false, error: 'hook said no', outOfScope: ['uv.lock'] });
    const reset = scoped.calls.find((call) => call.args.includes('--literal-pathspecs'));
    expect(reset?.args).toEqual(['--literal-pathspecs', '-C', '/w', 'reset', '-q', '--', 'uv.lock']);
  });

  it('skips a name-status entry that is cut short', async () => {
    const runner = new FakeProcessRunner().on(['--name-status'], { stdout: 'M\0a.txt\0R100\0old.txt\0' });
    expect(await new GitClient(runner, 'git', {}).changedFiles('/r', 'a', 'b')).toEqual([{ status: 'M', path: 'a.txt' }]);
  });

  it("describes a failed merge from git's error, or its exit code, when git printed nothing", async () => {
    const timedOut = new FakeProcessRunner().on(['merge', '--no-edit'], { code: null, error: 'timed out after 120000 ms' }).on(['MERGE_HEAD'], { code: 1 });
    expect(await new GitClient(timedOut, 'git', {}).merge('/r', 'b', 'm')).toEqual({ ok: false, reason: 'failed', detail: 'timed out after 120000 ms', conflicts: [] });
    const quiet = new FakeProcessRunner().on(['merge', '--no-edit'], { code: 2 }).on(['MERGE_HEAD'], { code: 1 });
    expect(await new GitClient(quiet, 'git', {}).merge('/r', 'b', 'm')).toEqual({ ok: false, reason: 'failed', detail: 'exit 2', conflicts: [] });
    expect(quiet.calls.some((call) => call.args.includes('--abort'))).toBe(false);
  });
});
