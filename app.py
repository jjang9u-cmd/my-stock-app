import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# --- 설정 ---
st.set_page_config(layout="wide", page_title="Insight Alpha: Quant Master")

# --- CSS 커스텀 (다크 테마 & 고급 스타일) ---
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
    .sector-tag {
        background-color: #4CAF50;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- 🧠 섹터별 기준 (월가 벤치마크) ---
SECTOR_BENCHMARKS = {
    "Technology": {"margin": 40, "peg": 1.5, "fcf_yield": 3.0},
    "Consumer Cyclical": {"margin": 15, "peg": 1.2, "fcf_yield": 4.0}, # 자동차 등
    "Consumer Defensive": {"margin": 10, "peg": 2.0, "fcf_yield": 3.0}, # 유통
    "Healthcare": {"margin": 50, "peg": 1.5, "fcf_yield": 2.5},
    "Financial Services": {"margin": 20, "peg": 1.2, "fcf_yield": 5.0},
    "Energy": {"margin": 20, "peg": 1.0, "fcf_yield": 8.0},
    "Default": {"margin": 30, "peg": 1.5, "fcf_yield": 3.5}
}

# --- AI 코멘트 생성기 ---
def get_ai_comment(score, symbol, grades):
    if score >= 90:
        return f"🔥 **강력 추천:** \"{symbol}은(는) 월가 펀드매니저들도 탐낼만한 완벽한 성적표입니다. 펀더멘털, 밸류에이션, 현금흐름 뭐 하나 빠지는 게 없네요. 지금 안 사면 후회할지도 모릅니다.\""
    elif score >= 80:
        return f"💎 **매수 적기:** \"상당히 훌륭합니다. {symbol}의 숫자는 탄탄합니다. 다만 시장의 광기 때문에 조금 비쌀 수 있으니 분할 매수로 접근하세요.\""
    elif score >= 60:
        if grades['Valuation'] == 'F':
            return f"⚠️ **비쌉니다:** \"회사는 좋은데 주가가 너무 비쌉니다. {symbol}이(가) 좋은 건 누구나 압니다. 하지만 이 가격에 사는 건 야수의 심장이 필요합니다. 조정 올 때까지 기다리세요.\""
        elif grades['Profitability'] == 'F' or grades['Profitability'] == 'D':
            return f"⚠️ **수익성 경고:** \"매출은 나오는데 남는 게 없네요. 마진율이 너무 박합니다. {symbol} 경영진은 돈 버는 법부터 다시 배워야 합니다.\""
        else:
            return f"👀 **관망 필요:** \"나쁘진 않지만, 그렇다고 당장 매수 버튼을 누를 만큼 매력적이지도 않습니다. 뭔가 결정적인 한 방이 부족합니다.\""
    elif score >= 40:
        return f"⛔ **투자 주의:** \"주가는 오를지 몰라도 펀더멘털 점수는 줄 수 없습니다. 제 기준에선 너무 위험하고 숫자가 엉망입니다. 다른 종목을 찾아보세요.\""
    else:
        return f"🗑️ **매도 의견:** \"이 주식을 포트폴리오에 담는 건 돈을 불에 태우는 것과 같습니다. 재무제표가 비명을 지르고 있네요. 절대 사지 마세요.\""

# --- 데이터 엔진 ---
def analyze_stock_pro(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'currentPrice' not in info: return None

        # --- 1. 섹터 보정 ---
        sector = info.get('sector', 'Default')
        bm = SECTOR_BENCHMARKS.get(sector, SECTOR_BENCHMARKS['Default'])

        # --- 2. 핵심 지표 추출 (Raw Data) ---
        market_cap = info.get('marketCap', 0)
        price = info.get('currentPrice', 0)
        
        # 현금흐름 (FCF Yield) - 중요
        fcf = info.get('freeCashflow', 0)
        fcf_yield = (fcf / market_cap * 100) if market_cap > 0 and fcf else 0
        
        # 밸류에이션
        peg = info.get('pegRatio', None)
        forward_pe = info.get('forwardPE', None)
        
        # 수익성
        gross_margin = info.get('grossMargins', 0) * 100
        oper_margin = info.get('operatingMargins', 0) * 100
        roe = info.get('returnOnEquity', 0) * 100
        
        # 이익의 질 (Earnings Quality) Check
        # 영업현금흐름 > 순이익 인가? (건전한 기업의 필수 조건)
        operating_cashflow = info.get('operatingCashflow', 0)
        net_income = info.get('netIncomeToCommon', 0)
        earnings_quality = True if operating_cashflow >= net_income else False

        # 성장성
        rev_growth = info.get('revenueGrowth', 0) * 100
        
        # 모멘텀 (상승여력)
        target_mean = info.get('targetMeanPrice', price)
        upside = ((target_mean - price) / price * 100) if price else 0

        # --- 3. 정밀 채점 (Scoring) ---
        score = 0
        
        # [A] Valuation (30점)
        val_score = 0
        if peg:
            if peg <= bm['peg'] * 0.8: val_score += 15 # 초저평가
            elif peg <= bm['peg']: val_score += 10
            elif peg <= bm['peg'] * 1.5: val_score += 5
        
        if fcf_yield >= bm['fcf_yield'] * 1.5: val_score += 15 # 현금 창출력 괴물
        elif fcf_yield >= bm['fcf_yield']: val_score += 10
        elif fcf_yield > 0: val_score += 5
        score += val_score

        # [B] Profitability (30점)
        prof_score = 0
        if gross_margin >= bm['margin']: prof_score += 10
        if oper_margin >= 10: prof_score += 10
        if roe >= 15: prof_score += 10
        score += prof_score

        # [C] Earnings Quality & Safety (20점) - 월가 스타일
        safe_score = 0
        if earnings_quality: safe_score += 10 # 흑자도산 방지
        else: safe_score -= 5 # 감점 요인
        
        debt_ratio = info.get('debtToEquity', 100)
        if debt_ratio < 150: safe_score += 10
        score += safe_score

        # [D] Growth & Momentum (20점)
        grow_score = 0
        if rev_growth >= 10: grow_score += 10
        elif rev_growth > 0: grow_score += 5
        
        if upside >= 15: grow_score += 10
        elif upside > 0: grow_score += 5
        score += grow_score
        
        # 점수 보정 (0~100)
        score = max(0, min(100, score))

        # --- 4. 등급 판정 ---
        grades = {
            "Valuation": "A" if val_score >= 20 else ("B" if val_score >= 10 else "F"),
            "Profitability": "A" if prof_score >= 25 else ("B" if prof_score >= 15 else ("C" if prof_score >= 10 else "F")),
            "Safety": "A" if safe_score >= 15 else ("B" if safe_score >= 10 else "C"),
        }

        return {
            "info": info,
            "score": score,
            "grades": grades,
            "metrics": {
                "PEG": peg if peg else 0,
                "FCF_Yield": fcf_yield,
                "G_Margin": gross_margin,
                "Earn_Qual": "우수" if earnings_quality else "주의",
                "Upside": upside,
                "Sector": sector
            }
        }

    except Exception as e:
        return None

# --- UI 레이아웃 ---
st.title("🧠 Insight Alpha: Quant Master")
st.caption("Wall Street Grade Financial Analysis Engine V3.0")

ticker_input = st.text_input("분석할 티커 (Ticker) 입력:", "").upper()

if st.button("Deep Dive 분석 시작"):
    if ticker_input:
        with st.spinner('월가 데이터를 크롤링하고 펀더멘털을 해부하는 중...'):
            data = analyze_stock_pro(ticker_input)
            
        if data:
            d = data['metrics']
            info = data['info']
            score = data['score']
            
            # --- 상단 요약 ---
            st.header(f"{info.get('shortName')} ({ticker_input})")
            st.markdown(f"<span class='sector-tag'>{d['Sector']} 섹터 기준 적용</span>", unsafe_allow_html=True)
            
            # --- 점수 게이지 ---
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                title = {'text': "Quant Score (100점 만점)"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#00C853" if score >= 80 else ("#FFD600" if score >= 50 else "#FF3D00")},
                    'steps': [{'range': [0, 100], 'color': "#262730"}]
                }
            ))
            st.plotly_chart(fig, use_container_width=True)

            # --- 🗣️ AI의 냉정한 한마디 (Highlight) ---
            ai_comment = get_ai_comment(score, ticker_input, data['grades'])
            st.markdown(f"""<div class='ai-comment-box'>{ai_comment}</div>""", unsafe_allow_html=True)

            # --- 핵심 지표 카드 (5-Factor) ---
            c1, c2, c3, c4, c5 = st.columns(5)
            
            c1.metric("Valuation (PEG)", f"{d['PEG']:.2f}", delta="낮을수록 좋음" if d['PEG'] < 1.5 else "고평가", delta_color="inverse")
            c2.metric("FCF Yield (현금수익률)", f"{d['FCF_Yield']:.1f}%", delta="높을수록 좋음")
            c3.metric("Gross Margin", f"{d['G_Margin']:.1f}%", f"섹터기준 {SECTOR_BENCHMARKS.get(d['
