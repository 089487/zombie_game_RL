"""
Simple Greedy Agent for Zombie Game

策略优先级：
1. 优先执行得分最高的跳跃 (expected_score > 0)
2. 如果没有得分的跳跃：
   a. 复活最高tier的棋子到中心区域
   b. 移动棋子靠近敌人（进攻）
   c. 移动棋子到中心区域（提高灵活性）
   d. 随机移动
"""

import random
from typing import Optional
from Zombie_env import ZombieEnv, Action, ActionType, Player


class SimpleGreedyAgent:
    """Simple greedy agent using heuristics"""
    
    def __init__(self, player: Player, verbose: bool = True):
        self.player = player
        self.verbose = verbose
    
    def get_action(self, env: ZombieEnv) -> Optional[Action]:
        """
        Select best action based on greedy strategy
        
        Priority:
        1. Highest scoring JUMP
        2. REVIVE highest tier to strategic position
        3. MOVE towards opponent
        4. MOVE towards center
        5. Random MOVE
        """
        legal_actions = env.get_legal_actions()
        
        if not legal_actions:
            return None
        
        # Strategy 1: Greedy jump - highest score
        jump_actions = [a for a in legal_actions if a.action_type == ActionType.JUMP]
        if jump_actions:
            best_jump = max(jump_actions, key=lambda a: a.expected_score)
            if best_jump.expected_score > 0:
                if self.verbose:
                    print(f"[Greedy] Choosing JUMP with score {best_jump.expected_score}")
                return best_jump
        
        # Strategy 2: Revive highest tier to strategic position
        revive_actions = [a for a in legal_actions if a.action_type == ActionType.REVIVE]
        if revive_actions:
            # Sort by tier (highest first)
            revive_actions.sort(key=lambda a: a.tier, reverse=True)
            
            # Prefer center positions for revival
            center_positions = [(2, 2), (2, 1), (2, 3), (1, 2), (3, 2)]
            for action in revive_actions:
                if action.to_pos in center_positions:
                    if self.verbose:
                        print(f"[Strategic] Reviving tier-{action.tier} to center {action.to_pos}")
                    return action
            
            # Otherwise revive highest tier anywhere
            best_revive = revive_actions[0]
            if self.verbose:
                print(f"[Strategic] Reviving tier-{best_revive.tier} to {best_revive.to_pos}")
            return best_revive
        
        # Strategy 3 & 4: Move towards opponent or center
        move_actions = [a for a in legal_actions if a.action_type == ActionType.MOVE]
        if move_actions:
            # Score moves by strategic value
            scored_moves = []
            for action in move_actions:
                score = self._evaluate_move(action, env)
                scored_moves.append((score, action))
            
            # Pick best move
            scored_moves.sort(key=lambda x: x[0], reverse=True)
            best_move = scored_moves[0][1]
            if self.verbose:
                print(f"[Tactical] Moving from {best_move.from_pos} to {best_move.to_pos}")
            return best_move
        
        # Strategy 5: If only jumps with score=0, pick one
        if jump_actions:
            if self.verbose:
                print(f"[Defensive] Taking zero-score jump")
            return random.choice(jump_actions)
        
        # Fallback: random action
        if self.verbose:
            print(f"[Random] Choosing random action")
        return random.choice(legal_actions)
    
    def _evaluate_move(self, action: Action, env: ZombieEnv) -> float:
        """
        Evaluate strategic value of a move
        
        Returns higher score for better moves:
        - Moving towards opponent
        - Moving towards center
        - Stacking on higher tier
        """
        from_pos = action.from_pos
        to_pos = action.to_pos
        
        score = 0.0
        
        # Check if stacking
        target_cell = env.board[to_pos[0]][to_pos[1]]
        if len(target_cell) > 0:
            # Stacking bonus
            score += 5.0
            # Higher tier stack = better
            target_tier = sum(p.tier for p in target_cell)
            score += target_tier
        
        # Distance to center bonus
        center = (2, 2)
        from_dist_to_center = abs(from_pos[0] - center[0]) + abs(from_pos[1] - center[1])
        to_dist_to_center = abs(to_pos[0] - center[0]) + abs(to_pos[1] - center[1])
        if to_dist_to_center < from_dist_to_center:
            score += 2.0  # Moving closer to center
        
        # Distance to opponent bonus
        opponent = Player.BLUE if self.player == Player.RED else Player.RED
        opponent_positions = []
        for r in range(env.board_size):
            for c in range(env.board_size):
                if len(env.board[r][c]) > 0 and env.board[r][c][0].player == opponent:
                    opponent_positions.append((r, c))
        
        if opponent_positions:
            # Find closest opponent
            min_from_dist = min(abs(from_pos[0] - op[0]) + abs(from_pos[1] - op[1]) 
                               for op in opponent_positions)
            min_to_dist = min(abs(to_pos[0] - op[0]) + abs(to_pos[1] - op[1]) 
                             for op in opponent_positions)
            
            if min_to_dist < min_from_dist:
                score += 3.0  # Moving closer to opponent (aggressive)
        
        return score


def play_game(agent1: SimpleGreedyAgent, agent2: SimpleGreedyAgent, 
              render: bool = True, max_turns: int = 100) -> Optional[Player]:
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
    
    if render:
        print("\n" + "="*60)
        print("GAME START")
        print("="*60)
        env.render()
    
    agents = {Player.RED: agent1, Player.BLUE: agent2}
    
    for turn in range(max_turns):
        current_agent = agents[env.current_player]
        
        # Get action from agent
        action = current_agent.get_action(env)
        
        if action is None:
            print(f"\n{env.current_player.name} has no legal actions! Game ends.")
            # Opponent wins
            opponent = Player.BLUE if env.current_player == Player.RED else Player.RED
            return opponent
        
        if render:
            print(f"\nTurn {turn + 1} - {env.current_player.name}")
            print(f"Action: {action}")
        
        # Execute action
        state, reward, done, info = env.step(action)
        
        if render:
            print(f"Reward: {reward}")
            env.render()
        
        if done:
            winner = env.current_player
            if render:
                print(f"\n{'='*60}")
                print(f"{winner.name} WINS with {env.scores[winner]} points!")
                print(f"{'='*60}")
            return winner
    
    # Max turns reached - draw
    if render:
        print(f"\nMax turns ({max_turns}) reached. Game ends in draw.")
        print(f"Final scores - RED: {env.scores[Player.RED]}, BLUE: {env.scores[Player.BLUE]}")
    
    # Winner is player with higher score
    if env.scores[Player.RED] > env.scores[Player.BLUE]:
        return Player.RED
    elif env.scores[Player.BLUE] > env.scores[Player.RED]:
        return Player.BLUE
    else:
        return None  # True draw


def run_tournament(num_games: int = 10) -> dict:
    """
    Run multiple games and collect statistics
    
    Args:
        num_games: Number of games to play
    
    Returns:
        Dictionary with statistics
    """
    print(f"\n{'='*60}")
    print(f"RUNNING TOURNAMENT: {num_games} games")
    print(f"{'='*60}\n")
    
    results = {
        Player.RED: 0,
        Player.BLUE: 0,
        'draws': 0,
        'avg_turns': 0,
        'total_turns': 0
    }
    
    for game_num in range(num_games):
        print(f"\n--- Game {game_num + 1}/{num_games} ---")
        
        agent1 = SimpleGreedyAgent(Player.RED, verbose=False)
        agent2 = SimpleGreedyAgent(Player.BLUE, verbose=False)
        
        env = ZombieEnv()
        turn = 0
        
        while turn < 100:
            agent = agent1 if env.current_player == Player.RED else agent2
            action = agent.get_action(env)
            
            if action is None:
                # Opponent wins
                opponent = Player.BLUE if env.current_player == Player.RED else Player.RED
                results[opponent] += 1
                break
            
            state, reward, done, info = env.step(action)
            turn += 1
            
            if done:
                winner = env.current_player
                results[winner] += 1
                break
        else:
            # Draw
            if env.scores[Player.RED] > env.scores[Player.BLUE]:
                results[Player.RED] += 1
            elif env.scores[Player.BLUE] > env.scores[Player.RED]:
                results[Player.BLUE] += 1
            else:
                results['draws'] += 1
        
        results['total_turns'] += turn
        print(f"Game {game_num + 1} finished in {turn} turns. "
              f"Scores - RED: {env.scores[Player.RED]}, BLUE: {env.scores[Player.BLUE]}")
    
    results['avg_turns'] = results['total_turns'] / num_games
    
    print(f"\n{'='*60}")
    print("TOURNAMENT RESULTS")
    print(f"{'='*60}")
    print(f"RED wins: {results[Player.RED]} ({results[Player.RED]/num_games*100:.1f}%)")
    print(f"BLUE wins: {results[Player.BLUE]} ({results[Player.BLUE]/num_games*100:.1f}%)")
    print(f"Draws: {results['draws']} ({results['draws']/num_games*100:.1f}%)")
    print(f"Average turns per game: {results['avg_turns']:.1f}")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "tournament":
        # Run tournament
        num_games = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run_tournament(num_games)
    else:
        # Play single game with rendering
        print("\nCreating agents...")
        agent_red = SimpleGreedyAgent(Player.RED, verbose=True)
        agent_blue = SimpleGreedyAgent(Player.BLUE, verbose=True)
        
        print("\nPlaying game...")
        winner = play_game(agent_red, agent_blue, render=True)
        
        if winner:
            print(f"\n🏆 Winner: {winner.name}")
        else:
            print(f"\n🤝 Draw!")
        
        print("\n" + "="*60)
        print("USAGE:")
        print("  python simple_agent.py              # Play single game with visualization")
        print("  python simple_agent.py tournament   # Run 10 games without visualization")
        print("  python simple_agent.py tournament N # Run N games")
        print("="*60)