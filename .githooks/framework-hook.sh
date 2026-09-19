#!/bin/sh
# Runs the pre-commit framework's own generated hook for one stage:
#
#     framework-hook.sh <stage> [hook arguments...]
#
# The shims beside this file (pre-commit, commit-msg.local, pre-push.local) are one line
# each and all end up here, so the lookup below is written once and cannot drift apart.
#
# vibey-gh owns core.hooksPath, so git never consults the framework's hook directory
# again and its hooks would silently stop running -- a worse failure than any gate they
# enforce, because everything keeps looking green.
#
# Delegates to the framework's OWN generated hook rather than calling `pre-commit run`:
# that script knows where its environment lives, and a git hook does not inherit an
# activated virtualenv, so re-invoking by name finds the wrong tools or none at all.
#
# WHERE that hook lives is asked of git, never spelled out. `pre-commit install` writes
# to `$(git rev-parse --git-common-dir)/hooks/<stage>`, so this reads exactly there. The
# literal `.git/hooks/<stage>` the shims used to test is right only in a plain clone: in
# a linked worktree `.git` is a FILE (`gitdir: ...`), that path never exists, and every
# commit and push from a worktree went out with no local gate at all and no word said
# (#282). `git rev-parse --git-path hooks/<stage>` is no answer either: it honours
# core.hooksPath, resolves to this very directory, and the chain would recurse.

if [ -z "${1:-}" ]; then
  echo "usage: $0 <stage> [hook arguments...]" >&2
  exit 2
fi
stage=$1
shift

common=$(git rev-parse --git-common-dir 2>/dev/null) || common=
hook="$common/hooks/$stage"

# In a linked worktree git exports GIT_DIR to its hooks; a plain clone's hooks get none.
# Passed on, it reaches every process the framework starts, the test suite included, and
# a `git init` or `git commit` there in a scratch directory then acts on THIS repository.
# That is not hypothetical: the first push this fix made possible ran a suite whose
# `git init <scratch>` rewrote the SHARED config to `core.bare = true` -- the main
# checkout stopped working for everyone -- and whose `git commit --allow-empty` landed on
# the pushing branch (#282). So the framework is handed exactly what a plain clone gives
# it. GIT_DIR is dropped only when it names the repository git finds from here anyway;
# an explicit `git --git-dir=...` that points somewhere else is left alone.
if [ -n "${GIT_DIR:-}" ]; then
  exported=$(cd "$GIT_DIR" 2>/dev/null && pwd -P) || exported=
  discovered=$(unset GIT_DIR; git rev-parse --absolute-git-dir 2>/dev/null) || discovered=
  if [ -n "$discovered" ]; then
    discovered=$(cd "$discovered" 2>/dev/null && pwd -P) || discovered=
  fi
  if [ -n "$exported" ] && [ "$exported" = "$discovered" ]; then
    unset GIT_DIR
  fi
fi

# `exec` keeps stdin, which is where git hands pre-push the refs being pushed.
if [ -n "$common" ] && [ -f "$hook" ] && [ -x "$hook" ]; then
  exec "$hook" "$@"
fi

# Not installed. A repository that never adopted the framework has nothing to run here
# and nothing to say. One that DECLARES it expects these gates, so the gap is named out
# loud -- but the commit or push still goes ahead: a contributor who has not run
# `pre-commit install` must still be able to work, and CI runs the same gates regardless.
# The declaration is the framework's config file, named by a key with the framework's
# own default rather than a literal.
config=${VIBEY_FRAMEWORK_HOOK_CONFIG:-.pre-commit-config.yaml}
if [ -f "$config" ]; then
  {
    echo "warning: the pre-commit framework's $stage hook is not installed, so none of"
    echo "  its $stage gates ran. Looked for: $hook"
    echo "  To install it (pre-commit refuses while core.hooksPath is set):"
    echo "      git config --unset core.hooksPath"
    echo "      uv run pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push"
    echo "      uv run vibey-gh install"
  } >&2
fi
exit 0
