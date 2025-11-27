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
    .recommendation-box {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .rec-title { font-size: 32px; font-weight: 900; margin-bottom: 5px; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    .rec-desc { font-size: 18px; font-weight: 500; color: white; }
    .metric-container {
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
    .header-stat { font-size: 18px; font-weight: bold; color: #333; margin-right: 15px; }
    .label-stat { font-size: 14px; color: #888; }
    .stButton>button { background-color: #212121; color: white; font-weight: bold; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 3. 함수 정의 ---
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

def calculate_valuation_score(info):
    metrics = [
        ('pegRatio', 1.0, 0.3),
        ('forwardPE', 20.0, 0.3),
        ('enterpriseToEbitda', 15.0, 0.2),
        ('priceToSalesTrailing12Months', 5.0, 0.2)
    ]
    
    total_score = 0
    total_weight = 0
    details = []
    
    for key, benchmark, weight in metrics:
        val = info.get(key)
        if val is not None:
            ratio = val / benchmark
            if ratio <= 0.5: s = 100
            elif ratio <= 0.8: s = 90
            elif ratio <= 1.0: s = 80
            elif ratio <= 1.5: s = 60
            elif ratio <= 2.0: s = 40
            else: s = 20
            
            total_score += s * weight
            total_weight += weight
            details.append(val)
        else:
            details.append(None)
            
    if total_weight == 0: return 50, details
    return int(total_score / total_weight), details

# --- 4. 메인 UI ---
st.title("🦅 Insight Alpha: Pro Terminal")

col_input, col_space = st.columns([1, 4])
with col_input:
    with st.form(key='search_form'):
        ticker = st.text_input("티커 (Ticker)", placeholder="예: AAPL").upper()
        submit_button = st.form_submit_button(label='🔍 분석 (Analyze)')

if submit_button:
    if not ticker:
        st.warning("티커를 입력해주세요.")
        st.stop()

    try:
        with st.spinner(f"분석 중... ({ticker})"):
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if 'currentPrice' not in info:
                st.error("데이터를 찾을 수 없습니다.")
                st.stop()
            
            # 1. 데이터 추출
            val_score, val_details = calculate_valuation_score(info)
            peg, fwd_pe, ev_ebitda, ps = val_details
            
            gm = info.get('grossMargins', 0) * 100
            prof_score = min(100, max(20, (gm / 50) * 80 + 20))
            
            rev_g = info.get('revenueGrowth', 0) * 100
            grow_score = min(100, max(20, (rev_g / 20) * 80 + 20))
            
            try:
                hist = stock.history(period="1y")
                if not hist.empty:
                    p_start = hist['Close'].iloc[0]
                    p_end = hist['Close'].iloc[-1]
                    mom_val = ((p_end - p_start) / p_start) * 100
                    mom_score = min(100, max(20, (mom_val / 40) * 60 + 40))
                else: mom_val, mom_score = 0, 50
            except: mom_val, mom_score = 0, 50
            
            de = info.get('debtToEquity')
            if de is not None:
                safe_score = min(100, max(20, 100 - ((de - 50) / 150 * 80)))
            else: de, safe_score = 0, 50

            final_quant_score = int(
                val_score * 0.3 + 
                prof_score * 0.25 + 
                grow_score * 0.2 + 
                mom_score * 0.15 + 
                safe_score * 0.1
            )
            
            # --- UI 출력 ---
            st.markdown(f"## {info.get('shortName')} ({ticker})")
            
            # 헤더 정보
            h1, h2, h3, h4 = st.columns(4)
            
            cur_p = info.get('currentPrice')
            tar_p = info.get('targetMeanPrice')
            
            h1.metric("Current Price", f"${cur_p}")
            
            if tar_p:
                upside = ((tar_p - cur_p) / cur_p) * 100
                h2.metric("Target Price", f"${tar_p}", f"{upside:+.1f}%")
            else:
                h2.metric("Target Price", "N/A")
                
            h3.metric("Market Cap", format_market_cap(info.get('marketCap')))
            h4.metric("Sector", info.get('sector', 'N/A'))
            
            st.divider()

            # 게이지 & 추천
            c_left, c_right = st.columns([1, 1])
            
            with c_left:
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = final_quant_score,
                    title = {'text': "<b>Quant Score</b>", 'font': {'size': 24}},
                    gauge = {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': get_color(final_quant_score)},
                        'steps': [
                            {'range': [0, 50], 'color': '#ffebee'},
                            {'range': [50, 80], 'color': '#fffde7'},
                            {'range': [80, 100], 'color': '#e8f5e9'}],
                    }
                ))
                fig.
