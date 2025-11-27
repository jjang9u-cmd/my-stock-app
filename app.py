import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 앱 설정 ---
st.set_page_config(layout="wide", page_title="Insight Alpha: Pro")

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
        padding: 15px;
        background-color: #fafafa;
        text-align: center;
        margin-bottom: 10px;
    }
    .grade-badge {
        font-size: 22px;
        font-weight: bold;
        padding: 5px 15px;
        border-radius: 15px;
        color: white;
        display: inline-block;
        margin-bottom: 5px;
    }
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 핵심 로직 ---
def get_grade_and_score(val, metric):
    if val is None or np.isnan(val): return "N/A", 50
    
    # 벤치마크 (Metric: [A, B, C, D])
    benchmarks = {
        # Valuation (Lower is better)
        "PEG": [0.8, 1.2, 1.8, 2.5],
        "PER": [15, 20, 25, 35],
        "P/S": [2, 4, 8, 12],  # 백업 지표
        
        # Profitability (Higher is better)
        "Margin": [50, 40, 30, 15],
        "ROE": [20, 15, 10, 5],
        
        # Growth (Higher is better)
        "Growth": [20, 10, 5, 0],
        
        # Momentum (Higher is better)
        "Momentum": [40, 20, 10, -10],
        
        # Safety (Lower is better)
        "Debt": [50, 100, 150, 200]
    }
    
    lower_better = ["PEG", "PER", "P/S", "Debt"]
    
    # 매핑
    key = "Margin"
    if "PEG" in metric: key = "PEG"
    elif "P/E" in metric: key = "PER"
    elif "P/S" in metric: key = "P/S"
    elif "Margin" in metric: key = "Margin"
    elif "ROE" in metric: key = "ROE"
    elif "Growth" in metric: key = "Growth"
    elif "Momentum" in metric: key = "Momentum"
    elif "Debt" in metric: key = "Debt"
    
    cr = benchmarks.get(key, [0,0,0,0])
    
    grade = "F"
    if key in lower_better:
        if val <= cr[0]: grade = "A+"
        elif val <= cr[0]*1.2: grade = "A"
        elif val <= cr[1]: grade = "B"
        elif val <= cr[2]: grade = "C"
        elif val <= cr[3]: grade = "D"
    else:
        if val >= cr[0]: grade = "A+"
        elif val >= cr[0]*0.8: grade = "A"
        elif val >= cr[1]: grade = "B"
        elif val >= cr[2]: grade = "C"
        elif val >= cr[3]: grade = "D"
        
    # 점수 환산
    score_map = {"A+":100, "A":90, "B":80, "C":60, "D":40, "F":20}
    return grade, score_map.get(grade, 20)

def get_color(s):
    if s >= 80: return "#00C853"
    elif s >= 60: return "#FFD600"
    else: return "#FF3D00"

# --- 4. 메인 화면 ---
st.title("🦅 Insight Alpha: Visual Quant")
st.caption("Wall Street Grade Analysis Engine")

# [수정] 버튼 위치 개선: 컬럼 없이 수직 배치
with st.form(key='search_form'):
    ticker = st.text_input("티커 입력 (예: QCOM, TSLA, NVDA)", "").upper()
    submit_button = st.form_submit_button(label='🚀 분석 시작 (Analyze)')

# --- 5. 분석 실행 ---
if submit_button:
    if not ticker:
        st.warning("티커를 입력해주세요.")
        st.stop()

    try:
        with st.spinner(f"{ticker} 데이터 수집 및 분석 중..."):
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if 'currentPrice' not in info:
                st.error(f"❌ '{ticker}' 데이터를 찾을 수 없습니다.")
                st.stop()
            
            # --- 데이터 추출 (백업 로직 적용) ---
            m = {}
            
            # 1. Valuation (PEG -> PER -> P/S 순서로 백업)
            peg = info.get('pegRatio')
            per = info.get('forwardPE')
            ps = info.get('priceToSalesTrailing12Months')
            
            m["Valuation"] = peg if peg else (per if per else ps)
            m["Valuation_Label"] = "PEG" if peg else ("P/E" if per else "P/S")
            
            # 2. Profitability
            m["Gross Margin"] = info.get('grossMargins', 0) * 100
            m["ROE"] = info.get('returnOnEquity', 0) * 100
            
            # 3. Growth
            m["Rev Growth"] = info.get('revenueGrowth', 0) * 100
            
            # 4. Momentum (추가됨)
            # 1년 수익률 계산
            try:
                hist = stock.history(period="1y")
                if not hist.empty:
                    start_p = hist['Close'].iloc[0]
                    end_p = hist['Close'].iloc[-1]
                    m["Momentum"] = ((end_p - start_p) / start_p) * 100
                else:
                    m["Momentum"] = 0
            except:
                m["Momentum"] = 0
                
            # 5. Safety
            m["Debt/Equity"] = info.get('debtToEquity')

            # --- 점수 및 등급 산출 ---
            # 평가 항목: 밸류에이션, 마진, ROE, 성장성, 모멘텀, 부채 (총 6개)
            eval_list = [
                (m["Valuation"], m["Valuation_Label"]),
                (m["Gross Margin"], "Margin"),
                (m["ROE"], "ROE"),
                (m["Rev Growth"], "Growth"),
                (m["Momentum"], "Momentum"),
                (m["Debt/Equity"], "Debt")
            ]
            
            total_score = 0
            count = 0
            grades = {}
            
            for val, label in eval_list:
                g, s = get_grade_and_score(val, label)
                # 키 이름 매핑
                display_key = label if label in ["PEG", "P/E", "P/S"] else label
                if label == "Margin": display_key = "Profitability"
                if label == "Debt": display_key = "Safety"
                
                # 중복 방지를 위한 처리
                if display_key in grades: display_key += "_2"
                
                grades[display_key] = {"grade": g, "value": val, "score": s}
                total_score += s
                count += 1
            
            final_score = int(total_score / count) if count > 0 else 0
            
            # --- UI 출력 ---
            
            # 헤더
            st.header(f"{info.get('shortName')} ({ticker})")
            st.write(f"현재가: **${info.get('currentPrice')}** | 섹터: {info.get('sector', 'N/A')}")
            
            # 게이지 차트
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
            
            # AI 코멘트
            if final_score >= 80:
                cmt = "🔥 **Strong Buy:** 밸류에이션, 성장성, 모멘텀 모두 완벽합니다."
            elif final_score >= 60:
                cmt = "✅ **Buy:** 전반적으로 준수합니다. 매수 고려해볼 만합니다."
            elif final_score >= 40:
                cmt = "⚠️ **Hold:** 매력이 부족하거나 주가가 비쌉니다."
            else:
                cmt = "⛔ **Sell:** 펀더멘털이 무너져 있습니다. 위험합니다."
                
            st.markdown(f"<div class='ai-box'>{cmt}</div>", unsafe_allow_html=True)
            
            # 팩터별 등급 카드 (5열 -> 모멘텀 포함)
            st.subheader("📊 Factor Grades")
            
            # 매핑 정의
            display_map = [
                ("Valuation", m["Valuation_Label"], m["Valuation"]),
                ("Profitability", "Margin", m["Gross Margin"]),
                ("Growth", "Growth", m["Rev Growth"]),
                ("Momentum", "Momentum", m["Momentum"]), # 추가됨
                ("Safety", "Debt", m["Debt/Equity"])
            ]
            
            cols = st.columns(5)
            
            for i, (title, key_type, val) in enumerate(display_map):
                g, s = get_grade_and_score(val, key_type)
                bg = get_color(s)
                
                # 값 포맷팅
                if val is None: val_str = "-"
                elif key_type in ["PEG", "P/E", "P/S"]: val_str = f"{val:.2f}"
                elif key_type == "Debt": val_str = f"{val:.1f}%"
                else: val_str = f"{val:.1f}%"
                
                with cols[i]:
                    st.markdown(f"""
                    <div class='metric-container'>
                        <div style='color:#666; font-size:14px; margin-bottom:5px;'>{title}</div>
                        <div class='grade-badge' style='background-color:{bg};'>{g}</div>
                        <div style='font-size:12px; color:#333;'>{key_type}: {val_str}</div>
                    </div>
                    """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"오류 발생: {e}")
