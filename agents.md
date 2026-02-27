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

## 五、 项目上下文与 AI 开发记忆 (Project AI Memory)
> 为了让未来的 AI 助手接手项目时不丢失当前上下文，请在每次重大更新后将架构变更记录于此。

### [v1.0] 起步核心奠基 (Streamlit + DuckDB + 原生 Pandas)
- **数据源之坑**：在开发 A 股数据时遭遇了 AkShare 的列名和冗余字段坑，已在 `data_loader.py` 使用统一中文标准字段 (`日期, 开盘, 最高, 最低, 收盘, 成交量`) 脱水清洗。在获取美股时因为 AkShare 不稳定经常 `Connection aborted`，已果断引入 `yfinance` 作多路补充。
- **渲染器之坑**：在直接使用原生代码包装 TradingView 的 JS 库时发生了日期解析错误和白屏，后改用官方维护的 `lightweight-charts`（Python 包内的 `StreamlitChart`），成功绘制主副图。需要画叠加均线时，`StreamlitChart.create_line(name="xxx")` 必须要求 DataFrame 中数据列必须和该 name 保持完全一致的命名，否则会报 `NameError`。
- **零延迟理念**：坚决贯彻两层机制保障极速投研体验。第一，所有获取下来的金融数据都会被转化为 `.parquet` 文件缓存在本地 `data/` 目录中，在面板点击测算时通过 **DuckDB** 快速查询复用，彻底消灭重复网络请求。第二，均线计算与盈亏模拟绝不使用 Python原生 `for` 循环，全部依靠 Pandas 的 `.cumprod()`、`.shift()` 向量化矩阵函数，使回测引擎可无感秒出结果。
- **交互规范**：当前前端控制台统一利用 Streamlit 左侧 Sidebar 提供入参调节。策略计算逻辑后续应从 `app.py` 中剥离以保持 UI 代码清爽。
