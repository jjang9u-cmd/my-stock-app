import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ----------------------------
# 1. APP CONFIG
# ----------------------------
st.set_page_config(layout="wide", page_title="Insight Alpha Pro")

# ----------------------------
# 2. CSS (스타일)
# ----------------------------
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; }
    
    .rec-box {
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .rec-title { font-size: 36px; font-weight: 900; margin-bottom: 5px; text-transform: uppercase; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
    .rec-desc { font-size: 20px; font-weight: 600; opacity: 0.9; }

    .insight-box {
        background-color: #f8f9fa;
        border-left: 5px solid #333;
        padding: 20px;
        border-radius: 8px;
        font-size: 16px;
        line-height: 1.6;
        color: #444;
    }

    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        height: 100%;
    }
    
    .factor-title { font-size: 14px; color: #666; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .factor-value { font-size: 13px; color: #888; margin-top: 8px; }

    .grade-badge {
        display: inline-block;
        width: 50px;
        height: 50px;
        line-height: 50px;
        border-radius: 50%;
        color: white;
        font-size: 24px;
        font-weight: 800;
        text-align: center;
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# 3. UTIL FUNCTIONS
# ----------------------------------------------------------

def format_large_number(num):
    if num is None: return "N/A"
    if num >= 1e12: return f"${num/1e12:.2f}T"
    elif num >= 1e9: return f"${num/1e9:.2f}B"
    elif num >= 1e6: return f"${num/1e6:.2f}M"
    else: return f"${num:,.0f}"

def get_color(score):
    if score >= 80: return "#00C853"
    elif score >= 60: return "#FFD600"
    else: return "#FF3D00"

def get_grade(score):
    if score >= 90: return "A+"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 60: return "C"
    elif score >= 40: return "D"
    else: return "F"

def get_grade_color(grade):
    if "A" in grade: return "#00C853"
    elif "B" in grade: return "#76FF03"
    elif "C" in grade: return "#FFD600"
    elif "D" in grade: return "#FF9100"
    else: return "#FF3D00"

# ----------------------------------------------------------
# 4. QUANT ENGINE (완성형 2.0)
# ----------------------------------------------------------

def analyze_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if 'currentPrice' not in info:
            return None

        # -----------------------
        # 1. Valuation
        # -----------------------
        peg = info.get('pegRatio')
        per = info.get('forwardPE')
        ps  = info.get('priceToSalesTrailing12Months')

        val_score = 50
        val_detail = "N/A"

        if peg is not None:
            ratio = peg / 1.0
            if ratio <= 0.5: val_score = 100
            elif ratio <= 0.8: val_score = 90
            elif ratio <= 1.0: val_score = 80
            elif ratio <= 1.5: val_score = 60
            elif ratio <= 2.0: val_score = 40
            else: val_score = 20
            val_detail = f"PEG: {peg:.2f}"

        elif per is not None:
            ratio = per / 20.0
            if ratio <= 0.5: val_score = 100
            elif ratio <= 0.8: val_score = 90
            elif ratio <= 1.0: val_score = 80
            elif ratio <= 1.5: val_score = 60
            elif ratio <= 2.0: val_score = 40
            else: val_score = 20
            val_detail = f"P/E: {per:.1f}"

        elif ps is not None:
            ratio = ps / 5.0
            if ratio <= 0.5: val_score = 100
            elif ratio <= 0.8: val_score = 90
            elif ratio <= 1.0: val_score = 80
            elif ratio <= 1.5: val_score = 60
            elif ratio <= 2.0: val_score = 40
            else: val_score = 20
            val_detail = f"P/S: {ps:.1f}"

        # -----------------------
        # 2. Profitability
        # -----------------------
        gm = info.get('grossMargins', 0) * 100
        prof_score = min(100, max(20, (gm / 50) * 80 + 20))

        # -----------------------
        # 3. Growth
        # -----------------------
        rev_g = info.get('revenueGrowth', 0) * 100
        grow_score = min(100, max(20, (rev_g / 20) * 80 + 20))

        # -----------------------
        # 4. Momentum
        # -----------------------
        mom_val = 0
        mom_score = 50
        try:
            hist = stock.history(period="1y")
            if not hist.empty:
                start = hist['Close'].iloc[0]
                end = hist['Close'].iloc[-1]
                mom_val = ((end - start) / start) * 100
                mom_score = min(100, max(20, (mom_val / 40) * 60 + 40))
        except:
            pass

        # -----------------------
        # 5. Safety
        # -----------------------
        de = info.get('debtToEquity')
        safe_score = 50
        safe_detail = "N/A"

        if de is not None:
            score_calc = 100 - ((de - 50) / 150 * 80)
            safe_score = min(100, max(20, score_calc))
            safe_detail = f"D/E: {de:.1f}%"

        # -----------------------
        # 6. Market Quality (신규 추가 요소)
        # -----------------------
        inst_own = info.get("heldPercentInstitutions", 0) * 100
        if inst_own >= 60: mq_score = 100
        elif inst_own >= 40: mq_score = 80
        elif inst_own >= 20: mq_score = 60
        else: mq_score = 40
        mq_detail = f"Institutional: {inst_own:.1f}%"

        # -----------------------
        # FINAL SCORE (2.0 업그레이드)
        # -----------------------
        final_score = (
            val_score * 0.25 +
            prof_score * 0.20 +
            grow_score * 0.20 +
            mom_score * 0.15 +
            safe_score * 0.10 +
            mq_score * 0.10
        )
        final_score = int(final_score)

        return {
            "info": info,
            "final_score": final_score,
            "scores": [val_score, prof_score, grow_score, mom_score, safe_score, mq_score],
            "details": [val_detail, f"Margin: {gm:.1f}%", f"Growth: {rev_g:.1f}%", f"1Y Return: {mom_val:.1f}%", safe_detail, mq_detail]
        }

    except Exception as e:
        return None

# ----------------------------------------------------------
# 5. MAIN UI
# ----------------------------------------------------------

st.title("🦅 Insight Alpha: Quant Score 2.0")

col1, col2 = st.columns([1, 4])
with col1:
    with st.form(key='search_form'):
        ticker = st.text_input("티커(Ticker)", placeholder="AAPL").upper()
        submit = st.form_submit_button("🔍 분석")

if submit:
    if not ticker:
        st.warning("티커를 입력해주세요.")
        st.stop()

    with st.spinner(f"데이터 로딩 중... ({ticker})"):
        data = analyze_data(ticker)

    if data is None:
        st.error("데이터를 찾을 수 없습니다.")
        st.stop()

    info = data["info"]
    final_score = data["final_score"]
    scores = data["scores"]
    details = data["details"]

    # -----------------------
    # HEADER
    # -----------------------
    st.markdown(f"## {info.get('shortName')} ({ticker})")

    h1, h2, h3, h4 = st.columns(4)

    cur_price = info.get('currentPrice')
    tar_price = info.get('targetMeanPrice')

    h1.metric("Current Price", f"${cur_price}")

    if tar_price:
        upside = ((tar_price - cur_price) / cur_price) * 100
        h2.metric("Target Price", f"${tar_price}", f"{upside:+.1f}%")
    else:
        h2.metric("Target Price", "N/A")

    h3.metric("Market Cap", format_large_number(info.get('marketCap')))
    h4.metric("Sector", info.get('sector', "N/A"))

    st.divider()

    # -----------------------
    # GAUGE + RECOMMENDATION
    # -----------------------
    c1, c2 = st.columns(2)

    with c1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=final_score,
            title={"text": "<b>Quant Score 2.0</b>", "font": {"size": 24}},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': get_color(final_score)},
                'steps': [
                    {'range': [0, 50], 'color': '#ffebee'},
                    {'range': [50, 80], 'color': '#fff8e1'},
                    {'range': [80, 100], 'color': '#e8f5e9'}
                ]
            }
        ))
        fig.update_layout(height=300, margin=dict(t=20, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        if final_score >= 80:
            rec_text, rec_desc, rec_bg = "STRONG BUY", "강력 매수 추천", "#00C853"
        elif final_score >= 60:
            rec_text, rec_desc, rec_bg = "BUY", "매수 가능", "#76FF03"
        elif final_score >= 40:
            rec_text, rec_desc, rec_bg = "HOLD", "관망 필요", "#FFD600"
        else:
            rec_text, rec_desc, rec_bg = "SELL", "비중 축소", "#FF3D00"

        html = f"""
        <div class="rec-box" style="background-color:{rec_bg}">
            <div class="rec-title">{rec_text}</div>
            <div class="rec-desc">{rec_desc}</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    st.divider()

    # -----------------------
    # FACTOR CARDS
    # -----------------------
    st.subheader("📊 6-Factor Grades")

    factors = ["Valuation", "Profitability", "Growth", "Momentum", "Safety", "Market Quality"]
    cols = st.columns(6)

    for i, f in enumerate(factors):
        score = scores[i]
        detail = details[i]
        grade = get_grade(score)
        color = get_grade_color(grade)

        with cols[i]:
            html = f"""
            <div class="metric-card">
                <div class="factor-title">{f}</div>
                <div class="grade-badge" style="background:{color}">{grade}</div>
                <div class="factor-value">{detail}</div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

    st.caption("Powered by Yahoo Finance — Quant Engine 2.0")

