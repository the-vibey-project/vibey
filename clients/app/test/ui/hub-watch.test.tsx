// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** #1186: a phone whose hub is not running says so, shows what to run, and reconnects by itself. */
import { act, fireEvent, render, screen } from '@testing-library/react-native';
import * as Clipboard from 'expo-clipboard';
import type { ReactNode } from 'react';
import { AppState } from 'react-native';
import { DoctorScreen } from '../../src/screens/doctor';
import { HomeScreen } from '../../src/screens/home';
import { AppStateProvider, MemoryStore } from '../../src/ui/app-state';

jest.mock('expo-router', () => ({
  Link: ({ children }: { children: ReactNode }) => children,
  router: { replace: jest.fn(), push: jest.fn() },
}));
jest.mock('expo-clipboard', () => ({ setStringAsync: jest.fn(async () => true) }));

interface Hub {
  up: boolean;
  requests: { method: string; path: string }[];
}

function fakeHub(): { hub: Hub; fetchLike: typeof fetch } {
  const hub: Hub = { up: false, requests: [] };
  const fetchLike = (async (url: string, init: { method: string }) => {
    const path = url.replace('http://studio.local:8765', '');
    hub.requests.push({ method: init.method, path });
    if (!hub.up) throw new TypeError('Network request failed');
    const body = path.startsWith('/api/v1/projects') ? [{ project_id: 'p1', name: 'Greeter', phase: 'BUILD', open_gates: 0, cycle: 1, max_cycles: 3 }] : {};
    return { status: 200, text: async () => JSON.stringify(body) };
  }) as unknown as typeof fetch;
  return { hub, fetchLike };
}

async function renderHome(fetchLike: typeof fetch, node: ReactNode = <HomeScreen />) {
  await render(
    <AppStateProvider store={new MemoryStore()} fetchLike={fetchLike} initial={{ connection: { baseUrl: 'http://studio.local:8765', token: 't' } }}>
      {node}
    </AppStateProvider>,
  );
}

const advance = (ms: number) => act(async () => void (await jest.advanceTimersByTimeAsync(ms)));

describe('a phone whose hub is not running', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it('says so, shows the command to run on that computer, and copies it', async () => {
    const { hub, fetchLike } = fakeHub();
    await renderHome(fetchLike);
    expect(await screen.findByText('The hub on your computer is not running')).toBeTruthy();
    expect(screen.getByText(/studio\.local:8765, and nothing answers there/)).toBeTruthy();
    expect(screen.getByText('On that computer, run:  vibey hub start')).toBeTruthy();
    expect(screen.getByText(/Closing a krypton app, on any device, never stops the hub/)).toBeTruthy();
    expect(screen.getByText(/asks again by itself/)).toBeTruthy();

    await fireEvent.press(screen.getByText('Copy the command'));
    await advance(0);
    expect(Clipboard.setStringAsync).toHaveBeenCalledWith('vibey hub start');
    expect(screen.getByText('Copied.')).toBeTruthy();

    // The hub is not reachable, and says so where the phone shows its status.
    expect(screen.getByText('Not reachable')).toBeTruthy();
    // Nothing was sent to the hub but reads.
    expect(hub.requests.every((request) => request.method === 'GET')).toBe(true);
  });

  it('says so when the clipboard refuses, rather than claiming it copied', async () => {
    (Clipboard.setStringAsync as jest.Mock).mockRejectedValueOnce(new Error('denied'));
    const { fetchLike } = fakeHub();
    await renderHome(fetchLike);
    await fireEvent.press(await screen.findByText('Copy the command'));
    await advance(0);
    expect(screen.queryByText('Copied.')).toBeNull();
  });

  it('reconnects by itself when the hub answers, with no one touching the screen', async () => {
    const { hub, fetchLike } = fakeHub();
    await renderHome(fetchLike);
    expect(await screen.findByTestId('hub-unreachable')).toBeTruthy();
    expect(screen.queryByText('Greeter')).toBeNull();

    // The host runs `vibey hub start`. The phone's next question is answered.
    hub.up = true;
    await advance(2_000);
    await advance(0);
    expect(await screen.findByText('Greeter')).toBeTruthy();
    expect(screen.queryByTestId('hub-unreachable')).toBeNull();
    expect(screen.getByText('Reachable')).toBeTruthy();
    expect(screen.getByText(/studio\.local:8765 · since just now/)).toBeTruthy();
  });

  it('asks more and more slowly while the hub is down, then not at all in the background', async () => {
    const { hub, fetchLike } = fakeHub();
    let onChange: (state: string) => void = () => undefined;
    const subscription = { remove: jest.fn() };
    jest.spyOn(AppState, 'addEventListener').mockImplementation((_type, listener) => {
      onChange = listener as (state: string) => void;
      return subscription as never;
    });
    await renderHome(fetchLike, <DoctorScreen />);
    const probes = () => hub.requests.filter((request) => request.path === '/health/live').length;
    await advance(0);
    expect(probes()).toBe(1);
    await advance(2_000);
    expect(probes()).toBe(2);
    await advance(3_999); // the next wait is 4 s, not 2
    expect(probes()).toBe(2);
    await advance(1);
    expect(probes()).toBe(3);

    await act(async () => onChange('background'));
    await advance(10 * 60_000);
    expect(probes()).toBe(3);

    await act(async () => onChange('active'));
    await advance(0);
    expect(probes()).toBe(4);
  });

  it('shows the status where Doctor is looked at, and lets go of the foreground listener on unmount', async () => {
    const { hub, fetchLike } = fakeHub();
    hub.up = true;
    const subscription = { remove: jest.fn() };
    jest.spyOn(AppState, 'addEventListener').mockReturnValue(subscription as never);
    await renderHome(fetchLike, <DoctorScreen />);
    await advance(0);
    expect(screen.getByText('The hub on your computer')).toBeTruthy();
    expect(screen.getByText('Reachable')).toBeTruthy();
    await screen.unmount();
    expect(subscription.remove).toHaveBeenCalled();
  });

  it('shows nothing about a hub before one is paired', async () => {
    await render(
      <AppStateProvider store={new MemoryStore()} fetchLike={fakeHub().fetchLike} initial={{}}>
        <HomeScreen />
      </AppStateProvider>,
    );
    expect(screen.queryByTestId('hub-status')).toBeNull();
  });
});
