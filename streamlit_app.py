import streamlit as st
import pandas as pd
import yfinance as yf
import talib

st.set_page_config(page_title="布林线看盘", layout="wide")
st.title("布林线 A 股简易看盘工具")

symbol = st.text_input("股票代码", value="000001.SZ")
period = st.selectbox("周期", ["1d","5d","1mo","3mo","6mo","1y"])
interval = st.selectbox("K线间隔", ["1h","1d"])

@st.cache_data
def get_data(sym, p, i):
    df = yf.download(sym, period=p, interval=i)
    if df.empty:
        return df
    df["mid"] = talib.SMA(df["Close"], timeperiod=20)
    df["upper"], df["mid"], df["lower"] = talib.BBANDS(df["Close"], timeperiod=20, nbdevup=2, nbdevdn=2)
    return df

data = get_data(symbol, period, interval)
if data.empty:
    st.error("获取行情失败，请检查代码或者网络")
else:
    st.line_chart(data[["Close","upper","mid","lower"]])
    latest = data.iloc[-1]
    st.write(f"最新价：{latest['Close']:.2f}｜上轨：{latest['upper']:.2f}｜中轨：{latest['mid']:.2f}｜下轨：{latest['lower']:.2f}")
