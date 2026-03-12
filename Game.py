"""
Game Manager for Zombie Game

Supports various agent matchups:
- Greedy vs Greedy
- Minimax vs Greedy
- Manual vs AI
- etc.

Usage:
    python Game.py greedy greedy           # Greedy vs Greedy
    python Game.py minimax:3 greedy        # Minimax(depth=3) vs Greedy
    python Game.py manual minimax:2        # Human vs Minimax(depth=2)
    python Game.py minimax:3 minimax:2 --gui  # With GUI
"""

import sys
from typing import Optional, Dict, Any
from Zombie_env import ZombieEnv, Player, Card
from gui_wrapper import ZombieEnvGui


class AgentFactory:
    """Factory for creating different types of agents"""
    
    @staticmethod
    def create_agent(agent_spec: str, player: Player, verbose: bool = True):
        """
        Create an agent from specification string
        
        Args:
            agent_spec: Agent specification in format "type[:param]"
                Examples: "greedy", "minimax:3", "manual"
            player: Player color (RED or BLUE)
            verbose: Whether agent should print info
        
        Returns:
            Agent instance
        """
        parts = agent_spec.lower().split(':')
        agent_type = parts[0]
        
        if agent_type == 'greedy':
            from simple_agent import SimpleGreedyAgent
            return SimpleGreedyAgent(player, verbose=verbose)
        
        elif agent_type == 'minimax':
            from minimax_agent import MinimaxAgent
            depth = int(parts[1]) if len(parts) > 1 else 3
            return MinimaxAgent(player, max_depth=depth, verbose=verbose)
        
        elif agent_type == 'manual':
            from manual_agent import ManualAgent
            return ManualAgent(player)
        
        elif agent_type == 'random':
            from random_agent import RandomAgent
            return RandomAgent(player)
        
        else:
            raise ValueError(f"Unknown agent type: {agent_type}. "
                           f"Available: greedy, minimax[:depth], manual, random")
    
    @staticmethod
    def parse_agent_name(agent_spec: str) -> str:
        """Get human-readable agent name from spec"""
        parts = agent_spec.lower().split(':')
        agent_type = parts[0]
        
        if agent_type == 'greedy':
            return "Greedy"
        elif agent_type == 'minimax':
            depth = parts[1] if len(parts) > 1 else '3'
            return f"Minimax(d={depth})"
        elif agent_type == 'manual':
            return "Human"
        elif agent_type == 'random':
            return "Random"
        else:
            return agent_spec


class Game:
    """Game manager for agent matchups"""
    
    def __init__(self, red_agent_spec: str, blue_agent_spec: str,
                 use_gui: bool = False, animate: bool = True,
                 verbose: bool = True, max_turns: int = 100,
                 red_card: Card = Card.NONE, blue_card: Card = Card.NONE):
        """
        Initialize game
        
        Args:
            red_agent_spec: RED player agent specification
            blue_agent_spec: BLUE player agent specification
            use_gui: Whether to use GUI rendering
            animate: Whether to show animations (GUI only)
            verbose: Whether to print game info
            max_turns: Maximum turns before draw
        """
        self.red_agent_spec = red_agent_spec
        self.blue_agent_spec = blue_agent_spec
        self.use_gui = use_gui
        self.animate = animate
        self.verbose = verbose
        self.max_turns = max_turns
        self.red_card = red_card
        self.blue_card = blue_card
        
        # Create environment
        self.env = ZombieEnv(red_card=red_card, blue_card=blue_card)
        
        # Create GUI wrapper if needed
        if self.use_gui or 'manual' in red_agent_spec.lower() or 'manual' in blue_agent_spec.lower():
            # Manual agent requires GUI
            self.env_gui = ZombieEnvGui(self.env, cell_size=100)
            # Adjust window for manual agent
            if 'manual' in red_agent_spec.lower() or 'manual' in blue_agent_spec.lower():
                self.env_gui.window_width = self.env_gui.board_width + 2 * self.env_gui.margin + 400
                self.env_gui.screen = self.env_gui.screen = pygame.display.set_mode(
                    (self.env_gui.window_width, self.env_gui.window_height)
                )
        else:
            self.env_gui = None
        
        # Create agents
        self.agents = {
            Player.RED: AgentFactory.create_agent(red_agent_spec, Player.RED, verbose),
            Player.BLUE: AgentFactory.create_agent(blue_agent_spec, Player.BLUE, verbose)
        }
        
        # Agent names for display
        self.agent_names = {
            Player.RED: AgentFactory.parse_agent_name(red_agent_spec),
            Player.BLUE: AgentFactory.parse_agent_name(blue_agent_spec)
        }
    
    def play(self) -> Dict[str, Any]:
        """
        Play a complete game
        
        Returns:
            Dictionary with game results
        """
        if self.verbose:
            print("\n" + "="*80)
            print(f"GAME START")
            print(f"RED: {self.agent_names[Player.RED]}")
            print(f"BLUE: {self.agent_names[Player.BLUE]}")
            print("="*80)
        
        # Initial render
        if self.env_gui:
            if self.use_gui:
                self.env_gui.render()
                print("\nClick Continue button to start...")
                if not self.env_gui.wait_for_continue_button():
                    return {'winner': None, 'reason': 'cancelled'}
        else:
            if self.verbose:
                self.env.render()
        
        # Game loop
        turn = 0
        last_action = None
        
        while turn < self.max_turns:
            current_player = self.env.current_player
            agent = self.agents[current_player]
            
            if self.verbose:
                print(f"\n{'='*80}")
                print(f"Turn {turn + 1} - {current_player.name} ({self.agent_names[current_player]})")
                print(f"Scores: RED={self.env.scores[Player.RED]}, BLUE={self.env.scores[Player.BLUE]}")
                print(f"{'='*80}")
            
            # Get action
            if self.env_gui and hasattr(agent, '_select_action_gui'):
                # Manual agent
                action = agent.get_action(self.env_gui)
            else:
                # AI agent
                action = agent.get_action(self.env_gui if self.env_gui else self.env)
            
            if action is None:
                if self.verbose:
                    print(f"\n{current_player.name} has no legal actions!")
                opponent = Player.BLUE if current_player == Player.RED else Player.RED
                return {
                    'winner': opponent,
                    'reason': 'no_legal_actions',
                    'turns': turn,
                    'scores': dict(self.env.scores),
                    'winner_name': self.agent_names[opponent]
                }
            
            if self.verbose:
                print(f"Action: {action}")
            
            # Execute action
            if self.env_gui:
                state, reward, done, info = self.env_gui.step(action, animate=self.animate)
            else:
                state, reward, done, info = self.env.step(action)
            
            if self.verbose:
                print(f"Reward: {reward}")
            
            # Render
            if self.env_gui:
                if self.use_gui:
                    # Check if it's manual agent's turn
                    is_manual = hasattr(agent, '_select_action_gui')
                    self.env_gui.render(last_action=action)
                    
                    # Wait for continue button (except for manual agent's next turn)
                    if not done and not is_manual:
                        print("Click Continue button to continue...")
                        if not self.env_gui.wait_for_continue_button():
                            return {'winner': None, 'reason': 'cancelled', 'turns': turn}
            else:
                if self.verbose:
                    self.env.render()
            
            last_action = action
            turn += 1
            
            # Check if game over
            if done:
                winner = current_player
                if self.verbose:
                    print(f"\n{'='*80}")
                    print(f"🏆 {winner.name} ({self.agent_names[winner]}) WINS!")
                    print(f"Score: {self.env.scores[winner]}/{self.env.win_score}")
                    print(f"Turns: {turn}")
                    print(f"{'='*80}")
                
                # Show winner in GUI
                if self.env_gui and self.use_gui:
                    import pygame
                    font = self.env_gui.font_large
                    win_color = self.env_gui.colors['red'] if winner == Player.RED else self.env_gui.colors['blue']
                    text = font.render(f"{winner.name} WINS!", True, win_color)
                    text_rect = text.get_rect(center=(self.env_gui.window_width // 2, 50))
                    self.env_gui.screen.blit(text, text_rect)
                    pygame.display.flip()
                    
                    print("\nClick Continue button to close...")
                    self.env_gui.wait_for_continue_button()
                
                return {
                    'winner': winner,
                    'reason': 'reached_win_score',
                    'turns': turn,
                    'scores': dict(self.env.scores),
                    'winner_name': self.agent_names[winner]
                }
        
        # Max turns reached
        if self.verbose:
            print(f"\nMax turns ({self.max_turns}) reached.")
            print(f"Final scores - RED: {self.env.scores[Player.RED]}, BLUE: {self.env.scores[Player.BLUE]}")
        
        # Determine winner by score
        if self.env.scores[Player.RED] > self.env.scores[Player.BLUE]:
            winner = Player.RED
        elif self.env.scores[Player.BLUE] > self.env.scores[Player.RED]:
            winner = Player.BLUE
        else:
            winner = None
        
        return {
            'winner': winner,
            'reason': 'max_turns',
            'turns': turn,
            'scores': dict(self.env.scores),
            'winner_name': self.agent_names[winner] if winner else 'Draw'
        }
    
    def cleanup(self):
        """Clean up resources"""
        if self.env_gui:
            self.env_gui.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Play a Zombie Game match between two agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Agent Specifications:
  greedy              Simple greedy agent
  minimax[:depth]     Minimax agent with optional depth (default: 3)
  manual              Human player (requires GUI)
  random              Random agent

Examples:
  python Game.py greedy greedy                    # Greedy vs Greedy
  python Game.py minimax:3 greedy                 # Minimax(3) vs Greedy
  python Game.py manual minimax:2                 # Human vs Minimax(2)
  python Game.py minimax:4 minimax:3 --gui        # With GUI visualization
  python Game.py greedy minimax:2 --no-animate    # GUI without animation
        """
    )
    
    parser.add_argument('red_agent', type=str, help='RED player agent specification')
    parser.add_argument('blue_agent', type=str, help='BLUE player agent specification')
    parser.add_argument('--gui', action='store_true', help='Use GUI rendering')
    parser.add_argument('--no-animate', action='store_true', help='Disable animations')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--max-turns', type=int, default=100, help='Maximum turns (default: 100)')
    parser.add_argument('--red-card', type=int, default=0, help='RED player card (0-9, default: 0=none)')
    parser.add_argument('--blue-card', type=int, default=0, help='BLUE player card (0-9, default: 0=none)')
    
    args = parser.parse_args()
    
    # Determine if GUI is needed
    use_gui = args.gui or 'manual' in args.red_agent.lower() or 'manual' in args.blue_agent.lower()
    
    # Create and play game
    game = Game(
        red_agent_spec=args.red_agent,
        blue_agent_spec=args.blue_agent,
        use_gui=use_gui,
        animate=not args.no_animate,
        verbose=not args.quiet,
        max_turns=args.max_turns,
        red_card=Card(args.red_card),
        blue_card=Card(args.blue_card)
    )
    
    try:
        result = game.play()
        
        # Print summary
        if not args.quiet:
            print("\n" + "="*80)
            print("GAME SUMMARY")
            print("="*80)
            print(f"Winner: {result.get('winner_name', 'None')}")
            print(f"Reason: {result.get('reason', 'unknown')}")
            print(f"Turns: {result.get('turns', 0)}")
            if result.get('scores'):
                print(f"Final Scores: RED={result['scores'][Player.RED]}, BLUE={result['scores'][Player.BLUE]}")
            print("="*80)
    
    finally:
        game.cleanup()


if __name__ == "__main__":
    # Check if we need to import pygame for GUI
    if '--gui' in sys.argv or 'manual' in ' '.join(sys.argv).lower():
        import pygame
    
    main()