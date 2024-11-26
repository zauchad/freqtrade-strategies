from datetime import datetime, timedelta
import talib.abstract as ta
import pandas_ta as pta
from freqtrade.persistence import Trade
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from freqtrade.strategy import DecimalParameter, IntParameter
from functools import reduce
import warnings

warnings.simplefilter(action="ignore", category=RuntimeWarning)

class E0V1E_45_Hyperopted_NonStableCoins(IStrategy):
    minimal_roi = {
        "0": 1
    }
    timeframe = '5m'
    process_only_new_candles = True
    startup_candle_count = 240
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
        "stoploss_on_exchange_limit_ratio": 0.99
    }

    stoploss = -0.342
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    is_optimize_32 = True
    buy_rsi_fast_32 = IntParameter(20, 70, default=34, space='buy', optimize=is_optimize_32)
    buy_rsi_32 = IntParameter(15, 50, default=15, space='buy', optimize=is_optimize_32)
    buy_sma15_32 = DecimalParameter(0.900, 1, default=0.964, decimals=3, space='buy', optimize=is_optimize_32)
    buy_cti_32 = DecimalParameter(-1, 1, default=0.21, decimals=2, space='buy', optimize=is_optimize_32)

    sell_fastx = IntParameter(50, 100, default=76, space='sell', optimize=True)

    cci_opt = True
    sell_loss_cci = IntParameter(low=0, high=600, default=595, space='sell', optimize=cci_opt)
    sell_loss_cci_profit = DecimalParameter(-0.15, 0, default=-0.09, decimals=2, space='sell', optimize=cci_opt)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe['sma_15'] = ta.SMA(dataframe, timeperiod=15)
        dataframe['cti'] = pta.cti(dataframe["close"], length=20)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)

        stoch_fast = ta.STOCHF(dataframe, 5, 3, 0, 3, 0)
        dataframe['fastk'] = stoch_fast['fastk']

        dataframe['cci'] = ta.CCI(dataframe, timeperiod=20)

        dataframe['ma120'] = ta.MA(dataframe, timeperiod=120)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []
        dataframe.loc[:, 'enter_tag'] = ''
        buy_1 = (
                (dataframe['rsi_slow'] < dataframe['rsi_slow'].shift(1)) &
                (dataframe['rsi_fast'] < self.buy_rsi_fast_32.value) &
                (dataframe['rsi'] > self.buy_rsi_32.value) &
                (dataframe['close'] < dataframe['sma_15'] * self.buy_sma15_32.value) &
                (dataframe['cti'] < self.buy_cti_32.value)
        )
        conditions.append(buy_1)
        dataframe.loc[buy_1, 'enter_tag'] += 'buy_1'
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x | y, conditions),
                'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, ['exit_long', 'exit_tag']] = (0, 'long_out')
        return dataframe
