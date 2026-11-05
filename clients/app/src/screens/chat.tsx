// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The chat-first landing screen for krypton on iOS, Android and the web (ADR-0100),
 * completely redesigned to match the frontier AI mobile application:
 * - Top app bar with drawer toggle, session title with status indicator, document viewer, new chat, and overflow
 * - Rich conversational transcript with inline badge pills for code/filenames, tool call cards, inline spend gates
 * - Full action bar per assistant message (Copy, Share, Audio/TTS, Thumbs up/down, Retry)
 * - AI disclaimer text
 * - Floating bottom composer with '+' session modal button, model pill selector, multiline input, mic, and waveform button
 * - 'Add to session' bottom sheet modal
 */
import { router } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { ChatModel, DevicePolicy, Presenters } from '../core';
import type { ChatGateCard, ChatToolCall, GateCard } from '../core';
import { useApp } from '../ui/app-state';
import { copyText } from '../ui/clipboard';
import { Button, Card, HubStatusCard, Label, Loaded, Notice, Pill, Screen, useHub } from '../ui/kit';
import { useTheme } from '../ui/theme';
import { AddSessionModal } from './add-session-modal';
import { reverify } from './gates';

const chatModel = new ChatModel();
const present = new Presenters();
const policy = new DevicePolicy();

const AVAILABLE_MODELS = [
  'Sonnet 5.5 Medium',
  'GPT-OSS 20B (Sovereign)',
  'Claudeloop',
  'Codexloop',
] as const;

interface TranscriptEntry {
  readonly id: string;
  readonly userMessage: string;
  readonly reply?: string;
  readonly error?: string;
  readonly toolCalls: readonly ChatToolCall[];
  readonly gates: readonly ChatGateCard[];
  readonly thumbsState?: 'up' | 'down';
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

/** Formats an assistant message paragraph with inline pill badges for code/file references */
function RichMessageText(props: { readonly text: string; readonly color: string }) {
  const { colors } = useTheme();
  const text = props.text;

  // Split lines
  const lines = text.split('\n');

  return (
    <View style={styles.richTextContainer}>
      {lines.map((line, lineIdx) => {
        const trimmed = line.trim();
        if (trimmed === '') {
          return <View key={lineIdx} style={styles.paragraphSpacer} />;
        }

        const isBullet = trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ');
        const content = isBullet ? trimmed.replace(/^[•\-\*]\s+/, '') : line;

        // Parse inline identifiers: `code`, #heading, filename.ext, flags --flag
        // Tokens surrounded by backticks or common extensions
        const parts = content.split(/(`[^`]+`|\b[a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9_\-]+|\b--[a-zA-Z0-9_\-]+|#\s*)/g);

        return (
          <View key={lineIdx} style={isBullet ? styles.bulletRow : styles.textRow}>
            {isBullet ? (
              <Text style={[styles.bulletPoint, { color: colors.text.secondary }]}>• </Text>
            ) : null}
            <Text style={[styles.paragraphText, { color: props.color }]}>
              {parts.map((part, partIdx) => {
                if (!part) return null;
                const isBackticked = part.startsWith('`') && part.endsWith('`');
                const isFile = /\b[a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9_\-]+/.test(part);
                const isFlag = /^--[a-zA-Z0-9_\-]+$/.test(part);
                const isHash = part.trim() === '#';

                if (isBackticked || isFile || isFlag || isHash) {
                  const cleaned = isBackticked ? part.slice(1, -1) : part;
                  return (
                    <Text
                      key={partIdx}
                      style={[
                        styles.inlinePill,
                        {
                          backgroundColor: colors.bg.canvas,
                          borderColor: colors.border.strong,
                          color: colors.accent.default,
                        },
                      ]}
                    >
                      {` ${cleaned} `}
                    </Text>
                  );
                }
                return <Text key={partIdx}>{part}</Text>;
              })}
            </Text>
          </View>
        );
      })}
    </View>
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
  const [modelIndex, setModelIndex] = useState(0);
  const [typed, setTyped] = useState('');
  const [sending, setSending] = useState(false);
  const [entries, setEntries] = useState<readonly TranscriptEntry[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [copiedTurnId, setCopiedTurnId] = useState<string | null>(null);
  const [speakingTurnId, setSpeakingTurnId] = useState<string | null>(null);

  const activeModel = AVAILABLE_MODELS[modelIndex] ?? 'Sonnet 5.5 Medium';
  const completions = chatModel.completeSlash(typed);

  const toggleModel = () => {
    setModelIndex((curr) => (curr + 1) % AVAILABLE_MODELS.length);
  };

  const handleCopy = async (id: string, text: string) => {
    await copyText(text);
    setCopiedTurnId(id);
    const timer = setTimeout(() => setCopiedTurnId(null), 2000);
    if (typeof (timer as unknown as { unref?: () => void }).unref === 'function') {
      (timer as unknown as { unref: () => void }).unref();
    }
  };

  const handleShare = async (text: string) => {
    try {
      await Share.share({ message: text });
    } catch {
      await copyText(text);
    }
  };

  const handleTts = (id: string) => {
    setSpeakingTurnId(id);
    const timer = setTimeout(() => setSpeakingTurnId(null), 1500);
    if (typeof (timer as unknown as { unref?: () => void }).unref === 'function') {
      (timer as unknown as { unref: () => void }).unref();
    }
  };

  const handleThumbs = (id: string, thumb: 'up' | 'down') => {
    setEntries((prev) =>
      prev.map((e) => (e.id === id ? { ...e, thumbsState: e.thumbsState === thumb ? undefined : thumb } : e)),
    );
  };

  const handleRetry = (entry: TranscriptEntry) => {
    void sendMessage(entry.userMessage);
  };

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
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: colors.bg.canvas }}
    >
      {/* Top App Bar matching frontier AI mobile screenshots */}
      <View
        style={[
          styles.topAppBar,
          { backgroundColor: colors.bg.surface, borderBottomColor: colors.border.subtle },
        ]}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Open drawer"
          style={styles.iconButton}
          onPress={() => {}}
        >
          <Text style={[styles.topBarIcon, { color: colors.text.primary }]}>☰</Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Select session"
          style={styles.sessionTitleContainer}
          onPress={() => setAddModalOpen(true)}
        >
          <Text
            numberOfLines={1}
            style={[styles.sessionTitleText, { color: colors.text.primary }]}
          >
            {selectedProjectId ? `Project: ${selectedProjectId.slice(0, 8)}…` : 'krypton chat'}
          </Text>
          <View style={[styles.liveDot, { backgroundColor: client ? '#10b981' : '#f59e0b' }]} />
        </Pressable>

        <View style={styles.topBarRightActions}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="View session documents"
            style={styles.iconButton}
            onPress={() => {}}
          >
            <Text style={[styles.topBarIcon, { color: colors.text.primary }]}>📄</Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="New session"
            style={styles.iconButton}
            onPress={() => {
              setEntries([]);
              setSelectedProjectId(null);
            }}
          >
            <Text style={[styles.topBarIcon, { color: colors.text.primary }]}>✏️</Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="More options"
            style={styles.iconButton}
            onPress={() => {}}
          >
            <Text style={[styles.topBarIcon, { color: colors.text.primary }]}>⋮</Text>
          </Pressable>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollArea}
        keyboardShouldPersistTaps="handled"
      >
        {/* Hub Connection status */}
        <HubStatusCard />

        {client === null ? (
          <Card role="warning" testID="chat-not-connected">
            <Label strong>Hub not connected</Label>
            <Label tone="secondary">
              Pair or connect with your vibey hub to chat, inspect projects, and answer gates.
            </Label>
            <Button label="Pair with hub" onPress={() => router.push('/pair')} />
          </Card>
        ) : null}

        <Loaded result={result}>
          {({ projects, gates }) => {
            const filteredGates =
              selectedProjectId === null
                ? gates
                : gates.filter((gate) => gate.project_id === selectedProjectId);
            const gateCards = present.gates(filteredGates, Date.now());

            return (
              <>
                {/* Session Project Selector */}
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

                {/* Quick Commands */}
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

                {/* Inline Gates Waiting for Decision */}
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

        {/* Welcome Card if transcript is empty */}
        {entries.length === 0 ? (
          <Card role="info" testID="chat-welcome">
            <Pill role="info">KRYPTON</Pill>
            <Label>
              Welcome to krypton chat. Pick a project session above, tap a quick command, or type `/` in
              the composer (`/projects`, `/status`, `/gates`, `/new`, `/help`).
            </Label>
          </Card>
        ) : null}

        {/* Transcript Entries */}
        {entries.map((entry) => (
          <View key={entry.id} style={styles.turnGroup}>
            {/* User message bubble */}
            <View style={styles.userBubbleContainer}>
              <View
                style={[
                  styles.userBubble,
                  { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
                ]}
                testID={`${entry.id}-user`}
              >
                <Pill role="info">YOU</Pill>
                <Label>{entry.userMessage}</Label>
              </View>
            </View>

            {/* Tool calls */}
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

            {/* Assistant reply with Rich Text & Action Bar */}
            {entry.reply !== undefined ? (
              <View style={styles.assistantResponseContainer} testID={`${entry.id}-reply`}>
                <RichMessageText text={entry.reply} color={colors.text.primary} />

                {/* Action Bar: Copy, Share, Audio/TTS, Thumbs up/down, Retry */}
                <View style={styles.actionBar}>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Copy response"
                    style={styles.actionButton}
                    onPress={() => void handleCopy(entry.id, entry.reply!)}
                  >
                    <Text style={[styles.actionIcon, { color: colors.text.tertiary }]}>
                      {copiedTurnId === entry.id ? '✓' : '⎘'}
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Share response"
                    style={styles.actionButton}
                    onPress={() => void handleShare(entry.reply!)}
                  >
                    <Text style={[styles.actionIcon, { color: colors.text.tertiary }]}>↗</Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Read aloud"
                    style={styles.actionButton}
                    onPress={() => handleTts(entry.id)}
                  >
                    <Text
                      style={[
                        styles.actionIcon,
                        {
                          color:
                            speakingTurnId === entry.id
                              ? colors.accent.default
                              : colors.text.tertiary,
                        },
                      ]}
                    >
                      🔊
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Thumbs up"
                    style={styles.actionButton}
                    onPress={() => handleThumbs(entry.id, 'up')}
                  >
                    <Text
                      style={[
                        styles.actionIcon,
                        {
                          color:
                            entry.thumbsState === 'up'
                              ? colors.accent.default
                              : colors.text.tertiary,
                        },
                      ]}
                    >
                      👍
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Thumbs down"
                    style={styles.actionButton}
                    onPress={() => handleThumbs(entry.id, 'down')}
                  >
                    <Text
                      style={[
                        styles.actionIcon,
                        {
                          color:
                            entry.thumbsState === 'down'
                              ? colors.status.danger
                              : colors.text.tertiary,
                        },
                      ]}
                    >
                      👎
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Retry turn"
                    style={styles.actionButton}
                    onPress={() => handleRetry(entry)}
                  >
                    <Text style={[styles.actionIcon, { color: colors.text.tertiary }]}>↻</Text>
                  </Pressable>
                </View>

                {/* Frontier AI disclaimer */}
                <Text style={[styles.disclaimerText, { color: colors.text.tertiary }]}>
                  krypton is AI and can make mistakes.
                </Text>
              </View>
            ) : null}

            {entry.error !== undefined ? (
              <Notice role="danger">{entry.error}</Notice>
            ) : null}
          </View>
        ))}

        {/* Slash command completion list */}
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
      </ScrollView>

      {/* Floating Bottom Composer matching screenshots */}
      <View
        style={[
          styles.composerWrapper,
          { backgroundColor: colors.bg.canvas, borderTopColor: colors.border.subtle },
        ]}
        testID="chat-composer"
      >
        <View
          style={[
            styles.composerContainer,
            { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
          ]}
        >
          {/* '+' Button for Add to session */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Add to session"
            style={[styles.plusButton, { backgroundColor: colors.bg.canvas }]}
            onPress={() => setAddModalOpen(true)}
          >
            <Text style={[styles.plusIcon, { color: colors.text.primary }]}>+</Text>
          </Pressable>

          {/* Model Pill Selector */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`Model: ${activeModel}`}
            style={[styles.modelPill, { backgroundColor: colors.bg.canvas }]}
            onPress={toggleModel}
          >
            <Text numberOfLines={1} style={[styles.modelPillText, { color: colors.text.primary }]}>
              {activeModel}
            </Text>
          </Pressable>

          {/* Text Input */}
          <TextInput
            accessibilityLabel="Chat message or slash command"
            value={typed}
            onChangeText={setTyped}
            onSubmitEditing={() => void sendMessage(typed)}
            placeholder="Reply to krypton..."
            placeholderTextColor={colors.text.tertiary}
            autoCapitalize="none"
            autoCorrect={false}
            multiline
            style={[styles.textInput, { color: colors.text.primary }]}
          />

          {/* Microphone Icon Button */}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voice input"
            style={styles.composerIconButton}
            onPress={() => {}}
          >
            <Text style={[styles.micIcon, { color: colors.text.tertiary }]}>🎙</Text>
          </Pressable>

          {/* Audio Waveform Circle Button or Send */}
          {typed.trim().length > 0 ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Send"
              disabled={sending}
              style={[
                styles.waveformButton,
                { backgroundColor: colors.accent.default, opacity: sending ? 0.5 : 1 },
              ]}
              onPress={() => void sendMessage(typed)}
            >
              <Text style={{ color: colors.text['on-accent'], fontWeight: '700', fontSize: 13 }}>
                Send
              </Text>
            </Pressable>
          ) : (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Audio mode"
              style={styles.waveformButton}
              onPress={() => {}}
            >
              <Text style={styles.waveformIcon}>ılı</Text>
            </Pressable>
          )}
        </View>
      </View>

      {/* 'Add to session' Bottom Sheet Modal */}
      <AddSessionModal
        visible={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        projects={result.state === 'ready' ? result.value.projects : []}
        selectedProjectId={selectedProjectId}
        onSelectProject={setSelectedProjectId}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  topAppBar: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    borderBottomWidth: 1,
  },
  iconButton: {
    padding: 8,
  },
  topBarIcon: {
    fontSize: 20,
  },
  sessionTitleContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginHorizontal: 8,
  },
  sessionTitleText: {
    fontSize: 16,
    fontWeight: '600',
    flexShrink: 1,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  topBarRightActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scrollArea: {
    padding: 16,
    gap: 12,
    paddingBottom: 90,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    alignItems: 'center',
  },
  turnGroup: {
    gap: 10,
    marginVertical: 4,
  },
  userBubbleContainer: {
    alignItems: 'flex-end',
  },
  userBubble: {
    maxWidth: '85%',
    borderRadius: 18,
    borderWidth: 1,
    padding: 12,
    gap: 6,
  },
  assistantResponseContainer: {
    paddingVertical: 8,
    gap: 8,
  },
  richTextContainer: {
    gap: 8,
  },
  textRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  bulletPoint: {
    fontSize: 16,
    lineHeight: 24,
    marginRight: 4,
  },
  paragraphSpacer: {
    height: 6,
  },
  paragraphText: {
    fontSize: 15,
    lineHeight: 23,
    flex: 1,
    flexWrap: 'wrap',
  },
  inlinePill: {
    fontSize: 13,
    fontWeight: '600',
    borderRadius: 6,
    borderWidth: 1,
    paddingHorizontal: 4,
    paddingVertical: 1,
  },
  actionBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    marginTop: 6,
    paddingHorizontal: 4,
  },
  actionButton: {
    padding: 4,
  },
  actionIcon: {
    fontSize: 16,
  },
  disclaimerText: {
    fontSize: 12,
    marginTop: 2,
    paddingHorizontal: 4,
  },
  completionRow: {
    gap: 2,
    marginVertical: 2,
  },
  composerWrapper: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderTopWidth: 1,
  },
  composerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 28,
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 6,
    gap: 8,
  },
  plusButton: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  plusIcon: {
    fontSize: 20,
    fontWeight: '600',
    lineHeight: 22,
  },
  modelPill: {
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 6,
    maxWidth: 130,
  },
  modelPillText: {
    fontSize: 12,
    fontWeight: '600',
  },
  textInput: {
    flex: 1,
    fontSize: 15,
    paddingVertical: 6,
    maxHeight: 100,
  },
  composerIconButton: {
    padding: 6,
  },
  micIcon: {
    fontSize: 18,
  },
  waveformButton: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  waveformIcon: {
    color: '#000000',
    fontSize: 16,
    fontWeight: '700',
  },
});
