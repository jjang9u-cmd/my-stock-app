import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 앱 설정 ---
st.set_page_config(layout="wide", page_title="Insight Alpha Pro")

# --- 2. CSS 스타일 (UI 개선) ---
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; }
    
    /* 매수/매도 추천 박스 (확대 및 컬러 적용) */
    .recommendation-box {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .rec-title { font-size: 32px; font-weight: 900; margin-bottom: 5px; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    .rec-desc { font-size: 18px; font-weight: 500; color: white; }

    /* 팩터 컨테이너 */
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
    
    /* 텍스트 스타일 */
    .sub-text { font-size: 13px; color: #666; }
    .header-stat { font-size: 18px; font-weight: bold; color: #333; margin-right: 15px; }
    .label-stat { font-size: 14px; color: #888; }
    
    /* 버튼 스타일 */
    .stButton>button { background-color: #212121; color: white; font-weight: bold; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 3. 포맷팅 함수 ---
def format_market_cap(value):
    if value is None: return "N/A"
    if value >= 1e12: return f"${value/1e12:.2f}T (조)"
    elif value >= 1e9: return f"${value/1e9:.2f}B (십억)"
    elif value >= 1e6: return f"${value/1e6:.2f}M (백만)"
    else: return f"${value:.0f}"

def get_color(score):
    if score >= 80: return "#00C853" # Strong Buy Green
    elif score >= 60: return "#FFD600" # Hold Yellow
    else: return "#FF3D00" # Sell Red

# --- 4. 핵심 분석 로직 (멀티 팩터 밸류에이션) ---
def calculate_valuation_score(info):
    # 월가 스타일: 단일 지표가 아닌 4대 지표의 가중 평균 사용
    # [지표명, 기준값(이하일 때 A), 가중치]
    metrics = [
        ('pegRatio', 1.0, 0.3),            # PEG (성장주 핵심)
        ('forwardPE', 20.0, 0.3),          # Forward P/E (이익 핵심)
        ('enterpriseToEbitda', 15.0, 0.2), # EV/EBITDA (현금창출 핵심)
        ('priceToSalesTrailing12Months', 5.0, 0.2) # P/S (매출 핵심)
    ]
    
    total_score = 0
    total_weight = 0
    details = []
    
    for key, benchmark, weight in metrics:
        val = info.get(key)
        if val is not None:
            # 점수 산출 (벤치마크보다 낮을수록 고득점)
            # 벤치마크의 50% 수준이면 100점, 2배 수준이면 0점
            ratio = val / benchmark
            if ratio <= 0.5: s = 100
            elif ratio <= 0.8: s = 90
            elif ratio <= 1.0: s = 80 # 기준점
            elif ratio <= 1.5: s = 60
            elif ratio <= 2.0: s = 40
            else: s = 20
            
            total_score += s * weight
            total_weight += weight
            details.append(val)
        else:
            details.append(None)
            
    # 데이터가 하나도 없으면 50점(중립)
    if total_weight == 0: return 50, details
    
    # 가중 평균 점수 환산
    final_score = total_score / total_weight
    return int(final_score), details

def get_grade(score):
    if score >= 90: return "A+"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 60: return "C"
    elif score >= 40: return "D"
    else: return "F"

# --- 5. 메인 앱 UI ---
st.title("🦅 Insight Alpha: Pro Terminal")

# [UI 개선] 티커 입력창을 1/5 크기로 축소
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
        with st.spinner(f"월가 데이터베이스 접속 중... ({ticker})"):
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if 'currentPrice' not in info:
                st.error("데이터를 찾을 수 없습니다. 올바른 미국 주식 티커인지 확인해주세요.")
                st.stop()
            
            # --- 1. 데이터 추출 및 계산 ---
            
            # (1) Valuation (복합 모델)
            val_score, val_details = calculate_valuation_score(info)
            peg, fwd_pe, ev_ebitda, ps = val_details
            
            # (2) Profitability
            gm = info.get('grossMargins', 0) * 100
            roe = info.get('returnOnEquity', 0) * 100
            # 마진 점수: 50% 이상 100점, 10% 이하 20점
            prof_score = min(100, max(20, (gm / 50) * 80 + 20))
            
            # (3) Growth
            rev_g = info.get('revenueGrowth', 0) * 100
            # 성장 점수: 20% 이상 100점
            grow_score = min(100, max(20, (rev_g / 20) * 80 + 20))
            
            # (4) Momentum (1년 수익률)
            try:
                hist = stock.history(period="1y")
                if not hist.empty:
                    p_start = hist['Close'].iloc[0]
                    p_end = hist['Close'].iloc[-1]
                    mom_val = ((p_end - p_start) / p_start) * 100
                    mom_score = min(100, max(20, (mom_val / 40) * 60 + 40)) # 40% 오르면 100점
                else: mom_val, mom_score = 0, 50
            except: mom_val, mom_score = 0, 50
            
            # (5) Safety (부채비율)
            de = info.get('debtToEquity')
            if de is not None:
                # 부채비율 50% 이하 100점, 200% 이상 20점
                safe_score = min(100, max(20, 100 - ((de - 50) / 150 * 80)))
            else: de, safe_score = 0, 50

            # --- 종합 점수 산출 ---
            # 가중치: 밸류(30) + 수익성(25) + 성장성(20) + 모멘텀(15) + 안전성(10)
            final_quant_score = (
                val_score * 0.3 + 
                prof_score * 0.25 + 
                grow_score * 0.2 + 
                mom_score * 0.15 + 
                safe_score * 0.1
            )
            final_quant_score = int(final_quant_score)
            
            # --- UI 출력 시작 ---
            
            # [헤더] 주가 정보 표시 (한 줄로 깔끔하게)
            st.markdown(f"## {info.get('shortName')} ({ticker})")
            
            h_col1, h_col2, h_col3, h_col4 = st.columns(4)
            h_col1.markdown(f"<span class='label-stat'>Current Price</span><br><span class='header-stat'>${info.get('currentPrice')}</span>", unsafe_allow_html=True)
            
            # 목표 주가 처리
            target_p = info.get('targetMeanPrice')
            target_str = f"${target_p}" if target_p else "N/A"
            upside = ((target_p - info.get('currentPrice')) / info.get('currentPrice') * 100) if target_p else 0
            upside_color = "green" if upside > 0 else "red"
            
            h_col2.markdown(f"<span class='label-stat'>Target Price</span><br><span class='header-stat'>{target_str}</span> <span style='color:{upside_color}; font-size:14px;'>({upside:+.1f}%)</span>", unsafe_allow_html=True)
            h_col3.markdown(f"<span class='label-stat'>Market Cap</span><br><span class='header-stat'>{format_market_cap(info.get('marketCap'))}</span>", unsafe_allow_html=True)
            h_col4.markdown(f"<span class='label-stat'>Sector</span><br><span class='header-stat' style='font-size:16px;'>{info.get('sector', 'N/A')}</span>", unsafe_allow_html=True)
            
            st.divider()

            # [상단] 게이지 차트 & AI 의견
            c_left, c_right = st.columns([1, 1])
            
            with c_left:
                # 게이지 차트 (텍스트 안 잘리게 마진 조정)
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = final_quant_score,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "<b>Quant Score</b>", 'font': {'size': 24}},
                    gauge = {
                        'axis': {'range': [0, 100], 'tickwidth': 1},
                        'bar': {'color': get_color(final_quant_score)},
                        'bgcolor': "white",
                        'borderwidth': 2,
                        'bordercolor': "#eee",
                        'steps': [
                            {'range': [0, 50], 'color': '#ffebee'},
                            {'range': [50, 80], 'color': '#fffde7'},
                            {'range': [80, 100], 'color': '#e8f5e9'}],
                    }
                ))
                # 마진(margin)을 넉넉히 주어 텍스트 잘림 방지
                fig.update_layout(height=280, margin=dict(t=50, b=20, l=30, r=30))
                st.plotly_chart(fig, use_container_width=True)

            with c_right:
                # 매수/매도 추천 박스
                rec_text = "HOLD"
                rec_sub = "관망 필요"
                rec_bg = "#FFD600" # Yellow
                
                if final_quant_score >= 80:
                    rec_text = "STRONG BUY"
                    rec_sub = "강력 매수 추천"
                    rec_bg = "#00C853" # Green
                elif final_quant_score >= 60:
                    rec_text = "BUY"
                    rec_sub = "매수 고려"
                    rec_bg = "#64DD17" # Light Green
                elif final_quant_score <= 40:
                    rec_text = "SELL"
                    rec_sub = "매도/비중 축소"
                    rec_bg = "#FF3D00" # Red
                
                st.markdown(f"""
                <div class='recommendation-box' style='background-color: {rec_bg};'>
                    <div class='rec-title'>{rec_text}</div>
                    <div class='rec-desc'>{rec_sub}</div>
                </div>
                <div style='background-color:#f5f5f5; padding:15px; border-radius:10px; font-size:15px; color:#555;'>
                    <b>💡 AI Insight:</b><br>
                    이 기업은 <b>{'밸류에이션 매력' if val_score >= 70 else '성장성'}</b>이 돋보입니다. 
                    {'하지만
