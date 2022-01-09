import time
from collections import defaultdict
import logging

import coloredlogs
import click
import termplotlib as tpl
import numpy as np
import pandas as pd

from catanatron.state import player_key
from catanatron_server.utils import ensure_link
from catanatron_server.models import database_session, upsert_game_state
from catanatron.game import Game
from catanatron.models.player import HumanPlayer, RandomPlayer, Color
from catanatron.players.weighted_random import WeightedRandomPlayer

from catanatron_gym.features import create_sample
from catanatron_gym.envs.catanatron_env import to_action_space

from catanatron_experimental.my_player import MyPlayer
from catanatron_experimental.mcts_score_collector import (
    MCTSScoreCollector,
    MCTSPredictor,
)
from catanatron_experimental.machine_learning.players.reinforcement import (
    QRLPlayer,
    TensorRLPlayer,
    VRLPlayer,
    PRLPlayer,
)
from catanatron_experimental.utils import formatSecs
from catanatron_experimental.tensorforce_player import ForcePlayer
from catanatron_experimental.machine_learning.players.minimax import (
    AlphaBetaPlayer,
    ValueFunctionPlayer,
)
from catanatron.players.search import (
    VictoryPointPlayer,
)
from catanatron_experimental.machine_learning.players.mcts import MCTSPlayer
from catanatron_experimental.machine_learning.players.scikit import ScikitPlayer
from catanatron_experimental.machine_learning.players.playouts import (
    GreedyPlayoutsPlayer,
)
from catanatron_experimental.machine_learning.players.online_mcts_dqn import (
    OnlineMCTSDQNPlayer,
)
from catanatron_experimental.dqn_player import DQNPlayer
from catanatron_experimental.machine_learning.board_tensor_features import (
    create_board_tensor,
)
from catanatron_experimental.machine_learning.utils import (
    get_discounted_return,
    get_tournament_return,
    get_victory_points_return,
    populate_matrices,
    DISCOUNT_FACTOR,
)

# Create a logger object.
logger = logging.getLogger(__name__)

# If you don't want to see log messages from libraries, you can pass a
# specific logger object to the install() function. In this case only log
# messages originating from that logger will show up on the terminal.
coloredlogs.install(
    level="DEBUG",
    logger=logger,
    fmt="%(asctime)s,%(msecs)03d %(levelname)s %(message)s",
)

LOG_IN_TF = False
RUNNING_AVG_LENGTH = 1

if LOG_IN_TF:
    import tensorflow as tf


PLAYER_CLASSES = {
    "R": RandomPlayer,
    "H": HumanPlayer,
    "W": WeightedRandomPlayer,
    "O": OnlineMCTSDQNPlayer,
    "S": ScikitPlayer,
    "VP": VictoryPointPlayer,
    "F": ValueFunctionPlayer,
    "Y": MyPlayer,
    # Tree Search Players
    "G": GreedyPlayoutsPlayer,
    "M": MCTSPlayer,
    "AB": AlphaBetaPlayer,
    # Used like: --players=V:path/to/model.model,T:path/to.model
    "C": ForcePlayer,
    "VRL": VRLPlayer,
    "Q": QRLPlayer,
    "P": PRLPlayer,
    "T": TensorRLPlayer,
    "D": DQNPlayer,
    "CO": MCTSScoreCollector,
    "COP": MCTSPredictor,
}


@click.command()
@click.option("-n", "--num", default=5, help="Number of games to play.")
@click.option(
    "--players",
    default="R,R,R,R",
    help=f"""
        Comma-separated players to use. Use : to specify additional params.\n
        (e.g. --players=R,G:25,AB:2:C,W).\n
        {", ".join(map(lambda e: f"{e[0]}={e[1].__name__}", PLAYER_CLASSES.items()))}
        """,
)
@click.option(
    "-o",
    "--outpath",
    default=None,
    help="Path where to save ML csvs.",
)
@click.option(
    "--save-in-db/--no-save-in-db",
    default=False,
    help="""
        Whether to save final state to database to allow for viewing.
        """,
)
@click.option(
    "--watch/--no-watch",
    default=False,
    help="""
        Whether to save intermediate states to database to allow for viewing.
        This will artificially slow down the game by 1s per move.
        """,
)
@click.option(
    "--loglevel",
    default="DEBUG",
    help="Controls verbosity. Values: DEBUG, INFO, ERROR",
)
def simulate(num, players, outpath, save_in_db, watch, loglevel):
    """Simple program simulates NUM Catan games."""
    player_keys = players.split(",")

    initialized_players = []
    colors = [c for c in Color]
    for i, key in enumerate(player_keys):
        player_keys = sorted(PLAYER_CLASSES.keys(), key=lambda x: -len(x))
        for player_key in player_keys:
            player_class = PLAYER_CLASSES[player_key]
            if key.startswith(player_key):
                params = [colors[i]] + key.split(":")[1:]
                initialized_players.append(player_class(*params))
                break

    play_batch(num, initialized_players, outpath, save_in_db, watch, loglevel)


def play_batch(
    num_games,
    players,
    games_directory=None,
    save_in_db=False,
    watch=False,
    loglevel="DEBUG",
):
    """Plays num_games, saves final game in database, and populates data/ matrices"""
    logger.setLevel(loglevel)

    wins = defaultdict(int)
    turns = []
    ticks = []
    durations = []
    games = []
    results_by_player = defaultdict(list)
    if LOG_IN_TF:
        writer = tf.summary.create_file_writer(f"logs/play/{int(time.time())}")
    for i in range(num_games):
        for player in players:
            player.reset_state()
        game = Game(players)

        logger.debug(
            f"Playing game {i + 1} / {num_games}. Seating: {game.state.players}"
        )
        action_callbacks = []
        if games_directory:
            action_callbacks.append(build_action_callback(games_directory))
        if watch:
            with database_session() as session:
                upsert_game_state(game, session)

            def callback(game):
                with database_session() as session:
                    upsert_game_state(game, session)
                time.sleep(0.25)

            action_callbacks.append(callback)
            logger.debug(
                f"Watch game by refreshing http://localhost:3000/games/{game.id}/states/latest"
            )

        start = time.time()
        game.play(action_callbacks)
        duration = time.time() - start
        logger.debug(
            str(
                {
                    str(p): game.state.player_state[
                        f"{player_key(game.state, p.color)}_ACTUAL_VICTORY_POINTS"
                    ]
                    for p in players
                }
            )
            + f" ({duration:.3g} secs) [{game.winning_color()}:{game.state.num_turns}({len(game.state.actions)})]"
        )
        if save_in_db and not watch:
            link = ensure_link(game)
            logger.info(f"Saved in db. See result at: {link}")

        winning_color = game.winning_color()
        if winning_color is None:
            continue

        wins[winning_color] += 1
        turns.append(game.state.num_turns)
        ticks.append(len(game.state.actions))
        durations.append(duration)
        games.append(game)
        for player in players:
            key = player_key(game.state, player.color)
            points = game.state.player_state[f"{key}_ACTUAL_VICTORY_POINTS"]
            results_by_player[player.color].append(points)
        if LOG_IN_TF:
            with writer.as_default():
                for player in players:
                    results = results_by_player[player.color]
                    last_results = results[len(results) - RUNNING_AVG_LENGTH :]
                    if len(last_results) >= RUNNING_AVG_LENGTH:
                        running_avg = sum(last_results) / len(last_results)
                        tf.summary.scalar(
                            f"{player.color}-vp-running-avg", running_avg, step=i
                        )
                writer.flush()

    logger.info(f"AVG Ticks: {sum(ticks) / len(ticks)}")
    logger.info(f"AVG Turns: {sum(turns) / len(turns)}")
    logger.info(f"AVG Duration: {formatSecs(sum(durations) / len(durations))}")

    for player in players:
        vps = results_by_player[player.color]
        logger.info(f"AVG VPS: {player} {sum(vps) / len(vps)}")

    # Print Winners graph in command line:
    fig = tpl.figure()
    fig.barh([wins[p.color] for p in players], players, force_ascii=False)
    for row in fig.get_string().split("\n"):
        logger.info(row)

    if games_directory:
        logger.info(f"GZIP CSVs saved at: {games_directory}")

    return dict(wins), dict(results_by_player), games


def build_action_callback(games_directory):
    import tensorflow as tf

    data = defaultdict(lambda: {"samples": [], "actions": [], "board_tensors": []})

    def action_callback(game: Game):
        if len(game.state.actions) == 0:
            return

        action = game.state.actions[-1]  # the action that just happened

        data[action.color]["samples"].append(create_sample(game, action.color))
        data[action.color]["actions"].append(to_action_space(action))
        board_tensor = create_board_tensor(game, action.color)
        shape = board_tensor.shape
        flattened_tensor = tf.reshape(
            board_tensor, (shape[0] * shape[1] * shape[2],)
        ).numpy()
        data[action.color]["board_tensors"].append(flattened_tensor)

        if game.winning_color() is not None:
            # for color in game.state.colors:
            #     data[color]["samples"].append(create_sample(game, color))
            flush_to_matrices(game, data, games_directory)

    return action_callback


def flush_to_matrices(game, data, games_directory):
    print("Flushing to matrices...")
    t1 = time.time()
    samples = []
    actions = []
    board_tensors = []
    labels = []
    for color in game.state.colors:
        player_data = data[color]

        # Make matrix of (RETURN, DISCOUNTED_RETURN, TOURNAMENT_RETURN, DISCOUNTED_TOURNAMENT_RETURN)
        episode_return = get_discounted_return(game, color, 1)
        discounted_return = get_discounted_return(game, color, DISCOUNT_FACTOR)
        tournament_return = get_tournament_return(game, color, 1)
        vp_return = get_victory_points_return(game, color)
        discounted_tournament_return = get_tournament_return(
            game, color, DISCOUNT_FACTOR
        )

        samples.extend(player_data["samples"])
        actions.extend(player_data["actions"])
        board_tensors.extend(player_data["board_tensors"])
        return_matrix = np.tile(
            [
                [
                    episode_return,
                    discounted_return,
                    tournament_return,
                    discounted_tournament_return,
                    vp_return,
                ]
            ],
            (len(player_data["samples"]), 1),
        )
        labels.extend(return_matrix)

    # Build Q-learning Design Matrix
    samples_df = (
        pd.DataFrame.from_records(samples, columns=sorted(samples[0].keys()))
        .astype("float64")
        .add_prefix("F_")
    )
    board_tensors_df = pd.DataFrame(board_tensors).astype("float64").add_prefix("BT_")
    actions_df = pd.DataFrame(actions, columns=["ACTION"]).astype("int")
    rewards_df = pd.DataFrame(
        labels,
        columns=[
            "RETURN",
            "DISCOUNTED_RETURN",
            "TOURNAMENT_RETURN",
            "DISCOUNTED_TOURNAMENT_RETURN",
            "VICTORY_POINTS_RETURN",
        ],
    ).astype("float64")
    main_df = pd.concat([samples_df, board_tensors_df, actions_df, rewards_df], axis=1)

    print(
        "Collected DataFrames. Data size:",
        "Main:",
        main_df.shape,
        "Samples:",
        samples_df.shape,
        "Board Tensors:",
        board_tensors_df.shape,
        "Actions:",
        actions_df.shape,
        "Rewards:",
        rewards_df.shape,
    )
    populate_matrices(
        samples_df,
        board_tensors_df,
        actions_df,
        rewards_df,
        main_df,
        games_directory,
    )
    print(
        "Saved to matrices at:", games_directory, ". Took", formatSecs(time.time() - t1)
    )
    return samples_df, board_tensors_df, actions_df, rewards_df


if __name__ == "__main__":
    simulate()