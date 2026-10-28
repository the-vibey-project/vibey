// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { render, screen, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';
import { WorkflowRuns } from '../../src/core/workflow-runs';
import { BudgetsScreen } from '../../src/screens/budgets';
import { DevicesScreen } from '../../src/screens/devices';
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
import { AccessibleControls } from './accessible-controls';
import type { TreeNode } from './accessible-controls';

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
}));
jest.mock('expo-camera', () => ({ CameraView: () => null, useCameraPermissions: () => [{ granted: false }, jest.fn()] }));
jest.mock('expo-local-authentication', () => ({ authenticateAsync: jest.fn(async () => ({ success: true })) }));

const controls = new AccessibleControls();

/**
 * THE MACHINE-CHECKABLE HALF of "every control is labelled". It reads the rendered tree of
 * each screen for what a screen reader would meet: every pressable, input and switch must have
 * a name, and every pressable a role. It says nothing about whether a name is a good one, and
 * a VoiceOver or TalkBack walk is a person's job (clients/app/ACCESSIBILITY.md records it).
 */
describe('the checker', () => {
  it('names a control by its label, else by the text inside it', () => {
    const tree: TreeNode = {
      type: 'View',
      children: [
        { type: 'View', props: { accessible: true, accessibilityRole: 'button', onClick: () => undefined }, children: [{ type: 'Text', children: ['Save'] }] },
        { type: 'TextInput', props: { accessibilityLabel: 'Project name' } },
        { type: 'RCTSwitch', props: { 'aria-label': 'Sounds' } },
      ],
    };
    expect(controls.find(tree).map((c) => [c.kind, c.name])).toEqual([['button', 'Save'], ['input', 'Project name'], ['switch', 'Sounds']]);
    expect(controls.flaws(tree)).toEqual([]);
  });

  it('flags a nameless control, a nameless input and a pressable with no role', () => {
    const tree: TreeNode[] = [
      { type: 'View', props: { accessible: true, accessibilityRole: 'button', onClick: () => undefined }, children: [{ type: 'View' }] },
      { type: 'TextInput', props: { placeholder: 'x' } },
      { type: 'View', props: { accessible: true, onClick: () => undefined }, children: [{ type: 'Text', children: ['Go'] }] },
      { type: 'View', props: { accessible: true, accessibilityRole: 'link', onClick: () => undefined }, children: [{ type: 'Text', children: ['Open'] }] },
    ];
    expect(controls.flaws(tree)).toEqual([
      'a button with no accessible name',
      'a input with no accessible name',
      'a pressable named "Go" with no accessibilityRole',
    ]);
  });

  it('finds nothing in an empty tree', () => {
    expect(controls.find(null)).toEqual([]);
  });
});

const project = { project_id: 'p1', name: 'Greeter', phase: 'BUILD', open_gates: 1, cycle: 1, max_cycle: 3, max_cycles: 3 };
const gate = (id: string, kind: string, options: string[]) => ({ gate_id: id, project_id: 'p1', job_id: null, kind, prompt: 'A question?', options, default_answer: null, timeout_at: null });

function hub(routes: Record<string, unknown>): typeof fetch {
  return (async (url: string, init: { method: string }) => {
    const route = routes[`${init.method} ${url.replace('http://hub:8765', '')}`];
    return { status: route === undefined ? 404 : 200, text: async () => JSON.stringify(route ?? {}) };
  }) as unknown as typeof fetch;
}

async function show(node: ReactNode, routes: Record<string, unknown> = {}, connected = true) {
  await render(
    <AppStateProvider store={new MemoryStore()} fetchLike={hub(routes)} initial={connected ? { connection: { baseUrl: 'http://hub:8765', token: 't' } } : {}}>
      {node}
    </AppStateProvider>,
  );
}

const loops = {
  efforts: ['TRIVIAL', 'LOW', 'STANDARD', 'HIGH', 'MAX', 'ULTRA'],
  default_loop: 'sovereignloop',
  paid_default_engine: 'claudeloop',
  ladder: { phase_base: {}, build_attempts: [], exhausted_after: 3, rotates_when_effort_rises: true },
  loops: [{ loop: 'sovereignloop', tier: 'local', default: true, declared_only: false, engines: [], by_effort: {} }],
};

/** Each screen with the data that makes it show its controls, the text that says it has loaded, and the fewest controls it must have. */
const SCREENS: readonly { title: string; render: () => Promise<void>; loaded: RegExp | string; atLeast: number }[] = [
  { title: 'Home', render: () => show(<HomeScreen />, { 'GET /api/v1/projects': [project] }), loaded: 'Greeter', atLeast: 4 },
  {
    title: 'Gates',
    render: () => show(<GatesScreen verify={async () => true} />, { 'GET /api/v1/gates': { gates: [gate('g1', 'approval', ['accept', 'reject']), gate('g2', 'question', []), gate('g3', 'budget_exhausted', ['25'])] } }),
    loaded: 'accept',
    atLeast: 3,
  },
  { title: 'Lanes', render: () => show(<LanesScreen />, { 'GET /api/v1/lanes': { lanes: [] } }), loaded: /lane/i, atLeast: 0 },
  { title: 'Effort', render: () => show(<EffortScreen />, { 'GET /api/v1/loops': loops, 'GET /api/v1/projects': [] }), loaded: 'ULTRA', atLeast: 5 },
  {
    title: 'Budgets',
    render: () => show(<BudgetsScreen />, { 'GET /api/v1/projects': [project], 'GET /api/v1/projects/p1/budget': { caps: { max_cycle_dollars: 10, max_cycle_turns: null }, spend: { dollars: 4, turns: 2 }, exhausted: false, history: [] } }),
    loaded: '$4.00 of $10.00',
    atLeast: 0,
  },
  { title: 'Doctor', render: () => show(<DoctorScreen />, { 'GET /api/v1/doctor': { scope: 'hub', checks: [{ name: 'database', mark: 'PASS', detail: 'the database answers' }] } }), loaded: 'the database answers', atLeast: 0 },
  { title: 'Settings', render: () => show(<SettingsScreen />), loaded: 'Sounds', atLeast: 8 },
  { title: 'Start', render: () => show(<StartScreen />), loaded: /Say what you want built/, atLeast: 3 },
  { title: 'Pair', render: () => show(<PairScreen />, {}, false), loaded: 'Pair', atLeast: 4 },
  { title: 'Devices', render: () => show(<DevicesScreen />), loaded: 'Forget this hub', atLeast: 1 },
  { title: 'Run on GitHub', render: () => show(<WorkflowsScreen runs={new WorkflowRuns({ sleep: async () => undefined })} />), loaded: /Run on GitHub/, atLeast: 2 },
];

describe('every screen', () => {
  it.each(SCREENS.map((entry) => [entry.title, entry] as const))('%s: every control has a name, every pressable a role', async (_title, { render: draw, loaded, atLeast }) => {
    await draw();
    await waitFor(() => expect(screen.getAllByText(loaded).length).toBeGreaterThan(0));
    const tree = screen.toJSON() as TreeNode | TreeNode[] | null;
    const found = controls.find(tree);
    // A screen with nothing to check would pass too: each one has the controls it should.
    expect(found.length).toBeGreaterThanOrEqual(atLeast);
    expect(controls.flaws(tree)).toEqual([]);
  });

  it('a screen that is still loading says so, rather than showing a silent spinner', async () => {
    const never = (() => new Promise(() => undefined)) as unknown as typeof fetch;
    await render(
      <AppStateProvider store={new MemoryStore()} fetchLike={never} initial={{ connection: { baseUrl: 'http://hub:8765', token: 't' } }}>
        <HomeScreen />
      </AppStateProvider>,
    );
    expect(screen.getByLabelText('Loading')).toBeTruthy();
  });

  it('the project card offers its actions with names too', async () => {
    await show(<HomeScreen />, { 'GET /api/v1/projects': [project] });
    await screen.findByText('Unwind…');
    expect(controls.find(screen.toJSON() as TreeNode).map((c) => c.name)).toEqual(expect.arrayContaining(['Start a project', 'Resume', 'Pause', 'Unwind…']));
  });
});
