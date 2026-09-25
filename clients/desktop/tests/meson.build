# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# GLib tests over libkryptondesktop, one executable per module. `meson test -C build`.
test_env = environment()
test_env.set('G_DEBUG', 'fatal-warnings')
test_env.set('G_TEST_SRCDIR', meson.current_source_dir())

# The CLI's own golden `vibey loops --json`: the desktop parses the very document the CLI
# prints, so a change to it that the desktop cannot read fails here.
loops_golden = meson.current_source_dir() / '../../../tests/cli/golden/vibey-loops.json'

core_tests = [
  'answer',
  'discovery',
  'format',
  'hub',
  'model',
  'pairing',
  'settings',
  'state',
]
if soup_dep.found()
  core_tests += 'hub-client'
endif

foreach name : core_tests
  exe = executable(
    'test-' + name,
    'test-' + name + '.c',
    dependencies: core_dep,
    c_args: ['-DKR_LOOPS_GOLDEN="' + loops_golden + '"'],
  )
  test(name, exe, env: test_env, protocol: 'tap', args: ['--tap'], timeout: 60)
endforeach
