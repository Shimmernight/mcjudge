# workbuddy.md — WorkBuddy 开发记录

本项目全程使用 WorkBuddy（官方合作伙伴）辅助开发，本文件为开发对话上下文的摘要记录，用于核验 WorkBuddy 联动活动奖励条件。

## 开发时间线

**2026 年 10 月 9 日（大赛开幕首日）**

1. **创意选题**：与 WorkBuddy 对话调研大赛规则（`M-China/mcd-developer-innovation-challenge`）与麦当劳 MCP 工具清单（35 个 Tool），经三轮头脑风暴（工具思维 → 梗文化思维），从「麦门判官 / 麦门预言家 / 赛博功德木鱼 / 麦辣闯关」中选定传播力最强的「麦门判官」方案：审判吃法 + 纯度段位 + 真实优惠券救赎闭环。

2. **项目搭建**：WorkBuddy 生成项目骨架——`skill/SKILL.md`（判官人设与工作流）、`scripts/judge.py`（纯度评分引擎，纯标准库、确定性可复现）、`README.md`、`MCP_INTEGRATION.md`，并原样引入官方 `CONTEST_DECLARATION.md`。当日完成 GitHub 公开仓库创建（`Shimmernight/mcjudge`）与报名 Issue 提交（官方仓库 Issue #66）。

3. **MCP 接入实测**：申请麦当劳 MCP Token 后，由 WorkBuddy 写入连接器配置并完成真实调用验证——`initialize` 握手、35 个工具列表拉取、`now-time-info` / `available-coupons` / `query-my-account` 实测返回真实数据。

4. **现场开庭**：WorkBuddy 以 MCP 实时数据完整演示一次判决（营养数据做罪证、活动日历引用、段位宣判），并当场发现「律法关键词追不上麦当劳上新速度」的真实缺陷。

5. **迭代修复**：
   - 新增「新生圣物」机制：引擎自动识别律法未收录的新品（每个 +2，上限 +6），配合 `--new-relic` 庭前查档通道（SKILL 判决前调 `campaign-calendar`/`query-meals` 核验新品），新品免维护（commit `e6f9d10`）
   - 修复长档案输入下常规商品被误判为新品的假阳性：自动识别加 60 字长度闸门，长档案一律走查档通道（commit `15a6f16`）

6. **档案提审模式**：应用户需求简化交互——开庭不再需要用户供述吃法，判官直接调 `order-list` 从历史订单重建吃法提审，`query-my-account` 积分作「功德值」旁证（含过期积分判词素材）。隐私边界同步写入 SKILL：只聚合呈现，不输出订单号/账户 ID（commit `15a6f16`）。

7. **全链路真机验证**：`auto-bind-coupons` 一键领券成功 3/3（免费脆薯饼、人气麦旋风买一送一、9.9 元中杯冰美式）；`query-nearby-stores` 定位门店；`query-store-coupons` 核验门店可用券（发现「薯薯任选」当晚过期）；`query-meals` 拉取实时菜单；`calculate-price` 真实算价——麦辣鸡腿堡三件套 + 冰美式（券后 ¥9.9），原价 ¥52.5 → 应付 ¥43.4，省 ¥9.1。

8. **create-order 实单验证**：经用户二次确认后，创建真实订单「薯薯任选（大薯条）×1」@ 龙华和平东路餐厅（外带自提），原价 ¥16 → 券后 ¥9.9，返回 orderId 与 H5 支付链接，15 分钟支付窗口由对话明确告知用户；支付环节按设计保留给用户在 App 内完成，Agent 不触碰支付。至此含下单在内的 MCP 点餐全链路真机验证完成，踩坑实录（takeWayCode 来源、券与门店强绑定、支付窗口）沉淀进 `MCP_INTEGRATION.md`。

## 结论

麦当劳 MCP 点餐主链路（领券 → 找店 → 查券 → 菜单 → 算价）在真实账户上全部验证通过；判决引擎在真实订单档案上完成提审判决。项目由 WorkBuddy 辅助完成创意调研、代码生成、MCP 接入调试、真机测试与文档撰写全流程。
