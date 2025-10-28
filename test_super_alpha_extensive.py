#!/usr/bin/env python
"""Extensive test script to run SuperAlpha vs AlphaBeta with statistics"""
import sys
import time
from collections import defaultdict

sys.path.insert(0, '/home/user/catantron/catanatron_core')
sys.path.insert(0, '/home/user/catantron/catanatron_gym')
sys.path.insert(0, '/home/user/catantron/catanatron_experimental')

from catanatron.game import Game
from catanatron.models.player import Color
from catanatron_experimental.machine_learning.players.minimax import AlphaBetaPlayer
from catanatron_experimental.machine_learning.players.super_alpha import SuperAlphaPlayer

def run_extensive_tests(num_games=100):
    """Run extensive test games with detailed statistics"""
    super_alpha_wins = 0
    alpha_beta_wins = 0

    # Track wins by position
    wins_by_position = {"SuperAlpha_RED": 0, "SuperAlpha_BLUE": 0,
                        "AlphaBeta": 0}

    # Track game lengths
    game_lengths = []
    game_times = []

    print(f"Running {num_games} games: SuperAlpha vs 3x AlphaBeta (depth 2)")
    print("=" * 70)
    print("This will take approximately 2-3 hours...")
    print("=" * 70)

    start_time = time.time()

    for i in range(num_games):
        # Alternate SuperAlpha between RED and BLUE for fairness
        if i % 2 == 0:
            players = [
                SuperAlphaPlayer(Color.RED, max_depth=4, prunning=True),
                AlphaBetaPlayer(Color.BLUE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.WHITE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.ORANGE, depth=2, prunning=False),
            ]
            super_alpha_color = Color.RED
            sa_position = "RED"
        else:
            players = [
                AlphaBetaPlayer(Color.RED, depth=2, prunning=False),
                SuperAlphaPlayer(Color.BLUE, max_depth=4, prunning=True),
                AlphaBetaPlayer(Color.WHITE, depth=2, prunning=False),
                AlphaBetaPlayer(Color.ORANGE, depth=2, prunning=False),
            ]
            super_alpha_color = Color.BLUE
            sa_position = "BLUE"

        game_start = time.time()

        try:
            game = Game(players)
            winner = game.play()

            game_time = time.time() - game_start
            game_times.append(game_time)
            game_lengths.append(game.state.num_turns)

            if winner == super_alpha_color:
                super_alpha_wins += 1
                wins_by_position[f"SuperAlpha_{sa_position}"] += 1
                result = "SA"
            else:
                alpha_beta_wins += 1
                wins_by_position["AlphaBeta"] += 1
                result = "AB"

            # Progress update every 10 games
            if (i + 1) % 10 == 0:
                elapsed = time.time() - start_time
                games_per_min = (i + 1) / (elapsed / 60)
                eta_mins = (num_games - i - 1) / games_per_min

                print(f"Game {i+1:3d}/{num_games} [{result}] | "
                      f"SA: {super_alpha_wins:3d} ({super_alpha_wins*100//(i+1):2d}%) | "
                      f"AB: {alpha_beta_wins:3d} ({alpha_beta_wins*100//(i+1):2d}%) | "
                      f"ETA: {eta_mins:.1f}m | "
                      f"Turns: {game.state.num_turns:3d} | "
                      f"Time: {game_time:.1f}s")

        except Exception as e:
            print(f"Game {i+1} ERROR: {e}")
            import traceback
            traceback.print_exc()
            # Continue with next game instead of breaking
            continue

    total_time = time.time() - start_time

    # Calculate statistics
    avg_game_length = sum(game_lengths) / len(game_lengths) if game_lengths else 0
    avg_game_time = sum(game_times) / len(game_times) if game_times else 0

    print("=" * 70)
    print(f"\n{'FINAL RESULTS':^70}")
    print("=" * 70)
    print(f"Total games completed: {super_alpha_wins + alpha_beta_wins}")
    print(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.2f} hours)")
    print(f"\n{'Win Statistics':^70}")
    print("-" * 70)
    print(f"  SuperAlpha wins: {super_alpha_wins:3d}  ({super_alpha_wins*100//num_games:2d}%)")
    print(f"  AlphaBeta wins:  {alpha_beta_wins:3d}  ({alpha_beta_wins*100//num_games:2d}%)")
    print(f"\n{'Positional Win Rate':^70}")
    print("-" * 70)
    red_games = num_games // 2
    blue_games = num_games - red_games
    print(f"  SuperAlpha as RED:  {wins_by_position['SuperAlpha_RED']:3d}/{red_games} "
          f"({wins_by_position['SuperAlpha_RED']*100//red_games if red_games else 0:2d}%)")
    print(f"  SuperAlpha as BLUE: {wins_by_position['SuperAlpha_BLUE']:3d}/{blue_games} "
          f"({wins_by_position['SuperAlpha_BLUE']*100//blue_games if blue_games else 0:2d}%)")
    print(f"\n{'Game Statistics':^70}")
    print("-" * 70)
    print(f"  Average game length: {avg_game_length:.1f} turns")
    print(f"  Average game time:   {avg_game_time:.1f} seconds")
    print(f"  Fastest game:        {min(game_times):.1f} seconds")
    print(f"  Slowest game:        {max(game_times):.1f} seconds")

    # Statistical significance (simple chi-square test approximation)
    print(f"\n{'Statistical Analysis':^70}")
    print("-" * 70)

    # Calculate confidence interval (approximate)
    win_rate = super_alpha_wins / num_games if num_games > 0 else 0
    std_error = (win_rate * (1 - win_rate) / num_games) ** 0.5
    confidence_95 = 1.96 * std_error

    print(f"  Win rate: {win_rate*100:.1f}%")
    print(f"  95% Confidence Interval: [{(win_rate-confidence_95)*100:.1f}%, "
          f"{(win_rate+confidence_95)*100:.1f}%]")

    # Z-test against 50% null hypothesis
    z_score = (win_rate - 0.5) / std_error if std_error > 0 else 0
    print(f"  Z-score vs 50%: {z_score:.2f}")

    if z_score > 1.96:
        print(f"  Result: SuperAlpha is SIGNIFICANTLY BETTER (p < 0.05)")
    elif z_score > 1.645:
        print(f"  Result: SuperAlpha is better (p < 0.10)")
    else:
        print(f"  Result: Not statistically significant difference")

    print("=" * 70)

    return super_alpha_wins, alpha_beta_wins

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test SuperAlpha vs AlphaBeta')
    parser.add_argument('--num', type=int, default=100,
                       help='Number of games to play (default: 100)')
    args = parser.parse_args()

    print("=" * 70)
    print(f"{'SuperAlpha vs AlphaBeta - Extensive Testing':^70}")
    print("=" * 70)
    print()

    run_extensive_tests(args.num)
