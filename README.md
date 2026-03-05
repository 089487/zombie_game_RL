# Zombie Game RL Environment

這是一個基於規則的殭屍棋盤遊戲環境，包含圖形化介面和簡單的基線策略。

## 檔案說明

- **rule.md**: 遊戲規則說明
- **Zombie_env.py**: 圖形化遊戲環境實作（支援跳躍動畫、手動模式）
- **simple_baseline.py**: 簡單基線策略（貪婪 + 一步前瞻）
- **MCTS.py**: 蒙地卡羅樹搜尋 (Monte Carlo Tree Search) 智能體
- **demo_animation.py**: 跳躍動畫演示腳本
- **manual_mode_demo.py**: 手動模式演示腳本（每步暫停等待按鍵）
- **test_jump.py**: 跳躍邏輯測試腳本
- **test_manual_mode.py**: 手動模式功能測試腳本

## 安裝相依套件

```bash
pip install pygame numpy
```

## 遊戲環境 (Zombie_env.py)

### 主要特色

- **5x5 棋盤**：含圖形化介面
- **三種殭屍階級**：1階、2階、3階
- **三種操作**：
  - **復活 (Revive)**：從陰間放置棋子到棋盤
  - **移動 (Move)**：移動到相鄰空格或疊加到己方更高階棋子上
  - **跳躍 (Jump)**：直線跳過連續棋子獲得分數
- **跳躍動畫**：逐步顯示跳躍過程，包含飛行軌跡和吃子效果
- **雙人對戰**：紅方 vs 藍方
- **勝利條件**：先達到 8 分獲勝

### 動畫功能

環境支援跳躍動作的逐步動畫顯示：
- 高亮顯示將要跳躍的棋子
- 動畫顯示棋子飛越過程（弧形軌跡）
- 標記被跳過的棋子
- 落地閃光效果
- 自動更新分數和遊戲狀態

### 手動模式 (Manual Mode)

手動模式允許你逐步觀察遊戲進程，每執行一步動作後會暫停並等待按鍵：

```python
# 創建環境並啟用手動模式
env = ZombieEnv(gui=True, manual_mode=True)

# 執行動作
state, reward, done = env.step(action)

# 渲染並等待按鍵
env.render()
env.wait_for_key()  # 等待用戶按任意鍵繼續
```

**快速演示：**
```bash
python manual_mode_demo.py
```

這個腳本會讓兩個基線智能體對戰，每一步都會暫停等待你按鍵。

### 使用範例

```python
from Zombie_env import ZombieEnv, ActionType, Action

# 建立環境（開啟 GUI）
env = ZombieEnv(gui=True)

# 取得合法動作
legal_actions = env.get_legal_actions()

# 執行動作（帶動畫）
if legal_actions:
    action = legal_actions[0]
    state, reward, done = env.step(action, with_animation=True)
    
    # 在遊戲循環中更新動畫
    while env.animation_active:
        if not env.update_animation():
            break  # 動畫完成
        env.render()
    
# 執行動作（不帶動畫，快速模式）
if legal_actions:
    action = legal_actions[0]
    state, reward, done = env.step(action, with_animation=False)
    
# 渲染畫面
env.render()

# 關閉環境
env.close()
```

### 演示動畫

```bash
python demo_animation.py
```

這會開啟遊戲視窗，按 ENTER 執行動作並觀看跳躍動畫。

### 測試環境

```bash
python Zombie_env.py
```

這會開啟一個遊戲視窗，顯示初始棋盤狀態。

## 簡單基線策略 (simple_baseline.py)

### 策略說明

這個基線使用 **貪婪 + 一步前瞻** 的策略：

1. **貪婪階段**：檢查是否有可以立即得分的跳躍動作
   - 如果有，選擇得分最高的跳躍

2. **一步前瞻階段**：如果沒有立即得分的跳躍
   - 枚舉所有可能的操作（復活、移動、跳躍）
   - 對每個操作進行模擬，檢查執行後能獲得的最佳跳躍得分
   - 選擇能在下一步帶來最高跳躍得分的操作

### 執行 Demo

```bash
python simple_baseline.py
```

### 控制方式

運行 demo 後：
- **SPACE**：切換自動播放模式
- **ENTER**：手動執行一步（非自動播放模式）
- **關閉視窗**：結束遊戲

### 使用範例

```python
from Zombie_env import ZombieEnv
from simple_baseline import SimpleBaseline

# 建立環境和智能體
env = ZombieEnv(gui=True)
agent = SimpleBaseline()

# 遊戲迴圈
done = False
while not done:
    # 選擇動作
    action = agent.select_action(env)
    
    if action:
        # 執行動作
        state, reward, done = env.step(action)
        
        # 渲染畫面
        env.render()
    else:
        break

env.close()
```

## MCTS 智能體 (MCTS.py)

### 演算法說明

實作標準的 **蒙地卡羅樹搜尋 (Monte Carlo Tree Search)** 演算法：

1. **Selection（選擇）**：使用 UCB1 公式選擇最有潛力的節點
   - UCB1 = 勝率 + 探索係數 × √(ln(父節點訪問次數) / 節點訪問次數)

2. **Expansion（擴展）**：為未嘗試的動作建立新節點

3. **Simulation（模擬）**：從新節點隨機遊玩到遊戲結束

4. **Backpropagation（回傳）**：將結果向上更新至根節點

### 執行方式

```bash
python MCTS.py
```

執行後會顯示三個選項：
1. **MCTS vs MCTS**：兩個 MCTS 智能體對戰
2. **MCTS vs Baseline**：MCTS 對上簡單基線（推薦）
3. **Run Tournament**：執行多局比賽統計勝率

程式會詢問是否啟用手動模式（Manual Mode）：
- 選擇 `y`：每執行一步會暫停，按任意鍵繼續
- 選擇 `n`：自動連續執行

### 使用範例

```python
from Zombie_env import ZombieEnv
from MCTS import MCTSAgent

# 建立環境和 MCTS 智能體
env = ZombieEnv(gui=True)
agent = MCTSAgent(simulation_time=1.0)  # 每步思考 1 秒

# 遊戲迴圈
done = False
while not done:
    # MCTS 選擇動作
    action = agent.select_action(env, verbose=True)
    
    if action:
        state, reward, done = env.step(action)
        env.render()
    else:
        break

env.close()
```

### 參數調整

```python
# 建立 MCTS 智能體時可調整參數
agent = MCTSAgent(
    simulation_time=2.0,      # 每步思考時間（秒）
    exploration_weight=1.414  # UCB1 探索係數（√2）
)
```

- **simulation_time**：越長越強，但速度越慢
- **exploration_weight**：較大值更傾向探索新動作，較小值更傾向利用已知好動作

### 快速對戰

```python
# MCTS vs Baseline（有 GUI）
from MCTS import play_mcts_vs_baseline
play_mcts_vs_baseline(mcts_time=1.0, mcts_is_red=True, gui=True, manual_mode=False)

# MCTS vs Baseline（手動模式）- 每步暫停
play_mcts_vs_baseline(mcts_time=1.0, mcts_is_red=True, gui=True, manual_mode=True)

# MCTS vs MCTS（有 GUI）
from MCTS import play_mcts_vs_mcts
play_mcts_vs_mcts(simulation_time=1.0, gui=True, manual_mode=False)

# 執行錦標賽（無 GUI，快速）
from MCTS import run_tournament
run_tournament(games=10, mcts_time=1.0)
```

## 遊戲規則重點

### 初始配置

- **紅方（上方）**：
  - 第 0 列：2階、空、3階、空、2階
  - 第 1 列：五個 1階
  - 陰間：兩個 2階

- **藍方（下方）**：
  - 第 3 列：五個 1階
  - 第 4 列：2階、空、3階、空、2階
  - 陰間：兩個 2階

### 跳躍規則

1. 沿直線方向跳過連續的殭屍棋
2. 跳躍棋子的階級總和必須 ≥ 被跳過棋子的階級總和
3. 可以落到空格（可繼續跳）、己方更高階棋子上（結束跳躍）、或跳出棋盤（結束跳躍）
4. 跳過對手棋子時，對手棋子進入陰間，獲得其階級總和的分數

### 得分規則

- 跳過對手的殭屍棋，將其送至陰間
- 獲得被送至陰間的對手殭屍棋階級總和作為分數
- 先達到 8 分者獲勝

## 進階使用

### 自訂智能體

你可以繼承或參考 `SimpleBaseline` 類別來實作自己的智能體：

```python
class MyAgent:
    def select_action(self, env):
        # 實作你的策略
        legal_actions = env.get_legal_actions()
        # ... 選擇動作的邏輯
        return chosen_action
```

### 強化學習整合

環境提供標準的 RL 介面：

- `get_state()`: 獲取當前狀態
- `get_legal_actions()`: 獲取合法動作列表
- `step(action)`: 執行動作，返回 (state, reward, done)
- `render()`: 渲染遊戲畫面

可以用來訓練 RL 智能體（如 DQN, PPO, AlphaZero 等）。

## 授權

本專案僅供學習和研究使用。
