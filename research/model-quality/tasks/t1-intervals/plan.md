Create intervals.py in the current directory defining merge_intervals(items: list[tuple[int, int]]) -> list[tuple[int, int]].

Each item is a closed interval (start, end) of integers. The function returns the smallest list of
disjoint intervals covering exactly the same points, sorted by start.
- Input may be unsorted and may contain duplicates or intervals contained in others.
- Intervals that overlap or merely touch are merged: (1, 3) and (3, 5) become (1, 5). Intervals
  that are only adjacent integers but do not share a point, such as (1, 2) and (3, 4), stay separate.
- An empty list returns an empty list.
- A single point interval such as (4, 4) is valid. If any item has start greater than end, raise
  ValueError.
- The input list must not be modified.

Example: merge_intervals([(8, 10), (1, 3), (2, 6), (15, 18), (17, 20)]) returns
[(1, 6), (8, 10), (15, 20)].
Quickly check a few cases yourself before finishing.
