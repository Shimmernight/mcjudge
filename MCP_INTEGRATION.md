# MCP_INTEGRATION — 麦当劳 MCP 接入说明

本文档说明「麦门判官」实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

## 接入信息

- **MCP Server**：麦当劳中国官方托管服务
- **接入地址**：`https://mcp.mcd.cn`
- **协议**：Streamable HTTP
- **认证**：`Authorization: Bearer <YOUR_MCP_TOKEN>`（Token 从 [mcp.mcd.cn](https://mcp.mcd.cn) 控制台申请）
- **配置示例**：见 [README.md 快速开始](README.md#完整模式workbuddy--麦当劳-mcp)

## 使用的 Tools 及调用流程

麦门判官的工作流分为「取证 → 宣判 → 救赎」三个阶段，救赎阶段全部由真实 MCP 工具驱动：

### 阶段一：取证（增强判词）

| Tool | 用途 | 调用时机 |
|---|---|---|
| `list-nutrition-foods` | 获取餐品营养数据（能量、蛋白质、脂肪、钠等） | 判词中引用真实数据做「罪证」（如热量梗） |
| `campaign-calendar` | 查询当月营销活动日历 | 判词引用「圣历」活动，增加时效性 |
| `now-time-info` | 获取当前时间 | 深夜开庭（加班场景）时调整判词语气 |

### 阶段二：宣判

由本地引擎 `scripts/judge.py` 完成纯度评分与段位判定（不消耗 MCP 调用）。

### 阶段三：救赎套餐（核心业务闭环）

```
query-my-coupons ──┐
                   ├─→ 匹配可用优惠
available-coupons ─┘        │
                            ▼
query-nearby-stores ─→ 选定门店 ─→ query-meals ─→ query-meal-detail
                                                          │
                                                          ▼
                              calculate-price ─→ 展示「原价 → 券后价」
                                                          │
                                              用户二次确认 │
                                                          ▼
                                                   create-order
```

| Tool | 在救赎流程中的角色 |
|---|---|
| `available-coupons` | 查询可领取的「麦麦省」优惠券列表 |
| `auto-bind-coupons` | 一键领取全部可用券（用户同意后调用） |
| `query-my-coupons` | 查询账户已有优惠券，作为凑单依据 |
| `query-nearby-stores` | 根据用户位置查找附近可点餐门店 |
| `query-meals` | 查询门店当前可售菜单（分类、餐品编码、标签） |
| `query-meal-detail` | 查看套餐组成与可替换项，确定救赎套餐内容 |
| `calculate-price` | 结合优惠券计算商品金额、优惠金额与应付总价 |
| `create-order` | **仅在用户明确确认后**创建订单，返回支付链接（支付在麦当劳 App 完成） |
| `cancel-order` | 用户反悔时取消订单 |
| `query-order` / `order-list` | 查询救赎订单的状态与历史 |

### 彩蛋环节（可选）

| Tool | 用途 |
|---|---|
| `query-my-account` | 查询积分，判词中调侃「你的麦门功德值」 |
| `query-lottery-info` / `draw-lottery` | 「赛博功德」环节：用积分抽奖，愿圣光眷顾 |

## 业务价值

1. **情绪价值获客，工具价值留存**：纯度审判是低门槛、高传播的趣味交互；判决后即时衔接真实券与点餐，把玩笑变成一次有效转化。
2. **激活沉睡权益**：大量用户的麦当劳优惠券处于「领了不用」状态；救赎流程让优惠券在具体场景中被消费。
3. **完整点餐闭环**：从查券、选门店、看菜单到算价、下单，覆盖 MCP 点餐主链路，验证了「对话即点餐」的可行性。
4. **确定性 + 实时性分层**：评分引擎离线确定可复现，MCP 数据实时新鲜，两层解耦、互为备份。

## 降级策略

- 无 Token：跳过阶段一与阶段三，离线判决 + 「忏悔室」文本环节，功能不残废
- Token 限流（429）：判词生成不依赖 MCP，仅救赎环节提示稍后重试
- 无可配送地址：`delivery-create-address` 可引导创建，用户拒绝则切换到店取餐场景
- 用户未确认下单：永远只展示救赎清单，不调用 `create-order`
