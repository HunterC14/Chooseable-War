from time import time
from sys import stderr
from argparse import ArgumentParser
import tournament_api as api

"""
usage: python -u tournament.py [-h] [-v] [-c COUNT] [-b BOTS [BOTS ...]] [-p]

Runs a Chooseable War tourney with bots

options:
  -h, --help                    show this help message and exit
  -v, --verbose                 send output logs to stdout
  -c, --count, --games COUNT    how many games to run
  -b, --bots BOTS [BOTS ...]    which bots will participate in the tourney
  -p, --progress                display current progress
"""

assert __name__ == "__main__"

# submissions_dir = Path(__file__).parent / "submissions"

parser = ArgumentParser(
    prog="tournament.py",
    description="Runs a Chooseable War tourney with bots"
)

parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-c", "--count", "--games", type=int, default=30_000)
parser.add_argument("-b","--bots", nargs="+", default=[])
parser.add_argument("-p", "--progress", action="store_true")
args = parser.parse_args()
DEBUG = args.verbose
round_count = args.count
playing_bots = args.bots
show_progress = args.progress
if playing_bots == []:
    api.import_bots()
else:
    api.import_bots(playing_bots)
submissions = api.submissions
sub_count = len(submissions)

def overview_print():
    for tid, score in points.items():
        name = submissions[tid].name
        print(f"{name} t#{tid} has {score:,.3f} points ({score/(round_num+1)*100:.2f}%)", file=stderr)

points: dict[int, float] = {i: 0.0 for i in range(sub_count)}
start_time = time()
round_time = 0
last_shown = start_time
if show_progress:
    print("\n"*sub_count,file=stderr)
round_num = 0
try:
    for round_num in range(round_count):
        if DEBUG:
            print(f"Initiating r#{round_num} (0-indexed)")
        round_start = time()
        scores = api.game(13 * 4 // sub_count, list(range(sub_count)), verbose=DEBUG)
        round_time += time()-round_start
        if DEBUG:
            print()
        for gid, incscore in scores.items():
            points[gid] += incscore
        if show_progress:
            if time() - last_shown > 0.01:
                last_shown = time()
                print("\x1b[A"*(sub_count+1),end="",file=stderr)
                print(f"Working round: {round_num+1}", file=stderr)
                overview_print()
                    
except KeyboardInterrupt:
    print(f"\rRan for {time()-start_time:,.1f} sec")
    round_num -= 1
total_time = time() - start_time
rounds_done = round_num + 1
print("Overview:", file=stderr)
print(f"{rounds_done:,}/{round_count:,} rounds", file=stderr)
overview_print()
print(f"Avg. game time: {round_time/rounds_done*1_000_000:.2f} \u03bcs", file=stderr)
print(f"Total elapsed time: {total_time:,.2f} sec", file=stderr)
print(f"Avg. time per round: {total_time/rounds_done*1_000_000:.2f} \u03bcs", file=stderr)