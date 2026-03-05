from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import copy
import heapq

class Player(Enum):
    RED = 0
    BLUE = 1

class ActionType(Enum):
    REVIVE = 0
    MOVE = 1
    JUMP = 2

@dataclass
class Piece:
    player: Player
    tier: int
    
    def __repr__(self):
        color = "R" if self.player == Player.RED else "B"
        return f"{color}{self.tier}"

@dataclass
class Action:
    action_type: ActionType
    from_pos: Optional[Tuple[int, int]]  # None for REVIVE
    to_pos: Optional[Tuple[int, int]]    # 最终着陆位置，(-1,-1) for 跳出棋盘
    tier: Optional[int]                  # REVIVE 的 tier
    initial_direction: Optional[str]     # JUMP 的初始方向: 'up'/'down'/'left'/'right'
    jump_sequence: Optional[List[Tuple]] # JUMP 的完整路径
    expected_score: float                # 预期得分
    
    def __repr__(self):
        if self.action_type == ActionType.REVIVE:
            return f"REVIVE(tier={self.tier}, to={self.to_pos}, score={self.expected_score})"
        elif self.action_type == ActionType.MOVE:
            return f"MOVE(from={self.from_pos}, to={self.to_pos}, score={self.expected_score})"
        else:  # JUMP
            steps = len(self.jump_sequence) if self.jump_sequence else 0
            return f"JUMP(from={self.from_pos}, dir={self.initial_direction}, steps={steps}, to={self.to_pos}, score={self.expected_score})"

class ZombieEnv:
    """Zombie Board Game Environment"""
    
    def __init__(self):
        self.board_size = 5
        self.win_score = 8
        
        # Initialize board: each cell is a list of pieces (can stack)
        self.board = [[[] for _ in range(self.board_size)] for _ in range(self.board_size)]
        
        # Underworld (pieces off board)
        self.underworld = {
            Player.RED: {1: 0, 2: 2, 3: 0},  # Initially 2x tier-2 in underworld
            Player.BLUE: {1: 0, 2: 2, 3: 0}
        }
        
        # Scores
        self.scores = {Player.RED: 0, Player.BLUE: 0}
        
        # Current player
        self.current_player = Player.RED
        
        # Initialize board
        self._setup_board()
    
    def _setup_board(self):
        """Initialize the board with starting pieces"""
        # Red player (top, row 0-1)
        self.board[0][0] = [Piece(Player.RED, 2)]
        self.board[0][2] = [Piece(Player.RED, 3)]
        self.board[0][4] = [Piece(Player.RED, 2)]
        
        for col in range(5):
            self.board[1][col] = [Piece(Player.RED, 1)]
        
        # Blue player (bottom, row 3-4)
        for col in range(5):
            self.board[3][col] = [Piece(Player.BLUE, 1)]
        
        self.board[4][0] = [Piece(Player.BLUE, 2)]
        self.board[4][2] = [Piece(Player.BLUE, 3)]
        self.board[4][4] = [Piece(Player.BLUE, 2)]
    
    def reset(self):
        """Reset environment to initial state"""
        self.board = [[[] for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.underworld = {
            Player.RED: {1: 0, 2: 2, 3: 0},
            Player.BLUE: {1: 0, 2: 2, 3: 0}
        }
        self.scores = {Player.RED: 0, Player.BLUE: 0}
        self.current_player = Player.RED
        self._setup_board()
        return self.get_state()
    
    def get_state(self):
        """Get current game state (deep copy)"""
        return {
            'board': [[cell[:] for cell in row] for row in self.board],
            'underworld': {p: dict(u) for p, u in self.underworld.items()},
            'scores': dict(self.scores),
            'current_player': self.current_player
        }
    
    def _has_own_pieces(self, row: int, col: int, player: Player) -> bool:
        """Check if cell has pieces belonging to player"""
        if not (0 <= row < self.board_size and 0 <= col < self.board_size):
            return False
        return len(self.board[row][col]) > 0 and self.board[row][col][0].player == player
    
    def _is_valid_move(self, from_row: int, from_col: int, to_row: int, to_col: int, player: Player) -> bool:
        """Check if a move is valid"""
        # Check bounds
        if not (0 <= to_row < self.board_size and 0 <= to_col < self.board_size):
            return False
        
        # Must be adjacent
        if abs(from_row - to_row) + abs(from_col - to_col) != 1:
            return False
        
        # Target must be empty or have own higher tier piece for stacking
        target = self.board[to_row][to_col]
        if len(target) == 0:
            return True
        
        # Can stack on own higher tier piece
        if target[0].player == player:
            moving_tier = sum(p.tier for p in self.board[from_row][from_col])
            target_tier = sum(p.tier for p in target)
            return target_tier > moving_tier
        
        return False
    
    def _try_jump_direction(self, row: int, col: int, dr: int, dc: int, 
                           player: Player, jumping_tier: int = None) -> List[Tuple]:
        """
        Try jumping in a direction, return list of (landing_pos, jumped_pieces, can_continue)
        
        Returns:
            List of tuples: (landing_pos, jumped_pieces_list, can_continue_bool)
        """
        results = []
        if jumping_tier is None:
            jumping_tier = sum(p.tier for p in self.board[row][col])
        
        # Find all continuous pieces in this direction
        continuous_pieces = []
        curr_row, curr_col = row + dr, col + dc
        
        while (0 <= curr_row < self.board_size and 
               0 <= curr_col < self.board_size and 
               len(self.board[curr_row][curr_col]) > 0):
            continuous_pieces.append((curr_row, curr_col))
            curr_row += dr
            curr_col += dc
        
        # No pieces to jump
        if not continuous_pieces:
            return []
        
        # Try different landing options:
        # Option 1: Jump over all N pieces and land on empty cell after them
        all_jumped_tier = sum(
            sum(p.tier for p in self.board[r][c]) 
            for r, c in continuous_pieces
        )
        
        if jumping_tier >= all_jumped_tier:
            # Position after all pieces
            land_row = continuous_pieces[-1][0] + dr
            land_col = continuous_pieces[-1][1] + dc
            
            # Land on empty cell (in bounds)
            if (0 <= land_row < self.board_size and 
                0 <= land_col < self.board_size and 
                len(self.board[land_row][land_col]) == 0):
                results.append(((land_row, land_col), continuous_pieces[:], True))
            
            # Jump off board (out of bounds)
            if not (0 <= land_row < self.board_size and 0 <= land_col < self.board_size):
                results.append(((-1, -1), continuous_pieces[:], False))
        
        # Option 2: Jump over first K pieces (K < N), stack on piece K+1 (if own higher tier)
        for k in range(len(continuous_pieces)):
            jumped_pieces = continuous_pieces[:k] if k > 0 else []
            landing_piece_pos = continuous_pieces[k]
            
            # Check if can jump over first k pieces
            jumped_tier = sum(
                sum(p.tier for p in self.board[r][c]) 
                for r, c in jumped_pieces
            ) if jumped_pieces else 0
            
            if jumping_tier < jumped_tier:
                continue
            
            # Check if landing piece is own higher tier
            landing_pieces = self.board[landing_piece_pos[0]][landing_piece_pos[1]]
            if landing_pieces[0].player == player:
                landing_tier = sum(p.tier for p in landing_pieces)
                if landing_tier > jumping_tier:
                    results.append((landing_piece_pos, jumped_pieces[:], False))
        
        return results
    
    def _dijkstra_from_position(self, start_pos: Tuple[int, int], 
                                initial_path: List[Tuple],
                                initial_score: float,
                                player: Player,
                                jumping_tier: int) -> Tuple[List[Tuple], Tuple[int, int], float]:
        """
        Run Dijkstra from a position to find the best jump path (only landing on empty cells)
        
        Args:
            start_pos: Starting position
            initial_path: Initial path (including first jump)
            initial_score: Initial score
            player: Current player
            jumping_tier: Total tier of jumping pieces
        
        Returns:
            (best_path, end_position, best_score)
        """
        opponent = Player.BLUE if player == Player.RED else Player.RED
        
        # Priority queue: (-score, path, current_pos)
        initial_path_copy = copy.deepcopy(initial_path)
        pq = [(-initial_score, initial_path_copy, start_pos)]
        visited = set()
        best_path = initial_path_copy
        best_score = initial_score
        best_end = start_pos
        
        while pq:
            neg_score, path, pos = heapq.heappop(pq)
            score = -neg_score
            
            if pos in visited:
                continue
            visited.add(pos)
            
            # Update best path
            if score > best_score:
                best_score = score
                best_path = copy.deepcopy(path)
                best_end = pos
            
            # Try jumping from current position in all 4 directions
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                jump_results = self._try_jump_direction(pos[0], pos[1], dr, dc, player, jumping_tier)
                
                for land_pos, jumped_pieces, can_continue in jump_results:
                    if not can_continue:  # Only consider landing on empty cells
                        continue
                    
                    if land_pos in visited:
                        continue
                    
                    # Calculate score from jumped opponent pieces
                    jump_score = sum(
                        sum(p.tier for p in self.board[r][c] if p.player == opponent)
                        for r, c in jumped_pieces
                    )
                    
                    new_score = score + jump_score
                    new_path = path + [(land_pos, jumped_pieces[:])]
                    
                    heapq.heappush(pq, (-new_score, new_path, land_pos))
        
        return best_path, best_end, best_score
    
    def _get_best_paths_by_initial_direction(self, row: int, col: int, 
                                            player: Player) -> Dict[str, List[Tuple]]:
        """
        Get best jump paths for each initial direction (up/down/left/right)
        Can return multiple paths per direction (for different terminal actions)
        
        Returns:
            {direction_name: [(best_path, end_position, score), ...]}
        """
        result = {}
        jumping_tier = sum(p.tier for p in self.board[row][col])
        opponent = Player.BLUE if player == Player.RED else Player.RED
        
        directions = {
            'up': (-1, 0),
            'down': (1, 0),
            'left': (0, -1),
            'right': (0, 1)
        }
        
        for dir_name, (dr, dc) in directions.items():
            result[dir_name] = []
            
            # Try first jump in this direction
            first_jump_results = self._try_jump_direction(row, col, dr, dc, player, jumping_tier)
            
            for land_pos, jumped_pieces, can_continue in first_jump_results:
                # Calculate first jump score
                first_score = sum(
                    sum(p.tier for p in self.board[r][c] if p.player == opponent)
                    for r, c in jumped_pieces
                )
                
                # Initial path
                initial_path = [(land_pos, jumped_pieces[:])]
                
                if can_continue:
                    # Run Dijkstra from landing position
                    best_path, end_pos, best_score = self._dijkstra_from_position(
                        land_pos, initial_path, first_score, player, jumping_tier
                    )
                    
                    # Add this path
                    result[dir_name].append((copy.deepcopy(best_path), end_pos, best_score))
                else:
                    # Terminal action (stacking or jumping off board)
                    result[dir_name].append((copy.deepcopy(initial_path), land_pos, first_score))
        
        return result
    
    def _get_extended_jump_options(self, end_pos: Tuple[int, int], 
                                   jumping_tier: int, 
                                   player: Player) -> List[Dict]:
        """
        Check if we can stack or jump off board from the end position
        
        Returns:
            List of dicts: [{'type': '上叠'/'跳出', 'land_pos': pos, 'jumped_pieces': [...]}]
        """
        options = []
        
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            jump_results = self._try_jump_direction(
                end_pos[0], end_pos[1], dr, dc, player, jumping_tier
            )
            
            for land_pos, jumped_pieces, can_continue in jump_results:
                if not can_continue:  # Stacking or jumping off
                    options.append({
                        'type': '上叠' if land_pos != (-1, -1) else '跳出',
                        'land_pos': land_pos,
                        'jumped_pieces': jumped_pieces[:]
                    })
        
        return options
    
    def _get_jump_actions_from_position(self, row: int, col: int, player: Player) -> List[Action]:
        """
        Generate all jump actions from a position (with expected scores)
        """
        actions = []
        jumping_tier = sum(p.tier for p in self.board[row][col])
        opponent = Player.BLUE if player == Player.RED else Player.RED
        
        # Get best paths for each initial direction
        best_paths = self._get_best_paths_by_initial_direction(row, col, player)
        
        for dir_name, paths_list in best_paths.items():
            for path, end_pos, base_score in paths_list:
                # Check if this is a terminal action (cannot continue)
                is_terminal = (end_pos == (-1, -1) or  # Jump off board
                              (0 <= end_pos[0] < self.board_size and 
                               0 <= end_pos[1] < self.board_size and
                               len(self.board[end_pos[0]][end_pos[1]]) > 0))  # Stacking
                
                # Add base action
                actions.append(Action(
                    action_type=ActionType.JUMP,
                    from_pos=(row, col),
                    to_pos=end_pos,
                    tier=None,
                    initial_direction=dir_name,
                    jump_sequence=copy.deepcopy(path),
                    expected_score=base_score
                ))
                
                # If this path ends on an empty cell, explore extended options
                if not is_terminal:
                    extended_options = self._get_extended_jump_options(end_pos, jumping_tier, player)
                    
                    for option in extended_options:
                        # Calculate extra score from extended jump
                        extra_score = sum(
                            sum(p.tier for p in self.board[r][c] if p.player == opponent)
                            for r, c in option['jumped_pieces']
                        )
                        
                        extended_path = copy.deepcopy(path) + [(option['land_pos'], option['jumped_pieces'])]
                        
                        actions.append(Action(
                            action_type=ActionType.JUMP,
                            from_pos=(row, col),
                            to_pos=option['land_pos'],
                            tier=None,
                            initial_direction=dir_name,
                            jump_sequence=extended_path,
                            expected_score=base_score + extra_score
                        ))
        
        return actions
    
    def get_legal_actions(self) -> List[Action]:
        """Get all legal actions for current player (with expected scores)"""
        actions = []
        player = self.current_player
        
        # 1. Revive actions
        for tier in [1, 2, 3]:
            if self.underworld[player][tier] > 0:
                for row in range(self.board_size):
                    for col in range(self.board_size):
                        if len(self.board[row][col]) == 0:  # Empty cell
                            actions.append(Action(
                                action_type=ActionType.REVIVE,
                                from_pos=None,
                                to_pos=(row, col),
                                tier=tier,
                                initial_direction=None,
                                jump_sequence=None,
                                expected_score=0.0
                            ))
        
        # 2. Move actions
        for row in range(self.board_size):
            for col in range(self.board_size):
                if self._has_own_pieces(row, col, player):
                    # Try all 4 directions
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        new_row, new_col = row + dr, col + dc
                        if self._is_valid_move(row, col, new_row, new_col, player):
                            actions.append(Action(
                                action_type=ActionType.MOVE,
                                from_pos=(row, col),
                                to_pos=(new_row, new_col),
                                tier=None,
                                initial_direction=None,
                                jump_sequence=None,
                                expected_score=0.0
                            ))
        
        # 3. Jump actions (with expected scores)
        for row in range(self.board_size):
            for col in range(self.board_size):
                if self._has_own_pieces(row, col, player):
                    jump_actions = self._get_jump_actions_from_position(row, col, player)
                    actions.extend(jump_actions)
        
        return actions
    
    def step(self, action: Action) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute an action and return (new_state, reward, done, info)
        """
        player = self.current_player
        opponent = Player.BLUE if player == Player.RED else Player.RED
        reward = 0
        
        if action.action_type == ActionType.REVIVE:
            tier = action.tier
            row, col = action.to_pos
            self.board[row][col] = [Piece(player, tier)]
            self.underworld[player][tier] -= 1
        
        elif action.action_type == ActionType.MOVE:
            from_row, from_col = action.from_pos
            to_row, to_col = action.to_pos
            pieces = self.board[from_row][from_col][:]  # Copy
            
            if len(self.board[to_row][to_col]) > 0:
                # Stacking
                self.board[to_row][to_col].extend(pieces)
            else:
                self.board[to_row][to_col] = pieces
            
            self.board[from_row][from_col] = []
        
        elif action.action_type == ActionType.JUMP:
            from_row, from_col = action.from_pos
            jump_sequence = action.jump_sequence
            pieces = self.board[from_row][from_col][:]  # Copy
            self.board[from_row][from_col] = []
            
            # Process each jump in the sequence
            for land_pos, jumped_positions in jump_sequence:
                for j_row, j_col in jumped_positions:
                    cell_pieces = self.board[j_row][j_col][:]  # Copy
                    
                    for piece in cell_pieces:
                        if piece.player == opponent:
                            reward += piece.tier
                            self.underworld[opponent][piece.tier] += 1
                        # Own pieces stay in place (不做任何处理)
                    
                    # Only remove opponent pieces
                    self.board[j_row][j_col] = [
                        p for p in self.board[j_row][j_col] if p.player == player
                    ]
            
            # Final landing
            final_land = action.to_pos
            if final_land == (-1, -1):  # Jump off board
                for piece in pieces:
                    self.underworld[player][piece.tier] += 1
            elif len(self.board[final_land[0]][final_land[1]]) > 0:
                # Stack on existing piece
                self.board[final_land[0]][final_land[1]].extend(pieces)
            else:
                # Land on empty cell
                self.board[final_land[0]][final_land[1]] = pieces
        
        # Update score
        self.scores[player] += reward
        
        # Check win condition
        done = self.scores[player] >= self.win_score
        
        # Switch player
        if not done:
            self.current_player = opponent
        
        # Info includes expected vs actual score comparison
        info = {
            'expected_score': action.expected_score,
            'actual_reward': reward
        }
        
        return self.get_state(), reward, done, info
    
    def render(self):
        """Render game state as text"""
        print("\n" + "="*60)
        print(f"Current Player: {self.current_player.name}")
        print(f"Scores - RED: {self.scores[Player.RED]}/{self.win_score}, BLUE: {self.scores[Player.BLUE]}/{self.win_score}")
        print("\nBoard:")
        print("     0    1    2    3    4")
        print("   " + "-"*25)
        for row in range(self.board_size):
            row_str = f"{row} |"
            for col in range(self.board_size):
                if len(self.board[row][col]) == 0:
                    if row == 2 and col == 2:
                        row_str += " ⊗  |"  # Center cell
                    else:
                        row_str += " .  |"
                else:
                    pieces = self.board[row][col]
                    player_char = "R" if pieces[0].player == Player.RED else "B"
                    total = sum(p.tier for p in pieces)
                    row_str += f"{player_char}{total:2d} |"
            print(row_str)
            print("   " + "-"*25)
        
        print("\nUnderworld:")
        for p in [Player.RED, Player.BLUE]:
            name = "RED" if p == Player.RED else "BLUE"
            u = self.underworld[p]
            print(f"  {name}: T1={u[1]}, T2={u[2]}, T3={u[3]}")
        print("="*60)
    
    def close(self):
        """Close the environment"""
        pass


if __name__ == "__main__":
    # Quick test
    env = ZombieEnv()
    env.render()
    
    print("\nGetting legal actions...")
    actions = env.get_legal_actions()
    print(f"Total actions: {len(actions)}")
    
    # Show action type distribution
    revive_count = sum(1 for a in actions if a.action_type == ActionType.REVIVE)
    move_count = sum(1 for a in actions if a.action_type == ActionType.MOVE)
    jump_count = sum(1 for a in actions if a.action_type == ActionType.JUMP)
    
    print(f"  REVIVE: {revive_count}")
    print(f"  MOVE: {move_count}")
    print(f"  JUMP: {jump_count}")
    
    # Show top 5 actions by expected score
    sorted_actions = sorted(actions, key=lambda a: a.expected_score, reverse=True)
    print("\nTop 5 actions by expected score:")
    for i, action in enumerate(sorted_actions[:5], 1):
        print(f"  {i}. {action}")
