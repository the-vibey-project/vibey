// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Run on GitHub: a vibey command line sent to the repository's GitHub-hosted runners, as `vibey -w` does (ADR-0085). */
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { HubClient, WorkflowRuns } from '../core';
import type { StatusRole, WorkflowRun } from '../core';
import { useApp } from '../ui/app-state';
import { Button, Card, Label, Notice, Pill, Screen } from '../ui/kit';
import { monoFamily, useTheme } from '../ui/theme';

const MONO = monoFamily();

function Output(props: { readonly title: string; readonly text: string; readonly finished: boolean }) {
  const { colors } = useTheme();
  if (props.text === '' && !props.finished) return null;
  return (
    <View style={{ gap: 4 }}>
      <Label tone="tertiary">{props.title}</Label>
      <ScrollView
        testID={`workflow-${props.title}`}
        nestedScrollEnabled
        style={{ maxHeight: 320, backgroundColor: colors.bg.code, borderColor: colors.border.subtle, borderWidth: 1, borderRadius: 12 }}
        contentContainerStyle={{ padding: 12 }}
      >
        <ScrollView horizontal nestedScrollEnabled>
          <Text selectable style={{ fontFamily: MONO, fontSize: 13, lineHeight: 18, color: props.text === '' ? colors.text.tertiary : colors.text.primary }}>
            {props.text === '' ? '(nothing)' : props.text}
          </Text>
        </ScrollView>
      </ScrollView>
    </View>
  );
}

export function WorkflowsScreen(props: { readonly runs?: WorkflowRuns }) {
  const { client } = useApp();
  const { colors } = useTheme();
  const runs = useMemo(() => props.runs ?? new WorkflowRuns(), [props.runs]);
  const [line, setLine] = useState('');
  const [sent, setSent] = useState<readonly string[]>([]);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ readonly text: string; readonly role: StatusRole } | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const start = async () => {
    if (client === null) return setMessage({ text: 'Not connected to a hub yet.', role: 'danger' });
    const parsed = runs.split(line);
    if (!parsed.ok) return setMessage({ text: parsed.reason, role: 'warning' });
    setBusy(true);
    setMessage(null);
    setRun(null);
    setSent(parsed.argv);
    try {
      const outcome = await runs.follow(client, parsed.argv, {
        onUpdate: (next) => {
          if (mounted.current) setRun(next);
        },
        cancelled: () => !mounted.current,
      });
      if (!mounted.current) return;
      if (outcome.kind === 'still-running') setMessage({ text: outcome.message, role: 'warning' });
      else if (outcome.run.state === 'failed') setMessage({ text: outcome.run.detail || 'The run failed on GitHub.', role: 'danger' });
    } catch (error) {
      if (mounted.current) setMessage({ text: error instanceof Error ? error.message : String(error), role: 'danger' });
    } finally {
      if (mounted.current) setBusy(false);
    }
  };

  const view = run === null ? null : runs.present(run);
  const input = { borderWidth: 1, borderColor: colors.border.strong, color: colors.text.primary, borderRadius: 12, padding: 12, fontSize: 16, fontFamily: MONO };

  return (
    <Screen
      title="Run on GitHub"
      subtitle={`Any vibey command, run on the repository's GitHub-hosted runners as \`vibey -w\` does. This device needs the \`workflows\` scope (${HubClient.SCOPES.workflows.toLowerCase()}) and the scopes of what the command does.`}
    >
      <Card role="info">
        <Label strong>Command</Label>
        <Label tone="secondary">Without `vibey` or `-w`. Double quotes keep a phrase together.</Label>
        <TextInput
          accessibilityLabel="Command line"
          style={input}
          autoCapitalize="none"
          autoCorrect={false}
          editable={!busy}
          value={line}
          onChangeText={setLine}
          onSubmitEditing={() => {
            if (!busy) void start();
          }}
          placeholder="status --json"
          placeholderTextColor={colors.text.tertiary}
        />
        <Button label={busy ? 'Running…' : 'Run'} disabled={busy} onPress={() => void start()} />
      </Card>
      {run !== null && view !== null ? (
        <Card role={view.role} testID="workflow-run">
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Pill role={view.role}>{view.label}</Pill>
            {busy ? <ActivityIndicator color={colors.accent.default} /> : null}
          </View>
          <Text selectable style={{ fontFamily: MONO, fontSize: 14, color: colors.text.secondary }}>{`vibey -w ${sent.join(' ')}`}</Text>
          {run.url === '' ? (
            <Label tone="tertiary">The GitHub link appears once the run is found.</Label>
          ) : (
            <Pressable accessibilityRole="link" onPress={() => { const url = HubClient.httpsUrl(run.url); if (url !== '') void Linking.openURL(url); }}>
              <Text style={{ color: colors.text.link, fontSize: 15, fontWeight: '600' }}>Open the run on GitHub ↗</Text>
            </Pressable>
          )}
          {run.exit_code === null ? null : <Label tone="secondary">{`Exit code ${run.exit_code}`}</Label>}
          <Output title="stdout" text={run.stdout} finished={view.finished} />
          <Output title="stderr" text={run.stderr} finished={view.finished} />
        </Card>
      ) : null}
      {message ? <Notice role={message.role}>{message.text}</Notice> : null}
    </Screen>
  );
}
