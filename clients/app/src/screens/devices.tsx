// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { router } from 'expo-router';
import { useApp } from '../ui/app-state';
import { Button, Card, Label, Notice, Screen } from '../ui/kit';

export function DevicesScreen() {
  const { connection, forget } = useApp();
  return (
    <Screen title="Devices" subtitle="This device and the hub it is paired with.">
      <Card role="info">
        <Label strong>This device</Label>
        <Label tone="secondary">{connection ? `Connected to ${connection.baseUrl}` : 'Not connected.'}</Label>
        <Button
          label="Forget this hub"
          kind="danger"
          onPress={() => void forget().then(() => router.replace('/pair'))}
        />
      </Card>
      <Notice>Seeing and revoking other paired devices arrives with the hub's pairing routes. On the host, revocation is one command and immediate.</Notice>
    </Screen>
  );
}
