// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { LocalHubToken } from '../../src/core/local-token';
import { scratch } from './helpers';

describe('LocalHubToken', () => {
  it('resolves the expected token paths across platforms and env variations', () => {
    const defaultToken = new LocalHubToken();
    expect(defaultToken.tokenPath('darwin', '/Users/me')).toBe(
      path.join('/Users/me', 'Library', 'Application Support', 'vibey', 'hub', 'token'),
    );

    const linuxWithXdg = new LocalHubToken('linux', '/home/me', { XDG_STATE_HOME: '/custom/state' });
    expect(linuxWithXdg.tokenPath()).toBe(path.join('/custom/state', 'vibey', 'hub', 'token'));

    const linuxWithoutXdg = new LocalHubToken('linux', '/home/me', {});
    expect(linuxWithoutXdg.tokenPath()).toBe(path.join('/home/me', '.local', 'state', 'vibey', 'hub', 'token'));

    const winWithAppData = new LocalHubToken('win32', 'C:\\Users\\me', { APPDATA: 'C:\\AppData\\Roaming' });
    expect(winWithAppData.tokenPath()).toBe(path.join('C:\\AppData\\Roaming', 'vibey', 'hub', 'token'));

    const winWithoutAppData = new LocalHubToken('win32', 'C:\\Users\\me', {});
    expect(winWithoutAppData.tokenPath()).toBe(path.join('C:\\Users\\me', 'AppData', 'Roaming', 'vibey', 'hub', 'token'));
  });

  it('reads a valid 0600 token file and trims whitespace', () => {
    const dir = scratch();
    const tokenFile = path.join(dir, 'token');
    fs.writeFileSync(tokenFile, '  secret-hub-token-1234  \n', { mode: 0o600 });

    const token = new LocalHubToken();
    const result = token.readToken(tokenFile);
    expect(result).toBe('secret-hub-token-1234');
  });

  it('reads default token path when customPath is omitted', () => {
    const dir = scratch();
    const tokenFile = path.join(dir, 'Library', 'Application Support', 'vibey', 'hub', 'token');
    fs.mkdirSync(path.dirname(tokenFile), { recursive: true });
    fs.writeFileSync(tokenFile, 'default-darwin-token\n', { mode: 0o600 });

    const token = new LocalHubToken('darwin', dir);
    expect(token.readToken()).toBe('default-darwin-token');
  });

  it('falls back to .local/share on linux when primary path is missing', () => {
    const dir = scratch();
    const fallbackFile = path.join(dir, '.local', 'share', 'vibey', 'hub', 'token');
    fs.mkdirSync(path.dirname(fallbackFile), { recursive: true });
    fs.writeFileSync(fallbackFile, 'linux-alt-token\n', { mode: 0o600 });

    const token = new LocalHubToken('linux', dir, {});
    expect(token.readToken()).toBe('linux-alt-token');
  });

  it('returns undefined if file does not exist on linux without fallback', () => {
    const dir = scratch();
    const token = new LocalHubToken('linux', dir, {});
    expect(token.readToken()).toBeUndefined();
  });

  it('returns undefined if customPath does not exist', () => {
    const token = new LocalHubToken();
    expect(token.readToken('/does/not/exist/token')).toBeUndefined();
  });

  it('refuses symbolic links', () => {
    const dir = scratch();
    const realFile = path.join(dir, 'real-token');
    const symlinkFile = path.join(dir, 'symlink-token');
    fs.writeFileSync(realFile, 'real-token-secret\n', { mode: 0o600 });
    fs.symlinkSync(realFile, symlinkFile);

    const token = new LocalHubToken();
    expect(token.readToken(symlinkFile)).toBeUndefined();
  });

  it('refuses directories', () => {
    const dir = scratch();
    const tokenDir = path.join(dir, 'token-dir');
    fs.mkdirSync(tokenDir);

    const token = new LocalHubToken();
    expect(token.readToken(tokenDir)).toBeUndefined();
  });

  it('refuses files with group or other permissions on non-windows platforms', () => {
    const dir = scratch();
    const tokenFile = path.join(dir, 'token');
    fs.writeFileSync(tokenFile, 'insecure-token\n', { mode: 0o644 });

    const token = new LocalHubToken('darwin', dir);
    expect(token.readToken(tokenFile)).toBeUndefined();
  });

  it('permits non-0600 modes on win32', () => {
    const dir = scratch();
    const tokenFile = path.join(dir, 'token');
    fs.writeFileSync(tokenFile, 'windows-token-value\n', { mode: 0o644 });

    const token = new LocalHubToken('win32', dir);
    expect(token.readToken(tokenFile)).toBe('windows-token-value');
  });

  it('returns undefined when the token file is empty or whitespace only', () => {
    const dir = scratch();
    const tokenFile = path.join(dir, 'token');
    fs.writeFileSync(tokenFile, '   \n  \t  \n', { mode: 0o600 });

    const token = new LocalHubToken();
    expect(token.readToken(tokenFile)).toBeUndefined();
  });

  it('returns undefined when filesystem throws an error', () => {
    const fakeFs = {
      ...fs,
      existsSync: () => true,
      lstatSync: () => ({ isSymbolicLink: () => false, isFile: () => true, mode: 0o600 }) as unknown as fs.Stats,
      readFileSync: () => {
        throw new Error('EACCES: permission denied');
      },
    };

    const token = new LocalHubToken('darwin', '/Users/me', {}, fakeFs as unknown as typeof fs);
    expect(token.readToken('/some/path')).toBeUndefined();
  });
});
