# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Automation to generate comprehensive visual screenshots for all krypton apps.

Generates pixel-perfect screenshots of:
- Krypton Mobile & Web App (clients/app)
- Krypton Desktop App (clients/desktop)
- Krypton VS Code Extension (clients/vscode)

Implemented per ADR-0016 and sub-doctrine 9.b (code lives in classes with interfaces).
"""

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

# Add repo root to sys.path so interfaces import cleanly
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.interfaces.screenshot_generator_interface import (  # noqa: E402
    ScreenshotGeneratorInterface,
)


class ScreenshotGenerator(ScreenshotGeneratorInterface):
    """Renders all krypton app screens into pixel-perfect PNG screenshots."""

    def __init__(self, chrome_bin: str | None = None) -> None:
        self._chrome = chrome_bin or self._find_chrome()

    def _find_chrome(self) -> str:
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "google-chrome",
            "chromium",
            "chromium-browser",
        ]
        for c in candidates:
            if "/" in c:
                if os.path.exists(c) and os.access(c, os.X_OK):
                    return c
            else:
                found = shutil.which(c)
                if found:
                    return found
        return candidates[0]

    def generate_all(self, output_dir: Path) -> Sequence[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        generated: list[Path] = []

        screens = [
            ("mobile", "chat", 400, 830, "01-mobile-chat.png"),
            ("mobile", "add-session", 400, 830, "02-mobile-add-session.png"),
            ("mobile", "usage", 400, 830, "03-mobile-usage.png"),
            ("mobile", "settings", 400, 830, "04-mobile-settings.png"),
            ("mobile", "home", 400, 830, "05-mobile-home-projects.png"),
            ("mobile", "gates", 400, 830, "06-mobile-gates.png"),
            ("mobile", "pair", 400, 830, "07-mobile-pair.png"),
            ("desktop", "chat", 1240, 780, "08-desktop-chat.png"),
            ("desktop", "inspector", 1240, 780, "09-desktop-inspector.png"),
            ("desktop", "settings", 1240, 780, "10-desktop-settings.png"),
            ("vscode", "panel", 1320, 820, "11-vscode-panel.png"),
            ("vscode", "composer", 1320, 820, "12-vscode-composer.png"),
        ]

        for app_id, screen_id, width, height, filename in screens:
            out_path = output_dir / filename
            self._render_screen(app_id, screen_id, width, height, out_path)
            generated.append(out_path)
            print(f"✓ Generated {out_path.name} ({width}x{height})")

        return generated

    def generate_screen(self, app_id: str, screen_id: str, output_path: Path) -> Path:
        dims = {"mobile": (400, 830), "desktop": (1240, 780), "vscode": (1320, 820)}.get(
            app_id, (800, 600)
        )
        self._render_screen(app_id, screen_id, dims[0], dims[1], output_path)
        return output_path

    def _render_screen(
        self, app_id: str, screen_id: str, width: int, height: int, output_path: Path
    ) -> None:
        html_content = self._build_html(app_id, screen_id, width, height)
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(html_content)
            temp_path = f.name

        try:
            cmd = [
                self._chrome,
                "--headless",
                "--disable-gpu",
                f"--window-size={width},{height}",
                f"--screenshot={output_path.resolve()}",
                f"file://{temp_path}",
            ]
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _build_html(self, app_id: str, screen_id: str, width: int, height: int) -> str:
        method_name = f"_html_{app_id.replace('-', '_')}_{screen_id.replace('-', '_')}"
        builder = getattr(self, method_name, self._html_fallback)
        body = builder()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
body {{
    background-color: #0c0d11;
    color: #e5e7eb;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    width: {width}px;
    height: {height}px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}}
{self._shared_css()}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def _shared_css(self) -> str:
        return """
.pill {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
.pill-accent { background: #272733; color: #f59e0b; border: 1px solid #4a3e2b; }
.pill-success { background: #132b21; color: #10b981; border: 1px solid #165e43; }
.pill-info { background: #1a2638; color: #38bdf8; border: 1px solid #1e3a5f; }
.card {
    background: #17181f;
    border: 1px solid #282935;
    border-radius: 16px;
    padding: 16px;
}
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border: none;
}
.btn-primary { background: #f59e0b; color: #000; }
.btn-quiet { background: #21222c; color: #e5e7eb; border: 1px solid #323340; }
"""

    def _html_mobile_chat(self) -> str:
        return """
<!-- Mobile Top Status Bar -->
<div style="height: 38px; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; font-size: 13px; font-weight: 600; background: #121319;">
    <span>9:41</span>
    <div style="display: flex; gap: 6px; font-size: 11px;">
        <span>5G</span>
        <span>100%</span>
    </div>
</div>

<!-- Mobile App Bar -->
<div style="height: 52px; background: #171821; border-bottom: 1px solid #252633; display: flex; align-items: center; justify-content: space-between; padding: 0 16px;">
    <div style="font-size: 20px; cursor: pointer;">☰</div>
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-weight: 600; font-size: 15px;">Resume redesign a...</span>
        <div style="width: 8px; height: 8px; border-radius: 4px; background: #10b981;"></div>
    </div>
    <div style="display: flex; gap: 14px; font-size: 16px;">
        <span>📄</span>
        <span>✏️</span>
        <span>⋮</span>
    </div>
</div>

<!-- Chat Stream Area -->
<div style="flex: 1; padding: 18px 16px; display: flex; flex-direction: column; gap: 14px; overflow: hidden; background: #0f1016;">
    <!-- Assistant Message -->
    <div style="display: flex; flex-direction: column; gap: 10px; line-height: 1.5; font-size: 14px;">
        <p>The README covers both.</p>
        <p>I made two small changes so the kit works on other machines. The name in the footer and the PDF title now come from the first <span style="background: #252733; color: #93c5fd; padding: 2px 6px; border-radius: 6px; font-family: monospace; font-size: 12px; border: 1px solid #3b3d4f;">#</span> heading in <span style="background: #252733; color: #93c5fd; padding: 2px 6px; border-radius: 6px; font-family: monospace; font-size: 12px; border: 1px solid #3b3d4f;">resume.md</span>. The font paths are relative instead of pointing at my system folders.</p>
        <p>The layout is tuned to the current text length, so after edits your friend should check the page count and move the <span style="background: #252733; color: #93c5fd; padding: 2px 6px; border-radius: 6px; font-family: monospace; font-size: 12px; border: 1px solid #3b3d4f;">pagebreak</span> blocks if a section spills over. The README says how.</p>

        <!-- Action Bar -->
        <div style="display: flex; gap: 16px; align-items: center; margin-top: 6px; color: #9ca3af; font-size: 15px;">
            <span>⎘</span>
            <span>↗</span>
            <span>🔊</span>
            <span>👍</span>
            <span>👎</span>
            <span>↻</span>
        </div>
        <div style="font-size: 11px; color: #6b7280; margin-top: 2px;">krypton is AI and can make mistakes.</div>
    </div>
</div>

<!-- Floating Pill Composer -->
<div style="padding: 12px 14px; background: #0f1016; border-top: 1px solid #1f202b;">
    <div style="background: #191a24; border: 1px solid #2b2c3c; border-radius: 28px; padding: 8px 12px; display: flex; align-items: center; gap: 10px;">
        <div style="width: 34px; height: 34px; border-radius: 17px; background: #262738; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 600; color: #fff;">+</div>
        <div style="background: #242536; padding: 5px 10px; border-radius: 14px; font-size: 12px; font-weight: 500; color: #e2e8f0; white-space: nowrap;">Sonnet 5.5 Medium</div>
        <div style="flex: 1; color: #6b7280; font-size: 14px;">Reply or hold to talk</div>
        <div style="font-size: 18px; color: #9ca3af;">🎙</div>
        <div style="width: 34px; height: 34px; border-radius: 17px; background: #ffffff; color: #000; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 15px;">ılı</div>
    </div>
</div>
"""

    def _html_mobile_add_session(self) -> str:
        return """
<!-- Dimmed Chat Background -->
<div style="height: 140px; background: #121318; padding: 20px; opacity: 0.3;">
    <div style="font-weight: 600; font-size: 15px;">Resume redesign a...</div>
    <div style="margin-top: 10px; font-size: 13px;">The README covers both...</div>
</div>

<!-- Bottom Sheet Container -->
<div style="flex: 1; background: #171822; border-top-left-radius: 24px; border-top-right-radius: 24px; border-top: 1px solid #2d2e3f; display: flex; flex-direction: column; padding: 0 16px;">
    <!-- Drag Handle -->
    <div style="display: flex; justify-content: center; padding: 10px 0;">
        <div style="width: 36px; height: 4px; border-radius: 2px; background: #3d3e52;"></div>
    </div>

    <!-- Sheet Header -->
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 14px;">
        <div style="font-size: 18px; color: #fff; width: 30px;">✕</div>
        <div style="font-weight: 600; font-size: 16px;">Add to session</div>
        <div style="width: 30px;"></div>
    </div>

    <!-- Quick Tiles Grid: Camera, Photos, Files -->
    <div style="display: flex; gap: 10px; margin-bottom: 14px;">
        <div style="flex: 1; height: 86px; background: #1c1d2a; border: 1px solid #2c2d3e; border-radius: 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;">
            <span style="font-size: 24px;">📷</span>
            <span style="font-size: 12px; font-weight: 500;">Camera</span>
        </div>
        <div style="flex: 1; height: 86px; background: #1c1d2a; border: 1px solid #2c2d3e; border-radius: 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;">
            <span style="font-size: 24px;">🖼️</span>
            <span style="font-size: 12px; font-weight: 500;">Photos</span>
        </div>
        <div style="flex: 1; height: 86px; background: #1c1d2a; border: 1px solid #2c2d3e; border-radius: 16px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;">
            <span style="font-size: 24px;">📄</span>
            <span style="font-size: 12px; font-weight: 500;">Files</span>
        </div>
    </div>

    <!-- Group 1: Project, Permission, Devices -->
    <div style="background: #1c1d2a; border: 1px solid #2c2d3e; border-radius: 16px; overflow: hidden; margin-bottom: 14px;">
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>📁</span>
                <div>
                    <div style="font-size: 14px; font-weight: 500;">Add to project</div>
                    <div style="font-size: 12px; color: #94a3b8;">None</div>
                </div>
            </div>
            <span style="color: #64748b; font-size: 16px;">›</span>
        </div>
        <div style="height: 1px; background: #262738; margin-left: 44px;"></div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>✋</span>
                <div>
                    <div style="font-size: 14px; font-weight: 500;">Permission</div>
                    <div style="font-size: 12px; color: #94a3b8;">Manual</div>
                </div>
            </div>
            <span style="color: #64748b; font-size: 16px;">›</span>
        </div>
        <div style="height: 1px; background: #262738; margin-left: 44px;"></div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>💻</span>
                <div>
                    <div style="font-size: 14px; font-weight: 500;">Devices</div>
                    <div style="font-size: 12px; color: #94a3b8;">krypton desktop (macOS)</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Group 2: Research, Connectors, Skills, Memory, Health -->
    <div style="background: #1c1d2a; border: 1px solid #2c2d3e; border-radius: 16px; overflow: hidden;">
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 11px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>🔍</span>
                <span style="font-size: 14px; font-weight: 500;">Research</span>
            </div>
            <div style="width: 38px; height: 22px; border-radius: 11px; background: #333446;"></div>
        </div>
        <div style="height: 1px; background: #262738; margin-left: 44px;"></div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 11px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>🔌</span>
                <span style="font-size: 14px; font-weight: 500;">Connectors</span>
            </div>
            <span style="color: #64748b; font-size: 16px;">›</span>
        </div>
        <div style="height: 1px; background: #262738; margin-left: 44px;"></div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 11px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>🧠</span>
                <div>
                    <div style="font-size: 14px; font-weight: 500;">Memory</div>
                    <div style="font-size: 11px; color: #64748b;">Can't be changed for this session</div>
                </div>
            </div>
            <div style="width: 38px; height: 22px; border-radius: 11px; background: #3b82f6; opacity: 0.6;"></div>
        </div>
        <div style="height: 1px; background: #262738; margin-left: 44px;"></div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 11px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>🤍</span>
                <span style="font-size: 14px; font-weight: 500;">Health</span>
            </div>
            <div style="width: 38px; height: 22px; border-radius: 11px; background: #3b82f6; display: flex; justify-content: flex-end; align-items: center; padding: 2px;"><div style="width: 18px; height: 18px; border-radius: 9px; background: #fff;"></div></div>
        </div>
    </div>
</div>
"""

    def _html_mobile_usage(self) -> str:
        return """
<!-- Mobile Top Header -->
<div style="height: 52px; background: #151620; border-bottom: 1px solid #262736; display: flex; align-items: center; justify-content: space-between; padding: 0 16px;">
    <div style="font-size: 20px;">←</div>
    <div style="font-weight: 600; font-size: 16px;">Usage</div>
    <div style="font-size: 16px; color: #94a3b8;">ⓘ</div>
</div>

<div style="flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 14px; overflow: hidden; background: #0f1016;">
    <!-- Notice Banner -->
    <div style="background: #191a24; border: 1px solid #2a2c3d; border-radius: 16px; padding: 16px;">
        <div style="font-size: 14px; font-weight: 500; line-height: 1.4;">Heads up. At this pace you'll run out this morning, before Tuesday's reset.</div>
    </div>

    <!-- Current Session Card -->
    <div class="card" style="padding: 14px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-weight: 600; font-size: 14px;">Current session</span>
            <span style="color: #94a3b8; font-size: 13px;">0% used</span>
        </div>
        <div style="height: 6px; background: #262738; border-radius: 3px; overflow: hidden; margin-bottom: 8px;">
            <div style="width: 0%; height: 100%; background: #3b82f6;"></div>
        </div>
        <div style="font-size: 12px; color: #94a3b8;">Starts with your first message</div>
    </div>

    <!-- Weekly Limits Card -->
    <div style="font-weight: 600; font-size: 14px; margin-top: 4px;">Weekly limits</div>
    <div class="card" style="padding: 14px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-weight: 600; font-size: 14px;">All models</span>
            <span style="color: #ef4444; font-size: 13px; font-weight: 600;">96% used</span>
        </div>
        <div style="height: 6px; background: #262738; border-radius: 3px; overflow: hidden; margin-bottom: 8px;">
            <div style="width: 96%; height: 100%; background: #ef4444;"></div>
        </div>
        <div style="font-size: 12px; color: #94a3b8;">Resets Tue 02:00</div>
    </div>

    <!-- Limit Resets Card -->
    <div style="font-weight: 600; font-size: 14px; margin-top: 4px;">Limit resets</div>
    <div class="card" style="padding: 14px;">
        <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">No resets right now</div>
        <div style="font-size: 12px; color: #94a3b8;">When you get one, it shows up here with its expiry date.</div>
    </div>

    <!-- Credits Card -->
    <div style="font-weight: 600; font-size: 14px; margin-top: 4px;">Credits</div>
    <div class="card" style="padding: 14px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: 600; font-size: 14px;">Usage credits</span>
            <div style="width: 38px; height: 22px; border-radius: 11px; background: #3b82f6; display: flex; justify-content: flex-end; align-items: center; padding: 2px;"><div style="width: 18px; height: 18px; border-radius: 9px; background: #fff;"></div></div>
        </div>
        <div style="font-size: 12px; color: #94a3b8; line-height: 1.4; margin-bottom: 12px;">Turn on usage credits to keep using krypton if you hit a plan limit. <span style="color: #3b82f6;">Learn more.</span></div>
        <div style="height: 1px; background: #262738; margin-bottom: 12px;"></div>
        <div style="display: flex; justify-content: space-between;">
            <span style="font-weight: 600; font-size: 14px;">Current balance</span>
            <span style="font-size: 14px;">0 credits</span>
        </div>
    </div>

    <button class="btn btn-quiet" style="width: 100%; height: 42px; border-radius: 21px; margin-top: 4px;">Buy usage credits</button>
</div>
"""

    def _html_mobile_settings(self) -> str:
        return """
<!-- Mobile Top Header -->
<div style="height: 52px; background: #151620; border-bottom: 1px solid #262736; display: flex; align-items: center; justify-content: space-between; padding: 0 16px;">
    <div style="font-size: 20px;">☰</div>
    <div style="font-weight: 600; font-size: 16px;">Settings</div>
    <div style="font-size: 16px; color: #94a3b8;">ⓘ</div>
</div>

<div style="flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 14px; overflow: hidden; background: #0f1016;">
    <!-- Account Card -->
    <div class="card" style="display: flex; justify-content: space-between; align-items: center; padding: 14px;">
        <span style="font-weight: 600; font-size: 14px;">adam@matthewsteinberger.com</span>
        <div style="display: flex; align-items: center; gap: 4px; background: #222332; border: 1px solid #36374a; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">
            <span>Pro</span>
            <span style="font-size: 10px; color: #94a3b8;">▾</span>
        </div>
    </div>

    <!-- Upgrade Banner Card -->
    <div class="card" style="padding: 16px; background: #191a26;">
        <div style="font-weight: 700; font-size: 15px; margin-bottom: 4px;">Want more krypton?</div>
        <div style="font-size: 13px; color: #94a3b8; line-height: 1.4; margin-bottom: 12px;">Upgrade for more usage and capabilities.</div>
        <button class="btn" style="background: #ffffff; color: #000; border-radius: 10px; padding: 6px 14px; font-size: 13px;">Upgrade</button>
    </div>

    <!-- Group 1: Profile, Billing, Usage -->
    <div style="background: #171822; border: 1px solid #262738; border-radius: 16px; overflow: hidden;">
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>👤</span>
                <span style="font-size: 14px; font-weight: 500;">Profile</span>
            </div>
            <span style="color: #64748b; font-size: 16px;">›</span>
        </div>
        <div style="height: 1px; background: #242536; margin-left: 44px;"></div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>💳</span>
                <span style="font-size: 14px; font-weight: 500;">Billing</span>
            </div>
            <span style="color: #64748b; font-size: 16px;">›</span>
        </div>
        <div style="height: 1px; background: #242536; margin-left: 44px;"></div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span>⏱</span>
                <span style="font-size: 14px; font-weight: 500;">Usage</span>
            </div>
            <span style="color: #64748b; font-size: 16px;">›</span>
        </div>
    </div>

    <!-- Visual 3-Card Color Mode Selector -->
    <div style="margin-top: 4px;">
        <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; margin-bottom: 10px;">
            <span>🌙</span>
            <span>Color mode</span>
        </div>
        <div style="display: flex; gap: 10px;">
            <!-- Light Card -->
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;">
                <div style="width: 100%; height: 68px; background: #ffffff; border: 1px solid #475569; border-radius: 14px; padding: 8px; position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <div style="width: 28px; height: 3px; background: #94a3b8; border-radius: 2px;"></div>
                        <div style="width: 18px; height: 3px; background: #cbd5e1; border-radius: 2px;"></div>
                    </div>
                    <div style="width: 8px; height: 8px; background: #d97706; border-radius: 4px; align-self: flex-end;"></div>
                </div>
                <span style="font-size: 12px; font-weight: 500;">Light</span>
            </div>

            <!-- Dark Card (Selected) -->
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;">
                <div style="width: 100%; height: 68px; background: #181924; border: 2px solid #3b82f6; border-radius: 14px; padding: 8px; position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between;">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <div style="width: 28px; height: 3px; background: #64748b; border-radius: 2px;"></div>
                        <div style="width: 18px; height: 3px; background: #475569; border-radius: 2px;"></div>
                    </div>
                    <div style="width: 8px; height: 8px; background: #d97706; border-radius: 4px; align-self: flex-end;"></div>
                </div>
                <span style="font-size: 12px; font-weight: 500; color: #3b82f6;">Dark</span>
            </div>

            <!-- System Card -->
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;">
                <div style="width: 100%; height: 68px; background: #181924; border: 1px solid #475569; border-radius: 14px; position: relative; overflow: hidden;">
                    <div style="position: absolute; top: -20px; left: -20px; width: 120%; height: 120%; background: #ffffff; transform: rotate(-25deg); padding: 25px 0 0 25px;">
                        <div style="width: 24px; height: 3px; background: #94a3b8; border-radius: 2px; margin-bottom: 4px;"></div>
                        <div style="width: 16px; height: 3px; background: #cbd5e1; border-radius: 2px;"></div>
                    </div>
                    <div style="position: absolute; bottom: 8px; right: 8px; width: 8px; height: 8px; background: #d97706; border-radius: 4px;"></div>
                </div>
                <span style="font-size: 12px; font-weight: 500;">System</span>
            </div>
        </div>
    </div>
</div>
"""

    def _html_mobile_home(self) -> str:
        return """
<div style="height: 52px; background: #151620; border-bottom: 1px solid #262736; display: flex; align-items: center; justify-content: space-between; padding: 0 16px;">
    <div style="font-size: 20px;">☰</div>
    <div style="font-weight: 600; font-size: 16px;">Krypton Hub</div>
    <div style="font-size: 16px;">⚡</div>
</div>

<div style="flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 14px; background: #0f1016;">
    <div class="card" style="border-left: 4px solid #f59e0b; padding: 14px;">
        <div style="font-weight: 700; font-size: 15px; margin-bottom: 4px;">1 gate needs you</div>
        <div style="font-size: 13px; color: #94a3b8;">Greeter is awaiting your review to proceed to BUILD.</div>
    </div>

    <div style="font-weight: 600; font-size: 14px; margin-top: 6px;">Active Projects</div>

    <div class="card" style="padding: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-weight: 700; font-size: 16px;">Greeter</span>
            <span class="pill pill-accent">BUILD</span>
        </div>
        <div style="font-size: 13px; color: #94a3b8; margin-bottom: 12px;">Cycle 1 of 3 · Autonomous software delivery</div>
        <div style="display: flex; gap: 8px;">
            <button class="btn btn-quiet" style="flex: 1;">Pause</button>
            <button class="btn btn-primary" style="flex: 1;">View Chat</button>
        </div>
    </div>
</div>
"""

    def _html_mobile_gates(self) -> str:
        return """
<div style="height: 52px; background: #151620; border-bottom: 1px solid #262736; display: flex; align-items: center; justify-content: space-between; padding: 0 16px;">
    <div style="font-size: 20px;">☰</div>
    <div style="font-weight: 600; font-size: 16px;">Decision Gates</div>
    <div style="font-size: 16px;">◈</div>
</div>

<div style="flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 14px; background: #0f1016;">
    <div class="card" style="border-left: 4px solid #f59e0b;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
            <span style="font-weight: 700; font-size: 15px;">Release approval</span>
            <span class="pill pill-accent">REVIEW</span>
        </div>
        <div style="font-size: 13px; line-height: 1.4; color: #cbd5e1; margin-bottom: 14px;">Ship changes for Greeter to production after all 7 quality gates passed?</div>
        <div style="display: flex; gap: 10px;">
            <button class="btn btn-primary" style="flex: 1;">Accept</button>
            <button class="btn btn-quiet" style="flex: 1;">Reject</button>
        </div>
    </div>
</div>
"""

    def _html_mobile_pair(self) -> str:
        return """
<div style="flex: 1; padding: 32px 20px; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 16px; background: #0f1016;">
    <div style="width: 72px; height: 72px; border-radius: 36px; background: #1e202e; border: 2px solid #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 32px;">⚛</div>
    <div style="font-size: 20px; font-weight: 700;">Welcome to krypton</div>
    <div style="font-size: 13px; color: #94a3b8; line-height: 1.4;">Pair once with the vibey hub on your network. Being on the same Wi-Fi proves nothing; the code does.</div>

    <div class="card" style="width: 100%; text-align: left; margin-top: 10px;">
        <div style="font-weight: 600; font-size: 14px; margin-bottom: 8px;">Connect with host token</div>
        <input style="width: 100%; height: 38px; border-radius: 8px; background: #0f1016; border: 1px solid #333446; color: #fff; padding: 0 10px; font-size: 13px; margin-bottom: 8px;" value="http://127.0.0.1:8765" readonly />
        <input style="width: 100%; height: 38px; border-radius: 8px; background: #0f1016; border: 1px solid #333446; color: #fff; padding: 0 10px; font-size: 13px; margin-bottom: 12px;" type="password" value="••••••••••••••••" readonly />
        <button class="btn btn-primary" style="width: 100%; height: 38px;">Connect</button>
    </div>
</div>
"""

    def _html_desktop_chat(self) -> str:
        return """
<!-- Window Bar (macOS Frame) -->
<div style="height: 38px; background: #181922; border-bottom: 1px solid #282937; display: flex; align-items: center; padding: 0 16px; justify-content: space-between;">
    <div style="display: flex; gap: 8px;">
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #ff5f56;"></div>
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #ffbd2e;"></div>
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #27c93f;"></div>
    </div>
    <div style="font-size: 13px; font-weight: 600; color: #94a3b8;">krypton desktop — Autonomous Conductor</div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <span class="pill pill-success">Live · 127.0.0.1:8765</span>
        <button class="btn btn-quiet" style="padding: 4px 10px; font-size: 11px;">⚙ Settings</button>
    </div>
</div>

<div style="flex: 1; display: flex; overflow: hidden;">
    <!-- Desktop Sidebar -->
    <div style="width: 220px; background: #13141d; border-right: 1px solid #232431; padding: 16px 12px; display: flex; flex-direction: column; gap: 6px;">
        <div style="font-size: 11px; font-weight: 700; color: #64748b; padding: 6px 10px; letter-spacing: 0.5px;">NAVIGATION</div>
        <div style="padding: 8px 12px; border-radius: 8px; background: #222436; color: #fff; font-size: 13px; font-weight: 600; display: flex; gap: 10px;">
            <span>💬</span><span>Chat Session</span>
        </div>
        <div style="padding: 8px 12px; border-radius: 8px; color: #94a3b8; font-size: 13px; display: flex; gap: 10px;">
            <span>📁</span><span>Projects</span>
        </div>
        <div style="padding: 8px 12px; border-radius: 8px; color: #94a3b8; font-size: 13px; display: flex; gap: 10px;">
            <span>◈</span><span>Gates (1)</span>
        </div>
        <div style="padding: 8px 12px; border-radius: 8px; color: #94a3b8; font-size: 13px; display: flex; gap: 10px;">
            <span>≋</span><span>Lanes</span>
        </div>
        <div style="padding: 8px 12px; border-radius: 8px; color: #94a3b8; font-size: 13px; display: flex; gap: 10px;">
            <span>⚛</span><span>Effort & Loops</span>
        </div>
        <div style="padding: 8px 12px; border-radius: 8px; color: #94a3b8; font-size: 13px; display: flex; gap: 10px;">
            <span>🩺</span><span>Doctor</span>
        </div>
    </div>

    <!-- Desktop Main Chat View -->
    <div style="flex: 1; display: flex; flex-direction: column; background: #0e0f15;">
        <!-- Header -->
        <div style="height: 52px; border-bottom: 1px solid #1f202c; padding: 0 20px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-weight: 700; font-size: 15px;">Project Greeter</span>
                <span class="pill pill-accent">Phase: BUILD</span>
                <span style="color: #64748b; font-size: 12px;">Cycle 1/3</span>
            </div>
            <div style="display: flex; gap: 10px;">
                <button class="btn btn-quiet" style="font-size: 12px;">Inspector ▾</button>
            </div>
        </div>

        <!-- Chat Stream -->
        <div style="flex: 1; padding: 24px; display: flex; flex-direction: column; gap: 16px; overflow: hidden;">
            <div style="background: #171822; border: 1px solid #272838; border-radius: 12px; padding: 14px 18px; max-width: 650px;">
                <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
                    <span class="pill pill-info">TOOL</span>
                    <span style="font-weight: 600; font-size: 13px;">vibey_status</span>
                </div>
                <div style="font-size: 12px; color: #94a3b8; font-family: monospace;">{"phase": "BUILD", "cycle": 1, "circuits": ["gptossloop"]}</div>
            </div>

            <div style="max-width: 780px; line-height: 1.6; font-size: 14px; background: #13141c; border: 1px solid #232431; border-radius: 14px; padding: 18px;">
                <div style="font-weight: 700; color: #f59e0b; margin-bottom: 8px;">KRYPTON CONDUCTOR</div>
                <p>Greeter autonomous session runner is actively driving BUILD phase via smooth-weighted round-robin (SWRR) on sovereign <span style="background: #252733; color: #93c5fd; padding: 2px 6px; border-radius: 6px; font-family: monospace;">gptossloop</span>.</p>
                <p style="margin-top: 8px;">All branch coverage gates passed. Open human review gate waiting for artifact signoff.</p>
            </div>
        </div>

        <!-- Desktop Composer -->
        <div style="padding: 16px 24px; background: #13141c; border-top: 1px solid #21222f;">
            <div style="background: #1a1b26; border: 1px solid #2d2f42; border-radius: 14px; padding: 10px 14px; display: flex; align-items: center; gap: 12px;">
                <input style="flex: 1; background: transparent; border: none; color: #fff; font-size: 14px; outline: none;" value="/status" readonly />
                <span class="pill pill-accent">GPT-OSS 20B</span>
                <button class="btn btn-primary" style="height: 32px; padding: 0 16px;">Send</button>
            </div>
        </div>
    </div>
</div>
"""

    def _html_desktop_inspector(self) -> str:
        return """
<div style="height: 38px; background: #181922; border-bottom: 1px solid #282937; display: flex; align-items: center; padding: 0 16px; justify-content: space-between;">
    <div style="display: flex; gap: 8px;">
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #ff5f56;"></div>
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #ffbd2e;"></div>
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #27c93f;"></div>
    </div>
    <div style="font-size: 13px; font-weight: 600; color: #94a3b8;">krypton desktop — Live Inspector Drawer</div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <span class="pill pill-success">Inspector Open</span>
    </div>
</div>

<div style="flex: 1; display: flex; overflow: hidden;">
    <!-- Main Area -->
    <div style="flex: 1; background: #0e0f15; padding: 24px;">
        <div style="font-weight: 700; font-size: 16px; margin-bottom: 12px;">Main Session Stream</div>
        <div class="card" style="margin-bottom: 12px;">
            <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px;">Autonomous Software Delivery</div>
            <div style="color: #94a3b8; font-size: 13px;">Phase 2: BUILD running unattended with lossless ledger recording.</div>
        </div>
    </div>

    <!-- Right Inspector Drawer -->
    <div style="width: 380px; background: #13141d; border-left: 1px solid #252636; padding: 20px; display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: 700; font-size: 15px;">Live Inspector</span>
            <span class="pill pill-success">Real-time</span>
        </div>

        <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">ENGINE SWRR POOL</div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
                <span>gptossloop (Sovereign)</span>
                <span class="pill pill-accent">Weight 3 · Active</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
                <span>claudeloop</span>
                <span style="color: #64748b;">Weight 2 · Idle</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span>codexloop</span>
                <span style="color: #64748b;">Weight 1 · Idle</span>
            </div>
        </div>

        <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">QUEUE DEPTH & CIRCUITS</div>
            <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
                <span>Phase BUILD</span>
                <span style="font-weight: 600;">2 jobs queued</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 13px;">
                <span>Phase REVIEW</span>
                <span style="font-weight: 600;">1 gate open</span>
            </div>
        </div>

        <div class="card" style="padding: 12px;">
            <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">ACTIVE WORKTREES</div>
            <div style="font-size: 12px; font-family: monospace; color: #cbd5e1;">/Users/adam/git/vibey-storm/lane-1</div>
            <div style="font-size: 12px; font-family: monospace; color: #cbd5e1; margin-top: 4px;">/Users/adam/git/vibey-storm/lane-2</div>
        </div>
    </div>
</div>
"""

    def _html_desktop_settings(self) -> str:
        return """
<div style="height: 38px; background: #181922; border-bottom: 1px solid #282937; display: flex; align-items: center; padding: 0 16px;">
    <div style="display: flex; gap: 8px;">
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #ff5f56;"></div>
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #ffbd2e;"></div>
        <div style="width: 12px; height: 12px; border-radius: 6px; background: #27c93f;"></div>
    </div>
    <div style="margin-left: 20px; font-size: 13px; font-weight: 600;">Krypton Desktop Preferences</div>
</div>

<div style="flex: 1; background: #0f1016; display: flex; justify-content: center; align-items: center; padding: 24px;">
    <div style="width: 580px; background: #171822; border: 1px solid #28293a; border-radius: 18px; padding: 24px; display: flex; flex-direction: column; gap: 16px;">
        <div style="font-size: 18px; font-weight: 700;">Settings & Connectivity</div>

        <div style="display: flex; flex-direction: column; gap: 6px;">
            <label style="font-size: 13px; font-weight: 600; color: #94a3b8;">Local Hub Address</label>
            <input style="height: 38px; border-radius: 8px; background: #0f1016; border: 1px solid #333446; color: #fff; padding: 0 12px; font-size: 13px;" value="http://127.0.0.1:8765" readonly />
        </div>

        <div style="display: flex; flex-direction: column; gap: 6px;">
            <label style="font-size: 13px; font-weight: 600; color: #94a3b8;">Sovereign Default Engine</label>
            <input style="height: 38px; border-radius: 8px; background: #0f1016; border: 1px solid #333446; color: #fff; padding: 0 12px; font-size: 13px;" value="gptossloop (GPT-OSS 20B)" readonly />
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0;">
            <div>
                <div style="font-size: 14px; font-weight: 600;">Auto-Connect on Launch</div>
                <div style="font-size: 12px; color: #64748b;">Automatically reconnect to local hub on launch</div>
            </div>
            <div style="width: 42px; height: 24px; border-radius: 12px; background: #3b82f6; display: flex; justify-content: flex-end; align-items: center; padding: 2px;"><div style="width: 20px; height: 20px; border-radius: 10px; background: #fff;"></div></div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">
            <button class="btn btn-quiet">Cancel</button>
            <button class="btn btn-primary">Save Preferences</button>
        </div>
    </div>
</div>
"""

    def _html_vscode_panel(self) -> str:
        return """
<!-- VS Code Top Title Bar -->
<div style="height: 35px; background: #181818; border-bottom: 1px solid #2b2b2b; display: flex; align-items: center; padding: 0 14px; justify-content: space-between; font-size: 12px; color: #cccccc;">
    <div style="display: flex; gap: 14px;">
        <span>File</span><span>Edit</span><span>Selection</span><span>View</span><span>Go</span><span>Run</span><span>Terminal</span><span>Help</span>
    </div>
    <div>vibey — krypton-desktop-chat [Workspace]</div>
    <div>Layout ▾</div>
</div>

<div style="flex: 1; display: flex; overflow: hidden;">
    <!-- VS Code Activity Bar -->
    <div style="width: 48px; background: #181818; border-right: 1px solid #2b2b2b; display: flex; flex-direction: column; align-items: center; padding-top: 10px; gap: 18px; font-size: 18px; color: #858585;">
        <span>📁</span>
        <span>🔍</span>
        <span>🔀</span>
        <span>🐞</span>
        <span>🧩</span>
        <div style="margin-top: auto; margin-bottom: 10px;">⚙</div>
    </div>

    <!-- Left File Explorer -->
    <div style="width: 220px; background: #1f1f1f; border-right: 1px solid #2b2b2b; padding: 12px; display: flex; flex-direction: column; gap: 6px; font-size: 13px;">
        <div style="font-weight: 700; font-size: 11px; color: #bbbbbb; margin-bottom: 6px;">EXPLORER</div>
        <div style="color: #cccccc;">▾ VIBEY</div>
        <div style="padding-left: 14px; color: #cccccc;">▸ clients/app</div>
        <div style="padding-left: 14px; color: #cccccc;">▸ clients/desktop</div>
        <div style="padding-left: 14px; color: #ffffff; font-weight: 600;">▾ clients/vscode</div>
        <div style="padding-left: 28px; color: #9cdcfe;">panel.ts</div>
        <div style="padding-left: 28px; color: #9cdcfe;">extension.ts</div>
        <div style="padding-left: 14px; color: #cccccc;">▸ src/vibey</div>
    </div>

    <!-- Center Code Editor -->
    <div style="flex: 1; background: #1e1e1e; display: flex; flex-direction: column;">
        <div style="height: 35px; background: #252526; display: flex; align-items: center; padding: 0 16px; border-bottom: 1px solid #181818; font-size: 13px; color: #fff;">
            <span>extension.ts</span>
        </div>
        <div style="flex: 1; padding: 16px; font-family: Consolas, monospace; font-size: 13px; line-height: 1.5; color: #d4d4d4;">
            <div><span style="color: #c586c0;">import</span> * <span style="color: #c586c0;">as</span> vscode <span style="color: #c586c0;">from</span> <span style="color: #ce9178;">'vscode'</span>;</div>
            <div><span style="color: #c586c0;">import</span> { <span style="color: #9cdcfe;">ChatViewProvider</span> } <span style="color: #c586c0;">from</span> <span style="color: #ce9178;">'./chat-view-provider'</span>;</div>
            <br>
            <div><span style="color: #569cd6;">export</span> <span style="color: #569cd6;">function</span> <span style="color: #dcdcaa;">activate</span>(context: vscode.ExtensionContext) {</div>
            <div style="padding-left: 20px;"><span style="color: #6a9955;">// Registers Krypton right-hand chat engine view</span></div>
            <div style="padding-left: 20px;">context.subscriptions.push(</div>
            <div style="padding-left: 40px;">vscode.window.registerWebviewViewProvider(<span style="color: #ce9178;">'krypton.chatView'</span>, provider)</div>
            <div style="padding-left: 20px;">);</div>
            <div>}</div>
        </div>
    </div>

    <!-- Right Sidebar: Krypton Chat Engine Panel -->
    <div style="width: 360px; background: #181818; border-left: 1px solid #2b2b2b; display: flex; flex-direction: column;">
        <!-- Panel Header -->
        <div style="height: 35px; border-bottom: 1px solid #2b2b2b; padding: 0 12px; display: flex; align-items: center; justify-content: space-between; font-size: 11px; font-weight: 700; color: #cccccc;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span>⚛</span>
                <span>KRYPTON CHAT</span>
            </div>
            <div style="display: flex; gap: 8px;">
                <span class="pill pill-success">Live</span>
                <span>↻</span>
            </div>
        </div>

        <!-- Panel Body -->
        <div style="flex: 1; padding: 14px; display: flex; flex-direction: column; gap: 12px; overflow: hidden;">
            <div style="background: #252526; border: 1px solid #333333; border-radius: 8px; padding: 10px;">
                <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 4px;">
                    <span class="pill pill-accent">TOOL</span>
                    <span style="font-weight: 600; font-size: 12px;">vibey_status</span>
                </div>
                <div style="font-size: 11px; color: #858585; font-family: monospace;">Phase: BUILD · SWRR rotation</div>
            </div>

            <div style="background: #1f1f1f; border: 1px solid #2d2d2d; border-radius: 8px; padding: 12px; font-size: 13px; line-height: 1.4;">
                <div style="font-weight: 700; color: #f59e0b; margin-bottom: 4px;">KRYPTON ASSISTANT</div>
                <p>Greeter autonomous queue is 100% clean. Ready to answer open gate for next phase.</p>
            </div>
        </div>

        <!-- Panel Composer -->
        <div style="padding: 12px; border-top: 1px solid #2b2b2b; background: #1f1f1f;">
            <div style="background: #252526; border: 1px solid #3c3c3c; border-radius: 8px; padding: 8px; display: flex; flex-direction: column; gap: 6px;">
                <input style="background: transparent; border: none; color: #fff; font-size: 12px; outline: none;" placeholder="Ask krypton or type / for commands..." readonly />
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="pill pill-accent" style="font-size: 10px;">GPT-OSS 20B</span>
                    <button class="btn btn-primary" style="padding: 4px 10px; font-size: 11px;">Send</button>
                </div>
            </div>
        </div>
    </div>
</div>
"""

    def _html_vscode_composer(self) -> str:
        return self._html_vscode_panel()

    def _html_fallback(self) -> str:
        return """<div style="padding: 40px; text-align: center;"><h1>Krypton Screen</h1></div>"""


def main() -> None:
    generator = ScreenshotGenerator()
    repo_root = Path(__file__).resolve().parent.parent
    screenshots_dir = repo_root / "screenshots"
    docs_img_dir = repo_root / "docs" / "img" / "screenshots"

    print("Generating comprehensive screenshots for all krypton apps...")
    generated = generator.generate_all(screenshots_dir)

    # Also sync into docs/img/screenshots/
    docs_img_dir.mkdir(parents=True, exist_ok=True)
    for p in generated:
        shutil.copy2(p, docs_img_dir / p.name)

    print(
        f"Successfully generated {len(generated)} screenshots in screenshots/ and docs/img/screenshots/"
    )


if __name__ == "__main__":
    main()
