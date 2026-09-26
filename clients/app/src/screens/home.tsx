// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { Link } from 'expo-router';
import { View } from 'react-native';
import { Presenters } from '../core';
import { AtomMark } from '../ui/atom-mark';
import { Card, Label, Loaded, Pill, Screen, useHub } from '../ui/kit';

const present = new Presenters();

export function HomeScreen() {
  const { result, reload } = useHub((client) => client.projects());
  return (
    <Screen title="krypton" subtitle="Every project krypton is running, live." onRefresh={reload}>
      <View style={{ alignItems: 'center', marginVertical: 8 }}>
        <AtomMark size={112} />
      </View>
      <Loaded result={result}>
        {(projects) => {
          const summary = present.home(projects);
          return (
            <>
              <Label strong>{summary.headline}</Label>
              {summary.cards.map((card) => (
                <Card key={card.id} role={card.role} testID={`project-${card.id}`}>
                  <Label strong>{card.name}</Label>
                  <Pill role={card.role}>{card.phase}</Pill>
                  {card.cycle ? <Label tone="secondary">{card.cycle}</Label> : null}
                  {card.openGates > 0 ? (
                    <Link href="/gates">
                      <Label tone="secondary">{`${card.openGates} open gate${card.openGates === 1 ? '' : 's'} →`}</Label>
                    </Link>
                  ) : null}
                </Card>
              ))}
              {summary.cards.length === 0 ? <Label tone="tertiary">No projects yet. Start one with `vibey run` on the host.</Label> : null}
            </>
          );
        }}
      </Loaded>
    </Screen>
  );
}
