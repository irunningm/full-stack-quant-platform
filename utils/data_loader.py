import akshare as ak
import pandas as pd
import duckdb
import os
from datetime import datetime

# 数据存储目录
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# --- 增强的 AkShare 请求机制 ---
import time
import requests

def fetch_data_with_retry(symbol: str, retries: int = 3, delay: int = 2) -> pd.DataFrame:
    """带重试机制的数据抓取"""
    for attempt in range(retries):
        try:
            # 去除可能带有的 sh/sz 前缀，很多 AkShare 的新方言接口只认 6 位数字
            clean_symbol = symbol.replace("sh", "").replace("sz", "")
            
            # 首选：新浪财经 A 股前复权接口 (相对稳定)
            df = ak.stock_zh_a_hist(symbol=clean_symbol, period="daily", start_date="19900101", end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq")
            
            if not df.empty:
                return df
                
        except requests.exceptions.ConnectionError as e:
            print(f"⚠️ [尝试 {attempt+1}/{retries}] 连接被拒绝或中断: {e}")
            time.sleep(delay)
        except Exception as e:
            print(f"⚠️ [尝试 {attempt+1}/{retries}] 发生未知错误: {e}")
            time.sleep(delay)
            
    print(f"❌ 警告：经过 {retries} 次尝试，仍未获取到 {symbol} 的数据。")
    return pd.DataFrame()

def get_a_share_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取 A 股历史日线数据，并使用 DuckDB + Parquet 缓存
    """
    # 将日期格式统一为 YYYYMMDD，适配 AkShare 接口
    ak_start = start_date.replace("-", "")
    ak_end = end_date.replace("-", "")
    
    # 强制清理股票代码供文件名使用（去除特殊字符）
    clean_symbol = symbol.replace("sh", "").replace("sz", "")
    file_path = os.path.join(DATA_DIR, f"A_{clean_symbol}_daily.parquet")
    
    # 策略 1：检查本地是否已有 Parquet 缓存
    if os.path.exists(file_path):
        print(f"📦 [A股:{clean_symbol}] 发现本地缓存，正在使用 DuckDB 极速加载...")
        conn = duckdb.connect()
        query = f"SELECT * FROM '{file_path}'"
        df = conn.execute(query).df()
        
        df['日期'] = pd.to_datetime(df['日期'])
        mask = (df['日期'] >= pd.to_datetime(start_date)) & (df['日期'] <= pd.to_datetime(end_date))
        filtered_df = df.loc[mask].copy()
        
        if not filtered_df.empty:
            return filtered_df
        else:
            print(f"⚠️ [A股:{clean_symbol}] 缓存数据未能覆盖请求的时间段，准备重新网络拉取...")

    # 策略 2：本地没有缓存，使用重试机制从网络拉取
    print(f"🌐 [A股:{clean_symbol}] 正在从网络接口下载历史数据...")
    df = fetch_data_with_retry(clean_symbol)
    
    if df.empty:
        return pd.DataFrame()
        
    try:
        print(f"✅ [A股:{clean_symbol}] 数据下载完成，共 {len(df)} 条，正在写入 Parquet 缓存。")
        df['日期'] = pd.to_datetime(df['日期'])
        conn = duckdb.connect()
        conn.execute(f"COPY (SELECT * FROM df) TO '{file_path}' (FORMAT PARQUET)")
        
        mask = (df['日期'] >= pd.to_datetime(start_date)) & (df['日期'] <= pd.to_datetime(end_date))
        return df.loc[mask]

    except Exception as e:
        print(f"❌ ERROR: [A股]缓存数据时发生错误：{e}")
        return pd.DataFrame()


# --- 新增：美股市场抓取模块 (基于 yfinance) ---
import yfinance as yf

def get_us_share_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取 美股 历史日线数据 (yfinance)，并转换为与 A股 对齐的格式后缓存为 Parquet。
    """
    clean_symbol = symbol.upper()
    file_path = os.path.join(DATA_DIR, f"US_{clean_symbol}_daily.parquet")
    
    # 策略 1：查询本地 DuckDB 缓存
    if os.path.exists(file_path):
        print(f"📦 [美股:{clean_symbol}] 发现本地缓存，正在加载...")
        conn = duckdb.connect()
        df = conn.execute(f"SELECT * FROM '{file_path}'").df()
        df['日期'] = pd.to_datetime(df['日期'])
        mask = (df['日期'] >= pd.to_datetime(start_date)) & (df['日期'] >= pd.to_datetime(start_date)) & (df['日期'] <= pd.to_datetime(end_date))
        filtered_df = df.loc[mask].copy()
        if not filtered_df.empty:
            return filtered_df
            
    # 策略 2：通过 yfinance 从全球网络获取（速度快，无限制）
    print(f"🌐 [美股:{clean_symbol}] 正在通过 yfinance 下载历史数据...")
    try:
        # 美股通常直接获取上市以来的最大值 (period="max") 用作未来缓存
        # 为提高速度，我们抓取近 10 年即可
        raw_df = yf.download(clean_symbol, period="10y", progress=False)
        
        if raw_df.empty:
            print(f"❌ 警告：未获取到美股代码 [{clean_symbol}] 的数据。请检查代码 (如 AAPL, TSLA, MSFT)。")
            return pd.DataFrame()
            
        print(f"✅ [美股:{clean_symbol}] 数据下载成功，正在清洗并写入缓存...")
        
        # 清洗列名：将多级表头拍平，只保留第一个级别
        if isinstance(raw_df.columns, pd.MultiIndex):
            raw_df.columns = raw_df.columns.get_level_values(0)
            
        raw_df = raw_df.reset_index()
        
        # 将 yfinance 的英文标准列名映射成咱们约定的中文统一格式
        rename_map = {
            'Date': '日期',
            'Open': '开盘',
            'High': '最高',
            'Low': '最低',
            'Close': '收盘',
            'Volume': '成交量'
        }
        df = raw_df.rename(columns=rename_map)
        
        # 仅保留核心列
        cols_to_keep = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
        # 兜底：如果某些数据少列
        cols_exist = [c for c in cols_to_keep if c in df.columns]
        df = df[cols_exist].copy()
        
        # 去除时区信息以便跨平台存入 Parquet
        if df['日期'].dt.tz is not None:
             df['日期'] = df['日期'].dt.tz_localize(None)
        
        # 落盘缓存
        conn = duckdb.connect()
        conn.execute(f"COPY (SELECT * FROM df) TO '{file_path}' (FORMAT PARQUET)")
        
        # 返回截取段
        mask = (df['日期'] >= pd.to_datetime(start_date)) & (df['日期'] <= pd.to_datetime(end_date))
        return df.loc[mask]
        
    except Exception as e:
        print(f"❌ ERROR: 获取美股时发生错误：{e}")
        return pd.DataFrame()


# 本地测试代码 (当直接运行此脚本时触发)
if __name__ == "__main__":
    # 测试拉取茅台(600519)的 2023 年数据
    test_symbol = "600519"
    print(f"🚀 开始测试获取 {test_symbol} 数据：")
    df_result = get_a_share_daily(test_symbol, "2023-01-01", "2023-12-31")
    if not df_result.empty:
         print(f"📊 成功截取数据 {len(df_result)} 条！前 3 条展示如下：")
         print(df_result.head(3))
