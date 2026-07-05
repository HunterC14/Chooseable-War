#!/usr/bin/env python3
"""Round-robin grid runner for Chooseable War bots.

Runs every pair of bots head-to-head via tournament_api (in-process, spread
over a pool of worker processes) in chunks, redrawing an ANSI-colored
win-rate grid after each pass until the total count per pair is reached.
Chunk size is dynamic by default: each pair starts with a single game and the
chunk is recalibrated after every run to target ~150ms per run, so fast pairs
batch thousands of games while slow ones update every game or two (a fixed
size can be forced with --chunk).

LEGEND: each cell is the percentage of games the ROW bot wins against the
COLUMN bot (draws count fractionally). Green = above par, red = below, where
par is an equal share (50% for plain pairs, 100/players with extras). The
right column is the bot's average thinking time per game in ms.

Extra bots (--extra) join every game without appearing in the grid: with
extras minbot & randobot and grid bots maxbot tophalfbot lowbot, the runs are
(minbot randobot maxbot tophalfbot), (minbot randobot maxbot lowbot), and
(minbot randobot tophalfbot lowbot). With more than 2 bots per game the grid
is no longer symmetric: cells (a, b) and (b, a) need not sum to 100% since
extras also win games.

Rows/columns are ordered by each bot's measured propensity to play high (the
'# highness:' comment maintained by highness.py), minbot first, maxbot last.

Usage:
  python3 grid.py                       # all bots, 10,000 games per pair
  python3 grid.py -c 2000               # change total games per pair
  python3 grid.py -b lowbot maxbot ...  # only these bots
  python3 grid.py -x minbot randobot    # extra bots in every game
  python3 grid.py --chunk 500           # games per pair per display update
"""

import re
import sys
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations_with_replacement
from os import cpu_count
from pathlib import Path
from time import monotonic

import tournament_api as api

HERE = Path(__file__).parent
TARGET_SECS = 0.150  # dynamic chunk sizing aims for one run per pair in ~150ms
# Standardized comment written by highness.py into each bot file.
HIGHNESS_RE = re.compile(r"^#\s*highness:\s*([0-9.]+)", re.MULTILINE)


def available_bots() -> list[str]:
    subs = HERE / "submissions"
    return sorted(p.stem for p in subs.iterdir()
                  if p.suffix == ".py" and p.name[0].isalnum())


def highness(bot: str) -> float:
    """The bot's measured propensity to play high (0.0 lowest .. 1.0 highest),
    from the '# highness:' comment maintained by highness.py; inf if absent."""
    m = HIGHNESS_RE.search((HERE / "submissions" / f"{bot}.py").read_text())
    return float(m.group(1)) if m else float("inf")


# Per worker process: seat-name tuple -> persistent Player instances, so bots
# are imported once per pair per process rather than once per chunk.
_players_cache: dict[tuple[str, ...], list] = {}


def run_games(seats: tuple[str, ...], n: int) -> tuple[float, float, float, float, float]:
    """Run `n` games between `seats` = (extras..., a, b) (possibly a == b) in
    this worker process; return the points and elapsed bot-seconds of a and b
    (seats -2 and -1), plus the wall-clock seconds for the whole run."""
    start = monotonic()
    players = _players_cache.get(seats)
    if players is None:
        players = _players_cache[seats] = api.import_bots(list(seats))
    e = len(seats) - 2
    pa, pb = players[e], players[e + 1]
    pts_a = pts_b = 0.0
    sec_a, sec_b = pa.elapsed_time, pb.elapsed_time
    deal = 13 * 4 // len(players)
    for _ in range(n):
        scores = api.game(deal, players)
        pts_a += scores.get(e, 0.0)
        pts_b += scores.get(e + 1, 0.0)
    return (pts_a, pts_b, pa.elapsed_time - sec_a, pb.elapsed_time - sec_b,
            monotonic() - start)


def heat_color(pct: float, par: float = 50) -> int:
    """ANSI 256-color heatmap: 0% red -> par yellow -> 100% green."""
    if pct <= par:
        r, g = 5, round(pct / par * 5)
    else:
        r, g = round((100 - pct) / (100 - par) * 5), 5
    return 16 + 36 * r + 6 * g


def render(bots: list[str], extra: list[str], points: dict[tuple[str, str], float],
           games: dict[tuple[str, str], int], secs: dict[str, float],
           seat_games: dict[str, int], done: int, total: int) -> str:
    n = len(bots)
    par = 100 / (len(extra) + 2)
    name_w = max(len(b) for b in bots) + 4
    cell_w = max(5, len(str(n)) + 1)
    out = [f"Chooseable War round-robin  |  {len(extra) + 2}-player games  |  "
           f"{done:,} / {total:,} games per pair (slowest pair)",
           "Legend: cell = ROW bot's win % in games against the COLUMN bot "
           f"(draws count fractionally). Green = above par ({par:.3g}%).",
           f"Diagonal = self-play (first seat's win rate; ~{par:.3g}% means no seat bias). "
           "Right column = bot's avg time per game (ms)."]
    if extra:
        out.append(f"Extra bots in every game (not shown): {', '.join(extra)}. "
                   "Grid is not symmetric: extras also win games.")
    out.append("")
    ms = {b: (f"{round(secs[b] / seat_games[b] * 1000)}" if seat_games[b] else "?")
          for b in bots}
    ms_w = max(len("ms/game"), *(len(v) for v in ms.values())) + 2
    header = (" " * name_w + "".join(f"{i + 1:>{cell_w}}" for i in range(n))
              + f"{'ms/game':>{ms_w}}")
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
        out.append(line + f"{ms[row]:>{ms_w}}")
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
    # Order rows/columns by propensity to play high (minbot first, maxbot
    # last); bots without a highness comment sort last, ties break by name.
    bots = sorted(bots, key=lambda b: (highness(b), b))

    pairs = list(combinations_with_replacement(bots, 2))  # includes self-play
    points = {(a, b): 0.0 for a, b in pairs} | {(b, a): 0.0 for a, b in pairs}
    games = dict.fromkeys(points, 0)
    # Per-pair chunk size: start at 1 (or the fixed --chunk) and, when
    # dynamic, recalibrate after every run so a run takes ~TARGET_SECS.
    chunk = dict.fromkeys(pairs, args.chunk or 1)
    done = dict.fromkeys(pairs, 0)
    # Per-bot elapsed thinking time and seat-games played (self-play counts
    # both seats), for the ms/game column.
    secs = dict.fromkeys(bots, 0.0)
    seat_games = dict.fromkeys(bots, 0)

    # Redraw on the alternate screen buffer (like less/vim) so scrollback
    # isn't littered with stale copies of the table; the final table is
    # printed once on the normal screen afterwards (also on Ctrl-C).
    alt = sys.stdout.isatty()
    grid = ""
    if alt:
        print("\x1b[?1049h", end="")
    try:
        with ProcessPoolExecutor(max_workers=cpu_count() or 4) as pool:
            while any(d < args.count for d in done.values()):
                active = [p for p in pairs if done[p] < args.count]
                ns = [min(chunk[p], args.count - done[p]) for p in active]
                seat_tuples = [(*args.extra, a, b) for a, b in active]
                for (a, b), n, result in zip(active, ns,
                                             pool.map(run_games, seat_tuples, ns)):
                    pts_a, pts_b, sec_a, sec_b, elapsed = result
                    points[(a, b)] += pts_a  # for a == b: first seat's points
                    if a != b:
                        points[(b, a)] += pts_b
                        games[(b, a)] += n
                    games[(a, b)] += n
                    done[(a, b)] += n
                    secs[a] += sec_a  # for a == b: both seats accumulate on
                    secs[b] += sec_b  # the same bot, over 2n seat-games
                    seat_games[a] += n
                    seat_games[b] += n
                    if args.chunk is None:
                        # Aim for TARGET_SECS per run; growth capped at 10x
                        # per step (1-game timings are noisy and the first run
                        # per pair per worker includes bot import).
                        est = round(n * TARGET_SECS / max(elapsed, 1e-3))
                        chunk[(a, b)] = max(1, min(est, 10 * n))
                grid = render(bots, args.extra, points, games, secs, seat_games,
                              min(done.values()), args.count)
                print(("\x1b[H\x1b[2J" if alt else "") + grid, flush=True)
    finally:
        if alt:
            # Leave the alternate screen, then print the last table once so
            # it survives in the normal buffer.
            print("\x1b[?1049l", end="")
            if grid:
                print(grid, flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted — grid above shows progress so far", file=sys.stderr)
        sys.exit(130)
