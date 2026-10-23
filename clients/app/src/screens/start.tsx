// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { router } from 'expo-router';
import { useState } from 'react';
import { TextInput } from 'react-native';
import { Presenters } from '../core';
import { useApp } from '../ui/app-state';
import { Button, Card, Label, Notice, Screen } from '../ui/kit';
import { useTheme } from '../ui/theme';

/** Say what to build, and the host does the rest: it makes the folder, starts the project and its worker. */
export function StartScreen() {
  const { client } = useApp();
  const { colors } = useTheme();
  const [name, setName] = useState('');
  const [intake, setIntake] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ readonly text: string; readonly good: boolean } | null>(null);
  const input = { borderWidth: 1, borderColor: colors.border.strong, color: colors.text.primary, borderRadius: 12, padding: 12, fontSize: 16 };

  const start = async () => {
    const problem = Presenters.projectNameProblem(name);
    if (problem !== undefined) return setMessage({ text: problem, good: false });
    if (client === null) return setMessage({ text: 'Pair with a vibey hub first.', good: false });
    setBusy(true);
    try {
      // No folder is sent: the host chooses where a project lives.
      const created = await client.createProject(name.trim(), { repo: '', intake });
      setMessage({
        text: `Started "${created.name}". It will ask you what it needs to know: each question appears under Gates, and krypton tells you when one comes.`,
        good: true,
      });
    } catch (error) {
      setMessage({ text: error instanceof Error ? error.message : String(error), good: false });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen title="Start a project" subtitle="Say what you want built. It asks you the rest.">
      <Card role="info">
        <Label strong>Name</Label>
        <TextInput accessibilityLabel="Project name" style={input} autoCapitalize="none" autoCorrect={false} value={name} onChangeText={setName} placeholder="my-first-app" placeholderTextColor={colors.text.tertiary} />
        <Label strong>What should it build?</Label>
        <Label tone="secondary">In your own words. A sentence is enough: it will ask about anything it needs to know.</Label>
        <TextInput accessibilityLabel="What to build" style={[input, { minHeight: 96, textAlignVertical: 'top' }]} multiline value={intake} onChangeText={setIntake} placeholder="a web page that greets the visitor by name" placeholderTextColor={colors.text.tertiary} />
        <Button label={busy ? 'Starting…' : 'Start'} disabled={busy} onPress={() => void start()} />
      </Card>
      {message ? <Notice role={message.good ? 'success' : 'warning'}>{message.text}</Notice> : null}
      {message?.good ? <Button label="See your projects" kind="quiet" onPress={() => router.replace('/')} /> : null}
    </Screen>
  );
}
