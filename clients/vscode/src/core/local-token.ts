// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Reads the host's hub token on the local machine (ADR-0068, ADR-0085).
 * The token file is mode 0600 in a 0700 directory, proving the caller is the host account.
 */
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type { LocalHubTokenInterface } from '../extension/interfaces/local-token-interface';

export class LocalHubToken implements LocalHubTokenInterface {
  constructor(
    private readonly platform: NodeJS.Platform = process.platform,
    private readonly home: string = os.homedir(),
    private readonly env: NodeJS.ProcessEnv = process.env,
    private readonly filesystem: {
      existsSync: typeof fs.existsSync;
      lstatSync: typeof fs.lstatSync;
      readFileSync: typeof fs.readFileSync;
    } = fs,
  ) {}

  tokenPath(platform = this.platform, home = this.home): string {
    if (platform === 'darwin') {
      return path.join(home, 'Library', 'Application Support', 'vibey', 'hub', 'token');
    }
    if (platform === 'linux') {
      const state = this.env.XDG_STATE_HOME || path.join(home, '.local', 'state');
      return path.join(state, 'vibey', 'hub', 'token');
    }
    const appData = this.env.APPDATA || path.join(home, 'AppData', 'Roaming');
    return path.join(appData, 'vibey', 'hub', 'token');
  }

  readToken(customPath?: string): string | undefined {
    const filePath = customPath ?? this.tokenPath();
    try {
      if (!this.filesystem.existsSync(filePath)) {
        if (this.platform === 'linux' && !customPath) {
          const altPath = path.join(this.home, '.local', 'share', 'vibey', 'hub', 'token');
          if (this.filesystem.existsSync(altPath)) {
            return this.readToken(altPath);
          }
        }
        return undefined;
      }
      const stat = this.filesystem.lstatSync(filePath);
      if (stat.isSymbolicLink() || !stat.isFile()) {
        return undefined;
      }
      if (this.platform !== 'win32' && (stat.mode & 0o077) !== 0) {
        return undefined;
      }
      const token = this.filesystem.readFileSync(filePath, 'utf8').trim();
      return token.length > 0 ? token : undefined;
    } catch {
      return undefined;
    }
  }
}
