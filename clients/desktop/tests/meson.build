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

# The hub client's TLS tests stand up an HTTPS hub on loopback, as `vibey serve` does on a
# declared LAN (src/vibey/infrastructure/hub/tls.py), and pin its certificate. The certificate
# is made fresh at build time, so no private key is ever committed; openssl also reports its
# SHA-256 fingerprint, the independent figure the client's own must equal. Without openssl
# those tests say they were skipped.
tls_args = []
tls_files = []
openssl = find_program('openssl', required: false)
if soup_dep.found() and openssl.found()
  hub_tls = custom_target(
    'hub-tls',
    output: ['hub-cert.pem', 'hub-key.pem'],
    command: [openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '3650',
              '-subj', '/CN=vibey hub test', '-out', '@OUTPUT0@', '-keyout', '@OUTPUT1@'],
  )
  hub_fingerprint = custom_target(
    'hub-tls-fingerprint',
    input: hub_tls[0],
    output: 'hub-cert.fingerprint',
    command: [openssl, 'x509', '-in', '@INPUT@', '-noout', '-fingerprint', '-sha256'],
    capture: true,
  )
  tls_files = [hub_tls, hub_fingerprint]
  tls_args = [
    '-DKR_TEST_CERT="' + hub_tls[0].full_path() + '"',
    '-DKR_TEST_KEY="' + hub_tls[1].full_path() + '"',
    '-DKR_TEST_FINGERPRINT="' + hub_fingerprint.full_path() + '"',
  ]
endif

foreach name : core_tests
  exe = executable(
    'test-' + name,
    'test-' + name + '.c',
    dependencies: core_dep,
    c_args: ['-DKR_LOOPS_GOLDEN="' + loops_golden + '"'] + (name == 'hub-client' ? tls_args : []),
  )
  test(name, exe, env: test_env, protocol: 'tap', args: ['--tap'], timeout: 60,
       depends: name == 'hub-client' ? tls_files : [])
endforeach
