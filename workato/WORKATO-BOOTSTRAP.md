# Workato 环境脚手架（MVP）

## 0. 固定命名
- Project: `attention-decision-system-mvp`
- Prefix namespace: `proj_attention_decision_mvp`

资源命名：
- `tbl_project_snapshots`
- `tbl_candidates`
- `tbl_watchlist`
- `tbl_audit_events`
- `rcp_ingest_signals`
- `rcp_hint_and_action`
- `mcp_local_runtime_bridge`

## 1. Workspace 归档（团队共享）
- Workspace ID: `TODO_FILL`
- Workato 登录邮箱: `TODO_FILL`
- AI Hub 左侧入口截图: `output/screenshots/ai-hub-left-nav.png`
- MCP 入口截图（Set up an MCP server）: `output/screenshots/mcp-entry.png`
- 归档文档: `workato/workspace-archive.md`

## 2. Data Tables（最小字段）

### tbl_project_snapshots
- `project_id` (string)
- `snapshot_time` (datetime)
- `tech_stack` (text)
- `current_goals` (text)
- `open_problems` (text)
- `acceptance_signals` (text)
- `rejection_signals` (text)
- `risk_tolerance` (string)
- `trace_id` (string)

### tbl_candidates
- `candidate_id` (string)
- `source_class` (string)
- `source_type` (string)
- `evidence_grade` (string)
- `candidate_url` (string)
- `summary` (text)
- `context_similarity` (number)
- `noise_risk_score` (number)
- `suggested_action` (string)
- `security_gate` (string)
- `trace_id` (string)

### tbl_watchlist
- `item_id` (string)
- `candidate_id` (string)
- `project_id` (string)
- `note` (text)
- `created_at` (datetime)
- `created_by` (string)
- `trace_id` (string)

### tbl_audit_events
- `who` (string)
- `when` (datetime)
- `source` (string)
- `trigger_reason` (text)
- `files_accessed` (text)
- `action_taken` (string)
- `user_confirmed` (boolean)
- `trace_id` (string)

## 3. Recipes（空壳职责）

### rcp_ingest_signals
职责：
- 接收 GitHub / 官方更新候选
- 标准化字段
- 写入 `tbl_candidates`

禁止：
- 相关性评分
- 深读判断
- B 类加权逻辑

### rcp_hint_and_action
职责：
- 接收中央决策层 final decision
- decision=`hint` 时写提示事件
- decision=`action` 且用户确认后，只写 `tbl_watchlist` / note
- 同步写 `tbl_audit_events`

禁止：
- policy 再判断
- recipe 内算分
- 直接调用本地深读逻辑

## 4. MCP 入口检查
- AI Hub 可见: `TODO_FILL_TRUE_OR_FALSE`
- `Set up an MCP server` 可见: `TODO_FILL_TRUE_OR_FALSE`
- 模板/示例可见: `TODO_FILL_TRUE_OR_FALSE`

## 5. 责任边界（固定）
- Workato = orchestration only
- MCP = bridge only
- Local runtime (Codex/Claude Code) = deep read / local execution only

## 6. 官方入口（已归档）
- Docs: https://docs.workato.com/
- Support: https://support.workato.com/en/support/home
- Community: https://systematic.workato.com/
- Sandbox login: https://app.trial.workato.com/users/sign_in_trial

## 7. 交付口径（防跑偏）
- working prototype / demo
- 2-4 分钟视频
- 8 页以内 deck
- 发送到 `submissions-naisc@workato.com`
- deadline: 2026-04-24
