// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { PlatformStorageInterface } from '../../src/core/interfaces/storage-interface';
import {
  DurabilityGate,
  LinuxStorage,
  MacStorage,
  PlatformStorage,
  ResolvedPath,
  StormHome,
  VolatileLocations,
  VolatileStorageError,
} from '../../src/core/storage';
import { scratch } from './helpers';

/** A platform whose volatile places are the test's own directories. */
function platform(fixed: [string, string][]): PlatformStorageInterface {
  return {
    name: 'test',
    defaultHome: () => '/nowhere',
    fixedVolatile: () => fixed,
    sessionVolatile: () => [
      ['TMPDIR', 'the session temporary directory'],
      ['XDG_RUNTIME_DIR', 'the runtime directory'],
    ],
    qwenloopConfigPath: () => '/nowhere/config.toml',
  };
}

describe('PlatformStorage', () => {
  it('knows macOS and Linux, and refuses Windows rather than guess (#1097)', () => {
    expect(PlatformStorage.detect('darwin')).toBeInstanceOf(MacStorage);
    expect(PlatformStorage.detect('linux')).toBeInstanceOf(LinuxStorage);
    expect(PlatformStorage.detect('freebsd')).toBeInstanceOf(LinuxStorage);
    expect(() => PlatformStorage.detect('win32')).toThrow('Windows is not supported yet (#1097)');
  });

  it('puts the storm home and qwenloop config where each platform keeps them', () => {
    const mac = new MacStorage();
    expect(mac.defaultHome({ HOME: '/Users/me' })).toBe('/Users/me/git/vibey-storm');
    expect(mac.qwenloopConfigPath({ HOME: '/Users/me' })).toBe('/Users/me/Library/Application Support/qwenloop/config.toml');
    expect(mac.defaultHome({})).toBe(path.join(os.homedir(), 'git', 'vibey-storm'));
    expect(mac.fixedVolatile().map(([place]) => place)).toContain('/private/var/folders');
    const linux = new LinuxStorage();
    expect(linux.defaultHome({ HOME: '/home/me' })).toBe('/home/me/.local/share/vibey/storm');
    expect(linux.defaultHome({ HOME: '/home/me', XDG_DATA_HOME: '/data' })).toBe('/data/vibey/storm');
    expect(linux.defaultHome({ HOME: '/home/me', XDG_DATA_HOME: 'relative' })).toBe('/home/me/.local/share/vibey/storm');
    expect(linux.qwenloopConfigPath({ HOME: '/home/me' })).toBe('/home/me/.config/qwenloop/config.toml');
    expect(linux.qwenloopConfigPath({ HOME: '/home/me', XDG_CONFIG_HOME: '/cfg' })).toBe('/cfg/qwenloop/config.toml');
    expect(linux.sessionVolatile().map(([name]) => name)).toEqual(['TMPDIR', 'XDG_RUNTIME_DIR']);
    expect(linux.fixedVolatile().map(([place]) => place)).toContain('/dev/shm');
  });
});

describe('ResolvedPath', () => {
  it('resolves through symlinks as far as the path exists, and keeps the rest as written', () => {
    const root = scratch();
    fs.mkdirSync(path.join(root, 'real'));
    fs.symlinkSync(path.join(root, 'real'), path.join(root, 'link'));
    expect(ResolvedPath.of(path.join(root, 'link', 'not', 'yet'))).toBe(path.join(root, 'real', 'not', 'yet'));
    expect(ResolvedPath.of('~', root)).toBe(root);
    expect(ResolvedPath.of('~/real', root)).toBe(path.join(root, 'real'));
    expect(ResolvedPath.of('~')).toBe(fs.realpathSync(os.homedir()));
  });

  it('knows what is inside what, even beside a name that starts with two dots', () => {
    expect(ResolvedPath.within('/a/b', '/a')).toBe(true);
    expect(ResolvedPath.within('/a', '/a')).toBe(true);
    expect(ResolvedPath.within('/a', '/a/b')).toBe(false);
    expect(ResolvedPath.within('/b', '/a')).toBe(false);
    expect(ResolvedPath.within('/a/..hidden', '/a')).toBe(true);
  });
});

describe('VolatileLocations', () => {
  it('lists fixed and session locations once, longest first, skipping a root or home TMPDIR', () => {
    const root = scratch();
    const tmp = path.join(root, 'tmp');
    fs.mkdirSync(tmp);
    const locations = new VolatileLocations({ HOME: path.join(root, 'home'), TMPDIR: tmp, XDG_RUNTIME_DIR: '' }, platform([
      [tmp, 'emptied'],
      [tmp, 'emptied again'],
      ['/dev/shm/x', 'memory'],
    ]));
    expect(locations.roots()).toEqual([
      [tmp, 'emptied'],
      ['/dev/shm/x', 'memory'],
    ].sort((left, right) => right[0].length - left[0].length) as [string, string][]);
    expect(locations.containing(path.join(tmp, 'work'))).toEqual([tmp, 'emptied']);
    expect(locations.containing(path.join(root, 'durable'))).toBeUndefined();
    const rootTmp = new VolatileLocations({ HOME: '/home/me', TMPDIR: '/' }, platform([]));
    expect(rootTmp.roots()).toEqual([]);
    const homeTmp = new VolatileLocations({ HOME: path.join(root, 'home'), TMPDIR: root }, platform([]));
    expect(homeTmp.roots()).toEqual([]);
    const session = new VolatileLocations({ HOME: '/home/me', XDG_RUNTIME_DIR: path.join(root, 'run') }, platform([]));
    expect(session.roots()).toEqual([[path.join(root, 'run'), 'the runtime directory']]);
    expect(new VolatileLocations({}, platform([])).roots()).toEqual([]);
  });
});

describe('StormHome', () => {
  it('takes the setting, then VIBEY_STORM_HOME, then the platform default', () => {
    const storage = new MacStorage();
    expect(new StormHome(' /mine ', { VIBEY_STORM_HOME: '/env' }, storage).resolve()).toEqual({ path: '/mine', source: 'the vibey.stormHome setting' });
    expect(new StormHome('', { VIBEY_STORM_HOME: '/env/../env2' }, storage).resolve()).toEqual({ path: '/env2', source: 'VIBEY_STORM_HOME' });
    expect(new StormHome('', { HOME: '/Users/me' }, storage).resolve()).toEqual({ path: '/Users/me/git/vibey-storm', source: 'the macos default' });
    expect(new StormHome('~/storm', { HOME: '/Users/me' }, storage).resolve().path).toBe('/Users/me/storm');
    expect(new StormHome('~', { HOME: '/Users/me' }, storage).resolve().path).toBe('/Users/me');
    expect(new StormHome('', { VIBEY_STORM_HOME: '~/s' }, storage).resolve().path).toBe(path.join(os.homedir(), 's'));
  });

  it('refuses a relative home: relative to what?', () => {
    expect(() => new StormHome('storm', {}, new MacStorage()).resolve()).toThrow('must be an absolute path');
  });
});

describe('DurabilityGate', () => {
  it('passes durable paths and refuses volatile ones, naming the place and why', () => {
    const root = scratch();
    const volatile = path.join(root, 'volatile');
    fs.mkdirSync(volatile);
    fs.symlinkSync(volatile, path.join(root, 'alias'));
    const gate = new DurabilityGate(new VolatileLocations({ HOME: '/home/me' }, platform([[volatile, 'emptied at boot']])));
    expect(gate.inspect({ home: path.join(root, 'durable') })).toEqual([]);
    expect(() => gate.enforce({ home: path.join(root, 'durable') })).not.toThrow();
    const hits = gate.inspect({ direct: path.join(volatile, 'w'), aliased: path.join(root, 'alias', 'w') });
    expect(hits.map((hit) => [hit.name, hit.location, hit.why])).toEqual([
      ['direct', volatile, 'emptied at boot'],
      ['aliased', volatile, 'emptied at boot'],
    ]);
    let error: VolatileStorageError | undefined;
    try {
      gate.enforce({ direct: path.join(volatile, 'w'), aliased: path.join(root, 'alias', 'w') });
    } catch (caught) {
      error = caught as VolatileStorageError;
    }
    expect(error).toBeInstanceOf(VolatileStorageError);
    expect(error?.hits).toHaveLength(2);
    expect(error?.message).toContain(`direct: ${path.join(volatile, 'w')}\n`);
    expect(error?.message).toContain(`aliased: ${path.join(root, 'alias', 'w')} -> ${path.join(volatile, 'w')}`);
    expect(error?.message).toContain('Sub-doctrine 10.h; ADR-0057.');
    expect(VolatileStorageError.EXIT_CODE).toBe(78);
  });
});
