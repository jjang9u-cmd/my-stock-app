import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 앱 설정 ---
st.set_page_config(layout="wide", page_title="Insight Alpha")

# --- 2. 스타일 설정 (에러 방지를 위해 한 줄로 처리) ---
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; }
    .ai-box { background-color: #f1f8ff; border-left: 6px solid #2196F3; padding: 20px; border-radius: 10px; margin: 20px 0; }
    .factor-card { background-color: #fafafa; border: 1px solid #eee; border-radius: 10px; padding: 15px; text-align: center; }
    .grade-badge { display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; font-size: 24px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. 분석 함수 ---
def assign_grade(value, metric):
    if value is None or np.isnan(value):
        return "N/A"
    
    # 벤치마크 기준
    benchmarks = {
        "PEG Ratio": [0.8, 1.2, 1.8, 2.5],
        "P/E (Fwd)": [15, 20, 25, 35],
        "EV/EBITDA": [10, 15, 20, 25],
        "P/FCF": [15, 20, 25, 35],
        "Rev Growth": [20, 10, 5, 0],
        "EPS Growth": [25, 15, 5, 0],
        "Gross Margin": [50, 40, 30, 15],
        "Net Margin": [20, 15, 8, 3],
        "ROE": [20, 15, 10, 5],
        "Perf 1Y": [40, 20, 5, -10],
        "Debt/Equity": [50, 100, 150, 200],
        "Quick Ratio": [1.5, 1.0, 0.8, 0.5]
    }
    
    lower_better = ["PEG Ratio", "P/E (Fwd)", "EV/EBITDA", "P/FCF", "Debt/Equity"]
    criteria = benchmarks.get(metric, [0, 0, 0, 0])
    
    if metric in lower_better:
        if value <= criteria[0]: return "A+"
        elif value <= criteria[0]*1.2: return "A"
        elif value <= criteria[1]: return "B"
        elif value <= criteria[2]: return "C"
        elif value <= criteria[3]: return "D"
        else: return "F"
    else:
        if value >= criteria[0]: return "A+"
        elif value >= criteria[0]*0.8: return "A"
        elif value >= criteria[1]: return "B"
        elif value >= criteria[2]: return "C"
        elif value >= criteria[3]: return "D"
        else: return "F"

def grade_to_score(grade):
    mapping = {"A+": 100, "A": 90, "B": 80, "C": 60, "D": 40, "F": 20, "N/A": 50}
    return mapping.get(grade, 50)

def get_color(score):
    if score >= 80: return "#00C853"
    elif score >= 60: return "#FFD600"
    else: return "#FF3D00"

# --- 4. 데이터 엔진 ---
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'currentPrice' not in info:
            return None
        
        # 데이터 안전 추출
        metrics = {}
        metrics["PEG Ratio"] = info.get('pegRatio')
        metrics["P/E (Fwd)"] = info.get('forwardPE')
        metrics["EV/EBITDA"] = info.get('enterpriseToEbitda')
        
        m_cap = info.get('marketCap', 0)
        fcf = info.get('freeCashflow')
        if fcf:
            metrics["P/FCF"] = m_cap / fcf
        else:
            metrics["P/FCF"] = None
            
        metrics["Rev Growth"] = info.get('revenueGrowth', 0) * 100
        metrics["EPS Growth"] = info.get('earningsGrowth', 0) * 100
        metrics["Gross Margin"] = info.get('grossMargins', 0) * 100
        metrics["Net Margin"] = info.get('profitMargins', 0) * 100
        metrics["ROE"] = info.get('returnOnEquity', 0) * 100
        metrics["Debt/Equity"] = info.get('debtToEquity')
        metrics["Quick Ratio"] = info.get('quickRatio')
        metrics["Perf 1Y"] = 10.0 # 기본값
        
        try:
            hist = stock.history(period="1y")
            if not hist.empty:
                s_price = hist['Close'].iloc[0]
                e_price = hist['Close'].iloc[-1]
                metrics["Perf 1Y"] = ((e_price - s_price) / s_price) * 100
        except:
            pass

        # 팩터 계산
        factors = {
            "Valuation": ["PEG Ratio", "P/E (Fwd)", "EV/EBITDA", "P/FCF"],
            "Growth": ["Rev Growth", "EPS Growth"],
            "Profitability": ["Gross Margin", "Net Margin", "ROE"],
            "Momentum": ["Perf 1Y"],
            "Safety": ["Debt/Equity", "Quick Ratio"]
        }
        
        factor_grades = {}
        total_score = 0
        count = 0
        
        for factor, ms in factors.items():
            f_score = 0
            f_count = 0
            for m in ms:
                val = metrics.get(m)
                g = assign_grade(val, m)
                f_score += grade_to_score(g)
                f_count += 1
            
            avg = f_score / f_count if f_count else 50
            
            if avg >= 90: grade = "A+"
            elif avg >= 80: grade = "A"
            elif avg >= 70: grade = "B"
            elif avg >= 60: grade = "C"
            elif avg >= 40: grade = "D"
            else: grade = "F"
            
            factor_grades[factor] = {"score": avg, "grade": grade}
            total_score += avg
            count += 1
            
        final_score = total_score / count if count else 0
        
        return {
            "info": info,
            "metrics": metrics,
            "factor_grades": factor_grades,
            "final_score": int(final_score)
        }

    except Exception:
        return None

# --- 5. 코멘트 생성 (문법 오류 방지를 위해 안전하게 작성) ---
def generate_comment(score, grades, ticker):
    val_grade = grades['Valuation']['grade']
    prof_grade
