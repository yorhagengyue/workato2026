# PRD - AI Native Developer Attention Decision System

## 1. 产品目标
面向 AI-native developer，在“当前项目上下文 + 长期研发画像”下，从外部信息流中筛选真正值得进入当前思考回路的候选项，并触发分级动作（轻提示、深读、落动作）。

## 2. 系统边界（硬规则）

### 2.1 A 类：一手源（事实源）
仅包含：
- GitHub Trending
- 指定 repo 列表
- repo 更新事件（release、tag、breaking PR、security advisory）
- AI 大厂官方 release notes / docs / blog / changelog

A 类可独立触发深读与落动作候选。

### 2.2 B 类：高密度解释源（观点助推）
仅包含少量白名单博主推文，作用是提供“理解角度/观点信号”，不是事实源。

B 类硬规则：
1. 仅收白名单作者，禁止开放式推文抓取。
2. B 类默认不能单独触发深读。
3. B 类最多只能触发两类动作：
   - 轻提示
   - 提升某个 A 类候选优先级
4. 触发本地 Codex / Claude Code 深读必须满足至少一个条件：
   - 有 A 类来源支撑
   - 与当前项目上下文高度相似
   - 用户主动表示兴趣

结论：B 类是“助推器”，不是“方向盘”。

## 3. 决策层与动作层

### 3.1 三层动作
- 轻提示（Hint）：进入收件箱摘要，不占用本地执行资源。
- 深读（Deep Read）：触发本地 Codex/Claude Code 对候选项做项目相关性拆解。
- 落动作（Action）：生成可执行任务（Issue/PR/实验脚本/验证清单）。

### 3.2 建议阈值（MVP）
统一总分 `score_total`（0-100）：
- `0-44`：丢弃或仅存档
- `45-64`：轻提示
- `65-79`：深读候选（需满足深读门槛条件）
- `>=80`：落动作候选（需通过权限与预算门禁）

门槛因子（必须显式记录）：
- `evidence_grade`：A0（仅 B 类）/ A1（单 A 类）/ A2（多 A 类交叉）
- `context_similarity`：与当前项目上下文相似度
- `user_intent_signal`：用户近期显式兴趣信号
- `execution_cost`：预计 token/时间/外部 API 成本
- `risk_level`：权限、数据、合规风险

## 4. 数据模型（MVP）

### 4.1 `project_snapshot`
```json
{
  "project_id": "string",
  "snapshot_time": "datetime",
  "repo_urls": ["string"],
  "tech_stack": ["string"],
  "active_modules": ["string"],
  "current_goals": ["string"],
  "open_problems": ["string"],
  "non_goals": ["string"],
  "risk_tolerance": "low|medium|high",
  "latency_budget_ms": 0,
  "cost_budget_daily_usd": 0,
  "security_constraints": ["string"],
  "acceptance_signals": ["string"],
  "rejection_signals": ["string"],
  "trace_id": "string",
  "last_feedback": [
    {
      "item_id": "string",
      "feedback": "upvote|downvote|mute|act",
      "reason": "string"
    }
  ]
}
```

### 4.2 `repo_compare`
```json
{
  "candidate_id": "string",
  "source_class": "A|B",
  "source_type": "github|official_doc|official_blog|tweet_whitelist",
  "evidence_grade": "A0|A1|A2",
  "candidate_url": "string",
  "published_at": "datetime",
  "summary": "string",
  "claimed_change_type": ["feature|breaking|security|perf|opinion"],
  "affected_stack": ["string"],
  "context_similarity": 0.0,
  "novelty_score": 0.0,
  "impact_score": 0.0,
  "trust_score": 0.0,
  "noise_risk_score": 0.0,
  "execution_cost_score": 0.0,
  "score_total": 0.0,
  "suggested_action": "discard|hint|deep_read|action",
  "trigger_reason": ["string"],
  "requires_user_confirm": true,
  "security_gate": "pass|review|block",
  "trace_id": "string"
}
```

## 5. 权限与安全边界（本地执行）
- 中央系统不直接操作本地代码仓库，仅发起“候选与建议动作”。
- 本地 Codex/Claude Code 在用户机器执行，默认最小权限：
  - 只读模式优先
  - 写操作需显式确认
  - 外网访问按域名白名单
  - 凭证从本地密钥管理读取，不回传中央系统
- MCP 仅做协议桥接与工具暴露，不承担策略决策。
- 所有深读/落动作写入审计日志：`who/when/why/what changed`。

## 6. 组件职责划分
- Workato：事件编排、连接器集成、流程调度、告警回流
- MCP：标准化工具调用与上下文传递桥梁
- 本地 skill（Codex/Claude Code）：深读、代码级验证、变更执行
- 中央决策层：评分、阈值决策、可视化、反馈学习

## 7. Demo 场景（MVP 必做）
1. A 类触发深读：官方 release note -> 对当前项目生成影响分析 -> 输出改造任务。
2. B 类助推 A 类：白名单推文提高 A 类候选优先级 -> 仍由 A 类证据触发深读。
3. 安全门禁拦截：高分候选因权限风险被阻断，展示审计链路与人工确认。

## 8. MVP 范围控制
保留：
- A/B 双类输入
- 评分与阈值
- 三层动作
- 本地执行门禁与审计
- 三个 demo 端到端链路

砍掉（延期）：
- 自动个性化重排模型（先规则 + 轻量反馈）
- 多目标强化学习
- 跨团队协同工作流
- 复杂知识图谱构建
- 全自动代码提交（MVP 仅到建议 PR 草稿）

## 9. 开发前置约束文档
- `decision-table.md`
- `security-contract.md`
- `demo-rubric.md`

说明：
- 开发实现必须遵循以上三份约束文档。
- 若实现与约束冲突，以约束文档为准并回写 PRD。
