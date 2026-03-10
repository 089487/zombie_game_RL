"""
Manual Agent for Zombie Game - Interactive GUI Control

允许玩家通过点击棋盘来手动选择和执行动作
"""

import pygame
from typing import Optional, List, Tuple
from Zombie_env import ZombieEnv, Action, ActionType, Player
from gui_wrapper import ZombieEnvGui


class ManualAgent:
    """Manual agent controlled by mouse clicks"""
    
    def __init__(self, player: Player):
        """
        Initialize Manual Agent
        
        Args:
            player: The player this agent controls (RED or BLUE)
        """
        self.player = player
    
    def get_action(self, env_gui: ZombieEnvGui) -> Optional[Action]:
        """
        Get action from human player via GUI interaction
        
        Args:
            env_gui: ZombieEnvGui instance (for rendering and interaction)
        
        Returns:
            Selected action or None
        """
        legal_actions = env_gui.get_legal_actions()
        
        if not legal_actions:
            return None
        
        print(f"\n{self.player.name}'s turn - Select an action:")
        print(f"Found {len(legal_actions)} legal actions")
        
        # Show action selection interface
        selected_action = self._select_action_gui(env_gui, legal_actions)
        
        return selected_action
    
    def _select_action_gui(self, env_gui: ZombieEnvGui, 
                      legal_actions: List[Action]) -> Optional[Action]:
        """
        Display actions and let player select via mouse clicks
        
        Returns:
            Selected action or None if cancelled
        """
        # Group actions by type
        revive_actions = [a for a in legal_actions if a.action_type == ActionType.REVIVE]
        move_actions = [a for a in legal_actions if a.action_type == ActionType.MOVE]
        jump_actions = [a for a in legal_actions if a.action_type == ActionType.JUMP]
        
        # Display selection UI
        selected_action = None
        action_buttons = []
        scroll_offset = 0
        max_visible = 15  # Maximum actions visible at once
        prev_hovered_action = None  # Track which action was hovered last frame
        need_redraw = True  # Flag to control when to redraw
    
        while selected_action is None:
            # Get current mouse position
            mouse_pos = pygame.mouse.get_pos()
            
            # Only redraw board if needed
            if need_redraw:
                env_gui.render()
                need_redraw = False
            
            # Always draw action list panel on top
            action_buttons, current_hovered_action = self._draw_action_list(
                env_gui, 
                revive_actions, 
                move_actions, 
                jump_actions,
                scroll_offset,
                max_visible,
                mouse_pos
            )
            
            # Check if hover changed
            if prev_hovered_action != current_hovered_action:
                need_redraw = True  # Need to redraw on next frame
                prev_hovered_action = current_hovered_action
            
            pygame.display.flip()
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Check if clicked on an action button
                    for i, (rect, action) in enumerate(action_buttons):
                        if rect.collidepoint(mouse_pos):
                            selected_action = action
                            print(f"Selected: {action}")
                            # Highlight selected action
                            self._highlight_action(env_gui, action)
                            pygame.time.wait(500)  # Brief pause to show selection
                            break
                
                elif event.type == pygame.MOUSEWHEEL:
                    # Scroll through actions
                    scroll_offset -= event.y
                    scroll_offset = max(0, min(scroll_offset, 
                                         max(0, len(legal_actions) - max_visible)))
                    need_redraw = True  # Force redraw on scroll
            
            env_gui.clock.tick(30)
        
        return selected_action

    def _draw_action_list(self, env_gui: ZombieEnvGui,
                     revive_actions: List[Action],
                     move_actions: List[Action],
                     jump_actions: List[Action],
                     scroll_offset: int,
                     max_visible: int,
                     mouse_pos: Tuple[int, int]) -> Tuple[List[Tuple[pygame.Rect, Action]], Optional[Action]]:
        """
        Draw scrollable action list on the side panel
        
        Returns:
            Tuple of (list of (rect, action) pairs, currently hovered action)
        """
        # Panel dimensions
        panel_x = env_gui.window_width - 400
        panel_y = 50
        panel_width = 380
        panel_height = env_gui.window_height - 100
        
        # Draw panel background
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.fill((250, 250, 250))
        panel_surface.set_alpha(240)
        env_gui.screen.blit(panel_surface, (panel_x, panel_y))
        
        # Draw border
        pygame.draw.rect(env_gui.screen, (100, 100, 100), 
                    (panel_x, panel_y, panel_width, panel_height), 3)
        
        # Title
        title_text = env_gui.font_medium.render(
            f"{self.player.name}'s Actions", 
            True, 
            env_gui.colors['red'] if self.player == Player.RED else env_gui.colors['blue']
        )
        env_gui.screen.blit(title_text, (panel_x + 10, panel_y + 10))
        
        # Action list
        button_rects = []
        y_offset = panel_y + 60
        button_height = 35
        button_spacing = 5
        hovered_action = None
        
        all_actions = []
        
        # Add section headers and actions
        if jump_actions:
            all_actions.append(('header', 'JUMP Actions:', None))
            for action in jump_actions:
                all_actions.append(('action', action, env_gui.colors['red']))
        
        if revive_actions:
            all_actions.append(('header', 'REVIVE Actions:', None))
            for action in revive_actions:
                all_actions.append(('action', action, env_gui.colors['blue']))
        
        if move_actions:
            all_actions.append(('header', 'MOVE Actions:', None))
            for action in move_actions:
                all_actions.append(('action', action, (100, 100, 100)))
        
        # Draw visible actions (with scrolling)
        visible_actions = all_actions[scroll_offset:scroll_offset + max_visible]
        
        for item in visible_actions:
            if item[0] == 'header':
                # Draw section header
                header_text = env_gui.font_small.render(item[1], True, (50, 50, 50))
                env_gui.screen.blit(header_text, (panel_x + 15, y_offset))
                y_offset += 25
            else:
                # Draw action button
                action = item[1]
                color = item[2]
                
                # Button rectangle
                button_rect = pygame.Rect(
                    panel_x + 10, 
                    y_offset, 
                    panel_width - 20, 
                    button_height
                )
                
                # Highlight on hover
                if button_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(env_gui.screen, (255, 255, 200), button_rect)
                    hovered_action = action
                    # Show action preview on board
                    self._preview_action(env_gui, action)
                else:
                    pygame.draw.rect(env_gui.screen, (255, 255, 255), button_rect)
                
                # Border
                pygame.draw.rect(env_gui.screen, color, button_rect, 2)
                
                # Action text
                action_text = self._format_action_text(action)
                text_surface = env_gui.font_small.render(action_text, True, color)
                env_gui.screen.blit(text_surface, (button_rect.x + 5, button_rect.y + 8))
                
                button_rects.append((button_rect, action))
                y_offset += button_height + button_spacing
    
        # Scroll indicator
        if len(all_actions) > max_visible:
            scroll_text = f"Scroll: {scroll_offset + 1}-{min(scroll_offset + max_visible, len(all_actions))}/{len(all_actions)}"
            scroll_surface = env_gui.font_small.render(scroll_text, True, (100, 100, 100))
            env_gui.screen.blit(scroll_surface, (panel_x + 10, panel_y + panel_height - 30))
        
        return button_rects, hovered_action
    
    def _format_action_text(self, action: Action) -> str:
        """Format action as readable text"""
        if action.action_type == ActionType.REVIVE:
            return f"Revive T{action.tier} → {action.to_pos}"
        elif action.action_type == ActionType.MOVE:
            return f"Move {action.from_pos} → {action.to_pos}"
        elif action.action_type == ActionType.JUMP:
            steps = len(action.jump_sequence) if action.jump_sequence else 0
            score = action.expected_score
            return f"Jump {action.from_pos} → {action.to_pos} ({steps} steps, +{score})"
        return str(action)
    
    def _preview_action(self, env_gui: ZombieEnvGui, action: Action):
        """Show action preview on board when hovering"""
        highlight_cells = []
        
        if action.action_type == ActionType.REVIVE:
            highlight_cells = [action.to_pos]
        elif action.action_type == ActionType.MOVE:
            highlight_cells = [action.from_pos, action.to_pos]
        elif action.action_type == ActionType.JUMP:
            highlight_cells = [action.from_pos]
            if action.to_pos != (-1, -1):
                highlight_cells.append(action.to_pos)
            # Add jumped cells
            if action.jump_sequence:
                for land_pos, jumped_pos in action.jump_sequence:
                    highlight_cells.extend(jumped_pos)
        
        # Draw highlights on board
        board_x = env_gui.margin
        board_y = env_gui.margin
        
        for row, col in highlight_cells:
            if 0 <= row < env_gui.board_size and 0 <= col < env_gui.board_size:
                x = board_x + col * env_gui.cell_size
                y = board_y + row * env_gui.cell_size
                
                # Draw semi-transparent highlight
                highlight_surface = pygame.Surface((env_gui.cell_size, env_gui.cell_size))
                highlight_surface.set_alpha(100)
                highlight_surface.fill((255, 215, 0))
                env_gui.screen.blit(highlight_surface, (x, y))
    
    def _highlight_action(self, env_gui: ZombieEnvGui, action: Action):
        """Highlight selected action briefly"""
        if action.action_type == ActionType.JUMP:
            highlight_cells = [action.from_pos]
            if action.jump_sequence:
                for land_pos, jumped_pos in action.jump_sequence:
                    highlight_cells.extend(jumped_pos)
                    if land_pos != (-1, -1):
                        highlight_cells.append(land_pos)
        elif action.action_type == ActionType.MOVE:
            highlight_cells = [action.from_pos, action.to_pos]
        else:  # REVIVE
            highlight_cells = [action.to_pos]
        
        env_gui.render(action, highlight_cells=highlight_cells)
        pygame.display.flip()


def play_manual_game(manual_player: Player = Player.RED):
    """
    Play a game with manual control
    
    Args:
        manual_player: Which player is controlled by human (RED or BLUE)
    """
    # Import AI agent for opponent
    from simple_agent import SimpleGreedyAgent
    
    # Create environment
    env = ZombieEnv()
    env_gui = ZombieEnvGui(env, cell_size=100)  # Smaller cells to fit action panel
    
    # Adjust window size for action panel
    env_gui.window_width = env_gui.board_width + 2 * env_gui.margin + 400  # Extra space for panel
    env_gui.screen = pygame.display.set_mode((env_gui.window_width, env_gui.window_height))
    
    # Create agents
    manual_agent = ManualAgent(manual_player)
    opponent_player = Player.BLUE if manual_player == Player.RED else Player.RED
    ai_agent = SimpleGreedyAgent(opponent_player, verbose=True)
    
    agents = {
        manual_player: manual_agent,
        opponent_player: ai_agent
    }
    
    print("\n" + "="*80)
    print(f"MANUAL GAME: You are {manual_player.name}")
    print(f"Opponent: {opponent_player.name} (AI Greedy Agent)")
    print("="*80)
    
    # Initial render
    env_gui.render(show_wait_prompt=True)
    print("\nPress any key to start...")
    if not env_gui.wait_for_key():
        return
    
    # Game loop
    turn = 0
    last_action = None
    
    while turn < 100:
        current_player = env_gui.current_player
        agent = agents[current_player]
        
        print(f"\n{'='*80}")
        print(f"Turn {turn + 1} - {current_player.name}'s turn")
        print(f"Scores: RED={env_gui.scores[Player.RED]}, BLUE={env_gui.scores[Player.BLUE]}")
        print(f"{'='*80}")
        
        # Get action
        if isinstance(agent, ManualAgent):
            # Manual control
            action = agent.get_action(env_gui)
        else:
            # AI agent
            print(f"{current_player.name} (AI) is thinking...")
            env_gui.render(last_action=last_action)
            action = agent.get_action(env_gui)
            print(f"AI chose: {action}")
        
        if action is None:
            print(f"{current_player.name} has no legal actions!")
            opponent = Player.BLUE if current_player == Player.RED else Player.RED
            winner = opponent
            break
        
        # Execute action
        state, reward, done, info = env_gui.step(action, animate=True)
        last_action = action
        
        print(f"Action executed: {action}")
        print(f"Reward: {reward}")
        
        # Render result
        env_gui.render(last_action=action)
        
        turn += 1
        
        if done:
            winner = current_player
            print(f"\n{'='*80}")
            print(f"🏆 {winner.name} WINS with {env_gui.scores[winner]} points!")
            print(f"{'='*80}")
            
            # Show winner message
            font = env_gui.font_large
            win_color = env_gui.colors['red'] if winner == Player.RED else env_gui.colors['blue']
            text = font.render(f"{winner.name} WINS!", True, win_color)
            text_rect = text.get_rect(center=(env_gui.window_width // 2, 50))
            env_gui.screen.blit(text, text_rect)
            pygame.display.flip()
            
            print("\nPress any key to close...")
            env_gui.wait_for_key()
            break
        
        # Wait for next turn (only for AI turns)
        if not isinstance(agent, ManualAgent):
            env_gui.render(last_action=action, show_wait_prompt=True)
            print("Press any key to continue...")
            if not env_gui.wait_for_key():
                break
    
    env_gui.close()


def play_manual_vs_manual():
    """Play a game with two human players taking turns"""
    env = ZombieEnv()
    env_gui = ZombieEnvGui(env, cell_size=100)
    
    # Adjust window size for action panel
    env_gui.window_width = env_gui.board_width + 2 * env_gui.margin + 400
    env_gui.screen = pygame.display.set_mode((env_gui.window_width, env_gui.window_height))
    
    # Create manual agents
    agent_red = ManualAgent(Player.RED)
    agent_blue = ManualAgent(Player.BLUE)
    agents = {Player.RED: agent_red, Player.BLUE: agent_blue}
    
    print("\n" + "="*80)
    print("MANUAL GAME: Two Players")
    print("="*80)
    
    # Initial render
    env_gui.render(show_wait_prompt=True)
    print("\nPress any key to start...")
    if not env_gui.wait_for_key():
        return
    
    # Game loop
    turn = 0
    
    while turn < 100:
        current_player = env_gui.current_player
        agent = agents[current_player]
        
        print(f"\n{'='*80}")
        print(f"Turn {turn + 1} - {current_player.name}'s turn")
        print(f"{'='*80}")
        
        # Get action from current player
        action = agent.get_action(env_gui)
        
        if action is None:
            print(f"{current_player.name} has no legal actions!")
            break
        
        # Execute action
        state, reward, done, info = env_gui.step(action, animate=True)
        
        # Render
        env_gui.render(last_action=action)
        
        turn += 1
        
        if done:
            winner = current_player
            print(f"\n🏆 {winner.name} WINS with {env_gui.scores[winner]} points!")
            
            # Show winner message
            font = env_gui.font_large
            win_color = env_gui.colors['red'] if winner == Player.RED else env_gui.colors['blue']
            text = font.render(f"{winner.name} WINS!", True, win_color)
            text_rect = text.get_rect(center=(env_gui.window_width // 2, 50))
            env_gui.screen.blit(text, text_rect)
            pygame.display.flip()
            
            print("Press any key to close...")
            env_gui.wait_for_key()
            break
    
    env_gui.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "red":
            # Human plays as RED
            play_manual_game(Player.RED)
        elif sys.argv[1] == "blue":
            # Human plays as BLUE
            play_manual_game(Player.BLUE)
        elif sys.argv[1] == "vs":
            # Two human players
            play_manual_vs_manual()
        else:
            print("Unknown command")
            sys.exit(1)
    else:
        # Default: human as RED
        play_manual_game(Player.RED)
    
    print("\n" + "="*80)
    print("USAGE:")
    print("  python manual_agent.py           # Play as RED vs AI")
    print("  python manual_agent.py red       # Play as RED vs AI")
    print("  python manual_agent.py blue      # Play as BLUE vs AI")
    print("  python manual_agent.py vs        # Two human players")
    print("="*80)