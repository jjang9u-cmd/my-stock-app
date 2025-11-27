import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 앱 설정 ---
st.set_page_config(layout="wide", page_title="Insight Alpha Pro")

# --- 2. CSS 스타일 (가독성 & 디자인 강화) ---
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; }
    
    /* 추천 박스 디자인 */
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
    
    /* AI 인사이트 박스 */
    .insight-box {
        background-color: #f8f9fa;
        border-left: 5px solid #333;
        padding: 20px;
        border-radius: 8px;
        font-size: 16px;
        line-height: 1.6;
        color: #444;
    }

    /* 팩터 카드 디자인 */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        height: 100%;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-5px); }
    
    .factor-title { font-size: 14px; color: #666; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .factor-value { font-size: 13px; color: #888; margin-top: 8px; }
    
    /* 등급 뱃지 */
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
    
    /* 버튼 스타일 */
    .stButton>button {
        width: 100%;
        background-color: #111;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 0;
    }
    .stButton>button:hover { background-color: #333; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 3. 유틸리티 함수 ---
def format_large_number(num):
    if num is None: return "N/A"
    if num >= 1e12: return f"${num/1e12:.2f}T"
    elif num >= 1e9: return f"${num/1e9:.2f}B"
    elif num >= 1e6: return f"${num/1e6:.2f}M"
    else: return f"${num:,.0f}"

def get_color(score):
    if score >= 80: return "#00C853" # Green
    elif score >= 60: return "#FFD600" # Yellow
    else: return "#FF3D00" # Red

def get_grade_color(grade):
    if "A" in grade: return "#00C853"
    elif "B" in grade: return "#76FF03"
    elif "C" in grade: return "#FFD600"
    elif "D" in grade: return "#FF9100"
    else: return "#FF3D00"

def get_grade(score):
    if score >= 90: return "A+"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 60: return "C"
    elif score >= 40: return "D"
    else: return "F"

# --- 4. 데이터 분석 엔진 (Multi-Factor Model) ---
def analyze_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 필수 데이터 확인
        if 'currentPrice' not in info:
            return None

        # 1. Valuation (복합 평가)
        # PEG -> PER -> P/S 순서로 유효한 값을 찾아서 평가
        peg = info.get('pegRatio')
        per = info.get('forwardPE')
        ps = info.get('priceToSalesTrailing12Months')
        
        val_score = 50
        val_detail = "N/A"
        
        if peg is not None:
            # PEG 기준: 1.0 이하면 우수
            ratio = peg / 1.0
            if ratio <= 0.5: val_score = 100
            elif ratio <= 0.8: val_score = 90
            elif ratio <= 1.0: val_score = 80
            elif ratio <= 1.5: val_score = 60
            elif ratio <= 2.0: val_score = 40
            else: val_score = 20
            val_detail = f"PEG: {peg:.2f}"
        elif per is not None:
            # PER 기준: 20배 이하면 우수
            ratio = per / 20.0
            if ratio <= 0.5: val_score = 100
            elif ratio <= 0.8: val_score = 90
            elif ratio <= 1.0: val_score = 80
            elif ratio <= 1.5: val_score = 60
            elif ratio <= 2.0: val_score = 40
            else: val_score = 20
            val_detail = f"P/E: {per:.1f}"
        elif ps is not None:
            # P/S 기준: 5배 이하면 우수
            ratio = ps / 5.0
            if ratio <= 0.5: val_score = 100
            elif ratio <= 0.8: val_score = 90
            elif ratio <= 1.0: val_score = 80
            elif ratio <= 1.5: val_score = 60
            elif ratio <= 2.0: val_score = 40
            else: val_score = 20
            val_detail = f"P/S: {ps:.1f}"

        # 2. Profitability (수익성)
        gm = info.get('grossMargins', 0) * 100
        # 마진 50% 이상이면 100점, 10% 이하면 20점
        prof_score = min(100, max(20, (gm / 50) * 80 + 20))
        
        # 3. Growth (성장성)
        rev_g = info.get('revenueGrowth', 0) * 100
        # 성장률 20% 이상이면 100점
        grow_score = min(100, max(20, (rev_g / 20) * 80 + 20))
        
        # 4. Momentum (모멘텀 - 1년 수익률)
        mom_val = 0
        mom_score = 50
        try:
            hist = stock.history(period="1y")
            if not hist.empty:
                start = hist['Close'].iloc[0]
                end = hist['Close'].iloc[-1]
                mom_val = ((end - start) / start) * 100
                # 40% 이상 상승 시 100점
                mom_score = min(100, max(20, (mom_val / 40) * 60 + 40))
        except:
            pass
            
        # 5. Safety (재무 건전성)
        de = info.get('debtToEquity')
        safe_score = 50
        safe_detail = "N/A"
        if de is not None:
            # 부채비율 50% 이하 100점, 150% 이상 감점
            score_calc = 100 - ((de - 50) / 150 * 80)
            safe_score = min(100, max(20, score_calc))
            safe_detail = f"D/E: {de:.1f}%"

        # 종합 점수 산출 (가중치 적용)
        # Valuation(30) + Profitability(25) + Growth(20) + Momentum(15) + Safety(10)
        final_score = (val_score * 0.3) + (prof_score * 0.25) + (grow_score * 0.2) + (mom_score * 0.15) + (safe_score * 0.1)
        final_score = int(final_score)
        
        return {
            "info": info,
            "final_score": final_score,
            "scores": [val_score, prof_score, grow_score, mom_score, safe_score],
            "details": [val_detail, f"Margin: {gm:.1f}%", f"Rev Growth: {rev_g:.1f}%", f"1Y Return: {mom_val:.1f}%", safe_detail]
        }

    except Exception as e:
        return None

# --- 5. UI 메인 ---
st.title("🦅 Insight Alpha: Pro Terminal")

# [UI] 컴팩트한 검색창 (1/5 비율) & 버튼 수직 배치
col1, col2 = st.columns([1, 4])
with col1:
    with st.form(key='search_form'):
        ticker = st.text_input("티커 (Ticker)", placeholder="AAPL").upper()
        submit = st.form_submit_button("🔍 분석 시작")

if submit:
    if not ticker:
        st.warning("티커를 입력해주세요.")
        st.stop()
        
    with st.spinner(f"월가 데이터베이스 접속 중... ({ticker})"):
        data = analyze_data(ticker)
        
    if data is None:
        st.error("데이터를 찾을 수 없습니다. 올바른 미국 주식 티커인지 확인해주세요.")
        st.stop()
        
    # 데이터 언패킹
    info = data["info"]
    final_score = data["final_score"]
    scores = data["scores"]
    details = data["details"]
    
    # --- [상단] 헤더 정보 ---
    st.markdown(f"## {info.get('shortName')} ({ticker})")
    
    h1, h2, h3, h4 = st.columns(4)
    
    # 가격 정보
    cur_price = info.get('currentPrice')
    tar_price = info.get('targetMeanPrice')
    
    h1.metric("Current Price", f"${cur_price}")
    
    if tar_price:
        upside = ((tar_price - cur_price) / cur_price) * 100
        h2.metric("Target Price", f"${tar_price}", f"{upside:+.1f}%")
    else:
        h2.metric("Target Price", "N/A")
        
    h3.metric("Market Cap", format_large_number(info.get('marketCap')))
    h4.metric("Sector", info.get('sector', 'N/A'))
    
    st.divider()
    
    # --- [중단] 게이지 & 추천 박스 ---
    c_left, c_right = st.columns([1, 1])
    
    with c_left:
        # 게이지 차트 (Plotly)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = final_score,
            title = {'text': "<b>Quant Score</b>", 'font': {'size': 24, 'color': '#333'}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': get_color(final_score)},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "#eee",
                'steps': [
                    {'range': [0, 50], 'color': '#ffebee'},
                    {'range': [50, 80], 'color': '#fffde7'},
                    {'range': [80, 100], 'color': '#e8f5e9'}
                ],
            }
        ))
        fig.update_layout(height=300, margin=dict(t=50, b=20, l=30, r=30))
        st.plotly_chart(fig, use_container_width=True)
        
    with c_right:
        # 추천 로직
        if final_score >= 80:
            rec_text = "STRONG BUY"
            rec_desc = "강력 매수 추천"
            rec_bg = "#00C853"
        elif final_score >= 60:
            rec_text = "BUY"
            rec_desc = "매수 고려"
            rec_bg = "#64DD17"
        elif final_score <= 40:
            rec_text = "SELL"
            rec_desc = "매도 / 비중 축소"
            rec_bg = "#FF3D00"
        else:
            rec_text = "HOLD"
            rec_desc = "관망 필요"
            rec_bg = "#FFD600"
            
        # Insight 텍스트 생성 (안전하게 변수로 분리)
        insight_p1 = "밸류에이션 매력" if scores[0] >= 70 else "성장 잠재력"
        insight_p2 = "하지만 가격 부담이 있습니다." if scores[0] < 50 else "현재 주가는 합리적인 수준입니다."
        insight_p3 = "재무 건전성도 우수합니다." if scores[4] >= 70 else "다만 부채 비율 관리가 필요합니다."
        
        # HTML 렌더링
        html_content = f"""
        <div class="rec-box" style="background-color: {rec_bg};">
            <div class="rec-title">{rec_text}</div>
            <div class="rec-desc">{rec_desc}</div>
        </div>
        <div class="insight-box">
            <b>💡 AI Insight:</b><br>
            데이터 분석 결과, 이 기업은 <b>{insight_p1}</b>이 돋보입니다. 
            {insight_p2} {insight_p3}
        </div>
        """
        st.markdown(html_content, unsafe_allow_html=True)
        
    st.divider()
    
    # --- [하단] 5-Factor Grades (카드 UI) ---
    st.subheader("📊 5-Factor Grades")
    
    factors = ["Valuation", "Profitability", "Growth", "Momentum", "Safety"]
    f_cols = st.columns(5)
    
    for i, title in enumerate(factors):
        score = scores[i]
        detail = details[i]
        grade = get_grade(score)
        bg_color = get_grade_color(grade)
        
        with f_cols[i]:
            card_html = f"""
            <div class="metric-card">
                <div class="factor-title">{title}</div>
                <div class="grade-badge" style="background-color: {bg_color};">{grade}</div>
                <div class="factor-value">{detail}</div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
    st.markdown("---")
    st.caption("Powered by Yahoo Finance | Algorithm: Weighted Multi-Factor Model")
