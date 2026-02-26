# 量化分析平台 AI 自动研究迭代工作流规范 (agents.md)

为了实现极速、低门槛的量化策略迭代，本项目强制采用以下技术选型与规范：

## 一、 核心技术栈
1. **环境与包管理**: `uv` (纯粹、极速的 Python 环境工具)
2. **交互式 Web 面板**: `streamlit` (无需编写前端代码，实现参数调优实时反馈)
3. **数据加工与存储引擎**: `duckdb` (极高的查询性能，推荐存储格式: `.parquet`)
4. **金融数据源**: `akshare` (获取 A 股/美股/ETF 等市场数据)
5. **专业 K 线渲染**: `lightweight-charts` (由 TradingView 开源的核心图表渲染引擎)
6. **数据处理**: `pandas`, `numpy`

## 二、 目录结构约定
- `/app.py`：Streamlit 入口文件。**切勿把所有逻辑都堆在这里**。这里只处理 UI。
- `/data/`：存储下载下来的历史 K 线数据，应优先存为 `Parquet` 文件。
- `/strategies/`：各类量化策略的计算逻辑放入此地。
- `/utils/`：存放获取数据、连接数据库等公用模块。

## 三、 开发准则与纪律 (针对 AI 代码生成)
1. **避免死循环请求**：AkShare 获取数据可能存在限流或网络延迟。必须将其封装，实现**本地缓存/复用** (基于 DuckDB 或本地文件)。绝对不允许每次调整 Streamlit 参数都去重新下载一遍历史数据！
2. **拒绝低效遍历**：计算均线、MACD、RSI 等金融指标时，**强制使用 Pandas 的向量化计算** (如 `rolling().mean()`) 或 DuckDB 的 SQL 原生处理，**禁止**写 `for` 循环遍历 K 线数据。
3. **图表性能要求**：展现股票趋势、买卖信号的主图，**必须**使用 `lightweight-charts` 集成到 Streamlit 中，而非缓慢且无法顺滑拖拽的 Matplotlib。
4. **增量开发**：每次更新策略时，仅改动相应的逻辑文件，不推倒重来，借助 Streamlit 的 hot-reload 实现秒级调试体验。

## 四、 启动指令
```bash
# 激活环境
source .venv/bin/activate
# 启动面板
streamlit run app.py
```
