// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Shares a project's text with the system's share sheet; on a browser with none, copies it. */
import { Share } from 'react-native';
import { ShareComposer } from '../core';
import type { ShareableProject } from '../core';
import { copyText } from './clipboard';

const composer = new ShareComposer();

export type ShareOutcome = 'shared' | 'copied' | 'dismissed' | 'failed';

export async function shareProject(project: ShareableProject): Promise<ShareOutcome> {
  const text = composer.compose(project);
  try {
    const result = await Share.share({ title: text.title, message: text.message });
    if (result.action === Share.dismissedAction) return 'dismissed';
    return 'shared';
  } catch {
    return (await copyText(text.message)) ? 'copied' : 'failed';
  }
}
