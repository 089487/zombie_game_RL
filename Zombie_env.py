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
    USE_CARD = 3

class Card(Enum):
    NONE            = 0
    DIAGONAL_TIER1  = 1   # 1阶可斜向移动/跳跃
    REVIVE_ON_STACK = 2   # 复活1阶可叠在己方2/3阶上
    WIN_AT_5        = 3   # 达到5分也算胜利
    BLOCK_STACK     = 4   # 对手下回合不能叠加（3次）
    STACK_SAME_TIER = 5   # 可叠相同tier，最高6阶且只能有1个6阶
    ONLY_REVIVE     = 6   # 对手下回合只能REVIVE（2次）
    PROTECT_REVIVED = 7   # 新复活的1/2阶对手跳过不计分
    JUMP_REVIVE     = 8   # 主动跳出棋盘后可立即复活其中一个
    DOUBLE_REVIVE   = 9   # REVIVE时可复活两个（不同格子）

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
        elif self.action_type == ActionType.USE_CARD:
            return f"USE_CARD(card={self.tier})"
        else:  # JUMP
            steps = len(self.jump_sequence) if self.jump_sequence else 0
            return f"JUMP(from={self.from_pos}, dir={self.initial_direction}, steps={steps}, to={self.to_pos}, score={self.expected_score})"

class ZombieEnv:
    """Zombie Board Game Environment"""
    
    def __init__(self, red_card: 'Card' = None, blue_card: 'Card' = None):
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

        # Card system (Step 0+1)
        self.cards = {
            Player.RED:  red_card  if red_card  is not None else Card.NONE,
            Player.BLUE: blue_card if blue_card is not None else Card.NONE,
        }
        # Remaining uses for active cards 4 and 6
        self.card_uses = {
            Player.RED:  {Card.BLOCK_STACK: 3, Card.ONLY_REVIVE: 2},
            Player.BLUE: {Card.BLOCK_STACK: 3, Card.ONLY_REVIVE: 2},
        }
        # One-turn effects applied to a player by the opponent's active card
        self.turn_effects = {Player.RED: set(), Player.BLUE: set()}
        # Card 7: positions of freshly-revived protected pieces
        self.protected_positions = {Player.RED: set(), Player.BLUE: set()}
        # Card 8: pieces that jumped off board this turn (pending jump-revive)
        self.jumpedout_pieces = []
        # Card 9: waiting for the second REVIVE action
        self.pending_double_revive = False

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
        self.turn_effects = {Player.RED: set(), Player.BLUE: set()}
        self.protected_positions = {Player.RED: set(), Player.BLUE: set()}
        self.jumpedout_pieces = []
        self.pending_double_revive = False
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
        
        # Must be adjacent (Chebyshev distance 1: allows orthogonal AND diagonal)
        # Diagonal directions are only passed here when Card 1 is active (see get_legal_actions)
        if max(abs(from_row - to_row), abs(from_col - to_col)) != 1:
            return False
        
        # Target must be empty or have own higher tier piece for stacking
        target = self.board[to_row][to_col]
        if len(target) == 0:
            return True
        
        # Can stack on own higher tier piece
        if target[0].player == player:
            moving_tier = sum(p.tier for p in self.board[from_row][from_col])
            target_tier = sum(p.tier for p in target)

            # Normal: target must be strictly higher tier
            if target_tier > moving_tier:
                return True

            # Card 5 (STACK_SAME_TIER): can stack on equal-tier, merged <= 6, max one 6-tier
            if self.cards[player] == Card.STACK_SAME_TIER and target_tier == moving_tier:
                merged = moving_tier + target_tier
                if merged > 6:
                    return False
                if merged == 6:
                    # Ensure no other 6-tier cell exists on the board
                    for r in range(self.board_size):
                        for c in range(self.board_size):
                            if (r, c) != (to_row, to_col) and (r, c) != (from_row, from_col):
                                if sum(p.tier for p in self.board[r][c]) == 6:
                                    return False
                return True

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
                results.append(((-1, -1), continuous_pieces[:], True))
        
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
                                jumping_tier: int,
                                top_k: int = 5) -> Tuple[List[Tuple], Tuple[int, int], float]:
        """
        Run Dijkstra from a position to find the best jump path (only landing on empty cells)
        
        Args:
            start_pos: Starting position
            initial_path: Initial path (including first jump)
            initial_score: Initial score
            player: Current player
            jumping_tier: Total tier of jumping pieces
            top_k: Number of best paths to return
        Returns:
            (best_path, end_position, best_score)
        """
        opponent = Player.BLUE if player == Player.RED else Player.RED
        
        # Priority queue: (-score, path, current_pos)
        initial_path_copy = copy.deepcopy(initial_path)
        pq = [(-initial_score, initial_path_copy, start_pos)]
        visited = set()

        # best_k_paths stores (score, path, end_pos); positive score so heappop removes LOWEST, keeping top-K highest
        best_k_paths = []
        
        while pq:
            neg_score, path, pos = heapq.heappop(pq)
            score = -neg_score
            
            if pos in visited:
                continue
            visited.add(pos)

            heapq.heappush(best_k_paths, (score, copy.deepcopy(path), pos))
            if len(best_k_paths) > top_k:   
                heapq.heappop(best_k_paths)  # removes LOWEST score, keeps top-K highest

            # Cannot continue jumping from off-board position
            if pos == (-1, -1):
                continue
            
            # Try jumping from current position in all 4 directions
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                jump_results = self._try_jump_direction(pos[0], pos[1], dr, dc, player, jumping_tier)
                
                for land_pos, jumped_pieces, can_continue in jump_results:
                    if not can_continue:  # Only consider landing on empty cells
                        continue
                    
                    if land_pos in visited:
                        continue
                    
                    # Calculate score from jumped opponent pieces (skip protected positions)
                    jump_score = sum(
                        sum(p.tier for p in self.board[r][c] if p.player == opponent)
                        for r, c in jumped_pieces
                        if (r, c) not in self.protected_positions[opponent]
                    )
                    
                    new_score = score + jump_score
                    new_path = path + [(land_pos, jumped_pieces[:])]
                    
                    heapq.heappush(pq, (-new_score, new_path, land_pos))
        

        return best_k_paths  # Return top K paths instead of just the best one
        #return best_path, best_end, best_score
    
    def _get_best_paths_by_initial_direction(self, row: int, col: int, 
                                            player: Player,
                                            top_k: int = 5,
                                            extra_dirs: list = None) -> Dict[str, List[Tuple]]:
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
        # Card 1: add diagonal directions if provided
        if extra_dirs:
            diag_names = {(-1,-1): 'up-left', (-1,1): 'up-right',
                          (1,-1):  'down-left', (1,1): 'down-right'}
            for dr, dc in extra_dirs:
                name = diag_names.get((dr, dc), f'diag_{dr}_{dc}')
                directions[name] = (dr, dc)
        
        for dir_name, (dr, dc) in directions.items():
            result[dir_name] = []
            
            # Try first jump in this direction
            first_jump_results = self._try_jump_direction(row, col, dr, dc, player, jumping_tier)
            
            for land_pos, jumped_pieces, can_continue in first_jump_results:
                # Calculate first jump score (skip protected positions)
                first_score = sum(
                    sum(p.tier for p in self.board[r][c] if p.player == opponent)
                    for r, c in jumped_pieces
                    if (r, c) not in self.protected_positions[opponent]
                )
                
                # Initial path
                initial_path = [(land_pos, jumped_pieces[:])]
                
                if can_continue:
                    # Run Dijkstra from landing position
                    best_k_paths = self._dijkstra_from_position(
                        land_pos, initial_path, first_score, player, jumping_tier, top_k
                    )
                    

                    # Add THOSE paths to result (not just the single best one)
                    for score, path, end_pos in best_k_paths:
                        result[dir_name].append((copy.deepcopy(path), end_pos, score))
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
    
    def _get_jump_actions_from_position(self, row: int, col: int, player: Player,
                                         extra_dirs: list = None) -> List[Action]:
        """
        Generate all jump actions from a position (with expected scores)
        """
        actions = []
        jumping_tier = sum(p.tier for p in self.board[row][col])
        opponent = Player.BLUE if player == Player.RED else Player.RED
        
        # Get best paths for each initial direction
        best_paths = self._get_best_paths_by_initial_direction(row, col, player, extra_dirs=extra_dirs)
        
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
                        # Calculate extra score from extended jump (skip protected positions)
                        extra_score = sum(
                            sum(p.tier for p in self.board[r][c] if p.player == opponent)
                            for r, c in option['jumped_pieces']
                            if (r, c) not in self.protected_positions[opponent]
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

        # Card 8: pending jump-revive — only allow reviving one of the jumped-out pieces
        if self.cards[player] == Card.JUMP_REVIVE and self.jumpedout_pieces:
            jump_revive_actions = []
            seen_tiers = set()
            for piece in self.jumpedout_pieces:
                if piece.tier not in seen_tiers:
                    seen_tiers.add(piece.tier)
                    for row in range(self.board_size):
                        for col in range(self.board_size):
                            if len(self.board[row][col]) == 0:
                                jump_revive_actions.append(Action(
                                    action_type=ActionType.REVIVE,
                                    from_pos=None,
                                    to_pos=(row, col),
                                    tier=piece.tier,
                                    initial_direction=None,
                                    jump_sequence=None,
                                    expected_score=0.0
                                ))
            return jump_revive_actions

        # Card 9: pending second revive — only allow reviving one more piece
        if self.cards[player] == Card.DOUBLE_REVIVE and self.pending_double_revive:
            second_revive_actions = []
            for tier in [1, 2, 3]:
                if self.underworld[player][tier] > 0:
                    for row in range(self.board_size):
                        for col in range(self.board_size):
                            if len(self.board[row][col]) == 0:
                                second_revive_actions.append(Action(
                                    action_type=ActionType.REVIVE,
                                    from_pos=None,
                                    to_pos=(row, col),
                                    tier=tier,
                                    initial_direction=None,
                                    jump_sequence=None,
                                    expected_score=0.0
                                ))
            return second_revive_actions

        # 1. Revive actions
        opponent = Player.BLUE if player == Player.RED else Player.RED
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
                        # Card 2: revive tier-1 onto own tier-2 or tier-3 cell
                        elif (tier == 1
                              and self.cards[player] == Card.REVIVE_ON_STACK
                              and len(self.board[row][col]) > 0
                              and all(p.player == player for p in self.board[row][col])
                              and sum(p.tier for p in self.board[row][col]) in (2, 3)):
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
                    # Card 1: tier-1 pieces can move diagonally
                    cell_tier = sum(p.tier for p in self.board[row][col])
                    move_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if self.cards[player] == Card.DIAGONAL_TIER1 and cell_tier == 1:
                        move_dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                    for dr, dc in move_dirs:
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
                    # Card 1: tier-1 pieces can also jump diagonally
                    cell_tier = sum(p.tier for p in self.board[row][col])
                    extra_dirs = []
                    if self.cards[player] == Card.DIAGONAL_TIER1 and cell_tier == 1:
                        extra_dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
                    jump_actions = self._get_jump_actions_from_position(row, col, player, extra_dirs=extra_dirs)
                    actions.extend(jump_actions)

        # 4. Active card use (Card 4 / Card 6) — usable before own move, once per turn
        if self.cards[player] == Card.BLOCK_STACK:
            if (self.card_uses[player][Card.BLOCK_STACK] > 0
                    and 'no_stack' not in self.turn_effects[opponent]):
                actions.append(Action(
                    action_type=ActionType.USE_CARD,
                    from_pos=None, to_pos=None,
                    tier=4,
                    initial_direction=None, jump_sequence=None,
                    expected_score=0.0
                ))
        if self.cards[player] == Card.ONLY_REVIVE:
            if (self.card_uses[player][Card.ONLY_REVIVE] > 0
                    and 'only_revive' not in self.turn_effects[opponent]):
                actions.append(Action(
                    action_type=ActionType.USE_CARD,
                    from_pos=None, to_pos=None,
                    tier=6,
                    initial_direction=None, jump_sequence=None,
                    expected_score=0.0
                ))

        # 5. Filter actions based on turn_effects imposed by opponent's card last turn
        if 'only_revive' in self.turn_effects[player]:
            # Can ONLY revive — remove moves, jumps, and card-use actions
            actions = [a for a in actions if a.action_type == ActionType.REVIVE]
        elif 'no_stack' in self.turn_effects[player]:
            # Cannot stack —  remove MOVE actions that target a non-empty cell
            def _is_stacking_move(a):
                if a.action_type != ActionType.MOVE:
                    return False
                to_r, to_c = a.to_pos
                return len(self.board[to_r][to_c]) > 0
            actions = [a for a in actions if not _is_stacking_move(a)]

        return actions
    
    def step(self, action: Action) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute an action and return (new_state, reward, done, info)
        """
        player = self.current_player
        opponent = Player.BLUE if player == Player.RED else Player.RED
        reward = 0
        
        if action.action_type == ActionType.USE_CARD:
            card_num = action.tier
            if card_num == 4:   # BLOCK_STACK
                self.card_uses[player][Card.BLOCK_STACK] -= 1
                self.turn_effects[opponent].add('no_stack')
            elif card_num == 6:  # ONLY_REVIVE
                self.card_uses[player][Card.ONLY_REVIVE] -= 1
                self.turn_effects[opponent].add('only_revive')
            # Card use does NOT switch the current player — player still acts this turn
            return self.get_state(), 0, False, {'expected_score': 0.0, 'actual_reward': 0}

        if action.action_type == ActionType.REVIVE:
            tier = action.tier
            row, col = action.to_pos
            if len(self.board[row][col]) > 0:
                # Card 2: stacking revive onto own piece
                self.board[row][col].append(Piece(player, tier))
            else:
                self.board[row][col] = [Piece(player, tier)]
            self.underworld[player][tier] -= 1
            # Card 7: mark freshly-revived tier-1/2 as protected for opponent's next turn
            if self.cards[player] == Card.PROTECT_REVIVED and tier in (1, 2):
                self.protected_positions[player].add((row, col))
            # Card 8: this was the pending jump-revive → clear flag, fall through to switch player
            if self.jumpedout_pieces:
                self.jumpedout_pieces = []
            # Card 9: first REVIVE → trigger pending second revive if pieces remain in underworld
            elif self.cards[player] == Card.DOUBLE_REVIVE and not self.pending_double_revive:
                has_remaining = any(self.underworld[player][t] > 0 for t in [1, 2, 3])
                if has_remaining:
                    self.pending_double_revive = True
                    self.scores[player] += reward
                    done = self.scores[player] >= self.win_score or (
                        self.cards[player] == Card.WIN_AT_5 and self.scores[player] == 5
                    )
                    return self.get_state(), reward, done, {'expected_score': action.expected_score, 'actual_reward': reward}
            # Card 9: second REVIVE → clear pending flag, fall through to switch player
            elif self.pending_double_revive:
                self.pending_double_revive = False

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
                            # Card 7: skip if this position is protected
                            if (j_row, j_col) in self.protected_positions[opponent]:
                                continue
                            reward += piece.tier
                            self.underworld[opponent][piece.tier] += 1
                        # Own pieces stay in place
                    
                    # Remove opponent pieces that are NOT protected
                    self.board[j_row][j_col] = [
                        p for p in self.board[j_row][j_col]
                        if p.player == player or (j_row, j_col) in self.protected_positions[opponent]
                    ]
            
            # Final landing
            final_land = action.to_pos
            if final_land == (-1, -1):  # Jump off board
                for piece in pieces:
                    self.underworld[player][piece.tier] += 1
                # Card 8: trigger pending jump-revive — player keeps their turn
                if self.cards[player] == Card.JUMP_REVIVE:
                    self.jumpedout_pieces = pieces[:]
                    self.scores[player] += reward
                    done = self.scores[player] >= self.win_score or (
                        self.cards[player] == Card.WIN_AT_5 and self.scores[player] == 5
                    )
                    return self.get_state(), reward, done, {'expected_score': action.expected_score, 'actual_reward': reward}
            elif len(self.board[final_land[0]][final_land[1]]) > 0:
                # Stack on existing piece
                self.board[final_land[0]][final_land[1]].extend(pieces)
            else:
                # Land on empty cell
                self.board[final_land[0]][final_land[1]] = pieces
        
        # Update score
        self.scores[player] += reward
        
        # Check win condition
        # Card 3 (WIN_AT_5): score == 5 is an extra win condition; normal >= win_score still applies
        done = self.scores[player] >= self.win_score or (
            self.cards[player] == Card.WIN_AT_5 and self.scores[player] == 5
        )
        
        # Switch player
        if not done:
            # Clear effects that were constraining THIS player's turn
            self.turn_effects[player].clear()
            # Clear OPPONENT's protection (it was valid for this one opponent-turn)
            self.protected_positions[opponent].clear()
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
