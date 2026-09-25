// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';
import { BudgetsScreen } from '../../src/screens/budgets';
import { DoctorScreen } from '../../src/screens/doctor';
import { EffortScreen } from '../../src/screens/effort';
import { GatesScreen } from '../../src/screens/gates';
import { HomeScreen } from '../../src/screens/home';
import { LanesScreen } from '../../src/screens/lanes';
import { PairScreen } from '../../src/screens/pair';
import { SettingsScreen } from '../../src/screens/settings';
import { AppStateProvider, MemoryStore } from '../../src/ui/app-state';

jest.mock('expo-router', () => ({
  Link: ({ children }: { children: ReactNode }) => children,
  router: { replace: jest.fn() },
}));
jest.mock('expo-camera', () => ({ CameraView: () => null, useCameraPermissions: () => [{ granted: false }, jest.fn()] }));
jest.mock('expo-local-authentication', () => ({ authenticateAsync: jest.fn(async () => ({ success: true })) }));

type Routes = Record<string, unknown>;

function hub(routes: Routes) {
  const posted: { url: string; body: string }[] = [];
  const fetchLike = (async (url: string, init: { method: string; body?: string }) => {
    const path = url.replace('http://hub:8765', '');
    if (init.method === 'POST') posted.push({ url: path, body: init.body ?? '' });
    const body = routes[`${init.method} ${path}`];
    return { status: body === undefined ? 404 : 200, text: async () => JSON.stringify(body ?? {}) };
  }) as unknown as typeof fetch;
  return { fetchLike, posted };
}

async function renderWith(node: ReactNode, routes: Routes, connected = true) {
  const { fetchLike, posted } = hub(routes);
  await render(
    <AppStateProvider
      store={new MemoryStore()}
      fetchLike={fetchLike}
      initial={connected ? { connection: { baseUrl: 'http://hub:8765', token: 't' } } : {}}
    >
      {node}
    </AppStateProvider>,
  );
  return posted;
}

const project = { project_id: 'p1', name: 'Greeter', phase: 'BUILD', open_gates: 1, cycle: 1, max_cycles: 3 };

describe('screens', () => {
  it('Home shows each project and what needs you', async () => {
    await renderWith(<HomeScreen />, { 'GET /api/v1/projects': [project] });
    expect(await screen.findByText('1 gate needs you')).toBeTruthy();
    expect(screen.getByText('Greeter')).toBeTruthy();
    expect(screen.getByText('Cycle 1 of 3')).toBeTruthy();
    expect(screen.getByLabelText('Krypton')).toBeTruthy();
  });

  it('Gates answers a review with a verdict, and re-verifies a gate that spends', async () => {
    const verify = jest.fn(async () => false);
    const posted = await renderWith(<GatesScreen verify={verify} />, {
      'GET /api/v1/gates': {
        gates: [
          { gate_id: 'g1', project_id: 'p1', job_id: null, kind: 'review_collect', prompt: 'Ship it?', options: ['accept'], default_answer: null, timeout_at: null },
          { gate_id: 'g2', project_id: 'p1', job_id: null, kind: 'budget_exhausted', prompt: 'More?', options: ['grant'], default_answer: null, timeout_at: null },
        ],
      },
      'POST /api/v1/gates/g1/answer': { replayed: false },
    });
    await fireEvent.press(await screen.findByText('accept'));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(JSON.parse(posted[0]!.body).answer).toEqual({ verdict: 'accept' });
    await fireEvent.press(screen.getByText('grant'));
    await waitFor(() => expect(verify).toHaveBeenCalled());
    expect(await screen.findByText('Not confirmed; nothing was sent.')).toBeTruthy();
    expect(posted).toHaveLength(1);
  });

  it('Lanes shows what each lane has written', async () => {
    await renderWith(<LanesScreen />, {
      'GET /api/v1/lanes': { lanes: [{ id: 'a', engine: 'e', label: 'repo · gptossloop', state: 'running', outcome: null, offset: 2048, last_event_at: Date.now() / 1000 }] },
    });
    expect(await screen.findByText('repo · gptossloop')).toBeTruthy();
    expect(screen.getByText('2.0 KB written · just now')).toBeTruthy();
  });

  it('Loops & Effort never lets a phone choose ULTRA without a cap', async () => {
    await renderWith(<EffortScreen />, {
      'GET /api/v1/loops': {
        efforts: ['TRIVIAL', 'LOW', 'STANDARD', 'HIGH', 'MAX', 'ULTRA'],
        default_loop: 'sovereignloop',
        paid_default_engine: 'claudeloop',
        ladder: { phase_base: {}, build_attempts: [], exhausted_after: 3, rotates_when_effort_rises: true },
        loops: [{ loop: 'sovereignloop', tier: 'local', default: true, declared_only: false, engines: [], by_effort: {} }],
      },
      'GET /api/v1/projects': [],
    });
    expect(await screen.findByText(/Needs a cap declared on the host first/)).toBeTruthy();
    const ultra = screen.getByText('ULTRA');
    await fireEvent.press(ultra);
    expect(screen.queryByText('✓ ULTRA')).toBeNull();
    await fireEvent.press(screen.getByText('HIGH'));
    expect(screen.getByText('✓ HIGH')).toBeTruthy();
  });

  it('Budgets reads spend and says caps are the host’s', async () => {
    await renderWith(<BudgetsScreen />, {
      'GET /api/v1/projects': [project],
      'GET /api/v1/projects/p1/budget': { caps: { max_cycle_dollars: 10, max_cycle_turns: null }, spend: { dollars: 4, turns: 2 }, exhausted: false, history: [] },
    });
    expect(await screen.findByText('$4.00 of $10.00')).toBeTruthy();
    expect(screen.getByText(/never from a device/)).toBeTruthy();
  });

  it('Doctor shows each check', async () => {
    await renderWith(<DoctorScreen />, { 'GET /api/v1/doctor': { scope: 'hub', checks: [{ name: 'database', mark: 'PASS', detail: 'the database answers' }] } });
    expect(await screen.findByText('the database answers')).toBeTruthy();
  });

  it('Settings switches theme and notifications', async () => {
    await renderWith(<SettingsScreen />, {});
    await fireEvent.press(screen.getByText('Dark'));
    await fireEvent(screen.getByLabelText('A gate needs you'), 'valueChange', false);
    expect(screen.getByLabelText('A gate needs you').props.value).toBe(false);
    expect(screen.getByText(/Channel: Krypton/)).toBeTruthy();
  });

  it('Pairing says plainly that codes wait for the hub, and a host token connects', async () => {
    await renderWith(<PairScreen />, { 'GET /api/v1/projects': [] }, false);
    await fireEvent.changeText(screen.getByLabelText('Pairing code'), '12');
    await fireEvent.press(screen.getByText('Pair'));
    expect(await screen.findByText('The code is the 6 digits the host shows.')).toBeTruthy();
    await fireEvent.changeText(screen.getByLabelText('Pairing code'), '123 456');
    await fireEvent.press(screen.getByText('Pair'));
    expect(await screen.findByText(/cannot pair devices yet/)).toBeTruthy();
    await fireEvent.changeText(screen.getByLabelText('Hub address'), 'http://hub:8765');
    await fireEvent.changeText(screen.getByLabelText('Host token'), 'secret');
    await fireEvent.press(screen.getByText('Connect'));
    const { router } = jest.requireMock('expo-router') as { router: { replace: jest.Mock } };
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith('/'));
  });

  it('says when no hub is connected', async () => {
    await renderWith(<HomeScreen />, {}, false);
    expect(await screen.findByText('Not connected to a hub yet.')).toBeTruthy();
  });
});
