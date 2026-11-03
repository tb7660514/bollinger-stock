import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf

st.set_page_config(page_title="布林线看盘", layout="wide")
st.title("布林线 A 股简易看盘工具")

symbol = st.text_input("股票代码", value="000001.SZ")
period = st.selectbox("周期", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
interval = st.selectbox("K线间隔", ["1h", "1d"])

@st.cache_data
def get_data(sym, p, i):
    df = yf.download(sym, period=p, interval=i, progress=False)
    if df.empty:
        return df
    win = 20
    df["mid"] = df["Close"].rolling(win).mean()
    std = df["Close"].rolling(win).std()
    df["upper"] = df["mid"] + 2 * std
    df["lower"] = df["mid"] - 2 * std
    return df

data = get_data(symbol, period, interval)
if data.empty:
    st.error("获取行情失败，请检查代码或者网络")
else:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data["Close"], name="收盘价"))
    fig.add_trace(go.Scatter(x=data.index, y=data["upper"], name="上轨", line=dict(dash="dot")))
    fig.add_trace(go.Scatter(x=data.index, y=data["mid"], name="MA20 中轨"))
    fig.add_trace(go.Scatter(x=data.index, y=data["lower"], name="下轨", line=dict(dash="dot")))
    fig.update_layout(height=620)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("本程序仅用于指标原理学习，不构成任何投资建议。")
