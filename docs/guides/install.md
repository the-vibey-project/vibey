---
description: Install vibey and every krypton interface (Desktop on macOS and Linux, VS Code extension, Web app, Android and iOS mobile app, browser launcher, and MCP chat driver) in one place, with step-by-step instructions for every skill level.
---
# Install, copy, reinstall, uninstall

> **Bottom Line Up Front (BLUF) — Every krypton interface, on every platform, in one table:**
>
> **Krypton and the vibey engine are the free, censorship-free Claude Code and Codex killer** meant to replace both. Open to everyone and 100% free of charge, vibey writes code the way a principal software engineer does — shipping high-quality, verified code rather than disposable slop. It operates as an autonomous AGI with superintelligence coming soon. **vibey** is the autonomous delivery engine; **krypton** is every app and interface you use to talk to it. You do not need any coding experience to install or use krypton.
>
> - **How to open a Terminal if you have never used one:**
>   - **On a Mac (macOS):** Hold down the **Command (⌘)** key and press **Spacebar**, type `Terminal`, and press **Return (Enter)**.
>   - **On Linux (Ubuntu, Fedora, Arch):** Press the **Super (Windows)** key, type `Terminal`, and press **Enter**.
>   - To run any command box below: copy the line, paste it into the Terminal window, and press **Enter**.
>
> | Interface | Platform | Fastest way to install & launch (copy & paste or click) |
> |---|---|---|
> | **1. Engine + Browser Launcher** (`vibey-engine` + `krypton-app`) | macOS & Linux | `curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh \| sh -s -- --with-krypton`<br>Then run `krypton` to start the local hub and open it in your browser. |
> | **2. AI Chat & IDE Driver (`vibey connect` MCP)** | Claude Code, Claude Desktop, Codex, Cursor, VS Code, Gemini CLI | `vibey connect --yes`<br>Registers `vibey mcp` in every supported AI client on your computer so you can run projects from your normal chat window. |
> | **3. krypton Desktop App** (native chat-first app) | **macOS 15+ (Apple silicon)** | Download `krypton-desktop-<version>-macos-arm64.dmg` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases), open it, drag **krypton** to **Applications**, then run:<br>`xattr -dr com.apple.quarantine /Applications/krypton.app`<br>Open **krypton** from Applications or Spotlight (`Cmd + L` focuses Chat). |
> | **3. krypton Desktop App** (native chat-first app) | **Linux (Flatpak — Ubuntu, Fedora, Arch, any distro)** | Download `krypton-desktop-<version>-linux-x86_64.flatpak` (or `aarch64`) from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and run:<br>`flatpak install --user krypton-desktop-<version>-linux-x86_64.flatpak`<br>Launch with: `flatpak run io.github.the_vibey_project.krypton` |
> | **3. krypton Desktop App** (native chat-first app) | **Linux (Ubuntu 24.04+ native tarball)** | Download `krypton-desktop-<version>-linux-x86_64.tar.gz` (or `aarch64`) from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and run:<br>`sudo apt update && sudo apt install -y libgtk-4-1 libadwaita-1-0 libsoup-3.0-0 libjson-glib-1.0-0 libavahi-client3 libavahi-glib1 glib-networking`<br>`sudo tar -xzf krypton-desktop-<version>-linux-x86_64.tar.gz -C /`<br>Launch with: `krypton-desktop` |
> | **4. krypton for VS Code / VSCodium / Cursor** | macOS & Linux | **Open VSX (VSCodium):** `codium --install-extension the-vibey-project.krypton`<br>**VS Code / Cursor:** Download `krypton-vscode-<version>.vsix` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and run `code --install-extension krypton-vscode-<version>.vsix` (or in VS Code click **Extensions → `…` → Install from VSIX…**). |
> | **5. krypton Web App** (full chat-first browser UI) | Any browser (macOS, Linux, mobile) | Download `krypton-web-<version>.tar.gz` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and run:<br>`mkdir krypton-web && tar -xzf krypton-web-<version>.tar.gz -C krypton-web && python3 -m http.server -d krypton-web`<br>Open `http://localhost:8000` in your web browser. |
> | **6. krypton Mobile App** | **Android** | Download `krypton-android-<version>.apk` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) on your Android phone and tap it to install (allow "Install unknown apps" when prompted), or from a computer run `adb install krypton-android-<version>.apk`. |
> | **6. krypton Mobile App** | **iOS (iPhone / iPad)** | Signed `.ipa` attached to releases (`krypton-ios-<version>.ipa`) for TestFlight / App Store distribution; or run directly from source in **Expo Go** (`cd clients/app && npm ci && npx expo start` and scan the QR code with your iPhone camera). |
> | **Uninstall all krypton interfaces** | macOS & Linux | `curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh \| sh -s -- --yes`<br>Removes krypton apps cleanly while leaving `vibey-engine` intact. |

---

## Step 1: Install (or reinstall, or upgrade) `vibey` and the `krypton` launcher

Run this single command in your Terminal on macOS or Linux:

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
```

What this one line does for you automatically:

1. Installs [uv](https://docs.astral.sh/uv/) (the fast Python package manager) into `~/.local/bin` if you do not already have it.
2. Installs `vibey-engine` (which puts `vibey`, all `*loop` runners, `vibey-gh`, `vibey-skills`, and `vibey-bootstrap` on your `PATH`).
3. Installs `krypton-app` (because `--with-krypton` was passed), which gives you the `krypton` command.
4. Finishes by running `vibey doctor`, which checks your machine and tells you in plain English what else needs your attention (PostgreSQL, Ollama, or an engine login).

**Safe to run again at any time:** running the exact same command again reinstalls and upgrades everything in place. If you only want the engine without the `krypton` command, omit `--with-krypton`:

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh
```

Prefer installing with `uv`, `pipx`, or `pip` directly?

```sh
uv tool install vibey-engine
uv tool install krypton-app
```

---

## Step 2: Install and open every krypton interface (platform by platform)

Every ready-built installer file is attached to the latest release on [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) (and rebuilt nightly on the [`krypton-nightly`](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly) prerelease). See the [Downloads](downloads.md) page for SHA-256 verification and signing details.

### Interface A: Connect your existing AI chat or IDE (`vibey connect` MCP driver)

If you already use **Claude Code**, **Claude Desktop**, **OpenAI Codex**, **Cursor**, **VS Code**, or **Gemini CLI**, you can drive all of vibey from inside your normal chat window without opening another app:

1. In your Terminal, run:
   ```sh
   vibey connect --yes
   ```
   *(Want to preview what files it will touch first? Run `vibey connect --dry-run`. Want to connect only one app, such as Claude Code? Run `vibey connect --client claude_code --yes`.)*
2. Restart or open your AI chat client (Claude Code, Claude Desktop, Codex, Cursor, VS Code, or Gemini CLI).
3. Ask your AI in plain English:
   - *"What vibey projects are running right now?"*
   - *"Show me any open vibey gates and help me answer them."*
   - *"Start a new vibey project called my-site that builds a static portfolio page."*

When your AI calls a `vibey_*` tool, `vibey mcp` starts the local hub (`vibey hub start`) automatically if it is not already running, and connects with a restricted `agent.token` that can view, answer non-spending questions, and start or pause work — **never** approve spending (`spend`).

---

### Interface B: The `krypton` Browser Launcher (`krypton-app`)

If you installed with `--with-krypton` (or ran `uv tool install krypton-app`), you already have the `krypton` command:

1. In your Terminal, run:
   ```sh
   krypton
   ```
2. `krypton` starts your local vibey hub (`vibey serve` on `http://127.0.0.1:8765`), waits until it is ready, and opens its status page in your default web browser.
3. Want to start the hub without opening a browser window? Run `krypton --no-browser` or `vibey hub start`.

---

### Interface C: krypton Desktop App (Native Chat-First App for macOS & Linux)

krypton desktop is a native, fast C17 / GTK 4 / libadwaita desktop app modeled after the Claude Code and Codex desktop apps. It opens directly into **Chat** (`Ctrl+L` / `Cmd+L`), starts your local hub automatically in the background, and lets you switch projects in the left sidebar, run `/` slash commands, inspect tool calls, and answer gates inline.

#### On macOS (macOS 15 Sequoia and newer, Apple silicon M1/M2/M3/M4/M5)

No Homebrew or developer tools are needed — the `.dmg` bundles its entire runtime inside `krypton.app`.

1. Go to [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and download **`krypton-desktop-<version>-macos-arm64.dmg`**.
2. Double-click the downloaded `.dmg` file in your **Downloads** folder.
3. Drag the **krypton** icon onto the **Applications** folder icon inside the window.
4. Because the app is ad-hoc signed while Developer ID notarisation secrets are not set, macOS Gatekeeper asks you to confirm the first launch. Do **either** of these once:
   - **Option 1 (one command in Terminal):**
     ```sh
     xattr -dr com.apple.quarantine /Applications/krypton.app
     ```
   - **Option 2 (using clicks only):** Double-click **krypton** in **Applications** (macOS will say it cannot verify the developer and show **Done**). Open **System Settings → Privacy & Security**, scroll to the **Security** section at the bottom, and click **Open Anyway** next to `krypton.app`.
5. Launch **krypton** from **Applications** or Spotlight. When macOS asks if krypton may find devices on your local network, click **Allow**.

#### On Linux — Any Distribution via Flatpak (Ubuntu, Fedora, Arch, Debian, Mint, openSUSE)

1. Make sure Flatpak and Flathub are enabled (`flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo`).
2. Go to [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and download:
   - **`krypton-desktop-<version>-linux-x86_64.flatpak`** (for standard Intel/AMD PCs), or
   - **`krypton-desktop-<version>-linux-aarch64.flatpak`** (for ARM64 machines).
3. In your Terminal, install the bundle from your Downloads folder:
   ```sh
   flatpak install --user ~/Downloads/krypton-desktop-*-linux-*.flatpak
   ```
4. Launch **krypton** from your desktop's application launcher, or from Terminal:
   ```sh
   flatpak run io.github.the_vibey_project.krypton
   ```

#### On Linux — Ubuntu 24.04 LTS and Newer (Native `.tar.gz` Install)

1. Install the system GTK 4 / libadwaita runtime libraries once:
   ```sh
   sudo apt update && sudo apt install -y \
     libgtk-4-1 libadwaita-1-0 libsoup-3.0-0 libjson-glib-1.0-0 \
     libavahi-client3 libavahi-glib1 glib-networking
   ```
2. Download **`krypton-desktop-<version>-linux-x86_64.tar.gz`** (or `aarch64`) from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases).
3. Unpack it into `/`:
   ```sh
   sudo tar -xzf ~/Downloads/krypton-desktop-*-linux-*.tar.gz -C /
   ```
4. Launch **krypton** from your application menu or by running `krypton-desktop` in Terminal.

#### On Linux — Building from Source (Arch, Fedora, Ubuntu)

- **Arch Linux:** `clients/desktop/packaging/arch/PKGBUILD` is in the repository, or install `meson ninja gcc pkgconf gtk4 libadwaita libsoup3 json-glib avahi glib-networking` and run `meson setup build clients/desktop && meson compile -C build && ./build/src/app/krypton-desktop`.
- **Fedora:** `clients/desktop/packaging/fedora/krypton-desktop.spec` is in the repository, or install `meson ninja-build gcc pkgconf-pkg-config gtk4-devel libadwaita-devel libsoup3-devel json-glib-devel avahi-devel avahi-glib-devel glib-networking` and build with Meson.

---

### Interface D: krypton for VS Code, VSCodium & Cursor

krypton's editor extension (`the-vibey-project.krypton`) puts a chat-first krypton sidebar, `@krypton` chat participant (`/chat`, `/mcp`, `/new`, `/next`, `/reply`, `/status`, `/pause`, `/resume`, `/unwind`), and inline gate approval cards inside your editor. See the [VS Code extension guide](vscode-extension.md) for every detail.

#### Method 1: Install without a Terminal (Graphical UI in VS Code, Cursor, or VSCodium)

1. Download **`krypton-vscode-<version>.vsix`** from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases).
2. Open **VS Code** (or **Cursor** / **VSCodium**).
3. Click the **Extensions** icon on the left sidebar (or press **Cmd+Shift+X** on macOS / **Ctrl+Shift+X** on Linux).
4. Click the **`…` (three dots)** menu in the top-right corner of the Extensions panel and choose **Install from VSIX…**.
5. Select the downloaded `krypton-vscode-<version>.vsix` file.
6. Click the **krypton atom** icon on the left activity bar to open the chat-first panel!

#### Method 2: Install from the Terminal

- **In VSCodium or any Open VSX editor:**
  ```sh
  codium --install-extension the-vibey-project.krypton
  ```
- **In VS Code (from the downloaded `.vsix` file):**
  ```sh
  code --install-extension ~/Downloads/krypton-vscode-*.vsix
  ```
  *(On macOS, if `code` is not on your `PATH`, run: `"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" --install-extension ~/Downloads/krypton-vscode-*.vsix`)*
- **In Cursor (from the downloaded `.vsix` file):**
  ```sh
  cursor --install-extension ~/Downloads/krypton-vscode-*.vsix
  ```

---

### Interface E: krypton Web App (Full Chat-First Browser App)

The krypton web bundle is a complete static web app built from `clients/app` (`expo export --platform web`). It opens directly to the **Chat** tab in any modern desktop or mobile browser.

1. Download **`krypton-web-<version>.tar.gz`** from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases).
2. Unpack it and start Python's built-in web server in one command:
   ```sh
   mkdir -p ~/krypton-web
   tar -xzf ~/Downloads/krypton-web-*.tar.gz -C ~/krypton-web
   python3 -m http.server 8000 -d ~/krypton-web
   ```
3. Open **[http://localhost:8000](http://localhost:8000)** in Safari, Chrome, Firefox, or Edge.
4. Make sure your local hub is running (`vibey hub start` or `krypton --no-browser`). In the web app's **Settings** tab, verify the Hub URL (`http://127.0.0.1:8765`) and paste your host token (from `~/Library/Application Support/vibey/hub/token` on macOS or `~/.local/state/vibey/hub/token` on Linux), then switch to the **Chat** tab.

---

### Interface F: krypton Mobile App (Android & iOS)

The mobile app (`clients/app`) gives you the same chat-first interface, project picker, slash commands, and inline gate approvals from your phone or tablet over your local Wi-Fi network.

#### On Android (Phone or Tablet)

**Option 1 — Direct install on your Android phone (no computer needed):**

1. On your Android phone, open [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) in your browser and tap **`krypton-android-<version>.apk`** to download it.
2. Tap the downloaded `.apk` notification (or open it in your **Files / Downloads** app).
3. If Android asks for permission to **Install unknown apps** from your browser or Files app, tap **Settings**, toggle **Allow from this source** on, and tap **Install**.
4. Open **krypton** from your home screen or app drawer.

**Option 2 — Install from your computer over USB (`adb`):**

```sh
adb install ~/Downloads/krypton-android-*.apk
```

#### On iOS (iPhone or iPad)

Apple requires every iOS app installed on a physical iPhone or iPad to be signed. You have two ways to run krypton on iOS:

- **Via TestFlight / App Store (`.ipa` release build):** While the repository's `EXPO_TOKEN` is set, every release builds and attaches the signed `krypton-ios-<version>.ipa` for TestFlight and App Store Connect (note: an `.ipa` file cannot be installed by double-clicking it on a phone; it is delivered through Apple's TestFlight app).
- **Run live on your iPhone right now with Expo Go (free, no Apple Developer account required):**
  1. Install **Expo Go** from the Apple App Store on your iPhone.
  2. On your computer (connected to the same Wi-Fi network), copy the repository if you haven't already, and start the Expo server:
     ```sh
     cd clients/app
     npm ci
     npx expo start
     ```
  3. Open the **Camera** app on your iPhone, point it at the QR code printed in your Terminal, and tap **Open in Expo Go**.

#### Connecting your Phone or Tablet to your Computer's Hub

To talk to your computer's hub from your phone over Wi-Fi:

1. On your computer, edit `vibey.toml` to allow LAN connections and set a folder for new projects:
   ```toml
   [hub]
   lan = true
   projects_root = "~/vibey-projects"
   ```
2. Start the hub on your computer:
   ```sh
   vibey hub start
   ```
3. On your phone, open **krypton → Settings**, enter your computer's local network address (`https://<your-computer-ip>:8765`), and connect.

---

## Copy the whole codebase

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --from-source ~/vibey
```

That clones every commit into `~/vibey`, builds it with `uv sync --extra dev`, and installs
the commands from that copy, so what you run is what you can read and change. Add `--with-krypton` to also install `krypton-app` from that source checkout. Run it again
and it updates the same copy instead of making a second one. If the repository's home is
ever gone, the [Rebuild](../continuation/rebuild.md) prompt starts from any surviving copy.

## Remove the krypton interfaces

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh | sh
```

On its own it changes nothing: it lists what it found. Add `--yes` to remove it:

```sh
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh | sh -s -- --yes
```

It removes the `krypton` command (whether uv, pipx or pip installed it), the editor extension
from every VS Code-family editor that has it, and krypton desktop — the Flatpak, the four
files the Ubuntu install put under `/usr`, and the macOS app, after checking the app really is
krypton's. Settings and the desktop's pairing with a hub are kept unless you add `--purge`;
before you do, it prints the `vibey hub revoke` command that makes the hub forget the device
too. It never asks for administrator rights: a file only root may remove is printed as a
`sudo` command for you to run. The phone app is removed on the phone.

## What is never uninstalled

vibey-engine's core — the engine, its runners, the `vibey` command and its TUI, its data, its
database, and the models it runs on — has no uninstall script and never will (sub-doctrine
10.m, [ADR-0082](../architecture/decisions/0082-install-copy-reinstall-and-a-core-that-stays.md)).
It is your machine: you can still remove anything with your own tools. The project simply
never offers to destroy its core.
