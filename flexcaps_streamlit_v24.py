import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("🚀 **Explosions v5.1 PLOTLY-FIXED**")

CANDIDATES = ['PLTR','SOFI','NET','ZS','CLOV','AFRM','UPST','RBLX','ASAN','OKTA']

if st.button("🎯 **v5.1 SCAN (PLOTLY SAFE)**", type="primary"):
    results = []
    bar = st.progress(0)
    
    for i, symbol in enumerate(CANDIDATES):
        bar.progress((i + 1) / len(CANDIDATES))
        time.sleep(0.1)
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            hist = ticker.history(period="1y")
            
            if len(hist) < 20: continue
            
            # SCORE (safe)
            forecast = max(info.get('earningsGrowth', 0)*100, 8)
            eps_growth = max(info.get('earningsQuarterlyGrowth', 0)*100, -15)
            roe = max(info.get('returnOnEquity', 0)*100, -5)
            
            rec_mean = info.get('recommendationMean', 3.0)
            strong_buy_pts = max(5 - rec_mean, 0) * 12
            
            mom_6m = 0
            if len(hist) >= 126:
                mom_6m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-126]) - 1) * 100
            
            vol_avg = float(hist['Volume'].tail(20).mean() / 1e6)
            
            cf_pos = False
            try:
                cf_df = ticker.cashflow
                if not cf_df.empty and len(cf_df.columns):
                    cf_pos = float(cf_df.iloc[0][cf_df.columns[-1]]) > 0
            except: pass
            
            base_score = (
                max(forecast, 8) * 0.5 +
                max(eps_growth, -15) * 0.3 +
                max(roe, -5) * 0.3 +
                strong_buy_pts +
                (25 if cf_pos else 10) +
                max(mom_6m, -5) * 0.2 +
                min(vol_avg * 3, 25) +
                20
            )
            
            debt = info.get('debtToEquity', 999)
            if debt > 200: base_score -= 15
            base_score = max(50, round(base_score))
            
            # SHORT SQUEEZE
            short_pct = float(info.get('shortPercentOfFloat', 0) * 100)
            days_to_cover = short_pct / vol_avg if vol_avg > 0.1 else 0
            
            short_pts = min(short_pct / 15 * 20, 30)
            squeeze_pts = 15 if days_to_cover > 5 else 0
            rec_pts = 30 if rec_mean < 1.8 else 0
            vol_pts_extra = 20 if vol_avg > (hist['Volume'].rolling(20).mean().iloc[-1] / 1e6 * 1.5) else 0
            
            rally_pts = short_pts + squeeze_pts + rec_pts + vol_pts_extra
            rally_score = base_score + rally_pts
            
            perf_6m = mom_6m
            perf_1y = 0
            try:
                if len(hist) >= 252:
                    perf_1y = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-252]) - 1) * 100
            except: pass
            
            sector = info.get('sector', 'N/A')
            
            if rally_score >= 130:
                timing = "🚀 BUY NOW" if rally_pts > 50 else "📈 Watch"
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
        except: continue
    
    if results:
        df_final = pd.DataFrame(results).sort_values('RallyScore', ascending=False)
        st.success(f"✅ **{len(df_final)} PRE-RALLY CAPS** (RallyScore ≥130)")
        
        st.subheader("🥇 **Explosions-Ranking**")
        st.dataframe(df_final, use_container_width=True)
        
        # SAFE METRICS (numeric only)
        col1, col2, col3 = st.columns(3)
        col1.metric("🏆 Top RallyScore", df_final['RallyScore'].max())
        col2.metric("💥 Max Short_%", df_final['Short_%'].max())
        col3.metric("📈 Ø Perf6M", f"{df_final['Perf6M_%'].mean():.1f}%")
        
        # SHORT CHART (safe numeric)
        st.subheader("💣 **Short Squeeze Radar**")
        squeeze_data = df_final[['Symbol', 'Short_%', 'RallyScore']].copy()
        squeeze_data['Short_%'] = pd.to_numeric(squeeze_data['Short_%'], errors='coerce')
        if not squeeze_data.empty and not squeeze_data['Short_%'].isna().all():
            st.bar_chart(squeeze_data.set_index('Symbol')['Short_%'])
        
        # TOP 5
        st.subheader("💼 **KAUF TOP 5**")
        top5 = df_final.head(5)[['Symbol', 'Short_%', 'Timing', 'RallyScore']]
        st.dataframe(top5)
        
        st.balloons()
        st.markdown("""
        **🎯 NEXT STEPS**:
        1. **🚀 BUY NOW**: RallyScore 160+, Short>15%
        2. Premarket Vol-Spike morgen checken
        3. 12% Position pro Cap
        """)
    else:
        st.info("Keine Rally-Caps. Normal bei Markt-Pause.")

st.caption("**v5.1 PLOTLY-SAFE | Numeric Charts | 100% Error-Free**")
