#!/usr/bin/env python -u
"""Test SuperAlpha v2 with game phase detection against AlphaBeta"""
import sys
sys.path.insert(0, '/home/user/catantron/catanatron_core')
sys.path.insert(0, '/home/user/catantron/catanatron_gym')
sys.path.insert(0, '/home/user/catantron/catanatron_experimental')

from catanatron.game import Game
from catanatron.models.player import Color
from catanatron_experimental.machine_learning.players.minimax import AlphaBetaPlayer
from catanatron_experimental.machine_learning.players.super_alpha_v2 import SuperAlphaV2Player
import time

def run_test(num_games=20):
    """Test SuperAlpha v2 vs AlphaBeta"""
    v2_wins = 0
    ab_wins = 0
    v2_red_wins = 0
    v2_blue_wins = 0
    red_games = 0
    blue_games = 0

    print("=" * 70, flush=True)
    print("SuperAlpha v2 (Game Phase Detection) vs AlphaBeta", flush=True)
    print("=" * 70, flush=True)
    print(f"Running {num_games} games...", flush=True)
    print("v2 Features: Early/Mid/Late game phase detection with adaptive weights", flush=True)
    print("=" * 70, flush=True)

    start_time = time.time()

    for i in range(num_games):
        # Alternate colors
        if i % 2 == 0:
            players = [
                SuperAlphaV2Player(Color.RED, max_depth=3, prunning=True),
                AlphaBetaPlayer(Color.BLUE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.WHITE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.ORANGE, depth=2, prunning=False),
            ]
            v2_color = Color.RED
            v2_position = "RED"
            red_games += 1
        else:
            players = [
                AlphaBetaPlayer(Color.RED, depth=2, prunning=False),
                SuperAlphaV2Player(Color.BLUE, max_depth=3, prunning=True),
                AlphaBetaPlayer(Color.WHITE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.ORANGE, depth=2, prunning=False),
            ]
            v2_color = Color.BLUE
            v2_position = "BLUE"
            blue_games += 1

        game_start = time.time()
        print(f"Game {i+1}/{num_games} (v2={v2_position})...", end=" ", flush=True)

        try:
            game = Game(players)
            winner = game.play()

            game_time = time.time() - game_start

            if winner == v2_color:
                v2_wins += 1
                if v2_position == "RED":
                    v2_red_wins += 1
                else:
                    v2_blue_wins += 1
                result = "V2 WIN"
            else:
                ab_wins += 1
                result = "AB WIN"

            print(f"{result} | V2:{v2_wins} AB:{ab_wins} | "
                  f"Time:{game_time:.1f}s | Turns:{game.state.num_turns}", flush=True)

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            continue

    total_time = time.time() - start_time
    total_games = v2_wins + ab_wins

    print("=" * 70, flush=True)
    print("FINAL RESULTS:", flush=True)
    print("=" * 70, flush=True)
    print(f"Total games: {total_games}", flush=True)
    print(f"Total time: {total_time/60:.1f} minutes", flush=True)
    print("", flush=True)
    print(f"SuperAlpha v2: {v2_wins}/{total_games} ({v2_wins*100//total_games if total_games else 0}%)", flush=True)
    print(f"AlphaBeta:     {ab_wins}/{total_games} ({ab_wins*100//total_games if total_games else 0}%)", flush=True)
    print("", flush=True)
    print("Positional Analysis:", flush=True)
    print(f"  v2 as RED:  {v2_red_wins}/{red_games} ({v2_red_wins*100//red_games if red_games else 0}%)", flush=True)
    print(f"  v2 as BLUE: {v2_blue_wins}/{blue_games} ({v2_blue_wins*100//blue_games if blue_games else 0}%)", flush=True)
    print("=" * 70, flush=True)

    # Compare to v1 results
    print("", flush=True)
    print("COMPARISON TO v1:", flush=True)
    print("-" * 70, flush=True)
    print("v1 Original Test: 60% overall (80% RED, 40% BLUE)", flush=True)
    print("v1 Current Test:  22% overall (0% RED, 50% BLUE)", flush=True)
    print(f"v2 This Test:     {v2_wins*100//total_games if total_games else 0}% overall "
          f"({v2_red_wins*100//red_games if red_games else 0}% RED, "
          f"{v2_blue_wins*100//blue_games if blue_games else 0}% BLUE)", flush=True)
    print("=" * 70, flush=True)

    return v2_wins, ab_wins

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--num', type=int, default=20, help='Number of games')
    args = parser.parse_args()

    run_test(args.num)
