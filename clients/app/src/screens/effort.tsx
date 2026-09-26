// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { CatalogueParser } from '@vibey/core';
import { useState } from 'react';
import type { Effort } from '@vibey/core';
import { DevicePolicy } from '../core';
import { Button, Card, Label, Loaded, Notice, Pill, Screen, useHub } from '../ui/kit';

const policy = new DevicePolicy();

export function EffortScreen() {
  const { result } = useHub(async (client) => {
    const [catalogue, budgets] = await Promise.all([client.loops().then((raw) => new CatalogueParser().parse(raw)), client.budgets()]);
    return { catalogue, capDeclared: budgets.some((budget) => budget.caps.max_cycle_dollars !== null) };
  }, 0);
  const [chosen, setChosen] = useState<Effort | null>(null);
  return (
    <Screen title="Loops & Effort" subtitle="Which loop runs, and how hard it tries.">
      <Loaded result={result}>
        {({ catalogue, capDeclared }) => (
          <>
            {catalogue.loops.map((loop) => (
              <Card key={loop.loop} role={loop.tier === 'local' ? 'success' : 'info'}>
                <Label strong>{loop.loop}</Label>
                <Pill role={loop.tier === 'local' ? 'success' : 'info'}>{loop.tier === 'local' ? 'sovereign' : 'paid · declared on the host'}</Pill>
                <Label tone="secondary">{loop.engines.map((engine) => engine.engine_id).join(' · ') || 'no engine installed'}</Label>
              </Card>
            ))}
            <Label strong>Effort</Label>
            {policy.effortOptions(capDeclared).map((option) => (
              <Card key={option.effort} role={option.effort === 'ULTRA' ? 'ultra' : undefined} testID={`effort-${option.effort}`}>
                <Button
                  label={chosen === option.effort ? `✓ ${option.label}` : option.label}
                  kind={chosen === option.effort ? 'primary' : 'quiet'}
                  disabled={!option.selectable}
                  onPress={() => setChosen(option.effort)}
                />
                <Label tone="secondary">{option.detail}</Label>
              </Card>
            ))}
            <Notice>The hub has no route to start a run yet; the effort you pick here is what the next start will use.</Notice>
          </>
        )}
      </Loaded>
    </Screen>
  );
}
