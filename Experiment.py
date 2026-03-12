"""
Experiment.py — enumerate card × card × start_score × start_score configs
and run MinimaxAgent vs MinimaxAgent for each config.

Usage:
    python Experiment.py                          # depth=4, 1 game/config
    python Experiment.py --depth 3 --games 2      # faster test
    python Experiment.py --sample 20              # random 20 configs only
    python Experiment.py --workers 4              # parallel with 4 processes
"""

import sys
import os
import argparse
import csv
import time
import copy
import random
import itertools
from typing import Optional
from multiprocessing import Pool

# ── Headless mock: must happen BEFORE importing minimax_agent ─────────────────
# minimax_agent.py has `from gui_wrapper import ZombieEnvGui` at module scope,
# which triggers pygame. We block that with a lightweight mock.
from unittest.mock import MagicMock

def _install_headless_mocks():
    """Install pygame / gui_wrapper mocks so imports don't need a display."""
    if 'pygame' not in sys.modules:
        sys.modules['pygame'] = MagicMock()
    if 'gui_wrapper' not in sys.modules:
        sys.modules['gui_wrapper'] = MagicMock()
        sys.modules['gui_wrapper'].ZombieEnvGui = MagicMock()

_install_headless_mocks()

from Zombie_env import ZombieEnv, Player, Card
from minimax_agent import MinimaxAgent

# All 10 card values
ALL_CARDS = list(Card)           # Card.NONE … Card.DOUBLE_REVIVE
START_SCORES = [0, 1, 2, 3]     # starting score for each player

OUTPUT_CSV = "experiment_results.csv"
CSV_FIELDNAMES = [
    "red_card", "blue_card",
    "red_start_score", "blue_start_score",
    "depth", "game_idx",
    "winner",
    "turns",
    "final_red_score", "final_blue_score",
]


# ── single-game runner (top-level so it's picklable for multiprocessing) ──────

def _run_single_game(args):
    """
    Run one game with MinimaxAgent vs MinimaxAgent.

    args = (red_card, blue_card, red_start, blue_start, depth, max_turns, game_idx)
    Returns a dict matching CSV_FIELDNAMES.
    """
    _install_headless_mocks()   # re-install in worker process (spawn)

    red_card, blue_card, red_start, blue_start, depth, max_turns, game_idx = args

    env = ZombieEnv(red_card=red_card, blue_card=blue_card)
    env.reset()
    # Set starting scores directly after reset
    env.scores[Player.RED]  = red_start
    env.scores[Player.BLUE] = blue_start

    agent_red  = MinimaxAgent(Player.RED,  max_depth=depth, verbose=False)
    agent_blue = MinimaxAgent(Player.BLUE, max_depth=depth, verbose=False)
    agents = {Player.RED: agent_red, Player.BLUE: agent_blue}

    done   = False
    turns  = 0
    winner = None

    while not done and turns < max_turns:
        agent  = agents[env.current_player]
        action = agent.get_action(env)
        if action is None:
            break
        _, _, done, info = env.step(action)
        turns += 1

        if done:
            # Determine winner by score
            rs = env.scores[Player.RED]
            bs = env.scores[Player.BLUE]
            # Check win condition (mirrors Zombie_env logic)
            win3_red  = (env.cards[Player.RED]  == Card.WIN_AT_5 and rs == 5)
            win3_blue = (env.cards[Player.BLUE] == Card.WIN_AT_5 and bs == 5)
            if rs >= env.win_score or win3_red:
                winner = "RED"
            elif bs >= env.win_score or win3_blue:
                winner = "BLUE"
            else:
                winner = "RED" if rs > bs else ("BLUE" if bs > rs else "DRAW")

    if winner is None:
        rs = env.scores[Player.RED]
        bs = env.scores[Player.BLUE]
        winner = "RED" if rs > bs else ("BLUE" if bs > rs else "DRAW")

    return {
        "red_card":         red_card.name,
        "blue_card":        blue_card.name,
        "red_start_score":  red_start,
        "blue_start_score": blue_start,
        "depth":            depth,
        "game_idx":         game_idx,
        "winner":           winner,
        "turns":            turns,
        "final_red_score":  env.scores[Player.RED],
        "final_blue_score": env.scores[Player.BLUE],
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_configs(depth, games, sample):
    """Return list of arg-tuples for all (or sampled) configs."""
    base = []
    for rc, bc in itertools.product(ALL_CARDS, ALL_CARDS):
        for rs, bs in itertools.product(START_SCORES, START_SCORES):
            for g in range(games):
                base.append((rc, bc, rs, bs, depth, 500, g))
    if sample is not None:
        random.shuffle(base)
        base = base[:sample]
    return base


def _load_done_keys(path):
    """Return set of (red_card, blue_card, red_start, blue_start, game_idx) already written."""
    done = set()
    if not os.path.exists(path):
        return done
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            done.add((row["red_card"], row["blue_card"],
                      int(row["red_start_score"]), int(row["blue_start_score"]),
                      int(row["game_idx"])))
    return done


def _print_summary(path):
    """Print a short win-rate summary from the CSV."""
    rows = []
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return

    total  = len(rows)
    red_w  = sum(1 for r in rows if r["winner"] == "RED")
    blue_w = sum(1 for r in rows if r["winner"] == "BLUE")
    draw   = total - red_w - blue_w

    print("\n" + "="*60)
    print(f"  Total games : {total}")
    print(f"  RED  wins   : {red_w} ({100*red_w/total:.1f}%)")
    print(f"  BLUE wins   : {blue_w} ({100*blue_w/total:.1f}%)")
    print(f"  Draws       : {draw}")

    # Per red-card win rate
    from collections import defaultdict
    rc_wins = defaultdict(lambda: [0, 0])   # [red_wins, total]
    for r in rows:
        rc_wins[r["red_card"]][1] += 1
        if r["winner"] == "RED":
            rc_wins[r["red_card"]][0] += 1

    print("\n  RED win-rate by red_card:")
    for card in sorted(rc_wins):
        w, t = rc_wins[card]
        print(f"    {card:<20s}  {w}/{t}  ({100*w/t:.1f}%)")

    print("="*60)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Zombie game card×score experiment")
    parser.add_argument("--depth",     type=int, default=4,          help="Minimax search depth")
    parser.add_argument("--games",     type=int, default=1,          help="Games per config")
    parser.add_argument("--workers",   type=int, default=1,          help="Parallel workers (1 = serial)")
    parser.add_argument("--max-turns", type=int, default=500,        help="Max turns per game")
    parser.add_argument("--output",    type=str, default=OUTPUT_CSV, help="Output CSV path")
    parser.add_argument("--sample",    type=int, default=None,       help="Random sample N configs")
    args = parser.parse_args()

    configs   = _build_configs(args.depth, args.games, args.sample)
    done_keys = _load_done_keys(args.output)

    # Filter already-completed configs
    pending = [c for c in configs
               if (c[0].name, c[1].name, c[2], c[3], c[6]) not in done_keys]

    print(f"Configs total  : {len(configs)}")
    print(f"Already done   : {len(configs) - len(pending)}")
    print(f"To run         : {len(pending)}")
    print(f"Depth          : {args.depth}")
    print(f"Workers        : {args.workers}")
    print(f"Output         : {args.output}")

    if not pending:
        print("Nothing to do.")
        _print_summary(args.output)
        return

    # Open CSV in append mode
    write_header = not os.path.exists(args.output)
    outfile = open(args.output, "a", newline="")
    writer  = csv.DictWriter(outfile, fieldnames=CSV_FIELDNAMES)
    if write_header:
        writer.writeheader()

    completed = 0
    t0        = time.time()

    def _on_result(result):
        nonlocal completed
        writer.writerow(result)
        outfile.flush()
        completed += 1
        elapsed = time.time() - t0
        rate    = completed / elapsed if elapsed > 0 else 0
        remain  = (len(pending) - completed) / rate if rate > 0 else float("inf")
        print(f"\r  [{completed}/{len(pending)}]  "
              f"{result['red_card']} vs {result['blue_card']}  "
              f"start({result['red_start_score']},{result['blue_start_score']})  "
              f"→ {result['winner']}  "
              f"turns={result['turns']}  "
              f"rate={rate:.2f} g/s  "
              f"ETA={remain/60:.1f}min   ",
              end="", flush=True)

    if args.workers == 1:
        # Serial — simpler, easier to debug
        for cfg in pending:
            result = _run_single_game(cfg)
            _on_result(result)
    else:
        # Parallel using spawn context (required on macOS)
        import multiprocessing
        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(processes=args.workers) as pool:
            for result in pool.imap_unordered(_run_single_game, pending):
                _on_result(result)

    outfile.close()
    print()  # newline after progress line
    print(f"\nDone! Results saved to {args.output}")
    _print_summary(args.output)


if __name__ == "__main__":
    main()
