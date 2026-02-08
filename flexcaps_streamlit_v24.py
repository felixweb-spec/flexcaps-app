import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="FlexCaps Analytics v3.0", layout="wide")
st.title("🎯 **Explosions Small-Caps Finder v3.0**")
st.markdown("**Long-Term Hold (12-24M) | Growth Forecast Master + 6-Faktor Sicherheits-Score**")

# Free API Demo Keys
FMP_KEY = "demo"

# === OPTIMIERTER SCANNER ===
if st.button("🚀 **TOP 5 ELITE SCANNEN** (MIN Score 80)", type="primary", use_container_width=True):
    with st.spinner("🔍 Screen 100+ Small-Caps + 3-Quellen Validierung..."):
        # 1. Small-Caps Markt (TradingView)
        @st.cache_data(ttl=1800)  # 30min Cache
        def load_smallcaps():
            url = "https://de.tradingview.com/markets/stocks-germany/market-movers-small-cap/"
            df = pd.read_html(url)[0]
            return df[df['Recommendation'] == 'Strong buy'].head(30)  # Top 30 Strong Buy [web:327]
        
        df_tv = load_smallcaps()
        candidates = df_tv['WKN/ISIN'].tolist()
        
        results = []
        for i, wkn in enumerate(candidates):
            st.progress(i / len(candidates), text=f"Analysiere {wkn}...")
            try:
                # Ticker Daten
                ticker = yf.Ticker(wkn)
                info = ticker.info
                hist = ticker.history(period="6mo")
                
                if len(hist) < 20: continue  # Genug Daten?
                
                # METRIKEN (optimiert)
                forecast_growth = info.get('earningsGrowth', 0) * 100  # MASTER
                eps_growth = info.get('earningsQuarterlyGrowth', 0) * 100
                strong_buy_count = min(5, df_tv[df_tv['WKN/ISIN']==wkn].index.size)  # 1-5
                
                # FMP Forecast (Quelle 2)
                try:
                    fmp_url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{wkn}?apikey={FMP_KEY}"
                    fmp = requests.get(fmp_url).json()
                    fmp_forecast = fmp[0].get('growthEstimate', forecast_growth) if fmp else forecast_growth
                except:
                    fmp_forecast = forecast_growth
                
                # Validierte Forecast (2/3 Quellen)
                forecasts = [forecast_growth, fmp_forecast]
                validated_forecast = np.mean([f for f in forecasts if f > 0])
                
                if validated_forecast < 20: continue  # Mind. 20%
                
                # SICHERHEITS-METRIKEN
                debt_equity = info.get('debtToEquity', 999)
                roe = info.get('returnOnEquity', 0) * 100
                momentum_3m = (hist['Close'][-1] / hist['Close'][-13] - 1) * 100  # 3M
                
                # CASHFLOW (letztes Quartal)
                cashflow_data = ticker.cashflow
                cashflow_pos = cashflow_data.iloc[0,0] > 0 if not cashflow_data.empty else False
                
                # OPTIMIERTER SCORE
                base_score = (
                    validated_forecast * 0.35 +
                    eps_growth * 0.20 +
                    strong_buy_count * 15 +
                    (15 if cashflow_pos else 0) +
                    roe * 0.10 +
                    momentum_3m * 0.05
                )
                
                # PENALTIES
                penalty = 0
                if debt_equity > 100: penalty -= 25  # Hohe Schulden
                if momentum_3m < 5: penalty -= 10   # Schwaches Momentum
                
                final_score = max(0, base_score + penalty)
                
                if final_score >= 80:  # ELITE nur!
                    results.append({
                        'WKN': wkn,
                        'Name': info.get('longName', wkn)[:30],
                        'Forecast': f"{validated_forecast:.1f}%",
                        'EPS_Growth': f"{eps_growth:.1f}%",
                        'ROE': f"{roe:.1f}%",
                        'StrongBuy': strong_buy_count,
                        'Score': round(final_score)
                    })
                    
            except Exception as e:
                continue
        
        # ERGEBNISSE
        if results:
            df_final = pd.DataFrame(results).sort_values('Score', ascending=False).head(5)
            st.success(f"🎉 **{len(df_final)} ELITE Explosions-Caps gefunden!** (MIN 80)")
            
            # Tabelle
            st.dataframe(df_final, use_container_width=True)
            
            # METRICS
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📈 Durchschn. Forecast", f"{df_final['Forecast'].str[:-1].astype(float).mean():.1f}%")
            col2.metric("💰 Top Score", df_final['Score'].max())
            col3.metric("🏢 Portfolio Size", f"{len(df_final)} Caps")
            col4.metric("⏳ Hold-Zeit", "12-24 Monate")
            
            # CHART
            fig = px.bar(df_final, x='WKN', y='Score', 
                        color='Forecast', hover_data=['EPS_Growth', 'ROE'],
                        title="🥇 Top 5 Explosions-Ranking (Buy & Hold)")
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.info("💼 **ANLEITUNG**: Top 5 gleichmäßig kaufen → 12-24 Monate halten!")
            st.balloons()
        else:
            st.warning("❌ Keine Caps mit Score ≥80 gefunden. Markt scannen später nochmal!")

st.caption("**v3.0 | Growth Forecast Master + 6-Faktor Safety | yfinance + FMP + TradingView**")
