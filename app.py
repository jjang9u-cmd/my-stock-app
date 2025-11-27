import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 페이지 설정 ---
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
        font-size: 18px;
        font-weight: 500;
        margin: 20px 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .factor-card {
        background-color: #fafafa;
        border: 1px solid #eee;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        transition: transform 0.2s;
    }
    .factor-card:hover { transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    .grade-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        font-size: 24px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 분석 로직 ---
def assign_grade(value, metric):
    if value is None or np.isnan(value): return "N/A"
    
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
        if 'currentPrice' not in info: return None
        
        metrics = {
            "PEG Ratio": info.get('pegRatio'),
            "P/E (Fwd)": info.get('forwardPE'),
            "EV/EBITDA": info.get('enterpriseToEbitda'),
            "P/FCF": (info.get('marketCap',0)/info.get('freeCashflow',1)) if info.get('freeCashflow') else None,
            "Rev Growth": info.get('revenueGrowth', 0) * 100,
            "EPS Growth": info.get('earningsGrowth', 0) * 100,
            "Gross Margin": info.get('grossMargins', 0) * 100,
            "Net Margin": info.get('profitMargins', 0) * 100,
            "ROE": info.get('returnOnEquity', 0) * 100,
            "Debt/Equity": info.get('debtToEquity'),
            "Quick Ratio": info.get('quickRatio'),
            "Perf 1Y": 10.0
        }
        
        try:
            hist = stock.history(period="1y")
            if not hist.empty:
                s = hist['Close'].iloc[0]
                e = hist['Close'].iloc[-1]
                metrics["Perf 1Y"] = ((e - s) / s) * 100
        except: pass

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

    except Exception as e:
        print(e)
        return None

def generate_comment(score, grades, ticker):
    if score >= 85:
        return f"🔥 **Strong Buy:** {ticker}는 완벽에 가깝습니다. 성장성, 수익성, 밸류에이션 박자가 맞습니다."
    elif score >= 70:
        if grades['Valuation']['grade'] in ['D', 'F']:
            return f"💎 **Buy (High Price):** 회사는 훌륭하지만(Quality A) 가격이 비쌉니다. 장기 투자는 유효합니다."
        else:
            return f"✅ **Buy:** 전반적으로 준수합니다. 치명적인 약점이 없고 합리적입니다."
    elif score >=
