import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title='FlexCapsAnalytics v2.4', layout='wide')

st.title('🏆 FlexCapsAnalytics v2.4 - WKN + BACKTEST')
st.markdown('**DE-Broker Ready | Score >90 = BUY**')

uploaded = st.file_uploader('📁 flexcaps_app_v24.json hochladen', type='json')

if uploaded:
    data = json.load(uploaded)
    df_top = pd.DataFrame(data['top_10'])
    backtest_data = pd.DataFrame(data['backtest']['data'])

    tab1, tab2, tab3 = st.tabs(['Top 10 Live', 'Backtest', 'Charts'])

    with tab1:
        st.subheader('Top 10 Small Caps (FlexCaps Score)')
        st.dataframe(
            df_top.sort_values('Flex_v2_Score', ascending=False),
            use_container_width=True
        )
        col1, col2 = st.columns(2)
        col1.metric('Top Score', df_top['Flex_v2_Score'].max())
        col2.metric('#1 Pick', df_top.iloc[0]['Ticker'])

    with tab2:
        st.subheader(f"Backtest {data['backtest']['period']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric('Total Return', f"+{data['backtest']['total_return']:.1f}%")
        col2.metric('vs S&P500', f"+{data['backtest']['vs_sp500']:.1f}%")
        col3.metric('Win-Rate', f"{data['backtest']['win_rate']:.0f}%")
        col4.metric('Best Trade', f"{backtest_data['Return_%'].max():.1f}%")
        st.dataframe(backtest_data)

    with tab3:
        st.subheader('Scores & Returns')
        fig = px.bar(df_top.head(5), x='Ticker', y='Flex_v2_Score', title='Top 5 Scores')
        st.plotly_chart(fig, use_container_width=True)
        fig2 = px.bar(backtest_data, x='Ticker', y='Return_%', title='Backtest Returns')
        st.plotly_chart(fig2, use_container_width=True)

    if st.button('🚀 BUY-Signal Top 3!'):
        top3 = df_top.head(3)
        picks = [f"{row.Ticker} ({row.WKN})" for row in top3.itertuples()]
        st.success('BUY: ' + ', '.join(picks))
        st.balloons()

    st.caption(data.get('formula', ''))
else:
    st.info('📥 Lade flexcaps_app_v24.json hoch, um die Analyse zu sehen.')
