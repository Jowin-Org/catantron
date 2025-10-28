"""
SuperAlpha Player - An enhanced AlphaBeta player designed to beat the original.

Key improvements:
1. Enhanced value function with opponent awareness
2. Iterative deepening for adaptive search depth
3. Smart action ordering for better pruning
4. Strategic features (ports, robber, opponent threat)
"""
import time
import random
from typing import Any

from catanatron.game import Game
from catanatron.models.player import Player
from catanatron.models.enums import RESOURCES, SETTLEMENT, CITY
from catanatron.state_functions import (
    get_longest_road_length,
    get_played_dev_cards,
    player_key,
    player_num_dev_cards,
    player_num_resource_cards,
    get_player_buildings,
)
from catanatron_gym.features import (
    build_production_features,
    reachability_features,
    resource_hand_features,
)
from catanatron_experimental.machine_learning.players.tree_search_utils import (
    expand_spectrum,
    list_prunned_actions,
)
from catanatron_experimental.machine_learning.players.value import (
    value_production,
    TRANSLATE_VARIETY,
)


MAX_SEARCH_TIME_SECS = 20
INITIAL_DEPTH = 1


# Enhanced weights with new strategic features
SUPER_WEIGHTS = {
    # Core features (keep existing)
    "public_vps": 3e14,
    "production": 1e8,
    "enemy_production": -1e8,
    "num_tiles": 2.5,
    "reachable_production_0": 2.0,
    "reachable_production_1": 1e4,
    "buildable_nodes": 1e3,
    "longest_road": 12,
    "hand_synergy": 1e2,
    "hand_resources": 2.5,
    "discard_penalty": -4,
    "hand_devs": 12,
    "army_size": 15,

    # NEW: Opponent threat modeling
    "opponent_max_vps": -2e14,          # Heavy penalty if opponent close to winning
    "opponent_vp_差": 5e13,              # Bonus for VP lead
    "turns_to_opponent_win": 1e13,      # Urgency based on opponent progress

    # NEW: Strategic features
    "port_access_2to1": 5e6,            # Value 2:1 ports highly
    "port_access_3to1": 1e6,            # Value 3:1 ports
    "card_diversity": 5e5,              # Diverse resources = more options
    "development_card_advantage": 5e6,   # More dev cards than opponents

    # NEW: Defensive features
    "settlement_vulnerability": -3e5,    # Penalize isolated settlements
    "robber_blocking_value": 3e7,       # Value of robber placement
}


def super_value_fn(params=SUPER_WEIGHTS):
    """Enhanced value function with opponent modeling and strategic awareness."""

    def fn(game, p0_color):
        # ===== EXISTING FEATURES (from base_fn) =====
        production_features = build_production_features(True)
        our_production_sample = production_features(game, p0_color)
        enemy_production_sample = production_features(game, p0_color)
        production = value_production(our_production_sample, "P0")
        enemy_production = value_production(enemy_production_sample, "P1", False)

        key = player_key(game.state, p0_color)
        our_vps = game.state.player_state[f"{key}_VICTORY_POINTS"]
        longest_road_length = get_longest_road_length(game.state, p0_color)

        reachability_sample = reachability_features(game, p0_color, 2)
        features = [f"P0_0_ROAD_REACHABLE_{resource}" for resource in RESOURCES]
        reachable_production_at_zero = sum([reachability_sample[f] for f in features])
        features = [f"P0_1_ROAD_REACHABLE_{resource}" for resource in RESOURCES]
        reachable_production_at_one = sum([reachability_sample[f] for f in features])

        hand_sample = resource_hand_features(game, p0_color)
        distance_to_city = (
            max(2 - hand_sample["P0_WHEAT_IN_HAND"], 0)
            + max(3 - hand_sample["P0_ORE_IN_HAND"], 0)
        ) / 5.0
        distance_to_settlement = (
            max(1 - hand_sample["P0_WHEAT_IN_HAND"], 0)
            + max(1 - hand_sample["P0_SHEEP_IN_HAND"], 0)
            + max(1 - hand_sample["P0_BRICK_IN_HAND"], 0)
            + max(1 - hand_sample["P0_WOOD_IN_HAND"], 0)
        ) / 4.0
        hand_synergy = (2 - distance_to_city - distance_to_settlement) / 2

        num_in_hand = player_num_resource_cards(game.state, p0_color)
        discard_penalty = params["discard_penalty"] if num_in_hand > 7 else 0

        buildings = game.state.buildings_by_color[p0_color]
        owned_nodes = buildings[SETTLEMENT] + buildings[CITY]
        owned_tiles = set()
        for n in owned_nodes:
            owned_tiles.update(game.state.board.map.adjacent_tiles[n])
        num_tiles = len(owned_tiles)

        num_buildable_nodes = len(game.state.board.buildable_node_ids(p0_color))
        longest_road_factor = params["longest_road"] if num_buildable_nodes == 0 else 0.1

        our_dev_cards = player_num_dev_cards(game.state, p0_color)
        our_knights = get_played_dev_cards(game.state, p0_color, "KNIGHT")

        # ===== NEW FEATURES: Opponent Modeling =====
        opponent_colors = [c for c in game.state.colors if c != p0_color]
        opponent_vps = []
        opponent_dev_cards = []

        for opp_color in opponent_colors:
            opp_key = player_key(game.state, opp_color)
            opp_vp = game.state.player_state[f"{opp_key}_VICTORY_POINTS"]
            opponent_vps.append(opp_vp)
            opponent_dev_cards.append(player_num_dev_cards(game.state, opp_color))

        # Find most threatening opponent
        max_opponent_vp = max(opponent_vps) if opponent_vps else 0
        vp_lead = our_vps - max_opponent_vp
        turns_to_opponent_win = max(0, 10 - max_opponent_vp)

        # Development card advantage
        avg_opponent_dev_cards = sum(opponent_dev_cards) / len(opponent_dev_cards) if opponent_dev_cards else 0
        dev_card_advantage = our_dev_cards - avg_opponent_dev_cards

        # ===== NEW FEATURES: Card Diversity =====
        resource_types_count = sum([
            hand_sample["P0_WHEAT_IN_HAND"] > 0,
            hand_sample["P0_ORE_IN_HAND"] > 0,
            hand_sample["P0_SHEEP_IN_HAND"] > 0,
            hand_sample["P0_WOOD_IN_HAND"] > 0,
            hand_sample["P0_BRICK_IN_HAND"] > 0,
        ])

        # ===== NEW FEATURES: Port Access =====
        # Check if player has access to ports
        port_access_2to1 = 0
        port_access_3to1 = 0

        # Get ports from board (if available in state)
        if hasattr(game.state.board, 'map') and hasattr(game.state.board.map, 'port_nodes'):
            for port_node in game.state.board.map.port_nodes:
                if port_node in owned_nodes:
                    port_resource = game.state.board.map.port_nodes.get(port_node)
                    if port_resource is None:  # 3:1 port
                        port_access_3to1 = 1
                    else:  # 2:1 port
                        port_access_2to1 = 1
                        break  # Having any 2:1 is valuable enough

        # ===== NEW FEATURES: Settlement Vulnerability =====
        # Simplified: More settlements without cities can be a weakness
        # A more sophisticated version would check road connectivity
        vulnerable_settlements = len(buildings[SETTLEMENT])
        # If we have cities, settlements are more protected
        if len(buildings[CITY]) > 0:
            vulnerable_settlements = max(0, vulnerable_settlements - len(buildings[CITY]))

        # ===== NEW FEATURES: Robber Value =====
        # Value the ability to block opponent's best tile
        robber_value = 0
        if hasattr(game.state.board, 'robber_coordinate'):
            # Calculate which tile would hurt opponents most
            # This is a simplified heuristic - real implementation would be more complex
            robber_value = 1 if max_opponent_vp > 5 else 0

        # ===== COMBINE ALL FEATURES =====
        base_value = float(
            # Original features
            our_vps * params["public_vps"]
            + production * params["production"]
            + enemy_production * params["enemy_production"]
            + reachable_production_at_zero * params["reachable_production_0"]
            + reachable_production_at_one * params["reachable_production_1"]
            + hand_synergy * params["hand_synergy"]
            + num_buildable_nodes * params["buildable_nodes"]
            + num_tiles * params["num_tiles"]
            + num_in_hand * params["hand_resources"]
            + discard_penalty
            + longest_road_length * longest_road_factor
            + our_dev_cards * params["hand_devs"]
            + our_knights * params["army_size"]
        )

        strategic_value = float(
            # NEW: Opponent modeling
            max_opponent_vp * params["opponent_max_vps"]
            + vp_lead * params["opponent_vp_差"]
            + turns_to_opponent_win * params["turns_to_opponent_win"]

            # NEW: Strategic features
            + port_access_2to1 * params["port_access_2to1"]
            + port_access_3to1 * params["port_access_3to1"]
            + resource_types_count * params["card_diversity"]
            + dev_card_advantage * params["development_card_advantage"]

            # NEW: Defensive features
            + vulnerable_settlements * params["settlement_vulnerability"]
            + robber_value * params["robber_blocking_value"]
        )

        return base_value + strategic_value

    return fn


class SuperAlphaPlayer(Player):
    """
    Enhanced AlphaBeta player with:
    - Iterative deepening for adaptive depth
    - Smart action ordering for better pruning
    - Enhanced value function with opponent awareness
    """

    def __init__(
        self,
        color,
        max_depth=4,
        prunning=True,
        params=SUPER_WEIGHTS,
        epsilon=None,
    ):
        super().__init__(color)
        self.max_depth = int(max_depth)
        self.prunning = str(prunning).lower() != "false"
        self.params = params
        self.epsilon = epsilon
        self.value_fn = super_value_fn(params)

    def get_actions(self, game):
        if self.prunning:
            return list_prunned_actions(game)
        return game.state.playable_actions

    def quick_evaluate(self, game, action):
        """Quick heuristic evaluation for action ordering."""
        game_copy = game.copy()
        game_copy.execute(action)
        return self.value_fn(game_copy, self.color)

    def decide(self, game: Game, playable_actions):
        actions = self.get_actions(game)
        if len(actions) == 1:
            return actions[0]

        if self.epsilon is not None and random.random() < self.epsilon:
            return random.choice(playable_actions)

        # Order actions by quick heuristic evaluation (best first)
        # This improves alpha-beta pruning efficiency
        ordered_actions = self._order_actions(game, actions)

        # Iterative deepening: start at depth 1, increase until time runs out
        start = time.time()
        deadline = start + MAX_SEARCH_TIME_SECS
        best_action = None

        for depth in range(INITIAL_DEPTH, self.max_depth + 1):
            time_remaining = deadline - time.time()
            if time_remaining < 0.5:  # Need at least 0.5s for a search
                break

            node = DebugStateNode(f"depth_{depth}", self.color)
            result = self.alphabeta(
                game.copy(),
                depth,
                float("-inf"),
                float("inf"),
                deadline,
                node,
                ordered_actions
            )

            if result[0] is not None:
                best_action = result[0]
                # print(f"SuperAlpha completed depth {depth} in {time.time() - start:.2f}s")

            # If we ran out of time, stop
            if time.time() >= deadline - 0.1:
                break

        return best_action if best_action is not None else playable_actions[0]

    def _order_actions(self, game, actions):
        """Order actions by quick evaluation (best first) for better pruning."""
        if len(actions) <= 1:
            return actions

        # Quick evaluation of each action
        action_values = []
        for action in actions:
            try:
                value = self.quick_evaluate(game, action)
                action_values.append((action, value))
            except:
                # If evaluation fails, give it neutral value
                action_values.append((action, 0))

        # Sort by value (descending - best first)
        action_values.sort(key=lambda x: x[1], reverse=True)
        return [action for action, _ in action_values]

    def alphabeta(self, game, depth, alpha, beta, deadline, node, ordered_actions=None):
        """AlphaBeta MiniMax with iterative deepening support."""

        # Terminal conditions
        if depth == 0 or game.winning_color() is not None or time.time() >= deadline:
            value = self.value_fn(game, self.color)
            node.expected_value = value
            return None, value

        maximizingPlayer = game.state.current_color() == self.color

        # Use pre-ordered actions if available, otherwise get and order them
        if ordered_actions is None:
            actions = self.get_actions(game)
            if maximizingPlayer and len(actions) > 1:
                actions = self._order_actions(game, actions)
        else:
            actions = ordered_actions

        action_outcomes = expand_spectrum(game, actions)

        if maximizingPlayer:
            best_action = None
            best_value = float("-inf")

            for i, (action, outcomes) in enumerate(action_outcomes.items()):
                action_node = DebugActionNode(action)
                expected_value = 0

                for j, (outcome, proba) in enumerate(outcomes):
                    out_node = DebugStateNode(
                        f"{node.label}_{i}_{j}", outcome.state.current_color()
                    )

                    result = self.alphabeta(
                        outcome, depth - 1, alpha, beta, deadline, out_node
                    )
                    value = result[1]
                    expected_value += proba * value

                    action_node.children.append(out_node)
                    action_node.probas.append(proba)

                action_node.expected_value = expected_value
                node.children.append(action_node)

                if expected_value > best_value:
                    best_action = action
                    best_value = expected_value

                alpha = max(alpha, best_value)
                if alpha >= beta:
                    break  # Beta cutoff

            node.expected_value = best_value
            return best_action, best_value
        else:
            best_action = None
            best_value = float("inf")

            for i, (action, outcomes) in enumerate(action_outcomes.items()):
                action_node = DebugActionNode(action)
                expected_value = 0

                for j, (outcome, proba) in enumerate(outcomes):
                    out_node = DebugStateNode(
                        f"{node.label}_{i}_{j}", outcome.state.current_color()
                    )

                    result = self.alphabeta(
                        outcome, depth - 1, alpha, beta, deadline, out_node
                    )
                    value = result[1]
                    expected_value += proba * value

                    action_node.children.append(out_node)
                    action_node.probas.append(proba)

                action_node.expected_value = expected_value
                node.children.append(action_node)

                if expected_value < best_value:
                    best_action = action
                    best_value = expected_value

                beta = min(beta, best_value)
                if beta <= alpha:
                    break  # Alpha cutoff

            node.expected_value = best_value
            return best_action, best_value

    def __repr__(self) -> str:
        return (
            super().__repr__()
            + f"(max_depth={self.max_depth},prunning={self.prunning})"
        )


class DebugStateNode:
    def __init__(self, label, color):
        self.label = label
        self.children = []
        self.expected_value = None
        self.color = color


class DebugActionNode:
    def __init__(self, action):
        self.action = action
        self.expected_value: Any = None
        self.children = []
        self.probas = []
