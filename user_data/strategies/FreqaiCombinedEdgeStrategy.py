"""
FreqAI Combined Edge Strategy
Implements machine-learning-driven adaptive trading within the Freqtrade framework.
Combines:
  1. Mathematically optimized EMAs (EMA 13 & EMA 18)
  2. Volatility guardrails (14-period Average True Range / ATR)
  3. Qualitative NLP sentiment features (FinBERT news sentiment scoring)
  4. LightGBM / XGBoost Regressor predicting forward 10-candle ROI targets (&target_roi)
  5. Dynamic 2x ATR Trailing Stops via Freqtrade custom_stoploss
"""

import logging
import os
import sys
from functools import reduce
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy, Trade

logger = logging.getLogger(__name__)

# Add monorepo root to sys.path to enable importing backend sentiment analyzer if available
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class FreqaiCombinedEdgeStrategy(IStrategy):
    """
    Adaptive AI Strategy migrating the 'Combined Edge' quantitative + NLP pipeline
    into the FreqAI machine learning framework.
    """

    INTERFACE_VERSION = 3

    # Minimal ROI table: Let FreqAI predictive signals and ATR trailing stops manage exits
    minimal_roi = {
        "0": 0.08,     # 8% target
        "120": 0.04,   # 4% after 2 hours
        "240": 0.02,   # 2% after 4 hours
        "480": -1,     # Exit controlled by ML & ATR trailing stop
    }

    # Baseline safety stoploss (overridden by custom ATR trailing stop)
    stoploss = -0.05
    use_custom_stoploss = True
    trailing_stop = False  # Handled dynamically via ATR custom_stoploss

    timeframe = "1h"
    process_only_new_candles = True
    startup_candle_count: int = 40
    can_short = False

    # Cached sentiment to avoid redundant API / HuggingFace FinBERT calls per candle
    _sentiment_cache: Dict[str, float] = {}

    def fetch_finbert_sentiment(self) -> float:
        """
        Retrieves live FinBERT sentiment score normalized to a numerical feature:
        +1.0 (Positive), 0.0 (Neutral), -1.0 (Negative).
        """
        if "global" in self._sentiment_cache:
            return self._sentiment_cache["global"]
        try:
            from backend.bot import analyze_news_sentiment, fetch_latest_news

            headlines = fetch_latest_news("BTC")
            sentiment_str = analyze_news_sentiment(headlines)
            if sentiment_str == "positive":
                score = 1.0
            elif sentiment_str == "negative":
                score = -1.0
            else:
                score = 0.0
            self._sentiment_cache["global"] = score
            return score
        except Exception as e:
            logger.debug(f"FinBERT news fetch fallback: {e}")
            return 0.0

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        FreqAI Feature Engineering:
        Designates indicators with '%-' prefix for automated multi-timeframe ML expansion.
        """
        # 1. Feed our proven EMAs into the ML model
        dataframe["%-ema_13"] = ta.EMA(dataframe, timeperiod=13)
        dataframe["%-ema_18"] = ta.EMA(dataframe, timeperiod=18)
        dataframe["%-ema_ratio"] = dataframe["%-ema_13"] / dataframe["%-ema_18"]

        # 2. Feed our volatility guardrail (ATR)
        dataframe["%-atr_14"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["%-atr_pct"] = dataframe["%-atr_14"] / dataframe["close"]

        # 3. Supplemental Momentum & Trend Features
        dataframe["%-rsi_14"] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe["%-macd"] = macd["macd"]
        dataframe["%-macdsignal"] = macd["macdsignal"]
        dataframe["%-macdhist"] = macd["macdhist"]

        # 4. Feed FinBERT NLP Sentiment Score
        sentiment_score = self.fetch_finbert_sentiment()
        dataframe["%-news_sentiment"] = sentiment_score

        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """Expands raw price and volume pct changes."""
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-volume-change"] = dataframe["volume"].pct_change()
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Defines the AI's predictive objective.
        Prefixed with '&' to designate target labels for the LightGBM Regressor.
        Target: Predict the percentage return (ROI) over the next 10 candles.
        """
        dataframe["&target_roi"] = (
            dataframe["close"].shift(-10) / dataframe["close"] - 1.0
        )
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Passes candlestick data through the FreqAI adaptive training & inference pipeline."""
        # Baseline indicators available directly in strategy dataframe
        dataframe["ema_13"] = ta.EMA(dataframe, timeperiod=13)
        dataframe["ema_18"] = ta.EMA(dataframe, timeperiod=18)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Logic:
        Enters a trade when:
          1. FreqAI model confirms prediction validity ('do_predict' == 1)
          2. Model predicted ROI ('&target_roi') exceeds threshold (> 0.005 or +0.5% expected return)
          3. Fast EMA (13) is above Slow EMA (18)
        """
        target_col = "&target_roi" if "&target_roi" in df.columns else "&-s_close"
        
        if target_col in df.columns and "do_predict" in df.columns:
            enter_long_conditions = [
                df["do_predict"] == 1,
                df[target_col] > 0.005,  # AI expects positive forward ROI
                df["ema_13"] >= df["ema_18"] * 0.995,  # Macro trend filter
            ]
            if enter_long_conditions:
                df.loc[
                    reduce(lambda x, y: x & y, enter_long_conditions),
                    ["enter_long", "enter_tag"],
                ] = (1, "freqai_combined_edge_long")

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit Logic:
        Triggers early exit signal if the ML model projects negative return reversal.
        """
        target_col = "&target_roi" if "&target_roi" in df.columns else "&-s_close"
        if target_col in df.columns and "do_predict" in df.columns:
            exit_long_conditions = [
                df["do_predict"] == 1,
                df[target_col] < -0.01,  # AI predicts sharp impending reversal
            ]
            if exit_long_conditions:
                df.loc[reduce(lambda x, y: x & y, exit_long_conditions), "exit_long"] = 1

        return df

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time,
        current_rate: float,
        current_profit: float,
        after_fill: bool = False,
        **kwargs,
    ) -> Optional[float]:
        """
        Dynamic 2x ATR Trailing Stop Volatility Shield:
        Retrieves the latest 14-period ATR from the analyzed dataframe,
        calculating stop floor: Stop Price = Peak Price - (2 * ATR).
        Returns relative stoploss percentage to current_rate.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return -0.05

        last_candle = dataframe.iloc[-1]
        atr = last_candle.get("atr", last_candle.get("%-atr_14", 0.0))
        if atr <= 0:
            return -0.05

        # 2x ATR dynamic stop distance in absolute USD
        atr_stop_distance = 2.0 * atr

        # Track trade peak price (highest rate since open)
        max_rate = trade.max_rate if hasattr(trade, "max_rate") and trade.max_rate else trade.open_rate
        highest_rate = max(max_rate, current_rate)

        # Dynamic stop floor
        stop_price = highest_rate - atr_stop_distance

        # Convert to negative percentage relative to current_rate as required by Freqtrade
        if current_rate > 0:
            relative_stoploss = (stop_price - current_rate) / current_rate
            # Never let stoploss be positive or wider than -10% hard max safety cap
            return float(min(0.0, max(-0.10, relative_stoploss)))

        return -0.05
