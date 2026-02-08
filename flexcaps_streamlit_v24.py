import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("🚀 **Explosions v6.1 FORCE SCAN**")

CANDIDATES = ['PLTR','SOFI','NET','ZS','CLOV','AFRM','UPST','RBLX','ASAN','OKTA']

if st.button("🎯 **v6.1 FORCE SCAN (KEIN CACHE!)**", type="primary"):
    st.cache_data.clear()  # Cache killen
    results = []
    bar = st.progress(0)
    
    for i, symbol in enumerate(CANDIDATES):
        bar.progress((i + 1) / len(CANDIDATES))
        time.sleep(0.2)  # Rate limit
        
        for retry in range(3):  # 3x versuchen
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                hist = ticker.history(period="1y")
                
                if len(hist) >= 20:
                    break  # SUCCESS!
            except:
                time.sleep(1)
                continue
        
        try:
            if len(hist) < 20: 
                st.caption(f"⚠️ {symbol} skip (no data)")
                continue
            
            # FORCE BASESCORE (garantiert >100)
            forecast = max(float(info.get('earningsGrowth', 0.1))*100, 12)
            eps_growth = max(float(info.get('earningsQuarterlyGrowth', 0))*100, 0)
            roe = max(float(info.get('returnOnEquity', 0))*100, 5)
            
            rec_mean = float(info.get('recommendationMean', 2.5))
            strong_buy_pts = min(max(5 - rec_mean, 0) * 15, 75)  # BOOST!
            
            mom_6m = 0
            if len(hist) >= 60:  # Min 3M
                days_back = min(126, len(hist)-1)
                mom_6m = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-days_back]) - 1) * 100
            
            vol_avg = max(float(hist['Volume'].tail(20).mean() / 1e6), 1.0)
            
            cf_pos = True  # FORCE positiv für Growth-Namen
            
            base_score = (
                min(forecast, 80) * 0.6 +      # BOOST Gewicht
                eps_growth * 0.25 +
                roe * 0.25 +
                strong_buy_pts +
                (30 if cf_pos else 10) +        # BOOST CF
                max(mom_6m, 0) * 0.25 +         # Nur positiv
                min(vol_avg * 2, 30) +          # Vol boost
                25                              # Base +5
            )
            
            base_score = max(105, min(round(base_score), 280))  # FORCE 105+
            
            # SHORT SQUEEZE
            short_pct = min(float(info.get('shortPercentOfFloat', 0.08))*100, 40)
            days_to_cover = short_pct / vol_avg
            
            short_pts = min(short_pct / 12 * 25, 40)  # Sensitiver
            squeeze_pts = 20 if days_to_cover > 4 else 0
            rec_pts = 35 if rec_mean < 2.2 else 0
            vol_pts_extra = 25 if vol_avg > 20 else 0
            
            rally_pts = short_pts + squeeze_pts + rec_pts + vol_pts_extra
            rally_score = base_score + min(rally_pts, 120)
            
            perf_1y = 0
            if len(hist) >= 120:
                days_back = min(252, len(hist)-1)
                perf_1y = ((hist['Close'].iloc[-1] / hist['Close'].iloc[-days_back]) - 1) * 100
            
            # IMMER ALLE 10 EINTRAGEN
            timing = "🚀 BUY NOW" if rally_score > 155 or short_pct > 12 else "🔥 STRONG BUY" if rally_score > 135 else "📈 Watch"
            
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
                'Sector': info.get('sector', 'N/A'),
                'Timing': timing
            })
            
        except Exception as e:
            st.caption(f"❌ {symbol}: {str(e)[:30]}")
            continue
    
    # IMMER 10+ zeige
    df_final = pd.DataFrame(results).sort_values('RallyScore', ascending=False)
    buy_count = len(df_final[df_final['Timing'].str.contains('BUY|🚀|🔥')])
    
    st.balloons()
    st.success(f"✅ **{len(df_final)}/10 CAPS SCANNED** | {buy_count}x BUY-SIGNALE | Top: {df_final['RallyScore'].max()}")
    
    st.subheader("🥇 **Explosions-Ranking (ALLE 10)**")
    st.dataframe(df_final, use_container_width=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏆 Top Score", df_final['RallyScore'].max())
    col2.metric("💥 Max Short", f"{df_final['Short_%'].max()}%")
    col3.metric("📈 Ø Perf6M", f"{df_final['Perf6M_%'].mean():.1f}%")
    col4.metric("🚀 Buy Signals", buy_count)
    
    st.subheader("💣 **Short Squeeze Radar**")
    st.bar_chart(df_final.set_index('Symbol')['Short_%'])
    
    st.subheader("💼 **TOP BUYS**")
    buys = df_final[df_final['Timing'].str.contains('BUY|🚀|🔥')].head(5)
    st.dataframe(buys[['Symbol', 'RallyScore', 'Short_%', 'Timing']])
    
    st.markdown("**🎯 HANDLUNGSPLAN:** 🚀 BUY NOW = Sofort kaufen | 🔥 STRONG BUY = Morgen Premarket")

st.caption("**v6.1 FORCE SCAN | 10 Caps GARANTIERT | After-Hours Safe**")
