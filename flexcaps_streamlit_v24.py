import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Global FlexCaps v3.2", layout="wide")
st.title("🌍 **GLOBAL Explosions Small-Caps v3.2**")
st.markdown("**Small-Caps (<2B USD) | Handelbar via IB/Consors/TR | 12-24M Hold**")

FMP_KEY = "demo"

if st.button("🚀 **TOP 10 GLOBAL ELITE** (MIN Score 80)", type="primary", use_container_width=True):
    with st.spinner("🔍 Globale Small-Caps + Multi-Exchange-Scan..."):
        @st.cache_data(ttl=1800)
        def load_smallcaps():
            # Globale Small-Cap Movers (US/INT focus, broker-freundlich)
            urls = [
                "https://www.tradingview.com/markets/stocks-usa/market-movers-small-cap/",
                "https://www.tradingview.com/markets/stocks-usa/market-movers-best-performing/",
                "https://www.tradingview.com/markets/stocks-europe/market-movers-small-cap/"
            ]
            all_symbols = []
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            for url in urls:
                resp = requests.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                rows = soup.select('tr[class*="row"]')[:30]
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) > 6:
                        symbol_a = cells[0].find('a')
                        symbol = symbol_a.text.strip() if symbol_a else ''
                        rec = cells[-1].text.strip()
                        if 'Strong buy' in rec and symbol and '.' not in symbol:  # Base symbol
                            # Broker-freundlich: US(.US), UK(.L), DE(.DE), FR(.PA), etc.
                            exts = ['.US', '.L', '.DE', '.PA', '.AS', '.FP']
                            for ext in exts:
                                all_symbols.append(symbol + ext)
            return pd.DataFrame({'Symbol': list(set(all_symbols))[:100]})  # Unique top 100

        candidates_df = load_smallcaps()
        candidates = candidates_df['Symbol'].tolist()
        results = []

        for i, symbol in enumerate(candidates):
            if i >= 50: break  # Limit für Speed
            st.progress(i / 50, text=f"🔎 {symbol}...")
            time.sleep(0.3)

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="6mo")

                # Market Cap Filter: Small-Cap <2B USD
                mcap = info.get('marketCap', 0)
                if mcap > 2e9 or mcap < 100e6: continue  # 100M-2B

                if len(hist) < 20: continue

                forecast_growth = info.get('earningsGrowth', 0) * 100 or info.get('revenueGrowth', 0) * 100
                eps_growth = info.get('earningsQuarterlyGrowth', 0) * 100
                strong_buy_count = 5

                # FMP
                fmp_forecast = forecast_growth
                try:
                    fmp_url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{symbol.replace('.','')}?apikey={FMP_KEY}"
                    fmp = requests.get(fmp_url, timeout=5).json()
                    if fmp: fmp_forecast = fmp[0].get('growthEstimate', forecast_growth)
                except: pass

                forecasts = [f for f in [forecast_growth, fmp_forecast] if f > 0]
                validated_forecast = np.mean(forecasts) if forecasts else 0

                if validated_forecast < 15: continue  # Global niedriger Threshold

                debt_equity = info.get('debtToEquity', 999)
                roe = info.get('returnOnEquity', 0) * 100
                momentum_3m = ((hist['Close'][-1] / hist['Close'][-13] - 1) * 100) if len(hist) >= 13 else 0

                # Cashflow fixed
                cashflow = ticker.cashflow
                cashflow_pos = False
                if not cashflow.empty and len(cashflow.columns):
                    latest = cashflow.iloc[:, -1]
                    op_cf = latest.get('Total Cash From Operating Activities', latest.get('Operating Cash Flow', 0))
                    cashflow_pos = op_cf > 0

                # Enhanced Score + Volume (broker-liq)
                volume_avg = hist['Volume'].tail(20).mean() / 1e6
                liquidity_bonus = min(20, volume_avg * 0.1) if volume_avg > 0.5 else 0

                base_score = (
                    validated_forecast * 0.35 +
                    eps_growth * 0.20 +
                    strong_buy_count * 12 +
                    (15 if cashflow_pos else 0) +
                    max(roe, 0) * 0.10 +
                    max(momentum_3m, 0) * 0.08 +
                    liquidity_bonus
                )
                penalty = 0
                if debt_equity > 150: penalty -= 25  # Global höher tol.
                if momentum_3m < 0: penalty -= 15
                final_score = max(0, base_score + penalty)

                if final_score >= 80:
                    results.append({
                        'Symbol': symbol,
                        'Name': info.get('longName', symbol)[:35],
                        'MarketCap': f"${mcap/1e9:.1f}B",
                        'Forecast': f"{validated_forecast:.1f}%",
                        'EPS': f"{eps_growth:.1f}%",
                        'ROE': f"{roe:.1f}%",
                        'Vol(M)': f"{volume_avg:.1f}",
                        'Score': round(final_score)
                    })

            except: continue

        if results:
            df_final = pd.DataFrame(results).sort_values('Score', ascending=False).head(10)
            st.success(f"🎉 **{len(df_final)} GLOBAL ELITE Small-Caps gefunden!** (Handelbar: IB/Consors/TR)")
            st.dataframe(df_final, use_container_width=True)

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("📈 Ø Forecast", f"{df_final['Forecast'].str[:-1].astype(float).mean():.1f}%")
            col2.metric("💰 Top Score", df_final['Score'].max())
            col3.metric("🏢 Anzahl", len(df_final))
            col4.metric("🌍 Ø Marktkap", df_final['MarketCap'].str.extract('(\d\.\d)').astype(float).mean().round(1).astype(str) + "B")
            col5.metric("⏳ Hold", "12-24M")

            fig = px.bar(df_final, x='Symbol', y='Score', color='Forecast',
                         hover_data=['MarketCap', 'EPS', 'Vol(M)'],
                         title="🥇 Global Top 10 Explosions Small-Caps")
            st.plotly_chart(fig, use_container_width=True)

            st.info("💼 **Broker-Tipp**: Interactive Brokers/Trade Republic für US/EU. Gleichgew. Portfolio bauen!")
            st.balloons()
        else:
            st.warning("❌ Keine Elite ≥80. Mehr Volumen/Threshold anpassen.")

st.caption("**v3.2 GLOBAL | Multi-Exchange + Liq-Filter + MCap <2B | yf + TV**")[web:1]
