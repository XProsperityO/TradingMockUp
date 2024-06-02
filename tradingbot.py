from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from datetime import timedelta
from finbert_utils import estimate_sentiment

API_KEY = "PK980234ZEOIEWEQY7SZ"
API_SECRET ="jvUOmC0W0nWeiRMjjEWqGygMYUtiYCqZ6UF01ZcC"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
  "API_KEY" :API_KEY,
  "API_SECRET": API_SECRET,
  "PAPER": True
}

class MLTrader(Strategy):
  def initialize(self, symbol:str="SPY", cash_at_risk:float=.05):
    self.symbol = symbol
    self.sleeptime = "24H"
    self.last_trade = None
    self.cash_at_risk = cash_at_risk
    self.api =REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

  def position_sizing(self):
    cash = self.get_cash()
    last_price = self.get_last_price(self.symbol)
    quantity = round(cash * self.cash_at_risk / last_price,0)
    return cash, last_price, quantity

  def get_dates(self):
    today = self.get_datetime()
    three_days_prior = today - timedelta(days=3)
    return today.strftime('%Y-%M-%d'), three_days_prior.strftime('%Y-%M-%d')

  def get_sentiment(self):
    today, three_days_prior = self.get_dates()
    news = self.api.get_news(symbol=self.symbol,start=three_days_prior,end=today)
    news = [ev._dict_["_raw"]["headline"] for ev in news]
    probability, sentiment = estimate_sentiment(news)
    return probability, sentiment

  def on_trading_iteration(self):
    probability, sentiment = self.get_sentiment()
    cash, last_price, quantity = self.position_sizing()

    if cash > last_price:
      if sentiment == "positive" and probability > 0.999:
        if self.last_trade == "sell":
            self.sell_all()
        order = self.create_order(
            self.symbol,
            quantity,
            "buy",
            type="bracket",
            take_profit_price=last_price * 1.20,
            stop_loss_price=last_price * 0.95
        )
        self.submit_order(order)
        self.last_trade = "buy"
    elif sentiment == "negative" and probability > 0.999:
        if self.last_trade == "buy":
            self.sell_all()
        order = self.create_order(
            self.symbol,
            quantity,
            "sell",
            type="bracket",
            take_profit_price=last_price * 0.8,
            stop_loss_price=last_price * 1.05
        )
        self.submit_order(order)
        self.last_trade = "sell"


start_date = datetime(2020,1,1)
end_date = datetime(2022,1,1)

broker = Alpaca(ALPACA_CREDS)

strategy = MLTrader(name='mlstrat', broker=broker, parameters={"symbol":"SPY","cash_at_risk":.5})

strategy.backtest(
  YahooDataBacktesting,
  start_date,
  end_date,
  parameters={"symbol":"SPY"}
)