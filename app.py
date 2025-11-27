import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 앱 설정 ---
st.set_page_config(layout="wide", page_title="Insight Alpha Pro")

# --- 2. CSS 스타일 ---
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; }
    .rec-box {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: white;
    }
    .rec-title { font-size: 32px; font-weight: 900; margin-bottom: 5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    .rec-desc { font-size: 18px; font-weight: 500; }
    .metric-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        background-color: #f9f9f9;
        text-align: center;
        height: 100%;
    }
    .grade-badge {
        font-size: 24px;
        font-weight: 800;
        padding: 5px 15px;
        border-radius: 8px;
        color: white;
        display: inline-block;
        margin: 10px 0;
    }
    .sub-text { font-size: 13px; color: #666; }
    .stButton>button { background-color: #212121; color: white; font-weight: bold; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 3. 헬퍼 함수 ---
def format_market_cap(value):
    if value is None: return "N/A"
    if value >= 1e12: return f"${value/1e12:.2f}T"
    elif value >= 1e9: return f"${value/1e9:.2f}B"
    elif value >= 1e6: return f"${value/1e6:.2f}M"
    else: return f"${value:.0f}"

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

# --- 4. 데이터 계산 로직 ---
def calculate_scores(info, stock):
    # 1. Valuation
    peg = info.get('pegRatio')
    per = info.get('forwardPE')
    ps = info.get('priceToSalesTrailing12Months')
    
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

    # 2. Profitability
    gm = info.get('grossMargins', 0) * 100
    prof_score = (gm / 50) * 80 + 20
    prof_score = min(100, max(20, prof_score))
    
    # 3. Growth
    rev_g = info.get('revenueGrowth', 0) * 100
    grow_score = (rev_g / 20) * 80 + 20
    grow_score = min(100, max(20, grow_score))
    
    # 4. Momentum
    mom_val = 0
    mom_score = 50
    try:
        hist = stock.history(period="1y")
        if not hist.empty:
            p_s = hist['Close'].iloc[0]
            p_e = hist['Close'].iloc[-1]
            mom_val = ((p_e - p_s) / p_s) * 100
            mom_score = (mom_val / 40) * 60 + 40
            mom_score = min(100, max(20, mom_score))
    except: pass
    
    # 5. Safety
    de = info.get('debtToEquity')
    safe_score = 50
    safe_detail = "N/A"
    if de is not None:
        safe_score = 100 - ((de - 50) / 150 * 80)
        safe_score = min(100, max(20, safe_score))
        safe_detail = f"D/E: {de:.1f}%"

    # 종합 점수
    final_score = int(val_score*0.3 + prof_score*0.25 + grow_score*0.2 + mom_score*0.15 + safe_score*0.1)
    
    return {
        "final": final_score,
        "scores": [val_score, prof_score, grow_score, mom_score, safe_score],
        "details": [val_detail, f"Margin: {gm:.1f}%", f"Rev Growth: {rev_g:.1f}%", f"1Y Return: {mom_val:.1f}%", safe_detail]
    }

# --- 5. 메인 UI ---
st.title("🦅 Insight Alpha: Pro Terminal")

col1, col2 = st.columns([1, 4])
with col1:
    with st.form(key='search_form'):
        ticker = st.text_input("티커 (Ticker)", placeholder="예: AAPL").upper()
        submit_button = st.form_submit_button(label='🔍 분석 (Analyze)')

# --- 6. 분석 로직 실행 (들여쓰기 제거로 에러 방지) ---
if submit_button:
    if not ticker:
        st.warning("티커를 입력해주세요.")
        st.stop()

    info = None
    stock = None
    
    # 데이터 가져오기 (여기만 작은 try 사용)
    try:
        with st.spinner(f"데이터 수집 중... ({ticker})"):
            stock = yf.Ticker(ticker)
            info = stock.info
    except Exception as e:
        st.error(f"데이터 통신 오류: {e}")
        st.stop()
        
    if info is None or 'currentPrice' not in info:
        st.error("데이터를 찾을 수 없습니다. 티커를 확인해주세요.")
        st.stop()

    # 점수 계산
    res = calculate_scores(info, stock)
    final_score = res["final"]
    scores = res["scores"]
    details = res["details"]
    
    # UI 표시
    st.markdown(f"## {info.get('shortName')} ({ticker})")
    
    # 헤더 정보
    h1, h2, h3, h4 = st.columns(4)
    cur = info.get('currentPrice')
    tar = info.get('targetMeanPrice')
    
    h1.metric("Current Price", f"${cur}")
    if tar:
        up = ((tar - cur) / cur) * 100
        h2.metric("Target Price", f"${tar}", f"{up:+.1f}%")
    else:
        h2.metric("Target Price", "N/A")
    h3.metric("Market Cap", format_market_cap(info.get('marketCap')))
    h4.metric("Sector", info.get('sector', 'N/A'))
    
    st.divider()

    # 차트 및 추천
    c_left, c_right = st.columns([1, 1])
    
    with c_left:
        gauge_color = get_color(final_score)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = final_score,
            title = {'text': "<b>Quant Score</b>", 'font': {'size': 24}},
            gauge = {
                'axis':
