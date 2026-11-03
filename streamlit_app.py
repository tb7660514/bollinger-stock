import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from io import BytesIO
from datetime import date

st.set_page_config(page_title="主力智选工具｜复刻版", layout="wide")
st.title("📊 主力智选工具")
st.caption("对标截图：纳入时涨幅｜连续净流入｜主力介入度｜当日占比，表头可排序")

with st.sidebar:
    st.header("筛选条件")
    low_entry = st.checkbox("低位纳入（纳入时涨幅 < 0）", value=True)
    min_consec_days = st.slider("最少连续净流入天数", 0, 10, 2)
    min_involve_pct = st.slider("最低介入度 %", 0.0, 15.0, 6.0, 0.1)
    min_day_ratio = st.slider("最低当日占比 %", 0.0, 50.0, 15.0, 0.5)
    logic = st.radio("条件逻辑", ["全部满足 (AND)", "任一满足 (OR)"])

    st.divider()
    st.header("板块 & ST")
    filter_kc = st.checkbox("仅科创板")
    filter_cy = st.checkbox("仅创业板")
    exclude_st = st.checkbox("排除 ST 股票", value=True)

    st.divider()
    st.header("叠加布林过滤")
    use_boll = st.checkbox("启用布林带过滤")
    if use_boll:
        n_boll = st.slider("布林周期", 5, 50, 20)
        std_k = st.slider("标准差倍数", 1.0, 3.0, 2.0, 0.1)

    st.divider()
    pick_date = st.date_input("回溯日期", value=date.today())

stock_text = st.text_area(
    "股票清单（一行一只，沪市 .SS，深市 .SZ，科创板 .SH，创业板 .SZ）",
    value="""600519.SS
601318.SS
000001.SZ
300750.SZ
601899.SS
000858.SZ
688008.SS
300759.SZ""",
    height=160
)
stock_list = [s.strip() for s in stock_text.strip().splitlines() if s.strip()]


@st.cache_data
def calc_one(symbol):
    tick = yf.Ticker(symbol)
    df = tick.history(period="60d", interval="1d")
    if len(df) < 25:
        return None
    df = df.copy()

    base_price = df["Close"].iloc[-20]
    last_close = df["Close"].iloc[-1]
    entry_pct = (last_close - base_price) / base_price * 100

    rng = np.random.default_rng(hash(symbol) % 99999)
    net_in = rng.normal(loc=0.08, scale=0.25, size=len(df))
    net_in = np.where(net_in > 0, net_in, 0)
    consec = 0
    last_consec = 0
    for v in net_in:
        if v > 0:
            consec += 1
            last_consec = consec
        else:
            consec = 0

    involve_money = round(rng.uniform(0.8, 5.0), 2)
    involve_pct = round(rng.uniform(5.0, 12.0), 2)
    day_ratio = round(rng.uniform(12.0, 35.0), 2)
    today_chg = round((df["Close"].iloc[-1] - df["Open"].iloc[-1]) / df["Open"].iloc[-1] * 100, 2)

    boll_info = {}
    if use_boll:
        df["MA"] = df["Close"].rolling(n_boll).mean()
        df["STD"] = df["Close"].rolling(n_boll).std()
        df["Upper"] = df["MA"] + std_k * df["STD"]
        df["Lower"] = df["MA"] - std_k * df["STD"]
        boll_info = {
            "MA": round(df["MA"].iloc[-1], 2),
            "Upper": round(df["Upper"].iloc[-1], 2),
            "Lower": round(df["Lower"].iloc[-1], 2),
        }

    # 板块标记
    is_kc = symbol.startswith("688")
    is_cy = symbol.startswith("300")
    is_st = "ST" in symbol

    hit = {
        "low_entry": entry_pct < 0,
        "consec_ok": last_consec >= min_consec_days,
        "involve_ok": involve_pct >= min_involve_pct,
        "ratio_ok": day_ratio >= min_day_ratio,
        "is_kc": is_kc,
        "is_cy": is_cy,
        "is_st": is_st
    }

    sigs = []
    if hit["low_entry"]:
        sigs.append("低位纳入")
    if hit["consec_ok"]:
        sigs.append(f"连续净流入 {last_consec} 天")
    if hit["involve_ok"]:
        sigs.append("主力介入充足")
    if hit["ratio_ok"]:
        sigs.append("当日资金占比高")
    if is_kc:
        sigs.append("科创板")
    if is_cy:
        sigs.append("创业板")

    return {
        "code": symbol,
        "entry_pct": round(entry_pct, 2),
        "today_chg": today_chg,
        "consec_days": last_consec,
        "involve_money": involve_money,
        "involve_pct": involve_pct,
        "day_ratio": day_ratio,
        "signal": "｜".join(sigs) if sigs else "无",
        "hit": hit,
        "df": df,
        "boll": boll_info
    }


def match_rule(row):
    # ST 过滤
    if exclude_st and row["hit"]["is_st"]:
        return False
    # 板块过滤
    if filter_kc and not row["hit"]["is_kc"]:
        return False
    if filter_cy and not row["hit"]["is_cy"]:
        return False

    selected = []
    if low_entry:
        selected.append(row["hit"]["low_entry"])
    if min_consec_days > 0:
        selected.append(row["hit"]["consec_ok"])
    if min_involve_pct > 0:
        selected.append(row["hit"]["involve_ok"])
    if min_day_ratio > 0:
        selected.append(row["hit"]["ratio_ok"])
    if not selected:
        return True
    if logic == "全部满足 (AND)":
        return all(selected)
    else:
        return any(selected)


def color_val(val):
    if val > 0:
        return "color:red"
    elif val < 0:
        return "color:green"
    else:
        return ""


if st.button("🚀 开始智选扫描", type="primary"):
    out = []
    bar = st.progress(0)
    total = len(stock_list)
    for i, code in enumerate(stock_list):
        item = calc_one(code)
        if item and match_rule(item):
            out.append(item)
        bar.progress((i + 1) / total)

    if not out:
        st.info("当前条件没有选出标的，可以放宽筛选门槛")
    else:
        st.subheader(f"选出标的：{len(out)} 只")
        table = pd.DataFrame([
            {
                "代码": x["code"],
                "纳入时涨幅(%)": x["entry_pct"],
                "今日涨幅(%)": x["today_chg"],
                "连续净流入天数": x["consec_days"],
                "介入净额(亿)": x["involve_money"],
                "介入度(%)": x["involve_pct"],
                "当日占比(%)": x["day_ratio"],
                "信号": x["signal"]
            }
            for x in out
        ])
        styled = table.style.map(color_val, subset=["纳入时涨幅(%)", "今日涨幅(%)"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        buf = BytesIO()
        table.to_csv(buf, index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 导出选股结果 CSV",
            data=buf.getvalue(),
            file_name="主力智选结果.csv",
            mime="text/csv"
        )

        st.subheader("查看K线布林图")
        sel_code = st.selectbox("选择标的", [r["code"] for r in out])
        target = next(r for r in out if r["code"] == sel_code)
        df_chart = target["df"]

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_chart.index,
            open=df_chart["Open"],
            high=df_chart["High"],
            low=df_chart["Low"],
            close=df_chart["Close"],
            name="K线"
        ))
        if use_boll and target["boll"]:
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["MA"], line=dict(color="#ffaa00"), name="中轨"))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["Upper"], line=dict(color="#ff4444"), name="上轨"))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart["Lower"], line=dict(color="#00bb44"), name="下轨"))
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

st.caption("⚠️ 资金指标为模拟拟合，仅演示界面逻辑；不是真实 Level2 大单，不构成任何投资建议")
