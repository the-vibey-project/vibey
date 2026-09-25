// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { CameraView, useCameraPermissions } from 'expo-camera';
import { router } from 'expo-router';
import { useState } from 'react';
import { Platform, TextInput, View } from 'react-native';
import { HubClient, Pairing, PairingExchange } from '../core';
import { useApp } from '../ui/app-state';
import { AtomMark } from '../ui/atom-mark';
import { Button, Card, Label, Notice, Screen } from '../ui/kit';
import { useTheme } from '../ui/theme';

const pairing = new Pairing();

export function PairScreen() {
  const { connect } = useApp();
  const { colors } = useTheme();
  const [scanning, setScanning] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();
  const [code, setCode] = useState('');
  const [address, setAddress] = useState(Platform.OS === 'web' && typeof window !== 'undefined' ? window.location.origin : '');
  const [token, setToken] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const input = { borderWidth: 1, borderColor: colors.border.strong, color: colors.text.primary, borderRadius: 12, padding: 12, fontSize: 16 };

  const exchange = async (text: string) => {
    setScanning(false);
    const parsed = pairing.parseQr(text);
    if (!parsed.ok) return setMessage(parsed.reason);
    await new PairingExchange().exchange(parsed.offer).catch((error: Error) => setMessage(error.message));
  };

  const withCode = async () => {
    const normal = pairing.normaliseCode(code);
    if (typeof normal !== 'string') return setMessage(normal.error);
    setMessage(PairingExchange.NOT_YET);
  };

  const withToken = async () => {
    const baseUrl = HubClient.normaliseBaseUrl(address);
    if (typeof baseUrl !== 'string') return setMessage(baseUrl.error);
    if (token.trim() === '') return setMessage("Paste the content of the hub's token file.");
    try {
      await connect({ baseUrl, token: token.trim() });
    } catch (error) {
      return setMessage(error instanceof Error ? error.message : String(error));
    }
    router.replace('/');
  };

  return (
    <Screen title="Welcome to Krypton" subtitle="Pair once with the vibey hub on your network. Being on the same Wi-Fi proves nothing; the code does.">
      <View style={{ alignItems: 'center', marginVertical: 12 }}>
        <AtomMark size={160} />
      </View>
      <Card role="info">
        <Label strong>Scan the QR code</Label>
        {scanning && permission?.granted ? (
          <CameraView style={{ height: 280, borderRadius: 16 }} barcodeScannerSettings={{ barcodeTypes: ['qr'] }} onBarcodeScanned={({ data }) => void exchange(data)} />
        ) : (
          <Button label="Scan" onPress={() => void (permission?.granted ? setScanning(true) : requestPermission().then((p) => setScanning(p.granted)))} />
        )}
      </Card>
      <Card role="info">
        <Label strong>Type the 6-digit code</Label>
        <TextInput accessibilityLabel="Pairing code" style={input} keyboardType="number-pad" maxLength={7} value={code} onChangeText={setCode} placeholder="123 456" placeholderTextColor={colors.text.tertiary} />
        <Button label="Pair" onPress={() => void withCode()} />
      </Card>
      <Card role="success">
        <Label strong>Connect with a host token</Label>
        <Label tone="secondary">Works today: the hub's address and the content of its token file.</Label>
        <TextInput accessibilityLabel="Hub address" style={input} autoCapitalize="none" value={address} onChangeText={setAddress} placeholder="http://127.0.0.1:8765" placeholderTextColor={colors.text.tertiary} />
        <TextInput accessibilityLabel="Host token" style={input} autoCapitalize="none" secureTextEntry value={token} onChangeText={setToken} placeholder="token" placeholderTextColor={colors.text.tertiary} />
        <Button label="Connect" onPress={() => void withToken()} />
      </Card>
      {message ? <Notice role="warning">{message}</Notice> : null}
    </Screen>
  );
}
