import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 앱 설정 (최상단 고정) ---
st.set_page_config(layout="wide", page_title="Insight Alpha")

# --- 2. CSS 스타일 ---
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; }
    .ai-box {
        background-color: #f1f8ff;
        border-left: 6px solid #2196F3;
        padding: 20px;
        border-radius: 10px;
        font-size: 16px;
        font-weight: 500;
        margin: 20px 0;
    }
    .metric-container {
        border: 1px solid #eee;
        border-radius: 8px;
        padding: 10px;
        background-color: #fafafa;
        text-align: center;
    }
    .grade-badge {
        font-size: 20px;
        font-weight: bold;
        padding: 4px 12px;
        border-radius: 15px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 핵심 로직 (에러 방지형) ---
def get_grade(val, metric):
    if val is None: return "N/A"
    
    # (Metric: [A, B, C, D])
    benchmarks = {
        "PEG": [0.8, 1.2, 1.8, 2.5],
        "PER": [15, 20, 25, 35],
        "Margin": [50, 40, 30, 15],
        "ROE": [20, 15, 10, 5],
        "Growth": [20, 10, 5, 0],
        "Debt": [50, 100, 150, 200]
    }
    
    # 낮을수록 좋은 것들
    lower_better = ["PEG", "PER", "Debt"]
    
    # 매핑
    key = "Margin" # 기본값
    if "PEG" in metric: key = "PEG"
    elif "P/E" in metric: key = "PER"
    elif "Margin" in metric: key = "Margin"
    elif "ROE" in metric: key = "ROE"
    elif "Growth" in metric: key = "Growth"
    elif "Debt" in metric: key = "Debt"
    
    cr = benchmarks.get(key, [0,0,0,0])
    
    if key in lower_better:
        if val <= cr[0]: return "A+"
        elif val <= cr[0]*1.2: return "A"
        elif val <= cr[1]: return "B"
        elif val <= cr[2]: return "C"
        elif val <= cr[3]: return "D"
        else: return "F"
    else:
        if val >= cr[0]: return "A+"
        elif val >= cr[0]*0.8: return "A"
        elif val >= cr[1]: return "B"
        elif val >= cr[2]: return "C"
        elif val >= cr[3]: return "D"
        else: return "F"

def score_conversion(grade):
    m = {"A+":100, "A":90, "B":80, "C":60, "D":40, "F":20, "N/A":50}
    return m.get(grade, 50)

def get_color(s):
    if s >= 80: return "#00C853"
    elif s >= 60: return "#FFD600"
    else: return "#FF3D00"

# --- 4. 메인 화면 ---
st.title("🦅 Insight Alpha: Visual Quant")
st.markdown("Seeking Alpha Style Analysis Tool")

# [중요] 폼(Form) 사용: 엔터키 입력 지원 및 새로고침 방지
with st.form(key='search_form'):
    col1, col2 = st.columns([4, 1])
    with col1:
        ticker = st.text_input("티커 입력 (예: QCOM)", "").upper()
    with col2:
        submit_button = st.form_submit_button(label='분석 시작')

# --- 5. 분석 실행 (버튼 클릭 시) ---
if submit_button:
    if not ticker:
        st.warning("티커를 입력해주세요.")
        st.stop()

    try:
        with st.spinner(f"{ticker} 데이터 분석 중..."):
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 데이터 검증 (가장 중요)
            if 'currentPrice' not in info:
                st.error(f"❌ '{ticker}'에 대한 데이터를 찾을 수 없습니다. 티커를 확인해주세요.")
                st.stop()
            
            # --- 데이터 추출 ---
            m = {}
            m["PEG Ratio"] = info.get('pegRatio')
            m["P/E (Fwd)"] = info.get('forwardPE')
            m["Gross Margin"] = info.get('grossMargins', 0) * 100
            m["Net Margin"] = info.get('profitMargins', 0) * 100
            m["ROE"] = info.get('returnOnEquity', 0) * 100
            m["Rev Growth"] = info.get('revenueGrowth', 0) * 100
            m["Debt/Equity"] = info.get('debtToEquity')
            
            # --- 점수 산출 ---
            factors = ["PEG Ratio", "P/E (Fwd)", "Gross Margin", "Net Margin", "ROE", "Rev Growth", "Debt/Equity"]
            total_score = 0
            count = 0
            grades = {}
            
            for f in factors:
                val = m.get(f)
                g = get_grade(val, f)
                grades[f] = g
                total_score += score_conversion(g)
                count += 1
            
            final_score = int(total_score / count) if count > 0 else 0
            
            # --- UI 출력 ---
            
            # 1. 헤더
            st.markdown(f"## {info.get('shortName')} ({ticker})")
            st.markdown(f"**{info.get('sector', 'N/A')}** | 현재가: **${info.get('currentPrice')}**")
            
            # 2. 게이지 차트
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = final_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Quant Score"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': get_color(final_score)},
                    'steps': [{'range': [0, 100], 'color': "#f0f0f0"}]
                }
            ))
            fig.update_layout(height=250, margin=dict(t=30,b=20,l=20,r=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # 3. AI 코멘트
            if final_score >= 80:
                cmt = "🔥 **Strong Buy:** 펀더멘털이 매우 강력합니다. 포트폴리오의 핵심 종목으로 추천합니다."
            elif final_score >= 60:
                cmt = "✅ **Buy:** 전반적으로 준수합니다. 매수하기에 나쁘지 않은 선택입니다."
            elif final_score >= 40:
                cmt = "⚠️ **Hold:** 확실한 매력이 부족합니다. 관망하는 것이 좋겠습니다."
            else:
                cmt = "⛔ **Sell:** 리스크가 너무 큽니다. 다른 종목을 찾아보세요."
                
            st.markdown(f"<div class='ai-box'>{cmt}</div>", unsafe_allow_html=True)
            
            # 4. 상세 등급표
            st.subheader("📊 팩터별 등급 (Factor Grades)")
            c1, c2, c3, c4 = st.columns(4)
            cols = [c1, c2, c3, c4]
            
            display_factors = [
                ("Valuation", "PEG Ratio"),
                ("Profitability", "Gross Margin"),
                ("Growth", "Rev Growth"),
                ("Safety", "Debt/Equity")
            ]
            
            for i, (cat, key) in enumerate(display_factors):
                g = grades[key]
                val = m[key]
                
                # 값 포맷팅
                if val is None: val_str = "-"
                elif "Ratio" in key or "P/E" in key: val_str = f"{val:.2f}"
                elif "Debt" in key: val_str = f"{val:.2f}%"
                else: val_str = f"{val:.1f}%"
                
                bg = get_color(score_conversion(g))
                
                with cols[i]:
                    st.markdown(f"""
                    <div class='metric-container'>
                        <div style='color:#666; font-size:14px;'>{cat}</div>
                        <div class='grade-badge' style='background-color:{bg};'>{g}</div>
                        <div style='margin-top:5px; font-size:12px;'>{key}: {val_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
