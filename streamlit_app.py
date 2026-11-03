import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="A股大盘布林线", layout="wide")
st.title("📈 A 股大盘 · 布林线")

symbol = st.text_input("代码（上证指数：000001.SH，深成指：399001.SZ）", value="000001.SH")
period_days = st.slider("取多少日数据", min_value=60, max_value=600, value=250)
n = st.slider("布林周期", min_value=5, max_value=50, value=20)
std_num = st.slider("标准差倍数", min_value=1.0, max_value=3.0, value=2.0, step=0.1)

@st.cache_data
def get_ak_data(code, days):
    df = ak.stock_zh_index_daily(symbol=code)
    df = df.tail(days).copy()
    df["MA"] = df["close"].rolling(n).mean()
    df["STD"] = df["close"].rolling(n).std()
    df["Upper"] = df["MA"] + std_num * df["STD"]
    df["Lower"] = df["MA"] - std_num * df["STD"]

    df["break_up"] = (df["close"] > df["Upper"]) & (df["close"].shift(1) <= df["Upper"].shift(1))
    df["break_down"] = (df["close"] < df["Lower"]) & (df["close"].shift(1) >= df["Lower"].shift(1))
    return df

df = get_ak_data(symbol, period_days)

if df.empty:
    st.error("获取 A 股行情失败！检查代码。")
else:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="K线"
    ))
    fig.add_trace(go.Scatter(x=df["date"], y=df["Upper"], line=dict(color="#ff4444"), name="上轨"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["MA"], line=dict(color="#ffaa00"), name="中轨"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["Lower"], line=dict(color="#00bb44"), name="下轨"))

    up = df[df["break_up"]]
    down = df[df["break_down"]]
    fig.add_trace(go.Scatter(
        x=up["date"], y=up["close"],
        mode="markers", marker=dict(symbol="triangle-up", color="red", size=10),
        name="向上突破"
    ))
    fig.add_trace(go.Scatter(
        x=down["date"], y=down["close"],
        mode="markers", marker=dict(symbol="triangle-down", color="green", size=10),
        name="向下突破"
    ))

    fig.update_layout(height=640)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("最近信号")
    sig = pd.concat([
        up[["date", "close"]].assign(signal="上轨突破"),
        down[["date", "close"]].assign(signal="下轨突破")
    ]).sort_values("date", ascending=False)
    st.dataframe(sig)

    st.subheader("最新行情")
    st.dataframe(df.tail(10)[["date", "open", "high", "low", "close", "MA", "Upper", "Lower"]])
