// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as LocalAuthentication from 'expo-local-authentication';
import { useState } from 'react';
import { Platform, View } from 'react-native';
import type { GateCard } from '../core';
import { DevicePolicy, Presenters } from '../core';
import { useApp } from '../ui/app-state';
import { Button, Card, Label, Loaded, Notice, Pill, Screen, useHub } from '../ui/kit';

const present = new Presenters();
const policy = new DevicePolicy();

/** Face ID, Touch ID or the passcode before a gate that spends. The web has none: it refuses. */
export async function reverify(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  const result = await LocalAuthentication.authenticateAsync({ promptMessage: 'Confirm an answer that spends money' });
  return result.success;
}

function Gate(props: { readonly gate: GateCard; readonly onDone: () => void; readonly verify: () => Promise<boolean> }) {
  const { client } = useApp();
  const [message, setMessage] = useState<string | null>(null);
  const { gate } = props;
  const choose = async (value: string) => {
    const decision = policy.decide(gate.spends ? 'answer-spend' : 'answer');
    if (decision.allowed && decision.confirm && !(await props.verify())) {
      setMessage(Platform.OS === 'web' ? 'Answer gates that spend from your phone, where it can check it is you.' : 'Not confirmed; nothing was sent.');
      return;
    }
    try {
      if (gate.answerKey === 'host') return;
      setMessage(await client!.answer(gate.id, { mode: gate.answerKey, value }));
      props.onDone();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  };
  return (
    <Card role={gate.spends ? 'ultra' : 'warning'} testID={`gate-${gate.id}`}>
      <Label strong>{gate.title}</Label>
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <Pill role="warning">{gate.due}</Pill>
        {gate.spends ? <Pill role="ultra">Spends · confirm it is you</Pill> : null}
      </View>
      <Label tone="secondary">{gate.prompt}</Label>
      {gate.answerKey !== 'host'
        ? gate.options.map((option) => <Button key={option} label={option} onPress={() => void choose(option)} />)
        : null}
      {gate.answerKey === 'host' || gate.options.length === 0 ? (
        <Label tone="tertiary">Answer this gate on the host: `vibey answer` takes the value it needs.</Label>
      ) : null}
      {message ? <Notice>{message}</Notice> : null}
    </Card>
  );
}

export function GatesScreen(props: { readonly verify?: () => Promise<boolean> }) {
  const { result, reload } = useHub((client) => client.gates());
  return (
    <Screen title="Gates" subtitle="Where vibey waits for you." onRefresh={reload}>
      <Loaded result={result}>
        {(gates) => {
          const cards = present.gates(gates, Date.now());
          return cards.length === 0 ? (
            <Label tone="tertiary">Nothing waits for you.</Label>
          ) : (
            cards.map((gate) => <Gate key={gate.id} gate={gate} onDone={reload} verify={props.verify ?? reverify} />)
          );
        }}
      </Loaded>
    </Screen>
  );
}
