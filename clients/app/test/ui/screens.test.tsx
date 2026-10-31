// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import * as Notifications from 'expo-notifications';
import type { ReactNode } from 'react';
import { Linking } from 'react-native';
import { WorkflowRuns } from '../../src/core/workflow-runs';
import { BudgetsScreen } from '../../src/screens/budgets';
import { DoctorScreen } from '../../src/screens/doctor';
import { EffortScreen } from '../../src/screens/effort';
import { GatesScreen } from '../../src/screens/gates';
import { HomeScreen } from '../../src/screens/home';
import { LanesScreen } from '../../src/screens/lanes';
import { PairScreen } from '../../src/screens/pair';
import { SettingsScreen } from '../../src/screens/settings';
import { StartScreen } from '../../src/screens/start';
import { WorkflowsScreen } from '../../src/screens/workflows';
import { AppStateProvider, MemoryStore } from '../../src/ui/app-state';
import { GateNotifications, NOTIFICATION_POLL_MS } from '../../src/ui/notifications';

jest.mock('expo-router', () => ({
  Link: ({ children }: { children: ReactNode }) => children,
  router: { replace: jest.fn(), push: jest.fn() },
}));
jest.mock('expo-notifications', () => ({
  setNotificationHandler: jest.fn(),
  addNotificationResponseReceivedListener: jest.fn(() => ({ remove: jest.fn() })),
  getPermissionsAsync: jest.fn(async () => ({ granted: true, canAskAgain: true })),
  requestPermissionsAsync: jest.fn(async () => ({ granted: true })),
  scheduleNotificationAsync: jest.fn(async () => 'id'),
  setNotificationCategoryAsync: jest.fn(async () => ({})),
  DEFAULT_ACTION_IDENTIFIER: 'expo.modules.notifications.actions.DEFAULT',
}));
jest.mock('expo-camera', () => ({ CameraView: () => null, useCameraPermissions: () => [{ granted: false }, jest.fn()] }));
jest.mock('expo-local-authentication', () => ({ authenticateAsync: jest.fn(async () => ({ success: true })) }));

type Routes = Record<string, unknown>;

function hub(routes: Routes) {
  const posted: { url: string; body: string }[] = [];
  const fetchLike = (async (url: string, init: { method: string; body?: string }) => {
    const path = url.replace('http://hub:8765', '');
    if (init.method === 'POST') posted.push({ url: path, body: init.body ?? '' });
    const route = routes[`${init.method} ${path}`];
    const found = typeof route === 'function' ? (route as () => unknown)() : route;
    const withStatus = typeof found === 'object' && found !== null && '__status' in found ? (found as { __status: number; body: unknown }) : undefined;
    const body = withStatus === undefined ? found : withStatus.body;
    return { status: withStatus?.__status ?? (body === undefined ? 404 : 200), text: async () => JSON.stringify(body ?? {}) };
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
    expect(screen.getByLabelText('krypton')).toBeTruthy();
  });

  it('Gates answers a review with a verdict, and re-verifies a gate that spends', async () => {
    const verify = jest.fn(async () => false);
    const posted = await renderWith(<GatesScreen verify={verify} />, {
      'GET /api/v1/gates': {
        gates: [
          { gate_id: 'g1', project_id: 'p1', job_id: null, kind: 'approval', prompt: 'Ship it?', options: ['accept'], default_answer: null, timeout_at: null },
          { gate_id: 'g2', project_id: 'p1', job_id: null, kind: 'budget_exhausted', prompt: 'More?', options: ['25'], default_answer: null, timeout_at: null },
        ],
      },
      'POST /api/v1/gates/g1/answer': { replayed: false },
    });
    await fireEvent.press(await screen.findByText('accept'));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(JSON.parse(posted[0]!.body).answer).toEqual({ verdict: 'accept' });
    // A grant is answered on the host: no button, nothing sent, no verification asked.
    expect(screen.queryByText('25')).toBeNull();
    expect(screen.getAllByText(/Answer this gate on the host/)).toHaveLength(1);
    expect(verify).not.toHaveBeenCalled();
    expect(posted).toHaveLength(1);
  });

  it('Home starts a project from a button, and says what to do when there is none', async () => {
    const { router } = jest.requireMock('expo-router') as { router: { push: jest.Mock } };
    await renderWith(<HomeScreen />, { 'GET /api/v1/projects': [] });
    expect(await screen.findByText(/@krypton \/new/)).toBeTruthy();
    await fireEvent.press(screen.getByText('Start a project'));
    expect(router.push).toHaveBeenCalledWith('/start');
  });

  it('Start refuses a bad name before asking the hub, and never sends a folder', async () => {
    const posted = await renderWith(<StartScreen />, {
      'POST /api/v1/projects': { __status: 201, body: { project_id: 'p9', name: 'greeter', outcome: 'design job j1' } },
    });
    await fireEvent.changeText(screen.getByLabelText('Project name'), 'has space');
    await fireEvent.press(screen.getByText('Start'));
    expect(await screen.findByText(/No spaces/)).toBeTruthy();
    expect(posted).toHaveLength(0);
    await fireEvent.changeText(screen.getByLabelText('Project name'), 'greeter');
    await fireEvent.changeText(screen.getByLabelText('What to build'), 'a greeting page');
    await fireEvent.press(screen.getByText('Start'));
    expect(await screen.findByText(/Started "greeter"/)).toBeTruthy();
    expect(JSON.parse(posted[0]!.body)).toEqual({ name: 'greeter', intake: 'a greeting page' });
  });

  it('Start says why the host will not, in the hub\'s words', async () => {
    await renderWith(<StartScreen />, { 'POST /api/v1/projects': { __status: 503, body: { detail: 'this host has not allowed projects to be started from a device' } } });
    await fireEvent.changeText(screen.getByLabelText('Project name'), 'greeter');
    await fireEvent.press(screen.getByText('Start'));
    expect(await screen.findByText(/this host has not allowed projects/)).toBeTruthy();
  });

  it('a project card resumes and pauses its own project', async () => {
    const posted = await renderWith(<HomeScreen />, {
      'GET /api/v1/projects': [project],
      'POST /api/v1/projects/p1/work/start': { message: 'worker started' },
      'POST /api/v1/projects/p1/work/pause': {},
    });
    await fireEvent.press(await screen.findByText('Resume'));
    expect(await screen.findByText('worker started')).toBeTruthy();
    await fireEvent.press(screen.getByText('Pause'));
    expect(await screen.findByText('Paused.')).toBeTruthy();
    expect(posted.map((call) => call.url)).toEqual(['/api/v1/projects/p1/work/start', '/api/v1/projects/p1/work/pause']);
  });

  it('a finished project offers no actions', async () => {
    await renderWith(<HomeScreen />, { 'GET /api/v1/projects': [{ ...project, phase: 'DONE', open_gates: 0 }] });
    await screen.findByText('Greeter');
    expect(screen.queryByText('Pause')).toBeNull();
  });

  it('Unwind asks why, shows what it would cancel, re-checks it is you, then does it', async () => {
    const report = { project_id: 'p1', name: 'Greeter', from: 'build', to: 'abandoned', dry_run: true, already_abandoned: false, cancelled_jobs: [{}, {}], withdrawn_gates: [{}] };
    const posted = await renderWith(<HomeScreen />, { 'GET /api/v1/projects': [project], 'POST /api/v1/projects/p1/abandon': report });
    await fireEvent.press(await screen.findByText('Unwind…'));
    await fireEvent.press(screen.getByText('See what it would cancel'));
    expect(await screen.findByText(/Say why/)).toBeTruthy();
    expect(posted).toHaveLength(0);
    await fireEvent.changeText(screen.getByLabelText('Why unwind this project'), 'not needed');
    await fireEvent.press(screen.getByText('See what it would cancel'));
    expect(await screen.findByText(/cancels 2 queued or running jobs and withdraws 1 waiting questions/)).toBeTruthy();
    await fireEvent.press(screen.getByText('Unwind for good'));
    expect(await screen.findByText(/Unwound "Greeter": 2 jobs cancelled/)).toBeTruthy();
    expect(posted.map((call) => JSON.parse(call.body))).toEqual([
      { reason: 'not needed', dry_run: true },
      { reason: 'not needed', dry_run: false },
    ]);
  });

  it('Unwind does nothing when it cannot confirm it is you, and can be cancelled', async () => {
    const auth = jest.requireMock('expo-local-authentication') as { authenticateAsync: jest.Mock };
    auth.authenticateAsync.mockResolvedValueOnce({ success: false });
    const report = { project_id: 'p1', name: 'Greeter', dry_run: true, already_abandoned: false, cancelled_jobs: [], withdrawn_gates: [] };
    const posted = await renderWith(<HomeScreen />, { 'GET /api/v1/projects': [project], 'POST /api/v1/projects/p1/abandon': report });
    await fireEvent.press(await screen.findByText('Unwind…'));
    await fireEvent.changeText(screen.getByLabelText('Why unwind this project'), 'not needed');
    await fireEvent.press(screen.getByText('See what it would cancel'));
    await fireEvent.press(await screen.findByText('Unwind for good'));
    expect(await screen.findByText(/Not confirmed; nothing was changed/)).toBeTruthy();
    expect(posted).toHaveLength(1);
    await fireEvent.press(screen.getByText('Keep it'));
    await fireEvent.press(screen.getByText('Unwind…'));
    await fireEvent.press(screen.getByText('Cancel'));
    expect(screen.getByText('Unwind…')).toBeTruthy();
  });

  it('Unwind says so when the project is already unwound', async () => {
    const report = { project_id: 'p1', name: 'Greeter', dry_run: true, already_abandoned: true, cancelled_jobs: [], withdrawn_gates: [] };
    await renderWith(<HomeScreen />, { 'GET /api/v1/projects': [project], 'POST /api/v1/projects/p1/abandon': report });
    await fireEvent.press(await screen.findByText('Unwind…'));
    await fireEvent.changeText(screen.getByLabelText('Why unwind this project'), 'x');
    await fireEvent.press(screen.getByText('See what it would cancel'));
    expect(await screen.findByText('This project is already unwound.')).toBeTruthy();
    expect(screen.queryByText('Unwind for good')).toBeNull();
  });

  it('Gates lets a phone accept the design interview\'s suggested answers', async () => {
    const posted = await renderWith(<GatesScreen verify={async () => true} />, {
      'GET /api/v1/gates': { gates: [{ gate_id: 'g5', project_id: 'p1', job_id: null, kind: 'question', prompt: 'Who is it for?', options: [], default_answer: null, timeout_at: null }] },
      'POST /api/v1/gates/g5/answer': { replayed: false },
    });
    await fireEvent.press(await screen.findByText('Accept the suggested answers'));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(JSON.parse(posted[0]!.body).answer).toEqual({ accept_defaults: true });
  });

  it('tells a person about a new question once, and about nothing that was already there', async () => {
    jest.useFakeTimers();
    try {
      const schedule = Notifications.scheduleNotificationAsync as jest.Mock;
      schedule.mockClear();
      let gates: unknown[] = [];
      await renderWith(<GateNotifications />, {
        'GET /api/v1/projects': [project],
        'GET /api/v1/gates': () => ({ gates }),
      });
      await act(async () => {
        await jest.advanceTimersByTimeAsync(10);
      });
      expect(schedule).not.toHaveBeenCalled();
      gates = [{ gate_id: 'g9', project_id: 'p1', project_name: 'Greeter', job_id: null, kind: 'question', prompt: 'Who is it for?\nmore', options: [], default_answer: null, timeout_at: null }];
      await act(async () => {
        await jest.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS);
      });
      expect(schedule).toHaveBeenCalledTimes(1);
      expect(schedule.mock.calls[0]![0]).toMatchObject({ identifier: 'gate-g9', content: { title: 'Greeter needs you', body: 'Who is it for?', data: { route: '/gates' } }, trigger: null });
      await act(async () => {
        await jest.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS);
      });
      expect(schedule).toHaveBeenCalledTimes(1);
    } finally {
      jest.useRealTimers();
    }
  });

  it('does not notify without the phone\'s permission, and says nothing when the hub is away', async () => {
    jest.useFakeTimers();
    try {
      const schedule = Notifications.scheduleNotificationAsync as jest.Mock;
      schedule.mockClear();
      (Notifications.getPermissionsAsync as jest.Mock).mockResolvedValue({ granted: false, canAskAgain: false });
      let gates: unknown[] = [];
      await renderWith(<GateNotifications />, { 'GET /api/v1/projects': [project], 'GET /api/v1/gates': () => ({ gates }) });
      await act(async () => {
        await jest.advanceTimersByTimeAsync(10);
      });
      gates = [{ gate_id: 'g9', project_id: 'p1', job_id: null, kind: 'question', prompt: 'q', options: [], default_answer: null, timeout_at: null }];
      await act(async () => {
        await jest.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS);
      });
      expect(schedule).not.toHaveBeenCalled();
      (Notifications.getPermissionsAsync as jest.Mock).mockResolvedValue({ granted: false, canAskAgain: true });
      (Notifications.requestPermissionsAsync as jest.Mock).mockResolvedValueOnce({ granted: true });
      gates = [...gates, { gate_id: 'g10', project_id: 'p1', job_id: null, kind: 'question', prompt: 'r', options: [], default_answer: null, timeout_at: null }];
      await act(async () => {
        await jest.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS);
      });
      expect(schedule).toHaveBeenCalledTimes(1);
    } finally {
      (Notifications.getPermissionsAsync as jest.Mock).mockResolvedValue({ granted: true, canAskAgain: true });
      jest.useRealTimers();
    }
  });

  describe('answering from a notification', () => {
    const gateOf = (kind: string, options: string[]) => ({ gate_id: 'g1', project_id: 'p1', project_name: 'Greeter', job_id: null, kind, prompt: 'Ship it?', options, default_answer: null, timeout_at: null });
    const DEFAULT = 'expo.modules.notifications.actions.DEFAULT';
    const schedule = Notifications.scheduleNotificationAsync as jest.Mock;
    const category = Notifications.setNotificationCategoryAsync as jest.Mock;
    const listener = () => (Notifications.addNotificationResponseReceivedListener as jest.Mock).mock.calls.at(-1)![0] as (response: unknown) => void;
    const pressed = (actionIdentifier: string, data: Record<string, unknown>) => ({ actionIdentifier, notification: { request: { content: { data } } } });

    /** The hub shows one new gate on the second look; returns what was posted. */
    async function raise(gate: unknown, answer: unknown = { replayed: false }) {
      schedule.mockClear();
      category.mockClear();
      let gates: unknown[] = [];
      const posted = await renderWith(<GateNotifications />, {
        'GET /api/v1/projects': [project],
        'GET /api/v1/gates': () => ({ gates }),
        'POST /api/v1/gates/g1/answer': answer,
      });
      await act(async () => {
        await jest.advanceTimersByTimeAsync(10);
      });
      gates = [gate];
      await act(async () => {
        await jest.advanceTimersByTimeAsync(NOTIFICATION_POLL_MS);
      });
      return posted;
    }

    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    it('puts the options on a review as buttons that need the phone unlocked and do not open the app', async () => {
      await raise(gateOf('approval', ['accept', 'reject']));
      expect(category).toHaveBeenCalledWith('krypton-gate:accept|reject', [
        { identifier: 'accept', buttonTitle: 'accept', options: { opensAppToForeground: false, isAuthenticationRequired: true } },
        { identifier: 'reject', buttonTitle: 'reject', options: { opensAppToForeground: false, isAuthenticationRequired: true } },
      ]);
      expect(schedule.mock.calls[0]![0].content).toMatchObject({ categoryIdentifier: 'krypton-gate:accept|reject', data: { route: '/gates', gateId: 'g1', gateKind: 'approval', options: ['accept', 'reject'] } });
    });

    it('puts no buttons on a gate that spends: its notification only opens the app', async () => {
      await raise(gateOf('budget_exhausted', ['25']));
      expect(category).not.toHaveBeenCalled();
      expect(schedule.mock.calls[0]![0].content.categoryIdentifier).toBeUndefined();
    });

    it('sends the answer once when a button is pressed, and says it was answered', async () => {
      const posted = await raise(gateOf('approval', ['accept', 'reject']));
      schedule.mockClear();
      await act(async () => {
        listener()(pressed('reject', { route: '/gates', gateId: 'g1', gateKind: 'approval', options: ['accept', 'reject'] }));
        await jest.advanceTimersByTimeAsync(10);
      });
      expect(posted.map((call) => [call.url, JSON.parse(call.body)])).toEqual([['/api/v1/gates/g1/answer', expect.objectContaining({ answer: { verdict: 'reject' } })]]);
      expect(schedule.mock.calls[0]![0]).toMatchObject({ identifier: 'answered-g1', content: { title: 'Answered' } });
    });

    it('never answers a gate that spends, even when told a button was pressed', async () => {
      const posted = await raise(gateOf('budget_exhausted', ['25']));
      schedule.mockClear();
      await act(async () => {
        listener()(pressed('25', { route: '/gates', gateId: 'g1', gateKind: 'budget_exhausted', options: ['25'] }));
        listener()(pressed('accept', { route: '/gates', gateId: 'g1', gateKind: 'deploy_acceptance', options: ['accept'] }));
        await jest.advanceTimersByTimeAsync(10);
      });
      expect(posted).toHaveLength(0);
      expect(schedule).not.toHaveBeenCalled();
    });

    it('ignores a button the gate does not offer, and a notification with no gate on it', async () => {
      const posted = await raise(gateOf('approval', ['accept']));
      schedule.mockClear();
      await act(async () => {
        listener()(pressed('delete-everything', { route: '/gates', gateId: 'g1', gateKind: 'approval', options: ['accept'] }));
        listener()(pressed('accept', { route: '/gates' }));
        listener()(pressed('accept', { gateId: 'g1', gateKind: 'approval', options: 'accept' }));
        await jest.advanceTimersByTimeAsync(10);
      });
      expect(posted).toHaveLength(0);
      expect(schedule).not.toHaveBeenCalled();
    });

    it('says when the answer was not sent, and opens Gates on a tap, rather than failing silently', async () => {
      const posted = await raise(gateOf('approval', ['accept']), { __status: 503, body: { detail: 'the hub is away' } });
      schedule.mockClear();
      await act(async () => {
        listener()(pressed('accept', { route: '/gates', gateId: 'g1', gateKind: 'approval', options: ['accept'] }));
        await jest.advanceTimersByTimeAsync(10);
      });
      expect(posted).toHaveLength(1);
      expect(schedule.mock.calls[0]![0]).toMatchObject({ identifier: 'answered-g1', content: { title: 'Your answer was not sent', data: { route: '/gates' } } });
      expect(schedule.mock.calls[0]![0].content.body).toContain('Open krypton to answer.');
    });

    it('still opens the app on a plain tap', async () => {
      const { router } = jest.requireMock('expo-router') as { router: { push: jest.Mock } };
      await raise(gateOf('approval', ['accept']));
      router.push.mockClear();
      listener()(pressed(DEFAULT, { route: '/gates' }));
      listener()(pressed(DEFAULT, {}));
      expect(router.push.mock.calls).toEqual([['/gates'], ['/']]);
    });
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
    expect(screen.getByText(/Channel: krypton/)).toBeTruthy();
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

  it('Run on GitHub says when no hub is connected', async () => {
    await renderWith(<WorkflowsScreen />, {}, false);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'status');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText('Not connected to a hub yet.')).toBeTruthy();
  });

  it('says when no hub is connected', async () => {
    await renderWith(<HomeScreen />, {}, false);
    expect(await screen.findByText('Not connected to a hub yet.')).toBeTruthy();
  });
});

type Answer = { readonly status: number; readonly body: unknown };

/** The workflows routes: the start answers 202, then each read takes the next answer. */
async function renderWorkflows(start: Answer, reads: readonly Answer[], runs?: WorkflowRuns) {
  const queue = [...reads];
  const sent: string[] = [];
  const fetchLike = (async (url: string, init: { method: string; body?: string }) => {
    // The app's own reachability probe is not one of the requests under test.
    if (url.includes('/health/')) return { status: 200, text: async () => '{}' };
    const answer = init.method === 'POST' ? start : (queue.shift() as Answer);
    if (init.method === 'POST') sent.push(init.body ?? '');
    else sent.push(url.replace('http://hub:8765', ''));
    return { status: answer.status, text: async () => JSON.stringify(answer.body) };
  }) as unknown as typeof fetch;
  await render(
    <AppStateProvider store={new MemoryStore()} fetchLike={fetchLike} initial={{ connection: { baseUrl: 'http://hub:8765', token: 't' } }}>
      <WorkflowsScreen runs={runs ?? new WorkflowRuns({ sleep: async () => undefined })} />
    </AppStateProvider>,
  );
  return sent;
}

const queued = { request_id: 'r1', state: 'queued', url: '', exit_code: null, stdout: '', stderr: '', detail: '' };
const url = 'https://github.com/o/r/actions/runs/7';

describe('Run on GitHub', () => {
  it('runs a command line, holds Run while it is in flight, and shows the output and the link', async () => {
    let release: () => void = () => undefined;
    const runs = new WorkflowRuns({ sleep: () => new Promise<void>((resolve) => (release = resolve)) });
    const sent = await renderWorkflows(
      { status: 202, body: queued },
      [{ status: 200, body: { ...queued, state: 'done', url, exit_code: 0, stdout: '{"phase": "BUILD"}', stderr: '' } }],
      runs,
    );
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'vibey -w status "--json"');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText('Queued')).toBeTruthy();
    expect(screen.getByText('vibey -w status --json')).toBeTruthy();
    expect(screen.getByText(/link appears once/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Running…' }).props.accessibilityState).toMatchObject({ disabled: true });
    await waitFor(() => release());
    expect(await screen.findByText('Done · exit 0')).toBeTruthy();
    expect(screen.getByText('{"phase": "BUILD"}')).toBeTruthy();
    expect(screen.getByText('(nothing)')).toBeTruthy();
    expect(screen.getByText('Exit code 0')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Run' }).props.accessibilityState).toMatchObject({ disabled: false });
    expect(JSON.parse(sent[0]!)).toEqual({ argv: ['status', '--json'] });
    expect(sent[1]).toBe('/api/v1/workflows/runs/r1');
    const open = jest.spyOn(Linking, 'openURL').mockResolvedValue(true);
    await fireEvent.press(screen.getByText('Open the run on GitHub ↗'));
    expect(open).toHaveBeenCalledWith(url);
  });

  it('says why a run failed', async () => {
    await renderWorkflows({ status: 202, body: queued }, [{ status: 200, body: { ...queued, state: 'failed', detail: 'the dispatch was cancelled' } }]);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'status');
    await fireEvent(screen.getByLabelText('Command line'), 'submitEditing');
    expect(await screen.findByText('the dispatch was cancelled')).toBeTruthy();
    expect(screen.getByText('Failed')).toBeTruthy();
  });

  it('says a failed run failed when the hub gives no reason', async () => {
    await renderWorkflows({ status: 202, body: queued }, [{ status: 200, body: { ...queued, state: 'failed' } }]);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'status');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText('The run failed on GitHub.')).toBeTruthy();
  });

  it('says a device without the workflows scope may not run it', async () => {
    await renderWorkflows({ status: 403, body: { detail: 'phone may not run commands on the workflows' } }, []);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'status');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText(/needs the `workflows` scope.*phone may not run commands/)).toBeTruthy();
    expect(screen.queryByTestId('workflow-run')).toBeNull();
  });

  it('says when the hub has no workflows enabled', async () => {
    await renderWorkflows({ status: 503, body: { detail: 'workflows are not enabled on this hub' } }, []);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'status');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText(/workflows are not enabled on it/)).toBeTruthy();
  });

  it('refuses a command line it cannot split, before anything is sent', async () => {
    const sent = await renderWorkflows({ status: 202, body: queued }, []);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'new "half');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText('A double quote is not closed.')).toBeTruthy();
    expect(sent).toEqual([]);
  });

  it('says plainly when it stopped waiting, and where the run carries on', async () => {
    let clock = 0;
    const runs = new WorkflowRuns({ now: () => clock, sleep: async (ms) => void (clock += ms), everyMs: 1000, giveUpMs: 1000 });
    await renderWorkflows({ status: 202, body: queued }, [{ status: 200, body: { ...queued, state: 'running', url, stdout: 'partial' } }], runs);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'status');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText(`Still running at ${url}. Stopped waiting after 0 min; the run carries on.`)).toBeTruthy();
    expect(screen.getByText('Running')).toBeTruthy();
    expect(screen.getByText('partial')).toBeTruthy();
  });

  it('stops reading when the screen goes away', async () => {
    let release: () => void = () => undefined;
    const runs = new WorkflowRuns({ sleep: () => new Promise<void>((resolve) => (release = resolve)) });
    const sent = await renderWorkflows({ status: 202, body: queued }, [], runs);
    await fireEvent.changeText(screen.getByLabelText('Command line'), 'status');
    await fireEvent.press(screen.getByText('Run'));
    expect(await screen.findByText('Queued')).toBeTruthy();
    await screen.unmount();
    await waitFor(() => release());
    expect(sent).toHaveLength(1);
  });
});
