"""Statistics for the study: Wilson intervals, Newcombe differences, loop metrics."""

from __future__ import annotations

import math
from collections import Counter

Z = 1.959963984540054


class Proportions:
    """Wilson score intervals and Newcombe's intervals for differences."""

    def wilson(
        self, k: int, n: int, z: float = Z
    ) -> tuple[float | None, float | None, float | None]:
        if n <= 0:
            return None, None, None
        p = k / n
        z2 = z * z
        centre = (p + z2 / (2 * n)) / (1 + z2 / n)
        half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
        return p, max(0.0, centre - half), min(1.0, centre + half)

    def diff_independent(self, k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
        """Newcombe's hybrid score interval for p1 - p2 (method 10 of Newcombe 1998a)."""
        p1, l1, u1 = self.wilson(k1, n1)
        p2, l2, u2 = self.wilson(k2, n2)
        d = p1 - p2
        return (
            d,
            d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
            d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2),
        )

    def diff_paired(self, a: int, b: int, c: int, d: int) -> tuple[float, float, float]:
        """Newcombe's (1998b) method 10 for paired p1 - p2, where
        a = both succeed, b = first only, c = second only, d = neither."""
        n = a + b + c + d
        p1, l1, u1 = self.wilson(a + b, n)
        p2, l2, u2 = self.wilson(a + c, n)
        theta = (b - c) / n
        denominator = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
        if denominator == 0:
            phi = 0.0
        else:
            ad_bc = a * d - b * c
            phi = (max(ad_bc - n / 2, 0) if ad_bc > 0 else ad_bc) / denominator
        dl = math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
        du = math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
        return theta, max(-1.0, theta - dl), min(1.0, theta + du)

    def quantile(self, values: list[float], q: float) -> float | None:
        if not values:
            return None
        s = sorted(values)
        pos = (len(s) - 1) * q
        lo, hi = math.floor(pos), math.ceil(pos)
        return s[lo] + (s[hi] - s[lo]) * (pos - lo)


class LoopMetric:
    """Is a reasoning trace going round in circles?"""

    def substring_loop(self, text: str, tail: int = 4000, width: int = 200, times: int = 3) -> bool:
        """PRIOR-ART's guard: some ≥`width`-char substring repeats ≥`times` in the last `tail` chars."""
        s = text[-tail:]
        if len(s) < width * times:
            return False
        for start in range(0, len(s) - width + 1, 25):
            if s.count(s[start : start + width]) >= times:
                return True
        return False

    def repeated_ngram_fraction(self, text: str, n: int = 8) -> float | None:
        """Share of word 8-grams that already occurred earlier in the trace."""
        words = text.split()
        grams = [tuple(words[i : i + n]) for i in range(max(0, len(words) - n + 1))]
        if not grams:
            return None
        seen: Counter[tuple[str, ...]] = Counter()
        repeats = 0
        for gram in grams:
            if seen[gram]:
                repeats += 1
            seen[gram] += 1
        return repeats / len(grams)


PROPORTIONS = Proportions()
LOOPS = LoopMetric()

if __name__ == "__main__":
    print(PROPORTIONS.wilson(0, 14), PROPORTIONS.wilson(48, 48), PROPORTIONS.wilson(12, 12))
    print(PROPORTIONS.diff_paired(15, 3, 2, 7), PROPORTIONS.diff_independent(10, 27, 5, 27))
    print(
        LOOPS.substring_loop("abc " * 2000), LOOPS.repeated_ngram_fraction("a b c d e f g h " * 10)
    )
