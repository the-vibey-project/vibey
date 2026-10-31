// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import * as Clipboard from 'expo-clipboard';
import type { ReactNode } from 'react';
import { Share } from 'react-native';
import { HomeScreen } from '../../src/screens/home';
import { AppStateProvider, MemoryStore } from '../../src/ui/app-state';

jest.mock('expo-router', () => ({
  Link: ({ children }: { children: ReactNode }) => children,
  router: { replace: jest.fn(), push: jest.fn() },
}));
jest.mock('expo-clipboard', () => ({ setStringAsync: jest.fn(async () => true) }));
jest.mock('expo-local-authentication', () => ({ authenticateAsync: jest.fn(async () => ({ success: true })) }));

const project = { project_id: 'p-secret-id', name: 'Greeter', phase: 'BUILD', open_gates: 2, cycle: 1, max_cycles: 3 };

async function home() {
  const fetchLike = (async (url: string) => ({
    status: url.endsWith('/api/v1/projects') ? 200 : 404,
    text: async () => JSON.stringify([project]),
  })) as unknown as typeof fetch;
  await render(
    <AppStateProvider store={new MemoryStore()} fetchLike={fetchLike} initial={{ connection: { baseUrl: 'http://hub:8765', token: 'host-token' } }}>
      <HomeScreen />
    </AppStateProvider>,
  );
  return screen.findByText('Greeter');
}

describe('sharing a project', () => {
  afterEach(() => jest.restoreAllMocks());

  it('opens the share sheet with the name, phase and cycle, and nothing else', async () => {
    const share = jest.spyOn(Share, 'share').mockResolvedValue({ action: Share.sharedAction });
    await home();
    await fireEvent.press(screen.getByText('Share'));
    await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
    expect(share).toHaveBeenCalledWith({ title: 'Greeter on krypton', message: 'Greeter is in BUILD, cycle 1 of 3.' });
    const sent = JSON.stringify(share.mock.calls);
    for (const leaked of ['p-secret-id', 'host-token', 'hub:8765']) expect(sent).not.toContain(leaked);
    expect(screen.queryByText('Copied to the clipboard.')).toBeNull();
  });

  it('says nothing when the share sheet is dismissed', async () => {
    const share = jest.spyOn(Share, 'share').mockResolvedValue({ action: Share.dismissedAction });
    await home();
    await fireEvent.press(screen.getByText('Share'));
    await waitFor(() => expect(share).toHaveBeenCalled());
    expect(screen.queryByText('Could not share it.')).toBeNull();
    expect(screen.queryByText('Copied to the clipboard.')).toBeNull();
  });

  it('copies the text where there is no share sheet, and says so', async () => {
    jest.spyOn(Share, 'share').mockRejectedValue(new Error('not supported'));
    await home();
    await fireEvent.press(screen.getByText('Share'));
    expect(await screen.findByText('Copied to the clipboard.')).toBeTruthy();
    expect(Clipboard.setStringAsync).toHaveBeenCalledWith('Greeter is in BUILD, cycle 1 of 3.');
  });

  it('says it could not share when neither the sheet nor the clipboard will', async () => {
    jest.spyOn(Share, 'share').mockRejectedValue(new Error('not supported'));
    (Clipboard.setStringAsync as jest.Mock).mockRejectedValueOnce(new Error('denied'));
    await home();
    await fireEvent.press(screen.getByText('Share'));
    expect(await screen.findByText('Could not share it.')).toBeTruthy();
  });
});
