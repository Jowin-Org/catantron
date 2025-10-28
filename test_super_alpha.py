#!/usr/bin/env python
"""Test script to run SuperAlpha vs AlphaBeta"""
import sys
sys.path.insert(0, '/home/user/catantron/catanatron_core')
sys.path.insert(0, '/home/user/catantron/catanatron_gym')
sys.path.insert(0, '/home/user/catantron/catanatron_experimental')

from catanatron.game import Game
from catanatron.models.player import Color
from catanatron_experimental.machine_learning.players.minimax import AlphaBetaPlayer
from catanatron_experimental.machine_learning.players.super_alpha import SuperAlphaPlayer

def run_test_games(num_games=10):
    """Run test games between SuperAlpha and AlphaBeta"""
    super_alpha_wins = 0
    alpha_beta_wins = 0

    print(f"Running {num_games} games: SuperAlpha vs AlphaBeta (depth 2)")
    print("=" * 60)

    for i in range(num_games):
        # Alternate colors to be fair
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

        print(f"Game {i+1}/{num_games}...", end=" ", flush=True)

        try:
            game = Game(players)
            winner = game.play()

            if winner == super_alpha_color:
                super_alpha_wins += 1
                print(f"SuperAlpha wins! (Winner: {winner})")
            else:
                alpha_beta_wins += 1
                print(f"AlphaBeta wins! (Winner: {winner})")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            break

    print("=" * 60)
    print(f"Results after {num_games} games:")
    print(f"  SuperAlpha wins: {super_alpha_wins} ({super_alpha_wins*100//num_games}%)")
    print(f"  AlphaBeta wins: {alpha_beta_wins} ({alpha_beta_wins*100//num_games}%)")
    print("=" * 60)

    return super_alpha_wins, alpha_beta_wins

if __name__ == "__main__":
    # Run a quick test with 10 games
    print("Testing SuperAlpha bot...")
    print("This may take several minutes...\n")

    run_test_games(10)
