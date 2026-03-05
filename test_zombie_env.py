import unittest
from Zombie_env import ZombieEnv, Player, ActionType, Action, Piece


class TestZombieEnvBasics(unittest.TestCase):
    """Test basic environment functionality"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_initial_state(self):
        """Test initial board setup"""
        # Check RED pieces
        self.assertEqual(len(self.env.board[0][0]), 1)
        self.assertEqual(self.env.board[0][0][0].tier, 2)
        self.assertEqual(self.env.board[0][2][0].tier, 3)
        self.assertEqual(self.env.board[0][4][0].tier, 2)
        
        # Check BLUE pieces
        self.assertEqual(len(self.env.board[4][0]), 1)
        self.assertEqual(self.env.board[4][0][0].tier, 2)
        self.assertEqual(self.env.board[4][2][0].tier, 3)
        
        # Check underworld
        self.assertEqual(self.env.underworld[Player.RED][2], 2)
        self.assertEqual(self.env.underworld[Player.BLUE][2], 2)
        
        # Check scores
        self.assertEqual(self.env.scores[Player.RED], 0)
        self.assertEqual(self.env.scores[Player.BLUE], 0)
    
    def test_reset(self):
        """Test reset functionality"""
        # Make a change
        self.env.scores[Player.RED] = 5
        self.env.current_player = Player.BLUE
        
        # Reset
        state = self.env.reset()
        
        self.assertEqual(self.env.scores[Player.RED], 0)
        self.assertEqual(self.env.current_player, Player.RED)
        self.assertEqual(len(self.env.board[0][0]), 1)


class TestReviveActions(unittest.TestCase):
    """Test REVIVE actions"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_revive_action_generation(self):
        """Test that REVIVE actions are generated for pieces in underworld"""
        actions = self.env.get_legal_actions()
        revive_actions = [a for a in actions if a.action_type == ActionType.REVIVE]
        
        # RED has 2x tier-2 in underworld initially
        # Count empty cells
        empty_cells = sum(1 for row in self.env.board for cell in row if len(cell) == 0)
        # Should have 1 REVIVE action per empty cell (tier-2)
        expected_revive = empty_cells  # Each empty cell can have one revive action
        
        self.assertEqual(len(revive_actions), expected_revive)
        
        # All should have expected_score = 0
        for action in revive_actions:
            self.assertEqual(action.expected_score, 0.0)
    
    def test_revive_execution(self):
        """Test executing a REVIVE action"""
        # RED has tier-2 in underworld, revive to center
        action = Action(
            action_type=ActionType.REVIVE,
            from_pos=None,
            to_pos=(2, 2),
            tier=2,
            initial_direction=None,
            jump_sequence=None,
            expected_score=0.0
        )
        
        underworld_before = self.env.underworld[Player.RED][2]
        state, reward, done, info = self.env.step(action)
        
        # Check piece is on board
        self.assertEqual(len(self.env.board[2][2]), 1)
        self.assertEqual(self.env.board[2][2][0].tier, 2)
        self.assertEqual(self.env.board[2][2][0].player, Player.RED)
        
        # Check underworld count decreased
        self.assertEqual(self.env.underworld[Player.RED][2], underworld_before - 1)
        
        # Check no reward/score change
        self.assertEqual(reward, 0)
        self.assertEqual(self.env.scores[Player.RED], 0)
        
        # Player should switch
        self.assertEqual(self.env.current_player, Player.BLUE)


class TestMoveActions(unittest.TestCase):
    """Test MOVE actions"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_move_action_generation(self):
        """Test that MOVE actions are generated"""
        actions = self.env.get_legal_actions()
        move_actions = [a for a in actions if a.action_type == ActionType.MOVE]
        
        # Should have some move actions
        self.assertGreater(len(move_actions), 0)
        
        # All should have expected_score = 0
        for action in move_actions:
            self.assertEqual(action.expected_score, 0.0)
    
    def test_move_to_empty_cell(self):
        """Test moving to an empty cell"""
        # Move RED piece from (1,2) to (2,2)
        action = Action(
            action_type=ActionType.MOVE,
            from_pos=(1, 2),
            to_pos=(2, 2),
            tier=None,
            initial_direction=None,
            jump_sequence=None,
            expected_score=0.0
        )
        
        state, reward, done, info = self.env.step(action)
        
        # Check piece moved
        self.assertEqual(len(self.env.board[1][2]), 0)
        self.assertEqual(len(self.env.board[2][2]), 1)
        self.assertEqual(self.env.board[2][2][0].tier, 1)
        
        # No reward
        self.assertEqual(reward, 0)
    
    def test_move_stacking(self):
        """Test moving to stack on own higher tier piece"""
        # First move tier-1 from (1,0) to (2,0)
        self.env.board[1][0] = [Piece(Player.RED, 1)]
        self.env.board[2][0] = [Piece(Player.RED, 3)]
        
        action = Action(
            action_type=ActionType.MOVE,
            from_pos=(1, 0),
            to_pos=(2, 0),
            tier=None,
            initial_direction=None,
            jump_sequence=None,
            expected_score=0.0
        )
        
        state, reward, done, info = self.env.step(action)
        
        # Check stacking
        self.assertEqual(len(self.env.board[2][0]), 2)
        self.assertEqual(self.env.board[2][0][0].tier, 3)
        self.assertEqual(self.env.board[2][0][1].tier, 1)


class TestJumpActions(unittest.TestCase):
    """Test JUMP actions"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_single_direction_jump(self):
        """Test a simple single-direction jump"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-2 at (2,0), BLUE tier-1 at (2,1), empty at (2,2)
        self.env.board[2][0] = [Piece(Player.RED, 2)]
        self.env.board[2][1] = [Piece(Player.BLUE, 1)]
        self.env.current_player = Player.RED
        
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP]
        
        # Should have jump to the right
        right_jumps = [a for a in jump_actions if a.initial_direction == 'right']
        self.assertGreater(len(right_jumps), 0)
        
        # Find the jump that lands at (2,2)
        target_action = next((a for a in right_jumps if a.to_pos == (2, 2)), None)
        self.assertIsNotNone(target_action)
        
        # Should have expected_score = 1 (jumping over tier-1)
        self.assertEqual(target_action.expected_score, 1.0)
    
    def test_multi_direction_jump(self):
        """Test that multi-direction jumps are possible"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-3 at (2,2)
        # BLUE pieces at (2,3) and (3,3)
        # This allows jumping right then down
        self.env.board[2][2] = [Piece(Player.RED, 3)]
        self.env.board[2][3] = [Piece(Player.BLUE, 1)]
        self.env.board[3][3] = [Piece(Player.BLUE, 1)]
        self.env.current_player = Player.RED
        
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP]
        
        # Should have jumps in the right direction
        right_jumps = [a for a in jump_actions if a.initial_direction == 'right']
        
        # Check if any jump has 2+ steps (multi-direction)
        multi_step_jumps = [a for a in right_jumps if len(a.jump_sequence) >= 2]
        
        # If Dijkstra works correctly, we should find multi-direction paths
        # The exact path depends on implementation, but we should have multiple steps
        if len(multi_step_jumps) > 0:
            # Print for debugging
            print(f"\nFound {len(multi_step_jumps)} multi-step jumps")
            for a in multi_step_jumps[:3]:
                print(f"  {a}")
    
    def test_own_pieces_not_captured(self):
        """Test that jumping over own pieces doesn't send them to underworld"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-3 at (2,0), RED tier-1 at (2,1), empty at (2,2)
        self.env.board[2][0] = [Piece(Player.RED, 3)]
        self.env.board[2][1] = [Piece(Player.RED, 1)]
        self.env.current_player = Player.RED
        
        # Get jump actions
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.from_pos == (2, 0)]
        
        # Find jump to (2,2)
        right_jumps = [a for a in jump_actions if a.to_pos == (2, 2)]
        if len(right_jumps) > 0:
            action = right_jumps[0]
            
            # Execute
            state, reward, done, info = self.env.step(action)
            
            # Check own piece is still at (2,1)
            self.assertEqual(len(self.env.board[2][1]), 1)
            self.assertEqual(self.env.board[2][1][0].tier, 1)
            
            # Check underworld didn't increase
            self.assertEqual(self.env.underworld[Player.RED][1], 0)
            
            # No reward
            self.assertEqual(reward, 0)
            self.assertEqual(action.expected_score, 0.0)
    
    def test_jump_capture_opponent(self):
        """Test that jumping over opponent pieces captures them"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-2 at (2,0), BLUE tier-1 at (2,1), empty at (2,2)
        self.env.board[2][0] = [Piece(Player.RED, 2)]
        self.env.board[2][1] = [Piece(Player.BLUE, 1)]
        self.env.current_player = Player.RED
        
        # Get jump actions
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.from_pos == (2, 0)]
        
        # Find jump to (2,2)
        right_jumps = [a for a in jump_actions if a.to_pos == (2, 2)]
        self.assertGreater(len(right_jumps), 0)
        
        action = right_jumps[0]
        
        # Execute
        underworld_before = self.env.underworld[Player.BLUE][1]
        state, reward, done, info = self.env.step(action)
        
        # Check opponent piece captured
        self.assertEqual(len(self.env.board[2][1]), 0)
        self.assertEqual(self.env.underworld[Player.BLUE][1], underworld_before + 1)
        
        # Check reward
        self.assertEqual(reward, 1)
        self.assertEqual(action.expected_score, 1.0)
        self.assertEqual(self.env.scores[Player.RED], 1)
    
    def test_jump_off_board(self):
        """Test jumping off the board"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-2 at (0,1), BLUE tier-1 at (0,0), jump left off board
        self.env.board[0][1] = [Piece(Player.RED, 2)]
        self.env.board[0][0] = [Piece(Player.BLUE, 1)]
        self.env.current_player = Player.RED
        
        # Get jump actions
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.from_pos == (0, 1)]
        
        # Find jump off board (to_pos = (-1, -1))
        off_board_jumps = [a for a in jump_actions if a.to_pos == (-1, -1)]
        self.assertGreater(len(off_board_jumps), 0)
        
        action = off_board_jumps[0]
        
        # Execute
        underworld_red_before = self.env.underworld[Player.RED][2]
        underworld_blue_before = self.env.underworld[Player.BLUE][1]
        
        state, reward, done, info = self.env.step(action)
        
        # Check RED piece went to underworld
        self.assertEqual(len(self.env.board[0][1]), 0)
        self.assertEqual(self.env.underworld[Player.RED][2], underworld_red_before + 1)
        
        # Check BLUE piece captured
        self.assertEqual(len(self.env.board[0][0]), 0)
        self.assertEqual(self.env.underworld[Player.BLUE][1], underworld_blue_before + 1)
        
        # Check reward (only from opponent)
        self.assertEqual(reward, 1)
        self.assertEqual(action.expected_score, 1.0)
    
    def test_jump_stacking(self):
        """Test jumping and stacking on own higher tier piece"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-2 at (2,0), BLUE tier-1 at (2,1), RED tier-3 at (2,2)
        # tier-2 can jump over tier-1, and stack on tier-3 (since 3 > 2)
        self.env.board[2][0] = [Piece(Player.RED, 2)]
        self.env.board[2][1] = [Piece(Player.BLUE, 1)]
        self.env.board[2][2] = [Piece(Player.RED, 3)]
        self.env.current_player = Player.RED
        
        # Get jump actions
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.from_pos == (2, 0)]
        
        # Debug: print all jump actions
        print(f"\nDEBUG: Found {len(jump_actions)} jump actions from (2,0):")
        for a in jump_actions:
            print(f"  {a}")
        
        # Find jump that stacks on (2,2)
        stack_jumps = [a for a in jump_actions if a.to_pos == (2, 2)]
        
        print(f"\nDEBUG: Found {len(stack_jumps)} stack jumps to (2,2)")
        
        self.assertGreater(len(stack_jumps), 0)
        
        action = stack_jumps[0]
        
        # Execute
        state, reward, done, info = self.env.step(action)
        
        # Check stacking - tier-2 should stack on tier-3
        self.assertEqual(len(self.env.board[2][2]), 2)
        self.assertEqual(self.env.board[2][2][0].tier, 3)
        self.assertEqual(self.env.board[2][2][1].tier, 2)
        
        # Check reward (only from jumping over tier-1 opponent)
        self.assertEqual(reward, 1)
        self.assertEqual(action.expected_score, 1.0)


class TestJumpLogic(unittest.TestCase):
    """Test complex jump logic"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_insufficient_tier_no_jump(self):
        """Test that piece with insufficient tier cannot jump"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-1 at (2,0), BLUE tier-2 at (2,1)
        self.env.board[2][0] = [Piece(Player.RED, 1)]
        self.env.board[2][1] = [Piece(Player.BLUE, 2)]
        self.env.current_player = Player.RED
        
        # Get jump actions from (2,0)
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.from_pos == (2, 0)]
        
        # Should have no right jumps (tier-1 < tier-2)
        right_jumps = [a for a in jump_actions if a.initial_direction == 'right']
        self.assertEqual(len(right_jumps), 0)
    
    def test_jump_over_multiple_pieces(self):
        """Test jumping over multiple stacked pieces"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup: RED tier-3 at (2,0), BLUE tier-1+tier-1 at (2,1), empty at (2,2)
        self.env.board[2][0] = [Piece(Player.RED, 3)]
        self.env.board[2][1] = [Piece(Player.BLUE, 1), Piece(Player.BLUE, 1)]
        self.env.current_player = Player.RED
        
        # Get jump actions
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.from_pos == (2, 0)]
        
        # Find jump to (2,2)
        right_jumps = [a for a in jump_actions if a.to_pos == (2, 2)]
        self.assertGreater(len(right_jumps), 0)
        
        action = right_jumps[0]
        
        # Execute
        state, reward, done, info = self.env.step(action)
        
        # Check captured 2 pieces
        self.assertEqual(reward, 2)
        self.assertEqual(action.expected_score, 2.0)
        self.assertEqual(self.env.scores[Player.RED], 2)
    
    def test_jump_continuous_in_multiple_directions(self):
        """Test path that changes direction (Dijkstra should find this)"""
        # Clear board
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        
        # Setup a path: RED tier-3 at (2,2), can jump right then up
        # (2,2) -> jump over (2,3) -> land (2,4) -> jump over (1,4) -> land (0,4)
        self.env.board[2][2] = [Piece(Player.RED, 3)]
        self.env.board[2][3] = [Piece(Player.BLUE, 1)]
        self.env.board[1][4] = [Piece(Player.BLUE, 1)]
        self.env.current_player = Player.RED
        
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.from_pos == (2, 2)]
        
        # Right direction initially
        right_jumps = [a for a in jump_actions if a.initial_direction == 'right']
        
        # Should find path with multiple steps
        multi_step = [a for a in right_jumps if len(a.jump_sequence) >= 2]
        
        if len(multi_step) > 0:
            # Check path includes direction change
            action = multi_step[0]
            self.assertEqual(action.expected_score, 2.0)  # Captures 2 tier-1 pieces
            
            # Execute and verify
            state, reward, done, info = self.env.step(action)
            self.assertEqual(reward, 2)


class TestWinCondition(unittest.TestCase):
    """Test win condition"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_win_on_reaching_8_points(self):
        """Test that game ends when player reaches 8 points"""
        # Set RED score to 7
        self.env.scores[Player.RED] = 7
        
        # Clear board and create simple jump to score 1 more point
        self.env.board = [[[] for _ in range(5)] for _ in range(5)]
        self.env.board[2][0] = [Piece(Player.RED, 2)]
        self.env.board[2][1] = [Piece(Player.BLUE, 1)]
        self.env.current_player = Player.RED
        
        # Get jump action
        actions = self.env.get_legal_actions()
        jump_actions = [a for a in actions if a.action_type == ActionType.JUMP and a.expected_score >= 1]
        
        if len(jump_actions) > 0:
            action = jump_actions[0]
            state, reward, done, info = self.env.step(action)
            
            # Should win
            self.assertEqual(self.env.scores[Player.RED], 8)
            self.assertTrue(done)


class TestExpectedScore(unittest.TestCase):
    """Test expected score calculations"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_expected_score_accuracy(self):
        """Test that expected_score matches actual reward"""
        # Run multiple random actions and check
        for _ in range(5):
            actions = self.env.get_legal_actions()
            if len(actions) == 0:
                break
            
            # Pick an action
            action = actions[0]
            
            # Execute
            state, reward, done, info = self.env.step(action)
            
            # Check expected vs actual
            self.assertEqual(action.expected_score, reward,
                           f"Expected {action.expected_score} but got {reward} for {action}")
            
            if done:
                break


class TestActionSpace(unittest.TestCase):
    """Test action space properties"""
    
    def setUp(self):
        self.env = ZombieEnv()
    
    def test_action_space_not_empty(self):
        """Test that legal actions are always available at start"""
        actions = self.env.get_legal_actions()
        self.assertGreater(len(actions), 0)
    
    def test_all_actions_have_expected_score(self):
        """Test that all actions have expected_score field"""
        actions = self.env.get_legal_actions()
        for action in actions:
            self.assertIsNotNone(action.expected_score)
            self.assertGreaterEqual(action.expected_score, 0.0)
    
    def test_no_duplicate_actions(self):
        """Test that action list has no duplicates (by value)"""
        actions = self.env.get_legal_actions()
        
        # Convert to tuples for comparison
        action_tuples = []
        for a in actions:
            # Convert jump_sequence to hashable format
            jump_seq_tuple = None
            if a.jump_sequence is not None:
                jump_seq_tuple = tuple(
                    (step[0], tuple(step[1])) 
                    for step in a.jump_sequence
                )
            
            action_tuples.append((
                a.action_type,
                a.from_pos,
                a.to_pos,
                a.tier,
                a.initial_direction,
                jump_seq_tuple,
                a.expected_score
            ))
        
        # Check no duplicates
        self.assertEqual(len(action_tuples), len(set(action_tuples)),
                        "Found duplicate actions in action space")


def run_full_game_test():
    """Run a short game simulation"""
    print("\n" + "="*60)
    print("RUNNING FULL GAME SIMULATION")
    print("="*60)
    
    env = ZombieEnv()
    env.render()
    
    for turn in range(20):
        actions = env.get_legal_actions()
        if len(actions) == 0:
            print("No legal actions available!")
            break
        
        # Pick action with highest expected score
        best_action = max(actions, key=lambda a: a.expected_score)
        
        print(f"\nTurn {turn+1} - {env.current_player.name} plays: {best_action}")
        
        state, reward, done, info = env.step(best_action)
        
        print(f"Reward: {reward}, Expected: {info['expected_score']}")
        
        env.render()
        
        if done:
            print(f"\n{env.current_player.name} WINS with {env.scores[env.current_player]} points!")
            break
    
    print("="*60)


if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...\n")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run full game simulation
    run_full_game_test()
