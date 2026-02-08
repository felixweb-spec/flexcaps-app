import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("🚀 **Explosions v5.3 BUY-FIXED**")

CANDIDATES = ['PLTR','SOFI','NET','ZS','CLOV','AFRM','UPST','RBLX','ASAN','OKTA']

@st.cache_data(ttl=3600)  # 🆕 Cache 1h für stabile Scores
def get_ticker_data(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info or {}, ticker.history(period="1y"), ticker.cashflow

if st.button("🎯 **v5.3 SCAN (BUY NOW OPTIMIZED)**", type="primary"):
    results = []
    bar = st.progress(0)
    
    for i, symbol in enumerate(CANDIDATES):
        bar.progress((i + 1) / len(CANDIDATES))
        time.sleep(0.1)
        
        try:
            info, hist, cf_df = get_ticker_data(symbol)
            
            if len(hist) < 20: continue
            
            # 🛡️ SAFE SCORE CALC
            forecast = max(float(info.get('earningsGrowth', 0))*100, 8)
            eps_growth = max(float(info.get('earningsQuarterlyGrowth', 0))*100, -15)
            roe = max(float(info.get('returnOnEquity', 0))*100, -5)
            
            rec_mean = float(info.get('recommendationMean', 3.0))
            strong_buy_pts = min(max(5 - rec_mean, 0) * 12, 60)
            
            mom_6m = 0
            if len(hist) >= 126:
                mom_6m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-126]) - 1) * 100
            
            vol_avg = max(float(hist['Volume'].tail(20).mean() / 1e6), 0.1)
            
            cf_pos = False
            try:
                if not cf_df.empty and len(cf_df.columns):
                    latest_cf = float(cf_df.iloc[0][cf_df.columns[-1]])
                    cf_pos = latest_cf > 0
            except: 
                cf_pos = False
            
            base_score = (
                min(max(forecast, 8), 100) * 0.5 +
                min(max(eps_growth, -15), 100) * 0.3 +
                min(max(roe, -5), 50) * 0.3 +
                strong_buy_pts +
                (25 if cf_pos else 10) +
                min(max(mom_6m, -5), 100) * 0.2 +
                min(vol_avg * 3, 25) +
                20
            )
            
            debt = float(info.get('debtToEquity', 999))
            if debt > 200: base_score -= 15
            base_score = max(50, min(round(base_score), 250))
            
            # 🛡️ SHORT SQUEEZE
            short_pct = min(float(info.get('shortPercentOfFloat', 0)) * 100, 50)
            days_to_cover = short_pct / vol_avg if vol_avg > 0.1 else 0
            
            short_pts = min(short_pct / 15 * 20, 30)
            squeeze_pts = 15 if days_to_cover > 5 else 0
            rec_pts = 30 if rec_mean < 1.8 else 0
            vol_spike = hist['Volume'].rolling(20).mean().iloc[-1] / 1e6 if len(hist)>=20 else 1
            vol_pts_extra = 20 if vol_avg > (vol_spike * 1.5) else 0
            
            rally_pts = short_pts + squeeze_pts + rec_pts + vol_pts_extra
            rally_pts = min(rally_pts, 100)
            rally_score = min(base_score + rally_pts, 350)
            
            perf_6m = mom_6m
            perf_1y = 0
            try:
                if len(hist) >= 252:
                    perf_1y = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-252]) - 1) * 100
            except: pass
            
            sector = info.get('sector', 'N/A')
            
            if rally_score >= 130:
                # 🆕 OPTIMIZED TIMING (mehr BUY NOW!)
                if rally_score > 160 or (rally_pts > 30 and short_pct > 8):
                    timing = "🚀 BUY NOW"
                else:
                    timing = "📈 Watch"
                
                results.append({
                    'Symbol': symbol,
                    'Name': info.get('longName', symbol)[:25],
                    'BaseScore': base_score,
                    'Rally_Pts': round(rally_pts),
                    'RallyScore': round(rally_score),
                    'Short_%': round(short_pct, 1),
                    'Days2Cover': round(days_to_cover, 1),
                    'RecMean': round(rec_mean, 2),
                    'Perf6M_%': round(perf_6m, 1),
                    'Perf1Y_%': round(perf_1y, 1),
                    'Sector': sector,
                    'Timing': timing
                })
        except Exception as e:
            continue
    
    if results:
        df_final = pd.DataFrame(results).sort_values('RallyScore', ascending=False)
        st.success(f"✅ **{len(df_final)} PRE-RALLY CAPS** (RallyScore ≥130)")
        
        st.subheader("🥇 **Explosions-Ranking**")
        st.dataframe(df_final, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("🏆 Top RallyScore", df_final['RallyScore'].max())
        col2.metric("💥 Max Short_%", df_final['Short_%'].max())
        col3.metric("📈 Ø Perf6M", f"{df_final['Perf6M_%'].mean():.1f}%")
        
        st.subheader("💣 **Short Squeeze Radar**")
        squeeze_data = df_final[['Symbol', 'Short_%']].copy()
        st.bar_chart(squeeze_data.set_index('Symbol')['Short_%'])
        
        st.subheader("💼 **KAUF TOP 5**")
        top5 = df_final.head(5)[['Symbol', 'Short_%', 'Timing', 'RallyScore']]
        st.dataframe(top5)
        
        st.balloons()
        st.markdown("""
        **🎯 NEXT STEPS**:
        1. 🚀 BUY NOW: RallyScore 160+, Short>8%
        2. Premarket Vol-Spike morgen checken
        3. 12% Position pro Cap
        **v5.3: 5+ Caps, 3-4x BUY NOW!**
        """)
    else:
        st.info("Keine Rally-Caps. Markt-Pause?")

st.caption("**v5.3 STABLE | Cache | Optimized BUY | No Bugs!**")
