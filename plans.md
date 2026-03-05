# ZombieEnv.py 重构实现计划

## 📌 重构目标

1. **修正跳跃逻辑**：支持多方向组合跳跃（上→右→左...）
2. **简化 Action Space**：每个起始方向使用 Dijkstra 找到最优路径
3. **修正自己棋子处理**：跳过自己的棋子时留在原位，不进入陰间
4. **扩展跳跃选项**：在最优路径终点可选择上叠或跳出棋盘

---

## 🏗️ 数据结构

### Enums
```python
class Player(Enum):
    RED = 0
    BLUE = 1

class ActionType(Enum):
    REVIVE = 0
    MOVE = 1
    JUMP = 2
```

### Dataclasses
```python
@dataclass
class Piece:
    player: Player
    tier: int

@dataclass
class Action:
    action_type: ActionType
    params: tuple
    # REVIVE: (tier, (row, col))
    # MOVE: ((from_row, from_col), (to_row, to_col))
    # JUMP: ((from_row, from_col), jump_sequence)
    #   - jump_sequence: [((land_row, land_col), [(jumped_r, jumped_c), ...]), ...]
```

---

## 🔧 核心方法实现顺序

### 1. 基础设施方法
- [x] `__init__()` - 初始化环境、GUI、变量
- [x] `_setup_board()` - 初始化棋盘布置
- [x] `get_state()` - 返回状态深拷贝
- [x] `_has_own_pieces()` - 检查位置是否有自己的棋子

### 2. Action 生成方法

#### 2.1 跳跃相关（核心重构部分）

**`_try_jump_direction(row, col, dr, dc, player, jumping_tier)`**
- **功能**：尝试在一个方向上跳一步
- **输入**：
  - `(row, col)`: 当前位置
  - `(dr, dc)`: 方向向量
  - `player`: 玩家
  - `jumping_tier`: 跳跃棋子的总tier
- **输出**：`[(着陆位置, 跳过的棋子列表, 是否可继续)]`
- **逻辑**：
  1. 沿方向找到所有连续的棋子
  2. 检查 `jumping_tier >= 跳过棋子的总tier`
  3. 计算着陆位置（最后一个棋子的下一格）
  4. 返回可能的着陆选项：
     - 空格（可继续）
     - 自己的更高阶棋子（上叠，不可继续）
     - 出界（跳出，不可继续）
- **⚠️ 注意**：返回 `jumped_pieces[:]` 复制，避免引用问题

**`_dijkstra_from_position(start_pos, initial_path, initial_score, player, jumping_tier)`**
- **功能**：从指定位置运行 Dijkstra 找最优路径
- **输入**：
  - `start_pos`: 起始位置（已经是第一跳的着陆点）
  - `initial_path`: 初始路径（包含第一跳）
  - `initial_score`: 初始得分
  - `player`: 玩家
  - `jumping_tier`: 跳跃棋子的总tier
- **输出**：`(best_path, end_pos, best_score)`
- **逻辑**：
  ```
  priority_queue = [(-initial_score, initial_path的深拷贝, start_pos)]
  visited = set()
  best_path, best_score, best_end = initial_path, initial_score, start_pos
  
  while pq 非空:
      neg_score, path, pos = heappop(pq)
      score = -neg_score
      
      if pos in visited: continue
      visited.add(pos)
      
      if score > best_score:
          best_score = score
          best_path = deepcopy(path)
          best_end = pos
      
      for 方向 in 4个方向:
          jump_results = _try_jump_direction(pos, 方向, player, jumping_tier)
          
          for land_pos, jumped_pieces, can_continue in jump_results:
              if not can_continue: continue  # 只考虑落在空格的
              if land_pos in visited: continue
              
              # 计算得分（只计算敌方棋子）
              jump_score = sum(敌方棋子tier)
              new_score = score + jump_score
              new_path = path + [(land_pos, jumped_pieces[:])]  # 复制
              
              heappush(pq, (-new_score, new_path, land_pos))
  
  return best_path, best_end, best_score
  ```
- **⚠️ 注意**：所有 path 操作都要深拷贝

**`_get_best_paths_by_initial_direction(row, col, player)`**
- **功能**：对4个初始方向分别计算最优路径
- **输入**：起始位置 `(row, col)`，玩家
- **输出**：`{方向名称: (最优路径, 终点位置, 得分)}`
- **逻辑**：
  ```
  result = {}
  jumping_tier = sum(棋子tier)
  
  for 方向 in ['up', 'down', 'left', 'right']:
      first_jump_results = _try_jump_direction(row, col, 方向, player, jumping_tier)
      
      for land_pos, jumped_pieces, can_continue in first_jump_results:
          if not can_continue: continue
          
          # 计算第一步得分
          first_score = sum(敌方棋子tier from jumped_pieces)
          
          # 第一步路径
          initial_path = [(land_pos, jumped_pieces[:])]
          
          # Dijkstra 从着陆点继续搜索
          best_path, end_pos, best_score = _dijkstra_from_position(
              land_pos, initial_path, first_score, player, jumping_tier
          )
          
          # 只保留该方向得分最高的
          if 方向 not in result or best_score > result[方向][2]:
              result[方向] = (deepcopy(best_path), end_pos, best_score)
  
  return result
  ```

**`_get_extended_jump_options(end_pos, jumping_tier, player)`**
- **功能**：检查从终点是否可以上叠或跳出
- **输入**：终点位置、jumping_tier、玩家
- **输出**：`[{'type': '上叠'/'跳出', 'land_pos': pos, 'jumped_pieces': [...]}]`
- **逻辑**：
  ```
  options = []
  
  for 方向 in 4个方向:
      jump_results = _try_jump_direction(end_pos, 方向, player, jumping_tier)
      
      for land_pos, jumped_pieces, can_continue in jump_results:
          if not can_continue:  # 上叠或跳出
              options.append({
                  'type': '上叠' if land_pos != (-1, -1) else '跳出',
                  'land_pos': land_pos,
                  'jumped_pieces': jumped_pieces[:]  # 复制
              })
  
  return options
  ```

**`_get_jump_actions_from_position(row, col, player)`**
- **功能**：为指定位置生成所有跳跃 actions
- **输入**：起始位置、玩家
- **输出**：`List[Action]`
- **逻辑**：
  ```
  actions = []
  jumping_tier = sum(棋子tier)
  
  # 获取4个方向的最优路径
  best_paths = _get_best_paths_by_initial_direction(row, col, player)
  
  for 方向, (path, end_pos, score) in best_paths.items():
      # 基础 action：停在终点空格
      actions.append(Action(JUMP, ((row, col), deepcopy(path))))
      
      # 扩展 action：上叠或跳出
      extended_options = _get_extended_jump_options(end_pos, jumping_tier, player)
      
      for option in extended_options:
          extended_path = deepcopy(path) + [(option['land_pos'], option['jumped_pieces'])]
          actions.append(Action(JUMP, ((row, col), extended_path)))
  
  return actions
  ```

#### 2.2 其他 Action 类型

**`get_legal_actions()`**
- **功能**：获取当前玩家所有合法 actions
- **逻辑**：
  ```
  actions = []
  player = self.current_player
  
  # 1. 复活 actions
  for tier in [1, 2, 3]:
      if self.underworld[player][tier] > 0:
          for row, col in 所有空格:
              actions.append(Action(REVIVE, (tier, (row, col))))
  
  # 2. 移动 actions
  for row, col in 所有自己的棋子位置:
      for 方向 in 4个方向:
          if _is_valid_move(row, col, 目标位置, player):
              actions.append(Action(MOVE, ((row, col), 目标位置)))
  
  # 3. 跳跃 actions
  for row, col in 所有自己的棋子位置:
      jump_actions = _get_jump_actions_from_position(row, col, player)
      actions.extend(jump_actions)
  
  return actions
  ```

### 3. 执行方法

**`step(action)`**
- **功能**：执行 action，更新状态
- **输入**：Action 对象
- **输出**：`(state, reward, done, info)`
- **逻辑**：
  ```
  player = self.current_player
  opponent = 对手
  reward = 0
  
  match action.action_type:
      case REVIVE:
          tier, (row, col) = action.params
          self.board[row][col] = [Piece(player, tier)]
          self.underworld[player][tier] -= 1
      
      case MOVE:
          (from_r, from_c), (to_r, to_c) = action.params
          pieces = self.board[from_r][from_c][:]  # 复制
          
          if 目标位置是空格:
              self.board[to_r][to_c] = pieces
          else:  # 上叠
              self.board[to_r][to_c].extend(pieces)
          
          self.board[from_r][from_c] = []
      
      case JUMP:
          (from_r, from_c), jump_sequence = action.params
          pieces = self.board[from_r][from_c][:]  # 复制
          self.board[from_r][from_c] = []
          
          for land_pos, jumped_positions in jump_sequence:
              for j_row, j_col in jumped_positions:
                  cell_pieces = self.board[j_row][j_col][:]
                  
                  for piece in cell_pieces:
                      if piece.player == opponent:
                          reward += piece.tier
                          self.underworld[opponent][piece.tier] += 1
                          # 从棋盘移除
                      # 自己的棋子留在原位
                  
                  # 只移除敌方棋子
                  self.board[j_row][j_col] = [
                      p for p in self.board[j_row][j_col] if p.player == player
                  ]
          
          # 最终着陆
          final_land = jump_sequence[-1][0]
          if final_land == (-1, -1):  # 跳出棋盘
              for piece in pieces:
                  self.underworld[player][piece.tier] += 1
          elif 目标位置有棋子:  # 上叠
              self.board[final_land[0]][final_land[1]].extend(pieces)
          else:  # 空格
              self.board[final_land[0]][final_land[1]] = pieces
  
  self.scores[player] += reward
  done = self.scores[player] >= self.win_score
  
  if not done:
      self.current_player = opponent
  
  return self.get_state(), reward, done, {}
  ```

---

## ⚠️ 关键注意事项

### 1. Mutable 引用问题
**所有列表操作都要复制：**
- ✅ `pieces = self.board[row][col][:]`
- ✅ `jumped_pieces[:]` 在返回时
- ✅ `copy.deepcopy(path)` 在 Dijkstra 中保存最佳路径
- ✅ `new_path = path + [(land_pos, jumped_pieces[:])]`

### 2. 自己棋子跳过规则
```python
# ❌ 错误（旧代码）：
if piece.player == player:
    self.underworld[player][piece.tier] += 1  # 不应该进入陰间

# ✅ 正确（新代码）：
# 跳过自己的棋子时，不做任何处理，棋子留在原位
# 只移除敌方棋子：
self.board[j_row][j_col] = [
    p for p in self.board[j_row][j_col] if p.player == player
]
```

### 3. Dijkstra 搜索范围
- ✅ **只探索**落在空格的路径（`can_continue=True`）
- ✅ **不包含**上叠和跳出的步骤（这些在终点单独处理）

### 4. Action Space 扩展
对每个方向的最优路径 `P_d`（终点在空格 `pos`）：
- 基础：`P_d` → 停在 pos
- 扩展：
  - 如果从 pos 可以上叠 → `P_d + 上叠步骤`
  - 如果从 pos 可以跳出 → `P_d + 跳出步骤`

---

## 📝 方法调用流程图

```
get_legal_actions()
├─ 复活 actions (直接生成)
├─ 移动 actions (直接生成)
└─ 跳跃 actions
    └─ for 每个自己的棋子位置:
        └─ _get_jump_actions_from_position(row, col, player)
            ├─ _get_best_paths_by_initial_direction(row, col, player)
            │   └─ for 每个初始方向:
            │       ├─ _try_jump_direction() → 第一步可行性
            │       └─ _dijkstra_from_position() → 继续搜索最优路径
            │           └─ while pq非空:
            │               └─ for 4个方向:
            │                   └─ _try_jump_direction() → 尝试继续跳
            │
            └─ for 每个方向的最优路径:
                ├─ 生成基础 action（停在终点）
                └─ _get_extended_jump_options(终点, tier, player)
                    └─ for 4个方向:
                        └─ _try_jump_direction() → 检查上叠/跳出
                        └─ 生成扩展 actions
```

---

## 🎯 实现步骤清单

### Phase 1: 核心跳跃逻辑
- [ ] 实现 `_try_jump_direction()` - 单步跳跃
- [ ] 实现 `_dijkstra_from_position()` - Dijkstra 搜索
- [ ] 实现 `_get_best_paths_by_initial_direction()` - 4个方向最优路径
- [ ] 实现 `_get_extended_jump_options()` - 终点扩展选项
- [ ] 实现 `_get_jump_actions_from_position()` - 生成跳跃 actions

### Phase 2: Action 生成
- [ ] 实现 `get_legal_actions()` - 整合所有 action 类型
- [ ] 实现 `_is_valid_move()` - 验证移动合法性
- [ ] 实现 `_has_own_pieces()` - 辅助方法

### Phase 3: 执行逻辑
- [ ] 实现 `step()` - 执行 action
  - [ ] 处理 REVIVE
  - [ ] 处理 MOVE
  - [ ] 处理 JUMP（关键：自己棋子留在原位）
- [ ] 修正得分计算（只计算敌方棋子）
- [ ] 更新陰间状态

### Phase 4: GUI & 动画（可选）
- [ ] 保留现有 GUI 渲染方法
- [ ] 保留动画系统
- [ ] 修正动画中的棋子处理逻辑

### Phase 5: 测试
- [ ] 测试单步跳跃
- [ ] 测试多步、多方向跳跃
- [ ] 测试上叠和跳出扩展
- [ ] 测试自己棋子不进入陰间
- [ ] 测试 Action Space 大小是否合理

---

## 🧪 测试案例

### 测试1：多方向跳跃
```
初始：棋子在 (2,2)，tier=3
布局：
  row 1: [R1] [R1] [ ] [ ] [ ]
  row 2: [ ] [ ] [R3] [ ] [ ]
  row 3: [B1] [ ] [ ] [ ] [B1]

预期：
- 可以往上跳 (2,2) → (0,2)
- 从 (0,2) 可以往左跳 → (0,0)
- 路径：上→左 得分=2
```

### 测试2：自己棋子不消失
```
跳过自己的棋子：
  [R2] → 跳过 → [R1] → 着陆 [ ]

预期：
- [R1] 留在原位
- 得分 = 0
- 陰间无变化
```

### 测试3：扩展选项
```
Dijkstra 终点：(1,1)
周围：
  (0,1): [R3]  # 更高阶，可上叠
  (2,1): [B1]  # 可跳出到 (3,1)

预期生成 actions：
- 基础：停在 (1,1)
- 扩展1：上叠到 (0,1)
- 扩展2：跳出到边界外
```

---

## 📊 预期 Action Space 大小估算

### 复活 actions
- 最多：3 种 tier × 25 个空格 = 75

### 移动 actions
- 最多：约 20 个棋子 × 4 方向 × 0.5 (有效率) ≈ 40

### 跳跃 actions
- **旧代码**：每个位置可能有数十甚至数百种跳跃组合（指数增长）
- **新代码**：每个位置最多 4 个方向 × 3 (基础+上叠+跳出) ≈ 12 个跳跃 action
- 总共：约 20 个棋子 × 12 ≈ 240

**总 Action Space：≈ 75 + 40 + 240 = 355 actions/回合**

相比旧代码大幅减少！

---

## 🔄 与旧代码的主要变化

| 项目 | 旧代码 | 新代码 |
|-----|--------|--------|
| 跳跃路径生成 | 递归探索所有可能组合 | Dijkstra 每个初始方向找最优路径 |
| Action Space | 指数级增长 | 线性增长（每方向1条+扩展） |
| 自己棋子处理 | 跳过后进入陰间 | 留在原位 |
| 路径终点 | 包含所有可能终点 | 只包含空格，上叠/跳出单独扩展 |
| 引用安全 | 部分复制 | 全面使用深拷贝 |

---

## 🚀 实现优先级

1. **高优先级（核心逻辑）**：
   - `_try_jump_direction`
   - `_dijkstra_from_position`
   - `_get_best_paths_by_initial_direction`
   - `step` 中的 JUMP 处理

2. **中优先级（功能完整性）**：
   - `_get_extended_jump_options`
   - `_get_jump_actions_from_position`
   - `get_legal_actions`

3. **低优先级（维护现有功能）**：
   - GUI 渲染方法
   - 动画系统
   - 手动模式

---

## ✅ 代码检查清单

在提交前确认：
- [ ] 所有列表返回都使用 `[:]` 或 `deepcopy()`
- [ ] `get_state()` 返回深拷贝
- [ ] 跳过自己的棋子不进入陰间
- [ ] Dijkstra 只探索落在空格的路径
- [ ] 每个初始方向最多生成有限个 actions
- [ ] 测试多方向跳跃路径是否正确
- [ ] 验证 Action Space 大小合理

---

## 📚 参考资料

- **游戏规则**：[rule.md](rule.md)
- **旧实现**：Zombie_env.py（已删除，仅供参考）
- **测试文件**：test_jump.py

---

**最后更新时间**: 2026-03-05
**状态**: 规划完成，待实现
