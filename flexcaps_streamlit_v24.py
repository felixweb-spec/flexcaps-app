import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

# =========================
# Global Pre-Rally Scanner
# v7.2 BALANCED+ (static markets dropdown)
# =========================

st.set_page_config(layout="wide")
st.title("🌍 Global Smallcap Pre-Rally Scanner — v7.2 (BALANCED+)")

# -------------------------
# 1) STATIC UNIVERSES (Dropdown)
# -------------------------
UNIVERSES = {
    "USA – Smallcaps (Tech/Growth)": [
        "PLTR", "SOFI", "AFRM", "UPST", "RBLX", "ASAN", "OKTA",
        "IONQ", "PATH", "AI", "DDOG", "NET"
    ],
    "Canada – Smallcaps": [
        "SHOP.TO", "LSPD.TO", "CTS.TO", "WELL.TO",
        "ABCL.TO", "VET.TO"
    ],
    "Germany – Smallcaps": [
        "S92.DE", "HFG.DE", "EVT.DE", "AT1.DE", "NDX1.DE"
    ],
    "Europe – Smallcaps": [
        "NEL.OL", "SINCH.ST", "AUTO.L", "DSV.CO"
    ],
    "Australia – Smallcaps": [
        "BHP.AX", "MIN.AX", "PLS.AX", "LTR.AX", "IGO.AX"
    ],
    "Japan – Growth": [
        "4385.T", "4477.T", "3659.T", "3902.T"
    ],
    "China / Hong Kong": [
        "9988.HK", "3690.HK", "9868.HK", "1810.HK"
    ],
    "Global – Mixed (Demo)": [
        "PLTR", "SHOP.TO", "S92.DE", "BHP.AX",
        "9988.HK", "MIN.AX", "4385.T"
    ],
}

# -------------------------
# 2) Region Benchmarks for RS (best effort)
# -------------------------
REGION_BENCH = {
    "USA": "IWM", "US": "IWM",
    "Canada": "EWC",
    "Germany": "EWG",
    "Europe": "VGK",
    "UK": "EWU",
    "Japan": "EWJ",
    "China / Hong Kong": "MCHI",
    "Australia": "EWA",
    "Global": "ACWI",
}

# -------------------------
# Helpers
# -------------------------
def clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))

def safe_div(a, b):
    try:
        if b is None or b == 0 or not np.isfinite(b):
            return np.nan
        return a / b
    except:
        return np.nan

def pct_change(series: pd.Series, periods: int):
    if series is None or len(series) <= periods:
        return np.nan
    return (series.iloc[-1] / series.iloc[-(periods + 1)] - 1.0) * 100.0

def percentile_rank(values: pd.Series):
    v = values.astype(float)
    ranks = v.rank(pct=True, na_option="bottom")
    return ranks.fillna(0.0).clip(0.0, 1.0)

def calc_atr_pct(df_ohlc: pd.DataFrame, n=14):
    if df_ohlc is None or len(df_ohlc) < n + 2:
        return np.nan
    high = df_ohlc["High"].astype(float)
    low = df_ohlc["Low"].astype(float)
    close = df_ohlc["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(n).mean()
    return safe_div(atr.iloc[-1], close.iloc[-1]) * 100.0

def get_info_fields(symbol: str):
    # Only for top-N to reduce slowness / missing key chaos
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        rec_mean = info.get("recommendationMean", np.nan)
        short_pct = info.get("shortPercentOfFloat", np.nan)
        sector = info.get("sector", "N/A")
        name = (info.get("longName") or symbol)[:40]
        return {
            "Name": name,
            "Sector": sector,
            "RecMean": float(rec_mean) if rec_mean is not None else np.nan,
            "Short_%": float(short_pct) * 100.0 if short_pct is not None else np.nan,
        }
    except:
        return {"Name": symbol, "Sector": "N/A", "RecMean": np.nan, "Short_%": np.nan}

# -------------------------
# Sidebar controls (Final criteria)
# - Static dropdown markets
# - Balanced+ thresholds (more signals, but still sane)
# - Batch OHLCV download
# - Optional catalysts only for Top N
# -------------------------
with st.sidebar:
    st.header("🌍 Markt-Auswahl (statisch)")
    market = st.selectbox("Markt / Region", list(UNIVERSES.keys()), index=0)
    symbols = UNIVERSES[market]
    st.caption(f"📊 Universe Size: {len(symbols)}")

    st.divider()
    st.subheader("🧪 Scanner-Mode: BALANCED+")
    st.caption("Setup dominiert (Preis/Volumen/RS). Catalyst (Short/Rec) nur als Bonus für Top N.")

    # Core minimum history
    days_required = st.slider("Min History Days", 80, 260, 120, 10)

    # Filters (light, global-friendly)
    price_min = st.number_input("Min Last Price", value=2.0, step=0.5)
    usd_vol_min = st.number_input("Min Avg $Volume (20d)", value=2_000_000, step=250_000)

    # Signal thresholds (BALANCED+)
    pre_setup_min = st.slider("PRE-BREAKOUT: min SetupScore", 40, 80, 58)
    pre_near_max = st.slider("PRE-BREAKOUT: max % below high", 2.0, 15.0, 8.0, 0.5)
    pre_atr_max = st.slider("PRE-BREAKOUT: max ATR% (14)", 2.0, 10.0, 5.5, 0.5)

    # Catalysts
    topn_info = st.slider("Fetch Rec/Short for Top N (slower)", 0, 25, 5)

st.subheader(f"🔍 Aktiver Markt: {market}")
st.caption("Hinweis: Das ist kein Finanzrat. Scanner liefert Setups/Beobachtungskandidaten, keine Anlageberatung.")

# -------------------------
# Main run
# -------------------------
if st.button("🎯 FORCE SCAN (Batch OHLCV, BALANCED+)", type="primary"):
    st.cache_data.clear()

    # Choose benchmark for RS (best effort)
    bench = REGION_BENCH.get(market.split("–")[0].strip(), REGION_BENCH.get(market, "ACWI"))
    # Also handle exact keys
    bench = REGION_BENCH.get(market, bench)

    # Batch download symbols + benchmark
    tickers = list(dict.fromkeys(symbols + ([bench] if bench else [])))
    st.info(f"Downloading 1Y daily OHLCV for {len(tickers)} tickers (batch)…")

    data = yf.download(
        tickers=tickers,
        period="1y",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False
    )

    # Benchmark close
    bench_close = None
    if bench:
        try:
            bench_close = data[bench]["Close"].dropna()
        except:
            bench_close = None

    results = []
    bar = st.progress(0)

    for i, sym in enumerate(symbols):
        bar.progress((i + 1) / len(symbols))
        time.sleep(0.02)

        try:
            df = data[sym].dropna()
        except:
            df = pd.DataFrame()

        # Always include all symbols (even if missing)
        if df is None or len(df) < days_required:
            results.append({
                "Symbol": sym, "Name": sym, "Sector": "N/A",
                "FinalScore": np.nan, "SetupScore": np.nan, "Catalyst": np.nan,
                "Trend": "—", "NearHigh_%": np.nan, "ATR%": np.nan, "VolDryUp": np.nan,
                "RS_3M": np.nan, "Avg$Vol20": np.nan, "LastPrice": np.nan,
                "Timing": "⚠️ No/low data", "EntryType": "—",
                "sub_trend": np.nan, "sub_rs": np.nan, "sub_near": np.nan, "sub_atr": np.nan, "sub_dry": np.nan
            })
            continue

        close = df["Close"].astype(float)
        vol = df["Volume"].astype(float)

        last_price = float(close.iloc[-1])
        vol20 = float(vol.tail(20).mean())
        avg_dvol = float((close.tail(20) * vol.tail(20)).mean())

        # Light global filters (don’t drop, just tag as filtered)
        filtered = (last_price < price_min) or (avg_dvol < usd_vol_min)

        # Trend
        sma50 = close.rolling(50).mean()
        sma50_now = float(sma50.iloc[-1]) if np.isfinite(sma50.iloc[-1]) else np.nan
        trend_ok = np.isfinite(sma50_now) and last_price > sma50_now
        sma50_slope = safe_div((sma50.iloc[-1] - sma50.iloc[-21]), sma50.iloc[-21]) * 100.0 if len(sma50.dropna()) > 60 else np.nan
        slope_ok = np.isfinite(sma50_slope) and sma50_slope > 0

        if trend_ok and slope_ok:
            trend_label = "✅"
        elif trend_ok or slope_ok:
            trend_label = "⚠️"
        else:
            trend_label = "❌"

        # Near high (20/55)
        high20 = float(close.tail(20).max())
        high55 = float(close.tail(55).max())
        near_high = np.nanmin([
            safe_div((high20 - last_price), last_price) * 100.0,
            safe_div((high55 - last_price), last_price) * 100.0
        ])

        # ATR%
        atr_pct = calc_atr_pct(df, n=14)

        # Volume dry-up ratio
        vol5 = float(vol.tail(5).mean())
        voldry = safe_div(vol5, vol20)  # <1 is drying up

        # RS vs benchmark over ~3M
        rs_3m = np.nan
        if bench_close is not None and len(bench_close) >= 70 and len(close) >= 70:
            rs_3m = pct_change(close, 63) - pct_change(bench_close, 63)

        # Subscores (BALANCED+ permissive)
        trend_sub = clip01((0.6 if trend_ok else 0.0) + (0.4 if slope_ok else 0.0))
        near_sub = clip01(1.0 - (max(near_high, 0.0) / 15.0)) if np.isfinite(near_high) else 0.0
        atr_sub = clip01(1.0 - ((atr_pct - 2.0) / 5.0)) if np.isfinite(atr_pct) else 0.0
        dry_sub = clip01((1.0 - voldry) / 0.4) if np.isfinite(voldry) else 0.0

        results.append({
            "Symbol": sym, "Name": sym, "Sector": "N/A",
            "Trend": trend_label,
            "NearHigh_%": round(float(near_high), 2) if np.isfinite(near_high) else np.nan,
            "ATR%": round(float(atr_pct), 2) if np.isfinite(atr_pct) else np.nan,
            "VolDryUp": round(float(voldry), 2) if np.isfinite(voldry) else np.nan,
            "RS_3M": round(float(rs_3m), 2) if np.isfinite(rs_3m) else np.nan,
            "Avg$Vol20": avg_dvol,
            "LastPrice": last_price,
            "Filtered": "⛔" if filtered else "",
            "_trend_sub": trend_sub,
            "_near_sub": near_sub,
            "_atr_sub": atr_sub,
            "_dry_sub": dry_sub,
        })

    df = pd.DataFrame(results)

    # RS percentile within this market universe
    df["_rs_sub"] = percentile_rank(df["RS_3M"])

    # SetupScore weights (final criteria)
    # Trend 30, RS 25, Near 20, ATR 15, Dry 10
    df["SetupScore"] = (
        df["_trend_sub"] * 30.0 +
        df["_rs_sub"]    * 25.0 +
        df["_near_sub"]  * 20.0 +
        df["_atr_sub"]   * 15.0 +
        df["_dry_sub"]   * 10.0
    ).round(0)

    # Debug subs (0..100)
    df["sub_trend"] = (df["_trend_sub"] * 100).round(0)
    df["sub_rs"]    = (df["_rs_sub"]    * 100).round(0)
    df["sub_near"]  = (df["_near_sub"]  * 100).round(0)
    df["sub_atr"]   = (df["_atr_sub"]   * 100).round(0)
    df["sub_dry"]   = (df["_dry_sub"]   * 100).round(0)

    # Catalyst (optional Top N only)
    df["Catalyst"] = 0.0
    df["FinalScore"] = df["SetupScore"]

    if topn_info > 0:
        top_syms = df.sort_values("SetupScore", ascending=False, na_position="last").head(topn_info)["Symbol"].tolist()
        st.info(f"Fetching Rec/Short for Top {len(top_syms)} (slow/fragile, best effort)…")
        cat_bar = st.progress(0)

        info_map = {}
        for i, s in enumerate(top_syms):
            info_map[s] = get_info_fields(s)
            cat_bar.progress((i + 1) / max(len(top_syms), 1))
            time.sleep(0.05)

        for s, inf in info_map.items():
            df.loc[df["Symbol"] == s, "Name"] = inf["Name"]
            df.loc[df["Symbol"] == s, "Sector"] = inf["Sector"]
            df.loc[df["Symbol"] == s, "RecMean"] = inf["RecMean"]
            df.loc[df["Symbol"] == s, "Short_%"] = inf["Short_%"]

        # Catalyst scoring (0..30): Short 0..20, Rec 0..10, no bullish defaults
        short_bonus = []
        for x in df.get("Short_%", pd.Series([np.nan] * len(df))).astype(float).fillna(np.nan):
            if not np.isfinite(x):
                short_bonus.append(0.0)
            else:
                short_bonus.append(clip01((x - 5.0) / 15.0) * 20.0)

        rec_bonus = []
        for r in df.get("RecMean", pd.Series([np.nan] * len(df))).astype(float).fillna(np.nan):
            if not np.isfinite(r):
                rec_bonus.append(0.0)
            else:
                rec_bonus.append(clip01((3.0 - r) / 1.2) * 10.0)

        df["Catalyst"] = (np.array(short_bonus) + np.array(rec_bonus)).round(0)
        df["FinalScore"] = (df["SetupScore"] + df["Catalyst"]).round(0)

    # Timing logic (final criteria: BALANCED+; more signals)
    timing = []
    entry_type = []
    for _, row in df.iterrows():
        setup = row.get("SetupScore", np.nan)
        near = row.get("NearHigh_%", np.nan)
        atrp = row.get("ATR%", np.nan)
        tr = row.get("Trend", "—")
        filt = row.get("Filtered", "")

        if not np.isfinite(setup):
            timing.append("⚠️ No data")
            entry_type.append("—")
            continue

        trend_not_bad = (tr != "❌")

        # (Conservative) breakout-zone proxy: extremely near highs + strong setup
        breakout_zone = (np.isfinite(near) and near <= 0.3 and setup >= 70 and trend_not_bad)

        pre_ok = (
            (setup >= pre_setup_min) and
            (np.isfinite(near) and near <= pre_near_max) and
            (np.isfinite(atrp) and atrp <= pre_atr_max) and
            trend_not_bad
        )

        watch_ok = (setup >= max(pre_setup_min - 10, 45)) and trend_not_bad

        if filt == "⛔":
            timing.append("⛔ Filtered (price/liquidity)")
            entry_type.append("—")
        elif breakout_zone:
            timing.append("🟢 BUY (breakout zone)")
            entry_type.append("Breakout zone")
        elif pre_ok:
            timing.append("🟡 PRE-BREAKOUT (starter)")
            entry_type.append("Starter position")
        elif watch_ok:
            timing.append("📈 WATCH (building)")
            entry_type.append("Watch")
        else:
            timing.append("👀 PASS")
            entry_type.append("Pass")

    df["Timing"] = timing
    df["EntryType"] = entry_type

    # Cleanup and sort
    df = df.drop(columns=[c for c in df.columns if c.startswith("_")], errors="ignore")
    df = df.sort_values("FinalScore", ascending=False, na_position="last")

    # Summary
    buy_cnt = df["Timing"].str.contains("🟢 BUY", na=False).sum()
    pre_cnt = df["Timing"].str.contains("PRE", na=False).sum()
    watch_cnt = df["Timing"].str.contains("WATCH", na=False).sum()

    st.success(f"✅ {len(df)}/{len(symbols)} gescannt | 🟢 BUY: {buy_cnt} | 🟡 PRE: {pre_cnt} | 📈 WATCH: {watch_cnt}")

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏆 Top FinalScore", int(df["FinalScore"].max()) if df["FinalScore"].notna().any() else "—")
    c2.metric("🎯 Top SetupScore", int(df["SetupScore"].max()) if df["SetupScore"].notna().any() else "—")
    c3.metric("🟡 PRE Count", int(pre_cnt))
    c4.metric("🟢 BUY Count", int(buy_cnt))

    # Display
    st.subheader("🥇 Ranking (Top 200)")
    show_cols = [
        "Symbol","Name","Sector",
        "FinalScore","SetupScore","Catalyst",
        "Trend","NearHigh_%","ATR%","VolDryUp","RS_3M",
        "Avg$Vol20","LastPrice",
        "Short_%","RecMean",
        "Timing","EntryType",
        "sub_trend","sub_rs","sub_near","sub_atr","sub_dry"
    ]
    show_cols = [c for c in show_cols if c in df.columns]
    st.dataframe(df[show_cols].head(200), use_container_width=True)

    st.subheader("🟡 PRE-BREAKOUT (Starter-Entries)")
    pre = df[df["Timing"].str.contains("PRE", na=False)]
    st.dataframe(pre[show_cols].head(100), use_container_width=True)

    st.subheader("🟢 BUY (Breakout zone)")
    buys = df[df["Timing"].str.contains("🟢 BUY", na=False)]
    st.dataframe(buys[show_cols].head(100), use_container_width=True)

    st.subheader("📈 WATCH (building)")
    watch = df[df["Timing"].str.contains("WATCH", na=False)]
    st.dataframe(watch[show_cols].head(100), use_container_width=True)

st.caption("v7.2 BALANCED+ | Static market dropdown | Batch OHLCV | RS vs benchmark | Top-N catalysts | Debug subs included")
