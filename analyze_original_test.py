# Original 10-game test results from earlier
results = """
Game 1: SuperAlpha (RED) wins
Game 2: AlphaBeta (ORANGE) wins  
Game 3: SuperAlpha (RED) wins
Game 4: SuperAlpha (BLUE) wins
Game 5: SuperAlpha (RED) wins
Game 6: AlphaBeta (RED) wins
Game 7: SuperAlpha (RED) wins
Game 8: AlphaBeta (RED) wins
Game 9: AlphaBeta (WHITE) wins
Game 10: SuperAlpha (BLUE) wins
"""

print("ORIGINAL 10-GAME TEST ANALYSIS")
print("=" * 60)

# Parse manually based on the pattern
sa_red = [1, 3, 5, 7]  # SA was RED and won
sa_blue = [4, 10]  # SA was BLUE and won
ab_wins = [2, 6, 8, 9]  # AB won

# Based on alternation pattern:
# Game 1 (i=0): SA=RED, winner=SA ✓
# Game 2 (i=1): SA=BLUE, winner=AB (ORANGE) - SA lost
# Game 3 (i=2): SA=RED, winner=SA ✓
# Game 4 (i=3): SA=BLUE, winner=SA ✓
# Game 5 (i=4): SA=RED, winner=SA ✓
# Game 6 (i=5): SA=BLUE, winner=AB (RED) - SA lost
# Game 7 (i=6): SA=RED, winner=SA ✓
# Game 8 (i=7): SA=BLUE, winner=AB (RED) - SA lost
# Game 9 (i=8): SA=RED, winner=AB (WHITE) - SA lost
# Game 10 (i=9): SA=BLUE, winner=SA ✓

red_games = [1, 3, 5, 7, 9]
blue_games = [2, 4, 6, 8, 10]

red_wins = [1, 3, 5, 7]  # Game 9 was a loss
blue_wins = [4, 10]  # Games 2, 6, 8 were losses

print(f"SuperAlpha as RED: {len(red_wins)}/5 wins (80%)")
print(f"SuperAlpha as BLUE: {len(blue_wins)}/5 wins (40%)")
print()
print("INTERESTING: In original test, RED was BETTER!")
print("This suggests RANDOMNESS in board setup matters greatly")
