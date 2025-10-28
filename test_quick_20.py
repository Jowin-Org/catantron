#!/usr/bin/env python -u
"""Quick test with immediate output - 20 games for faster results"""
import sys
sys.path.insert(0, '/home/user/catantron/catanatron_core')
sys.path.insert(0, '/home/user/catantron/catanatron_gym')
sys.path.insert(0, '/home/user/catantron/catanatron_experimental')

from catanatron.game import Game
from catanatron.models.player import Color
from catanatron_experimental.machine_learning.players.minimax import AlphaBetaPlayer
from catanatron_experimental.machine_learning.players.super_alpha import SuperAlphaPlayer
import time

def run_quick_test(num_games=20):
    """Run quick test with immediate output"""
    super_alpha_wins = 0
    alpha_beta_wins = 0

    print("=" * 60, flush=True)
    print(f"Running {num_games} games: SuperAlpha vs AlphaBeta", flush=True)
    print("=" * 60, flush=True)

    start_time = time.time()

    for i in range(num_games):
        # Alternate colors
        if i % 2 == 0:
            players = [
                SuperAlphaPlayer(Color.RED, max_depth=4, prunning=True),
                AlphaBetaPlayer(Color.BLUE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.WHITE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.ORANGE, depth=2, prunning=False),
            ]
            super_alpha_color = Color.RED
        else:
            players = [
                AlphaBetaPlayer(Color.RED, depth=2, prunning=False),
                SuperAlphaPlayer(Color.BLUE, max_depth=4, prunning=True),
                AlphaBetaPlayer(Color.WHITE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.ORANGE, depth=2, prunning=False),
            ]
            super_alpha_color = Color.BLUE

        game_start = time.time()
        print(f"Game {i+1}/{num_games}...", end=" ", flush=True)

        try:
            game = Game(players)
            winner = game.play()

            game_time = time.time() - game_start

            if winner == super_alpha_color:
                super_alpha_wins += 1
                result = "SA WIN"
            else:
                alpha_beta_wins += 1
                result = "AB WIN"

            print(f"{result} | SA:{super_alpha_wins} AB:{alpha_beta_wins} | "
                  f"Time:{game_time:.1f}s | Turns:{game.state.num_turns}", flush=True)

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            continue

    total_time = time.time() - start_time
    win_rate = super_alpha_wins * 100 // num_games if num_games > 0 else 0

    print("=" * 60, flush=True)
    print("FINAL RESULTS:", flush=True)
    print(f"  SuperAlpha: {super_alpha_wins}/{num_games} ({win_rate}%)", flush=True)
    print(f"  AlphaBeta:  {alpha_beta_wins}/{num_games} ({100-win_rate}%)", flush=True)
    print(f"  Total time: {total_time/60:.1f} minutes", flush=True)
    print("=" * 60, flush=True)

    return super_alpha_wins, alpha_beta_wins

if __name__ == "__main__":
    run_quick_test(20)
