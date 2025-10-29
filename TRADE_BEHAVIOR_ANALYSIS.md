# What Happens When You Offer a Trade to AlphaBeta?

## Quick Answer

**AlphaBeta will evaluate the trade using its minimax search and value function.** It will either:
- **ACCEPT** the trade if it increases its position value
- **REJECT** the trade otherwise (default behavior)

However, in practice, **AlphaBeta almost always REJECTS trades** because its value function doesn't properly account for resource scarcity and trade value.

---

## How It Works: Step-by-Step

### 1. You Offer a Trade
```python
# Example: You offer to give 1 wood for 1 wheat
trade_offer = (1, 0, 0, 0, 0,  # Give: wood, brick, sheep, wheat, ore
               0, 0, 0, 1, 0)  # Want: wood, brick, sheep, wheat, ore
action = Action(your_color, ActionType.OFFER_TRADE, trade_offer)
```

### 2. Game Broadcasts Trade to All Players
```python
# From actions.py lines 89-98
elif action_prompt == ActionPrompt.DECIDE_TRADE:
    actions = [Action(color, ActionType.REJECT_TRADE, state.current_trade)]

    # can only accept if have enough cards
    freqdeck = get_player_freqdeck(state, color)
    asked = state.current_trade[5:10]  # What you're asking for
    if freqdeck_contains(freqdeck, asked):
        actions.append(Action(color, ActionType.ACCEPT_TRADE, state.current_trade))

    return actions
```

Each opponent bot (including AlphaBeta) gets 1-2 possible actions:
- ✅ **Always available:** `REJECT_TRADE`
- ⚠️ **Conditional:** `ACCEPT_TRADE` (only if bot has the resources you want)

### 3. AlphaBeta's Decision Process
```python
# From minimax.py - decide() method
def decide(self, game, playable_actions):
    # If only one action (can only reject), return it
    if len(actions) == 1:
        return actions[0]  # REJECT_TRADE

    # If two actions (can accept or reject), run minimax search
    result = self.alphabeta(game.copy(), self.depth, ...)
    return result[0]  # Best action according to search
```

**AlphaBeta will:**
1. Create a game copy
2. Try ACCEPT_TRADE: Simulate accepting, evaluate resulting position
3. Try REJECT_TRADE: Simulate rejecting, evaluate resulting position
4. Pick the action with higher value

### 4. Evaluation: What Does AlphaBeta Consider?

AlphaBeta evaluates each option using its value function:

```python
# Simplified from value.py
def evaluate_position(game, color):
    score = (
        victory_points * 3e14 +         # VPs dominate
        production * 1e8 +               # Resource production
        hand_synergy * 1e2 +             # Distance to next building
        num_buildable_nodes * 1e3 +      # Expansion potential
        # ... etc
    )
    return score
```

**For ACCEPT_TRADE:**
```
Before: Has 1 wheat, needs wood
After:  Has 0 wheat, has 1 wood
```

**For REJECT_TRADE:**
```
State unchanged
```

AlphaBeta compares:
- `value(accept)` = evaluate position with wood instead of wheat
- `value(reject)` = evaluate current position

---

## Why AlphaBeta Usually Rejects Trades

### Problem 1: **No Trade-Specific Features**

AlphaBeta's value function has NO features for:
- ❌ Resource scarcity (is wheat rare right now?)
- ❌ Immediate building potential (can I build settlement NOW with this trade?)
- ❌ Opponent benefit (does accepting help the opponent more?)
- ❌ Resource diversity (do I need variety?)

It only sees:
- ✅ Total production (doesn't change from a single trade)
- ✅ Hand synergy (might improve slightly)
- ✅ VPs (doesn't change from trading)

### Problem 2: **Static Evaluation**

```python
# Before trade: 1 wheat, 0 wood
# "hand_synergy" = how close to next building?
# Maybe 0.6 (60% of way to settlement)

# After accepting trade: 0 wheat, 1 wood
# "hand_synergy" = how close to next building?
# Maybe 0.65 (65% of way to settlement)

# Improvement: +0.05 * 1e2 = +5 points
# But production, VPs, everything else = same

# Conclusion: Tiny improvement, not worth thinking about
```

### Problem 3: **Assumes Opponent is Rational**

If you're offering the trade, AlphaBeta (correctly) assumes:
- "If my opponent offers this, it probably benefits THEM"
- "Therefore, I should reject to not help them"

This is actually **smart game theory**, but doesn't work when:
- You're offering a fair trade
- You're a human making suboptimal offers
- The trade has mutual benefit

---

## When Would AlphaBeta Accept?

AlphaBeta would accept a trade only if:

### Scenario 1: **Massive Hand Synergy Improvement**
```python
# Before: 0 wood, 3 brick, 1 wheat, 1 sheep, 0 ore
# Can't build anything
# hand_synergy = 0.3

# You offer: Give me 1 brick, take 1 wood
# After: 1 wood, 2 brick, 1 wheat, 1 sheep, 0 ore
# Can build settlement!
# hand_synergy = 1.0

# Improvement: +0.7 * 1e2 = +70 points
# AlphaBeta might accept
```

### Scenario 2: **You Offer an Unfair Trade** (in bot's favor)
```python
# You offer: Give me 1 ore, take 4 wheat
# AlphaBeta evaluates: "I'm getting 4 wheat for 1 ore? Yes!"
# (Assuming it has ore and wants wheat)
```

### Scenario 3: **Endgame Critical Resource**
```python
# AlphaBeta at 9 VPs, needs wheat to buy dev card for win
# You offer: Give me wheat, take ore
# But AlphaBeta sees: losing wheat = can't win next turn
# Will REJECT even if "value" says accept
# (because -VPs weight is so high)
```

---

## Other Bots' Behavior

### RandomPlayer
```python
def decide(self, game, playable_actions):
    return random.choice(playable_actions)
```
**Result:** 50% chance accepts, 50% chance rejects (if has resources)

### ValueFunctionPlayer
Similar to AlphaBeta but no lookahead:
- Evaluates immediate value change
- Usually rejects for same reasons

### SuperAlpha v1/v2
Same as AlphaBeta - uses value function to decide
- Actually WORSE at trades because complex features don't help

---

## Example Scenarios

### Scenario A: Human vs AlphaBeta
```
YOU:   "I'll give you 2 wheat for 1 ore"
       (You need ore for development card)

ALPHABETA thinks:
  - My hand: 1 ore, 1 wood, 1 brick
  - If accept: 0 ore, 3 wheat, 1 wood, 1 brick
  - hand_synergy before: 0.4
  - hand_synergy after: 0.5
  - Improvement: minimal
  - DECISION: REJECT

Result: REJECTED ❌
```

### Scenario B: Desperate Trade
```
YOU:   "I'll give you 3 sheep for 1 wood"
       (Unfair in AlphaBeta's favor)

ALPHABETA thinks:
  - My hand: 1 wood, 0 sheep
  - If accept: 0 wood, 3 sheep
  - hand_synergy before: 0.3
  - hand_synergy after: 0.6
  - Improvement: significant
  - DECISION: ACCEPT

Result: ACCEPTED ✅
```

### Scenario C: Building-Enabling Trade
```
YOU:   "I'll give you 1 brick for 1 wood"
       (AlphaBeta has 1 brick, 1 wheat, 1 sheep, needs wood for settlement)

ALPHABETA thinks:
  - My hand: 1 brick, 1 wheat, 1 sheep, 0 wood
  - If accept: 0 brick, 1 wheat, 1 sheep, 1 wood
  - hand_synergy before: 0.75 (missing only wood)
  - hand_synergy after: 1.0 (CAN BUILD SETTLEMENT!)
  - Improvement: MAJOR
  - DECISION: ACCEPT

Result: ACCEPTED ✅
```

---

## Technical Details

### Where the Decision Happens
```python
# File: minimax.py, method: decide()
# Line ~58-79

def decide(self, game, playable_actions):
    actions = self.get_actions(game)
    if len(actions) == 1:
        return actions[0]  # Only option (usually REJECT)

    # Run minimax search on ACCEPT vs REJECT
    result = self.alphabeta(
        game.copy(),
        self.depth,        # Usually 2
        float("-inf"),
        float("inf"),
        deadline,
        node
    )
    return result[0]  # Best action
```

### Search Depth Impact
```python
# depth = 1: Immediate evaluation only
# depth = 2: Considers opponent's next move
# depth = 3+: Considers 2+ moves ahead

# For trades, depth matters:
# depth=1: "Does this trade improve my position NOW?"
# depth=2: "After I accept, what will opponent do? Will they win?"
```

---

## Summary

| Question | Answer |
|----------|--------|
| **Does AlphaBeta evaluate trades?** | Yes, using minimax + value function |
| **Does it usually accept?** | No, almost always rejects |
| **Why reject?** | Value function doesn't capture trade value |
| **When does it accept?** | Only if trade significantly improves hand_synergy or position |
| **Can I exploit this?** | Yes - offer unfair trades in bot's favor |
| **Is this realistic?** | No - real players trade much more |

---

## Recommendation

If you want bots that trade intelligently, you would need to:

1. **Add trade-specific features** to value function:
   ```python
   "resource_scarcity": Evaluate which resources are rare
   "building_potential": Can I build immediately after trade?
   "opponent_benefit": How much does this help the offerer?
   ```

2. **Implement negotiation logic**:
   ```python
   def evaluate_trade(self, give, receive):
       # Special logic for trades
       value_given = sum(resource_values[r] for r in give)
       value_received = sum(resource_values[r] for r in receive)
       return value_received - value_given
   ```

3. **Or use machine learning** to learn when to trade from human games

**But the current bots (AlphaBeta, SuperAlpha, etc.) will almost always reject player-to-player trades.**

---

*Analysis Date: 2025-10-28*
*Based on: Catanatron codebase analysis*
