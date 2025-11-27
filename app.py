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
    .insight-box {
        background-color: #f8f9fa;
        border-left: 5px solid #333;
        padding: 20px;
        border-radius: 8px;
        font-size: 16px;
        line-height: 1.6;
        color: #444;
    }
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
    .stButton>button {
        width: 100%;
        background-color: #111;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 0;
    }
    .stButton>button:hover { background-color: #333; color: white; }
    .footer {
        text-align: center;
        margin-top: 80px;
        padding-top: 20px;
        border-top: 1px solid #eee;
        color: #888;
        font-weight: 900;
        font-size: 14px;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 헬퍼 함수 ---
def format_large_number(num):
    if num is None: return "N/A"
    if num >= 1e12: return f"${num/1e12:.2f}T"
    elif num >= 1e9: return f"${num/1e9:.2f}B"
    elif num >= 1e6: return f"${num/1e6:.2f}M"
    else: return f"${num:,.0f}"

def get_color(score):
    if score >= 80: return "#00C853"
    elif score >= 60: return "#FFD600"
    else: return "#FF3D00"

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

# --- 4. 데이터 분석 엔진 ---
def analyze_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if 'currentPrice' not in info:
            return None

        # 1. Valuation
        peg = info.get('pegRatio')
        per = info.get('forwardPE')
        ps = info.get('priceToSalesTrailing12Months')
        
        val_score = 50
        val_detail = "N/A"
        
        if peg is not None:
            ratio = peg / 1.0
            if ratio <= 0.5: val_score = 10
