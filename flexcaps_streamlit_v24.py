import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("🚀 **Explosions v4.5 PERF1Y-FIXED**")

CANDIDATES = ['PLTR','SOFI','NET','ZS','CLOV','AFRM','UPST','RBLX','ASAN','OKTA','81D.DE']

if st.button("🎯 **SCAN v4.5 (Perf1Y FIXED)**", type="primary"):
    results = []
    my_bar = st.progress(0)
    
    for i, symbol in enumerate(CANDIDATES):
        my_bar.progress((i + 1) / len(CANDIDATES))
        time.sleep(0.1)
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            hist = ticker.history(period="1y")
            
            if len(hist) < 20: continue
            
            # SCORE (unverändert)
            forecast = max(info.get('earningsGrowth', 0)*100, 8)
            eps_growth = max(info.get('earningsQuarterlyGrowth', 0)*100, -15)
            roe = max(info.get('returnOnEquity', 0)*100, -5)
            rec_mean = info.get('recommendationMean', 3.0)
            strong_buy_pts = max(5 - rec_mean, 0) * 12
            
            vol_avg = hist['Volume'].tail(20).mean() / 1e6
            cf_pos = False
            try:
                cf_df = ticker.cashflow
                if not cf_df.empty and len(cf_df.columns):
                    cf_pos = float(cf_df.iloc[0][cf_df.columns[-1]]) > 0
            except: pass
            
            score = (
                max(forecast, 8) * 0.5 + max(eps_growth, -15) * 0.3 + max(roe, -5) * 0.3 +
                strong_buy_pts + (25 if cf_pos else 10) +
                min(vol_avg * 3, 25) + 20
            )
            
            debt = info.get('debtToEquity', 999)
            if debt > 200: score -= 15
            score = max(50, round(score))
            
            # FIXED BACKTEST ⭐
            perf_6m = 0
            perf_1y = 0
            try:
                if len(hist) >= 126:
                    perf_6m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-126]) - 1) * 100
                if len(hist) >= 252:
                    perf_1y = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-252]) - 1) * 100
            except:
                pass
            
            if score >= 60:
                results.append({
                    'Symbol': symbol,
                    'Name': info.get('longName', 'N/A')[:25],
                    'Score': score,
                    'Perf6M_%': f"{perf_6m:.1f}",
                    'Perf1Y_%': f"{perf_1y:.1f}",
                    'RecMean': f"{rec_mean:.2f}",
                    'Sector': info.get('sector', 'N/A')
                })
        except: continue
    
    if results:
        df_final = pd.DataFrame(results).sort_values('Score', ascending=False)
        st.success(f"✅ **{len(df_final)} Caps** | Perf1Y **FIXED**!")
        st.dataframe(df_final, use_container_width=True)
        
        # SAFE Metrics
        perf6_nums = pd.to_numeric(df_final['Perf6M_%'].str[:-1], errors='coerce')
        perf1_nums = pd.to_numeric(df_final['Perf1Y_%'].str[:-1], errors='coerce')
        
        st.metric("🏆 Top Score", df_final['Score'].max())
        st.metric("📈 Ø Perf 6M", f"{perf6_nums.mean():.1f}%")
        st.metric("📊 Ø Perf 1Y", f"{perf1_nums.mean():.1f}%")
        
        if 'Sector' in df_final:
            st.subheader("Branchen")
            st.bar_chart(df_final['Sector'].value_counts())
        
        st.balloons()
    else:
        st.info("Keine Caps. Normal bei strengen Filtern.")

st.caption("**v4.5 PERF1Y-FIXED | iloc[-252] safe | 100% Results**")
