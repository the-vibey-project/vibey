// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Krypton's mark, the Kr-84 atom: a nucleus of 36 protons and 48 neutrons, and electron
 * shells of 2, 8, 18 and 8, drawn in the palette's violet, cyan and mint
 * (`design/identity/atom.svg` is the master). The shells turn slowly unless motion is reduced.
 */
import { useEffect, useRef } from 'react';
import { AccessibilityInfo, Animated, Easing } from 'react-native';
import Svg, { Circle, G } from 'react-native-svg';

export const SHELLS: readonly number[] = [2, 8, 18, 8];
export const PROTONS = 36;
export const NEUTRONS = 48;

const VIOLET = '#9d7bff';
const CYAN = '#57dcff';
const MINT = '#75f0c2';

/** Nucleons packed on a sunflower spiral, protons and neutrons interleaved. */
function nucleons(): { x: number; y: number; proton: boolean }[] {
  const total = PROTONS + NEUTRONS;
  const golden = Math.PI * (3 - Math.sqrt(5));
  return Array.from({ length: total }, (_, index) => {
    const r = 11 * Math.sqrt((index + 0.5) / total);
    return { x: 50 + r * Math.cos(index * golden), y: 50 + r * Math.sin(index * golden), proton: index % 7 < 3 };
  });
}

const NUCLEUS = nucleons();

export function AtomMark(props: { readonly size?: number; readonly animated?: boolean }) {
  const size = props.size ?? 96;
  const spin = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (props.animated === false) return;
    let loop: Animated.CompositeAnimation | undefined;
    void AccessibilityInfo.isReduceMotionEnabled().then((reduced) => {
      if (reduced) return;
      loop = Animated.loop(Animated.timing(spin, { toValue: 1, duration: 24000, easing: Easing.linear, useNativeDriver: true }));
      loop.start();
    });
    return () => loop?.stop();
  }, [spin, props.animated]);
  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  return (
    <Animated.View accessibilityRole="image" accessibilityLabel="Krypton" style={{ width: size, height: size, transform: [{ rotate }] }}>
      <Svg width={size} height={size} viewBox="0 0 100 100">
        {SHELLS.map((count, shell) => {
          const r = 18 + shell * 9;
          return (
            <G key={`shell-${shell}`}>
              <Circle cx={50} cy={50} r={r} stroke={shell % 2 === 0 ? VIOLET : CYAN} strokeOpacity={0.45} strokeWidth={0.8} fill="none" />
              {Array.from({ length: count }, (_, index) => {
                const angle = (index / count) * 2 * Math.PI + shell * 0.4;
                return <Circle key={`e-${shell}-${index}`} cx={50 + r * Math.cos(angle)} cy={50 + r * Math.sin(angle)} r={1.4} fill={MINT} />;
              })}
            </G>
          );
        })}
        {NUCLEUS.map((n, index) => (
          <Circle key={`n-${index}`} cx={n.x} cy={n.y} r={1.9} fill={n.proton ? VIOLET : CYAN} />
        ))}
      </Svg>
    </Animated.View>
  );
}
