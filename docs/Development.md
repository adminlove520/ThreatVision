# CyberSentinel AI 开发报告

## 1. 项目概述
CyberSentinel AI 是一个自动化的安全监控与 AI 分析系统。它旨在实时监控 GitHub 上的 CVE 漏洞信息和安全相关的开源项目，利用大语言模型（OpenAI GPT 和 Google Gemini）对收集到的数据进行深度分析，评估风险等级，并自动生成安全简报。

## 2. 系统架构
本系统采用模块化设计，主要包含以下核心组件：

### 2.1 核心模块
*   **监控模块 (Monitors)**:
    *   `CVEMonitor`: 专门负责监控 CVE 相关的仓库。通过 GitHub Search API 定期搜索 `CVE-2024`, `CVE-2025` 等关键词。
    *   `GithubMonitor`: 负责监控特定的高价值仓库（Watched Repos）以及通用安全关键词。
*   **AI 分析模块 (AI Analyzer)**:
    *   `AIAnalyzer`: 封装了 OpenAI 和 Gemini 的 API 调用。实现了自动重试（Retry）和故障转移（Failover）机制。当 OpenAI 不可用时，自动切换至 Gemini。
*   **数据存储 (Database)**:
    *   使用 SQLite 数据库进行轻量级存储。
    *   `CVERecord`: 存储 CVE 编号、描述、发布时间、AI 分析结果等。
    *   `Repository`: 存储仓库元数据、星数、更新时间、AI 分析结果等。
*   **工具模块 (Utils)**:
    *   `ArticleFetcher`: 抓取外部安全文章（如微信公众号/技术博客）。
    *   `ArticleManager`: 管理文章去重、生成每日 Markdown 报告。
    *   `BlogManager`: 对接外部博客 API，实现自动发布。
    *   `Logger`: 统一的日志管理。

### 2.2 数据流向
1.  **采集**: Monitors 轮询 GitHub API -> 获取原始数据。
2.  **存储**: 原始数据存入 SQLite 数据库。
3.  **分析**: 异步线程池触发 AI 分析 -> 调用 LLM 生成 JSON 格式分析报告 -> 更新数据库。
4.  **报告**: 每日定时任务 -> 读取高价值数据 -> 生成 Markdown 报告 -> 发布博客。

## 3. 关键技术实现

### 3.1 鲁棒的 API 交互
*   **GitHub Token 轮换**: `CVEMonitor` 和 `GithubMonitor` 支持配置多个 Token。当遇到 403 Rate Limit 错误时，自动切换到下一个 Token，确保监控不中断。
*   **AI 服务高可用**: 使用 `tenacity` 库实现了指数退避重试。在 `_call_openai` 失败后，自动降级调用 `_call_gemini`，保证分析任务的完成率。

### 3.2 异步并发处理
*   系统使用 `ThreadPoolExecutor` (线程池) 来处理耗时的 AI 分析任务。监控线程只负责快速抓取和入库，分析任务异步执行，避免阻塞主监控循环。

### 3.3 结构化输出
*   通过 Prompt Engineering 强制要求 LLM 输出 JSON 格式数据。
*   实现了 `_validate_json` 方法，确保 AI 返回的数据可以被程序正确解析和存储。

## 4. 遇到的挑战与解决方案

### 4.1 GitHub API 速率限制
*   **问题**: 频繁搜索会导致 403 错误。
*   **解决**: 实现了 Token 轮换池，并在请求间增加随机延时。

### 4.2 AI 输出不稳定性
*   **问题**: LLM 有时会输出非 JSON 格式的闲聊内容。
*   **解决**: 在 Prompt 中明确约束 "Output strictly valid JSON"，并在代码中增加 JSON 解析的容错处理（尝试从 Markdown 代码块中提取 JSON）。

## 5. 总结与展望
目前系统已完成了核心的监控、分析和报告功能。未来可考虑：
*   增加 Web 前端界面，用于直观展示监控数据。
*   集成更多的威胁情报源（如 NVD, Exploit-DB）。
*   支持更多类型的通知渠道（如 Telegram, Slack, 钉钉）。
