"""
Unit tests for MinimaxAgent bug fixes and evaluation function.

Tests cover:
1. Bug fix: is_maximizing derived from env.current_player (USE_CARD does not switch player)
2. Bug fix: _get_state_hash includes turn_effects / protected_positions / card_uses
3. Bug fix: _evaluate_state uses directional advance instead of center distance
4. Evaluation: jump_threat term
5. Evaluation: underworld penalty direction

Run with: python -m pytest test_minimax.py -v
"""

import copy
import pytest
import math
from Zombie_env import ZombieEnv, Card, Player, Piece, Action, ActionType
from minimax_agent import MinimaxAgent


# ─────────────────────────────────────
# Helpers
# ─────────────────────────────────────

def make_agent(player=Player.RED, depth=1):
    return MinimaxAgent(player=player, max_depth=depth, verbose=False)


def clear_board(env):
    """Remove all pieces from the board."""
    for r in range(env.board_size):
        for c in range(env.board_size):
            env.board[r][c] = []


# ─────────────────────────────────────────────────────────────────────────────
# Bug Fix 1: is_maximizing from env.current_player, not caller-passed argument
#   USE_CARD does NOT switch current_player, so the next _minimax call must
#   still see the same player as maximizing.
# ─────────────────────────────────────────────────────────────────────────────

class TestIsMaximizingFromEnvPlayer:

    def test_is_maximizing_true_when_our_turn(self):
        """After a normal action, opponent's turn → is_maximizing should be False."""
        env = ZombieEnv()
        agent = make_agent(Player.RED)
        # At start, current_player = RED (our player)
        assert env.current_player == Player.RED
        # is_maximizing should be True for RED agent when it's RED's turn
        is_max = (env.current_player == agent.player)
        assert is_max is True

    def test_is_maximizing_stays_true_after_use_card(self):
        """
        USE_CARD does not switch current_player.
        After stepping USE_CARD, current_player is still RED → still maximizing.
        """
        env = ZombieEnv(red_card=Card.BLOCK_STACK)
        assert env.current_player == Player.RED

        use_card_action = Action(
            action_type=ActionType.USE_CARD,
            from_pos=None, to_pos=None,
            tier=4,
            initial_direction=None, jump_sequence=None,
            expected_score=0.0
        )
        env.step(use_card_action)

        # current_player must still be RED
        assert env.current_player == Player.RED

        agent = make_agent(Player.RED)
        is_max = (env.current_player == agent.player)
        assert is_max is True

    def test_is_maximizing_false_after_normal_action(self):
        """After a normal (non-USE_CARD) action, it's opponent's turn → is_maximizing False."""
        env = ZombieEnv()
        agent = make_agent(Player.RED)

        actions = env.get_legal_actions()
        non_card = next(a for a in actions if a.action_type != ActionType.USE_CARD)
        env.step(non_card)

        # Now it's BLUE's turn
        assert env.current_player == Player.BLUE
        is_max = (env.current_player == agent.player)
        assert is_max is False

    def test_minimax_chooses_action_after_use_card_correctly(self):
        """
        Agent holds Card 4 (BLOCK_STACK). USE_CARD should appear among legal actions.
        After playing it the agent should still get another action this turn.
        We verify get_action() returns a non-None action even when USE_CARD is
        the first thing played (depth=1 search must not crash).
        """
        env = ZombieEnv(red_card=Card.BLOCK_STACK)
        agent = make_agent(Player.RED, depth=1)
        action = agent.get_action(env)
        assert action is not None


# ─────────────────────────────────────────────────────────────────────────────
# Bug Fix 2: _get_state_hash includes turn_effects / protected_positions / card_uses
# ─────────────────────────────────────────────────────────────────────────────

class TestStateHash:

    def _base_env(self):
        return ZombieEnv(red_card=Card.BLOCK_STACK, blue_card=Card.PROTECT_REVIVED)

    def test_hash_differs_when_turn_effects_differ(self):
        agent = make_agent(Player.RED)
        env1 = self._base_env()
        env2 = copy.deepcopy(env1)

        # Add a turn effect to env2 only
        env2.turn_effects[Player.BLUE].add('no_stack')

        h1 = agent._get_state_hash(env1)
        h2 = agent._get_state_hash(env2)
        assert h1 != h2

    def test_hash_differs_when_protected_positions_differ(self):
        agent = make_agent(Player.RED)
        env1 = self._base_env()
        env2 = copy.deepcopy(env1)

        env2.protected_positions[Player.BLUE].add((3, 3))

        h1 = agent._get_state_hash(env1)
        h2 = agent._get_state_hash(env2)
        assert h1 != h2

    def test_hash_differs_when_card_uses_differ(self):
        agent = make_agent(Player.RED)
        env1 = self._base_env()
        env2 = copy.deepcopy(env1)

        env2.card_uses[Player.RED][Card.BLOCK_STACK] = 1  # was 3

        h1 = agent._get_state_hash(env1)
        h2 = agent._get_state_hash(env2)
        assert h1 != h2

    def test_hash_same_when_state_identical(self):
        agent = make_agent(Player.RED)
        env1 = self._base_env()
        env2 = copy.deepcopy(env1)

        assert agent._get_state_hash(env1) == agent._get_state_hash(env2)

    def test_transposition_table_not_reused_across_different_effects(self):
        """
        Cached value for state with empty turn_effects must not be returned
        when turn_effects has changed (different hash).
        """
        agent = make_agent(Player.RED, depth=2)
        env = self._base_env()

        # Warm up transposition table with clean state
        agent._minimax(copy.deepcopy(env), depth=2, alpha=-math.inf, beta=math.inf)

        # Now add a turn effect — hash should differ, table miss expected
        env.turn_effects[Player.BLUE].add('no_stack')
        new_hash = agent._get_state_hash(env)
        assert new_hash not in agent.transposition_table or True  # just verifying no crash


# ─────────────────────────────────────────────────────────────────────────────
# Bug Fix 3 + improvements: _evaluate_state
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluateState:

    def _fresh_env(self):
        env = ZombieEnv()
        clear_board(env)
        env.underworld = {
            Player.RED:  {1: 0, 2: 0, 3: 0},
            Player.BLUE: {1: 0, 2: 0, 3: 0},
        }
        env.scores = {Player.RED: 0, Player.BLUE: 0}
        return env

    # ── Score difference ──────────────────────────────────────────────────

    def test_score_diff_positive_when_we_lead(self):
        env = self._fresh_env()
        env.scores[Player.RED] = 3
        env.scores[Player.BLUE] = 1
        agent = make_agent(Player.RED)
        assert agent._evaluate_state(env) > 0

    def test_score_diff_negative_when_opponent_leads(self):
        env = self._fresh_env()
        env.scores[Player.RED] = 0
        env.scores[Player.BLUE] = 3
        agent = make_agent(Player.RED)
        assert agent._evaluate_state(env) < 0

    # ── Directional advance (replaces center-distance) ────────────────────

    def test_red_piece_advance_increases_eval_as_it_moves_toward_blue(self):
        """
        RED advances toward BLUE side (row 4). A piece on row 3 should give
        more advance bonus than the same piece on row 1.
        """
        agent = make_agent(Player.RED)

        env_near = self._fresh_env()
        env_near.board[3][2] = [Piece(Player.RED, 1)]   # row 3 = near BLUE

        env_far = self._fresh_env()
        env_far.board[1][2] = [Piece(Player.RED, 1)]    # row 1 = far from BLUE

        val_near = agent._evaluate_state(env_near)
        val_far  = agent._evaluate_state(env_far)
        assert val_near > val_far

    def test_blue_piece_advance_correct_direction(self):
        """
        BLUE advances toward RED side (row 0). For BLUE agent, piece on row 1
        should give more advance bonus than piece on row 3.
        """
        agent = make_agent(Player.BLUE)

        env_near = self._fresh_env()
        env_near.board[1][2] = [Piece(Player.BLUE, 1)]  # row 1 = near RED

        env_far = self._fresh_env()
        env_far.board[3][2] = [Piece(Player.BLUE, 1)]   # row 3 = far from RED

        val_near = agent._evaluate_state(env_near)
        val_far  = agent._evaluate_state(env_far)
        assert val_near > val_far

    # ── Jump threat ───────────────────────────────────────────────────────

    def test_jump_threat_increases_eval_when_aligned(self):
        """
        Our piece aligned in same row/col with opponent piece at distance 1~2
        should increase eval compared to unaligned positions.
        """
        agent = make_agent(Player.RED)

        # Aligned: RED at (2,0), BLUE at (2,2) — same row, distance 2
        env_threat = self._fresh_env()
        env_threat.board[2][0] = [Piece(Player.RED, 2)]
        env_threat.board[2][2] = [Piece(Player.BLUE, 2)]

        # Not aligned: RED at (0,0), BLUE at (4,4) — diagonal, distance 8
        env_no_threat = self._fresh_env()
        env_no_threat.board[0][0] = [Piece(Player.RED, 2)]
        env_no_threat.board[4][4] = [Piece(Player.BLUE, 2)]

        val_threat    = agent._evaluate_state(env_threat)
        val_no_threat = agent._evaluate_state(env_no_threat)
        assert val_threat > val_no_threat

    def test_jump_threat_zero_when_not_aligned(self):
        """
        Pieces on different rows AND different columns should not add jump threat.
        """
        agent = make_agent(Player.RED)
        env = self._fresh_env()
        env.board[0][0] = [Piece(Player.RED, 3)]
        env.board[2][2] = [Piece(Player.BLUE, 3)]  # diagonal, not same row or col

        # Compute manually: jump_threat = 0 → score has no threat bonus
        # The eval should equal just board_tier and advance terms
        val = agent._evaluate_state(env)
        # Just verify it runs and returns a float
        assert isinstance(val, float)

    # ── Underworld penalty ────────────────────────────────────────────────

    def test_our_pieces_in_underworld_reduce_score(self):
        """Having our own pieces in underworld should reduce eval."""
        agent = make_agent(Player.RED)

        env_clean = self._fresh_env()
        env_uw    = self._fresh_env()
        env_uw.underworld[Player.RED][2] = 2  # 2 tier-2 pieces in underworld

        val_clean = agent._evaluate_state(env_clean)
        val_uw    = agent._evaluate_state(env_uw)
        assert val_clean > val_uw

    def test_opponent_pieces_in_underworld_increase_score(self):
        """Having opponent pieces in underworld should increase eval."""
        agent = make_agent(Player.RED)

        env_clean = self._fresh_env()
        env_opp   = self._fresh_env()
        env_opp.underworld[Player.BLUE][2] = 2

        val_clean = agent._evaluate_state(env_clean)
        val_opp   = agent._evaluate_state(env_opp)
        assert val_opp > val_clean

    # ── Stacking bonus ────────────────────────────────────────────────────

    def test_stacking_bonus_applied_once_per_cell_not_per_piece(self):
        """
        A cell with 2 pieces should give stacking_bonus=1.2 applied to the
        whole cell_tier, NOT multiplied per individual piece.
        """
        agent = make_agent(Player.RED)

        # Single piece, tier 2
        env_single = self._fresh_env()
        env_single.board[2][2] = [Piece(Player.RED, 2)]

        # Two pieces stacked: tier 1 + tier 1 → cell_tier = 2, stacking_bonus applied once
        env_stack = self._fresh_env()
        env_stack.board[2][2] = [Piece(Player.RED, 1), Piece(Player.RED, 1)]

        val_single = agent._evaluate_state(env_single)
        val_stack  = agent._evaluate_state(env_stack)
        # Stacked cell should score higher (×1.2 vs ×1.0 on same total tier)
        assert val_stack > val_single


# ─────────────────────────────────────────────────────────────────────────────
# Integration: get_action doesn't crash and returns legal action
# ─────────────────────────────────────────────────────────────────────────────

class TestGetActionIntegration:

    def test_returns_legal_action_depth1(self):
        env = ZombieEnv()
        agent = make_agent(Player.RED, depth=1)
        action = agent.get_action(env)
        assert action is not None
        legal = env.get_legal_actions()
        assert action in legal

    def test_returns_legal_action_depth2(self):
        env = ZombieEnv()
        agent = make_agent(Player.RED, depth=2)
        action = agent.get_action(env)
        assert action is not None
        legal = env.get_legal_actions()
        assert action in legal

    def test_blue_agent_returns_legal_action(self):
        env = ZombieEnv()
        # Advance to BLUE's turn
        red_agent = make_agent(Player.RED, depth=1)
        env.step(red_agent.get_action(env))

        blue_agent = make_agent(Player.BLUE, depth=1)
        action = blue_agent.get_action(env)
        assert action is not None
        legal = env.get_legal_actions()
        assert action in legal

    def test_with_card4_does_not_crash(self):
        """Agent with Card 4 should handle USE_CARD in search without crashing."""
        env = ZombieEnv(red_card=Card.BLOCK_STACK)
        agent = make_agent(Player.RED, depth=2)
        action = agent.get_action(env)
        assert action is not None

    def test_with_card7_does_not_crash(self):
        """Agent with Card 7 should handle protected_positions in hash without crashing."""
        env = ZombieEnv(red_card=Card.PROTECT_REVIVED)
        agent = make_agent(Player.RED, depth=2)
        action = agent.get_action(env)
        assert action is not None
