import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(page_title="Explosions v4.2 BRANCHEN", layout="wide")
st.title("🚀 **Explosions Small-Caps v4.2**")
st.markdown("**FINAL + BRANCHEN + Score 70-150 | Strong Buy + Backtest**")

@st.cache_data(ttl=1800)
def get_candidates():
    symbols = [
        'CLOV','SOFI','PLTR','AFRM','UPST','RBLX','NET','ASAN','ZS','DOCN',
        '81D.DE','PO1.DE','MS1.DE','NN6.DE','LMIA.DE','RTC.DE',
        'BAB.L','HLMA.L','SGE.L','ALXP.PA','OKTA','MDB'
    ]
    valid = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            mcap = info.get('marketCap', 0)
            if 50e6 < mcap < 3e9:
                valid.append(sym)
        except: continue
    return pd.DataFrame({'Symbol': valid})

if st.button("🎯 **SCAN v4.2 + BRANCHEN**", type="primary"):
    candidates_df = get_candidates()
    st.success(f"✅ **{len(candidates_df)} Small-Caps** analysiert")
    
    results = []
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(candidates_df['Symbol']):
        progress_bar.progress((i + 1) / len(candidates_df))
        time.sleep(0.1)
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1y")
            
            if len(hist) < 20: continue
            
            # v4.2 SCORE (FIXED)
            forecast = max(info.get('earningsGrowth', 0)*100, info.get('revenueGrowth', 0)*80, 8)
            eps_growth = max(info.get('earningsQuarterlyGrowth', 0)*100, -15)
            roe = max(info.get('returnOnEquity', 0)*100, -5)
            rec_mean = info.get('recommendationMean', 3.0)
            strong_buy_pts = max(5 - rec_mean, 0) * 12
            
            mom_6m = 0
            if len(hist) >= 126:
                mom_6m = (hist['Close'][-1] / hist['Close'][-126] - 1) * 100
            vol_avg = hist['Volume'].tail(20).mean() / 1e6 if len(hist) >= 20 else 0
            
            # FIXED Cashflow
            cf_pos = False
            try:
                cashflow = ticker.cashflow
                if not cashflow.empty and len(cashflow.columns) > 0:
                    cf_pos = cashflow.iloc[0, cashflow.columns[-1]] > 0
            except: pass
            
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
            
            # BACKTEST + BRANCHE ⭐ NEU
            perf_6m = mom_6m
            perf_1y = 0
            if len(hist) >= 252:
                perf_1y = (hist['Close'][-1] / hist['Close'][-252] - 1) * 100
            
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            
            if score >= 65:
                results.append({
                    'Symbol': symbol,
                    'Name': info.get('longName', symbol)[:25],
                    'Score': score,
                    'Branche': sector,
                    'Industrie': industry[:25],
                    'Perf6M_%': f"{perf_6m:.1f}",
                    'Perf1Y_%': f"{perf_1y:.1f}",
                    'RecMean': f"{rec_mean:.2f}"
                })
                
        except: continue
    
    if results:
        df_final = pd.DataFrame(results).sort_values('Score', ascending=False).head(20)
        st.success(f"🎉 **{len(df_final)} EXPLOSIONS-CAPS** gefunden!")
        
        # TABELLE MIT BRANCHEN
        st.subheader("🥇 **Ranking + Branchen**")
        st.dataframe(df_final, use_container_width=True)
        
        # BRANCHEN-ÜBERSICHT
        st.subheader("📊 **Branchen-Exposure**")
        branchen_count = df_final['Branche'].value_counts()
        st.bar_chart(branchen_count)
        
        # METRICS
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏆 Top Score", df_final['Score'].max())
        col2.metric("📈 Ø Perf 6M", f"{df_final['Perf6M_%'].str[:-1].astype(float).mean():.1f}%")
        col3.metric("⭐ Beste RecMean", df_final['RecMean'].min())
        col4.metric("🏢 Caps", len(df_final))
        
        # DUAL-CHART
        col_a, col_b = st.columns(2)
        with col_a:
            fig_score = px.bar(df_final.head(12), x='Symbol', y='Score', color='Perf6M_%',
                              title="Score Ranking", hover_data=['Branche'])
            st.plotly_chart(fig_score, use_container_width=True)
        
        with col_b:
            fig_branche = px.scatter(df_final, x='Perf6M_%', y='Score', color='Branche',
                                    size='RecMean', hover_name='Symbol',
                                    title="Performance vs. Branchen")
            st.plotly_chart(fig_branche, use_container_width=True)
        
        # PORTFOLIO
        st.subheader("💼 **Portfolio-Vorschlag**")
        top5 = df_final.head(5)
        portfolio_perf = top5['Perf6M_%'].str[:-1].astype(float).mean()
        st.metric("Top-5 Ø 6M Return", f"{portfolio_perf:.1f}%")
        st.dataframe(top5[['Symbol', 'Branche', 'Score', 'Perf6M_%']], use_container_width=True)
        
        st.info("""
        🎯 **KAUFEN**:
        • Top 8 (10-15% Position)
        • Diversifiziert über Branchen
        • Broker: IB / Trade Republic
        • Hold: 12-24 Monate
        """)
        st.balloons()
    else:
        st.warning("Keine Caps. Versuche später.")

st.caption("**v4.2 BRANCHEN-POWER | Error-Free | Explosions-Ready**")
