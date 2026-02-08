import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(layout="wide")
st.title("🚀 Explosions v7 — Pre-Rally Scanner (BALANCED)")

CANDIDATES = ['PLTR','SOFI','NET','ZS','CLOV','AFRM','UPST','RBLX','ASAN','OKTA']
BENCH = "SPY"

def clip01(x):
    return float(np.clip(x, 0.0, 1.0))

def safe_div(a, b):
    return a / b if (b is not None and b != 0 and np.isfinite(b)) else np.nan

def pct_change(series: pd.Series, periods: int):
    if series is None or len(series) <= periods:
        return np.nan
    return (series.iloc[-1] / series.iloc[-(periods+1)] - 1.0) * 100.0

def zscore(series: pd.Series):
    s = series.astype(float)
    m = np.nanmean(s)
    sd = np.nanstd(s)
    if sd == 0 or not np.isfinite(sd):
        return (s * 0)  # all zeros
    return (s - m) / sd

def percentile_rank(values: pd.Series):
    # returns 0..1 percentile ranks, robust to NaNs
    v = values.astype(float)
    ranks = v.rank(pct=True, na_option="bottom")
    return ranks.fillna(0.0).clip(0.0, 1.0)

def calc_atr_pct(df_ohlc: pd.DataFrame, n=14):
    # ATR% = ATR / Close
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
    atr_pct = safe_div(atr.iloc[-1], close.iloc[-1]) * 100.0
    return atr_pct

def get_info_fields(symbol: str):
    # only for top symbols to reduce slowness / missing values impact
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        rec_mean = info.get("recommendationMean", np.nan)
        short_pct = info.get("shortPercentOfFloat", np.nan)
        sector = info.get("sector", "N/A")
        name = (info.get("longName") or symbol)[:28]
        return {
            "Name": name,
            "Sector": sector,
            "RecMean": float(rec_mean) if rec_mean is not None else np.nan,
            "Short_%": float(short_pct) * 100.0 if short_pct is not None else np.nan,
        }
    except:
        return {"Name": symbol, "Sector": "N/A", "RecMean": np.nan, "Short_%": np.nan}

st.caption("Balanced = Setup (Preis/Volumen) dominiert. Catalyst (Short/Analyst) nur als Bonus und nur wenn verfügbar.")

if st.button("🎯 FORCE SCAN v7 (Batch Download, balanced)", type="primary"):
    st.cache_data.clear()
    bar = st.progress(0)

    tickers = CANDIDATES + [BENCH]
    # Batch download: much faster + fewer rate limit issues
    data = yf.download(
        tickers=tickers,
        period="1y",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False
    )

    results = []
    # Benchmark series for Relative Strength
    bench_close = None
    try:
        bench_close = data[BENCH]["Close"].dropna()
    except:
        bench_close = None

    for i, sym in enumerate(CANDIDATES):
        bar.progress((i + 1) / len(CANDIDATES))
        time.sleep(0.05)

        # Extract OHLCV
        try:
            df = data[sym].dropna()
        except:
            df = pd.DataFrame()

        if df is None or len(df) < 80:  # need enough history for MA/RS features
            results.append({
                "Symbol": sym,
                "Name": sym,
                "Sector": "N/A",
                "SetupScore": np.nan,
                "Catalyst": np.nan,
                "FinalScore": np.nan,
                "Trend": "—",
                "NearHigh": np.nan,
                "ATR%": np.nan,
                "VolDryUp": np.nan,
                "RS_3M": np.nan,
                "Timing": "⚠️ No/low data",
                "EntryType": "—",
            })
            continue

        close = df["Close"].astype(float)
        vol = df["Volume"].astype(float)

        # --- Core features ---
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()

        close_now = float(close.iloc[-1])
        sma50_now = float(sma50.iloc[-1]) if np.isfinite(sma50.iloc[-1]) else np.nan
        sma200_now = float(sma200.iloc[-1]) if len(sma200.dropna()) > 0 else np.nan

        # Trend filter
        trend_ok = np.isfinite(sma50_now) and close_now > sma50_now
        sma50_slope = safe_div((sma50.iloc[-1] - sma50.iloc[-21]), sma50.iloc[-21]) * 100.0 if len(sma50.dropna()) > 60 else np.nan
        slope_ok = np.isfinite(sma50_slope) and sma50_slope > 0

        trend_label = "✅" if (trend_ok and slope_ok) else "⚠️" if trend_ok else "❌"

        # Breakout proximity (to recent highs)
        high20 = float(close.tail(20).max())
        high55 = float(close.tail(55).max())
        dist20 = safe_div((high20 - close_now), close_now) * 100.0
        dist55 = safe_div((high55 - close_now), close_now) * 100.0
        near_high = np.nanmin([dist20, dist55])  # smaller is closer

        # Volatility contraction via ATR%
        atr_pct = calc_atr_pct(df, n=14)

        # Volume dry-up: last 5d avg vs last 20d avg
        vol5 = float(vol.tail(5).mean())
        vol20 = float(vol.tail(20).mean())
        voldry = safe_div(vol5, vol20)  # <1 means drying up

        # Relative Strength vs benchmark over ~3 months (63 trading days)
        rs_3m = np.nan
        if bench_close is not None and len(bench_close) >= 70 and len(close) >= 70:
            sym_ret = pct_change(close, 63)
            ben_ret = pct_change(bench_close, 63)
            rs_3m = sym_ret - ben_ret

        # Breakout confirmed?
        breakout20 = close_now > high20 * 1.001  # small buffer
        breakout55 = close_now > high55 * 1.001
        vol_confirm = (vol.iloc[-1] > vol20 * 1.5) if np.isfinite(vol20) else False
        breakout_confirmed = (breakout20 or breakout55) and vol_confirm

        # --- Normalize features into 0..1 sub-scores (balanced) ---
        # Trend subscore
        trend_sub = 0.0
        if trend_ok:
            trend_sub += 0.6
        if slope_ok:
            trend_sub += 0.4
        trend_sub = clip01(trend_sub)

        # Near-high subscore: best in 0–3% below high; too far = low score; already breakout = handled separately
        # Convert near_high% to score: 0% -> 1.0, 3% -> ~1.0, 10% -> low
        if np.isfinite(near_high):
            near_sub = clip01(1.0 - (max(near_high, 0) / 10.0))  # 0..10% mapped to 1..0
        else:
            near_sub = 0.0

        # ATR% subscore: lower ATR% = better contraction (but not absurdly low)
        # Map: 1% ATR => great, 5% => weak. Clamp to 0..1.
        if np.isfinite(atr_pct):
            atr_sub = clip01(1.0 - ((atr_pct - 1.0) / 4.0))
        else:
            atr_sub = 0.0

        # Volume dry-up subscore: 0.6 or below is strong dry-up; >1 is not drying
        if np.isfinite(voldry):
            dry_sub = clip01((1.0 - voldry) / 0.4)  # voldry=0.6 -> 1.0, voldry=1.0 -> 0
        else:
            dry_sub = 0.0

        # RS subscore: within your candidate set later (percentile)
        # For now store raw RS, percentile later
        results.append({
            "Symbol": sym,
            "Name": sym,           # replaced later for topN
            "Sector": "N/A",
            "Trend": trend_label,
            "NearHigh": round(float(near_high), 2) if np.isfinite(near_high) else np.nan,
            "ATR%": round(float(atr_pct), 2) if np.isfinite(atr_pct) else np.nan,
            "VolDryUp": round(float(voldry), 2) if np.isfinite(voldry) else np.nan,
            "RS_3M": round(float(rs_3m), 2) if np.isfinite(rs_3m) else np.nan,
            "_trend_sub": trend_sub,
            "_near_sub": near_sub,
            "_atr_sub": atr_sub,
            "_dry_sub": dry_sub,
            "_breakout": breakout_confirmed,
        })

    df = pd.DataFrame(results)

    # RS percentile within candidate set
    rs_pct = percentile_rank(df["RS_3M"])
    df["_rs_sub"] = rs_pct

    # SetupScore = weighted sum (0..100)
    # Balanced weights: Trend 25, NearHigh 25, Contraction(ATR) 25, RS 15, Volume Dry-up 10
    df["SetupScore"] = (
        df["_trend_sub"] * 25.0 +
        df["_near_sub"]  * 25.0 +
        df["_atr_sub"]   * 25.0 +
        df["_rs_sub"]    * 15.0 +
        df["_dry_sub"]   * 10.0
    ).round(0)

    # Initial Catalyst placeholders
    df["Catalyst"] = 0.0

    # Only fetch info for top N (by SetupScore), to keep it fast/reliable
    TOPN_INFO = 5
    top_syms = df.sort_values("SetupScore", ascending=False).head(TOPN_INFO)["Symbol"].tolist()

    info_map = {s: get_info_fields(s) for s in top_syms}

    # Fill Name/Sector for those
    for s, inf in info_map.items():
        df.loc[df["Symbol"] == s, "Name"] = inf["Name"]
        df.loc[df["Symbol"] == s, "Sector"] = inf["Sector"]
        df.loc[df["Symbol"] == s, "RecMean"] = inf["RecMean"]
        df.loc[df["Symbol"] == s, "Short_%"] = inf["Short_%"]

    # Catalyst scoring (0..30): short interest + analyst rec (optional)
    # Short%: 0..20 points, RecMean: 0..10 points
    # (If missing, no bonus rather than bullish default)
    short_pct_series = df.get("Short_%", pd.Series([np.nan]*len(df)))
    rec_mean_series = df.get("RecMean", pd.Series([np.nan]*len(df)))

    # Short bonus: 5%->0, 20%->max. clamp
    short_bonus = []
    for x in short_pct_series.astype(float).fillna(np.nan):
        if not np.isfinite(x):
            short_bonus.append(0.0)
        else:
            short_bonus.append(clip01((x - 5.0) / 15.0) * 20.0)
    df["Catalyst"] += np.array(short_bonus)

    # Rec bonus: 3.0 -> 0, 1.8 -> max (better = lower)
    rec_bonus = []
    for r in rec_mean_series.astype(float).fillna(np.nan):
        if not np.isfinite(r):
            rec_bonus.append(0.0)
        else:
            rec_bonus.append(clip01((3.0 - r) / 1.2) * 10.0)
    df["Catalyst"] += np.array(rec_bonus)

    df["Catalyst"] = df["Catalyst"].round(0)

    # FinalScore
    df["FinalScore"] = (df["SetupScore"] + df["Catalyst"]).round(0)

    # Timing logic (balanced)
    # - Breakout confirmed => BUY
    # - High SetupScore + near high + contraction => Pre-breakout watch/buy (balanced)
    timing = []
    entry_type = []
    for _, row in df.iterrows():
        setup = row["SetupScore"]
        near = row["NearHigh"]
        atrp = row["ATR%"]
        brk = bool(row["_breakout"])

        if not np.isfinite(setup):
            timing.append("⚠️ No data")
            entry_type.append("—")
            continue

        if brk:
            timing.append("🟢 BUY (confirmed breakout)")
            entry_type.append("Breakout confirmed")
        else:
            # Pre-breakout: setup strong + close to highs + contraction not too high
            pre_ok = (setup >= 70) and (np.isfinite(near) and near <= 3.5) and (np.isfinite(atrp) and atrp <= 3.5)
            watch_ok = (setup >= 60)

            if pre_ok:
                timing.append("🟡 PRE-BREAKOUT (balanced)")
                entry_type.append("Pre-breakout")
            elif watch_ok:
                timing.append("📈 WATCH (building)")
                entry_type.append("Watch")
            else:
                timing.append("👀 PASS (weak setup)")
                entry_type.append("Pass")

    df["Timing"] = timing
    df["EntryType"] = entry_type

    # Clean up
    df = df.drop(columns=[c for c in df.columns if c.startswith("_")], errors="ignore")
    df = df.sort_values("FinalScore", ascending=False, na_position="last")

    # Display
    buy_count = (df["Timing"].str.contains("BUY|PRE-BREAKOUT", na=False)).sum()

    st.success(f"✅ {len(df)}/{len(CANDIDATES)} gescannt | {buy_count}x (BUY oder PRE-BREAKOUT)")

    st.subheader("🥇 Ranking (balanced)")
    show_cols = [
        "Symbol","Name","Sector",
        "FinalScore","SetupScore","Catalyst",
        "Trend","NearHigh","ATR%","VolDryUp","RS_3M",
        "Short_%","RecMean",
        "Timing","EntryType"
    ]
    # only show columns that exist (Short/Rec only for topN)
    show_cols = [c for c in show_cols if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏆 Top FinalScore", int(df["FinalScore"].max()) if df["FinalScore"].notna().any() else "—")
    col2.metric("🎯 Top SetupScore", int(df["SetupScore"].max()) if df["SetupScore"].notna().any() else "—")
    col3.metric("🧊 Ø ATR%", f"{df['ATR%'].mean():.2f}%" if df["ATR%"].notna().any() else "—")
    col4.metric("🟢/🟡 Signals", int(buy_count))

    st.subheader("📌 Pre-breakout Watchlist (balanced)")
    pre = df[df["Timing"].str.contains("PRE-BREAKOUT", na=False)].head(5)
    st.dataframe(pre[show_cols], use_container_width=True)

    st.subheader("✅ Breakout confirmed (volume confirm)")
    brk = df[df["Timing"].str.contains("confirmed breakout", na=False)].head(5)
    st.dataframe(brk[show_cols], use_container_width=True)

    st.caption("Hinweis: Das ist kein Finanzrat. Pre-breakout Signale sind absichtlich 'balanced' — früher, aber mit Trend+Contraction+Nähe zum High.")
