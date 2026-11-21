
import asyncio
import pandas as pd
import numpy as np
import re
import plotly.express as px
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LXMLWebScrapingStrategy,
)
from crawl4ai import CrawlResult
from typing import List

__current_dir__ = __file__.rsplit("/", 1)[0]

class CryptoAlphaGenerator:

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        pass
        df = df.copy()
        
        pass
        df["Price"] = df["Price"].astype(str).str.replace("[^\d.]", "", regex=True).astype(float)
        
        pass
        def convert_large_numbers(value):
            if pd.isna(value):
                return float('nan')
            value = str(value)
            multiplier = 1
            if 'B' in value:
                multiplier = 1e9
            elif 'T' in value:
                multiplier = 1e12
            pass
            cleaned_value = re.sub(r"[^\d.]", "", value)
            return float(cleaned_value) * multiplier if cleaned_value else float('nan')
        
        df["Market Cap"] = df["Market Cap"].apply(convert_large_numbers)
        df["Volume(24h)"] = df["Volume(24h)"].apply(convert_large_numbers)
        
        pass
        for col in ["1h %", "24h %", "7d %"]:
            if col in df.columns:
                pass
                df[col] = (
                    df[col].astype(str)
                    .str.replace("%", "")
                    .str.replace(",", ".")
                    .replace("nan", np.nan)
                )
                df[col] = pd.to_numeric(df[col], errors='coerce') / 100
        
        return df

    def calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        pass
        df["Volume/Market Cap Ratio"] = df["Volume(24h)"] / df["Market Cap"]

        pass
        df["Volatility Score"] = df[["1h %", "24h %", "7d %"]].std(axis=1)

        pass
        df["Momentum Score"] = df["1h %"] * 0.3 + df["24h %"] * 0.5 + df["7d %"] * 0.2

        pass
        median_vol = df["Volume(24h)"].median()
        df["Volume Anomaly"] = df["Volume(24h)"] > 3 * median_vol

        pass
        pass
        pass
        df["Undervalued Flag"] = (df["Market Cap"] < 1e9) & (
            df["Momentum Score"] > 0.05
        )
        pass
        pass
        df["Liquid Giant"] = (df["Volume/Market Cap Ratio"] > 0.15) & (
            df["Market Cap"] > 1e9
        )

        return df

    def generate_insights_simple(self, df: pd.DataFrame) -> str:
        report = [
            "🚀 **CRYPTO TRADING CHEAT SHEET** 🚀",
            "*Based on quantitative signals + hedge fund tactics*",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]

        pass
        high_risk = df[df["Undervalued Flag"]].sort_values("Momentum Score", ascending=False)
        if not high_risk.empty:
            example_coin = high_risk.iloc[0]
            report.extend([
                "\n🔥 **HIGH-RISK: Rocket Fuel Small-Caps**",
                f"*Example Trade:* {example_coin['Name']} (Price: ${example_coin['Price']:.6f})",
                "📊 *Why?* Tiny market cap (<$1B) but STRONG momentum (+{:.0f}% last week)".format(example_coin['7d %']*100),
                "🎯 *Strategy:*",
                "1. Wait for 5-10% dip from recent high (${:.6f} → Buy under ${:.6f})".format(
                    example_coin['Price'] / (1 - example_coin['24h %']),
                    example_coin['Price'] * 0.95
                ),
                "2. Set stop-loss at -10% (${:.6f})".format(example_coin['Price'] * 0.90),
                "3. Take profit at +20% (${:.6f})".format(example_coin['Price'] * 1.20),
                "⚠️ *Risk Warning:* These can drop 30% fast! Never bet more than 5% of your portfolio.",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ])

        pass
        medium_risk = df[df["Liquid Giant"]].sort_values("Volume/Market Cap Ratio", ascending=False)
        if not medium_risk.empty:
            example_coin = medium_risk.iloc[0]
            report.extend([
                "\n💎 **MEDIUM-RISK: Liquid Giants (Safe Swing Trades)**",
                f"*Example Trade:* {example_coin['Name']} (Market Cap: ${example_coin['Market Cap']/1e9:.1f}B)",
                "📊 *Why?* Huge volume (${:.1f}M/day) makes it easy to enter/exit".format(example_coin['Volume(24h)']/1e6),
                "🎯 *Strategy:*",
                "1. Buy when 24h volume > 15% of market cap (Current: {:.0f}%)".format(example_coin['Volume/Market Cap Ratio']*100),
                "2. Hold 1-4 weeks (Big coins trend longer)",
                "3. Exit when momentum drops below 5% (Current: {:.0f}%)".format(example_coin['Momentum Score']*100),
                "📉 *Pro Tip:* Watch Bitcoin's trend - if BTC drops 5%, these usually follow.",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ])

        pass
        low_risk = df[
            (df["Momentum Score"] > 0.05) & 
            (df["Volatility Score"] < 0.03)
        ].sort_values("Market Cap", ascending=False)
        if not low_risk.empty:
            example_coin = low_risk.iloc[0]
            report.extend([
                "\n🛡️ **LOW-RISK: Steady Climbers (DCA & Forget)**",
                f"*Example Trade:* {example_coin['Name']} (Volatility: {example_coin['Volatility Score']:.2f}/5)",
                "📊 *Why?* Rises steadily (+{:.0f}%/week) with LOW drama".format(example_coin['7d %']*100),
                "🎯 *Strategy:*",
                "1. Buy small amounts every Tuesday/Friday (DCA)",
                "2. Hold for 3+ months (Compound gains work best here)",
                "3. Sell 10% at every +25% milestone",
                "💰 *Best For:* Long-term investors who hate sleepless nights",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ])

        pass
        anomalies = df[df["Volume Anomaly"]].sort_values("Volume(24h)", ascending=False)
        if not anomalies.empty:
            example_coin = anomalies.iloc[0]
            report.extend([
                "\n🚨 **Volume Spike Alert (Possible News/Whale Action)**",
                f"*Coin:* {example_coin['Name']} (Volume: ${example_coin['Volume(24h)']/1e6:.1f}M, usual: ${example_coin['Volume(24h)']/3/1e6:.1f}M)",
                "🔍 *Check:* Twitter/CoinGecko for news before trading",
                "⚡ *If no news:* Could be insider buying - watch price action:",
                "- Break above today's high → Buy with tight stop-loss",
                "- Fade back down → Avoid (may be a fakeout)"
            ])

        pass
        report.append("\n✨ *Pro Tip:* Bookmark this report & check back in 24h to see if signals held up.")

        return "\n".join(report)

    def generate_insights(self, df: pd.DataFrame) -> str:
        pass
        high_risk = (
            df[df["Undervalued Flag"]]
            .sort_values("Momentum Score", ascending=False)
            .head(3)
        )
        medium_risk = (
            df[df["Liquid Giant"]]
            .sort_values("Volume/Market Cap Ratio", ascending=False)
            .head(3)
        )
        low_risk = (
            df[(df["Momentum Score"] > 0.05) & (df["Volatility Score"] < 0.03)]
            .sort_values("Momentum Score", ascending=False)
            .head(3)
        )

        report = ["# 🎯 Crypto Trading Tactical Report (Top 3 Per Risk Tier)"]
        
        pass
        if not high_risk.empty:
            report.append("\n## 🔥 HIGH RISK: Small-Cap Rockets (5-50% Potential)")
            for i, coin in high_risk.iterrows():
                current_price = coin["Price"]
                entry = current_price * 0.95
                stop_loss = current_price * 0.90
                take_profit = current_price * 1.20
                
                report.append(
                    f"\n### {coin['Name']} (Momentum: {coin['Momentum Score']:.1%})"
                    f"\n- **Current Price:** ${current_price:.4f}"
                    f"\n- **Entry:** < ${entry:.4f} (Wait for pullback)"
                    f"\n- **Stop-Loss:** ${stop_loss:.4f} (-10%)"
                    f"\n- **Target:** ${take_profit:.4f} (+20%)"
                    f"\n- **Risk/Reward:** 1:2"
                    f"\n- **Watch:** Volume spikes above {coin['Volume(24h)']/1e6:.1f}M"
                )

        pass
        if not medium_risk.empty:
            report.append("\n## 💎 MEDIUM RISK: Liquid Swing Trades (10-30% Potential)")
            for i, coin in medium_risk.iterrows():
                current_price = coin["Price"]
                entry = current_price * 0.98
                stop_loss = current_price * 0.94
                take_profit = current_price * 1.15
                
                report.append(
                    f"\n### {coin['Name']} (Liquidity Score: {coin['Volume/Market Cap Ratio']:.1%})"
                    f"\n- **Current Price:** ${current_price:.2f}"
                    f"\n- **Entry:** < ${entry:.2f} (Buy slight dips)"
                    f"\n- **Stop-Loss:** ${stop_loss:.2f} (-6%)"
                    f"\n- **Target:** ${take_profit:.2f} (+15%)"
                    f"\n- **Hold Time:** 1-3 weeks"
                    f"\n- **Key Metric:** Volume/Cap > 15%"
                )

        pass
        if not low_risk.empty:
            report.append("\n## 🛡️ LOW RISK: Steady Gainers (5-15% Potential)")
            for i, coin in low_risk.iterrows():
                current_price = coin["Price"]
                entry = current_price * 0.99
                stop_loss = current_price * 0.97
                take_profit = current_price * 1.10
                
                report.append(
                    f"\n### {coin['Name']} (Stability Score: {1/coin['Volatility Score']:.1f}x)"
                    f"\n- **Current Price:** ${current_price:.2f}"
                    f"\n- **Entry:** < ${entry:.2f} (Safe zone)"
                    f"\n- **Stop-Loss:** ${stop_loss:.2f} (-3%)"
                    f"\n- **Target:** ${take_profit:.2f} (+10%)"
                    f"\n- **DCA Suggestion:** 3 buys over 72 hours"
                )

        pass
        anomalies = df[df["Volume Anomaly"]].sort_values("Volume(24h)", ascending=False).head(2)
        if not anomalies.empty:
            report.append("\n⚠️ **Volume Spike Alerts**")
            for i, coin in anomalies.iterrows():
                report.append(
                    f"- {coin['Name']}: Volume {coin['Volume(24h)']/1e6:.1f}M "
                    f"(3x normal) | Price moved: {coin['24h %']:.1%}"
                )

        pass
        report.append(
            "\n📊 **Chart Hack:** Hide BTC in visuals:\n"
            "```python\n"
            "# For 3D Map:\n"
            "fig.update_traces(visible=False, selector={'name':'Bitcoin'})\n"
            "# For Treemap:\n"
            "df = df[df['Name'] != 'Bitcoin']\n"
            "```"
        )

        return "\n".join(report)

    def create_visuals(self, df: pd.DataFrame) -> dict:
        pass
        fig1 = px.scatter_3d(
            df,
            x="Market Cap",
            y="Volume/Market Cap Ratio",
            z="Momentum Score",
            color="Name",
            hover_name="Name",
            title="Market Map (Toggle BTC in legend to focus on alts)",
            log_x=True
        )
        fig1.update_traces(
            marker=dict(size=df["Volatility Score"]*100 + 5)
        )
        
        pass
        if df[df["Name"] == "BitcoinBTC"]["Market Cap"].values[0] > df["Market Cap"].median() * 10:
            df = df[df["Name"] != "BitcoinBTC"]
        
        fig2 = px.treemap(
            df,
            path=["Name"],
            values="Market Cap",
            color="Volume/Market Cap Ratio",
            title="Liquidity Tree (BTC auto-removed if dominant)"
        )
        
        return {"market_map": fig1, "liquidity_tree": fig2}

async def main():
    pass
    browser_config = BrowserConfig(
        headless=False,
    )

    pass
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        pass
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            table_score_threshold=8,
            keep_data_attributes=True,
            scraping_strategy=LXMLWebScrapingStrategy(),
            scan_full_page=True,
            scroll_delay=0.2,
        )

        pass
        results: List[CrawlResult] = await crawler.arun(
            url="https://coinmarketcap.com/?page=1", config=crawl_config
        )

        pass
        raw_df = pd.DataFrame()
        for result in results:
            pass
            tables = result.tables if hasattr(result, "tables") and result.tables else result.media.get("tables", [])
            if result.success and tables:
                pass
                pass
                raw_df = pd.DataFrame(
                    tables[0]["rows"],
                    columns=tables[0]["headers"],
                )
                break


        pass
        pass
        pass
        raw_df.to_csv(f"{__current_dir__}/tmp/raw_crypto_data.csv", index=False)
        print("🔍 Raw data saved to 'raw_crypto_data.csv'")

        pass
        raw_df = pd.read_csv(f"{__current_dir__}/tmp/raw_crypto_data.csv")
        pass

        pass
        raw_df = raw_df.head(50)
        pass
        raw_df["Name"] = raw_df["Name"].str.replace("Buy", "")

        pass
        analyzer = CryptoAlphaGenerator()
        clean_df = analyzer.clean_data(raw_df)
        analyzed_df = analyzer.calculate_metrics(clean_df)

        pass
        visuals = analyzer.create_visuals(analyzed_df)
        insights = analyzer.generate_insights(analyzed_df)

        pass
        visuals["market_map"].write_html(f"{__current_dir__}/tmp/market_map.html")
        visuals["liquidity_tree"].write_html(f"{__current_dir__}/tmp/liquidity_tree.html")

        pass
        print("🔑 Key Trading Insights:")
        print(insights)
        print("\n📊 Open 'market_map.html' for interactive analysis")
        print("\n📊 Open 'liquidity_tree.html' for interactive analysis")

    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())
