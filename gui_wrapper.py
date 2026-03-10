"""
GUI Wrapper for ZombieEnv using Pygame

Usage:
    env = ZombieEnv()
    env_gui = ZombieEnvGui(env)
    env_gui.render()
"""

import pygame
import time
from typing import Optional, Tuple, Dict
from Zombie_env import ZombieEnv, Player, Action, ActionType, Piece


class ZombieEnvGui:
    """GUI wrapper for ZombieEnv that adds visual rendering"""
    
    def __init__(self, env: ZombieEnv, cell_size: int = 100, fps: int = 30):
        """
        Initialize GUI wrapper
        
        Args:
            env: ZombieEnv instance to wrap
            cell_size: Size of each board cell in pixels (default: 100)
            fps: Frames per second for animations
        """
        self.env = env
        self.cell_size = cell_size
        self.fps = fps
        
        # Calculate window dimensions
        self.board_size = env.board_size
        self.board_width = self.board_size * cell_size
        self.margin = 50  # Reduced from 100
        self.info_height = 130  # Reduced from 200
        self.window_width = self.board_width + 2 * self.margin
        self.window_height = self.board_width + 2 * self.margin + self.info_height
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption("Zombie Board Game")
        self.clock = pygame.time.Clock()
        
        # Colors
        self.colors = {
            'bg': (240, 240, 240),
            'board': (220, 220, 220),
            'cell_light': (255, 255, 255),
            'cell_dark': (245, 245, 245),
            'cell_center': (255, 250, 200),
            'grid': (180, 180, 180),
            'red': (220, 50, 50),
            'red_light': (255, 100, 100),
            'blue': (50, 50, 220),
            'blue_light': (100, 100, 255),
            'text': (50, 50, 50),
            'highlight': (255, 215, 0),
            'underworld': (100, 100, 100)
        }
        
        # Fonts
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        # Animation state
        self.animation_queue = []
        self.is_animating = False
        
        # History for undo functionality
        self.state_history = []
        self.action_history = []
    def __getattr__(self, name):
        if name == 'env':
            raise AttributeError("ZombieEnvGui has no attribute 'env' to prevent infinite recursion")
        return getattr(self.env, name)
        
    # ========== Proxy Methods (delegate to wrapped env) ==========
    
    def reset(self):
        """Reset environment"""
        return self.env.reset()
    
    def get_legal_actions(self):
        """Get legal actions"""
        return self.env.get_legal_actions()
    
    def get_state(self):
        """Get current state"""
        return self.env.get_state()
    
    def step(self, action: Action, animate: bool = False) -> Tuple:
        """
        Execute action with optional animation
        
        Args:
            action: Action to execute
            animate: Whether to show animation
        
        Returns:
            (state, reward, done, info)
        """
        if animate:
            self._animate_action(action)
        
        result = self.env.step(action)
        
        if animate:
            time.sleep(0.3)  # Brief pause after action
        
        return result
    
    def save_state(self, action: Action):
        """Save current state before action for undo"""
        state = {
            'board': [[cell[:] for cell in row] for row in self.env.board],
            'underworld': {p: dict(u) for p, u in self.env.underworld.items()},
            'scores': dict(self.env.scores),
            'current_player': self.env.current_player
        }
        self.state_history.append(state)
        self.action_history.append(action)
    
    def undo(self) -> bool:
        """Undo last action, return True if successful"""
        if not self.state_history:
            return False
        
        # Restore previous state
        state = self.state_history.pop()
        self.action_history.pop()
        
        # Restore board
        self.env.board = [[cell[:] for cell in row] for row in state['board']]
        
        # Restore underworld
        for player, underworld in state['underworld'].items():
            self.env.underworld[player] = dict(underworld)
        
        # Restore scores
        self.env.scores = dict(state['scores'])
        
        # Restore current player
        self.env.current_player = state['current_player']
        
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.state_history) > 0
    
    def clear_history(self):
        """Clear undo history"""
        self.state_history.clear()
        self.action_history.clear()
    
    def close(self):
        """Close GUI"""
        pygame.quit()
    
    # ========== GUI Rendering Methods ==========
    
    def render(self, last_action: Optional[Action] = None, 
           highlight_cells: Optional[list] = None,
           show_wait_prompt: bool = False):
        """
        Render game state with GUI (overrides ZombieEnv.render())
        
        Args:
            last_action: Last action taken (for highlighting)
            highlight_cells: List of (row, col) to highlight
            show_wait_prompt: Whether to show continue button (deprecated, call wait_for_continue_button instead)
        """
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
                return
    
        # Clear screen
        self.screen.fill(self.colors['bg'])
        
        # Draw board
        self._draw_board(highlight_cells)
        
        # Draw pieces
        self._draw_pieces()
        
        # Draw info panel
        self._draw_info_panel(last_action)
        
        # Update display
        pygame.display.flip()
        self.clock.tick(self.fps)
    
    def _draw_wait_prompt(self):
        """Draw 'Press any key to continue' prompt (deprecated, use _draw_continue_button)"""
        center_x = self.window_width // 2
        prompt_y = self.window_height - 40
        
        # Draw background rectangle
        prompt_text = "Press any key to continue..."
        text = self.font_medium.render(prompt_text, True, (255, 255, 255))
        text_rect = text.get_rect(center=(center_x, prompt_y))
        
        # Draw semi-transparent background
        padding = 20
        bg_rect = pygame.Rect(
            text_rect.left - padding,
            text_rect.top - padding // 2,
            text_rect.width + padding * 2,
            text_rect.height + padding
        )
        
        # Create surface for transparency
        s = pygame.Surface((bg_rect.width, bg_rect.height))
        s.set_alpha(200)
        s.fill((50, 50, 50))
        self.screen.blit(s, bg_rect)
        
        # Draw text
        self.screen.blit(text, text_rect)
    
    def _draw_continue_button(self, mouse_pos: tuple) -> pygame.Rect:
        """Draw continue button at bottom center
        
        Args:
            mouse_pos: Current mouse position
            
        Returns:
            Button rectangle
        """
        center_x = self.window_width // 2
        button_y = self.window_height - 50  # Reduced from 60
        button_width = 135  # Reduced from 180 (75%)
        button_height = 30  # Reduced from 40 (75%)
        
        button_rect = pygame.Rect(
            center_x - button_width // 2,
            button_y,
            button_width,
            button_height
        )
        
        # Highlight on hover
        if button_rect.collidepoint(mouse_pos):
            button_color = (100, 200, 100)
        else:
            button_color = (70, 170, 70)
        
        # Draw button
        pygame.draw.rect(self.screen, button_color, button_rect, border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), button_rect, 3, border_radius=10)
        
        # Draw text
        text = self.font_medium.render("Continue ►", True, (255, 255, 255))
        text_rect = text.get_rect(center=button_rect.center)
        self.screen.blit(text, text_rect)
        
        return button_rect
    
    def _draw_board(self, highlight_cells: Optional[list] = None):
        """Draw the game board"""
        board_x = self.margin
        board_y = self.margin
        
        # Draw cells
        for row in range(self.board_size):
            for col in range(self.board_size):
                x = board_x + col * self.cell_size
                y = board_y + row * self.cell_size
                
                # Determine cell color
                if row == 2 and col == 2:
                    color = self.colors['cell_center']  # Center cell
                elif (row + col) % 2 == 0:
                    color = self.colors['cell_light']
                else:
                    color = self.colors['cell_dark']
                
                # Highlight if needed
                if highlight_cells and (row, col) in highlight_cells:
                    color = self.colors['highlight']
                
                # Draw cell
                pygame.draw.rect(self.screen, color, 
                               (x, y, self.cell_size, self.cell_size))
                
                # Draw grid
                pygame.draw.rect(self.screen, self.colors['grid'], 
                               (x, y, self.cell_size, self.cell_size), 2)
                
                # Draw coordinates (small)
                coord_text = self.font_small.render(f"{row},{col}", True, 
                                                    self.colors['grid'])
                self.screen.blit(coord_text, (x + 5, y + 5))
    
    def _draw_pieces(self):
        """Draw all pieces on the board"""
        board_x = self.margin
        board_y = self.margin
        
        for row in range(self.board_size):
            for col in range(self.board_size):
                pieces = self.env.board[row][col]
                if not pieces:
                    continue
                
                x = board_x + col * self.cell_size + self.cell_size // 2
                y = board_y + row * self.cell_size + self.cell_size // 2
                
                # Draw piece stack
                self._draw_piece_stack(x, y, pieces)
    
    def _draw_piece_stack(self, x: int, y: int, pieces: list):
        """Draw a stack of pieces at position"""
        player = pieces[0].player
        total_tier = sum(p.tier for p in pieces)
        stack_height = len(pieces)
        
        # Choose color
        if player == Player.RED:
            color = self.colors['red']
            light_color = self.colors['red_light']
        else:
            color = self.colors['blue']
            light_color = self.colors['blue_light']
        
        # Draw circle (piece)
        radius = min(40, self.cell_size // 3)
        
        # Draw shadow for stacked pieces
        if stack_height > 1:
            offset = 5
            for i in range(stack_height - 1):
                shadow_x = x + offset * (i + 1)
                shadow_y = y + offset * (i + 1)
                pygame.draw.circle(self.screen, (200, 200, 200), 
                                 (shadow_x, shadow_y), radius)
        
        # Draw main piece
        pygame.draw.circle(self.screen, color, (x, y), radius)
        pygame.draw.circle(self.screen, light_color, (x, y), radius, 3)
        
        # Draw tier number
        tier_text = self.font_large.render(str(total_tier), True, (255, 255, 255))
        text_rect = tier_text.get_rect(center=(x, y))
        self.screen.blit(tier_text, text_rect)
        
        # Draw stack count if > 1
        if stack_height > 1:
            stack_text = self.font_small.render(f"×{stack_height}", True, (50, 50, 50))
            self.screen.blit(stack_text, (x + radius - 15, y + radius - 10))
    
    def _draw_info_panel(self, last_action: Optional[Action] = None):
        """Draw information panel with scores and status"""
        panel_y = self.margin + self.board_width + 10  # Reduced from 20
        center_x = self.window_width // 2
        
        # Draw current player indicator
        current_player_text = f"Current Player: {self.env.current_player.name}"
        player_color = self.colors['red'] if self.env.current_player == Player.RED else self.colors['blue']
        text = self.font_medium.render(current_player_text, True, player_color)
        text_rect = text.get_rect(center=(center_x, panel_y))
        self.screen.blit(text, text_rect)
        
        # Draw scores
        score_y = panel_y + 35  # Reduced from 50
        red_score = f"RED: {self.env.scores[Player.RED]}/{self.env.win_score}"
        blue_score = f"BLUE: {self.env.scores[Player.BLUE]}/{self.env.win_score}"
        
        red_text = self.font_medium.render(red_score, True, self.colors['red'])
        blue_text = self.font_medium.render(blue_score, True, self.colors['blue'])
        
        red_rect = red_text.get_rect(center=(center_x - 150, score_y))
        blue_rect = blue_text.get_rect(center=(center_x + 150, score_y))
        
        self.screen.blit(red_text, red_rect)
        self.screen.blit(blue_text, blue_rect)
        
        # Draw underworld counts
        underworld_y = score_y + 35  # Reduced from 50
        
        for i, player in enumerate([Player.RED, Player.BLUE]):
            x_offset = -200 if player == Player.RED else 200
            color = self.colors['red'] if player == Player.RED else self.colors['blue']
            
            name = "RED" if player == Player.RED else "BLUE"
            u = self.env.underworld[player]
            underworld_text = f"{name} Underworld: T1={u[1]}, T2={u[2]}, T3={u[3]}"
            
            text = self.font_small.render(underworld_text, True, color)
            text_rect = text.get_rect(center=(center_x + x_offset, underworld_y))
            self.screen.blit(text, text_rect)
        
        # Draw last action
        if last_action:
            action_y = underworld_y + 30  # Reduced from 40
            action_text = f"Last: {last_action}"
            text = self.font_small.render(action_text, True, self.colors['text'])
            text_rect = text.get_rect(center=(center_x, action_y))
            self.screen.blit(text, text_rect)
    
    def _animate_action(self, action: Action):
        """Animate an action"""
        if action.action_type == ActionType.REVIVE:
            self._animate_revive(action)
        elif action.action_type == ActionType.MOVE:
            self._animate_move(action)
        elif action.action_type == ActionType.JUMP:
            self._animate_jump(action)
    
    def _animate_revive(self, action: Action):
        """Animate revive action"""
        to_row, to_col = action.to_pos
        
        # Flash the target cell
        for _ in range(3):
            self.render(action, highlight_cells=[action.to_pos])
            time.sleep(0.1)
            self.render(action)
            time.sleep(0.1)
    
    def _animate_move(self, action: Action):
        """Animate move action"""
        from_row, from_col = action.from_pos
        to_row, to_col = action.to_pos
        
        # Highlight from and to cells
        self.render(action, highlight_cells=[action.from_pos, action.to_pos])
        time.sleep(0.3)
    
    def _animate_jump(self, action: Action):
        """Animate jump action with path visualization"""
        if not action.jump_sequence:
            return
        
        # Show each step of the jump
        for i, (land_pos, jumped_pieces) in enumerate(action.jump_sequence):
            # Highlight jumped pieces and landing position
            highlight = jumped_pieces + [land_pos] if land_pos != (-1, -1) else jumped_pieces
            self.render(action, highlight_cells=highlight)
            time.sleep(0.4)
    
    def wait_for_key(self):
        """Wait for user to press a key (deprecated, use wait_for_continue_button)"""
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                if event.type == pygame.KEYDOWN:
                    waiting = False
            self.clock.tick(30)
        return True
    
    def wait_for_continue_button(self) -> bool:
        """Wait for user to click continue button
        
        Returns:
            True if continue clicked, False if window closed
        """
        waiting = True
        while waiting:
            mouse_pos = pygame.mouse.get_pos()
            
            # Redraw with continue button
            button_rect = self._draw_continue_button(mouse_pos)
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if button_rect.collidepoint(mouse_pos):
                        waiting = False
            
            self.clock.tick(30)
        return True


def demo_gui():
    """Demo of GUI wrapper usage"""
    from simple_agent import SimpleGreedyAgent
    
    # Create environment
    env = ZombieEnv()
    
    # Wrap with GUI
    env_gui = ZombieEnvGui(env)
    
    # Create agents
    agent_red = SimpleGreedyAgent(Player.RED, verbose=True)
    agent_blue = SimpleGreedyAgent(Player.BLUE, verbose=True)
    agents = {Player.RED: agent_red, Player.BLUE: agent_blue}
    
    # Initial render
    env_gui.render()
    print("Click Continue button to start...")
    if not env_gui.wait_for_continue_button():
        return
    
    # Game loop
    turn = 0
    last_action = None
    
    while turn < 100:
        # Get action from agent
        agent = agents[env.current_player]
        action = agent.get_action(env)
        
        if action is None:
            print(f"{env.current_player.name} has no legal actions!")
            break
        
        print(f"\nTurn {turn + 1} - {env.current_player.name}")
        print(f"Action: {action}")
        
        # Execute with animation
        state, reward, done, info = env_gui.step(action, animate=True)
        
        # Render
        env_gui.render(last_action=action)
        
        last_action = action
        turn += 1
        
        # Check if game over
        if done:
            winner = env_gui.current_player
            print(f"\n{winner.name} WINS with {env.scores[winner]} points!")
            
            # Show winner message on screen
            font = env_gui.font_large
            text = font.render(f"{winner.name} WINS!", True, 
                             env_gui.colors['red'] if winner == Player.RED else env_gui.colors['blue'])
            text_rect = text.get_rect(center=(env_gui.window_width // 2, 50))
            env_gui.screen.blit(text, text_rect)
            pygame.display.flip()
            
            print("Click Continue button to close...")
            env_gui.wait_for_continue_button()
            break
        
        # Wait for continue button before next turn
        print("Click Continue button to continue...")
        if not env_gui.wait_for_continue_button():
            break
    
    env_gui.close()


if __name__ == "__main__":
    demo_gui()