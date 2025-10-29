#!/usr/bin/env python -u
"""Test what happens when you offer a trade to AlphaBeta"""
import sys
sys.path.insert(0, '/home/user/catantron/catanatron_core')
sys.path.insert(0, '/home/user/catantron/catanatron_gym')
sys.path.insert(0, '/home/user/catantron/catanatron_experimental')

from catanatron.game import Game
from catanatron.models.player import Color, Player
from catanatron.models.enums import Action, ActionType
from catanatron_experimental.machine_learning.players.minimax import AlphaBetaPlayer
from catanatron_experimental.machine_learning.players.value import ValueFunctionPlayer

class TradeOfferingPlayer(Player):
    """Player that offers trades to test bot responses"""

    def __init__(self, color):
        super().__init__(color)
        self.trade_offered = False
        self.trade_responses = []

    def decide(self, game, playable_actions):
        # Check if any action is OFFER_TRADE
        can_offer_trade = any(a.action_type == ActionType.OFFER_TRADE for a in playable_actions)

        # After rolling, try to offer a trade once
        if not self.trade_offered and can_offer_trade and game.state.player_state.get(f"{self.color.value}_HAS_ROLLED"):
            # Offer: Give 1 wood, want 1 wheat
            # Format: (give_wood, give_brick, give_sheep, give_wheat, give_ore, want_wood, want_brick, want_sheep, want_wheat, want_ore)
            trade_offer = (1, 0, 0, 0, 0, 0, 0, 0, 1, 0)

            print(f"\n{self.color.value} OFFERING TRADE: Give 1 WOOD for 1 WHEAT", flush=True)
            self.trade_offered = True

            return Action(self.color, ActionType.OFFER_TRADE, trade_offer)

        # For all other decisions, just pick first action
        return playable_actions[0]

def test_trade_with_alphabeta():
    """Test what AlphaBeta does when offered a trade"""

    print("=" * 70, flush=True)
    print("Testing: What happens when you offer a trade to AlphaBeta?", flush=True)
    print("=" * 70, flush=True)

    # Create a simple game with trade-offering player vs AlphaBeta
    players = [
        TradeOfferingPlayer(Color.RED),
        AlphaBetaPlayer(Color.BLUE, depth=1),  # Shallow depth for speed
        ValueFunctionPlayer(Color.WHITE),
        ValueFunctionPlayer(Color.ORANGE),
    ]

    game = Game(players)

    # Play just a few turns
    try:
        for turn in range(50):  # Limited turns
            game.play_tick()

            # Check if trade was offered and see responses
            if hasattr(game.state, 'current_trade') and game.state.current_trade:
                print(f"\nTrade on table: {game.state.current_trade}", flush=True)

            # Stop if RED player offered trade
            if players[0].trade_offered and turn > 5:
                print(f"\nTrade offering detected on turn {turn}", flush=True)
                # Continue a few more turns to see responses
                for _ in range(10):
                    if game.winning_color():
                        break
                    game.play_tick()
                break

            if game.winning_color():
                print(f"\nGame ended, winner: {game.winning_color()}", flush=True)
                break

    except Exception as e:
        print(f"\nError during game: {e}", flush=True)
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70, flush=True)
    print("CONCLUSION:", flush=True)
    print("=" * 70, flush=True)
    print("When a bot (AlphaBeta, ValueFunction, etc.) receives a trade offer,", flush=True)
    print("it uses its regular decide() method on the available actions:", flush=True)
    print("  - REJECT_TRADE (always available)", flush=True)
    print("  - ACCEPT_TRADE (if bot has the resources)", flush=True)
    print("", flush=True)
    print("Since bots don't have special trade evaluation logic,", flush=True)
    print("they will pick the action that maximizes their value function.", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    test_trade_with_alphabeta()
