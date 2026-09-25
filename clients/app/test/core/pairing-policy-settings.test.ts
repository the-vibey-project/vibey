// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { DevicePolicy } from '../../src/core/device-policy';
import { AppIdentities } from '../../src/core/identity';
import { Pairing, PairingExchange } from '../../src/core/pairing';
import { Screens } from '../../src/core/screens';
import { SettingsModel } from '../../src/core/settings';

const FP = `sha256:${'AB'.repeat(32)}`;

describe('Pairing', () => {
  const pairing = new Pairing();

  it('reads a full offer from the QR code', () => {
    const parsed = pairing.parseQr(`krypton://pair?host=mac.local&port=8765&fp=${FP}&code=123-456&name=Studio`);
    expect(parsed).toEqual({
      ok: true,
      offer: { host: 'mac.local', port: 8765, scheme: 'https', fingerprint: FP.toLowerCase(), code: '123456', name: 'Studio' },
    });
    if (parsed.ok) {
      expect(pairing.baseUrl(parsed.offer)).toBe('https://mac.local:8765');
    }
  });

  it('accepts the nightly scheme, plain http on loopback, and brackets IPv6', () => {
    const parsed = pairing.parseQr('krypton-nightly:pair?host=127.0.0.1&port=8765&code=000111');
    expect(parsed).toMatchObject({ ok: true, offer: { scheme: 'http', fingerprint: null, name: null } });
    const six = pairing.parseQr(`krypton://pair?host=fe80::1&port=1&code=111111&fp=${FP}`);
    expect(six.ok && pairing.baseUrl(six.offer)).toBe('https://[fe80::1]:1');
    const bracketed = pairing.parseQr(`krypton://pair?host=[::1]&port=2&code=111111&fp=${FP}`);
    expect(bracketed.ok && pairing.baseUrl(bracketed.offer)).toBe('https://[::1]:2');
  });

  it.each([
    ['not a url', 'not a Krypton pairing code'],
    ['https://evil.example/pair?host=a&port=1&code=111111', 'not a Krypton pairing code'],
    ['krypton://elsewhere?host=a&port=1&code=111111', 'not a Krypton pairing code'],
    ['krypton://pair?port=1&code=111111', 'names no host'],
    ['krypton://pair?host=a/b&port=1&code=111111', 'names no host'],
    ['krypton://pair?host=a&code=111111', 'no valid port'],
    ['krypton://pair?host=a&port=70000&code=111111', 'no valid port'],
    ['krypton://pair?host=a&port=1&code=12', '6 digits'],
    ['krypton://pair?host=a&port=1', '6 digits'],
    ['krypton://pair?host=a&port=1&code=111111', 'no certificate fingerprint'],
    ['krypton://pair?host=a&port=1&code=111111&fp=md5:00', 'malformed'],
  ])('refuses %s', (text, reason) => {
    const parsed = pairing.parseQr(text);
    expect(parsed.ok).toBe(false);
    expect(!parsed.ok && parsed.reason).toMatch(reason);
  });

  it('normalises a typed code', () => {
    expect(pairing.normaliseCode(' 123 456 ')).toBe('123456');
    expect(pairing.normaliseCode('12345a')).toEqual({ error: 'The code is the 6 digits the host shows.' });
  });

  it('refuses the exchange plainly until the hub offers it', async () => {
    const parsed = pairing.parseQr('krypton://pair?host=localhost&port=1&code=111111');
    if (!parsed.ok) throw new Error('fixture');
    await expect(new PairingExchange().exchange(parsed.offer)).rejects.toThrow(/cannot pair devices yet/);
  });
});

describe('DevicePolicy', () => {
  const policy = new DevicePolicy();

  it.each(['declare-paid-use', 'ultra-no-cap', 'set-cap', 'clear-cap', 'change-dsn', 'run-migrations', 'touch-canon'] as const)(
    'never lets a device %s',
    (action) => {
      const decision = policy.decide(action);
      expect(decision.allowed).toBe(false);
      expect(!decision.allowed && decision.reason).toMatch(/never|only by the operator/);
    },
  );

  it('re-verifies spending, and nothing else', () => {
    expect(policy.decide('answer-spend')).toEqual({ allowed: true, confirm: true });
    expect(policy.decide('answer')).toEqual({ allowed: true, confirm: false });
    expect(policy.decide('view')).toEqual({ allowed: true, confirm: false });
  });

  it('offers ULTRA only under a declared cap', () => {
    const open = policy.effortOptions(false);
    expect(open.map((option) => option.effort)).toEqual(['TRIVIAL', 'LOW', 'STANDARD', 'HIGH', 'MAX', 'ULTRA']);
    expect(open.find((option) => option.effort === 'ULTRA')).toMatchObject({ selectable: false });
    expect(open.filter((option) => option.selectable)).toHaveLength(5);
    expect(policy.effortOptions(true).every((option) => option.selectable)).toBe(true);
  });
});

describe('SettingsModel', () => {
  const model = new SettingsModel();

  it('defaults to the System theme, sounds on and every notification on', () => {
    expect(model.defaults.theme).toBe('system');
    expect(Object.values(model.defaults.notifications).every(Boolean)).toBe(true);
    expect(Object.keys(SettingsModel.LABELS)).toEqual([...SettingsModel.CLASSES]);
  });

  it('applies every change, clamping the volume', () => {
    let settings = model.apply(model.defaults, { type: 'theme', theme: 'dark' });
    settings = model.apply(settings, { type: 'sounds', on: false });
    settings = model.apply(settings, { type: 'volume', volume: 3 });
    settings = model.apply(settings, { type: 'notification', which: 'budget', on: false });
    expect(settings).toMatchObject({ theme: 'dark', sounds: false, volume: 1, notifications: { budget: false, gate: true } });
    expect(model.apply(settings, { type: 'volume', volume: Number.NaN }).volume).toBe(0);
    expect(model.apply(settings, { type: 'volume', volume: -1 }).volume).toBe(0);
    expect(model.apply(settings, { type: 'reset' })).toEqual(model.defaults);
  });

  it('round-trips, and falls back field by field on anything unreadable', () => {
    const custom = model.apply(model.defaults, { type: 'theme', theme: 'light' });
    expect(model.load(model.save(custom))).toEqual(custom);
    expect(model.load(null)).toEqual(model.defaults);
    expect(model.load('{')).toEqual(model.defaults);
    expect(model.load('7')).toEqual(model.defaults);
    expect(model.load('{"theme":"neon","sounds":"yes","volume":0.2,"notifications":{"gate":false,"failed":"no"}}')).toEqual({
      ...model.defaults,
      volume: 0.2,
      notifications: { ...model.defaults.notifications, gate: false },
    });
  });
});

describe('AppIdentities', () => {
  const identities = new AppIdentities();

  it('is stable unless nightly is asked for by name', () => {
    expect(identities.channel(undefined)).toBe('stable');
    expect(identities.channel('beta')).toBe('stable');
    expect(identities.channel(' Nightly ')).toBe('nightly');
  });

  it('gives the two channels different names, identifiers and schemes', () => {
    const stable = identities.identity('stable');
    const nightly = identities.identity('nightly');
    expect(stable.name).toBe('Krypton');
    expect(nightly.name).toBe('Krypton Nightly');
    for (const key of ['slug', 'scheme', 'iosBundleIdentifier', 'androidPackage', 'updateChannel'] as const) {
      expect(stable[key]).not.toBe(nightly[key]);
    }
    expect(Pairing.SCHEMES).toEqual([`${stable.scheme}:`, `${nightly.scheme}:`]);
  });
});

describe('Screens', () => {
  it('carries every row of the parity matrix', () => {
    const screens = new Screens();
    expect(screens.missing()).toEqual([]);
    expect(screens.tabs.map((screen) => screen.title)).toEqual(['Home', 'Gates', 'Lanes', 'Loops & Effort', 'Settings']);
  });

  it('notices a missing feature', () => {
    const screens = new Screens();
    Object.defineProperty(screens, 'all', { value: [] });
    expect(screens.missing()).toEqual(Screens.FEATURES);
  });
});

describe('app.config.ts', () => {
  it('chooses the same identity AppIdentities does, stable by default', () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { identityFor } = require('../../app.config') as { identityFor: (variant?: string) => { name: string } };
    const identities = new AppIdentities();
    for (const variant of [undefined, 'nightly', 'stable', 'other']) {
      expect(identityFor(variant)).toEqual(identities.identity(identities.channel(variant)));
    }
  });
});
