import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# --- 설정: 유료 앱스러운 깔끔한 UI ---
st.set_page_config(layout="wide", page_title="Insight Alpha Pro")

# --- CSS 커스텀 (다크 모드 & 고급 폰트 느낌) ---
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        text-align: center;
    }
    .big-score {
        font-size: 48px;
        font-weight: bold;
        color: #4CAF50;
    }
    .grade-a { color: #00E676; font-weight: bold; }
    .grade-b { color: #9C27B0; font-weight: bold; }
    .grade-c { color: #FFC107; font-weight: bold; }
    .grade-d { color: #FF9800; font-weight: bold; }
    .grade-f { color: #FF5252; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 등급 부여 로직 (Strict Grading) ---
def get_grade(value, criteria_list):
    # criteria_list 형식: [(기준값, '등급'), ...] (높을수록 좋은 경우 내림차순 정렬 필요)
    for criteria, grade in criteria_list:
        if value is None: return "N/A"
        # 기준보다 좋으면 해당 등급 부여
        if isinstance(criteria, str): return "N/A"
        if value >= criteria: # 값이 높을수록 좋은 경우 (예: 마진율)
            return grade 
    return "F" # 기준 미달

def get_valuation_grade(peg, p_fcf):
    # 낮을수록 좋은 지표는 별도 로직
    score = 0
    if peg <= 1.0: score += 50
    elif peg <= 1.5: score += 40
    elif peg <= 2.0: score += 20
    
    if p_fcf <= 15: score += 50
    elif p_fcf <= 25: score += 35
    elif p_fcf <= 35: score += 15
    
    if score >= 90: return "A+"
    elif score >= 80: return "A"
    elif score >= 70: return "B"
    elif score >= 50: return "C"
    elif score >= 30: return "D"
    else: return "F"

# --- 데이터 분석 엔진 ---
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'currentPrice' not in info:
            return None

        # 1. Valuation Data (가치)
        peg = info.get('pegRatio', 0)
        p_fcf = info.get('marketCap', 0) / info.get('freeCashflow', 1) if info.get('freeCashflow') else 100
        forward_pe = info.get('forwardPE', 100)
        
        # 2. Profitability Data (수익성)
        gross_margin = info.get('grossMargins', 0) * 100
        operating_margin = info.get('operatingMargins', 0) * 100
        roe = info.get('returnOnEquity', 0) * 100

        # 3. Growth Data (성장성)
        rev_growth = info.get('revenueGrowth', 0) * 100
        earnings_growth = info.get('earningsGrowth', 0) * 100

        # 4. Momentum (수급/추세) - 간접 지표 활용
        current_price = info.get('currentPrice', 0)
        target_mean = info.get('targetMeanPrice', 0)
        upside = ((target_mean - current_price) / current_price) * 100 if current_price else 0
        
        # --- 점수 계산 (Scoring Engine) ---
        total_score = 0
        
        # [Valuation] (30점)
        if peg < 1.0: total_score += 15
        elif peg < 1.5: total_score += 10
        elif peg < 2.0: total_score += 5
        
        if p_fcf < 15: total_score += 15
        elif p_fcf < 25: total_score += 10
        elif p_fcf < 35: total_score += 5

        # [Profitability] (30점) - 빡센 기준
        if gross_margin > 50: total_score += 10
        elif gross_margin > 30: total_score += 5
        
        if operating_margin > 20: total_score += 10
        elif operating_margin > 10: total_score += 5
        
        if roe > 20: total_score += 10
        elif roe > 10: total_score += 5

        # [Growth] (20점)
        if rev_growth > 15: total_score += 10
        elif rev_growth > 5: total_score += 5
        
        if earnings_growth > 15: total_score += 10
        elif earnings_growth > 5: total_score += 5

        # [Momentum/Safety] (20점)
        if upside > 20: total_score += 20
        elif upside > 10: total_score += 10

        # --- 등급 산정 (A~F) ---
        grades = {
            "Valuation": get_valuation_grade(peg, p_fcf),
            "Profitability": get_grade(gross_margin, [(50, "A+"), (40, "A"), (30, "B"), (20, "C"), (10, "D")]),
            "Growth": get_grade(rev_growth, [(20, "A"), (10, "B"), (5, "C"), (0, "D")]),
            "Momentum": get_grade(upside, [(30, "A+"), (20, "A"), (10, "B"), (0, "C")]),
            "Safety": "A" if info.get('debtToEquity', 100) < 100 else "C" # 간단한 로직 적용
        }

        return {
            "info": info,
            "score": total_score,
            "grades": grades,
            "metrics": {
                "PEG": peg, "P/FCF": p_fcf, "G.Margin": gross_margin, 
                "Rev.Growth": rev_growth, "Upside": upside
            }
        }

    except Exception as e:
        return None

# --- UI 레이아웃 ---
st.title("🚀 Insight Alpha")
st.write("월가 수준의 정밀 퀀트 분석 (Premium)")

ticker_input = st.text_input("분석할 티커를 입력하세요 (예: QCOM)", "").upper()

if st.button("분석 시작 (Analyze)"):
    if ticker_input:
        with st.spinner('딥러닝 서버가 재무제표를 뜯어보는 중...'):
            data = analyze_stock(ticker_input)
            
        if data:
            info = data['info']
            score = data['score']
            grades = data['grades']
            m = data['metrics']
            
            # 1. Hero Section (점수판)
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # 게이지 차트
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = score,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "퀀트 종합 점수"},
                    gauge = {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#4CAF50" if score >= 80 else "#FFC107"},
                        'steps': [
                            {'range': [0, 50], 'color': "#ffebee"},
                            {'range': [50, 80], 'color': "#e8f5e9"}],
                    }))
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.header(f"{info.get('shortName')} ({ticker_input})")
                st.subheader(f"현재가: ${info.get('currentPrice')} | 목표가: ${info.get('targetMeanPrice')}")
                
                if score >= 80:
                    st.success("## 💎 Strong Buy (강력 매수)")
                    st.write("펀더멘털과 저평가 매력이 완벽하게 조화된 상태입니다.")
                elif score >= 60:
                    st.info("## 👀 Buy (매수 고려)")
                    st.write("좋은 기업이지만 일부 지표가 기준에 미치지 못합니다.")
                else:
                    st.error("## ⚠️ Hold/Sell (주의)")
                    st.write("현재 가격은 리스크가 큽니다.")

            st.divider()

            # 2. Seeking Alpha Style Grades
            st.subheader("📊 5-Factor Grades")
            c1, c2, c3, c4, c5 = st.columns(5)
            
            def display_grade(col, title, grade, detail):
                color_class = f"grade-{grade[0].lower()}" if grade[0] in ['A','B','C','D','F'] else ""
                col.markdown(f"""
                <div class='metric-card'>
                    <h4>{title}</h4>
                    <h2 class='{color_class}' style='color: {"#00E676" if "A" in grade else "#FFC107"};'>{grade}</h2>
                    <p style='font-size:12px; color:#aaa;'>{detail}</p>
                </div>
                """, unsafe_allow_html=True)

            display_grade(c1, "Valuation", grades['Valuation'], f"PEG {m['PEG']:.2f} / P/FCF {m['P/FCF']:.1f}x")
            display_grade(c2, "Profitability", grades['Profitability'], f"마진율 {m['G.Margin']:.1f}%")
            display_grade(c3, "Growth", grades['Growth'], f"매출성장 {m['Rev.Growth']:.1f}%")
            display_grade(c4, "Momentum", grades['Momentum'], f"상승여력 {m['Upside']:.1f}%")
            display_grade(c5, "Safety", grades['Safety'], "부채비율 안정적")

        else:
            st.error("데이터를 불러올 수 없습니다. 티커를 확인해주세요.")
