import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.stats import zscore
import itertools
import math
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(layout="wide", page_title="Insight Alpha 2.0")

# -------------------------
# CSS (no f-strings to avoid brace issues)
# -------------------------
st.markdown("""
<style>
    .rec-box {
        padding: 18px;
        border-radius: 12px;
        text-align: center;
        color: white;
    }
    .rec-title { font-size: 28px; font-weight: 800; }
    .rec-desc { font-size: 15px; }
    .metric-card { padding:12px; border-radius:10px; background:#fff; border:1px solid #eee; text-align:center; }
    .grade-badge { font-weight:800; padding:6px 10px; border-radius:8px; color:white; display:inline-block; }
    .stButton>button { background-color:#111; color:white; border-radius:8px; padding:8px 0; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Utility functions
# -------------------------
def format_large(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return "N/A"
    try:
        v = float(v)
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9: return f"${v/1e9:.2f}B"
        if v >= 1e6: return f"${v/1e6:.2f}M"
        return f"${v:,.0f}"
    except:
        return "N/A"

def grade_from_score(s):
    s = float(s)
    if s >= 90: return "A+"
    if s >= 80: return "A"
    if s >= 70: return "B"
    if s >= 60: return "C"
    if s >= 40: return "D"
    return "F"

def color_from_score(s):
    s = float(s)
    if s >= 80: return "#00C853"
    if s >= 60: return "#FFD600"
    return "#FF3D00"

# -------------------------
# Industry normalization rules
# returns a dict of scaling/floor rules applied to raw factor values
# -------------------------
def industry_rule_map(sector, industry):
    # Basic rules: return dict with keys to adjust interpretation of margins/growth/de ratios
    # This is intentionally conservative and editable.
    s = (sector or "").lower()
    i = (industry or "").lower()
    # default
    rule = {
        "gm_scale": 1.0,    # multiply gross margin (which is % already)
        "growth_scale": 1.0,
        "safe_de_norm": lambda x: x  # function to transform D/E before scoring
    }
    # Tech / Software / Internet
    if "software" in i or "internet" in s or "technology" in s or "semiconductor" in s:
        rule["gm_scale"] = 1.0   # margins matter but lower than platforms
        rule["growth_scale"] = 1.0
        rule["safe_de_norm"] = lambda x: x  # low D/E expected
    # Financials (banks, insurance) - different leverage norm
    if "financial" in s or "bank" in i or "insurance" in i:
        rule["gm_scale"] = 0.5
        rule["growth_scale"] = 0.6
        rule["safe_de_norm"] = lambda x: x / 5.0  # reduce effective D/E
    # Mining / Energy / Utilities (incl crypto miners)
    if "mining" in s or "energy" in s or "utility" in s or "crypto" in i or "mining" in i:
        rule["gm_scale"] = 0.6
        rule["growth_scale"] = 0.8
        rule["safe_de_norm"] = lambda x: x * 1.5  # higher risk from leverage
    # REITs / Real Estate - high D/E normal
    if "real estate" in s or "reit" in i:
        rule["gm_scale"] = 0.7
        rule["growth_scale"] = 0.8
        rule["safe_de_norm"] = lambda x: x / 4.0
    # Biotech (loss-making typical)
    if "biotechnology" in i or "pharmaceutical" in s:
        rule["gm_scale"] = 0.3
        rule["growth_scale"] = 1.2
        rule["safe_de_norm"] = lambda x: x * 2.0
    return rule

# -------------------------
# Score calculators (normalized to 0-100)
# -------------------------
def score_valuation(info):
    # Use PEG -> forwardPE -> PS (same fallback) but transform with log and zscore to be robust
    peg = info.get("pegRatio")
    per = info.get("forwardPE")
    ps = info.get("priceToSalesTrailing12Months")
    # prefer PEG if valid
    val = None
    if isinstance(peg, (int,float)) and peg>0:
        val = peg
        # lower PEG better
        # map: 0.1 -> 100, 1 -> 80, 2 -> 50, 5 -> 20
        if val <= 0.5: s=100
        elif val <= 0.8: s=90
        elif val <= 1.0: s=80
        elif val <= 1.5: s=60
        elif val <= 2.0: s=40
        else: s=20
        return s, f"PEG: {val:.2f}"
    if isinstance(per,(int,float)) and per>0:
        val = per
        # lower PER better relative to sector - simple mapping
        if val <= 10: s=100
        elif val <= 15: s=90
        elif
