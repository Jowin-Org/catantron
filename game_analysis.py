# Analyze the test results in detail
results = """
Game 1/20... AB WIN | SA:0 AB:1 | Time:61.3s | Turns:78
Game 2/20... SA WIN | SA:1 AB:1 | Time:163.8s | Turns:99
Game 3/20... AB WIN | SA:1 AB:2 | Time:14.8s | Turns:53
Game 4/20... SA WIN | SA:2 AB:2 | Time:65.4s | Turns:70
Game 5/20... AB WIN | SA:2 AB:3 | Time:62.0s | Turns:83
Game 6/20... AB WIN | SA:2 AB:4 | Time:24.7s | Turns:68
Game 7/20... AB WIN | SA:2 AB:5 | Time:25.3s | Turns:72
Game 8/20... AB WIN | SA:2 AB:6 | Time:59.1s | Turns:94
Game 9/20... AB WIN | SA:2 AB:7 | Time:38.1s | Turns:65
"""

games = []
for i, line in enumerate(results.strip().split('\n'), 1):
    if 'WIN' in line:
        parts = line.split('|')
        winner = 'SA' if 'SA WIN' in parts[0] else 'AB'
        time = float(parts[2].split(':')[1].replace('s', ''))
        turns = int(parts[3].split(':')[1])
        
        # Alternation: even index (0,2,4...) = RED, odd (1,3,5...) = BLUE
        sa_color = 'RED' if (i-1) % 2 == 0 else 'BLUE'
        
        games.append({
            'game': i,
            'winner': winner,
            'sa_color': sa_color,
            'time': time,
            'turns': turns
        })

print("=" * 70)
print("DETAILED GAME ANALYSIS")
print("=" * 70)

print("\nGame-by-Game Breakdown:")
print(f"{'Game':<6} {'SA Color':<10} {'Winner':<8} {'Time':<8} {'Turns':<6}")
print("-" * 70)
for g in games:
    print(f"{g['game']:<6} {g['sa_color']:<10} {g['winner']:<8} {g['time']:<8.1f} {g['turns']:<6}")

print("\n" + "=" * 70)
print("POSITIONAL ANALYSIS")
print("=" * 70)

red_games = [g for g in games if g['sa_color'] == 'RED']
blue_games = [g for g in games if g['sa_color'] == 'BLUE']

red_wins = len([g for g in red_games if g['winner'] == 'SA'])
blue_wins = len([g for g in blue_games if g['winner'] == 'SA'])

print(f"\nSuperAlpha as RED (player 1, goes first):")
print(f"  Games: {len(red_games)}")
print(f"  Wins:  {red_wins} ({red_wins*100//len(red_games) if red_games else 0}%)")
print(f"  Losses: {len(red_games) - red_wins}")

print(f"\nSuperAlpha as BLUE (player 2):")
print(f"  Games: {len(blue_games)}")
print(f"  Wins:  {blue_wins} ({blue_wins*100//len(blue_games) if blue_games else 0}%)")
print(f"  Losses: {len(blue_games) - blue_wins}")

print("\n" + "=" * 70)
print("GAME CHARACTERISTICS")
print("=" * 70)

sa_wins = [g for g in games if g['winner'] == 'SA']
ab_wins = [g for g in games if g['winner'] == 'AB']

print(f"\nWhen SuperAlpha WINS:")
print(f"  Avg turns: {sum(g['turns'] for g in sa_wins) / len(sa_wins):.1f}")
print(f"  Avg time:  {sum(g['time'] for g in sa_wins) / len(sa_wins):.1f}s")
print(f"  Games: {[g['game'] for g in sa_wins]}")

print(f"\nWhen AlphaBeta WINS:")
print(f"  Avg turns: {sum(g['turns'] for g in ab_wins) / len(ab_wins):.1f}")
print(f"  Avg time:  {sum(g['time'] for g in ab_wins) / len(ab_wins):.1f}s")
print(f"  Games: {[g['game'] for g in ab_wins]}")

# Identify very short games (likely quick losses)
short_games = [g for g in games if g['time'] < 30]
print(f"\nVery SHORT games (<30s):")
for g in short_games:
    print(f"  Game {g['game']}: {g['winner']} wins, SA was {g['sa_color']}, {g['time']:.1f}s, {g['turns']} turns")

# Identify very long games
long_games = [g for g in games if g['time'] > 100]
print(f"\nVery LONG games (>100s):")
for g in long_games:
    print(f"  Game {g['game']}: {g['winner']} wins, SA was {g['sa_color']}, {g['time']:.1f}s, {g['turns']} turns")

