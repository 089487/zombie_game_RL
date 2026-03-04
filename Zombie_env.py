import copy
import pygame
import sys

# ==========================================
# 1. 遊戲狀態定義 (純資料，為 MCTS 設計)
# ==========================================
class GameState:
    def __init__(self):
        self.board_size = 4
        # board 是一個 4x4 的 2D List。
        # None 表示空格； dict 表示棋子，例如 {"player": 1, "level": 1}
        self.board = [[None for _ in range(self.board_size)] for _ in range(self.board_size)]
        
        # 陰間 (備用區) 的棋子，存放整數代表階級
        self.yin_realm = {
            1: [2, 2], # 玩家 1 初始有兩隻 2階
            2: [2, 2]  # 玩家 2 初始有兩隻 2階
        }
        
        self.scores = {1: 0, 2: 0}
        self.current_player = 1
        self.target_score = 8

    def is_terminal(self):
        """檢查遊戲是否結束"""
        return self.scores[1] >= self.target_score or self.scores[2] >= self.target_score

    def get_winner(self):
        if self.scores[1] >= self.target_score: return 1
        if self.scores[2] >= self.target_score: return 2
        return 0

# ==========================================
# 2. 遊戲環境引擎 (處理規則、合法步、狀態轉移)
# ==========================================
class ZombieEnv:
    def __init__(self):
        self.state = GameState()
        self._setup_initial_board()

    def _setup_initial_board(self):
        """
        根據說明書建立初始盤面 (此處為推測的對稱 4x4 初始佈置)
        您可以根據實體桌遊調整具體的起始位置。
        """
        # 玩家 1 (上方)
        self.state.board[0][0] = {"player": 1, "level": 1}
        self.state.board[0][1] = {"player": 1, "level": 3}
        self.state.board[0][2] = {"player": 1, "level": 1}
        self.state.board[0][3] = {"player": 1, "level": 1}
        
        # 玩家 2 (下方)
        self.state.board[3][0] = {"player": 2, "level": 1}
        self.state.board[3][1] = {"player": 2, "level": 1}
        self.state.board[3][2] = {"player": 2, "level": 3}
        self.state.board[3][3] = {"player": 2, "level": 1}

    def get_legal_actions(self, state: GameState):
        """
        回傳所有合法動作。動作格式為 Tuple:
        1. ("REVIVE", level, (r, c))
        2. ("MOVE", (r1, c1), (r2, c2))
        3. ("JUMP", start_pos, [path_of_landings]) -> 為了簡化，這裡回傳單步跳躍，MCTS 可以在內部處理連跳。
        """
        actions =[]
        p = state.current_player

        # --- 1. 復活 (Revive) ---
        unique_yin_pieces = set(state.yin_realm[p])
        empty_cells =[(r, c) for r in range(4) for c in range(4) if state.board[r][c] is None]
        for level in unique_yin_pieces:
            for r, c in empty_cells:
                actions.append(("REVIVE", level, (r, c)))

        # --- 2. 移動 (Move) & 3. 簡單跳躍 (Jump) ---
        dirs =[(-1, 0), (1, 0), (0, -1), (0, 1)]
        for r in range(4):
            for c in range(4):
                piece = state.board[r][c]
                if piece and piece["player"] == p:
                    # 檢查四個方向
                    for dr, dc in dirs:
                        nr, nc = r + dr, c + dc
                        # --- 移動邏輯 ---
                        if 0 <= nr < 4 and 0 <= nc < 4:
                            target = state.board[nr][nc]
                            # 空格
                            if target is None:
                                actions.append(("MOVE", (r, c), (nr, nc)))
                            # 上疊 (友軍且階級較高)
                            elif target["player"] == p and target["level"] > piece["level"]:
                                actions.append(("MOVE", (r, c), (nr, nc)))
                        
                        # --- 跳躍邏輯 (基礎直線偵測) ---
                        # 實作一個簡單射線尋找連續棋子
                        jump_len = 1
                        jumped_levels = 0
                        enemy_levels = 0
                        valid_jump = False
                        
                        while True:
                            jr, jc = r + dr * jump_len, c + dc * jump_len
                            if not (0 <= jr < 4 and 0 <= jc < 4):
                                # 跳出棋盤 (入陰間)
                                if jumped_levels > 0 and piece["level"] >= jumped_levels:
                                    actions.append(("JUMP_OUT", (r, c), (dr, dc), enemy_levels))
                                break
                            
                            mid_piece = state.board[jr][jc]
                            if mid_piece is not None:
                                jumped_levels += mid_piece["level"]
                                if mid_piece["player"] != p:
                                    enemy_levels += mid_piece["level"]
                                jump_len += 1
                            else:
                                # 碰到空格，結算是否能落在此處
                                if jumped_levels > 0 and piece["level"] >= jumped_levels:
                                    actions.append(("JUMP", (r, c), (jr, jc), enemy_levels))
                                break
                                
                            # 如果碰到友軍且打算上疊結束 (視為落在該友軍上)
                            # 需再往前看一格是友軍的情況
                            if mid_piece is not None and mid_piece["player"] == p and mid_piece["level"] > piece["level"]:
                                if jumped_levels - mid_piece["level"] > 0 and piece["level"] >= (jumped_levels - mid_piece["level"]):
                                     actions.append(("JUMP_STACK", (r, c), (jr, jc), enemy_levels))
                                
        return actions

    def step(self, state: GameState, action):
        """
        給定狀態與動作，回傳 (new_state, reward, done)
        使用 deepcopy 確保 MCTS 不會污染原本的狀態
        """
        new_state = copy.deepcopy(state)
        p = new_state.current_player
        act_type = action[0]

        if act_type == "REVIVE":
            _, level, (r, c) = action
            new_state.yin_realm[p].remove(level)
            new_state.board[r][c] = {"player": p, "level": level}

        elif act_type == "MOVE":
            _, (r1, c1), (r2, c2) = action
            piece = new_state.board[r1][c1]
            target = new_state.board[r2][c2]
            
            if target is None:
                new_state.board[r2][c2] = piece
            else: # 上疊
                new_state.board[r2][c2]["level"] += piece["level"]
            new_state.board[r1][c1] = None

        elif act_type == "JUMP" or act_type == "JUMP_STACK" or act_type == "JUMP_OUT":
            # 簡化版跳躍邏輯：吃掉路徑上的敵人
            r1, c1 = action[1]
            r2, c2 = action[2]
            enemy_score = action[3]
            piece = new_state.board[r1][c1]
            
            # 給分並將敵軍送入陰間
            if enemy_score > 0:
                new_state.scores[p] += enemy_score
                # 實作細節：需把途中敵軍清空，並加入對方 yin_realm
                dr = 0 if r2 == r1 else (1 if r2 > r1 else -1)
                dc = 0 if c2 == c1 else (1 if c2 > c1 else -1)
                curr_r, curr_c = r1 + dr, c1 + dc
                while (curr_r, curr_c) != (r2, c2) and (0 <= curr_r < 4 and 0 <= curr_c < 4):
                    mid = new_state.board[curr_r][curr_c]
                    if mid and mid["player"] != p:
                        new_state.yin_realm[3-p].append(mid["level"]) # 3-p 就是對手
                    new_state.board[curr_r][curr_c] = None # 清空路徑
                    curr_r += dr
                    curr_c += dc

            # 移動跳躍者
            new_state.board[r1][c1] = None
            if act_type == "JUMP":
                new_state.board[r2][c2] = piece
            elif act_type == "JUMP_STACK":
                new_state.board[r2][c2]["level"] += piece["level"]
            elif act_type == "JUMP_OUT":
                new_state.yin_realm[p].append(piece["level"])

        # 換人回合
        new_state.current_player = 3 - p 
        
        return new_state, new_state.scores[p], new_state.is_terminal()


# ==========================================
# 3. 圖形化介面 (僅讀取 GameState 並繪製)
# ==========================================
class ZombieGUI:
    def __init__(self, env):
        pygame.init()
        self.env = env
        self.CELL_SIZE = 100
        self.MARGIN = 50
        self.WIDTH = self.CELL_SIZE * 4 + self.MARGIN * 2 + 200 # 右側留白顯示資訊
        self.HEIGHT = self.CELL_SIZE * 4 + self.MARGIN * 2
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("殭屍棋 (Zombie Bump) MCTS Env")
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.colors = {
            "bg": (30, 30, 40),
            "grid": (200, 200, 200),
            "p1": (220, 50, 50),   # 玩家1 紅色
            "p2": (50, 150, 220),  # 玩家2 藍色
            "text": (255, 255, 255)
        }

    def draw_state(self, state: GameState):
        self.screen.fill(self.colors["bg"])
        
        # 畫棋盤
        for r in range(4):
            for c in range(4):
                rect = (self.MARGIN + c * self.CELL_SIZE, self.MARGIN + r * self.CELL_SIZE, self.CELL_SIZE, self.CELL_SIZE)
                pygame.draw.rect(self.screen, self.colors["grid"], rect, 2)
                
                piece = state.board[r][c]
                if piece:
                    color = self.colors["p1"] if piece["player"] == 1 else self.colors["p2"]
                    center = (self.MARGIN + c * self.CELL_SIZE + self.CELL_SIZE//2, 
                              self.MARGIN + r * self.CELL_SIZE + self.CELL_SIZE//2)
                    pygame.draw.circle(self.screen, color, center, self.CELL_SIZE//3)
                    
                    # 畫階級數字
                    text = self.font.render(str(piece["level"]), True, self.colors["text"])
                    text_rect = text.get_rect(center=center)
                    self.screen.blit(text, text_rect)

        # 畫右側資訊面板
        info_x = self.MARGIN * 2 + 4 * self.CELL_SIZE
        
        y_offset = 50
        turn_text = self.font.render(f"Turn: Player {state.current_player}", True, self.colors["text"])
        self.screen.blit(turn_text, (info_x, y_offset))
        
        y_offset += 40
        score_text = self.font.render(f"P1 Score: {state.scores[1]} / 8", True, self.colors["p1"])
        self.screen.blit(score_text, (info_x, y_offset))
        
        y_offset += 30
        score_text2 = self.font.render(f"P2 Score: {state.scores[2]} / 8", True, self.colors["p2"])
        self.screen.blit(score_text2, (info_x, y_offset))

        y_offset += 50
        y1_text = self.font.render(f"P1 Yin: {state.yin_realm[1]}", True, self.colors["p1"])
        self.screen.blit(y1_text, (info_x, y_offset))

        y_offset += 30
        y2_text = self.font.render(f"P2 Yin: {state.yin_realm[2]}", True, self.colors["p2"])
        self.screen.blit(y2_text, (info_x, y_offset))

        pygame.display.flip()

# ==========================================
# 4. 測試主程式與隨機對役展示 (供您測試接 MCTS)
# ==========================================
if __name__ == "__main__":
    import random
    import time

    env = ZombieEnv()
    gui = ZombieGUI(env)
    
    current_state = env.state
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
        gui.draw_state(current_state)
        
        if not current_state.is_terminal():
            # ==========================================
            # 在這裡，您可以把這段換成您的 MCTS Agent:
            # action = mcts.search(current_state)
            # ==========================================
            legal_actions = env.get_legal_actions(current_state)
            if legal_actions:
                # 這裡暫時用 Random Agent 代替 MCTS
                action = random.choice(legal_actions)
                current_state, reward, done = env.step(current_state, action)
                time.sleep(0.5) # 放慢速度以便觀察
            else:
                # 若無步可走 (理論上很少發生，因為有復活機制)，強制跳過
                current_state.current_player = 3 - current_state.current_player
        else:
            print(f"Game Over! Winner: Player {current_state.get_winner()}")
            time.sleep(3)
            running = False

    pygame.quit()
    sys.exit()