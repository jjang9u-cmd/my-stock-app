import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# --- 설정 ---
st.set_page_config(layout="wide", page_title="Insight Alpha")

# --- CSS 스타일 ---
st.markdown("""
<style>
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #444;
        text-align: center;
        margin-bottom: 10px;
    }
    .ai-comment-box {
        background-color: #f0f2f6;
        color: #31333F;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        font-style: italic;
        font-size: 16px;
        margin: 20px 0;
    }
    .sector-tag { background-color: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# --- 섹터별 기준값 ---
SECTOR_BENCHMARKS = {
    "Technology": {"margin": 40, "peg": 1.5, "fcf_yield": 3.0},
    "Consumer Cyclical": {"margin": 15, "peg": 1.2, "fcf_yield": 4.0},
    "Consumer Defensive": {"margin": 10, "peg": 2.0, "fcf_yield": 3.0},
    "Healthcare": {"margin": 50, "peg": 1.5, "fcf_yield": 2.5},
    "Financial Services": {"margin": 20, "peg": 1.2, "fcf_yield": 5.0},
    "Energy": {"margin": 20, "peg": 1.0, "fcf_yield": 8.0},
    "Default": {"margin": 30, "peg": 1.5, "fcf_yield": 3.5}
}

# --- AI 코멘트 생성 ---
def get_ai_comment(score, symbol, grades):
    if score >= 90:
        return f"🔥 **강력 추천:** '{symbol}은(는) 펀드매니저도 탐낼 완벽한 성적표입니다. 펀더멘털, 밸류에이션, 현금흐름 모두 완벽합니다.'"
    elif score >= 80:
        return f"💎 **매수 적기:** '{symbol}의 숫자는 탄탄합니다. 다만 시장 상황에 따라 분할 매수로 접근하세요.'"
    elif score >= 60:
        if grades['Valuation'] == 'F':
            return f"⚠️ **고평가 주의:** '회사는 좋지만 주가가 너무 비쌉니다. {symbol}은(는) 야수의 심장만 접근하세요.'"
        elif grades['Profitability'] == 'F':
            return f"⚠️ **수익성 경고:** '매출은 나오는데 마진이 너무 박합니다. 경영진의 효율성 개선이 필요합니다.'"
        else:
            return f"👀 **관망 필요:** '나쁘진 않지만, 지금 당장 매수할 만큼 매력적인 한 방이 부족합니다.'"
    elif score >= 40:
        return f"⛔ **투자 주의:** '주가는 오를지 몰라도 펀더멘털 점수는 줄 수 없습니다. 리스크가 큽니다.'"
    else:
        return f"🗑️ **매도 의견:** '이 주식을 사는 건 돈을 태우는 것과 같습니다. 재무제표 상태가 매우 좋지 않습니다.'"

# --- 핵심 분석 엔진 ---
def analyze_stock_pro(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'currentPrice' not in info:
            return None

        # 1. 섹터 확인
        sector = info.get('sector', 'Default')
        if sector not in SECTOR_BENCHMARKS:
            sector = 'Default'
        bm = SECTOR_BENCHMARKS[sector]

        # 2. 데이터 추출
        market_cap = info.get('marketCap', 0)
        price = info.get('currentPrice', 0)
        
        fcf = info.get('freeCashflow', 0)
        fcf_yield = (fcf / market_cap * 100) if (market_cap > 0 and fcf) else 0
        
        peg = info.get('pegRatio', None)
        
        gross_margin = info.get('grossMargins', 0) * 100
        oper_margin = info.get('operatingMargins', 0) * 100
        roe = info.get('returnOnEquity', 0) * 100
        
        op_cash = info.get('operatingCashflow', 0)
        net_income = info.get('netIncomeToCommon', 0)
        earnings_quality = True if op_cash >= net_income else False

        rev_growth = info.get('revenueGrowth', 0) * 100
        
        target_mean = info.get('targetMeanPrice', price)
        upside = ((target_mean - price) / price * 100) if price else 0

        # 3. 점수 계산
        score = 0
        
        # [A] Valuation
        val_score = 0
        if peg:
            if peg <= bm['peg'] * 0.8: val_score += 15
            elif peg <= bm['peg']: val_score += 10
            elif peg <= bm['peg'] * 1.5: val_score += 5
        
        if fcf_yield >= bm['fcf_yield'] * 1.5: val_score += 15
        elif fcf_yield >= bm['fcf_yield']: val_score += 10
        elif fcf_yield > 0: val_score += 5
        score += val_score

        # [B] Profitability
        prof_score = 0
        if gross_margin >= bm['margin']: prof_score += 10
        if oper_margin >= 10: prof_score += 10
        if roe >= 15: prof_score += 10
        score += prof_score

        # [C] Safety
        safe_score = 0
        if earnings_quality: safe_score += 10
        else: safe_score -= 5
        
        debt_ratio = info.get('debtToEquity', 100)
        if debt_ratio < 150: safe_score += 10
        score += safe_score

        # [D] Growth
        grow_score = 0
        if rev_growth >= 10: grow_score += 10
        elif rev_growth > 0: grow_score += 5
        
        if upside >= 15: grow_score += 10
        elif upside > 0: grow_score += 5
        score += grow_score
        
        score = max(0, min(100, score))

        # 4. 등급 판정
        val_grade = "F"
        if val_score >= 20: val_grade = "A"
        elif val_score >= 10: val_grade = "B"
        
        prof_grade = "F"
        if prof_score >= 25: prof_grade = "A"
        elif prof_score >= 15: prof_grade = "B"
        elif prof_score >= 10: prof_grade = "C"

        grades = {
            "Valuation": val_grade,
            "Profitability": prof_grade
        }
        
        target_margin = bm.get('margin', 30)
        
        # 결과 반환 (딕셔너리)
        result = {
            "info": info,
            "score": score,
            "grades": grades,
            "metrics": {
                "PEG": peg if peg else 0,
                "FCF_Yield": fcf_yield,
                "G_Margin": gross_margin,
                "Earn_Qual": "우수" if earnings_quality else "주의",
                "Upside": upside,
                "Sector": sector,
                "Target_Margin": target_margin
            }
        }
        return result

    except Exception as e:
        print(f"Error: {e}")
        return None

# --- UI 실행 ---
st.title("🧠 Insight Alpha: Quant Master")
st.caption("Wall Street Grade Financial Analysis Engine V3.3")

ticker_input = st.text_input("분석할 티커 (Ticker) 입력:", "").upper()

if st.button("Deep Dive 분석 시작"):
    if ticker_input:
        with st.spinner('데이터 분석 중...'):
            data = analyze_stock_pro(ticker_input)
            
        if data:
            d = data['metrics']
            info = data['info']
            score = data['score']
            
            st.header(f"{info.get('shortName')} ({ticker_input})")
            st.markdown(f"<span class='sector-tag'>{d['Sector']} 섹터 적용</span>", unsafe_allow_html=True)
            
            # 게이지 차트
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                title = {'text': "Quant Score"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#00C853" if score >= 80 else ("#FFD600" if score >= 50 else "#FF3D00")},
                    'steps': [{'range': [0, 100], 'color': "#262730"}]
                }
