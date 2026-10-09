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

### 阶段一：受理与取证（档案提审）

| Tool | 用途 | 调用时机 |
|---|---|---|
| `order-list` | 调取近期到店/外送历史订单 | **开庭受理（默认模式）**：用户不供述吃法时，直接从订单历史重建吃法提审 |
| `query-my-account` | 查询积分账户（可用/将过期/已过期积分） | 受理时作「功德值」旁证，过期积分是判词素材 |
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
| `order-list` | （受理阶段）历史订单重建吃法描述；（结案阶段）对照历史避免重复推荐 |
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

1. **零输入开庭**：档案提审模式让用户一句话都不用说——「开庭」两个字就能从 `order-list` 历史订单直接生成判决，交互成本降到最低；判决书里出现的是用户真实吃过的东西，代入感和传播欲都远强于编造案例。
2. **情绪价值获客，工具价值留存**：纯度审判是低门槛、高传播的趣味交互；判决后即时衔接真实券与点餐，把玩笑变成一次有效转化。2. **激活沉睡权益**：大量用户的麦当劳优惠券处于「领了不用」状态；救赎流程让优惠券在具体场景中被消费。
3. **完整点餐闭环**：从查券、选门店、看菜单到算价、下单，覆盖 MCP 点餐主链路，验证了「对话即点餐」的可行性。
4. **确定性 + 实时性分层**：评分引擎离线确定可复现，MCP 数据实时新鲜，两层解耦、互为备份。

## 降级策略

- 无 Token：跳过阶段一与阶段三，离线判决 + 「忏悔室」文本环节，功能不残废
- Token 限流（429）：判词生成不依赖 MCP，仅救赎环节提示稍后重试
- 无可配送地址：`delivery-create-address` 可引导创建，用户拒绝则切换到店取餐场景
- 用户未确认下单：永远只展示救赎清单，不调用 `create-order`

## 真机验证记录（2026-10-09，真实账户）

以下链路在真实麦当劳账户上全部实测通过：

| # | 链路 | 结果 |
|---|---|---|
| 1 | `initialize` 握手 + `tools/list` | ✅ 35 个工具全量返回 |
| 2 | `now-time-info` / `campaign-calendar` / `list-nutrition-foods` | ✅ 实时数据正常 |
| 3 | `order-list` 历史订单提审 | ✅ 返回 6 单真实订单，重建吃法成功 |
| 4 | `query-my-account` 功德旁证 | ✅ 积分明细完整 |
| 5 | `auto-bind-coupons` 一键领券 | ✅ 3/3 成功（免费脆薯饼、麦旋风买一送一、9.9 冰美式） |
| 6 | `query-nearby-stores` 门店定位 | ✅ 返回 5 家门店含距离/营业时间/预约时段 |
| 7 | `query-store-coupons` 门店可用券核验 | ✅ 门店维度券过滤正确（不同门店可用券不同） |
| 8 | `query-meals` 实时菜单 | ✅ 全量菜单含现价/原价/优惠类型/常点标记 |
| 9 | `calculate-price` 算价 | ✅ 券后价精确到分（¥16 → ¥9.9，优惠 ¥6.1） |
| 10 | `create-order` 创建订单 | ✅ 返回 orderId / payH5Url / 15 分钟支付窗口（expirePayTime） |
| 11 | 支付 | 支付跳转 H5/App 完成（设计上不由 Agent 触碰支付） |

**踩坑实录**（对后来者的价值）：

- `create-order` 的 `takeWayCode` 必须取自 `calculate-price` 返回的 `takeWayList[].code`（`eat-in`=堂食 / `take-in-store`=外带自提），不能自己编
- 券与门店强绑定：同一张券在 A 店可用、B 店不可用，凑单前必须 `query-store-coupons` 逐店核验
- 到店订单有 **15 分钟支付窗口**（`expirePayTime`），超时自动取消，对话式点餐需要把这个时限明确告知用户
- `薯薯任选` 这类「券商品」在 `query-meals` 里有独立 productCode，下单时以券商品 code + couponId/couponCode 成对传入
- 限流 600 次/分钟很宽裕，正常对话流程（10 次调用以内）远远碰不到
