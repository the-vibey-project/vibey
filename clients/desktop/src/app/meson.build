# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# The GTK views. libadwaita loads style.css and style-dark.css from the application's
# resource base path by itself; both are the design tokens' generated GTK stylesheets
# (design/dist/gtk, ADR-0066), compiled in unchanged.
gnome = import('gnome')

resources = gnome.compile_resources(
  'krypton-resources',
  'krypton.gresource.xml',
  source_dir: [gtk_css_dir],
  c_name: 'krypton',
)

executable(
  'krypton-desktop',
  'main.c',
  'kr-mark.c',
  'kr-window.c',
  resources,
  dependencies: [core_dep, gtk_dep, adw_dep],
  c_args: [
    '-DKRYPTON_CHANNEL=' + channel_id,
    '-DKRYPTON_VERSION="@0@"'.format(meson.project_version()),
  ],
  install: true,
)

desktop_conf = configuration_data()
desktop_conf.set('APP_ID', app_id)
desktop_conf.set('APP_NAME', app_name)
data_dir = meson.project_source_root() / 'data'
configure_file(
  input: data_dir / 'io.github.the_vibey_project.Krypton.desktop.in',
  output: app_id + '.desktop',
  configuration: desktop_conf,
  install: true,
  install_dir: get_option('datadir') / 'applications',
)
configure_file(
  input: data_dir / 'io.github.the_vibey_project.Krypton.metainfo.xml.in',
  output: app_id + '.metainfo.xml',
  configuration: desktop_conf,
  install: true,
  install_dir: get_option('datadir') / 'metainfo',
)
install_data(
  meson.project_source_root() / '../../design/identity/icon.svg',
  rename: app_id + '.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps',
)
