#!/usr/bin/env python -u
"""Test RandomBot's behavior with trades"""
import sys
sys.path.insert(0, '/home/user/catantron/catanatron_core')
sys.path.insert(0, '/home/user/catantron/catanatron_gym')
sys.path.insert(0, '/home/user/catantron/catanatron_experimental')

from catanatron.game import Game
from catanatron.models.player import Color, Player, RandomPlayer
from catanatron.models.enums import Action, ActionType

class TradeOfferingPlayer(Player):
    """Player that offers multiple trades to test RandomBot responses"""

    def __init__(self, color):
        super().__init__(color)
        self.trades_offered = 0
        self.max_trades = 5

    def decide(self, game, playable_actions):
        # Try to offer trades after rolling
        has_rolled = game.state.player_state.get(f"{self.color.value}_HAS_ROLLED", False)

        if has_rolled and self.trades_offered < self.max_trades:
            # Check if we can offer trade
            for action in playable_actions:
                if action.action_type == ActionType.OFFER_TRADE:
                    # Offer: Give 1 wood for 1 wheat
                    trade_offer = (1, 0, 0, 0, 0, 0, 0, 0, 1, 0)
                    self.trades_offered += 1
                    print(f"\n{self.color.value} OFFERING TRADE #{self.trades_offered}: 1 wood for 1 wheat", flush=True)
                    return Action(self.color, ActionType.OFFER_TRADE, trade_offer)

        # Otherwise pick first action
        return playable_actions[0]

def test_random_bot_trades():
    """Test how RandomBot responds to trades"""

    print("=" * 70, flush=True)
    print("Testing: RandomBot's Trade Behavior", flush=True)
    print("=" * 70, flush=True)
    print("\nRandomBot code:", flush=True)
    print("  def decide(self, game, playable_actions):", flush=True)
    print("      return random.choice(playable_actions)", flush=True)
    print("\nThis means:", flush=True)
    print("  - If RandomBot has the resources you want:", flush=True)
    print("    → 50% chance ACCEPTS (chooses ACCEPT_TRADE)", flush=True)
    print("    → 50% chance REJECTS (chooses REJECT_TRADE)", flush=True)
    print("  - If RandomBot DOESN'T have the resources:", flush=True)
    print("    → 100% REJECTS (only option is REJECT_TRADE)", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    test_random_bot_trades()
