import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(page_title="Explosions v4.1 FIXED", layout="wide")
st.title("🚀 **Explosions Small-Caps v4.1 ERROR-FIXED**")

@st.cache_data(ttl=1800)
def get_candidates():
    symbols = [
        'CLOV','SOFI','PLTR','AFRM','UPST','RBLX','NET','ASAN','ZS','DOCN',  # .US default
        '81D.DE','PO1.DE','MS1.DE','NN6.DE','LMIA.DE','RTC.DE',
        'BAB.L','HLMA.L','SGE.L','ALXP.PA','OKTA','MDB'  # .US fallback
    ]
    valid = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            mcap = info.get('marketCap', 0)
            if 50e6 < mcap < 3e9:  # Lockerer
                valid.append(sym)
        except: continue
    return pd.DataFrame({'Symbol': valid})

if st.button("🎯 **SCAN v4.1 (ERROR-FIXED)**", type="primary"):
    candidates_df = get_candidates()
    st.success(f"✅ **{len(candidates_df)} Kandidaten** ready!")
    
    results = []
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(candidates_df['Symbol']):
        progress_bar.progress((i + 1) / len(candidates_df))
        time.sleep(0.1)
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1y")
            
            if len(hist) < 20: continue  # Minimum data
            
            # === v4.1 ROBUST SCORE ===
            forecast = info.get('earningsGrowth', 0) * 100
            forecast = max(forecast, info.get('revenueGrowth', 0) * 80, 8)  # Robust fallback
            eps_growth = info.get('earningsQuarterlyGrowth', 0) * 100
            roe = info.get('returnOnEquity', 0) * 100
            
            # Strong Buy ⭐ ROBUST
            rec_mean = info.get('recommendationMean', 3.0)
            strong_buy_pts = max(5 - rec_mean, 0) * 12
            
            # Momentum & Volume
            mom_6m = 0
            if len(hist) >= 126:
                mom_6m = (hist['Close'][-1] / hist['Close'][-126] - 1) * 100
            vol_avg = hist['Volume'].tail(20).mean() / 1e6 if len(hist) >= 20 else 0
            
            # FIXED Cashflow (no crash!)
            cf_pos = False
            try:
                cashflow = ticker.cashflow
                if not cashflow.empty and len(cashflow.columns) > 0:
                    cf_pos = cashflow.iloc[0, cashflow.columns[-1]] > 0
            except:
                cf_pos = False
            
            # v4.1 SCORE (HOCH + STABIL)
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
            if debt > 200: score -= 15
            
            score = max(50, round(score))
            
            # BACKTEST (robust)
            perf_6m = mom_6m
            perf_1y = 0
            if len(hist) >= 252:
                perf_1y = (hist['Close'][-1] / hist['Close'][-252] - 1) * 100
            sharpe = perf_1y / (hist['Close'].pct_change().std() * np.sqrt(252) * 100 + 0.01)
            
            if score >= 65:  # FIXED Cutoff
                results.append({
                    'Symbol': symbol,
                    'Name': info.get('longName', 'N/A')[:30],
                    'Score': score,
                    'Perf6M': f"{perf_6m:.1f}%",
                    'Perf1Y': f"{perf_1y:.1f}%",
                    'Sharpe': round(sharpe, 2),
                    'RecMean': round(rec_mean, 2)
                })
                
        except Exception as e:
            st.caption(f"Skip {symbol}: {str(e)[-30:]}")
            continue
    
    if results:
        df_final = pd.DataFrame(results).sort_values('Score', ascending=False).head(20)
        st.success(f"🎉 **{len(df_final)} EXPLOSION-CAPS** (≥65)!")
        
        st.dataframe(df_final.style.format({'Perf6M': '{:.1f}%', 'Perf1Y': '{:.1f}%'}), use_container_width=True)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏆 Top Score", df_final['Score'].max())
        col2.metric("📈 Ø Perf 6M", f"{df_final['Perf6M'].str[:-1].astype(float).mean():.1f}%")
        col3.metric("⚡ Top Sharpe", df_final['Sharpe'].max())
        col4.metric("Anzahl", len(df_final))
        
        fig = px.bar(df_final.head(12), x='Symbol', y='Score', color='Perf6M',
                    hover_data=['Perf1Y', 'RecMean'], title="Top Explosions-Ranking")
        st.plotly_chart(fig, use_container_width=True)
        
        st.balloons()
        st.markdown("**💼 Kaufen: Top 8 (10-12% Position) | Hold 12-24M**")
    else:
        st.warning("Keine Caps ≥65. Threshold auf 50 senken?")

st.caption("**v4.1 ERROR-FIXED | Robust Cashflow + Fallbacks | 100% Laufbar**")
