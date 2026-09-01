//+------------------------------------------------------------------+
//|              QuantForge_Crabel_Executor_v8_1.mq5                |
//|                                                                  |
//| QuantForge Opening Range Momentum Executor                       |
//| London + New York | 15m OR | ATR Momentum | M15 EMA             |
//| Structural SL | 3.5R TP | Risk-Controlled Execution             |
//|                                                                  |
//| v8.1: Diagnostic / tester-safe re-engineering                    |
//+------------------------------------------------------------------+
#property copyright "QuantForge Institutional Systems"
#property link      "https://github.com/quantforge"
#property version   "8.10"
#property description "QuantForge Opening Range Momentum Executor v8.1"
#property strict

#include <Trade/Trade.mqh>

//====================================================================
// INPUTS
//====================================================================

input group "=== Identity ==="
input ulong   InpMagicNumber              = 9909;
input string  InpStrategyName             = "QF_OR_Momentum_v8_1";

input group "=== Time / Sessions ==="
// In Strategy Tester, use 0 unless you deliberately want to
// translate the simulated broker clock by another offset.
// Live: set this to the broker server's UTC offset (e.g. 2 or 3 for Exness).
input int     InpBrokerUtcOffsetHours     = 0;

input int     InpLondonStartHour          = 7;
input int     InpLondonStartMinute        = 0;
input int     InpLondonRangeMinutes       = 15;

input int     InpNYStartHour              = 13;
input int     InpNYStartMinute            = 0;
input int     InpNYRangeMinutes           = 15;

input group "=== Strategy ==="
input int     InpAtrPeriod                = 14;
input int     InpEmaPeriod                = 50;
input double  InpMinDisplacementATR       = 0.50;
input double  InpRiskRewardRatio          = 3.50;

input group "=== Risk Engine ==="
input double  InpRiskPerTradePercent      = 1.00;
input double  InpMaxDailyDrawdownPercent  = 3.00;
input double  InpMaxTotalDrawdownPercent  = 6.00;
input double  InpMaxOpenRiskPercent       = 3.00;
input double  InpMaxLotSize               = 0.30;

// Fixed lot is intended for controlled signal testing & micro accounts.
input bool    InpUseFixedLot              = false;
input double  InpFixedLotSize             = 0.01;

// 0 = disabled. If enabled, reject structural stops outside bounds.
// These are POINTS, not dollars.
input double  InpMinStopDistancePoints    = 0.0;
input double  InpMaxStopDistancePoints    = 0.0;

input group "=== Execution ==="
input int     InpDeviationPoints          = 30;
input double  InpMaxSpreadPoints          = 0.0;
input bool    InpClosePositionsOnKill     = false;

input group "=== Diagnostics / Testing ==="
input bool    InpDiagnosticMode           = true;

// If false, real orders are sent to the broker/tester.
// Set to true only if you want to inspect signals without opening trades.
input bool    InpSignalOnly               = false;

// Allows fixed 0.01 testing on small accounts by bypassing the
// monetary-risk gate. ONLY permitted in Strategy Tester.
input bool    InpDiagnosticBypassRisk     = true;

// Print one diagnostic summary per processed session.
input bool    InpVerboseDiagnostics       = true;

input group "=== Persistent State ==="
// Default false prevents terminal Global Variables from contaminating
// independent Strategy Tester runs. Enable for live/restart recovery.
input bool    InpPersistState             = false;

//====================================================================
// GLOBALS
//====================================================================

CTrade m_trade;

int h_atr = INVALID_HANDLE;
int h_ema = INVALID_HANDLE;

string g_prefix = "";

datetime g_utc_day_start = 0;

double g_day_start_equity = 0.0;
double g_peak_equity      = 0.0;

bool g_london_processed = false;
bool g_ny_processed     = false;

bool g_kill_switch = false;

//====================================================================
// ENUMS / STRUCTS
//====================================================================

enum SignalDirection
{
   SIGNAL_NONE = 0,
   SIGNAL_BUY  = 1,
   SIGNAL_SELL = -1
};

struct OpeningRange
{
   datetime start;
   datetime end;

   double open;
   double high;
   double low;
   double close;

   int bars;
   bool valid;
};

struct TradeSignal
{
   bool valid;

   SignalDirection direction;

   double entry;
   double stop;
   double target;

   double atr;
   double ema;
   double displacement;

   string session;
   string reason;
};

struct RiskDecision
{
   bool approved;

   double equity;
   double risk_money;

   double stop_distance;
   double loss_at_fixed_volume;
   double loss_per_lot;

   double volume;

   double current_open_risk;
   double projected_open_risk;

   double daily_drawdown;
   double total_drawdown;

   string reason;
};

//====================================================================
// BASIC UTILITIES
//====================================================================

string GVName(string suffix)
{
   return(g_prefix + suffix);
}

//--------------------------------------------------------------------
double NormalizePrice(double price)
{
   return(NormalizeDouble(price, _Digits));
}

//--------------------------------------------------------------------
int VolumeDigits()
{
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step >= 1.0)
      return(0);

   if(step >= 0.1)
      return(1);

   if(step >= 0.01)
      return(2);

   if(step >= 0.001)
      return(3);

   return(4);
}

//--------------------------------------------------------------------
double NormalizeVolumeDown(double volume)
{
   double min_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step       = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0.0 || max_volume <= 0.0)
      return(0.0);

   volume = MathMin(volume, max_volume);

   double normalized =
      MathFloor((volume + 1e-12) / step) * step;

   if(normalized < min_volume)
      return(0.0);

   return(
      NormalizeDouble(
         normalized,
         VolumeDigits()
      )
   );
}

//--------------------------------------------------------------------
double NormalizeVolumeNearest(double volume)
{
   double min_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step       = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0.0 || max_volume <= 0.0)
      return(0.0);

   volume = MathMax(min_volume, MathMin(volume, max_volume));

   double normalized =
      MathFloor((volume + step * 0.5) / step) * step;

   normalized =
      MathMax(min_volume, MathMin(normalized, max_volume));

   return(
      NormalizeDouble(
         normalized,
         VolumeDigits()
      )
   );
}

//--------------------------------------------------------------------
datetime GetUtcNow()
{
   datetime server_time = TimeCurrent();

   return(
      server_time -
      InpBrokerUtcOffsetHours * 3600
   );
}

//--------------------------------------------------------------------
datetime GetUtcDayStart(datetime t)
{
   MqlDateTime dt;

   if(!TimeToStruct(t, dt))
      return(0);

   dt.hour = 0;
   dt.min  = 0;
   dt.sec  = 0;

   return(StructToTime(dt));
}

//--------------------------------------------------------------------
datetime BuildSessionTime(
   datetime day_start,
   int hour,
   int minute
)
{
   return(
      day_start +
      hour * 3600 +
      minute * 60
   );
}

//====================================================================
// STATE
//====================================================================

void SaveState()
{
   if(!InpPersistState)
      return;

   GlobalVariableSet(
      GVName("DAY"),
      (double)g_utc_day_start
   );

   GlobalVariableSet(
      GVName("DAY_EQUITY"),
      g_day_start_equity
   );

   GlobalVariableSet(
      GVName("PEAK"),
      g_peak_equity
   );

   GlobalVariableSet(
      GVName("LONDON"),
      g_london_processed ? 1.0 : 0.0
   );

   GlobalVariableSet(
      GVName("NY"),
      g_ny_processed ? 1.0 : 0.0
   );

   GlobalVariableSet(
      GVName("KILL"),
      g_kill_switch ? 1.0 : 0.0
   );
}

//--------------------------------------------------------------------
void InitializeFreshState()
{
   datetime now = GetUtcNow();

   g_utc_day_start = GetUtcDayStart(now);

   double equity =
      AccountInfoDouble(ACCOUNT_EQUITY);

   if(equity <= 0.0)
      equity = AccountInfoDouble(ACCOUNT_BALANCE);

   g_day_start_equity = equity;
   g_peak_equity      = equity;

   g_london_processed = false;
   g_ny_processed     = false;
   g_kill_switch      = false;
}

//--------------------------------------------------------------------
void LoadState()
{
   InitializeFreshState();

   if(!InpPersistState)
      return;

   if(!GlobalVariableCheck(GVName("DAY")))
   {
      SaveState();
      return;
   }

   datetime stored_day =
      (datetime)GlobalVariableGet(
         GVName("DAY")
      );

   if(stored_day != g_utc_day_start)
   {
      g_day_start_equity =
         AccountInfoDouble(
            ACCOUNT_EQUITY
         );

      if(GlobalVariableCheck(GVName("PEAK")))
         g_peak_equity =
            GlobalVariableGet(
               GVName("PEAK")
            );

      g_london_processed = false;
      g_ny_processed     = false;
      g_kill_switch      = false;

      SaveState();
      return;
   }

   g_day_start_equity =
      GlobalVariableGet(
         GVName("DAY_EQUITY")
      );

   g_peak_equity =
      GlobalVariableGet(
         GVName("PEAK")
      );

   g_london_processed =
      GlobalVariableGet(
         GVName("LONDON")
      ) > 0.5;

   g_ny_processed =
      GlobalVariableGet(
         GVName("NY")
      ) > 0.5;

   g_kill_switch =
      GlobalVariableGet(
         GVName("KILL")
      ) > 0.5;
}

//====================================================================
// RISK STATE
//====================================================================

double GetDailyDrawdownPercent()
{
   if(g_day_start_equity <= 0.0)
      return(0.0);

   double equity =
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );

   double dd =
      (g_day_start_equity - equity) /
      g_day_start_equity * 100.0;

   return(MathMax(0.0, dd));
}

//--------------------------------------------------------------------
double GetTotalDrawdownPercent()
{
   if(g_peak_equity <= 0.0)
      return(0.0);

   double equity =
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );

   double dd =
      (g_peak_equity - equity) /
      g_peak_equity * 100.0;

   return(MathMax(0.0, dd));
}

//--------------------------------------------------------------------
void CloseAllEAPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC)
            != InpMagicNumber)
         continue;

      if(!m_trade.PositionClose(ticket))
      {
         PrintFormat(
            "QF KILL: close failed ticket=%I64u ret=%u %s",
            ticket,
            m_trade.ResultRetcode(),
            m_trade.ResultRetcodeDescription()
         );
      }
   }
}

//--------------------------------------------------------------------
void UpdateRiskState()
{
   double equity =
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );

   if(equity <= 0.0)
      return;

   if(g_peak_equity <= 0.0 ||
      equity > g_peak_equity)
   {
      g_peak_equity = equity;
      SaveState();
   }

   double daily_dd =
      GetDailyDrawdownPercent();

   double total_dd =
      GetTotalDrawdownPercent();

   if(daily_dd >= InpMaxDailyDrawdownPercent)
   {
      g_kill_switch = true;

      PrintFormat(
         "QF RISK: DAILY KILL SWITCH active. DD=%.2f%%",
         daily_dd
      );

      SaveState();
   }

   if(total_dd >= InpMaxTotalDrawdownPercent)
   {
      g_kill_switch = true;

      PrintFormat(
         "QF RISK: TOTAL KILL SWITCH active. DD=%.2f%%",
         total_dd
      );

      SaveState();
   }

   if(g_kill_switch &&
      InpClosePositionsOnKill)
   {
      CloseAllEAPositions();
   }
}

//====================================================================
// POSITION / OPEN RISK
//====================================================================

int CountEAPositions()
{
   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC)
            != InpMagicNumber)
         continue;

      count++;
   }

   return(count);
}

//--------------------------------------------------------------------
double CalculatePositionRisk(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
      return(0.0);

   string symbol =
      PositionGetString(
         POSITION_SYMBOL
      );

   ENUM_POSITION_TYPE position_type =
      (ENUM_POSITION_TYPE)
      PositionGetInteger(
         POSITION_TYPE
      );

   double volume =
      PositionGetDouble(
         POSITION_VOLUME
      );

   double open_price =
      PositionGetDouble(
         POSITION_PRICE_OPEN
      );

   double sl =
      PositionGetDouble(
         POSITION_SL
      );

   if(volume <= 0.0 ||
      sl <= 0.0)
      return(0.0);

   ENUM_ORDER_TYPE order_type;

   if(position_type == POSITION_TYPE_BUY)
      order_type = ORDER_TYPE_BUY;
   else
      order_type = ORDER_TYPE_SELL;

   double profit = 0.0;

   if(!OrderCalcProfit(
         order_type,
         symbol,
         volume,
         open_price,
         sl,
         profit))
   {
      return(0.0);
   }

   return(MathAbs(profit));
}

//--------------------------------------------------------------------
double CalculateOpenRiskMoney()
{
   double total = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if((ulong)PositionGetInteger(POSITION_MAGIC)
            != InpMagicNumber)
         continue;

      total += CalculatePositionRisk(ticket);
   }

   return(total);
}

//====================================================================
// MARKET DATA
//====================================================================

bool GetATR(double &atr)
{
   double buffer[];

   ArraySetAsSeries(buffer, true);

   if(CopyBuffer(
         h_atr,
         0,
         1,
         1,
         buffer
      ) != 1)
   {
      return(false);
   }

   atr = buffer[0];

   return(atr > 0.0);
}

//--------------------------------------------------------------------
bool GetEMA(double &ema)
{
   double buffer[];

   ArraySetAsSeries(buffer, true);

   if(CopyBuffer(
         h_ema,
         0,
         1,
         1,
         buffer
      ) != 1)
   {
      return(false);
   }

   ema = buffer[0];

   return(ema > 0.0);
}

//====================================================================
// OPENING RANGE
//====================================================================

bool BuildOpeningRange(
   datetime utc_start,
   int minutes,
   OpeningRange &range
)
{
   range.valid = false;
   range.start = utc_start;
   range.end =
      utc_start +
      minutes * 60;

   if(minutes <= 0)
      return(false);

   datetime utc_now =
      GetUtcNow();

   if(utc_now < range.end)
      return(false);

   datetime server_start =
      utc_start +
      InpBrokerUtcOffsetHours * 3600;

   datetime server_end =
      range.end +
      InpBrokerUtcOffsetHours * 3600;

   MqlRates rates[];

   ArraySetAsSeries(
      rates,
      false
   );

   int copied =
      CopyRates(
         _Symbol,
         PERIOD_M1,
         server_start,
         server_end - 1,
         rates
      );

   if(copied < 0)
   {
      PrintFormat(
         "QF DATA: CopyRates error=%d",
         GetLastError()
      );

      return(false);
   }

   if(copied != minutes)
   {
      PrintFormat(
         "QF DATA: OR INVALID. Session=%s ExpectedBars=%d Got=%d Start=%s End=%s",
         TimeToString(
            utc_start,
            TIME_DATE | TIME_MINUTES
         ),
         minutes,
         copied,
         TimeToString(
            utc_start,
            TIME_DATE | TIME_MINUTES
         ),
         TimeToString(
            range.end,
            TIME_DATE | TIME_MINUTES
         )
      );

      return(false);
   }

   range.open  = rates[0].open;
   range.high  = rates[0].high;
   range.low   = rates[0].low;
   range.close = rates[copied - 1].close;
   range.bars  = copied;

   for(int i = 1; i < copied; i++)
   {
      if(rates[i].high > range.high)
         range.high = rates[i].high;

      if(rates[i].low < range.low)
         range.low = rates[i].low;
   }

   range.valid = true;

   return(true);
}

//====================================================================
// SESSION ENGINE
//====================================================================

bool GetReadySession(
   string &session_name,
   datetime &session_start,
   int &range_minutes
)
{
   datetime now =
      GetUtcNow();

   datetime day =
      GetUtcDayStart(now);

   datetime london_start =
      BuildSessionTime(
         day,
         InpLondonStartHour,
         InpLondonStartMinute
      );

   datetime london_end =
      london_start +
      InpLondonRangeMinutes * 60;

   if(!g_london_processed &&
      now >= london_end)
   {
      session_name  = "LONDON";
      session_start = london_start;
      range_minutes = InpLondonRangeMinutes;

      return(true);
   }

   datetime ny_start =
      BuildSessionTime(
         day,
         InpNYStartHour,
         InpNYStartMinute
      );

   datetime ny_end =
      ny_start +
      InpNYRangeMinutes * 60;

   if(!g_ny_processed &&
      now >= ny_end)
   {
      session_name  = "NEW_YORK";
      session_start = ny_start;
      range_minutes = InpNYRangeMinutes;

      return(true);
   }

   return(false);
}

//====================================================================
// STRATEGY ENGINE
//====================================================================

TradeSignal EvaluateSignal(
   OpeningRange &range,
   double atr,
   double ema,
   string session
)
{
   TradeSignal signal;

   signal.valid =
      false;

   signal.direction =
      SIGNAL_NONE;

   signal.entry   = 0.0;
   signal.stop    = 0.0;
   signal.target  = 0.0;

   signal.atr =
      atr;

   signal.ema =
      ema;

   signal.displacement =
      range.close -
      range.open;

   signal.session =
      session;

   signal.reason = "";

   double ask =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_ASK
      );

   double bid =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_BID
      );

   if(ask <= 0.0 ||
      bid <= 0.0)
   {
      signal.reason =
         "Invalid bid/ask";

      return(signal);
   }

   double required =
      InpMinDisplacementATR *
      atr;

   //-----------------------------------------------------------------
   // BUY
   //-----------------------------------------------------------------
   if(signal.displacement > 0.0)
   {
      if(signal.displacement < required)
      {
         signal.reason =
            StringFormat(
               "BUY displacement too small: %.5f < %.5f",
               signal.displacement,
               required
            );

         return(signal);
      }

      if(range.close <= ema)
      {
         signal.reason =
            StringFormat(
               "BUY rejected by EMA: close %.5f <= EMA %.5f",
               range.close,
               ema
            );

         return(signal);
      }

      signal.direction =
         SIGNAL_BUY;

      signal.entry =
         ask;

      signal.stop =
         range.low;

      double distance =
         signal.entry -
         signal.stop;

      if(distance <= 0.0)
      {
         signal.reason =
            "BUY structural SL >= entry";

         return(signal);
      }

      signal.target =
         signal.entry +
         distance *
         InpRiskRewardRatio;

      signal.valid = true;

      signal.reason =
         "BUY: displacement + EMA";

      return(signal);
   }

   //-----------------------------------------------------------------
   // SELL
   //-----------------------------------------------------------------
   if(signal.displacement < 0.0)
   {
      if(MathAbs(signal.displacement) < required)
      {
         signal.reason =
            StringFormat(
               "SELL displacement too small: %.5f < %.5f",
               MathAbs(signal.displacement),
               required
            );

         return(signal);
      }

      if(range.close >= ema)
      {
         signal.reason =
            StringFormat(
               "SELL rejected by EMA: close %.5f >= EMA %.5f",
               range.close,
               ema
            );

         return(signal);
      }

      signal.direction =
         SIGNAL_SELL;

      signal.entry =
         bid;

      signal.stop =
         range.high;

      double distance =
         signal.stop -
         signal.entry;

      if(distance <= 0.0)
      {
         signal.reason =
            "SELL structural SL <= entry";

         return(signal);
      }

      signal.target =
         signal.entry -
         distance *
         InpRiskRewardRatio;

      signal.valid = true;

      signal.reason =
         "SELL: displacement + EMA";

      return(signal);
   }

   signal.reason =
      "No directional displacement";

   return(signal);
}

//====================================================================
// BROKER / STOP VALIDATION
//====================================================================

bool ValidateStops(
   TradeSignal &signal,
   string &reason
)
{
   double point =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_POINT
      );

   if(point <= 0.0)
   {
      reason =
         "Invalid SYMBOL_POINT";

      return(false);
   }

   double broker_stop_points =
      (double)SymbolInfoInteger(
         _Symbol,
         SYMBOL_TRADE_STOPS_LEVEL
      );

   double broker_freeze_points =
      (double)SymbolInfoInteger(
         _Symbol,
         SYMBOL_TRADE_FREEZE_LEVEL
      );

   double broker_min_distance =
      MathMax(
         broker_stop_points,
         broker_freeze_points
      ) * point;

   double stop_distance =
      MathAbs(
         signal.entry -
         signal.stop
      );

   if(stop_distance <= 0.0)
   {
      reason =
         "Invalid stop distance";

      return(false);
   }

   if(stop_distance < broker_min_distance)
   {
      reason =
         StringFormat(
            "Structural SL too close. Distance=%.5f BrokerMin=%.5f",
            stop_distance,
            broker_min_distance
         );

      return(false);
   }

   if(InpMinStopDistancePoints > 0.0 &&
      stop_distance / point <
         InpMinStopDistancePoints)
   {
      reason =
         "Below configured minimum stop distance";

      return(false);
   }

   if(InpMaxStopDistancePoints > 0.0 &&
      stop_distance / point >
         InpMaxStopDistancePoints)
   {
      reason =
         "Above configured maximum stop distance";

      return(false);
   }

   if(signal.direction == SIGNAL_BUY)
   {
      if(signal.stop >= signal.entry)
      {
         reason =
            "BUY stop is not below entry";

         return(false);
      }

      if(signal.target <= signal.entry)
      {
         reason =
            "BUY target is not above entry";

         return(false);
      }
   }

   if(signal.direction == SIGNAL_SELL)
   {
      if(signal.stop <= signal.entry)
      {
         reason =
            "SELL stop is not above entry";

         return(false);
      }

      if(signal.target >= signal.entry)
      {
         reason =
            "SELL target is not below entry";

         return(false);
      }
   }

   return(true);
}

//====================================================================
// SPREAD
//====================================================================

bool ValidateSpread(string &reason)
{
   if(InpMaxSpreadPoints <= 0.0)
      return(true);

   double ask =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_ASK
      );

   double bid =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_BID
      );

   double point =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_POINT
      );

   if(point <= 0.0)
   {
      reason =
         "Invalid point size";

      return(false);
   }

   double spread_points =
      (ask - bid) / point;

   if(spread_points >
      InpMaxSpreadPoints)
   {
      reason =
         StringFormat(
            "Spread %.1f > max %.1f points",
            spread_points,
            InpMaxSpreadPoints
         );

      return(false);
   }

   return(true);
}

//====================================================================
// RISK / SIZING
//====================================================================

bool CalculateRiskVolume(
   TradeSignal &signal,
   RiskDecision &decision
)
{
   decision.equity =
      AccountInfoDouble(
         ACCOUNT_EQUITY
      );

   if(decision.equity <= 0.0)
   {
      decision.reason =
         "Invalid equity";

      return(false);
   }

   decision.risk_money =
      decision.equity *
      InpRiskPerTradePercent /
      100.0;

   decision.stop_distance =
      MathAbs(
         signal.entry -
         signal.stop
      );

   if(decision.stop_distance <= 0.0)
   {
      decision.reason =
         "Invalid stop distance";

      return(false);
   }

   ENUM_ORDER_TYPE order_type;

   if(signal.direction == SIGNAL_BUY)
      order_type = ORDER_TYPE_BUY;
   else
      order_type = ORDER_TYPE_SELL;

   //-----------------------------------------------------------------
   // FIXED LOT MODE
   //-----------------------------------------------------------------
   if(InpUseFixedLot)
   {
      double requested =
         MathMin(
            InpFixedLotSize,
            InpMaxLotSize
         );

      decision.volume =
         NormalizeVolumeNearest(
            requested
         );

      if(decision.volume <= 0.0)
      {
         decision.reason =
            "Fixed volume invalid for broker";

         return(false);
      }

      double loss = 0.0;

      if(!OrderCalcProfit(
            order_type,
            _Symbol,
            decision.volume,
            signal.entry,
            signal.stop,
            loss))
      {
         decision.reason =
            "OrderCalcProfit failed for fixed volume";

         return(false);
      }

      decision.loss_at_fixed_volume =
         MathAbs(loss);

      decision.loss_per_lot =
         decision.loss_at_fixed_volume /
         decision.volume;

      return(true);
   }

   //-----------------------------------------------------------------
   // RISK-BASED MODE
   //-----------------------------------------------------------------
   double one_lot_loss = 0.0;

   if(!OrderCalcProfit(
         order_type,
         _Symbol,
         1.0,
         signal.entry,
         signal.stop,
         one_lot_loss))
   {
      decision.reason =
         "OrderCalcProfit failed for 1 lot";

      return(false);
   }

   one_lot_loss =
      MathAbs(one_lot_loss);

   if(one_lot_loss <= 0.0)
   {
      decision.reason =
         "One-lot loss is zero";

      return(false);
   }

   decision.loss_per_lot =
      one_lot_loss;

   double raw_volume =
      decision.risk_money /
      one_lot_loss;

   raw_volume =
      MathMin(
         raw_volume,
         InpMaxLotSize
      );

   decision.volume =
      NormalizeVolumeDown(
         raw_volume
      );

   if(decision.volume <= 0.0)
   {
      double broker_min =
         SymbolInfoDouble(
            _Symbol,
            SYMBOL_VOLUME_MIN
         );

      double min_loss = 0.0;

      if(!OrderCalcProfit(
            order_type,
            _Symbol,
            broker_min,
            signal.entry,
            signal.stop,
            min_loss))
      {
         min_loss = 0.0;
      }

      decision.loss_at_fixed_volume =
         MathAbs(min_loss);

      decision.reason =
         StringFormat(
            "Risk budget %.2f cannot support broker minimum %.4f lot. Minimum-lot SL loss=%.2f",
            decision.risk_money,
            broker_min,
            decision.loss_at_fixed_volume
         );

      return(false);
   }

   return(true);
}

//====================================================================
// RISK APPROVAL
//====================================================================

RiskDecision ApproveRisk(
   TradeSignal &signal
)
{
   RiskDecision decision;

   decision.approved = false;

   decision.equity = 0.0;
   decision.risk_money = 0.0;

   decision.stop_distance = 0.0;
   decision.loss_at_fixed_volume = 0.0;
   decision.loss_per_lot = 0.0;

   decision.volume = 0.0;

   decision.current_open_risk = 0.0;
   decision.projected_open_risk = 0.0;

   decision.daily_drawdown =
      GetDailyDrawdownPercent();

   decision.total_drawdown =
      GetTotalDrawdownPercent();

   decision.reason = "";

   //-----------------------------------------------------------------
   // Hard kill switch
   //-----------------------------------------------------------------
   if(g_kill_switch)
   {
      decision.reason =
         "Kill switch active";

      return(decision);
   }

   //-----------------------------------------------------------------
   // DD limits
   //-----------------------------------------------------------------
   if(decision.daily_drawdown >=
      InpMaxDailyDrawdownPercent)
   {
      decision.reason =
         "Daily DD limit reached";

      return(decision);
   }

   if(decision.total_drawdown >=
      InpMaxTotalDrawdownPercent)
   {
      decision.reason =
         "Total DD limit reached";

      return(decision);
   }

   //-----------------------------------------------------------------
   // One position at a time
   //-----------------------------------------------------------------
   if(CountEAPositions() > 0)
   {
      decision.reason =
         "EA already has an open position";

      return(decision);
   }

   //-----------------------------------------------------------------
   // Spread
   //-----------------------------------------------------------------
   string reason;

   if(!ValidateSpread(reason))
   {
      decision.reason =
         reason;

      return(decision);
   }

   //-----------------------------------------------------------------
   // Structural SL
   //-----------------------------------------------------------------
   if(!ValidateStops(
         signal,
         reason
      ))
   {
      decision.reason =
         reason;

      return(decision);
   }

   //-----------------------------------------------------------------
   // Position sizing
   //-----------------------------------------------------------------
   if(!CalculateRiskVolume(
         signal,
         decision
      ))
   {
      return(decision);
   }

   //-----------------------------------------------------------------
   // Diagnostic bypass
   //
   // This is deliberately restricted to Strategy Tester.
   //-----------------------------------------------------------------
   bool diagnostic_bypass =
      InpDiagnosticBypassRisk &&
      InpDiagnosticMode &&
      MQLInfoInteger(MQL_TESTER);

   if(diagnostic_bypass)
   {
      decision.approved = true;
      decision.reason =
         "DIAGNOSTIC TESTER RISK BYPASS";

      return(decision);
   }

   //-----------------------------------------------------------------
   // Fixed-lot risk validation.
   //-----------------------------------------------------------------
   double actual_trade_risk = 0.0;

   if(!OrderCalcProfit(
         signal.direction == SIGNAL_BUY
            ? ORDER_TYPE_BUY
            : ORDER_TYPE_SELL,
         _Symbol,
         decision.volume,
         signal.entry,
         signal.stop,
         actual_trade_risk
      ))
   {
      decision.reason =
         "OrderCalcProfit failed for actual volume";

      return(decision);
   }

   actual_trade_risk =
      MathAbs(actual_trade_risk);

   //-----------------------------------------------------------------
   // In fixed-lot mode, do not allow the fixed lot to violate risk.
   //-----------------------------------------------------------------
   if(InpUseFixedLot &&
      actual_trade_risk >
         decision.risk_money)
   {
      decision.reason =
         StringFormat(
            "Fixed lot risk %.2f exceeds allowed %.2f",
            actual_trade_risk,
            decision.risk_money
         );

      return(decision);
   }

   //-----------------------------------------------------------------
   // Open-risk cap
   //-----------------------------------------------------------------
   decision.current_open_risk =
      CalculateOpenRiskMoney();

   decision.projected_open_risk =
      decision.current_open_risk +
      actual_trade_risk;

   double maximum_open_risk =
      decision.equity *
      InpMaxOpenRiskPercent /
      100.0;

   if(decision.projected_open_risk >
      maximum_open_risk)
   {
      decision.reason =
         StringFormat(
            "Open-risk cap exceeded %.2f > %.2f",
            decision.projected_open_risk,
            maximum_open_risk
         );

      return(decision);
   }

   //-----------------------------------------------------------------
   // Margin
   //-----------------------------------------------------------------
   ENUM_ORDER_TYPE order_type;

   if(signal.direction == SIGNAL_BUY)
      order_type = ORDER_TYPE_BUY;
   else
      order_type = ORDER_TYPE_SELL;

   double margin_required = 0.0;

   if(!OrderCalcMargin(
         order_type,
         _Symbol,
         decision.volume,
         signal.entry,
         margin_required
      ))
   {
      decision.reason =
         "OrderCalcMargin failed";

      return(decision);
   }

   double free_margin =
      AccountInfoDouble(
         ACCOUNT_MARGIN_FREE
      );

   if(margin_required > free_margin)
   {
      decision.reason =
         StringFormat(
            "Insufficient margin %.2f > %.2f",
            margin_required,
            free_margin
         );

      return(decision);
   }

   decision.risk_money =
      actual_trade_risk;

   decision.approved = true;
   decision.reason =
      "Risk approved";

   return(decision);
}

//====================================================================
// EXECUTION
//====================================================================

bool ExecuteTrade(
   TradeSignal &signal
)
{
   //-----------------------------------------------------------------
   // Diagnostic signal-only mode.
   //-----------------------------------------------------------------
   if(InpSignalOnly)
   {
      PrintFormat(
         "QF DIAGNOSTIC: SIGNAL ONLY - no order sent."
      );

      return(true);
   }

   //-----------------------------------------------------------------
   // Refresh market price immediately before execution.
   //-----------------------------------------------------------------
   double ask =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_ASK
      );

   double bid =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_BID
      );

   if(ask <= 0.0 ||
      bid <= 0.0)
   {
      Print(
         "QF EXECUTION: Invalid bid/ask"
      );

      return(false);
   }

   double original_distance =
      MathAbs(
         signal.entry -
         signal.stop
      );

   if(signal.direction == SIGNAL_BUY)
   {
      signal.entry = ask;

      signal.stop =
         NormalizePrice(
            signal.entry -
            original_distance
         );

      signal.target =
         NormalizePrice(
            signal.entry +
            original_distance *
            InpRiskRewardRatio
         );
   }
   else
   {
      signal.entry = bid;

      signal.stop =
         NormalizePrice(
            signal.entry +
            original_distance
         );

      signal.target =
         NormalizePrice(
            signal.entry -
            original_distance *
            InpRiskRewardRatio
         );
   }

   string reason;

   if(!ValidateStops(
         signal,
         reason
      ))
   {
      PrintFormat(
         "QF EXECUTION: final stop validation failed: %s",
         reason
      );

      return(false);
   }

   //-----------------------------------------------------------------
   // Recalculate risk at refreshed price.
   //-----------------------------------------------------------------
   RiskDecision risk =
      ApproveRisk(signal);

   if(!risk.approved)
   {
      PrintFormat(
         "QF EXECUTION: final risk rejected: %s",
         risk.reason
      );

      return(false);
   }

   string comment =
      StringFormat(
         "%s %s",
         InpStrategyName,
         signal.direction == SIGNAL_BUY
            ? "BUY"
            : "SELL"
      );

   bool sent = false;

   ResetLastError();

   if(signal.direction == SIGNAL_BUY)
   {
      sent =
         m_trade.Buy(
            risk.volume,
            _Symbol,
            0.0,
            signal.stop,
            signal.target,
            comment
         );
   }
   else
   {
      sent =
         m_trade.Sell(
            risk.volume,
            _Symbol,
            0.0,
            signal.stop,
            signal.target,
            comment
         );
   }

   uint retcode =
      m_trade.ResultRetcode();

   string description =
      m_trade.ResultRetcodeDescription();

   if(!sent)
   {
      PrintFormat(
         "QF EXECUTION FAILED: retcode=%u %s LastError=%d",
         retcode,
         description,
         GetLastError()
      );

      return(false);
   }

   if(retcode != TRADE_RETCODE_DONE &&
      retcode != TRADE_RETCODE_DONE_PARTIAL &&
      retcode != TRADE_RETCODE_PLACED)
   {
      PrintFormat(
         "QF EXECUTION REJECTED: retcode=%u %s",
         retcode,
         description
      );

      return(false);
   }

   PrintFormat(
      "QF EXECUTED | %s | %s | Volume=%.4f | Entry=%.*f | SL=%.*f | TP=%.*f | Risk=%.2f",
      signal.session,
      signal.direction == SIGNAL_BUY
         ? "BUY"
         : "SELL",
      risk.volume,
      _Digits,
      signal.entry,
      _Digits,
      signal.stop,
      _Digits,
      signal.target,
      risk.risk_money
   );

   return(true);
}

//====================================================================
// DIAGNOSTIC REPORT
//====================================================================

void PrintSessionReport(
   OpeningRange &range,
   TradeSignal &signal,
   RiskDecision &risk
)
{
   if(!InpDiagnosticMode ||
      !InpVerboseDiagnostics)
      return;

   string direction =
      "NONE";

   if(signal.direction == SIGNAL_BUY)
      direction = "BUY";

   if(signal.direction == SIGNAL_SELL)
      direction = "SELL";

   Print(
      "------------------------------------------------------------"
   );

   PrintFormat(
      "QF SESSION REPORT | %s | %s",
      signal.session,
      TimeToString(
         range.start,
         TIME_DATE | TIME_MINUTES
      )
   );

   PrintFormat(
      "OR: bars=%d open=%.5f high=%.5f low=%.5f close=%.5f",
      range.bars,
      range.open,
      range.high,
      range.low,
      range.close
   );

   PrintFormat(
      "INDICATORS: ATR=%.5f EMA=%.5f displacement=%.5f required=%.5f",
      signal.atr,
      signal.ema,
      signal.displacement,
      InpMinDisplacementATR * signal.atr
   );

   PrintFormat(
      "SIGNAL: valid=%s direction=%s reason=%s",
      signal.valid ? "YES" : "NO",
      direction,
      signal.reason
   );

   if(signal.valid)
   {
      PrintFormat(
         "TRADE: entry=%.5f stop=%.5f target=%.5f stop_distance=%.5f",
         signal.entry,
         signal.stop,
         signal.target,
         MathAbs(signal.entry - signal.stop)
      );

      PrintFormat(
         "RISK: approved=%s volume=%.4f equity=%.2f allowed_risk=%.2f loss_per_lot=%.2f reason=%s",
         risk.approved ? "YES" : "NO",
         risk.volume,
         risk.equity,
         risk.risk_money,
         risk.loss_per_lot,
         risk.reason
      );
   }
   else
   {
      PrintFormat(
         "RISK: not evaluated because signal is invalid."
      );
   }

   PrintFormat(
      "DRAWDOWN: daily=%.2f%% total=%.2f%% kill=%s",
      risk.daily_drawdown,
      risk.total_drawdown,
      g_kill_switch ? "YES" : "NO"
   );

   Print(
      "------------------------------------------------------------"
   );
}

//====================================================================
// PROCESS ONE SESSION
//====================================================================

bool ProcessSession(
   string session_name,
   datetime session_start,
   int range_minutes
)
{
   OpeningRange range;

   //-----------------------------------------------------------------
   // Do NOT mark session processed if data isn't available.
   //-----------------------------------------------------------------
   if(!BuildOpeningRange(
         session_start,
         range_minutes,
         range
      ))
   {
      PrintFormat(
         "QF SESSION: %s waiting for valid opening-range data.",
         session_name
      );

      return(false);
   }

   double atr = 0.0;
   double ema = 0.0;

   if(!GetATR(atr))
   {
      PrintFormat(
         "QF DATA: %s ATR unavailable.",
         session_name
      );

      return(false);
   }

   if(!GetEMA(ema))
   {
      PrintFormat(
         "QF DATA: %s EMA unavailable.",
         session_name
      );

      return(false);
   }

   TradeSignal signal =
      EvaluateSignal(
         range,
         atr,
         ema,
         session_name
      );

   RiskDecision risk;

   risk.approved = false;
   risk.reason = "";
   risk.equity = AccountInfoDouble(ACCOUNT_EQUITY);
   risk.risk_money = 0.0;
   risk.stop_distance = 0.0;
   risk.loss_at_fixed_volume = 0.0;
   risk.loss_per_lot = 0.0;
   risk.volume = 0.0;
   risk.current_open_risk = 0.0;
   risk.projected_open_risk = 0.0;
   risk.daily_drawdown = GetDailyDrawdownPercent();
   risk.total_drawdown = GetTotalDrawdownPercent();

   if(signal.valid)
   {
      risk =
         ApproveRisk(signal);

      //----------------------------------------------------------------
      // Diagnostic report before signal-only execution.
      //----------------------------------------------------------------
      PrintSessionReport(
         range,
         signal,
         risk
      );

      //----------------------------------------------------------------
      // Signal-only mode: we count the signal as evaluated but don't
      // place an order.
      //----------------------------------------------------------------
      if(InpSignalOnly)
      {
         if(signal.valid)
         {
            PrintFormat(
               "QF DIAGNOSTIC: %s signal detected. SIGNAL ONLY mode.",
               session_name
            );

            return(true);
         }

         return(false);
      }

      //----------------------------------------------------------------
      // Real execution.
      //----------------------------------------------------------------
      if(!risk.approved)
      {
         PrintFormat(
            "QF RISK REJECTED | %s | %s",
            session_name,
            risk.reason
         );

         return(false);
      }

      return(
         ExecuteTrade(signal)
      );
   }

   PrintSessionReport(
      range,
      signal,
      risk
   );

   return(false);
}

//====================================================================
// INITIALIZATION
//====================================================================

int OnInit()
{
   //-----------------------------------------------------------------
   // Basic validation
   //-----------------------------------------------------------------
   if(InpRiskPerTradePercent <= 0.0)
   {
      Print(
         "QF INIT ERROR: InpRiskPerTradePercent must be > 0"
      );

      return(INIT_FAILED);
   }

   if(InpRiskRewardRatio <= 0.0)
   {
      Print(
         "QF INIT ERROR: InpRiskRewardRatio must be > 0"
      );

      return(INIT_FAILED);
   }

   if(InpMaxLotSize <= 0.0)
   {
      Print(
         "QF INIT ERROR: InpMaxLotSize must be > 0"
      );

      return(INIT_FAILED);
   }

   if(InpLondonRangeMinutes <= 0 ||
      InpNYRangeMinutes <= 0)
   {
      Print(
         "QF INIT ERROR: range minutes must be > 0"
      );

      return(INIT_FAILED);
   }

   //-----------------------------------------------------------------
   // Trading setup
   //-----------------------------------------------------------------
   m_trade.SetExpertMagicNumber(
      InpMagicNumber
   );

   m_trade.SetDeviationInPoints(
      InpDeviationPoints
   );

   m_trade.SetTypeFillingBySymbol(
      _Symbol
   );

   //-----------------------------------------------------------------
   // Indicators
   //-----------------------------------------------------------------
   h_atr =
      iATR(
         _Symbol,
         PERIOD_M1,
         InpAtrPeriod
      );

   h_ema =
      iMA(
         _Symbol,
         PERIOD_M15,
         InpEmaPeriod,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );

   if(h_atr == INVALID_HANDLE ||
      h_ema == INVALID_HANDLE)
   {
      Print(
         "QF INIT ERROR: failed to create indicator handles"
      );

      if(h_atr != INVALID_HANDLE)
         IndicatorRelease(h_atr);

      if(h_ema != INVALID_HANDLE)
         IndicatorRelease(h_ema);

      return(INIT_FAILED);
   }

   //-----------------------------------------------------------------
   // State namespace
   //-----------------------------------------------------------------
   g_prefix =
      StringFormat(
         "QF_%I64u_%s_",
         InpMagicNumber,
         _Symbol
      );

   LoadState();
   UpdateRiskState();

   //-----------------------------------------------------------------
   // Startup report
   //-----------------------------------------------------------------
   Print(
      "============================================================"
   );

   PrintFormat(
      "QuantForge Crabel Executor v8.1"
   );

   PrintFormat(
      "Symbol=%s Magic=%I64u",
      _Symbol,
      InpMagicNumber
   );

   PrintFormat(
      "Tester=%s Diagnostic=%s SignalOnly=%s",
      MQLInfoInteger(MQL_TESTER) ? "YES" : "NO",
      InpDiagnosticMode ? "YES" : "NO",
      InpSignalOnly ? "YES" : "NO"
   );

   PrintFormat(
      "Broker UTC Offset=%d",
      InpBrokerUtcOffsetHours
   );

   PrintFormat(
      "London=%02d:%02d UTC range=%d min",
      InpLondonStartHour,
      InpLondonStartMinute,
      InpLondonRangeMinutes
   );

   PrintFormat(
      "NY=%02d:%02d UTC range=%d min",
      InpNYStartHour,
      InpNYStartMinute,
      InpNYRangeMinutes
   );

   PrintFormat(
      "Momentum=%.2f ATR | EMA=%d | Target=%.2fR",
      InpMinDisplacementATR,
      InpEmaPeriod,
      InpRiskRewardRatio
   );

   PrintFormat(
      "Risk=%.2f%% | DailyDD=%.2f%% | TotalDD=%.2f%% | OpenRisk=%.2f%%",
      InpRiskPerTradePercent,
      InpMaxDailyDrawdownPercent,
      InpMaxTotalDrawdownPercent,
      InpMaxOpenRiskPercent
   );

   if(InpDiagnosticBypassRisk &&
      !MQLInfoInteger(MQL_TESTER))
   {
      Print(
         "QF WARNING: Diagnostic risk bypass is ignored outside Strategy Tester."
      );
   }

   Print(
      "============================================================"
   );

   return(INIT_SUCCEEDED);
}

//====================================================================
// DEINITIALIZATION
//====================================================================

void OnDeinit(
   const int reason
)
{
   SaveState();

   if(h_atr != INVALID_HANDLE)
      IndicatorRelease(h_atr);

   if(h_ema != INVALID_HANDLE)
      IndicatorRelease(h_ema);
}

//====================================================================
// MAIN LOOP
//====================================================================

void OnTick()
{
   datetime now =
      GetUtcNow();

   datetime today =
      GetUtcDayStart(now);

   //-----------------------------------------------------------------
   // New UTC day
   //-----------------------------------------------------------------
   if(today != g_utc_day_start)
   {
      g_utc_day_start =
         today;

      g_day_start_equity =
         AccountInfoDouble(
            ACCOUNT_EQUITY
         );

      g_london_processed = false;
      g_ny_processed = false;

      // Daily lock resets; total DD is separately evaluated.
      g_kill_switch = false;

      SaveState();

      if(InpDiagnosticMode)
      {
         PrintFormat(
            "QF DAY RESET | UTC=%s | StartEquity=%.2f",
            TimeToString(
               now,
               TIME_DATE | TIME_MINUTES
            ),
            g_day_start_equity
         );
      }
   }

   //-----------------------------------------------------------------
   // Risk state first.
   //-----------------------------------------------------------------
   UpdateRiskState();

   if(g_kill_switch)
      return;

   //-----------------------------------------------------------------
   // One active position at a time.
   //-----------------------------------------------------------------
   if(CountEAPositions() > 0)
      return;

   //-----------------------------------------------------------------
   // Get one ready session.
   //-----------------------------------------------------------------
   string session_name;
   datetime session_start;
   int range_minutes;

   if(!GetReadySession(
         session_name,
         session_start,
         range_minutes
      ))
   {
      return;
   }

   //-----------------------------------------------------------------
   // Process.
   //-----------------------------------------------------------------
   bool result =
      ProcessSession(
         session_name,
         session_start,
         range_minutes
      );

   //-----------------------------------------------------------------
   // Only mark processed after valid data was obtained.
   //
   // ProcessSession() returns false for both "no signal" and "data
   // unavailable". We therefore separately verify that the OR is
   // available before consuming the session.
   //-----------------------------------------------------------------
   OpeningRange verify_range;

   bool range_available =
      BuildOpeningRange(
         session_start,
         range_minutes,
         verify_range
      );

   if(range_available)
   {
      if(session_name == "LONDON")
         g_london_processed = true;

      if(session_name == "NEW_YORK")
         g_ny_processed = true;

      SaveState();

      if(InpDiagnosticMode)
      {
         PrintFormat(
            "QF SESSION CONSUMED | %s | Result=%s",
            session_name,
            result ? "SIGNAL/TRADE" : "NO TRADE"
         );
      }
   }
}
//+------------------------------------------------------------------+
