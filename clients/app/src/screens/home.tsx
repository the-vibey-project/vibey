// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { Link, router } from 'expo-router';
import { View } from 'react-native';
import { Presenters } from '../core';
import { AtomMark } from '../ui/atom-mark';
import { Button, Card, HubStatusCard, Label, Loaded, Pill, Screen, useHub } from '../ui/kit';
import { ProjectActions } from './project-actions';

const present = new Presenters();

export function HomeScreen() {
  const { result, reload } = useHub((client) => client.projects());
  return (
    <Screen title="krypton" subtitle="Every project krypton is running, live." onRefresh={reload}>
      <View style={{ alignItems: 'center', marginVertical: 8 }}>
        <AtomMark size={112} />
      </View>
      <HubStatusCard />
      <Button label="Start a project" onPress={() => router.push('/start')} />
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
                  <ProjectActions card={card} onDone={reload} />
                </Card>
              ))}
              {summary.emptyNote === '' ? null : <Label tone="tertiary">{summary.emptyNote}</Label>}
            </>
          );
        }}
      </Loaded>
    </Screen>
  );
}
