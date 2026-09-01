//+------------------------------------------------------------------+
//|                                   QuantForge_StrategyTester.mq5  |
//|      QuantForge Institutional Opening Range Momentum Engine      |
//|    Verified Opening Range Momentum (London & NY) + 1:3.5 Target  |
//+------------------------------------------------------------------+
#property copyright "QuantForge Institutional Systems"
#property link      "https://github.com/quantforge"
#property version   "7.50"
#property strict

#include <Trade/Trade.mqh>

//--- Strategy Inputs
input group "=== Compounding Capital Growth ==="
input bool   InpAutoCompounding     = true;      // Compound Lot Size as Account Grows
input double InpBaseEquityPer001Lot = 30.0;      // Equity required per 0.01 lot ($30 = 0.01, $60 = 0.02, $90 = 0.03)
input double InpFixedLotSize        = 0.01;      // Fixed Lot Size (if compounding disabled)
input double InpMaxLotSize          = 0.30;      // Maximum Allowed Lot Size
input ulong  InpMagicNumber         = 9909;      // Magic Number

input group "=== Strict 2 Golden Daily Opens (UTC) ==="
// London Institutional Pulse: 07:00 - 10:30 UTC
input int    InpLondonStartHour     = 7;         // London Open Hour (UTC)
input int    InpLondonStartMin      = 0;         // London Open Minute
input int    InpLondonSignalMins    = 15;        // London Opening Signal Window (Minutes)

// New York Institutional Pulse: 13:00 - 16:30 UTC
input int    InpNYStartHour         = 13;        // New York Open Hour (UTC)
input int    InpNYStartMin          = 0;         // New York Open Minute
input int    InpNYSignalMins        = 15;        // New York Opening Signal Window (Minutes)

input group "=== Risk & Institutional Profit Targets ==="
input double InpRiskRewardRatio     = 3.5;       // Asymmetric Target Multiplier (1:3.5 Target)
input double InpMinStopUSD          = 1.50;      // Minimum Protective Stop ($ per 0.01 lot)
input double InpMaxStopUSD          = 3.50;      // Maximum Protective Stop ($ per 0.01 lot)
input int    InpAtrPeriod           = 14;        // ATR Volatility Period

//--- Global Variables
CTrade   m_trade;
int      h_atr = INVALID_HANDLE;
int      h_ema = INVALID_HANDLE;
datetime g_last_trade_day = 0;
bool     g_london_traded_today = false;
bool     g_ny_traded_today = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(30);
   m_trade.SetTypeFillingBySymbol(_Symbol);

   h_atr = iATR(_Symbol, PERIOD_M1, InpAtrPeriod);
   h_ema = iMA(_Symbol, PERIOD_M15, 50, 0, MODE_EMA, PRICE_CLOSE);

   if(h_atr == INVALID_HANDLE || h_ema == INVALID_HANDLE)
     {
      Print("❌ Failed to initialize indicator handles");
      return(INIT_FAILED);
     }

   Print(StringFormat("🏛️ QuantForge Crabel Engine v7.50 Initialized on %s", _Symbol));
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(h_atr != INVALID_HANDLE) IndicatorRelease(h_atr);
   if(h_ema != INVALID_HANDLE) IndicatorRelease(h_ema);
  }

//+------------------------------------------------------------------+
//| Calculate Dynamic Compounding Lot Size based on Account Equity   |
//+------------------------------------------------------------------+
double CalculateDynamicLotSize()
  {
   if(!InpAutoCompounding) return(InpFixedLotSize);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0) equity = AccountInfoDouble(ACCOUNT_BALANCE);
   if(equity <= 0) equity = 30.0;

   int units = (int)MathFloor(equity / InpBaseEquityPer001Lot);
   if(units < 1) units = 1;
   double calculated_lots = units * 0.01;

   calculated_lots = MathMin(InpMaxLotSize, calculated_lots);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0)
      calculated_lots = MathFloor(calculated_lots / step) * step;

   return(MathMax(0.01, NormalizeDouble(calculated_lots, 2)));
  }

//+------------------------------------------------------------------+
//| Count active positions for this EA                               |
//+------------------------------------------------------------------+
int CountPositions()
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) > 0)
        {
         if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
           {
            count++;
           }
        }
     }
   return(count);
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Check active open positions
   if(CountPositions() >= 1) return;

   MqlDateTime dt;
   datetime current_time = TimeCurrent();
   TimeToStruct(current_time, dt);

   // Daily reset of session trade flags
   datetime today = (datetime)(current_time - (current_time % 86400));
   if(today != g_last_trade_day)
     {
      g_last_trade_day = today;
      g_london_traded_today = false;
      g_ny_traded_today = false;
     }

   int current_mins = dt.hour * 60 + dt.min;

   // 1. Check London Opening Window Trigger (Exact completion of 15m Signal Window)
   int london_trigger_min = InpLondonStartHour * 60 + InpLondonStartMin + InpLondonSignalMins;
   bool is_london_trigger = (!g_london_traded_today && current_mins == london_trigger_min && dt.sec < 10);

   // 2. Check New York Opening Window Trigger (Exact completion of 15m Signal Window)
   int ny_trigger_min = InpNYStartHour * 60 + InpNYStartMin + InpNYSignalMins;
   bool is_ny_trigger = (!g_ny_traded_today && current_mins == ny_trigger_min && dt.sec < 10);

   if(!is_london_trigger && !is_ny_trigger) return;

   int signal_window = is_london_trigger ? InpLondonSignalMins : InpNYSignalMins;

   // Fetch the completed 15-minute Opening Window M1 bars
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_M1, 1, signal_window + 2, rates) < signal_window) return;

   // Fetch ATR and M15 Trend EMA
   double atr_val[], ema_val[];
   ArraySetAsSeries(atr_val, true);
   ArraySetAsSeries(ema_val, true);
   if(CopyBuffer(h_atr, 0, 1, 2, atr_val) <= 0) return;
   if(CopyBuffer(h_ema, 0, 1, 2, ema_val) <= 0) return;

   double current_atr = atr_val[0];
   double m15_ema     = ema_val[0];

   // Evaluate Opening Range Momentum Direction
   double signal_open  = rates[signal_window - 1].open;
   double signal_close = rates[0].close;
   double signal_high  = rates[0].high;
   double signal_low   = rates[0].low;

   for(int i = 1; i < signal_window; i++)
     {
      if(rates[i].high > signal_high) signal_high = rates[i].high;
      if(rates[i].low < signal_low)   signal_low  = rates[i].low;
     }

   double momentum_displacement = signal_close - signal_open;

   bool is_btc = (StringFind(_Symbol, "BTC") >= 0);
   double contract_mult = is_btc ? 1.0 : 100.0;
   double min_stop_pts  = InpMinStopUSD / (0.01 * contract_mult);
   double max_stop_pts  = InpMaxStopUSD / (0.01 * contract_mult);

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double trade_lots = CalculateDynamicLotSize();

   // Minimum Displacement Filter: Ensure true directional institutional drive
   if(MathAbs(momentum_displacement) < (0.50 * current_atr)) return;

   // ====================================================================
   // CRABEL BULLISH SESSION MOMENTUM (Strong Green Opening Pulse)
   // ====================================================================
   if(momentum_displacement > 0 && signal_close > m15_ema)
     {
      // Stop Loss placed at the Opening Range Low (Structural Floor)
      double stop_dist = ask - signal_low;
      stop_dist = MathMax(min_stop_pts, MathMin(max_stop_pts, stop_dist));
      double target_dist = stop_dist * InpRiskRewardRatio; // 1:3.5 Target

      double sl = NormalizeDouble(ask - stop_dist, _Digits);
      double tp = NormalizeDouble(ask + target_dist, _Digits);

      if(m_trade.Buy(trade_lots, _Symbol, ask, sl, tp, StringFormat("Crabel BUY (%.2f lots)", trade_lots)))
        {
         if(is_london_trigger) g_london_traded_today = true;
         if(is_ny_trigger)     g_ny_traded_today = true;
         Print(StringFormat("🟢 Crabel Live Execution BUY: Ask=%.3f, SL=%.3f, TP=%.3f, Lots=%.2f", ask, sl, tp, trade_lots));
        }
     }
   // ====================================================================
   // CRABEL BEARISH SESSION MOMENTUM (Strong Red Opening Pulse)
   // ====================================================================
   else if(momentum_displacement < 0 && signal_close < m15_ema)
     {
      // Stop Loss placed at the Opening Range High (Structural Ceiling)
      double stop_dist = signal_high - bid;
      stop_dist = MathMax(min_stop_pts, MathMin(max_stop_pts, stop_dist));
      double target_dist = stop_dist * InpRiskRewardRatio; // 1:3.5 Target

      double sl = NormalizeDouble(bid + stop_dist, _Digits);
      double tp = NormalizeDouble(bid - target_dist, _Digits);

      if(m_trade.Sell(trade_lots, _Symbol, bid, sl, tp, StringFormat("Crabel SELL (%.2f lots)", trade_lots)))
        {
         if(is_london_trigger) g_london_traded_today = true;
         if(is_ny_trigger)     g_ny_traded_today = true;
         Print(StringFormat("🔴 Crabel Live Execution SELL: Bid=%.3f, SL=%.3f, TP=%.3f, Lots=%.2f", bid, sl, tp, trade_lots));
        }
     }
  }
//+------------------------------------------------------------------+
