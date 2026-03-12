"""
Unit tests for Card system - Steps 0, 1, 2, 3
Run with: python -m pytest test_cards.py -v
"""

import pytest
from Zombie_env import ZombieEnv, Card, Player, Piece, Action, ActionType


# ─────────────────────────────────────────────
# Step 0: Card Enum
# ─────────────────────────────────────────────

class TestCardEnum:
    def test_all_values_exist(self):
        for i in range(10):
            assert Card(i) is not None

    def test_values(self):
        assert Card.NONE.value            == 0
        assert Card.DIAGONAL_TIER1.value  == 1
        assert Card.REVIVE_ON_STACK.value == 2
        assert Card.WIN_AT_5.value        == 3
        assert Card.BLOCK_STACK.value     == 4
        assert Card.STACK_SAME_TIER.value == 5
        assert Card.ONLY_REVIVE.value     == 6
        assert Card.PROTECT_REVIVED.value == 7
        assert Card.JUMP_REVIVE.value     == 8
        assert Card.DOUBLE_REVIVE.value   == 9

    def test_lookup_by_value(self):
        assert Card(5) == Card.STACK_SAME_TIER


# ─────────────────────────────────────────────
# Step 1: ZombieEnv accepts card parameters
# ─────────────────────────────────────────────

class TestEnvCardInit:
    def test_default_no_cards(self):
        env = ZombieEnv()
        assert env.cards[Player.RED]  == Card.NONE
        assert env.cards[Player.BLUE] == Card.NONE

    def test_red_card_assigned(self):
        env = ZombieEnv(red_card=Card.WIN_AT_5)
        assert env.cards[Player.RED]  == Card.WIN_AT_5
        assert env.cards[Player.BLUE] == Card.NONE

    def test_both_cards_assigned(self):
        env = ZombieEnv(red_card=Card.DIAGONAL_TIER1, blue_card=Card.STACK_SAME_TIER)
        assert env.cards[Player.RED]  == Card.DIAGONAL_TIER1
        assert env.cards[Player.BLUE] == Card.STACK_SAME_TIER

    def test_card_uses_initialized(self):
        env = ZombieEnv(red_card=Card.BLOCK_STACK)
        assert env.card_uses[Player.RED][Card.BLOCK_STACK]  == 3
        assert env.card_uses[Player.RED][Card.ONLY_REVIVE]  == 2
        assert env.card_uses[Player.BLUE][Card.BLOCK_STACK] == 3

    def test_turn_effects_empty(self):
        env = ZombieEnv(red_card=Card.WIN_AT_5, blue_card=Card.DIAGONAL_TIER1)
        assert len(env.turn_effects[Player.RED])  == 0
        assert len(env.turn_effects[Player.BLUE]) == 0

    def test_protected_positions_empty(self):
        env = ZombieEnv()
        assert len(env.protected_positions[Player.RED])  == 0
        assert len(env.protected_positions[Player.BLUE]) == 0

    def test_jumpedout_pieces_empty(self):
        env = ZombieEnv()
        assert env.jumpedout_pieces == []

    def test_reset_preserves_cards(self):
        env = ZombieEnv(red_card=Card.WIN_AT_5, blue_card=Card.DIAGONAL_TIER1)
        env.scores[Player.RED] = 5
        env.reset()
        # Cards preserved after reset
        assert env.cards[Player.RED]  == Card.WIN_AT_5
        assert env.cards[Player.BLUE] == Card.DIAGONAL_TIER1
        # State reset
        assert env.scores[Player.RED] == 0
        assert len(env.turn_effects[Player.RED]) == 0

    def test_backward_compatible(self):
        """ZombieEnv() with no args still works exactly as before."""
        env = ZombieEnv()
        actions = env.get_legal_actions()
        assert len(actions) > 0


# ─────────────────────────────────────────────
# Step 2: Card 3 — win at 5 points
# ─────────────────────────────────────────────

class TestCard3WinAt5:
    def _make_jumpable_env(self, red_card=Card.NONE):
        """Setup: RED at (0,2) tier-2, BLUE at (1,2) tier-1 → RED can jump down to (2,2)"""
        env = ZombieEnv(red_card=red_card)
        env.board = [[[] for _ in range(5)] for _ in range(5)]
        env.board[0][2] = [Piece(Player.RED, 2)]
        env.board[1][2] = [Piece(Player.BLUE, 1)]
        env.current_player = Player.RED
        return env

    def test_win_at_5_triggers(self):
        env = self._make_jumpable_env(red_card=Card.WIN_AT_5)
        env.scores[Player.RED] = 4

        actions = env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.expected_score >= 1]
        assert len(jump_actions) > 0

        _, reward, done, _ = env.step(jump_actions[0])
        assert reward == 1
        assert env.scores[Player.RED] == 5
        assert done  # should win at 5

    def test_normal_win_still_works(self):
        """Without card 3, RED still needs 8 points."""
        env = self._make_jumpable_env(red_card=Card.NONE)
        env.scores[Player.RED] = 7

        actions = env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.expected_score >= 1]
        _, reward, done, _ = env.step(jump_actions[0])
        assert env.scores[Player.RED] == 8
        assert done

    def test_no_early_win_at_4(self):
        """With card 3, reaching 4 does NOT trigger win."""
        env = self._make_jumpable_env(red_card=Card.WIN_AT_5)
        env.scores[Player.RED] = 3

        actions = env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.expected_score >= 1]
        _, _, done, _ = env.step(jump_actions[0])
        assert env.scores[Player.RED] == 4
        assert not done

    def test_card3_only_applies_to_holder(self):
        """BLUE has card 3, RED does not — RED needs 8, BLUE needs 5."""
        env = ZombieEnv(blue_card=Card.WIN_AT_5)
        env.board = [[[] for _ in range(5)] for _ in range(5)]
        # RED jumps and scores
        env.board[0][2] = [Piece(Player.RED, 2)]
        env.board[1][2] = [Piece(Player.BLUE, 1)]
        env.scores[Player.RED] = 7
        env.current_player = Player.RED

        actions = env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.expected_score >= 1]
        _, _, done, _ = env.step(jump_actions[0])
        # RED scored 8, wins (normal threshold)
        assert done

    def test_card3_blue_wins_at_5(self):
        """BLUE has card 3 and scores 5."""
        env = ZombieEnv(blue_card=Card.WIN_AT_5)
        env.board = [[[] for _ in range(5)] for _ in range(5)]
        env.board[4][2] = [Piece(Player.BLUE, 2)]
        env.board[3][2] = [Piece(Player.RED, 1)]
        env.scores[Player.BLUE] = 4
        env.current_player = Player.BLUE

        actions = env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.expected_score >= 1]
        assert len(jump_actions) > 0
        _, _, done, _ = env.step(jump_actions[0])
        assert env.scores[Player.BLUE] == 5
        assert done


# ─────────────────────────────────────────────
# Step 3: Card 1 — tier-1 diagonal move/jump
# ─────────────────────────────────────────────

class TestCard1Diagonal:
    def _empty_env(self, red_card=Card.NONE):
        env = ZombieEnv(red_card=red_card)
        env.board = [[[] for _ in range(5)] for _ in range(5)]
        env.current_player = Player.RED
        return env

    # ── MOVE tests ──

    def test_tier1_has_diagonal_moves(self):
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[2][2] = [Piece(Player.RED, 1)]

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions if a.action_type == ActionType.MOVE}
        assert (1, 1) in move_targets
        assert (1, 3) in move_targets
        assert (3, 1) in move_targets
        assert (3, 3) in move_targets

    def test_tier2_no_diagonal_moves(self):
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[2][2] = [Piece(Player.RED, 2)]   # tier 2 — card doesn't apply

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions if a.action_type == ActionType.MOVE}
        assert (1, 1) not in move_targets
        assert (3, 3) not in move_targets

    def test_no_card_no_diagonal(self):
        env = self._empty_env(red_card=Card.NONE)
        env.board[2][2] = [Piece(Player.RED, 1)]

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions if a.action_type == ActionType.MOVE}
        assert (1, 1) not in move_targets
        assert (3, 3) not in move_targets

    def test_diagonal_move_to_edge(self):
        """tier-1 at (0,0) can move diagonally to (1,1) only (others out of bounds)."""
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[0][0] = [Piece(Player.RED, 1)]

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions if a.action_type == ActionType.MOVE}
        assert (1, 1) in move_targets
        # (-1,-1), (-1,1), (1,-1) are out of bounds
        assert (-1, -1) not in move_targets

    def test_diagonal_move_stacking_own(self):
        """tier-1 can diagonally stack on a higher-tier own piece."""
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.board[1][1] = [Piece(Player.RED, 2)]   # own higher tier at diagonal

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions if a.action_type == ActionType.MOVE
                        and a.from_pos == (2, 2)}
        assert (1, 1) in move_targets   # can stack diagonally

    # ── JUMP tests ──

    def test_tier1_can_jump_diagonally(self):
        """RED tier-1 at (2,2), BLUE tier-1 at (1,1) → RED can jump to (0,0)."""
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.board[1][1] = [Piece(Player.BLUE, 1)]

        actions = env.get_legal_actions()
        jump_targets = {a.to_pos for a in actions if a.action_type == ActionType.JUMP}
        assert (0, 0) in jump_targets

    def test_tier1_diagonal_jump_scores(self):
        """Diagonal jump over BLUE tier-1 gives reward 1."""
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.board[1][1] = [Piece(Player.BLUE, 1)]

        actions = env.get_legal_actions()
        diag_jump = next(
            a for a in actions
            if a.action_type == ActionType.JUMP and a.to_pos == (0, 0)
        )
        _, reward, _, _ = env.step(diag_jump)
        assert reward == 1
        assert env.board[0][0] == [Piece(Player.RED, 1)]
        assert env.board[1][1] == []   # BLUE piece removed

    def test_tier2_no_diagonal_jump(self):
        """Without card, or with tier > 1, no diagonal jump generated."""
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[2][2] = [Piece(Player.RED, 2)]   # tier-2
        env.board[1][1] = [Piece(Player.BLUE, 1)]

        actions = env.get_legal_actions()
        diag_dir_names = {'up-left', 'up-right', 'down-left', 'down-right'}
        diag_jumps = [a for a in actions
                      if a.action_type == ActionType.JUMP
                      and a.initial_direction in diag_dir_names]
        assert len(diag_jumps) == 0

    def test_no_card_no_diagonal_jump(self):
        env = self._empty_env(red_card=Card.NONE)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.board[1][1] = [Piece(Player.BLUE, 1)]

        actions = env.get_legal_actions()
        diag_dir_names = {'up-left', 'up-right', 'down-left', 'down-right'}
        diag_jumps = [a for a in actions
                      if a.action_type == ActionType.JUMP
                      and a.initial_direction in diag_dir_names]
        assert len(diag_jumps) == 0

    def test_diagonal_jump_direction_name(self):
        """initial_direction field is set correctly for diagonal jumps."""
        env = self._empty_env(red_card=Card.DIAGONAL_TIER1)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.board[1][3] = [Piece(Player.BLUE, 1)]  # up-right

        actions = env.get_legal_actions()
        up_right_jumps = [a for a in actions
                          if a.action_type == ActionType.JUMP
                          and a.initial_direction == 'up-right']
        assert len(up_right_jumps) > 0


# ─────────────────────────────────────────────
# Card 2: REVIVE_ON_STACK
# ─────────────────────────────────────────────

class TestCard2ReviveOnStack:
    def _empty_env(self, red_card=Card.NONE, blue_card=Card.NONE):
        env = ZombieEnv(red_card=red_card, blue_card=blue_card)
        for r in range(5):
            for c in range(5):
                for p in env.board[r][c]:
                    env.underworld[p.player][p.tier] += 1
                env.board[r][c] = []
        return env

    def test_card2_revive_tier1_onto_own_tier2(self):
        """With Card 2, tier-1 revive targets include own tier-2 cells."""
        env = self._empty_env(red_card=Card.REVIVE_ON_STACK)
        env.board[2][2] = [Piece(Player.RED, 2)]
        env.underworld[Player.RED][1] = 1

        actions = env.get_legal_actions()
        revive_targets = {a.to_pos for a in actions if a.action_type == ActionType.REVIVE and a.tier == 1}
        assert (2, 2) in revive_targets

    def test_card2_revive_tier1_onto_own_tier3(self):
        """With Card 2, tier-1 revive targets include own tier-3 cells."""
        env = self._empty_env(red_card=Card.REVIVE_ON_STACK)
        env.board[1][3] = [Piece(Player.RED, 3)]
        env.underworld[Player.RED][1] = 1

        actions = env.get_legal_actions()
        revive_targets = {a.to_pos for a in actions if a.action_type == ActionType.REVIVE and a.tier == 1}
        assert (1, 3) in revive_targets

    def test_card2_no_revive_onto_opponent_piece(self):
        """Card 2 must NOT allow reviving onto opponent's cell."""
        env = self._empty_env(red_card=Card.REVIVE_ON_STACK)
        env.board[2][2] = [Piece(Player.BLUE, 2)]
        env.underworld[Player.RED][1] = 1

        actions = env.get_legal_actions()
        revive_targets = {a.to_pos for a in actions if a.action_type == ActionType.REVIVE and a.tier == 1}
        assert (2, 2) not in revive_targets

    def test_card2_no_revive_tier1_onto_own_tier1(self):
        """Card 2 only allows tier-2 or tier-3 targets, not tier-1."""
        env = self._empty_env(red_card=Card.REVIVE_ON_STACK)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.underworld[Player.RED][1] = 1

        actions = env.get_legal_actions()
        revive_targets = {a.to_pos for a in actions if a.action_type == ActionType.REVIVE and a.tier == 1}
        assert (2, 2) not in revive_targets

    def test_card2_no_revive_tier2_on_stack(self):
        """Card 2 only enables tier-1 stacking, not tier-2 or tier-3."""
        env = self._empty_env(red_card=Card.REVIVE_ON_STACK)
        env.board[2][2] = [Piece(Player.RED, 2)]
        env.underworld[Player.RED][2] = 1

        actions = env.get_legal_actions()
        revive_targets = {a.to_pos for a in actions if a.action_type == ActionType.REVIVE and a.tier == 2}
        assert (2, 2) not in revive_targets

    def test_card2_no_card_no_stack_revive(self):
        """Without Card 2, revive targets are only empty cells."""
        env = self._empty_env(red_card=Card.NONE)
        env.board[2][2] = [Piece(Player.RED, 2)]
        env.underworld[Player.RED][1] = 1

        actions = env.get_legal_actions()
        revive_targets = {a.to_pos for a in actions if a.action_type == ActionType.REVIVE and a.tier == 1}
        assert (2, 2) not in revive_targets

    def test_card2_step_stacks_piece(self):
        """Executing card-2 revive actually stacks the piece on the board."""
        env = self._empty_env(red_card=Card.REVIVE_ON_STACK)
        env.board[2][2] = [Piece(Player.RED, 2)]
        env.underworld[Player.RED][1] = 1

        actions = env.get_legal_actions()
        revive_action = next(
            a for a in actions
            if a.action_type == ActionType.REVIVE and a.tier == 1 and a.to_pos == (2, 2)
        )
        env.step(revive_action)
        cell = env.board[2][2]
        assert len(cell) == 2
        tiers = sorted(p.tier for p in cell)
        assert tiers == [1, 2]
        assert env.underworld[Player.RED][1] == 0


# ─────────────────────────────────────────────
# Card 5: STACK_SAME_TIER
# ─────────────────────────────────────────────

class TestCard5StackSameTier:
    def _empty_env(self, red_card=Card.NONE, blue_card=Card.NONE):
        env = ZombieEnv(red_card=red_card, blue_card=blue_card)
        for r in range(5):
            for c in range(5):
                for p in env.board[r][c]:
                    env.underworld[p.player][p.tier] += 1
                env.board[r][c] = []
        return env

    def test_card5_can_stack_same_tier(self):
        """With Card 5, RED tier-2 can move onto own tier-2."""
        env = self._empty_env(red_card=Card.STACK_SAME_TIER)
        env.board[2][2] = [Piece(Player.RED, 2)]
        env.board[2][3] = [Piece(Player.RED, 2)]

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions
                        if a.action_type == ActionType.MOVE and a.from_pos == (2, 2)}
        assert (2, 3) in move_targets

    def test_no_card_cannot_stack_same_tier(self):
        """Without Card 5, same-tier stacking is NOT allowed."""
        env = self._empty_env(red_card=Card.NONE)
        env.board[2][2] = [Piece(Player.RED, 2)]
        env.board[2][3] = [Piece(Player.RED, 2)]

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions
                        if a.action_type == ActionType.MOVE and a.from_pos == (2, 2)}
        assert (2, 3) not in move_targets

    def test_card5_merged_exceeds_6_blocked(self):
        """Card 5 rejects stacking if merged tier > 6 (e.g. tier-4 onto tier-4)."""
        env = self._empty_env(red_card=Card.STACK_SAME_TIER)
        env.board[2][2] = [Piece(Player.RED, 4)]  # moving
        env.board[2][3] = [Piece(Player.RED, 4)]  # target, 4+4=8 > 6

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions
                        if a.action_type == ActionType.MOVE and a.from_pos == (2, 2)}
        assert (2, 3) not in move_targets

    def test_card5_merged_equals_6_allowed_when_no_other_6(self):
        """Card 5 allows merging to 6 when no other 6-tier exists."""
        env = self._empty_env(red_card=Card.STACK_SAME_TIER)
        env.board[2][2] = [Piece(Player.RED, 3)]
        env.board[2][3] = [Piece(Player.RED, 3)]  # 3+3=6

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions
                        if a.action_type == ActionType.MOVE and a.from_pos == (2, 2)}
        assert (2, 3) in move_targets

    def test_card5_merged_equals_6_blocked_when_another_6_exists(self):
        """Card 5 blocks merging to 6 if there's already a 6-tier piece on board."""
        env = self._empty_env(red_card=Card.STACK_SAME_TIER)
        env.board[2][2] = [Piece(Player.RED, 3)]
        env.board[2][3] = [Piece(Player.RED, 3)]
        env.board[0][0] = [Piece(Player.RED, 3), Piece(Player.RED, 3)]  # existing 6-tier

        actions = env.get_legal_actions()
        move_targets = {a.to_pos for a in actions
                        if a.action_type == ActionType.MOVE and a.from_pos == (2, 2)}
        assert (2, 3) not in move_targets

    def test_card5_step_merges_pieces(self):
        """Executing a Card-5 same-tier move actually merges the pieces."""
        env = self._empty_env(red_card=Card.STACK_SAME_TIER)
        env.board[2][2] = [Piece(Player.RED, 2)]
        env.board[2][3] = [Piece(Player.RED, 2)]

        actions = env.get_legal_actions()
        move = next(a for a in actions
                    if a.action_type == ActionType.MOVE
                    and a.from_pos == (2, 2) and a.to_pos == (2, 3))
        env.step(move)
        assert env.board[2][2] == []
        assert len(env.board[2][3]) == 2
        assert sum(p.tier for p in env.board[2][3]) == 4


# ─────────────────────────────────────────────
# Card 7: PROTECT_REVIVED
# ─────────────────────────────────────────────

class TestCard7ProtectRevived:
    def _empty_env(self, red_card=Card.NONE, blue_card=Card.NONE):
        env = ZombieEnv(red_card=red_card, blue_card=blue_card)
        for r in range(5):
            for c in range(5):
                for p in env.board[r][c]:
                    env.underworld[p.player][p.tier] += 1
                env.board[r][c] = []
        return env

    def _do_revive(self, env, tier, pos):
        """Helper: execute a REVIVE action."""
        action = Action(
            action_type=ActionType.REVIVE,
            from_pos=None, to_pos=pos, tier=tier,
            initial_direction=None, jump_sequence=None, expected_score=0.0
        )
        env.step(action)

    def test_card7_revive_sets_protection(self):
        """After RED revives tier-1 with Card 7, position is in protected_positions."""
        env = self._empty_env(red_card=Card.PROTECT_REVIVED)
        env.underworld[Player.RED][1] = 1
        self._do_revive(env, 1, (2, 2))
        assert (2, 2) in env.protected_positions[Player.RED]

    def test_card7_revive_tier2_sets_protection(self):
        """Card 7 also protects freshly-revived tier-2."""
        env = self._empty_env(red_card=Card.PROTECT_REVIVED)
        env.underworld[Player.RED][2] = 1
        self._do_revive(env, 2, (3, 3))
        assert (3, 3) in env.protected_positions[Player.RED]

    def test_card7_revive_tier3_no_protection(self):
        """Card 7 does NOT protect tier-3 revived pieces."""
        env = self._empty_env(red_card=Card.PROTECT_REVIVED)
        env.underworld[Player.RED][3] = 1
        self._do_revive(env, 3, (2, 2))
        assert (2, 2) not in env.protected_positions[Player.RED]

    def test_card7_no_card_no_protection(self):
        """Without Card 7, reviving sets no protection."""
        env = self._empty_env(red_card=Card.NONE)
        env.underworld[Player.RED][1] = 1
        self._do_revive(env, 1, (2, 2))
        assert (2, 2) not in env.protected_positions[Player.RED]

    def test_card7_protected_piece_survives_jump(self):
        """Opponent jumping over a Card-7 protected piece scores 0 and piece stays."""
        env = self._empty_env(red_card=Card.PROTECT_REVIVED)
        # RED revives tier-1 at (2,2) with protection
        env.underworld[Player.RED][1] = 1
        self._do_revive(env, 1, (2, 2))   # RED turn -> switches to BLUE

        # BLUE tier-2 at (2,3), RED protected tier-1 at (2,2), landing at (2,1) empty
        env.board[2][3] = [Piece(Player.BLUE, 2)]

        actions = env.get_legal_actions()
        # BLUE jumps LEFT from (2,3) over RED@(2,2) → landing at (2,1)
        jump = next(
            (a for a in actions
             if a.action_type == ActionType.JUMP
             and a.from_pos == (2, 3)
             and a.to_pos == (2, 1)),
            None
        )
        assert jump is not None, "Expected jump (2,3)->(2,1) to be generated"

        _, reward, _, _ = env.step(jump)
        assert reward == 0                                  # no score gained
        assert env.board[2][2] == [Piece(Player.RED, 1)]   # piece still alive

    def test_card7_protection_expires_after_one_opponent_turn(self):
        """After opponent takes their turn, protection is cleared."""
        env = self._empty_env(red_card=Card.PROTECT_REVIVED)
        env.underworld[Player.RED][1] = 1
        self._do_revive(env, 1, (2, 2))   # RED revives -> switches to BLUE
        assert (2, 2) in env.protected_positions[Player.RED]

        # BLUE takes any action (revive)
        env.underworld[Player.BLUE][1] = 1
        self._do_revive(env, 1, (4, 4))   # BLUE revives -> switches to RED
        # Protection should now be cleared
        assert (2, 2) not in env.protected_positions[Player.RED]

    def test_card7_unprotected_piece_is_scored(self):
        """Without Card 7, opponent jump over tier-1 scores normally."""
        env = self._empty_env(red_card=Card.NONE)
        env.underworld[Player.RED][1] = 1
        self._do_revive(env, 1, (2, 2))   # RED -> BLUE

        # BLUE tier-2 at (2,3), RED tier-1 at (2,2), empty at (2,1)
        env.board[2][3] = [Piece(Player.BLUE, 2)]

        actions = env.get_legal_actions()
        jump = next(
            (a for a in actions
             if a.action_type == ActionType.JUMP
             and a.from_pos == (2, 3)
             and a.to_pos == (2, 1)),
            None
        )
        assert jump is not None, "Expected jump (2,3)->(2,1) to be generated"

        _, reward, _, _ = env.step(jump)
        assert reward == 1
        assert env.board[2][2] == []


# ─────────────────────────────────────────────
# Card 4: BLOCK_STACK  |  Card 6: ONLY_REVIVE
# ─────────────────────────────────────────────

class TestCard4And6ActiveCards:
    def _empty_env(self, red_card=Card.NONE, blue_card=Card.NONE):
        env = ZombieEnv(red_card=red_card, blue_card=blue_card)
        for r in range(5):
            for c in range(5):
                for p in env.board[r][c]:
                    env.underworld[p.player][p.tier] += 1
                env.board[r][c] = []
        return env

    # ── Card 4 ──

    def test_card4_use_card_action_available(self):
        """RED with Card 4 and uses remaining should see a USE_CARD action."""
        env = self._empty_env(red_card=Card.BLOCK_STACK)
        env.board[2][2] = [Piece(Player.RED, 1)]

        actions = env.get_legal_actions()
        use_actions = [a for a in actions if a.action_type == ActionType.USE_CARD and a.tier == 4]
        assert len(use_actions) == 1

    def test_card4_no_uses_left_no_action(self):
        """If card_uses exhausted, USE_CARD should not appear."""
        env = self._empty_env(red_card=Card.BLOCK_STACK)
        env.card_uses[Player.RED][Card.BLOCK_STACK] = 0
        env.board[2][2] = [Piece(Player.RED, 1)]

        actions = env.get_legal_actions()
        use_actions = [a for a in actions if a.action_type == ActionType.USE_CARD]
        assert len(use_actions) == 0

    def test_card4_use_does_not_switch_player(self):
        """Using Card 4 keeps current_player as RED."""
        env = self._empty_env(red_card=Card.BLOCK_STACK)
        env.board[2][2] = [Piece(Player.RED, 1)]

        use_action = Action(
            action_type=ActionType.USE_CARD,
            from_pos=None, to_pos=None, tier=4,
            initial_direction=None, jump_sequence=None, expected_score=0.0
        )
        env.step(use_action)
        assert env.current_player == Player.RED

    def test_card4_decrements_uses(self):
        """Using Card 4 decrements card_uses by 1."""
        env = self._empty_env(red_card=Card.BLOCK_STACK)
        env.board[2][2] = [Piece(Player.RED, 1)]
        before = env.card_uses[Player.RED][Card.BLOCK_STACK]

        use_action = Action(
            action_type=ActionType.USE_CARD,
            from_pos=None, to_pos=None, tier=4,
            initial_direction=None, jump_sequence=None, expected_score=0.0
        )
        env.step(use_action)
        assert env.card_uses[Player.RED][Card.BLOCK_STACK] == before - 1

    def test_card4_blocks_stacking_move_for_opponent(self):
        """After RED uses Card 4, BLUE cannot make stacking MOVE actions."""
        env = self._empty_env(red_card=Card.BLOCK_STACK)
        # RED uses card, then takes a regular action to switch to BLUE
        env.board[2][2] = [Piece(Player.RED, 1)]
        use_action = Action(ActionType.USE_CARD, None, None, 4, None, None, 0.0)
        env.step(use_action)

        # RED takes regular move (switch to BLUE)
        env.board[0][0] = [Piece(Player.RED, 1)]
        move = Action(ActionType.MOVE, (0, 0), (0, 1), None, None, None, 0.0)
        env.step(move)

        # Now BLUE: place a tier-1 at (3,3), own tier-2 at (3,4) → stacking move blocked
        env.board[3][3] = [Piece(Player.BLUE, 1)]
        env.board[3][4] = [Piece(Player.BLUE, 2)]

        actions = env.get_legal_actions()
        stacking_moves = [
            a for a in actions
            if a.action_type == ActionType.MOVE
            and a.from_pos == (3, 3) and a.to_pos == (3, 4)
        ]
        assert len(stacking_moves) == 0

    def test_card4_effect_expires_after_opponent_turn(self):
        """After BLUE takes their turn, no_stack effect is cleared."""
        env = self._empty_env(red_card=Card.BLOCK_STACK)
        env.board[2][2] = [Piece(Player.RED, 1)]
        use_action = Action(ActionType.USE_CARD, None, None, 4, None, None, 0.0)
        env.step(use_action)

        move = Action(ActionType.MOVE, (2, 2), (2, 3), None, None, None, 0.0)
        env.step(move)   # RED acts → switch to BLUE
        assert 'no_stack' in env.turn_effects[Player.BLUE]

        # BLUE takes any action
        env.board[4][4] = [Piece(Player.BLUE, 1)]
        env.underworld[Player.BLUE][1] = 1
        revive = Action(ActionType.REVIVE, None, (0, 0), 1, None, None, 0.0)
        env.step(revive)  # BLUE acts → switch to RED, clears BLUE's turn_effects

        assert 'no_stack' not in env.turn_effects[Player.BLUE]

    # ── Card 6 ──

    def test_card6_use_card_action_available(self):
        """RED with Card 6 and uses remaining sees USE_CARD action."""
        env = self._empty_env(red_card=Card.ONLY_REVIVE)
        env.board[2][2] = [Piece(Player.RED, 1)]

        actions = env.get_legal_actions()
        use_actions = [a for a in actions if a.action_type == ActionType.USE_CARD and a.tier == 6]
        assert len(use_actions) == 1

    def test_card6_opponent_only_revive(self):
        """After RED uses Card 6, BLUE can only REVIVE (no MOVE or JUMP)."""
        env = self._empty_env(red_card=Card.ONLY_REVIVE)
        env.board[2][2] = [Piece(Player.RED, 1)]
        use_action = Action(ActionType.USE_CARD, None, None, 6, None, None, 0.0)
        env.step(use_action)

        # RED takes regular move → switch to BLUE
        move = Action(ActionType.MOVE, (2, 2), (2, 3), None, None, None, 0.0)
        env.step(move)

        # BLUE: give pieces for MOVE/JUMP and underworld piece for REVIVE
        env.board[3][3] = [Piece(Player.BLUE, 1)]
        env.underworld[Player.BLUE][1] = 1

        actions = env.get_legal_actions()
        non_revive = [a for a in actions if a.action_type != ActionType.REVIVE]
        assert len(non_revive) == 0, f"Expected only REVIVE actions, got: {non_revive}"

    def test_card6_effect_expires_after_opponent_turn(self):
        """After BLUE takes their turn, only_revive effect is cleared."""
        env = self._empty_env(red_card=Card.ONLY_REVIVE)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.step(Action(ActionType.USE_CARD, None, None, 6, None, None, 0.0))
        env.step(Action(ActionType.MOVE, (2, 2), (2, 3), None, None, None, 0.0))

        assert 'only_revive' in env.turn_effects[Player.BLUE]

        env.underworld[Player.BLUE][1] = 1
        env.step(Action(ActionType.REVIVE, None, (0, 0), 1, None, None, 0.0))

        assert 'only_revive' not in env.turn_effects[Player.BLUE]

    def test_card6_use_not_available_after_used_this_turn(self):
        """Once Card 6 used this turn, USE_CARD no longer appears until after next turn."""
        env = self._empty_env(red_card=Card.ONLY_REVIVE)
        env.board[2][2] = [Piece(Player.RED, 1)]
        env.step(Action(ActionType.USE_CARD, None, None, 6, None, None, 0.0))

        # Still RED's turn — USE_CARD should no longer appear (effect already applied)
        actions = env.get_legal_actions()
        use_actions = [a for a in actions if a.action_type == ActionType.USE_CARD]
        assert len(use_actions) == 0


# ─────────────────────────────────────────────
# Card 8: JUMP_REVIVE
# ─────────────────────────────────────────────

class TestCard8JumpRevive:
    """Card 8: after jumping off board, player may immediately revive one of the pieces that just left."""

    def _env(self):
        """RED tier-3 at (0,2); BLUE tier-1 at (1,2). RED can jump up over BLUE and off board."""
        env = ZombieEnv(red_card=Card.JUMP_REVIVE)
        for r in range(env.board_size):
            for c in range(env.board_size):
                env.board[r][c] = []
        env.board[0][2] = [Piece(Player.RED, 3)]
        env.board[1][2] = [Piece(Player.BLUE, 1)]
        env.underworld = {Player.RED: {1: 0, 2: 0, 3: 0}, Player.BLUE: {1: 0, 2: 0, 3: 0}}
        env.scores = {Player.RED: 0, Player.BLUE: 0}
        env.current_player = Player.RED
        return env

    def _jump_off(self, env):
        jump = Action(
            action_type=ActionType.JUMP,
            from_pos=(0, 2), to_pos=(-1, -1), tier=None,
            initial_direction='up',
            jump_sequence=[((-1, -1), [(1, 2)])],
            expected_score=1.0
        )
        return env.step(jump)

    def test_card8_player_does_not_switch_after_jump_off(self):
        env = self._env()
        self._jump_off(env)
        assert env.current_player == Player.RED

    def test_card8_jumpedout_pieces_populated(self):
        env = self._env()
        self._jump_off(env)
        assert len(env.jumpedout_pieces) == 1
        assert env.jumpedout_pieces[0].tier == 3

    def test_card8_legal_actions_are_only_revive_of_jumped_tier(self):
        env = self._env()
        self._jump_off(env)
        actions = env.get_legal_actions()
        assert len(actions) > 0
        assert all(a.action_type == ActionType.REVIVE for a in actions)
        assert all(a.tier == 3 for a in actions)  # only the piece that jumped off

    def test_card8_revive_switches_player(self):
        env = self._env()
        self._jump_off(env)
        revive = env.get_legal_actions()[0]
        env.step(revive)
        assert env.current_player == Player.BLUE
        assert env.jumpedout_pieces == []

    def test_card8_piece_lands_on_board_after_revive(self):
        env = self._env()
        self._jump_off(env)
        revive = Action(ActionType.REVIVE, None, (2, 2), 3, None, None, 0.0)
        env.step(revive)
        assert len(env.board[2][2]) == 1
        assert env.board[2][2][0].tier == 3
        assert env.underworld[Player.RED][3] == 0

    def test_card8_no_pending_without_card(self):
        """Without Card 8, jumping off board switches player immediately."""
        env = ZombieEnv()
        for r in range(env.board_size):
            for c in range(env.board_size):
                env.board[r][c] = []
        env.board[0][2] = [Piece(Player.RED, 3)]
        env.board[1][2] = [Piece(Player.BLUE, 1)]
        env.underworld = {Player.RED: {1: 0, 2: 0, 3: 0}, Player.BLUE: {1: 0, 2: 0, 3: 0}}
        env.current_player = Player.RED
        jump = Action(ActionType.JUMP, (0, 2), (-1, -1), None, 'up',
                      [((-1, -1), [(1, 2)])], 1.0)
        env.step(jump)
        assert env.current_player == Player.BLUE
        assert env.jumpedout_pieces == []

    def test_card8_multiple_tiers_jumped_off_offers_each_tier_once(self):
        """If two pieces of different tiers jump off, both tiers appear in revive options."""
        env = ZombieEnv(red_card=Card.JUMP_REVIVE)
        for r in range(env.board_size):
            for c in range(env.board_size):
                env.board[r][c] = []
        # Stacked RED: tier 1 + tier 1 = tier-value 2 total
        env.board[0][2] = [Piece(Player.RED, 1), Piece(Player.RED, 2)]
        env.board[1][2] = [Piece(Player.BLUE, 1)]
        env.underworld = {Player.RED: {1: 0, 2: 0, 3: 0}, Player.BLUE: {1: 0, 2: 0, 3: 0}}
        env.current_player = Player.RED
        # jumping_tier = 3 (1+2), jumps BLUE tier-1 at (1,2) → off board
        jump = Action(ActionType.JUMP, (0, 2), (-1, -1), None, 'up',
                      [((-1, -1), [(1, 2)])], 1.0)
        env.step(jump)
        actions = env.get_legal_actions()
        offered_tiers = {a.tier for a in actions}
        assert 1 in offered_tiers
        assert 2 in offered_tiers


# ─────────────────────────────────────────────
# Card 9: DOUBLE_REVIVE
# ─────────────────────────────────────────────

class TestCard9DoubleRevive:
    """Card 9: when reviving, player may revive one additional piece to a different empty cell."""

    def _env(self, count=2):
        env = ZombieEnv(red_card=Card.DOUBLE_REVIVE)
        for r in range(env.board_size):
            for c in range(env.board_size):
                env.board[r][c] = []
        env.underworld = {Player.RED: {1: count, 2: 0, 3: 0}, Player.BLUE: {1: 0, 2: 0, 3: 0}}
        env.scores = {Player.RED: 0, Player.BLUE: 0}
        env.current_player = Player.RED
        return env

    def test_card9_first_revive_does_not_switch_player(self):
        env = self._env()
        revive = Action(ActionType.REVIVE, None, (2, 2), 1, None, None, 0.0)
        env.step(revive)
        assert env.current_player == Player.RED
        assert env.pending_double_revive is True

    def test_card9_legal_actions_after_first_revive_only_revive(self):
        env = self._env()
        env.step(Action(ActionType.REVIVE, None, (2, 2), 1, None, None, 0.0))
        actions = env.get_legal_actions()
        assert len(actions) > 0
        assert all(a.action_type == ActionType.REVIVE for a in actions)

    def test_card9_second_revive_switches_player(self):
        env = self._env()
        env.step(Action(ActionType.REVIVE, None, (2, 2), 1, None, None, 0.0))
        env.step(Action(ActionType.REVIVE, None, (3, 3), 1, None, None, 0.0))
        assert env.current_player == Player.BLUE
        assert env.pending_double_revive is False

    def test_card9_two_pieces_placed_on_board(self):
        env = self._env()
        env.step(Action(ActionType.REVIVE, None, (2, 2), 1, None, None, 0.0))
        env.step(Action(ActionType.REVIVE, None, (3, 3), 1, None, None, 0.0))
        assert len(env.board[2][2]) == 1
        assert len(env.board[3][3]) == 1
        assert env.underworld[Player.RED][1] == 0

    def test_card9_no_second_revive_if_underworld_empty(self):
        """If only one piece in underworld, no pending after reviving it → switches immediately."""
        env = self._env(count=1)
        env.step(Action(ActionType.REVIVE, None, (2, 2), 1, None, None, 0.0))
        assert env.current_player == Player.BLUE
        assert env.pending_double_revive is False

    def test_no_card9_no_double_revive(self):
        """Without Card 9, first REVIVE switches player immediately."""
        env = ZombieEnv()
        for r in range(env.board_size):
            for c in range(env.board_size):
                env.board[r][c] = []
        env.underworld = {Player.RED: {1: 2, 2: 0, 3: 0}, Player.BLUE: {1: 0, 2: 0, 3: 0}}
        env.current_player = Player.RED
        env.step(Action(ActionType.REVIVE, None, (2, 2), 1, None, None, 0.0))
        assert env.current_player == Player.BLUE
        assert env.pending_double_revive is False

    def test_card9_second_revive_must_be_different_cell(self):
        """The second revive target must be an empty cell (first target now occupied)."""
        env = self._env()
        env.step(Action(ActionType.REVIVE, None, (2, 2), 1, None, None, 0.0))
        actions = env.get_legal_actions()
        targets = {a.to_pos for a in actions}
        assert (2, 2) not in targets  # (2,2) is now occupied


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




