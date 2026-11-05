// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The chat-first landing screen for krypton on iOS, Android and the web (ADR-0100), mirroring
 * Claude Code and Codex: a session selector of projects, a conversational transcript with
 * tool-call cards and inline gate approval cards (with spend gates clearly badged), quick
 * slash-command chips, and a composer with `/` command completion.
 */
import { router } from 'expo-router';
import { useState } from 'react';
import { Platform, StyleSheet, TextInput, View } from 'react-native';
import { ChatModel, DevicePolicy, Presenters } from '../core';
import type { ChatGateCard, ChatToolCall, GateCard } from '../core';
import { useApp } from '../ui/app-state';
import { Button, Card, HubStatusCard, Label, Loaded, Notice, Pill, Screen, useHub } from '../ui/kit';
import { useTheme } from '../ui/theme';
import { reverify } from './gates';

const chatModel = new ChatModel();
const present = new Presenters();
const policy = new DevicePolicy();

interface TranscriptEntry {
  readonly id: string;
  readonly userMessage: string;
  readonly reply?: string;
  readonly error?: string;
  readonly toolCalls: readonly ChatToolCall[];
  readonly gates: readonly ChatGateCard[];
}

function InlineGateCard(props: {
  readonly gate: GateCard;
  readonly onDone: () => void;
  readonly verify: () => Promise<boolean>;
}) {
  const { client } = useApp();
  const [note, setNote] = useState<string | null>(null);
  const { gate } = props;

  const choose = async (value: string) => {
    const decision = policy.decide(gate.spends ? 'answer-spend' : 'answer');
    if (decision.allowed && decision.confirm && !(await props.verify())) {
      setNote(
        Platform.OS === 'web'
          ? 'Answer gates that spend from your phone, where it can check it is you.'
          : 'Not confirmed; nothing was sent.',
      );
      return;
    }
    try {
      if (gate.answerKey === 'host') return;
      setNote(
        await client!.answer(
          gate.id,
          gate.answerKey === 'interview' ? { mode: 'defaults' } : { mode: gate.answerKey, value },
        ),
      );
      props.onDone();
    } catch (error) {
      setNote(error instanceof Error ? error.message : String(error));
    }
  };

  return (
    <Card role={gate.spends ? 'ultra' : 'warning'} testID={`chat-gate-${gate.id}`}>
      <Label strong>{gate.title}</Label>
      <View style={styles.row}>
        <Pill role="warning">{gate.due}</Pill>
        <Pill role={gate.spends ? 'ultra' : 'info'}>
          {chatModel.gateBadge({ isSpend: gate.spends })}
        </Pill>
      </View>
      <Label tone="secondary">{gate.prompt}</Label>
      {gate.answerKey === 'interview' ? (
        <Button label="Accept the suggested answers" onPress={() => void choose('')} />
      ) : null}
      {gate.answerKey === 'verdict' || gate.answerKey === 'choice'
        ? gate.options.map((option) => (
            <Button key={option} label={option} onPress={() => void choose(option)} />
          ))
        : null}
      {gate.answerKey === 'host' || (gate.answerKey !== 'interview' && gate.options.length === 0) ? (
        <Label tone="tertiary">Answer this gate on the host: `vibey answer` takes the value it needs.</Label>
      ) : null}
      {note ? <Notice>{note}</Notice> : null}
    </Card>
  );
}

export function ChatScreen(props: { readonly verify?: () => Promise<boolean> }) {
  const { client } = useApp();
  const { colors } = useTheme();
  const { result, reload } = useHub(async (hub) => {
    const [projects, gates] = await Promise.all([hub.projects(), hub.gates()]);
    return { projects, gates };
  });

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [typed, setTyped] = useState('');
  const [sending, setSending] = useState(false);
  const [entries, setEntries] = useState<readonly TranscriptEntry[]>([]);

  const completions = chatModel.completeSlash(typed);

  const sendMessage = async (rawMessage: string) => {
    const trimmed = rawMessage.trim();
    if (trimmed === '' || sending) return;
    const turnId = `turn-${entries.length + 1}`;
    setTyped('');
    if (client === null) {
      setEntries((prev) => [
        ...prev,
        { id: turnId, userMessage: trimmed, error: 'Not connected to a hub yet.', toolCalls: [], gates: [] },
      ]);
      return;
    }
    setSending(true);
    try {
      const turn = await client.chat(trimmed, selectedProjectId);
      if (turn.projectId !== null) {
        setSelectedProjectId(turn.projectId);
      }
      setEntries((prev) => [
        ...prev,
        {
          id: turnId,
          userMessage: trimmed,
          reply: turn.reply,
          toolCalls: turn.toolCalls,
          gates: turn.gates,
        },
      ]);
      reload();
    } catch (error) {
      setEntries((prev) => [
        ...prev,
        {
          id: turnId,
          userMessage: trimmed,
          error: error instanceof Error ? error.message : String(error),
          toolCalls: [],
          gates: [],
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <Screen
      title="Chat"
      subtitle="Drive krypton by conversation: ask about projects, answer gates, or type / for commands."
      onRefresh={reload}
    >
      <HubStatusCard />
      <View style={styles.row}>
        <Button label="Start a project" kind="quiet" onPress={() => router.push('/start')} />
      </View>

      <Loaded result={result}>
        {({ projects, gates }) => {
          const filteredGates =
            selectedProjectId === null
              ? gates
              : gates.filter((gate) => gate.project_id === selectedProjectId);
          const gateCards = present.gates(filteredGates, Date.now());

          return (
            <>
              <Card testID="chat-sessions">
                <Label strong>Session</Label>
                <View style={styles.row}>
                  <Button
                    label="All projects"
                    kind={selectedProjectId === null ? 'primary' : 'quiet'}
                    onPress={() => setSelectedProjectId(null)}
                  />
                  {projects.map((project) => (
                    <Button
                      key={project.project_id}
                      label={project.name}
                      kind={selectedProjectId === project.project_id ? 'primary' : 'quiet'}
                      onPress={() => setSelectedProjectId(project.project_id)}
                    />
                  ))}
                </View>
              </Card>

              <Card testID="chat-quick-commands">
                <Label strong>Quick commands</Label>
                <View style={styles.row}>
                  {ChatModel.QUICK_COMMANDS.map((item) => (
                    <Button
                      key={item.command}
                      label={item.label}
                      kind="quiet"
                      disabled={sending}
                      onPress={() => void sendMessage(item.command)}
                    />
                  ))}
                </View>
              </Card>

              {gateCards.length > 0 ? (
                <>
                  <Label strong>Waiting for your decision</Label>
                  {gateCards.map((gate) => (
                    <InlineGateCard
                      key={gate.id}
                      gate={gate}
                      onDone={reload}
                      verify={props.verify ?? reverify}
                    />
                  ))}
                </>
              ) : null}
            </>
          );
        }}
      </Loaded>

      <Card role="info" testID="chat-welcome">
        <Pill role="info">KRYPTON</Pill>
        <Label>
          Welcome to krypton chat. Pick a project session above, tap a quick command, or type `/` in
          the composer (`/projects`, `/status`, `/gates`, `/new`, `/help`).
        </Label>
      </Card>

      {entries.map((entry) => (
        <View key={entry.id} style={styles.turnGroup}>
          <Card testID={`${entry.id}-user`}>
            <Pill role="info">YOU</Pill>
            <Label>{entry.userMessage}</Label>
          </Card>

          {entry.toolCalls.map((call, idx) => (
            <Card key={`${entry.id}-tool-${idx}`} testID={`${entry.id}-tool-${idx}`}>
              <View style={styles.row}>
                <Pill role="neutral">TOOL</Pill>
                <Label strong>{call.name}</Label>
              </View>
              <Label tone="secondary">{call.argumentsJson}</Label>
              <Label tone="tertiary">{call.resultJson}</Label>
            </Card>
          ))}

          {entry.reply !== undefined ? (
            <Card role="success" testID={`${entry.id}-reply`}>
              <Pill role="success">KRYPTON</Pill>
              <Label>{entry.reply}</Label>
            </Card>
          ) : null}

          {entry.error !== undefined ? (
            <Notice role="danger">{entry.error}</Notice>
          ) : null}
        </View>
      ))}

      {completions.length > 0 ? (
        <Card testID="chat-completions">
          <Label strong>Slash commands</Label>
          {completions.map((spec) => (
            <View key={spec.slash} style={styles.completionRow}>
              <Button
                label={spec.usage}
                kind="quiet"
                onPress={() => setTyped(`/${spec.slash} `)}
              />
              <Label tone="secondary">{spec.description}</Label>
            </View>
          ))}
        </Card>
      ) : null}

      <Card testID="chat-composer">
        <Label strong>Message krypton</Label>
        <TextInput
          accessibilityLabel="Chat message or slash command"
          value={typed}
          onChangeText={setTyped}
          onSubmitEditing={() => void sendMessage(typed)}
          placeholder="Ask about a project, answer a gate, or type / for commands…"
          placeholderTextColor={colors.text.tertiary}
          autoCapitalize="none"
          autoCorrect={false}
          style={[
            styles.input,
            { color: colors.text.primary, borderColor: colors.border.subtle, backgroundColor: colors.bg.canvas },
          ]}
        />
        <Button
          label={sending ? 'Sending…' : 'Send'}
          disabled={sending}
          onPress={() => void sendMessage(typed)}
        />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  turnGroup: { gap: 8 },
  completionRow: { gap: 2, marginVertical: 2 },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
});
