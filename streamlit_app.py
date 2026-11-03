import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="布林条件选股器", layout="wide")
st.title("📊 布林带｜多条件组合选股")

with st.sidebar:
    st.header("参数")
    n = st.slider("布林周期", 5, 50, 20)
    std_k = st.slider("标准差倍数", 1.0, 3.0, 2.0, 0.1)
    near_tol = st.slider("贴近轨道阈值 %", 0.3, 5.0, 1.5, 0.1)
    bw_qtl = st.slider("盘整带宽分位", 0.05, 0.35, 0.20, 0.01)
    logic = st.radio("条件逻辑", ["全部满足 (AND)", "任一满足 (OR)"])

    st.divider()
    st.markdown("**勾选选股条件**")
    cond = {}
    cond["near_lower"] = st.checkbox("贴近下轨")
    cond["near_upper"] = st.checkbox("贴近上轨")
    cond["break_up"] = st.checkbox("向上突破上轨")
    cond["break_down"] = st.checkbox("向下跌破下轨")
    cond["band_squeeze"] = st.checkbox("带宽收缩（盘整）")
    cond["above_mid"] = st.checkbox("收于中轨之上")
    cond["below_mid"] = st.checkbox("收于中轨之下")
    cond["new_low_20"] = st.checkbox("20日新低")
    cond["new_high_20"] = st.checkbox("20日新高")

stock_text = st.text_area(
    "股票清单（一行一只）",
    value="""600519.SS
601318.SS
000001.SZ
300750.SZ
601899.SS
000858.SZ
600036.SS
002594.SZ""",
    height=180
)
stock_list = [s.strip() for s in stock_text.strip().splitlines() if s.strip()]


@st.cache_data
def calc_stock(symbol):
    df = yf.download(
        tickers=symbol,
        period="1y",
        interval="1d",
        progress=False,
        multi_level_index=False
    )
    if len(df) < n + 20:
        return None

    df["MA"] = df["Close"].rolling(n).mean()
    df["STD"] = df["Close"].rolling(n).std()
    df["Upper"] = df["MA"] + std_k * df["STD"]
    df["Lower"] = df["MA"] - std_k * df["STD"]
    df["BandWidth"] = (df["Upper"] - df["Lower"]) / df["MA"]

    df["break_up"] = (df["Close"] > df["Upper"]) & (df["Close"].shift(1) <= df["Upper"].shift(1))
    df["break_down"] = (df["Close"] < df["Lower"]) & (df["Close"].shift(1) >= df["Lower"].shift(1))

    df["low20"] = df["Close"].rolling(20).min()
    df["high20"] = df["Close"].rolling(20).max()

    last = df.iloc[-1]
    close = float(last["Close"])
    upper = float(last["Upper"])
    lower = float(last["Lower"])
    mid = float(last["MA"])
    bw = float(last["BandWidth"])

    pct_up = (upper - close) / close * 100
    pct_low = (close - lower) / close * 100

    hit = {}
    hit["near_lower"] = abs(pct_low) <= near_tol
    hit["near_upper"] = abs(pct_up) <= near_tol
    hit["break_up"] = bool(last["break_up"])
    hit["break_down"] = bool(last["break_down"])
    hit["band_squeeze"] = bw < float(df["BandWidth"].quantile(bw_qtl))
    hit["above_mid"] = close > mid
    hit["below_mid"] = close < mid
    hit["new_low_20"] = abs(close - float(last["low20"])) < 1e-6
    hit["new_high_20"] = abs(close - float(last["high20"])) < 1e-6

    signals = []
    if hit["near_lower"]:
        signals.append("贴近下轨")
    if hit["near_upper"]:
        signals.append("贴近上轨")
    if hit["break_up"]:
        signals.append("突破上轨")
    if hit["break_down"]:
        signals.append("跌破下轨")
    if hit["band_squeeze"]:
        signals.append("盘整收缩")
    if hit["above_mid"]:
        signals.append("站上中轨")
    if hit["below_mid"]:
        signals.append("跌破中轨")
    if hit["new_low_20"]:
        signals.append("20日新低")
    if hit["new_high_20"]:
        signals.append("20日新高")

    return {
        "code": symbol,
        "close": round(close, 2),
        "mid": round(mid, 2),
        "upper": round(upper, 2),
        "lower": round(lower, 2),
        "bandwidth": round(bw, 4),
        "signal": "｜".join(signals) if signals else "无信号",
        "hit": hit,
        "raw_df": df
    }


def match(row, conds, logic_and):
    selected = [k for k, v in conds.items() if v]
    if not selected:
        return True
    res = [row["hit"][k] for k in selected]
    if logic_and:
        return all(res)
    else:
        return any(res)


if st.button("🚀 开始扫描选股", type="primary"):
    all_res = []
    bar = st.progress(0)
    total = len(stock_list)
    for i, code in enumerate(stock_list):
        r = calc_stock(code)
        if r:
            all_res.append(r)
        bar.progress((i + 1) / total)

    if not all_res:
        st.error("没有拉取到行情，请检查代码或者稍后重试")
    else:
        and_mode = (logic == "全部满足 (AND)")
        filtered = [x for x in all_res if match(x, cond, and_mode)]

        st.subheader(f"筛选结果：{len(filtered)} 只标的")
        table = pd.DataFrame([
            {k: v for k, v in x.items() if k not in ("hit", "raw_df")}
            for x in filtered
        ])
        st.dataframe(table, use_container_width=True)

        st.subheader("查看 K 线布林图")
        if filtered:
            sel_code = st.selectbox("选择标的", [r["code"] for r in filtered])
            target = next(r for r in filtered if r["code"] == sel_code)
            df_chart = target["raw_df"]

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df_chart.index,
                open=df_chart["Open"],
                high=df_chart["High"],
                low=df_chart["Low"],
                close=df_chart["Close"],
                name="K线"
            ))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["Upper"], line=dict(color="#ff4444"), name="上轨"))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MA"], line=dict(color="#ffaa00"), name="中轨"))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["Lower"], line=dict(color="#00bb44"), name="下轨"))

            up_pt = df_chart[df_chart["break_up"]]
            down_pt = df_chart[df_chart["break_down"]]
            fig.add_trace(go.Scatter(
                x=up_pt.index, y=up_pt["Close"],
                mode="markers", marker=dict(symbol="triangle-up", color="red", size=11),
                name="突破上轨"
            ))
            fig.add_trace(go.Scatter(
                x=down_pt.index, y=down_pt["Close"],
                mode="markers", marker=dict(symbol="triangle-down", color="green", size=11),
                name="跌破下轨"
            ))
            fig.update_layout(height=620)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("当前条件没有选出标的，可以放宽条件")

st.caption("⚠️ 工具仅行情可视化，信号不构成任何投资建议")
