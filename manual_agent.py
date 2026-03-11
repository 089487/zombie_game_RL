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
        Display actions in multi-level menu and let player select via mouse clicks
        
        Level 1: Choose action type (JUMP/REVIVE/MOVE)
        Level 2: For JUMP/MOVE - choose piece to move (from position)
                 For REVIVE - choose position to revive to (to position)
        Level 3: For JUMP/MOVE - choose destination (to position)
                 For REVIVE - choose tier to revive (T1/T2/T3)
        
        Returns:
            Selected action or None if cancelled
        """
        # Group actions by type
        revive_actions = [a for a in legal_actions if a.action_type == ActionType.REVIVE]
        move_actions = [a for a in legal_actions if a.action_type == ActionType.MOVE]
        jump_actions = [a for a in legal_actions if a.action_type == ActionType.JUMP]
        
        action_groups = {
            'JUMP': jump_actions,
            'REVIVE': revive_actions,
            'MOVE': move_actions
        }
        
        # Menu state
        selected_action = None
        current_menu_level = 1  # 1 = type, 2 = from/to position, 3 = destination/tier
        selected_type = None
        selected_from_pos = None  # For MOVE/JUMP
        selected_to_pos = None  # For REVIVE
        scroll_offset = 0
        max_visible = 15
        prev_hovered = None
        need_redraw = True
        
        while selected_action is None:
            mouse_pos = pygame.mouse.get_pos()
            
            # Redraw board if needed
            if need_redraw:
                env_gui.render()
                need_redraw = False
            
            # Draw appropriate menu level
            if current_menu_level == 1:
                # Level 1: Type selection menu
                type_buttons, hovered = self._draw_type_menu(env_gui, action_groups, mouse_pos)
                
                # Handle type selection
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return None
                    
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        for rect, action_type in type_buttons:
                            if rect.collidepoint(mouse_pos):
                                if len(action_groups[action_type]) > 0:
                                    selected_type = action_type
                                    current_menu_level = 2
                                    scroll_offset = 0
                                    need_redraw = True
                                    print(f"Selected type: {action_type}")
                                break
            
            elif current_menu_level == 2:
                # Level 2: Choose position (from_pos for MOVE/JUMP, to_pos for REVIVE)
                if selected_type == 'REVIVE':
                    # REVIVE: show to position selection
                    # Get unique positions for max calculation
                    to_positions_temp = {}
                    for action in action_groups[selected_type]:
                        to_pos = action.to_pos
                        if to_pos not in to_positions_temp:
                            to_positions_temp[to_pos] = []
                        to_positions_temp[to_pos].append(action)
                    total_positions = len(to_positions_temp)
                    
                    to_buttons, hovered = self._draw_to_position_menu(
                        env_gui,
                        action_groups[selected_type],
                        scroll_offset,
                        max_visible,
                        mouse_pos
                    )
                    
                    # Handle to position selection
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            return None
                        
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if self._check_back_button(env_gui, mouse_pos):
                                current_menu_level = 1
                                selected_type = None
                                scroll_offset = 0
                                need_redraw = True
                                print("Back to type selection")
                            else:
                                for rect, to_pos in to_buttons:
                                    if rect.collidepoint(mouse_pos):
                                        selected_to_pos = to_pos
                                        current_menu_level = 3
                                        scroll_offset = 0
                                        need_redraw = True
                                        print(f"Selected revive position: {to_pos}")
                                        break
                        
                        elif event.type == pygame.MOUSEWHEEL:
                            scroll_offset -= event.y
                            scroll_offset = max(0, min(scroll_offset, 
                                                     max(0, total_positions - max_visible)))
                            need_redraw = True
                else:
                    # MOVE/JUMP: show from position selection
                    # Get unique positions for max calculation
                    from_positions_temp = {}
                    for action in action_groups[selected_type]:
                        from_pos = action.from_pos
                        if from_pos not in from_positions_temp:
                            from_positions_temp[from_pos] = []
                        from_positions_temp[from_pos].append(action)
                    total_positions = len(from_positions_temp)
                    
                    from_buttons, hovered = self._draw_from_position_menu(
                        env_gui,
                        selected_type,
                        action_groups[selected_type],
                        scroll_offset,
                        max_visible,
                        mouse_pos
                    )
                    
                    # Handle from position selection
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            return None
                        
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if self._check_back_button(env_gui, mouse_pos):
                                current_menu_level = 1
                                selected_type = None
                                scroll_offset = 0
                                need_redraw = True
                                print("Back to type selection")
                            else:
                                for rect, from_pos in from_buttons:
                                    if rect.collidepoint(mouse_pos):
                                        selected_from_pos = from_pos
                                        current_menu_level = 3
                                        scroll_offset = 0
                                        need_redraw = True
                                        print(f"Selected piece at: {from_pos}")
                                        break
                        
                        elif event.type == pygame.MOUSEWHEEL:
                            scroll_offset -= event.y
                            scroll_offset = max(0, min(scroll_offset, 
                                                     max(0, total_positions - max_visible)))
                            need_redraw = True
            
            else:  # current_menu_level == 3
                # Level 3: Show final selection
                if selected_type == 'REVIVE':
                    # REVIVE: show tier options for selected position
                    filtered_actions = [a for a in action_groups[selected_type] 
                                       if a.to_pos == selected_to_pos]
                    
                    tier_buttons, hovered = self._draw_tier_menu(
                        env_gui,
                        filtered_actions,
                        selected_to_pos,
                        scroll_offset,
                        max_visible,
                        mouse_pos
                    )
                    
                    # Handle tier selection
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            return None
                        
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if self._check_back_button(env_gui, mouse_pos):
                                current_menu_level = 2
                                selected_to_pos = None
                                scroll_offset = 0
                                need_redraw = True
                                print("Back to position selection")
                            else:
                                for rect, action in tier_buttons:
                                    if rect.collidepoint(mouse_pos):
                                        selected_action = action
                                        print(f"Selected: {action}")
                                        self._highlight_action(env_gui, action)
                                        pygame.time.wait(500)
                                        break
                        
                        elif event.type == pygame.MOUSEWHEEL:
                            scroll_offset -= event.y
                            scroll_offset = max(0, min(scroll_offset, 
                                                     max(0, len(filtered_actions) - max_visible)))
                            need_redraw = True
                else:
                    # MOVE/JUMP: show destination options for selected piece
                    filtered_actions = [a for a in action_groups[selected_type] 
                                       if a.from_pos == selected_from_pos]
                    
                    action_buttons, hovered = self._draw_action_menu(
                        env_gui,
                        selected_type,
                        filtered_actions,
                        selected_from_pos,
                        scroll_offset,
                        max_visible,
                        mouse_pos
                    )
                    
                    # Handle destination selection
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            return None
                        
                        elif event.type == pygame.MOUSEBUTTONDOWN:
                            if self._check_back_button(env_gui, mouse_pos):
                                current_menu_level = 2
                                selected_from_pos = None
                                scroll_offset = 0
                                need_redraw = True
                                print("Back to from position selection")
                            else:
                                for rect, action in action_buttons:
                                    if rect.collidepoint(mouse_pos):
                                        selected_action = action
                                        print(f"Selected: {action}")
                                        self._highlight_action(env_gui, action)
                                        pygame.time.wait(500)
                                        break
                        
                        elif event.type == pygame.MOUSEWHEEL:
                            scroll_offset -= event.y
                            scroll_offset = max(0, min(scroll_offset, 
                                                     max(0, len(filtered_actions) - max_visible)))
                            need_redraw = True
            
            # Check if hover changed
            if prev_hovered != hovered:
                need_redraw = True
                prev_hovered = hovered
            
            pygame.display.flip()
            env_gui.clock.tick(30)
        
        return selected_action

    def _draw_type_menu(self, env_gui: ZombieEnvGui, 
                       action_groups: dict,
                       mouse_pos: Tuple[int, int]) -> Tuple[List[Tuple[pygame.Rect, str]], None]:
        """
        Draw Level 1 menu: action type selection
        
        Returns:
            List of (rect, type_name) tuples
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
            f"{self.player.name}'s Turn", 
            True, 
            env_gui.colors['red'] if self.player == Player.RED else env_gui.colors['blue']
        )
        env_gui.screen.blit(title_text, (panel_x + 10, panel_y + 10))
        
        # Subtitle
        subtitle_text = env_gui.font_small.render(
            "Choose Action Type:", 
            True, 
            (50, 50, 50)
        )
        env_gui.screen.blit(subtitle_text, (panel_x + 10, panel_y + 50))
        
        # Type buttons
        type_buttons = []
        y_offset = panel_y + 90
        button_height = 60  # Reduced from 80 (75%)
        button_spacing = 20
        
        type_configs = [
            ('JUMP', env_gui.colors['red'], '⚔'),
            ('REVIVE', env_gui.colors['blue'], '♻'),
            ('MOVE', (100, 100, 100), '→')
        ]
        
        for type_name, color, icon in type_configs:
            actions = action_groups[type_name]
            count = len(actions)
            
            # Button rectangle
            button_rect = pygame.Rect(
                panel_x + 20,
                y_offset,
                panel_width - 40,
                button_height
            )
            
            # Highlight on hover (only if has actions)
            if button_rect.collidepoint(mouse_pos) and count > 0:
                pygame.draw.rect(env_gui.screen, (255, 255, 200), button_rect, border_radius=10)
            elif count > 0:
                pygame.draw.rect(env_gui.screen, (255, 255, 255), button_rect, border_radius=10)
            else:
                # Disabled appearance
                pygame.draw.rect(env_gui.screen, (220, 220, 220), button_rect, border_radius=10)
            
            # Border (thicker if has actions)
            border_width = 3 if count > 0 else 1
            border_color = color if count > 0 else (180, 180, 180)
            pygame.draw.rect(env_gui.screen, border_color, button_rect, border_width, border_radius=10)
            
            # Type name
            name_text = env_gui.font_large.render(f"{icon} {type_name}", True, color if count > 0 else (180, 180, 180))
            name_rect = name_text.get_rect(center=(button_rect.centerx, button_rect.centery - 15))
            env_gui.screen.blit(name_text, name_rect)
            
            # Count
            count_text = env_gui.font_medium.render(
                f"{count} action{'s' if count != 1 else ''}", 
                True, 
                (100, 100, 100)
            )
            count_rect = count_text.get_rect(center=(button_rect.centerx, button_rect.centery + 20))
            env_gui.screen.blit(count_text, count_rect)
            
            if count > 0:
                type_buttons.append((button_rect, type_name))
            
            y_offset += button_height + button_spacing
        
        return type_buttons, None
    
    def _draw_from_position_menu(self, env_gui: ZombieEnvGui,
                                action_type: str,
                                actions: List[Action],
                                scroll_offset: int,
                                max_visible: int,
                                mouse_pos: Tuple[int, int]) -> Tuple[List[Tuple[pygame.Rect, Tuple[int, int]]], Optional[Tuple[int, int]]]:
        """
        Draw Level 2 menu for MOVE/JUMP: select which piece to move
        
        Returns:
            Tuple of (list of (rect, from_pos) tuples, hovered from_pos)
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
        
        # Back button
        back_button_rect = self._draw_back_button(env_gui, panel_x, panel_y, mouse_pos)
        
        # Title
        type_colors = {
            'JUMP': env_gui.colors['red'],
            'MOVE': (100, 100, 100)
        }
        title_text = env_gui.font_medium.render(
            f"Select Piece to {action_type}", 
            True, 
            type_colors.get(action_type, (50, 50, 50))
        )
        env_gui.screen.blit(title_text, (panel_x + 60, panel_y + 15))
        
        # Get unique from positions
        from_positions = {}
        for action in actions:
            from_pos = action.from_pos
            if from_pos not in from_positions:
                from_positions[from_pos] = []
            from_positions[from_pos].append(action)
        
        # Sort by position
        sorted_positions = sorted(from_positions.keys())
        
        # From position buttons
        from_buttons = []
        hovered_from_pos = None
        y_offset = panel_y + 60
        button_height = 52  # Reduced from 70 (75%)
        button_spacing = 10
        
        # Draw visible positions (with scrolling)
        visible_positions = sorted_positions[scroll_offset:scroll_offset + max_visible]
        
        for from_pos in visible_positions:
            row, col = from_pos
            action_count = len(from_positions[from_pos])
            
            # Get piece info at this position
            pieces = env_gui.board[row][col]
            if not pieces:
                continue
            
            total_tier = sum(p.tier for p in pieces)
            piece_player = pieces[0].player
            
            # Button rectangle
            button_rect = pygame.Rect(
                panel_x + 20,
                y_offset,
                panel_width - 40,
                button_height
            )
            
            # Highlight on hover
            if button_rect.collidepoint(mouse_pos):
                pygame.draw.rect(env_gui.screen, (255, 255, 200), button_rect, border_radius=10)
                hovered_from_pos = from_pos
                # Preview this piece on board
                self._preview_from_position(env_gui, from_pos)
            else:
                pygame.draw.rect(env_gui.screen, (255, 255, 255), button_rect, border_radius=10)
            
            # Border
            piece_color = env_gui.colors['red'] if piece_player == Player.RED else env_gui.colors['blue']
            pygame.draw.rect(env_gui.screen, piece_color, button_rect, 3, border_radius=10)
            
            # Position text
            pos_text = env_gui.font_large.render(f"({row}, {col})", True, piece_color)
            pos_rect = pos_text.get_rect(center=(button_rect.centerx, button_rect.centery - 15))
            env_gui.screen.blit(pos_text, pos_rect)
            
            # Piece info
            info_text = env_gui.font_small.render(
                f"Tier {total_tier} - {action_count} option{'s' if action_count > 1 else ''}", 
                True, 
                (100, 100, 100)
            )
            info_rect = info_text.get_rect(center=(button_rect.centerx, button_rect.centery + 20))
            env_gui.screen.blit(info_text, info_rect)
            
            from_buttons.append((button_rect, from_pos))
            y_offset += button_height + button_spacing
        
        # Scroll indicator
        if len(sorted_positions) > max_visible:
            scroll_text = f"Showing {scroll_offset + 1}-{min(scroll_offset + max_visible, len(sorted_positions))} of {len(sorted_positions)}"
            scroll_surface = env_gui.font_small.render(scroll_text, True, (100, 100, 100))
            env_gui.screen.blit(scroll_surface, (panel_x + 10, panel_y + panel_height - 30))
        
        return from_buttons, hovered_from_pos
    
    def _preview_from_position(self, env_gui: ZombieEnvGui, from_pos: Tuple[int, int]):
        """Highlight the from position on board"""
        board_x = env_gui.margin
        board_y = env_gui.margin
        
        row, col = from_pos
        x = board_x + col * env_gui.cell_size
        y = board_y + row * env_gui.cell_size
        
        # Draw semi-transparent highlight
        highlight_surface = pygame.Surface((env_gui.cell_size, env_gui.cell_size))
        highlight_surface.set_alpha(100)
        highlight_surface.fill((100, 200, 255))
        env_gui.screen.blit(highlight_surface, (x, y))
    
    def _draw_to_position_menu(self, env_gui: ZombieEnvGui,
                              actions: List[Action],
                              scroll_offset: int,
                              max_visible: int,
                              mouse_pos: Tuple[int, int]) -> Tuple[List[Tuple[pygame.Rect, Tuple[int, int]]], Optional[Tuple[int, int]]]:
        """
        Draw Level 2 menu for REVIVE: select position to revive to
        
        Returns:
            Tuple of (list of (rect, to_pos) tuples, hovered to_pos)
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
        
        # Back button
        back_button_rect = self._draw_back_button(env_gui, panel_x, panel_y, mouse_pos)
        
        # Title
        title_text = env_gui.font_medium.render(
            f"Select Revive Position", 
            True, 
            env_gui.colors['blue']
        )
        env_gui.screen.blit(title_text, (panel_x + 60, panel_y + 15))
        
        # Get unique to positions
        to_positions = {}
        for action in actions:
            to_pos = action.to_pos
            if to_pos not in to_positions:
                to_positions[to_pos] = []
            to_positions[to_pos].append(action)
        
        # Sort by position
        sorted_positions = sorted(to_positions.keys())
        
        # To position buttons
        to_buttons = []
        hovered_to_pos = None
        y_offset = panel_y + 60
        button_height = 52  # Reduced from 70 (75%)
        button_spacing = 10
        
        # Draw visible positions (with scrolling)
        visible_positions = sorted_positions[scroll_offset:scroll_offset + max_visible]
        
        for to_pos in visible_positions:
            row, col = to_pos
            action_count = len(to_positions[to_pos])
            
            # Get available tiers at this position
            tiers = sorted(set(a.tier for a in to_positions[to_pos]))
            tier_str = ", ".join(f"T{t}" for t in tiers)
            
            # Button rectangle
            button_rect = pygame.Rect(
                panel_x + 20,
                y_offset,
                panel_width - 40,
                button_height
            )
            
            # Highlight on hover
            if button_rect.collidepoint(mouse_pos):
                pygame.draw.rect(env_gui.screen, (255, 255, 200), button_rect, border_radius=10)
                hovered_to_pos = to_pos
                # Preview this position on board
                self._preview_to_position(env_gui, to_pos)
            else:
                pygame.draw.rect(env_gui.screen, (255, 255, 255), button_rect, border_radius=10)
            
            # Border
            pygame.draw.rect(env_gui.screen, env_gui.colors['blue'], button_rect, 3, border_radius=10)
            
            # Position text
            pos_text = env_gui.font_large.render(f"({row}, {col})", True, env_gui.colors['blue'])
            pos_rect = pos_text.get_rect(center=(button_rect.centerx, button_rect.centery - 15))
            env_gui.screen.blit(pos_text, pos_rect)
            
            # Available tiers info
            info_text = env_gui.font_small.render(
                f"{tier_str} available", 
                True, 
                (100, 100, 100)
            )
            info_rect = info_text.get_rect(center=(button_rect.centerx, button_rect.centery + 20))
            env_gui.screen.blit(info_text, info_rect)
            
            to_buttons.append((button_rect, to_pos))
            y_offset += button_height + button_spacing
        
        # Scroll indicator
        if len(sorted_positions) > max_visible:
            scroll_text = f"Showing {scroll_offset + 1}-{min(scroll_offset + max_visible, len(sorted_positions))} of {len(sorted_positions)}"
            scroll_surface = env_gui.font_small.render(scroll_text, True, (100, 100, 100))
            env_gui.screen.blit(scroll_surface, (panel_x + 10, panel_y + panel_height - 30))
        
        return to_buttons, hovered_to_pos
    
    def _preview_to_position(self, env_gui: ZombieEnvGui, to_pos: Tuple[int, int]):
        """Highlight the to position on board"""
        board_x = env_gui.margin
        board_y = env_gui.margin
        
        row, col = to_pos
        x = board_x + col * env_gui.cell_size
        y = board_y + row * env_gui.cell_size
        
        # Draw semi-transparent highlight (green for revive target)
        highlight_surface = pygame.Surface((env_gui.cell_size, env_gui.cell_size))
        highlight_surface.set_alpha(100)
        highlight_surface.fill((100, 255, 100))
        env_gui.screen.blit(highlight_surface, (x, y))
    
    def _draw_tier_menu(self, env_gui: ZombieEnvGui,
                       actions: List[Action],
                       to_pos: Tuple[int, int],
                       scroll_offset: int,
                       max_visible: int,
                       mouse_pos: Tuple[int, int]) -> Tuple[List[Tuple[pygame.Rect, Action]], Optional[Action]]:
        """
        Draw Level 3 menu for REVIVE: select tier to revive
        
        Returns:
            Tuple of (list of (rect, action) pairs, hovered action)
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
        
        # Back button
        back_button_rect = self._draw_back_button(env_gui, panel_x, panel_y, mouse_pos)
        
        # Title
        title_text = env_gui.font_medium.render(
            f"Revive to {to_pos}", 
            True, 
            env_gui.colors['blue']
        )
        env_gui.screen.blit(title_text, (panel_x + 60, panel_y + 15))
        
        # Tier selection buttons
        button_rects = []
        y_offset = panel_y + 60
        button_height = 52  # Reduced from 70 (75%)
        button_spacing = 10
        hovered_action = None
        
        # Sort actions by tier (descending)
        sorted_actions = sorted(actions, key=lambda a: a.tier, reverse=True)
        
        # Draw visible actions (with scrolling if needed)
        visible_actions = sorted_actions[scroll_offset:scroll_offset + max_visible]
        
        for action in visible_actions:
            # Button rectangle
            button_rect = pygame.Rect(
                panel_x + 20,
                y_offset,
                panel_width - 40,
                button_height
            )
            
            # Highlight on hover
            if button_rect.collidepoint(mouse_pos):
                pygame.draw.rect(env_gui.screen, (255, 255, 200), button_rect, border_radius=10)
                hovered_action = action
                # Show action preview on board
                self._preview_action(env_gui, action)
            else:
                pygame.draw.rect(env_gui.screen, (255, 255, 255), button_rect, border_radius=10)
            
            # Border
            pygame.draw.rect(env_gui.screen, env_gui.colors['blue'], button_rect, 3, border_radius=10)
            
            # Tier text (large)
            tier_text = env_gui.font_large.render(f"Tier {action.tier}", True, env_gui.colors['blue'])
            tier_rect = tier_text.get_rect(center=(button_rect.centerx, button_rect.centery))
            env_gui.screen.blit(tier_text, tier_rect)
            
            button_rects.append((button_rect, action))
            y_offset += button_height + button_spacing
        
        # Scroll indicator
        if len(sorted_actions) > max_visible:
            scroll_text = f"Showing {scroll_offset + 1}-{min(scroll_offset + max_visible, len(sorted_actions))} of {len(sorted_actions)}"
            scroll_surface = env_gui.font_small.render(scroll_text, True, (100, 100, 100))
            env_gui.screen.blit(scroll_surface, (panel_x + 10, panel_y + panel_height - 30))
        
        return button_rects, hovered_action
    
    def _draw_action_menu(self, env_gui: ZombieEnvGui,
                         action_type: str,
                         actions: List[Action],
                         from_pos: Optional[Tuple[int, int]],
                         scroll_offset: int,
                         max_visible: int,
                         mouse_pos: Tuple[int, int]) -> Tuple[List[Tuple[pygame.Rect, Action]], Optional[Action]]:
        """
        Draw Level 3 menu for MOVE/JUMP: specific destination selection
        
        For MOVE/JUMP: Show destination options for selected piece
        
        Returns:
            Tuple of (list of (rect, action) pairs, hovered action)
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
        
        # Back button
        back_button_rect = self._draw_back_button(env_gui, panel_x, panel_y, mouse_pos)
        
        # Title with type name
        type_colors = {
            'JUMP': env_gui.colors['red'],
            'REVIVE': env_gui.colors['blue'],
            'MOVE': (100, 100, 100)
        }
        
        if from_pos:
            title_text = env_gui.font_medium.render(
                f"{action_type} from {from_pos}", 
                True, 
                type_colors.get(action_type, (50, 50, 50))
            )
        else:
            title_text = env_gui.font_medium.render(
                f"{action_type} Actions", 
                True, 
                type_colors.get(action_type, (50, 50, 50))
            )
        env_gui.screen.blit(title_text, (panel_x + 60, panel_y + 15))
        
        # Action list
        button_rects = []
        y_offset = panel_y + 60
        button_height = 26  # Reduced from 35 (75%)
        button_spacing = 5
        hovered_action = None
        
        # Draw visible actions (with scrolling)
        visible_actions = actions[scroll_offset:scroll_offset + max_visible]
        
        for action in visible_actions:
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
            pygame.draw.rect(env_gui.screen, type_colors.get(action_type, (100, 100, 100)), button_rect, 2)
            
            # Action text - simplified for MOVE/JUMP when from_pos is known
            if from_pos and action_type in ['MOVE', 'JUMP']:
                action_text = self._format_destination_text(action)
            else:
                action_text = self._format_action_text(action)
            
            text_surface = env_gui.font_small.render(action_text, True, type_colors.get(action_type, (50, 50, 50)))
            env_gui.screen.blit(text_surface, (button_rect.x + 5, button_rect.y + 8))
            
            button_rects.append((button_rect, action))
            y_offset += button_height + button_spacing
        
        # Scroll indicator
        if len(actions) > max_visible:
            scroll_text = f"Showing {scroll_offset + 1}-{min(scroll_offset + max_visible, len(actions))} of {len(actions)}"
            scroll_surface = env_gui.font_small.render(scroll_text, True, (100, 100, 100))
            env_gui.screen.blit(scroll_surface, (panel_x + 10, panel_y + panel_height - 30))
        
        return button_rects, hovered_action
    
    def _draw_back_button(self, env_gui: ZombieEnvGui, 
                         panel_x: int, panel_y: int,
                         mouse_pos: Tuple[int, int]) -> pygame.Rect:
        """Draw back button and return its rect"""
        back_rect = pygame.Rect(panel_x + 10, panel_y + 10, 30, 30)  # Reduced from 40x40 (75%)
        
        # Highlight on hover
        if back_rect.collidepoint(mouse_pos):
            pygame.draw.rect(env_gui.screen, (255, 255, 200), back_rect, border_radius=5)
        else:
            pygame.draw.rect(env_gui.screen, (255, 255, 255), back_rect, border_radius=5)
        
        # Border
        pygame.draw.rect(env_gui.screen, (100, 100, 100), back_rect, 2, border_radius=5)
        
        # Back arrow
        arrow_text = env_gui.font_large.render("<", True, (50, 50, 50))
        arrow_rect = arrow_text.get_rect(center=back_rect.center)
        env_gui.screen.blit(arrow_text, arrow_rect)
        
        return back_rect
    
    def _check_back_button(self, env_gui: ZombieEnvGui, mouse_pos: Tuple[int, int]) -> bool:
        """Check if back button was clicked"""
        panel_x = env_gui.window_width - 400
        panel_y = 50
        back_rect = pygame.Rect(panel_x + 10, panel_y + 10, 30, 30)  # Reduced from 40x40 (75%)
        return back_rect.collidepoint(mouse_pos)
    
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
    
    def _format_destination_text(self, action: Action) -> str:
        """Format destination text when from position is already known"""
        if action.action_type == ActionType.MOVE:
            return f"→ {action.to_pos}"
        elif action.action_type == ActionType.JUMP:
            steps = len(action.jump_sequence) if action.jump_sequence else 0
            score = action.expected_score
            if action.to_pos == (-1, -1):
                return f"→ Jump off board ({steps} steps, +{score})"
            else:
                return f"→ {action.to_pos} ({steps} steps, +{score})"
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
    env_gui.render()
    print("\nClick Continue button to start...")
    if not env_gui.wait_for_continue_button():
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
            
            print("\nClick Continue button to close...")
            env_gui.wait_for_continue_button()
            break
        
        # Wait for next turn (only for AI turns)
        if not isinstance(agent, ManualAgent):
            env_gui.render(last_action=action)
            print("Click Continue button to continue...")
            if not env_gui.wait_for_continue_button():
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
    env_gui.render()
    print("\nClick Continue button to start...")
    if not env_gui.wait_for_continue_button():
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
            
            print("Click Continue button to close...")
            env_gui.wait_for_continue_button()
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