"""
SuperAlpha v2 - Adaptive Strategy with Game Phase Detection

Key improvements over v1:
1. Game phase detection (early/mid/late)
2. Adaptive weights that change based on game state
3. Simplified, more robust features
4. Better initial placement strategy
5. Reduced over-fitting to specific boards

Based on analysis showing v1 had high variance and poor early game performance.
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
)


MAX_SEARCH_TIME_SECS = 20
INITIAL_DEPTH = 1


class GamePhase:
    """Detect and classify game phase"""
    EARLY = "EARLY"    # Initial placement and first few turns
    MID = "MID"        # Building phase
    LATE = "LATE"      # Race to victory

    @staticmethod
    def detect(game, player_color):
        """Detect current game phase based on multiple factors"""
        state = game.state
        key = player_key(state, player_color)

        # Get game metrics
        num_turns = state.num_turns
        our_vps = state.player_state[f"{key}_VICTORY_POINTS"]

        # Get max opponent VP
        opponent_vps = []
        for color in state.colors:
            if color != player_color:
                opp_key = player_key(state, color)
                opp_vp = state.player_state[f"{opp_key}_VICTORY_POINTS"]
                opponent_vps.append(opp_vp)
        max_opponent_vp = max(opponent_vps) if opponent_vps else 0

        # LATE GAME: Anyone close to winning
        if our_vps >= 7 or max_opponent_vp >= 7:
            return GamePhase.LATE

        # EARLY GAME: Initial placement or very early turns
        if num_turns < 15 or our_vps < 3:
            return GamePhase.EARLY

        # MID GAME: Everything else
        return GamePhase.MID


# Phase-specific weights
EARLY_GAME_WEIGHTS = {
    # Early game: Focus on fundamentals
    "public_vps": 3e14,
    "production": 2e8,              # Production is CRITICAL early
    "num_tiles": 5.0,               # Tile diversity important
    "reachable_production_0": 5.0,
    "reachable_production_1": 2e4,  # Expansion potential
    "buildable_nodes": 2e3,         # Space to grow
    "hand_synergy": 1e2,
    "hand_resources": 2.0,
    "discard_penalty": -5,

    # Deemphasize opponent tracking early
    "enemy_production": -5e7,       # Less aggressive
    "opponent_max_vps": -1e13,      # Much lower weight
    "opponent_vp_lead": 1e12,       # Low priority

    # Strategic features (moderate)
    "port_access_2to1": 1e6,
    "port_access_3to1": 5e5,
    "card_diversity": 2e5,
}

MID_GAME_WEIGHTS = {
    # Mid game: Balanced strategy
    "public_vps": 3e14,
    "production": 1e8,
    "num_tiles": 3.0,
    "reachable_production_0": 3.0,
    "reachable_production_1": 1e4,
    "buildable_nodes": 1e3,
    "hand_synergy": 1e2,
    "hand_resources": 2.5,
    "discard_penalty": -4,

    # Moderate opponent tracking
    "enemy_production": -1e8,
    "opponent_max_vps": -1e14,
    "opponent_vp_lead": 3e13,

    # Strategic features active
    "port_access_2to1": 3e6,
    "port_access_3to1": 1e6,
    "card_diversity": 5e5,
    "development_card_advantage": 3e6,
    "longest_road": 15,
    "army_size": 15,
}

LATE_GAME_WEIGHTS = {
    # Late game: Race to victory, block opponents
    "public_vps": 3e14,
    "production": 5e7,              # Less important, it's too late
    "num_tiles": 1.0,
    "reachable_production_0": 1.0,
    "reachable_production_1": 5e3,
    "buildable_nodes": 5e2,
    "hand_synergy": 2e2,            # Building quickly matters
    "hand_resources": 3.0,
    "discard_penalty": -3,

    # HEAVY opponent tracking
    "enemy_production": -1e8,
    "opponent_max_vps": -3e14,      # CRITICAL: block wins!
    "opponent_vp_lead": 1e14,       # Huge bonus for being ahead

    # Strategic features (win conditions)
    "port_access_2to1": 2e6,
    "port_access_3to1": 5e5,
    "card_diversity": 3e5,
    "development_card_advantage": 1e7,  # Dev cards can win games
    "longest_road": 30,             # Worth more if it secures win
    "army_size": 30,
}


def adaptive_value_fn(phase_weights):
    """Create value function that uses phase-specific weights"""

    def fn(game, p0_color):
        # Determine game phase
        phase = GamePhase.detect(game, p0_color)

        # Select appropriate weights
        if phase == GamePhase.EARLY:
            params = EARLY_GAME_WEIGHTS
        elif phase == GamePhase.MID:
            params = MID_GAME_WEIGHTS
        else:  # LATE
            params = LATE_GAME_WEIGHTS

        # ===== CORE FEATURES (from AlphaBeta) =====
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
        longest_road_factor = params.get("longest_road", 10) if num_buildable_nodes == 0 else 0.1

        our_dev_cards = player_num_dev_cards(game.state, p0_color)
        our_knights = get_played_dev_cards(game.state, p0_color, "KNIGHT")

        # ===== OPPONENT FEATURES (scaled by phase) =====
        opponent_colors = [c for c in game.state.colors if c != p0_color]
        opponent_vps = []
        opponent_dev_cards = []

        for opp_color in opponent_colors:
            opp_key = player_key(game.state, opp_color)
            opp_vp = game.state.player_state[f"{opp_key}_VICTORY_POINTS"]
            opponent_vps.append(opp_vp)
            opponent_dev_cards.append(player_num_dev_cards(game.state, opp_color))

        max_opponent_vp = max(opponent_vps) if opponent_vps else 0
        vp_lead = our_vps - max_opponent_vp

        avg_opponent_dev_cards = sum(opponent_dev_cards) / len(opponent_dev_cards) if opponent_dev_cards else 0
        dev_card_advantage = our_dev_cards - avg_opponent_dev_cards

        # ===== STRATEGIC FEATURES (simplified) =====
        resource_types_count = sum([
            hand_sample["P0_WHEAT_IN_HAND"] > 0,
            hand_sample["P0_ORE_IN_HAND"] > 0,
            hand_sample["P0_SHEEP_IN_HAND"] > 0,
            hand_sample["P0_WOOD_IN_HAND"] > 0,
            hand_sample["P0_BRICK_IN_HAND"] > 0,
        ])

        # Port access (simplified check)
        port_access_2to1 = 0
        port_access_3to1 = 0
        if hasattr(game.state.board, 'map') and hasattr(game.state.board.map, 'port_nodes'):
            for port_node in game.state.board.map.port_nodes:
                if port_node in owned_nodes:
                    port_resource = game.state.board.map.port_nodes.get(port_node)
                    if port_resource is None:
                        port_access_3to1 = 1
                    else:
                        port_access_2to1 = 1
                        break

        # ===== COMBINE ALL FEATURES WITH PHASE-SPECIFIC WEIGHTS =====
        base_value = float(
            our_vps * params["public_vps"]
            + production * params["production"]
            + enemy_production * params.get("enemy_production", -1e8)
            + reachable_production_at_zero * params["reachable_production_0"]
            + reachable_production_at_one * params["reachable_production_1"]
            + hand_synergy * params["hand_synergy"]
            + num_buildable_nodes * params["buildable_nodes"]
            + num_tiles * params["num_tiles"]
            + num_in_hand * params["hand_resources"]
            + discard_penalty
            + longest_road_length * longest_road_factor
            + our_knights * params.get("army_size", 10)
        )

        strategic_value = float(
            max_opponent_vp * params.get("opponent_max_vps", -1e14)
            + vp_lead * params.get("opponent_vp_lead", 1e13)
            + port_access_2to1 * params.get("port_access_2to1", 1e6)
            + port_access_3to1 * params.get("port_access_3to1", 5e5)
            + resource_types_count * params.get("card_diversity", 5e5)
            + dev_card_advantage * params.get("development_card_advantage", 5e6)
        )

        return base_value + strategic_value

    return fn


class SuperAlphaV2Player(Player):
    """
    SuperAlpha v2 with game phase detection and adaptive strategy.

    Improvements over v1:
    - Detects game phase (early/mid/late)
    - Adapts weights based on phase
    - Simpler, more robust features
    - Better early game performance
    - Reduced variance across boards
    """

    def __init__(
        self,
        color,
        max_depth=3,  # Reduced from 4 for better early game
        prunning=True,
        epsilon=None,
    ):
        super().__init__(color)
        self.max_depth = int(max_depth)
        self.prunning = str(prunning).lower() != "false"
        self.epsilon = epsilon
        self.value_fn = adaptive_value_fn(None)  # Will select phase internally

    def get_actions(self, game):
        if self.prunning:
            return list_prunned_actions(game)
        return game.state.playable_actions

    def quick_evaluate(self, game, action):
        """Quick heuristic evaluation for action ordering"""
        game_copy = game.copy()
        game_copy.execute(action)
        return self.value_fn(game_copy, self.color)

    def decide(self, game: Game, playable_actions):
        actions = self.get_actions(game)
        if len(actions) == 1:
            return actions[0]

        if self.epsilon is not None and random.random() < self.epsilon:
            return random.choice(playable_actions)

        # Detect game phase for potential optimizations
        phase = GamePhase.detect(game, self.color)

        # Early game: Be more careful, use less depth to avoid timeout
        if phase == GamePhase.EARLY:
            max_depth = min(self.max_depth, 2)
        else:
            max_depth = self.max_depth

        # Order actions by quick heuristic
        ordered_actions = self._order_actions(game, actions)

        # Iterative deepening
        start = time.time()
        deadline = start + MAX_SEARCH_TIME_SECS
        best_action = None

        for depth in range(INITIAL_DEPTH, max_depth + 1):
            time_remaining = deadline - time.time()
            if time_remaining < 0.5:
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

            if time.time() >= deadline - 0.1:
                break

        return best_action if best_action is not None else playable_actions[0]

    def _order_actions(self, game, actions):
        """Order actions by quick evaluation (best first)"""
        if len(actions) <= 1:
            return actions

        action_values = []
        for action in actions:
            try:
                value = self.quick_evaluate(game, action)
                action_values.append((action, value))
            except:
                action_values.append((action, 0))

        action_values.sort(key=lambda x: x[1], reverse=True)
        return [action for action, _ in action_values]

    def alphabeta(self, game, depth, alpha, beta, deadline, node, ordered_actions=None):
        """AlphaBeta with phase-adaptive evaluation"""

        if depth == 0 or game.winning_color() is not None or time.time() >= deadline:
            value = self.value_fn(game, self.color)
            node.expected_value = value
            return None, value

        maximizingPlayer = game.state.current_color() == self.color

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
                    break

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
                    break

            node.expected_value = best_value
            return best_action, best_value

    def __repr__(self) -> str:
        return (
            super().__repr__()
            + f"V2(max_depth={self.max_depth},adaptive_weights,prunning={self.prunning})"
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
