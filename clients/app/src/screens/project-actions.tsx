// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { useState } from 'react';
import { TextInput, View } from 'react-native';
import type { ProjectCard } from '../core';
import type { VibeyAbandonReport } from '@vibey/core';
import { useApp } from '../ui/app-state';
import { Button, Label, Notice } from '../ui/kit';
import { useTheme } from '../ui/theme';
import { reverify } from './gates';

/** Resume, pause and unwind one project. Unwinding is the one that cannot be undone, so it shows a preview and re-checks it is you. */
export function ProjectActions(props: { readonly card: ProjectCard; readonly onDone: () => void; readonly verify?: (prompt: string) => Promise<boolean> }) {
  const { client } = useApp();
  const { colors } = useTheme();
  const [step, setStep] = useState<'idle' | 'reason' | 'preview'>('idle');
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState<VibeyAbandonReport | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const verify = props.verify ?? reverify;
  const input = { borderWidth: 1, borderColor: colors.border.strong, color: colors.text.primary, borderRadius: 12, padding: 12, fontSize: 16 };
  const { card } = props;

  if (card.finished || client === null) return null;

  const act = async (work: () => Promise<string>) => {
    try {
      setMessage(await work());
      props.onDone();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  };

  const look = async () => {
    if (reason.trim() === '') return setMessage('Say why, in a few words. It is recorded with the project.');
    try {
      setPreview(await client.abandonProject(card.id, reason.trim(), { dryRun: true }));
      setMessage(null);
      setStep('preview');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  };

  const unwind = async () => {
    if (!(await verify('Confirm unwinding this project'))) {
      return setMessage('Not confirmed; nothing was changed. Unwinding cannot be undone, so it needs Face ID, Touch ID or your passcode.');
    }
    await act(async () => {
      const done = await client.abandonProject(card.id, reason.trim());
      setStep('idle');
      return `Unwound "${done.name}": ${done.cancelled_jobs} jobs cancelled, ${done.withdrawn_gates} questions withdrawn.`;
    });
  };

  return (
    <View style={{ gap: 8 }}>
      {step === 'idle' ? (
        <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
          <Button label="Resume" kind="quiet" onPress={() => void act(() => client.startWork(card.id))} />
          <Button label="Pause" kind="quiet" onPress={() => void act(() => client.pauseWork(card.id))} />
          <Button label="Unwind…" kind="quiet" onPress={() => setStep('reason')} />
        </View>
      ) : null}
      {step === 'reason' ? (
        <>
          <Label tone="secondary">Why unwind it? In a few words; it is recorded on the project.</Label>
          <TextInput accessibilityLabel="Why unwind this project" style={input} value={reason} onChangeText={setReason} placeholder="the requirements changed" placeholderTextColor={colors.text.tertiary} />
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Button label="See what it would cancel" onPress={() => void look()} />
            <Button label="Cancel" kind="quiet" onPress={() => setStep('idle')} />
          </View>
        </>
      ) : null}
      {step === 'preview' && preview !== null ? (
        <>
          <Notice role="warning">
            {preview.already_abandoned
              ? 'This project is already unwound.'
              : `Unwinding cancels ${preview.cancelled_jobs} queued or running jobs and withdraws ${preview.withdrawn_gates} waiting questions. This cannot be undone; the work already on disk is left as it is.`}
          </Notice>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            {preview.already_abandoned ? null : <Button label="Unwind for good" kind="danger" onPress={() => void unwind()} />}
            <Button label="Keep it" kind="quiet" onPress={() => setStep('idle')} />
          </View>
        </>
      ) : null}
      {message ? <Notice>{message}</Notice> : null}
    </View>
  );
}
