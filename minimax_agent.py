"""
Minimax Agent for Zombie Game with Alpha-Beta Pruning

使用 Minimax 算法进行博弈树搜索：
- Alpha-Beta 剪枝提高搜索效率
- 可调节搜索深度
- 启发式评估函数评估非终止状态
- 移动排序优化剪枝效果
"""

import copy
import math
from typing import Optional, Tuple, List
from Zombie_env import ZombieEnv, Action, ActionType, Player, Piece


class MinimaxAgent:
    """Minimax agent with alpha-beta pruning"""
    
    def __init__(self, player: Player, max_depth: int = 3, verbose: bool = True):
        """
        Initialize Minimax Agent
        
        Args:
            player: The player this agent controls (RED or BLUE)
            max_depth: Maximum search depth (higher = stronger but slower)
            verbose: Print search information
        """
        self.player = player
        self.max_depth = max_depth
        self.verbose = verbose
        self.nodes_searched = 0  # Statistics
        self.pruned_count = 0    # Statistics
    
    def get_action(self, env: ZombieEnv) -> Optional[Action]:

        """ if the env is ZombieEnvGui, we need to get the underlying env for the minimax search """
        if hasattr(env, 'env'):
            env = env.env
        """
        Select best action using minimax search
        
        Returns:
            Best action according to minimax evaluation
        """
        self.nodes_searched = 0
        self.pruned_count = 0
        
        legal_actions = env.get_legal_actions()
        
        if not legal_actions:
            return None
        
        if len(legal_actions) == 1:
            return legal_actions[0]
        
        # Minimax search
        best_action = None
        best_value = -math.inf
        alpha = -math.inf
        beta = math.inf
        
        # Sort actions for better pruning (high-score moves first)
        sorted_actions = self._sort_actions(legal_actions, env)
        
        if self.verbose:
            print(f"\n[Minimax] Searching {len(sorted_actions)} actions at depth {self.max_depth}...")
        
        for action in sorted_actions:
            # Simulate action
            env_copy = copy.deepcopy(env)
            env_copy.step(action)
            
            # Minimax search (opponent's turn)
            value = self._minimax(env_copy, self.max_depth - 1, alpha, beta, False)
            
            if self.verbose:
                print(f"  Action: {action} -> Value: {value:.2f}")
            
            if value > best_value:
                best_value = value
                best_action = action
            
            alpha = max(alpha, value)
        
        if self.verbose:
            print(f"[Minimax] Best action: {best_action} (value={best_value:.2f})")
            print(f"[Stats] Nodes searched: {self.nodes_searched}, Pruned: {self.pruned_count}")
        
        return best_action
    
    def _minimax(self, env: ZombieEnv, depth: int, alpha: float, beta: float, 
                 is_maximizing: bool) -> float:
        """
        Minimax algorithm with alpha-beta pruning
        
        Args:
            env: Current game state
            depth: Remaining search depth
            alpha: Alpha value for pruning
            beta: Beta value for pruning
            is_maximizing: True if maximizing player's turn
        
        Returns:
            Evaluation value of the state
        """
        self.nodes_searched += 1
        
        # Check if game is over
        current_player = env.current_player
        opponent = Player.BLUE if current_player == Player.RED else Player.RED
        
        # Terminal state: someone won
        if env.scores[self.player] >= env.win_score:
            return 10000  # We win
        if env.scores[opponent] >= env.win_score:
            return -10000  # Opponent wins
        
        # Depth limit reached: evaluate state
        if depth == 0:
            return self._evaluate_state(env)
        
        legal_actions = env.get_legal_actions()
        
        # No legal actions: opponent wins
        if not legal_actions:
            if is_maximizing:
                return -10000  # We lose
            else:
                return 10000   # Opponent loses (we win)
        
        # Sort actions for better pruning
        sorted_actions = self._sort_actions(legal_actions, env)
        
        if is_maximizing:
            # Maximizing player (us)
            max_eval = -math.inf
            for action in sorted_actions:
                env_copy = copy.deepcopy(env)
                env_copy.step(action)
                
                eval_value = self._minimax(env_copy, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval_value)
                alpha = max(alpha, eval_value)
                
                if beta <= alpha:
                    self.pruned_count += 1
                    break  # Beta cutoff
            
            return max_eval
        else:
            # Minimizing player (opponent)
            min_eval = math.inf
            for action in sorted_actions:
                env_copy = copy.deepcopy(env)
                env_copy.step(action)
                
                eval_value = self._minimax(env_copy, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval_value)
                beta = min(beta, eval_value)
                
                if beta <= alpha:
                    self.pruned_count += 1
                    break  # Alpha cutoff
            
            return min_eval
    
    def _evaluate_state(self, env: ZombieEnv) -> float:
        """
        Heuristic evaluation function for non-terminal states
        
        Considers:
        1. Score difference (most important)
        2. Board piece values
        3. Underworld piece values
        4. Positional advantages
        
        Returns:
            Evaluation score (positive = good for us, negative = bad)
        """
        opponent = Player.BLUE if self.player == Player.RED else Player.RED
        
        score = 0.0
        
        # 1. Score difference (weight: 100)
        score_diff = env.scores[self.player] - env.scores[opponent]
        score += score_diff * 100
        
        # 2. Board piece values
        our_board_value = 0
        opp_board_value = 0
        our_piece_positions = []
        opp_piece_positions = []
        
        for r in range(env.board_size):
            for c in range(env.board_size):
                cell = env.board[r][c]
                if len(cell) > 0:
                    for piece in cell:
                        piece_value = piece.tier
                        # Bonus for stacking
                        if len(cell) > 1:
                            piece_value *= 1.2
                        
                        # Positional bonus (center control)
                        center_dist = abs(r - 2) + abs(c - 2)
                        position_bonus = (4 - center_dist) * 0.5
                        
                        if piece.player == self.player:
                            our_board_value += piece_value + position_bonus
                            our_piece_positions.append((r, c))
                        else:
                            opp_board_value += piece_value + position_bonus
                            opp_piece_positions.append((r, c))
        
        score += (our_board_value - opp_board_value) * 10
        
        # 3. Underworld piece values (slight penalty)
        our_underworld = sum(tier * count for tier, count in env.underworld[self.player].items())
        opp_underworld = sum(tier * count for tier, count in env.underworld[opponent].items())
        score += (opp_underworld - our_underworld) * 2  # Opponent's pieces in underworld is good
        
        # 4. Tactical advantages
        # 4a. Proximity to opponent (aggressive positioning)
        if our_piece_positions and opp_piece_positions:
            avg_distance = 0
            for our_pos in our_piece_positions:
                min_dist = min(abs(our_pos[0] - opp[0]) + abs(our_pos[1] - opp[1]) 
                              for opp in opp_piece_positions)
                avg_distance += min_dist
            avg_distance /= len(our_piece_positions)
            # Closer is better (more jump opportunities)
            score += (10 - avg_distance) * 1.0
        
        # 4b. Tier diversity on board (having high-tier pieces active is good)
        our_max_tier = max((p.tier for r in env.board for cell in r for p in cell 
                           if p.player == self.player), default=0)
        opp_max_tier = max((p.tier for r in env.board for cell in r for p in cell 
                           if p.player == opponent), default=0)
        score += (our_max_tier - opp_max_tier) * 2
        
        return score
    
    def _sort_actions(self, actions: List[Action], env: ZombieEnv) -> List[Action]:
        """
        Sort actions to improve alpha-beta pruning efficiency
        
        Priority:
        1. High-scoring jumps
        2. Revives of high-tier pieces
        3. Strategic moves
        4. Others
        """
        def action_priority(action: Action) -> float:
            priority = 0.0
            
            # Jumps with high expected score
            if action.action_type == ActionType.JUMP:
                priority += action.expected_score * 100
            
            # Revive high-tier pieces
            elif action.action_type == ActionType.REVIVE:
                priority += action.tier * 10
                # Bonus for center revival
                r, c = action.to_pos
                center_dist = abs(r - 2) + abs(c - 2)
                priority += (4 - center_dist) * 2
            
            # Strategic moves
            elif action.action_type == ActionType.MOVE:
                to_r, to_c = action.to_pos
                # Center control
                center_dist = abs(to_r - 2) + abs(to_c - 2)
                priority += (4 - center_dist)
                # Stacking bonus
                if len(env.board[to_r][to_c]) > 0:
                    priority += 5
            
            return priority
        
        return sorted(actions, key=action_priority, reverse=True)

from gui_wrapper import ZombieEnvGui

def play_game(agent1, agent2, render: bool = True, max_turns: int = 100) -> Optional[Player]:
    """
    Play a full game between two agents
    
    Args:
        agent1: RED player agent
        agent2: BLUE player agent
        render: Whether to render the game state
        max_turns: Maximum number of turns before draw
    
    Returns:
        Winner (Player.RED or Player.BLUE), or None if draw
    """
    env = ZombieEnv()

    env_gui = ZombieEnvGui(env)  # Wrap with GUI for rendering
    
    if render:
        print("\n" + "="*80)
        print("GAME START: Minimax Agent Demo")
        print("="*80)
        env_gui.render(show_wait_prompt=True)
        print("Press any key to start...")
        if not env_gui.wait_for_key():
            return
 
    
    agents = {Player.RED: agent1, Player.BLUE: agent2}
    
    for turn in range(max_turns):
        current_agent = agents[env.current_player]
        
        # Get action from agent
        if render:
            print(f"\n{'='*80}")
            print(f"Turn {turn + 1} - {env.current_player.name}'s turn")
            print(f"{'='*80}")
        
        action = current_agent.get_action(env_gui)
        
        if action is None:
            print(f"\n{env.current_player.name} has no legal actions! Game ends.")
            opponent = Player.BLUE if env.current_player == Player.RED else Player.BLUE
            return opponent
        
        if render:
            print(f"\nChosen action: {action}")
        
        # Execute action
        state, reward, done, info = env_gui.step(action)
        
        if render:
            print(f"Reward: {reward}")
            env_gui.render(show_wait_prompt=True)
        
        if done:
            winner = env.current_player
            if render:
                print(f"\n{'='*80}")
                print(f"🏆 {winner.name} WINS with {env.scores[winner]} points!")
                print(f"{'='*80}")
            return winner
                # Wait for key press before next turn
        print("Press any key to continue...")
        if not env_gui.wait_for_key():
            break
    
    # Max turns reached - determine winner by score
    if render:
        print(f"\nMax turns ({max_turns}) reached. Game ends.")
        print(f"Final scores - RED: {env.scores[Player.RED]}, BLUE: {env.scores[Player.BLUE]}")
    
    if env.scores[Player.RED] > env.scores[Player.BLUE]:
        return Player.RED
    elif env.scores[Player.BLUE] > env.scores[Player.RED]:
        return Player.BLUE
    else:
        return None


def run_tournament(agent1_depth: int = 3, agent2_depth: int = 3, num_games: int = 5) -> dict:
    """
    Run tournament between minimax agents
    
    Args:
        agent1_depth: Search depth for RED player
        agent2_depth: Search depth for BLUE player
        num_games: Number of games to play
    
    Returns:
        Dictionary with statistics
    """
    print(f"\n{'='*80}")
    print(f"MINIMAX TOURNAMENT")
    print(f"RED depth={agent1_depth} vs BLUE depth={agent2_depth}")
    print(f"Games: {num_games}")
    print(f"{'='*80}\n")
    
    results = {
        Player.RED: 0,
        Player.BLUE: 0,
        'draws': 0,
        'total_turns': 0,
        'total_nodes': 0
    }
    
    for game_num in range(num_games):
        print(f"\n{'='*80}")
        print(f"Game {game_num + 1}/{num_games}")
        print(f"{'='*80}")
        
        agent1 = MinimaxAgent(Player.RED, max_depth=agent1_depth, verbose=False)
        agent2 = MinimaxAgent(Player.BLUE, max_depth=agent2_depth, verbose=False)
        
        env = ZombieEnv()
        turn = 0
        
        while turn < 100:
            agent = agent1 if env.current_player == Player.RED else agent2
            action = agent.get_action(env)
            
            if action is None:
                opponent = Player.BLUE if env.current_player == Player.RED else Player.RED
                results[opponent] += 1
                print(f"{env.current_player.name} has no legal actions. {opponent.name} wins!")
                break
            
            state, reward, done, info = env.step(action)
            turn += 1
            
            if done:
                winner = env.current_player
                results[winner] += 1
                print(f"{winner.name} wins in {turn} turns! Score: {env.scores[winner]}")
                break
        else:
            # Draw or timeout
            if env.scores[Player.RED] > env.scores[Player.BLUE]:
                results[Player.RED] += 1
                print(f"Game timeout. RED wins by score {env.scores[Player.RED]}-{env.scores[Player.BLUE]}")
            elif env.scores[Player.BLUE] > env.scores[Player.RED]:
                results[Player.BLUE] += 1
                print(f"Game timeout. BLUE wins by score {env.scores[Player.BLUE]}-{env.scores[Player.RED]}")
            else:
                results['draws'] += 1
                print(f"Game timeout. Draw {env.scores[Player.RED]}-{env.scores[Player.BLUE]}")
        
        results['total_turns'] += turn
        results['total_nodes'] += agent1.nodes_searched + agent2.nodes_searched
    
    # Print results
    print(f"\n{'='*80}")
    print("TOURNAMENT RESULTS")
    print(f"{'='*80}")
    print(f"RED wins: {results[Player.RED]} ({results[Player.RED]/num_games*100:.1f}%)")
    print(f"BLUE wins: {results[Player.BLUE]} ({results[Player.BLUE]/num_games*100:.1f}%)")
    print(f"Draws: {results['draws']} ({results['draws']/num_games*100:.1f}%)")
    print(f"Average turns per game: {results['total_turns']/num_games:.1f}")
    print(f"Average nodes searched per game: {results['total_nodes']/num_games:.0f}")
    print(f"{'='*80}\n")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "tournament":
            # Tournament mode
            depth1 = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            depth2 = int(sys.argv[3]) if len(sys.argv) > 3 else 3
            num_games = int(sys.argv[4]) if len(sys.argv) > 4 else 5
            run_tournament(depth1, depth2, num_games)
        
        elif sys.argv[1] == "vs_greedy":
            # Minimax vs Greedy
            from simple_agent import SimpleGreedyAgent
            
            print("\n" + "="*80)
            print("Minimax vs Greedy Agent")
            print("="*80)
            
            depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            minimax_agent = MinimaxAgent(Player.RED, max_depth=depth, verbose=True)
            greedy_agent = SimpleGreedyAgent(Player.BLUE, verbose=True)
            
            winner = play_game(minimax_agent, greedy_agent, render=True)
            
            if winner:
                print(f"\n🏆 Winner: {winner.name}")
            else:
                print("\n🤝 Draw!")
        
        else:
            print("Unknown command")
            sys.exit(1)
    else:
        # Demo: Minimax vs Minimax
        print("\nCreating Minimax agents...")
        agent_red = MinimaxAgent(Player.RED, max_depth=2, verbose=True)
        agent_blue = MinimaxAgent(Player.BLUE, max_depth=2, verbose=True)
        
        winner = play_game(agent_red, agent_blue, render=True, max_turns=50)
        
        if winner:
            print(f"\n🏆 Winner: {winner.name}")
        else:
            print("\n🤝 Draw!")
    
    print("\n" + "="*80)
    print("USAGE:")
    print("  python minimax_agent.py                          # Demo: Minimax vs Minimax (depth=2)")
    print("  python minimax_agent.py tournament [d1] [d2] [n] # Tournament: depth d1 vs d2, n games")
    print("  python minimax_agent.py vs_greedy [depth]        # Minimax vs Greedy Agent")
    print("\nEXAMPLES:")
    print("  python minimax_agent.py tournament 3 3 10        # 10 games, both depth=3")
    print("  python minimax_agent.py vs_greedy 4              # Minimax (depth=4) vs Greedy")
    print("="*80)