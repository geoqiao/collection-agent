# Project TODO

> 记录项目后续优化方向，按优先级排序。

---

## P1: 前端完善

### 页面布局/交互优化
- [ ] 优化三栏布局（配置/对话/调试）的响应式适配
- [ ] 对话面板增加时间戳和意图标签
- [ ] 调试面板增加 collapsible sections（展开/折叠）
- [ ] 添加消息气泡的视觉层次（不同颜色区分 Agent/用户/系统）
- [ ] 输入框增加快捷指令（"/stop", "/escalate" 等）

### 移动端适配
- [ ] 三栏布局在移动端改为抽屉式导航
- [ ] 对话面板全屏显示
- [ ] 触摸友好的按钮尺寸
- [ ] 输入框固定在底部

### 状态可视化增强
- [ ] 会话状态机图形化展示（normal → stopped 的流转图）
- [ ] 意图置信度仪表盘
- [ ] 协商轮数进度条
- [ ] 对话情感趋势图（情绪变化曲线）
- [ ] 工具调用链可视化（query_bill → record_promise → reply）

---

## P2: 文档完善

### README 架构说明
- [ ] 补充新版架构图（Harness → Decide → Execute）
- [ ] 添加 Skill 系统说明（Markdown 配置 + ReAct 执行）
- [ ] 添加状态机说明（流动态 vs 单向门）
- [ ] 添加前端截图/GIF

### API 文档
- [ ] REST API 端点说明（/api/users, /api/events）
- [ ] WebSocket 协议说明
- [ ] 请求/响应示例
- [ ] 错误码定义

### 部署指南
- [ ] uv 本地开发环境搭建
- [ ] 配置说明（config.yaml 各字段）
- [ ] LLM Provider 配置（DeepSeek/Claude/OpenAI）
- [ ] 前端服务启动（uvicorn）

---

## P3: 功能增强

### 批量用户管理
- [ ] CSV 导入用户列表
- [ ] 批量触发催收
- [ ] 用户状态批量查看

### 对话导出
- [ ] 导出单用户对话为 JSON
- [ ] 导出对话为 PDF 报告
- [ ] 对话回放功能

### A/B 测试框架
- [ ] Skill 版本对比（A/B Skill）
- [ ] 话术效果统计（回复率、还款率）
- [ ] 指标看板

---

## P4: 测试补充

### 前端 E2E 测试
- [ ] Playwright 测试：创建用户 → 触发催收 → 模拟对话 → 验证状态
- [ ] 测试 WebSocket 消息实时推送
- [ ] 测试移动端响应式布局

### WebSocket 测试
- [ ] 多客户端同时连接同一用户
- [ ] 连接断开重连
- [ ] 消息广播隔离性（用户A看不到用户B的消息）

### 边界 case
- [ ] LLM 超时/错误 fallback
- [ ] 并发事件处理
- [ ] 状态机非法流转（locked 状态试图回退）
- [ ] Skill 步数耗尽 fallback

---

## P5: 工程化

### Docker 部署
- [ ] Dockerfile（multi-stage build）
- [ ] docker-compose.yml（app + nginx）
- [ ] 生产环境配置（uvicorn workers, gunicorn）

### CI/CD
- [ ] GitHub Actions：pytest + ruff + mypy
- [ ] 自动部署到 Render/Vercel/自有服务器
- [ ] 代码覆盖率报告（codecov）

### 代码覆盖率
- [ ] 当前覆盖率基线
- [ ] 目标：核心模块 > 90%
- [ ] 集成覆盖率工具到 CI

---

## 附：技术债务

- [ ] `TODO` 标注清理（harness.py quota check）
- [ ] 废弃的 legacy 代码确认删除（test_integration.py 已删，检查其他）
- [ ] Prompt 版本管理（当前用文件系统，考虑版本号）
- [ ] 日志系统（当前只有 print，需要结构化日志）
