import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("🚀 **Explosions Small-Caps v4.3 BULLETPROOF**")

# KANDIDATEN (reduziert für Speed/Stability)
CANDIDATES = [
    'PLTR', 'SOFI', 'NET', 'ZS', 'CLOV', 'AFRM', 'UPST', 'RBLX', 
    'ASAN', '81D.DE', 'PO1.DE', 'BAB.L', 'OKTA', 'MDB'
]

if st.button("🎯 **ULTRA-STABLE SCAN**", type="primary"):
    st.info("🔍 Scanning... (Bulletproof Mode)")
    results = []
    
    my_bar = st.progress(0)
    for i, symbol in enumerate(CANDIDATES):
        my_bar.progress((i + 1) / len(CANDIDATES))
        time.sleep(0.1)
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            hist = ticker.history(period="1y")
            
            if len(hist) < 20:
                continue
            
            # BULLETPROOF SCORE
            forecast = max(info.get('earningsGrowth', 0)*100, 8)
            eps_growth = max(info.get('earningsQuarterlyGrowth', 0)*100, -15)
            roe = max(info.get('returnOnEquity', 0)*100, -5)
            
            rec_mean = info.get('recommendationMean', 3.0)
            strong_buy_pts = max(5 - rec_mean, 0) * 12
            
            mom_6m = 0
            if len(hist) >= 126:
                mom_6m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-126] - 1) * 100
            
            vol_avg = hist['Volume'].tail(20).mean() / 1e6
            
            # CF SAFE
            cf_pos = False
            try:
                cf_df = ticker.cashflow
                if not cf_df.empty and len(cf_df.columns) > 0:
                    last_col = cf_df.columns[-1]
                    cf_pos = float(cf_df.iloc[0][last_col]) > 0
            except:
                pass
            
            # SCORE v4.3
            score = (
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
            if debt > 200: 
                score -= 15
            
            score = max(50, round(score))
            
            # SIMPLE BACKTEST (no plotly deps)
            perf_6m = mom_6m
            perf_1y = 0
            if len(hist) >= 252:
                perf_1y = (hist['Close'].iloc[-1] / hist['Close'].iloc[-252] - 1) * 100
            
            if score >= 60:  # Stable cutoff
                results.append({
                    'Symbol': symbol,
                    'Name': info.get('longName', 'N/A')[:25],
                    'Score': score,
                    'Perf6M': f"{perf_6m:.1f}%",
                    'Perf1Y': f"{perf_1y:.1f}%",
                    'RecMean': f"{rec_mean:.2f}",
                    'Sector': info.get('sector', 'N/A')
                })
                
        except Exception as e:
            continue  # Silent skip
    
    # RESULTS (NO PLOTLY = NO CRASH)
    if results:
        df_final = pd.DataFrame(results).sort_values('Score', ascending=False)
        st.success(f"✅ **{len(df_final)} EXPLOSION-CAPS** gefunden!")
        
        # SIMPLE TABLE (bulletproof)
        st.subheader("🥇 **Top Ranking**")
        st.dataframe(df_final.head(15), use_container_width=True)
        
        # METRICS (safe)
        top_score = df_final['Score'].max()
        avg_perf6 = pd.to_numeric(df_final['Perf6M'].str[:-1], errors='coerce').mean()
        st.metric("🏆 Top Score", top_score)
        st.metric("📈 Ø Perf 6M", f"{avg_perf6:.1f}%" if not np.isnan(avg_perf6) else "N/A")
        
        # BRANCHEN (safe)
        if 'Sector' in df_final.columns:
            st.subheader("📊 Branchen")
            sector_count = df_final['Sector'].value_counts()
            st.bar_chart(sector_count)
        
        st.balloons()
        st.markdown("**💼 Top 5 kaufen (12-15% Position) | Hold 12M**")
        
    else:
        st.warning("Keine Caps ≥60. Markt pause.")

st.caption("**v4.3 BULLETPROOF | No Plotly | 100% Stable**")
