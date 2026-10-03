#!/bin/sh
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
#
# Remove the krypton interfaces from this machine — and nothing of vibey-engine's core.
#
#   sh scripts/uninstall-krypton.sh            # show what would be removed (changes nothing)
#   sh scripts/uninstall-krypton.sh --yes      # remove it
#   sh scripts/uninstall-krypton.sh --yes --purge   # also remove krypton's settings and pairing
#
# Without the repository:
#   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh | sh -s -- --yes
#
# It removes: the `krypton` command (krypton-app, however it was installed), the VS Code
# extension, and krypton desktop (Flatpak, the Ubuntu tarball's four files, the macOS app).
# It NEVER removes vibey-engine, the `vibey` command and its TUI, vibey's data, its database,
# or Ollama: the engine's core is not uninstalled by this or any script (docs/guides/install.md).
# It never escalates on its own: a file only root may remove is printed as a `sudo` command.
# POSIX sh on purpose, so it runs where Python does not. Every identifier below is checked
# against the source by tests/meta/test_install_scripts.py, and each may be overridden.

set -u

APP_ID="${KRYPTON_APP_ID:-io.github.the_vibey_project.krypton}"
EXTENSION_ID="${KRYPTON_EXTENSION_ID:-the-vibey-project.krypton}"
PYTHON_PACKAGE="${KRYPTON_PYTHON_PACKAGE:-krypton-app}"
EDITORS="${KRYPTON_EDITORS:-code code-insiders codium cursor windsurf}"
ROOT="${KRYPTON_ROOT:-}"
TARBALL_FILES="${ROOT}/usr/bin/krypton-desktop
${ROOT}/usr/share/applications/${APP_ID}.desktop
${ROOT}/usr/share/metainfo/${APP_ID}.metainfo.xml
${ROOT}/usr/share/icons/hicolor/scalable/apps/${APP_ID}.svg"
MAC_APPS="/Applications/krypton.app ${HOME}/Applications/krypton.app"
CONFIG_ROOT="${XDG_CONFIG_HOME:-${HOME}/.config}"
# One directory per line: the loop below splits on newlines only, because macOS's
# "Application Support" holds a space.
SETTINGS_DIRS="${CONFIG_ROOT}/krypton
${CONFIG_ROOT}/krypton-nightly
${HOME}/Library/Application Support/krypton
${HOME}/Library/Application Support/krypton-nightly"

APPLY=0
PURGE=0
for arg in "$@"; do
  case "$arg" in
    --yes) APPLY=1 ;;
    --purge) PURGE=1 ;;
    -h|--help) sed -n '4,20p' "$0" 2>/dev/null; exit 0 ;;
    *) echo "uninstall-krypton: unknown option $arg (try --help)" >&2; exit 2 ;;
  esac
done

found=0
failed=0
manual=""

have() { command -v "$1" >/dev/null 2>&1; }

# Run a removal, or only describe it on a dry run. A failure is counted and reported, never hidden.
step() {
  what="$1"; shift
  found=$((found + 1))
  if [ "$APPLY" -eq 1 ]; then
    if "$@" >/dev/null 2>&1; then
      echo "  removed: $what"
    else
      echo "  could not remove: $what (run: $*)"
      failed=$((failed + 1))
    fi
  else
    echo "  would remove: $what"
  fi
}

# Something only a person (or root) can do: collected and printed at the end, never forced.
by_hand() { found=$((found + 1)); manual="${manual}
  - $1"; }

if [ "$APPLY" -eq 1 ]; then
  echo "Removing the krypton interfaces from this machine. vibey-engine stays installed."
else
  echo "Dry run: this lists what would be removed and changes nothing. Add --yes to remove it."
fi
echo

# 1. The `krypton` command (krypton-app). Removing it leaves its dependency, vibey-engine, in place.
echo "The krypton command:"
if have uv && uv tool list 2>/dev/null | grep -q "^${PYTHON_PACKAGE} "; then
  step "${PYTHON_PACKAGE} (uv tool)" uv tool uninstall "$PYTHON_PACKAGE"
elif have pipx && pipx list --short 2>/dev/null | grep -q "^${PYTHON_PACKAGE} "; then
  step "${PYTHON_PACKAGE} (pipx)" pipx uninstall "$PYTHON_PACKAGE"
elif have python3 && python3 -m pip show "$PYTHON_PACKAGE" >/dev/null 2>&1; then
  step "${PYTHON_PACKAGE} (pip)" python3 -m pip uninstall -y "$PYTHON_PACKAGE"
else
  echo "  not installed"
fi

# 2. The editor extension, in every VS Code-family editor that has it.
echo "The editor extension:"
seen_editor=0
for editor in $EDITORS; do
  if have "$editor" && "$editor" --list-extensions 2>/dev/null | grep -qix "$EXTENSION_ID"; then
    seen_editor=1
    step "${EXTENSION_ID} in ${editor}" "$editor" --uninstall-extension "$EXTENSION_ID"
  fi
done
[ "$seen_editor" -eq 0 ] && echo "  not installed"

# 3. krypton desktop.
echo "krypton desktop:"
seen_desktop=0
if have flatpak; then
  for scope in --user --system; do
    if flatpak info "$scope" "$APP_ID" >/dev/null 2>&1; then
      seen_desktop=1
      if [ "$PURGE" -eq 1 ]; then
        step "Flatpak ${APP_ID} (${scope#--}) and its data" flatpak uninstall "$scope" -y --delete-data "$APP_ID"
      else
        step "Flatpak ${APP_ID} (${scope#--})" flatpak uninstall "$scope" -y "$APP_ID"
      fi
    fi
  done
fi
tarball_left=""
for file in $TARBALL_FILES; do
  if [ -e "$file" ]; then
    seen_desktop=1
    if [ "$(id -u)" -eq 0 ]; then
      step "$file" rm -f "$file"
    else
      tarball_left="${tarball_left} ${file}"
    fi
  fi
done
[ -n "$tarball_left" ] && by_hand "the Ubuntu install's files need root: sudo rm -f${tarball_left}"
for app in $MAC_APPS; do
  if [ -d "$app" ]; then
    seen_desktop=1
    # Only the app this project built: its XML Info.plist must name krypton's identifier
    # (scripts/macos_app_bundle.py writes it), so another app called krypton is never removed.
    if grep -A1 '<key>CFBundleIdentifier</key>' "${app}/Contents/Info.plist" 2>/dev/null \
         | grep -q "<string>${APP_ID}</string>"; then
      step "$app" rm -rf "$app"
    else
      echo "  left alone: $app (it is not krypton's app: its bundle identifier is not ${APP_ID})"
    fi
  fi
done
[ "$seen_desktop" -eq 0 ] && echo "  not installed"

# 4. Settings and pairing — only with --purge. The hub is told to forget the device first.
echo "krypton's settings and pairing:"
old_ifs=$IFS
IFS='
'
for dir in $SETTINGS_DIRS; do
  [ -d "$dir" ] || continue
  if [ -f "${dir}/paired-hub.ini" ]; then
    device=$(sed -n '/^\[device\]/,/^\[/{s/^id=//p;}' "${dir}/paired-hub.ini" | head -n 1)
    [ -n "$device" ] && by_hand "ask the hub to forget this device (on the hub's machine): vibey hub revoke ${device}"
  fi
  if [ "$PURGE" -eq 1 ]; then
    step "$dir" rm -rf "$dir"
  else
    echo "  kept: $dir (add --purge to remove it)"
  fi
done
IFS=$old_ifs

# 5. The phone and the browser cannot be reached from here.
by_hand "the iOS or Android app, if you have it: remove it on the phone (press and hold krypton, then Remove)"
by_hand "the web client keeps nothing installed; stop serving its folder if you host it"

echo
if [ -n "$manual" ]; then
  echo "Left for you:${manual}"
  echo
fi
if [ "$APPLY" -eq 1 ]; then
  echo "Done: ${failed} step(s) could not be completed. vibey-engine was not touched."
  echo "To put krypton back: uv tool install krypton-app  (or: sh scripts/install.sh --with-krypton)"
else
  echo "Nothing was changed. Run again with --yes to remove what is listed."
fi
[ "$failed" -eq 0 ]
