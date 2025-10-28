# SuperAlpha v2 - Failed Experiment Analysis

## Executive Summary

SuperAlpha v2 with game phase detection **FAILED** to improve upon v1, achieving only a **10% win rate** vs AlphaBeta, compared to v1's 22-60% range.

## Test Results Comparison

| Version | Win Rate | As RED | As BLUE | Notes |
|---------|----------|--------|---------|-------|
| **v1 Original Test** | **60%** | 80% | 40% | Best performance |
| **v1 Current Test** | **22%** | 0% | 50% | High variance |
| **v2 This Test** | **10%** ❌ | 10% | 10% | **WORSE than v1** |
| **AlphaBeta Baseline** | ~50% | N/A | N/A | Consistent |

## What We Tried in v2

### 1. Game Phase Detection
```python
class GamePhase:
    EARLY = "EARLY"  # Initial placement, first few turns
    MID = "MID"      # Building phase
    LATE = "LATE"    # Race to victory

def detect(game, player_color):
    # Detect based on:
    # - Turn number
    # - Our VPs
    # - Max opponent VP
```

### 2. Adaptive Weights
- **EARLY_GAME_WEIGHTS**: Focus on production (2x weight), deemphasize opponents
- **MID_GAME_WEIGHTS**: Balanced strategy
- **LATE_GAME_WEIGHTS**: Heavy opponent tracking (3x weight on blocking)

### 3. Reduced Search Depth
- Early game: max_depth=2 (vs v1's 4)
- Mid/Late game: max_depth=3
- Rationale: Avoid timeout in early game complex positions

### 4. Simplified Features
- Removed settlement vulnerability (was brittle)
- Kept core features from v1
- Made weights adapt to phase

## Why v2 Failed

### Hypothesis 1: Over-Correction
**Problem:** We over-corrected for v1's early game weakness by reducing search depth and deemphasizing strategic features early.

**Result:** Lost v1's main advantage (deeper search) while not fixing core issues.

### Hypothesis 2: Phase Detection Too Simplistic
```python
# Our phase detection:
if our_vps >= 7 or max_opponent_vp >= 7:
    return LATE
elif num_turns < 15 or our_vps < 3:
    return EARLY
else:
    return MID
```

**Problems:**
- Turn 15 threshold arbitrary
- Doesn't account for board state (resource scarcity, blocked positions)
- Same phase for all board configurations
- Can get "stuck" in wrong phase

### Hypothesis 3: Weight Adaptation Harmful
Changing weights mid-game may confuse the search:
- Depth 1 evaluates with EARLY weights
- Depth 2 evaluates with MID weights
- Inconsistent value estimates → poor tree search

### Hypothesis 4: Early Game Production Over-Emphasis
```python
EARLY_GAME_WEIGHTS = {
    "production": 2e8,  # 2x normal weight
}
```

**Problem:** May have over-valued production at expense of position/expansion.

### Hypothesis 5: Reduced Depth Hurt Performance
- v1: max_depth=4 with iterative deepening
- v2: max_depth=2-3 based on phase

**Impact:** v2 searches less deeply across all game phases, losing tactical advantage.

## Detailed Game Analysis

### Games v2 Won (2/20)
- **Game 7**: RED, 87.0s, 103 turns - Long game, v2 eventually prevailed
- **Game 20**: BLUE, 16.6s, 70 turns - Quick win (unusual)

### Games v2 Lost (18/20)
- **Average time**: 23.1s (fast losses)
- **Shortest**: 9.9s (Game 19) - Catastrophic failure
- **Pattern**: AB wins quickly and decisively

### Positional Analysis
- **v1 showed opposite patterns** in different tests (80% RED vs 0% RED)
- **v2 shows consistency**: 10% both positions
- **Interpretation**: v2 is consistently BAD, not randomly variant

## Root Cause Analysis

### Primary Issue: Reduced Search Capability
By reducing max_depth to 2-3 and adding phase-checking overhead, v2 lost the computational advantage that v1 had.

**v1 strength** = Iterative deepening to depth 4 + complex features
**v2 weakness** = Reduced depth 2-3 + phase overhead + weight switching

### Secondary Issue: Weight Instability
Adaptive weights create inconsistent evaluations:
```
Turn 10 (EARLY): position A = +1000
Turn 16 (MID):   position A = +500  (different weights!)
```

This breaks the assumption of consistent value estimation needed for minimax.

### Tertiary Issue: False Assumptions
We assumed:
1. Early game needs different strategy → **Maybe, but our approach was wrong**
2. Opponent tracking harmful early → **Wrong, still need it**
3. Reducing depth helps → **Wrong, hurt performance**

## Lessons Learned

### ❌ What Doesn't Work
1. **Phase-based weight switching** - Creates inconsistent evaluations
2. **Reducing search depth** - Loses tactical advantage
3. **Over-correcting for variance** - v1's variance was random, not systematic
4. **Simplistic phase detection** - Turn-based thresholds don't capture game state

### ✅ What We Know Works (from v1)
1. **Iterative deepening to depth 4** - When it reaches depth 4, it wins
2. **Complex opponent modeling** - Valuable mid/late game
3. **Action ordering** - Improves pruning efficiency
4. **Consistent weights** - Same evaluation function throughout

### 🤔 What Remains Uncertain
1. **Why v1 has high variance** - Still unexplained (22% vs 60%)
2. **Initial placement** - Both v1 and v2 struggle here
3. **Board-dependent performance** - Neither version robust

## Alternative Approaches to Consider

### Approach A: Simplify v1
- Remove complex features (ports, card diversity, etc.)
- Keep only: production, opponent VPs, expansion potential
- Use v1's search depth but simpler evaluation

### Approach B: Opening Book
- Pre-compute strong initial placements
- Use lookup table for first 2-4 moves
- Switch to v1 after opening

### Approach C: Ensemble
- Use simple strategy early (like ValueFunction)
- Switch to v1's complex strategy mid-game
- Hard cutover instead of gradual weights

### Approach D: Accept AlphaBeta is Better
- AlphaBeta has been tested on 1000+ games
- Its weights are tuned through extensive testing
- Our "improvements" are speculative and untested at scale

## Recommendations

### Immediate: **Stop Development**
- v1 and v2 both underperform AlphaBeta overall
- High variance makes them unreliable
- Further iterations unlikely to help without understanding root cause

### Short-term: **Study AlphaBeta**
- Why does simple strategy beat complex one?
- What makes AlphaBeta robust?
- Can we identify specific situations where v1 wins?

### Long-term: **Different Approach**
Instead of hand-crafted improvements, consider:
1. **Machine Learning**: Train value function from AlphaBeta self-play
2. **Parameter Optimization**: Use Bayesian optimization on v1 weights
3. **Hybrid Strategy**: AlphaBeta for first 20 turns, v1 for endgame
4. **Simpler is Better**: Try removing features instead of adding

## Conclusion

SuperAlpha v2's game phase detection and adaptive weights **made performance significantly worse** (10% vs 22-60%).

**Key Insight**: Complexity doesn't equal strength. AlphaBeta's simpler, well-tuned approach beats our sophisticated but unstable strategies.

**Next Steps**: Either:
1. Abandon SuperAlpha and document AlphaBeta as best
2. Take radically different approach (ML, optimization, hybrid)
3. Run 1000+ game test to understand true performance with statistics

**Recommendation**: Stop iterating on hand-crafted improvements. The problem is fundamental, not tactical.

---

*Analysis Date: 2025-10-28*
*Test Results: 20 games, 10% win rate*
*Status: Failed Experiment - Do Not Deploy*
