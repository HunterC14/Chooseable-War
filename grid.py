#!/usr/bin/env python3
"""Round-robin grid runner for Chooseable War bots.

Runs every pair of bots head-to-head via tournament.py in chunks, redrawing
an ANSI-colored win-rate grid after each pass until the total count per pair
is reached. Chunk size is dynamic by default: each pair starts with a single
game and the chunk is recalibrated after every run to target ~150ms per run,
so fast pairs batch thousands of games while slow ones update every game or
two (a fixed size can be forced with --chunk).

LEGEND: each cell is the percentage of games the ROW bot wins against the
COLUMN bot (draws count fractionally). Green = above par, red = below, where
par is an equal share (50% for plain pairs, 100/players with extras).

Extra bots (--extra) join every game without appearing in the grid: with
extras minbot & randobot and grid bots maxbot tophalfbot lowbot, the runs are
(minbot randobot maxbot tophalfbot), (minbot randobot maxbot lowbot), and
(minbot randobot tophalfbot lowbot). With more than 2 bots per game the grid
is no longer symmetric: cells (a, b) and (b, a) need not sum to 100% since
extras also win games.

Usage:
  python3 grid.py                       # all bots, 10,000 games per pair
  python3 grid.py -c 2000               # change total games per pair
  python3 grid.py -b lowbot maxbot ...  # only these bots
  python3 grid.py -x minbot randobot    # extra bots in every game
  python3 grid.py --chunk 500           # games per pair per display update
"""

import re
import subprocess
import sys
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations_with_replacement
from os import cpu_count
from pathlib import Path
from time import monotonic

HERE = Path(__file__).parent
TARGET_SECS = 0.150  # dynamic chunk sizing aims for one run per pair in ~150ms
TOURNAMENT = HERE / "tournament.py"
# Parse by t#id, not name: in self-play both entries share the bot's name.
RESULT_RE = re.compile(r"^\S+ t#(\d+) has ([\d,.]+) points", re.MULTILINE)


def available_bots() -> list[str]:
    subs = HERE / "submissions"
    return sorted(p.stem for p in subs.iterdir()
                  if p.suffix == ".py" and p.name[0].isalnum())


def run_pair(a: str, b: str, count: int, extra: list[str]) -> tuple[float, float]:
    """Run `count` games of a vs b (possibly a == b) with the extra bots also
    seated; return the points of a and b (seats len(extra) and len(extra)+1,
    matching the -b argument order)."""
    e = len(extra)
    proc = subprocess.run(
        [sys.executable, str(TOURNAMENT), "-c", str(count), "-b", *extra, a, b],
        capture_output=True, text=True, cwd=HERE)
    found = {int(m.group(1)): float(m.group(2).replace(",", ""))
             for m in RESULT_RE.finditer(proc.stdout + proc.stderr)}
    if not {e, e + 1} <= set(found):
        sys.exit(f"unexpected output for {a} vs {b} (exit {proc.returncode}):\n"
                 f"{proc.stdout}{proc.stderr}")
    return found[e], found[e + 1]


def heat_color(pct: float, par: float = 50) -> int:
    """ANSI 256-color heatmap: 0% red -> par yellow -> 100% green."""
    if pct <= par:
        r, g = 5, round(pct / par * 5)
    else:
        r, g = round((100 - pct) / (100 - par) * 5), 5
    return 16 + 36 * r + 6 * g


def render(bots: list[str], extra: list[str], points: dict[tuple[str, str], float],
           games: dict[tuple[str, str], int], done: int, total: int) -> str:
    n = len(bots)
    par = 100 / (len(extra) + 2)
    name_w = max(len(b) for b in bots) + 4
    cell_w = max(5, len(str(n)) + 1)
    out = [f"Chooseable War round-robin  |  {done:,} / {total:,} games per pair (slowest pair)",
           "Legend: cell = ROW bot's win % in games against the COLUMN bot "
           f"(draws count fractionally). Green = above par ({par:.3g}%).",
           f"Diagonal = self-play (first seat's win rate; ~{par:.3g}% means no seat bias)."]
    if extra:
        out.append(f"Extra bots in every game (not shown): {', '.join(extra)}. "
                   "Grid is not symmetric: extras also win games.")
    out.append("")
    header = " " * name_w + "".join(f"{i + 1:>{cell_w}}" for i in range(n))
    out.append(header)
    for i, row in enumerate(bots):
        line = f"{i + 1:>2}. {row:<{name_w - 4}}"
        for j, col in enumerate(bots):
            g = games[(row, col)]
            if g == 0:
                line += f"{'?':>{cell_w}}"
                continue
            pct = points[(row, col)] / g * 100
            cell = f"{round(pct):>{cell_w - 1}}%"
            line += f"\x1b[38;5;{heat_color(pct, par)}m{cell}\x1b[0m"
        out.append(line)
    return "\n".join(out)


def main():
    parser = ArgumentParser(description="Run all bots against each other and "
                            "display a win-rate grid.")
    parser.add_argument("-c", "--count", type=int, default=10_000,
                        help="total games per pair (default 10,000)")
    parser.add_argument("-b", "--bots", nargs="+", default=None,
                        help="bots to include (default: all in submissions/)")
    parser.add_argument("-x", "--extra", nargs="+", default=[],
                        help="extra bots seated in every game but not shown "
                             "in the grid (makes the grid asymmetric)")
    parser.add_argument("--chunk", type=int, default=None,
                        help="fixed games per pair between display updates "
                             "(default: dynamic, calibrated per pair to "
                             f"~{round(TARGET_SECS * 1000)}ms per run)")
    args = parser.parse_args()

    all_bots = available_bots()
    bots = args.bots or all_bots
    unknown = [b for b in bots + args.extra if b not in all_bots]
    if unknown:
        sys.exit(f"unknown bot(s): {', '.join(unknown)}\navailable: {', '.join(all_bots)}")
    if len(bots) < 2:
        sys.exit("need at least 2 grid bots")

    pairs = list(combinations_with_replacement(bots, 2))  # includes self-play
    points = {(a, b): 0.0 for a, b in pairs} | {(b, a): 0.0 for a, b in pairs}
    games = dict.fromkeys(points, 0)
    # Per-pair chunk size: start at 1 (or the fixed --chunk) and, when
    # dynamic, recalibrate after every run so a run takes ~TARGET_SECS.
    chunk = dict.fromkeys(pairs, args.chunk or 1)
    done = dict.fromkeys(pairs, 0)

    def run_chunk(pair):
        n = min(chunk[pair], args.count - done[pair])
        start = monotonic()
        result = run_pair(*pair, n, args.extra)
        return result, n, monotonic() - start

    while any(d < args.count for d in done.values()):
        active = [p for p in pairs if done[p] < args.count]
        with ThreadPoolExecutor(max_workers=cpu_count() or 4) as pool:
            for (a, b), (result, n, elapsed) in zip(active, pool.map(run_chunk, active)):
                pts_a, pts_b = result
                points[(a, b)] += pts_a  # for a == b: first seat's points
                if a != b:
                    points[(b, a)] += pts_b
                    games[(b, a)] += n
                games[(a, b)] += n
                done[(a, b)] += n
                if args.chunk is None:
                    # Aim for TARGET_SECS per run; growth capped at 10x per
                    # step (1-game timings are noisy and include process
                    # startup). If one game already exceeds the target, the
                    # estimate stays at 1.
                    est = round(n * TARGET_SECS / max(elapsed, 1e-3))
                    chunk[(a, b)] = max(1, min(est, 10 * n))
        print("\x1b[H\x1b[2J" + render(bots, args.extra, points, games,
                                       min(done.values()), args.count),
              flush=True)
    print()


if __name__ == "__main__":
    main()
