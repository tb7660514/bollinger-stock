import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="布林线 Bollinger Bands", layout="wide")
st.title("📈 布林线工具")

symbol = st.text_input("股票代码（美股如 AAPL）", value="AAPL")
period = st.selectbox("时间范围", ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","max"], index=5)
interval = st.selectbox("K线周期", ["1m","2m","5m","15m","30m","60m","90m","1d","5d","1wk","1mo"], index=7)
n = st.slider("布林周期", min_value=5, max_value=50, value=20)
std_num = st.slider("标准差倍数", min_value=1.0, max_value=3.0, value=2.0, step=0.1)

@st.cache_data
def get_data(sym, p, i):
    # 关键：multi_level_index=False，关掉双层列
    df = yf.download(
        tickers=sym,
        period=p,
        interval=i,
        progress=False,
        multi_level_index=False
    )
    if df.empty:
        return df
    df["MA"] = df["Close"].rolling(n).mean()
    df["STD"] = df["Close"].rolling(n).std()
    df["Upper"] = df["MA"] + std_num * df["STD"]
    df["Lower"] = df["MA"] - std_num * df["STD"]
    return df

df = get_data(symbol, period, interval)

if df.empty:
    st.error("获取行情失败！代码不对，或是 Yahoo Finance 拉取不到数据。")
else:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="K线"
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df["Upper"], line=dict(color="#ff4444"), name="上轨"))
    fig.add_trace(go.Scatter(x=df.index, y=df["MA"], line=dict(color="#ffaa00"), name="中轨"))
    fig.add_trace(go.Scatter(x=df.index, y=df["Lower"], line=dict(color="#00bb44"), name="下轨"))
    fig.update_layout(height=620)
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("最新行情")
    st.dataframe(df.tail(20))
