import streamlit as st
import pandas as pd
import duckdb

# --- 页面配置 ---
st.set_page_config(
    page_title="AI 量化投研平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 侧边栏 ---
with st.sidebar:
    st.header("🎛️ 投研控制面板")
    
    # 获取市场类型与对应标识代码
    market_type = st.radio("选择市场", options=["A股 (AkShare)", "美股 (yfinance)"], horizontal=True)
    default_symbol = "000001" if "A股" in market_type else "TSLA"
    symbol = st.text_input("股票代码", value=default_symbol, help="A股直接输6位数字，美股输代码如 AAPL, TSLA")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", pd.to_datetime("2023-01-01"))
    with col2:
        end_date = st.date_input("结束日期", pd.to_datetime("2024-01-01"))
        
    st.markdown("---")
    st.subheader("💡 量化策略调优区")
    strategy_type = st.selectbox("选择测试策略", options=["经典双均线策略", "进阶 MACD + RSI 震荡策略"])
    
    # 动态渲染炼丹（参数调优）滑块
    strategy_params = {}
    if "双均线" in strategy_type:
        st.caption("均线周期设置 (天)")
        strategy_params['ma_short'] = st.slider("短线周期 (快线)", 1, 30, 5)
        strategy_params['ma_long'] = st.slider("长线周期 (慢线)", 10, 200, 20)
    elif "MACD" in strategy_type:
        st.caption("MACD 趋势周期设置")
        mac_col1, mac_col2 = st.columns(2)
        with mac_col1:
            strategy_params['macd_fast'] = st.slider("MACD 快线", 1, 50, 12, key="mf")
        with mac_col2:
            strategy_params['macd_slow'] = st.slider("MACD 慢线", 1, 100, 26, key="ms")
            
        st.caption("RSI 震荡与超买/超卖设置")
        strategy_params['rsi_period'] = st.slider("RSI 判断周期", 2, 30, 14)
        rsi_col1, rsi_col2 = st.columns(2)
        with rsi_col1:
            strategy_params['rsi_overbought'] = st.slider("超买界限(做空区)", 50, 95, 70)
        with rsi_col2:
            strategy_params['rsi_oversold'] = st.slider("超卖界限(做多区)", 5, 50, 30)

    st.markdown("---")
    submit_btn = st.button("开始投研分析", use_container_width=True, type="primary")

# --- 主页面 ---
st.title("📈 AI 极速量化投研平台")
st.markdown("欢迎使用基于 `Streamlit` + `uv` + `DuckDB` + `Lightweight Charts` 打造的现代量化开发环境。")

# --- 核心逻辑 ---
from utils.data_loader import get_a_share_daily, get_us_share_daily

# 当用户点击侧边栏的按钮时触发
if submit_btn:
    with st.spinner(f"正在获取 {symbol} 的 {market_type} 历史数据，请稍候..."):
        # 将 date 对象转为字符串格式
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # 调用核心获取函数
        if "A股" in market_type:
            df = get_a_share_daily(symbol, start_str, end_str)
        else:
            df = get_us_share_daily(symbol, start_str, end_str)
        
        if df.empty:
            st.error(f"❌ 未能获取到股票代码为 {symbol} 的数据。请检查代码是否正确（例如：贵州茅台是 600519）。")
        else:
            st.success(f"✅ 数据加载成功！共获取 {len(df)} 个交易日数据。")
            
            # 计算简单的统计信息
            st.subheader("💡 基础统计信息")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("区间起始价", f"{df['开盘'].iloc[0]:.2f}")
            with col2:
                st.metric("区间最新价", f"{df['收盘'].iloc[-1]:.2f}")
            with col3:
                change = df['收盘'].iloc[-1] - df['开盘'].iloc[0]
                pct = (change / df['开盘'].iloc[0]) * 100
                st.metric("区间涨幅", f"{pct:.2f}%", f"{change:.2f}")
            with col4:
                st.metric("期间最高价", f"{df['最高'].max():.2f}")
                
            # 准备画图数据，转换 Pandas 列名
            chart_df = df.copy()
            chart_df = chart_df.rename(columns={
                '日期': 'time',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            })
            chart_df['time'] = pd.to_datetime(chart_df['time'])
            
            # --- 核心量化策略实现 ---
            
            markers = []
            
            if "双均线" in strategy_type:
                # 提取参数
                ma_short_period = strategy_params['ma_short']
                ma_long_period = strategy_params['ma_long']
                
                chart_df['MA_Short'] = chart_df['close'].rolling(window=ma_short_period).mean()
                chart_df['MA_Long'] = chart_df['close'].rolling(window=ma_long_period).mean()
                
                # --- 寻找买卖点 (金叉/死叉) 并在图表上打 Tag ---
                chart_df['prev_MA_Short'] = chart_df['MA_Short'].shift(1)
                chart_df['prev_MA_Long'] = chart_df['MA_Long'].shift(1)
                
                golden_cross = chart_df[(chart_df['prev_MA_Short'] < chart_df['prev_MA_Long']) & (chart_df['MA_Short'] > chart_df['MA_Long'])]
                death_cross = chart_df[(chart_df['prev_MA_Short'] > chart_df['prev_MA_Long']) & (chart_df['MA_Short'] < chart_df['MA_Long'])]
                
                for _, row in golden_cross.iterrows():
                    markers.append({
                        "time": row['time'].strftime('%Y-%m-%d'),
                        "position": "below",
                        "shape": "arrow_up",
                        "color": "#ef5350",
                        "text": "买入(金叉)"
                    })
                    
                for _, row in death_cross.iterrows():
                    markers.append({
                        "time": row['time'].strftime('%Y-%m-%d'),
                        "position": "above",
                        "shape": "arrow_down",
                        "color": "#26a69a",
                        "text": "卖出(死叉)"
                    })
                    
                # 信号生成: 快线大于慢线时持仓
                chart_df['Signal'] = 0
                chart_df.loc[chart_df['MA_Short'] > chart_df['MA_Long'], 'Signal'] = 1
                
            elif "MACD" in strategy_type:
                # 提取 MACD 参数
                fast = strategy_params['macd_fast']
                slow = strategy_params['macd_slow']
                signal_period = 9  # 默认平滑
                
                # 提取 RSI 参数
                rsi_p = strategy_params['rsi_period']
                rsi_overbought = strategy_params['rsi_overbought']
                rsi_oversold = strategy_params['rsi_oversold']
                
                # 计算 MACD
                exp1 = chart_df['close'].ewm(span=fast, adjust=False).mean()
                exp2 = chart_df['close'].ewm(span=slow, adjust=False).mean()
                chart_df['DIF'] = exp1 - exp2
                chart_df['DEA'] = chart_df['DIF'].ewm(span=signal_period, adjust=False).mean()
                chart_df['MACD'] = 2 * (chart_df['DIF'] - chart_df['DEA'])
                
                # 计算 RSI
                delta = chart_df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
                rs = gain / loss
                chart_df['RSI'] = 100 - (100 / (1 + rs))
                
                # 买卖点逻辑：RSI 从超卖区回升（前一天<=oversold，今天>oversold） 或 MACD 金叉 (且RSI不能在超买区)
                chart_df['prev_RSI'] = chart_df['RSI'].shift(1)
                chart_df['prev_DIF'] = chart_df['DIF'].shift(1)
                chart_df['prev_DEA'] = chart_df['DEA'].shift(1)
                
                # 买入条件：MACD金叉，且非超买
                buy_cond = (chart_df['prev_DIF'] < chart_df['prev_DEA']) & (chart_df['DIF'] > chart_df['DEA']) & (chart_df['RSI'] < rsi_overbought)
                # 卖出条件：MACD死叉，或者 RSI 极度超买断头铡
                sell_cond = ((chart_df['prev_DIF'] > chart_df['prev_DEA']) & (chart_df['DIF'] < chart_df['DEA'])) | ((chart_df['prev_RSI'] >= rsi_overbought) & (chart_df['RSI'] < rsi_overbought))
                
                buy_points = chart_df[buy_cond]
                sell_points = chart_df[sell_cond]
                
                for _, row in buy_points.iterrows():
                    markers.append({"time": row['time'].strftime('%Y-%m-%d'), "position": "below", "shape": "arrow_up", "color": "#ef5350", "text": "买入(趋势启动)"})
                for _, row in sell_points.iterrows():
                    markers.append({"time": row['time'].strftime('%Y-%m-%d'), "position": "above", "shape": "arrow_down", "color": "#26a69a", "text": "卖出(离场)"})
                
                # 信号生成：使用前值填充状态机
                chart_df['Signal'] = 0
                chart_df.loc[buy_cond, 'Signal'] = 1
                chart_df.loc[sell_cond, 'Signal'] = -1
                # 将信号 1 和 -1 铺满期间，遇到 1 买入，遇到 -1 卖出，期间持仓不变
                chart_df['Signal'] = chart_df['Signal'].replace(0, pd.NA).ffill().fillna(-1)
                chart_df['Signal'] = chart_df['Signal'].apply(lambda x: 1 if x == 1 else 0)
            
            # 延后 1 天交易（避免用到未来函数）
            chart_df['Signal'] = chart_df['Signal'].shift(1).fillna(0)
            
            # --- 构建专业的交互式 K 线图 ---
            st.subheader(f"📈 股票历史走势分析 ({strategy_type})")
            
            from lightweight_charts.widgets import StreamlitChart
            
            # 初始化图表
            chart = StreamlitChart(height=500)
            chart.layout(background_color='#131722', text_color='white')
            chart.grid(vert_enabled=True, horz_enabled=True, color='rgba(42, 46, 57, 0.5)')
            chart.candle_style(up_color='#ef5350', down_color='#26a69a', wick_up_color='#ef5350', wick_down_color='#26a69a', border_visible=False)
            chart.volume_config(scale_margin_top=0.8, scale_margin_bottom=0, up_color='#ef5350', down_color='#26a69a')
            chart.set(chart_df)
            
            if "双均线" in strategy_type:
                ma_short_name = f"MA{ma_short_period}"
                ma_long_name = f"MA{ma_long_period}"
                
                ma_short_data = chart_df[['time', 'MA_Short']].dropna().rename(columns={'MA_Short': ma_short_name})
                ma_long_data = chart_df[['time', 'MA_Long']].dropna().rename(columns={'MA_Long': ma_long_name})
                
                line_short = chart.create_line(name=ma_short_name, color="rgba(255, 192, 0, 1.0)", width=2)
                line_short.set(ma_short_data)
                
                line_long = chart.create_line(name=ma_long_name, color="rgba(41, 98, 255, 1.0)", width=2)
                line_long.set(ma_long_data)

            # 打 Marker 并渲染
            chart.marker_list(markers)
            chart.load()
            
            # --- 渲染附图 MACD / RSI (如果是对应策略) ---
            if "MACD" in strategy_type:
                st.write("📊 **附图：MACD (趋势发现) & RSI (震荡辅助)**")
                # 因为 Lightweight in Streamlit 目前无法像 JS 那样直接添加独立附图窗口(pane)，
                # 我们利用 Streamlit 原生的图表展示这两个核心数值线作为下方的 Dashboard。
                
                macd_data = chart_df[['time', 'DIF', 'DEA', 'MACD']].set_index('time')
                st.line_chart(macd_data[['DIF', 'DEA']], color=["#ef5350", "#26a69a"], height=200)
                
                rsi_data = chart_df[['time', 'RSI']].set_index('time')
                st.area_chart(rsi_data, height=150, color="#FFC107")
            
            # --- 阶段四：构建极速自动化回测流水线 (Native Pandas 版) ---
            st.markdown("---")
            st.subheader(f"🤖 极速自动回测研究流水线 ({strategy_type})")
            
            # 2. 计算标的每日基准收益率 (Benchmark Return)
            chart_df['Daily_Return'] = chart_df['close'].pct_change().fillna(0)
            
            # 3. 计算策略每日收益率 (只有在持仓 signal=1 时才吃到当天的涨跌幅)
            chart_df['Strategy_Return'] = chart_df['Signal'] * chart_df['Daily_Return']
            
            # 4. 计算累计净值 (Cumulative Wealth)
            # 假设初始资金为 1 块钱
            chart_df['Cumulative_Benchmark'] = (1 + chart_df['Daily_Return']).cumprod()
            chart_df['Cumulative_Strategy'] = (1 + chart_df['Strategy_Return']).cumprod()
            
            # 5. 绩效统计指标
            total_strategy_return = (chart_df['Cumulative_Strategy'].iloc[-1] - 1) * 100
            total_benchmark_return = (chart_df['Cumulative_Benchmark'].iloc[-1] - 1) * 100
            
            # 胜率计算：统计产生交易信号且吃到正收益的天数 / 持仓总天数
            holding_days = chart_df[chart_df['Signal'] == 1].shape[0]
            winning_days = chart_df[(chart_df['Signal'] == 1) & (chart_df['Strategy_Return'] > 0)].shape[0]
            win_rate = (winning_days / holding_days * 100) if holding_days > 0 else 0
            
            # 渲染回测面板的指标卡片
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(label="策略累计收益率", value=f"{total_strategy_return:.2f}%", 
                          delta=f"跑赢基准：{total_strategy_return - total_benchmark_return:.2f}%")
            with col2:
                st.metric(label="基准(一直持有)收益", value=f"{total_benchmark_return:.2f}%")
            with col3:
                st.metric(label="持仓天数", value=f"{holding_days} 天")
            with col4:
                st.metric(label="按日胜率", value=f"{win_rate:.2f}%")
                
            # 绘制资金净值曲线比对图
            st.write("📊 **策略净值 vs 基准净值 (1元起投)**")
            wealth_df = chart_df[['time', 'Cumulative_Strategy', 'Cumulative_Benchmark']].set_index('time')
            st.line_chart(wealth_df, color=["#ef5350", "#26a69a"])
            
            st.success("✅ **阶段四（自动化回测）与阶段三已全部通过原生 Pandas 流水线成功构建！**")

else:
    st.info("👈 请在左侧面板输入股票代码并点击【获取分析数据】。")
