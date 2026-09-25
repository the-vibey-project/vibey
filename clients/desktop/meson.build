# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Krypton desktop: the vibey desktop app, in C17 on GTK 4 and libadwaita (clients/desktop).
#
#   libkryptondesktop  the pure-C core: models, the hub client, state, formatting,
#                      pairing, discovery. Each module is a header (its interface) and a .c.
#   krypton-desktop    the thin GTK views over the core (-Dgui).
#
# Tests are GLib tests over the core. CI builds with -Db_sanitize=address,undefined and
# measures the core's coverage with gcovr (.github/workflows/ci.yml, job `desktop`).
project(
  'krypton-desktop',
  'c',
  version: '0.1.0',
  license: 'MIT',
  meson_version: '>= 1.1.0',
  default_options: [
    'c_std=c17',
    'warning_level=2',
    'werror=true',
    'buildtype=debugoptimized',
  ],
)

cc = meson.get_compiler('c')
add_project_arguments(
  cc.get_supported_arguments(
    '-D_DEFAULT_SOURCE',
    '-D_DARWIN_C_SOURCE',
    '-Wshadow',
    '-Wstrict-prototypes',
    '-Wmissing-prototypes',
    '-Wformat=2',
    '-Wno-unused-parameter',
    '-Wno-missing-field-initializers',
    '-fno-common',
  ),
  language: 'c',
)

channel = get_option('channel')
channel_id = channel == 'nightly' ? 'KR_CHANNEL_NIGHTLY' : 'KR_CHANNEL_STABLE'
app_id = channel == 'nightly' ? 'io.github.the_vibey_project.Krypton.Nightly' : 'io.github.the_vibey_project.Krypton'
app_name = channel == 'nightly' ? 'Krypton Nightly' : 'Krypton'

glib_dep = dependency('glib-2.0', version: '>= 2.74')
gio_dep = dependency('gio-2.0', version: '>= 2.74')
json_dep = dependency(
  'json-glib-1.0',
  version: '>= 1.6',
  fallback: ['json-glib', 'json_glib_dep'],
  default_options: [
    'introspection=disabled',
    'gtk_doc=disabled',
    'tests=false',
    'man=false',
  ],
)
soup_dep = dependency('libsoup-3.0', required: get_option('hub_transport'))
math_dep = cc.find_library('m', required: false)

# The design tokens (ADR-0066) are generated once for every surface; the desktop reads the
# C header and the GTK stylesheets straight from design/dist, never a copy.
# is_system: the generated header's banner quotes a glob (tokens/*.tokens.json) inside a
# comment, which -Wcomment would turn into an error under -Werror.
tokens_inc = include_directories('../../design/dist/c', is_system: true)
gtk_css_dir = meson.current_source_dir() / '../../design/dist/gtk'

core_sources = files(
  'src/core/kr-answer.c',
  'src/core/kr-discovery.c',
  'src/core/kr-format.c',
  'src/core/kr-hub.c',
  'src/core/kr-model.c',
  'src/core/kr-pairing.c',
  'src/core/kr-settings.c',
  'src/core/kr-state.c',
)
core_deps = [glib_dep, gio_dep, json_dep, math_dep]
core_args = []

if soup_dep.found()
  core_sources += files('src/core/kr-hub-client.c')
  core_deps += soup_dep
  core_args += '-DKR_HAVE_HUB_CLIENT'
endif

# Discovery: Avahi on Linux, dns_sd.h (Bonjour) on macOS. Without either, Krypton still
# pairs by typing a hub's address and 6-digit code.
discovery_backend = 'none'
if host_machine.system() == 'darwin'
  if not get_option('discovery').disabled() and cc.has_header('dns_sd.h')
    core_sources += files('src/core/kr-discovery-dnssd.c')
    core_args += '-DKR_HAVE_DNSSD'
    discovery_backend = 'dns_sd'
  endif
else
  avahi_client_dep = dependency('avahi-client', required: get_option('discovery'))
  avahi_glib_dep = dependency('avahi-glib', required: get_option('discovery'))
  if avahi_client_dep.found() and avahi_glib_dep.found()
    core_sources += files('src/core/kr-discovery-avahi.c')
    core_deps += [avahi_client_dep, avahi_glib_dep]
    core_args += '-DKR_HAVE_AVAHI'
    discovery_backend = 'avahi'
  endif
endif

core_inc = include_directories('src/core')
core_lib = static_library(
  'kryptondesktop',
  core_sources,
  include_directories: [core_inc, tokens_inc],
  dependencies: core_deps,
  c_args: core_args,
)
core_dep = declare_dependency(
  link_with: core_lib,
  include_directories: [core_inc, tokens_inc],
  dependencies: core_deps,
  compile_args: core_args,
)

subdir('tests')

gtk_dep = dependency('gtk4', version: '>= 4.12', required: get_option('gui'))
adw_dep = dependency('libadwaita-1', version: '>= 1.4', required: get_option('gui'))
if gtk_dep.found() and adw_dep.found() and soup_dep.found()
  subdir('src/app')
endif

summary(
  {
    'channel': '@0@ (@1@)'.format(channel, app_id),
    'hub transport': soup_dep.found(),
    'discovery': discovery_backend,
    'gui': gtk_dep.found() and adw_dep.found() and soup_dep.found(),
  },
  section: 'Krypton desktop',
)
