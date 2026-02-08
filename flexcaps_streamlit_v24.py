import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("🚀 **Explosions v6.0 FINAL**")

CANDIDATES = ['PLTR','SOFI','NET','ZS','CLOV','AFRM','UPST','RBLX','ASAN','OKTA']

@st.cache_data(ttl=3600)  # Cache 1h stabile Scores
def get_ticker_data(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info or {}, ticker.history(period="1y"), ticker.cashflow

if st.button("🎯 **v6.0 FINAL SCAN (Top 10 + Perf1Y FIX)**", type="primary"):
    results = []
    bar = st.progress(0)
    
    for i, symbol in enumerate(CANDIDATES):
        bar.progress((i + 1) / len(CANDIDATES))
        time.sleep(0.1)
        
        try:
            info, hist, cf_df = get_ticker_data(symbol)
            
            if len(hist) < 20: continue
            
            # 🛡️ SAFE FUNDAMENTALS
            forecast = max(float(info.get('earningsGrowth', 0))*100, 8)
            eps_growth = max(float(info.get('earningsQuarterlyGrowth', 0))*100, -15)
            roe = max(float(info.get('returnOnEquity', 0))*100, -5)
            
            rec_mean = float(info.get('recommendationMean', 3.0))
            strong_buy_pts = min(max(5 - rec_mean, 0) * 12, 60)
            
            # 🆕 FIX: Robuste Perf6M/1Y
            mom_6m = 0
            perf_1y = 0
            if len(hist) >= 126:
                days_back_6m = min(126, len(hist)-1)
                mom_6m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-days_back_6m]) - 1) * 100
                
                days_back_1y = min(252, len(hist)-1)
                perf_1y = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-days_back_1y]) - 1) * 100
            
            vol_avg = max(float(hist['Volume'].tail(20).mean() / 1e6), 0.1)
            
            cf_pos = False
            try:
                if not cf_df.empty and len(cf_df.columns):
                    latest_cf = float(cf_df.iloc[0][cf_df.columns[-1]])
                    cf_pos = latest_cf > 0
            except: pass
            
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
            
            # 🛡️ SHORT SQUEEZE SAFE
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
            
            sector = info.get('sector', 'N/A')
            
            # 🆕 IMMER Top 10 + OPTIMIZED TIMING
            if rally_score >= 100:  # Min für Ranking
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
                    'Perf6M_%': round(mom_6m, 1),
                    'Perf1Y_%': round(perf_1y, 1),
                    'Sector': sector,
                    'Timing': timing
                })
        except Exception as e:
            continue
    
    if results:
        df_final = pd.DataFrame(results).sort_values('RallyScore', ascending=False)
        buy_now = len(df_final[df_final['Timing'] == '🚀 BUY NOW'])
        st.success(f"✅ **{len(df_final)} TOP CAPS** | {buy_now}x 🚀 BUY NOW | Score: {df_final['RallyScore'].max()}")
        
        st.subheader("🥇 **Explosions-Ranking (Top 10)**")
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
        st.dataframe(top5, use_container_width=True)
        
        st.balloons()
        st.markdown("""
        **🎯 NEXT STEPS**:
        1. 🚀 BUY NOW: Rally>160+ oder Short>8%
        2. Premarket Vol-Spike checken
        3. 12% Position pro Cap
        **v6.0 FINAL: 10 Caps + Perf1Y + Stable!**
        """)
    else:
        st.info("Keine qualifizierten Caps (Score <100).")

st.caption("**v6.0 FINAL | Top10 | Perf1Y Fix | Cache | Optimized BUY**")
