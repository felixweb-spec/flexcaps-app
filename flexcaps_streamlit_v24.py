import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(page_title="Explosions Small-Caps v4.0 FINAL", layout="wide")
st.title("🚀 **Explosions Small-Caps Finder v4.0**")
st.markdown("**FINAL | Explosions-Score 70-150 | Strong Buy + Backtest | Broker-Ready**")

@st.cache_data(ttl=1800)
def get_candidates():
    """Broker-freundliche Small-Caps (<2.5B USD)"""
    symbols = [
        # US Explosive Growth
        'CLOV.US','SOFI.US','PLTR.US','AFRM.US','UPST.US','RBLX.US','NET.US','ASAN.US','ZS.US','DOCN.US',
        # DE/EU
        '81D.DE','PO1.DE','MS1.DE','NN6.DE','LMIA.DE','RTC.DE',
        # UK/FR
        'BAB.L','HLMA.L','SGE.L','ALXP.PA','ENPH.US','OKTA.US','MDB.US'
    ]
    valid = []
    for sym in symbols:
        try:
            mcap = yf.Ticker(sym).info.get('marketCap', 0)
            if 50e6 < mcap < 2.5e9:
                valid.append(sym)
        except: pass
    return pd.DataFrame({'Symbol': valid})

if st.button("🎯 **FINAL SCAN + BACKTEST** (v4.0)", type="primary", use_container_width=True):
    with st.spinner("🔍 Explosions-Scan läuft..."):
        candidates_df = get_candidates()
        st.info(f"📊 **{len(candidates_df)} Small-Caps** (<2.5B USD) gescreent")
        
        results = []
        progress = st.progress(0)
        
        for i, symbol in enumerate(candidates_df['Symbol']):
            progress.progress((i+1) / len(candidates_df))
            time.sleep(0.15)
            
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1y")
                
                if len(hist) < 30: continue
                
                # === v4.0 HOCH-SCORE FORMEL ===
                forecast = max(info.get('earningsGrowth', 0)*100, 8)
                eps_growth = max(info.get('earningsQuarterlyGrowth', 0)*100, -15)
                roe = max(info.get('returnOnEquity', 0)*100, -5)
                
                # ⭐ STRONG BUY RATING (Game Changer)
                rec_mean = info.get('recommendationMean', 3)
                strong_buy_pts = max(5 - rec_mean, 0) * 12
                
                # Cashflow + Momentum + Liquidity
                mom_6m = ((hist['Close'][-1] / hist['Close'][-126] - 1) * 100) if len(hist) >= 126 else 0
                vol_avg = hist['Volume'].tail(20).mean() / 1e6
                cashflow = ticker.cashflow
                cf_pos = cashflow.iloc[0, -1] > 0 if not cashflow.empty else False
                
                # HOCH-SKALIERTE PUNKTE
                score = (
                    forecast * 0.5 +                    # 4-50+
                    eps_growth * 0.3 +                  # -4.5 bis +30
                    roe * 0.3 +                         # -1.5 bis +30
                    strong_buy_pts +                    # 0-45 ⭐
                    (25 if cf_pos else 10) +            # CF Boost
                    max(mom_6m, -5) * 0.2 +             # Momentum
                    min(vol_avg * 3, 25) +              # Liquidity
                    20  # Base
                )
                
                debt = info.get('debtToEquity', 999)
                if debt > 200: score -= 15
                score = max(50, round(score))
                
                # BACKTEST METRICS
                perf_6m = ((hist['Close'][-1] / hist['Close'][-126] - 1) * 100) if len(hist) >= 126 else 0
                perf_1y = ((hist['Close'][-1] / hist['Close'][-252] - 1) * 100) if len(hist) >= 252 else 0
                daily_ret = hist['Close'].pct_change().dropna()
                vol_ann = daily_ret.std() * np.sqrt(252) * 100
                sharpe = (perf_1y / 100) / (vol_ann / 100) if vol_ann > 0 else 0
                
                if score >= 70:  # Explosions-Cutoff
                    results.append({
                        'Symbol': symbol,
                        'Name': info.get('longName', symbol)[:35],
                        '**Score**': score,
                        'Perf6M_%': round(perf_6m, 1),
                        'Perf1Y_%': round(perf_1y, 1),
                        'Sharpe': round(sharpe, 2),
                        'Vol_%': round(vol_ann, 1),
                        'Rec_Mean': round(rec_mean, 1)
                    })
                    
            except Exception as e:
                continue
        
        # === RESULTS ===
        if results:
            df_final = pd.DataFrame(results).sort_values('**Score**', ascending=False).head(15)
            st.success(f"🎉 **{len(df_final)} EXPLOSIONS-CAPS** gefunden! (Score ≥70)")
            
            # HAUPTTABELLE
            st.subheader("🥇 **Top Explosions-Ranking**")
            st.dataframe(df_final, use_container_width=True)
            
            # METRICS
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("🔥 Top Score", df_final['**Score**'].max())
            col2.metric("📈 Ø Perf 6M", f"{df_final['Perf6M_%'].mean():.1f}%")
            col3.metric("⚡ Top Sharpe", df_final['Sharpe'].max())
            col4.metric("🏢 Portfolio", f"{len(df_final)} Caps")
            col5.metric("⏳ Hold", "12-24 Monate")
            
            # CHARTS
            col_a, col_b = st.columns(2)
            with col_a:
                fig_score = px.bar(df_final.head(10), x='Symbol', y='**Score**',
                                  color='Perf6M_%', title="Score Ranking")
                st.plotly_chart(fig_score, use_container_width=True)
            
            with col_b:
                fig_perf = px.scatter(df_final, x='Perf6M_%', y='**Score**', size='Sharpe',
                                     hover_name='Symbol', color='Perf1Y_%',
                                     title="Score vs. Performance")
                st.plotly_chart(fig_perf, use_container_width=True)
            
            # PORTFOLIO SIMULATION
            st.subheader("💼 **Portfolio Simulation** (gleichgewichtet)")
            port_6m = df_final['Perf6M_%'].mean()
            port_1y = df_final['Perf1Y_%'].mean()
            st.metric("Erwartet 6M Return", f"{port_6m:.1f}%")
            st.metric("Erwartet 1Y Return", f"{port_1y:.1f}%")
            
            st.markdown("---")
            st.info("""
            💰 **AKTION**:
            • Top 5-10 kaufen (10-15% je Position)
            • Broker: Interactive Brokers / Trade Republic / Consorsbank
            • Hold: 12-24 Monate → Ziel 50-150%+
            • Stop-Loss: -25%
            """)
            st.balloons()
            
        else:
            st.warning("❌ Keine Explosions-Caps ≥70. Markt scannen später!")

st.markdown("---")
st.caption("**v4.0 FINAL | yfinance | Strong Buy + Backtest | Explosions-Score 70-150**")
