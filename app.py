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

# --- 3. 헬퍼 함수 ---
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

# --- 4. 데이터 분석 로직 ---
def calculate_scores(info, stock):
    # 1. Valuation (멀티 팩터)
    metrics = [
        ('pegRatio', 1.0, 0.3),
        ('forwardPE', 20.0, 0.3),
        ('enterpriseToEbitda', 15.0, 0.2),
        ('priceToSalesTrailing12Months', 5.0, 0.2)
    ]
    
    total_val_score = 0
    total_weight = 0
    val_detail = None
    
    for key, benchmark, weight in metrics:
        val = info.get(key)
        if val is not None:
            if val_detail is None: val_detail = val # 첫 번째 유효값 저장 (PEG 우선)
            ratio = val / benchmark
            if ratio <= 0.5: s = 100
            elif ratio <= 0.8: s = 90
            elif ratio <= 1.0: s = 80
            elif ratio <= 1.5: s = 60
            elif ratio <= 2.0: s = 40
            else: s = 20
            total_val_score += s * weight
            total_weight += weight
            
    val_score = int(total_val_score / total_weight) if total_weight > 0 else 50
    
    # 2. Profitability
    gm = info.get('grossMargins', 0) * 100
    prof_score = min(100, max(20, (gm / 50) * 80 + 20))
    
    # 3. Growth
    rev_g = info.get('revenueGrowth', 0) * 100
    grow_score = min(100, max(20, (rev_g / 20) * 80 + 20))
    
    # 4. Momentum
    try:
        hist = stock.history(period="1y")
        if not hist.empty:
            p_start = hist['Close'].iloc[0]
            p_end = hist['Close'].iloc[-1]
            mom_val = ((p_end - p_start) / p_start) * 100
            mom_score = min(100, max(20, (mom_val / 40) * 60 + 40))
        else: mom_val, mom_score = 0, 50
    except: mom_val, mom_score = 0, 50
    
    # 5. Safety
    de = info.get('debtToEquity')
    if de is not None:
        safe_score = min(100, max(20, 100 - ((de - 50) / 150 * 80)))
    else: de, safe_score = 0, 50

    # 종합 점수
    final_score = int(
        val_score * 0.3 + 
        prof_score *
