//+------------------------------------------------------------------+
//|                 QuantForge_Crabel_Executor_v8.mq5               |
//|                                                                  |
//| QuantForge Opening Range Momentum Engine                         |
//| London + New York | 15m Opening Range | EMA50 | ATR Momentum    |
//| Structural Stop | 3.5R Target | Risk-Controlled Execution       |
//+------------------------------------------------------------------+
#property copyright "QuantForge Institutional Systems"
#property link      "https://github.com/quantforge"
#property version   "8.00"
#property description "QuantForge Opening Range Momentum Executor v8.0"
#property strict

#include <Trade/Trade.mqh>

//====================================================================
// CONFIGURATION
//====================================================================

input group "=== Identity ==="
input ulong   InpMagicNumber              = 9909;
input string  InpStrategyName             = "QF_OR_Momentum_v8";

//--------------------------------------------------------------------
// SESSION
//--------------------------------------------------------------------
input group "=== UTC Session Engine ==="

// IMPORTANT:
// TimeCurrent() is broker/server time.
// Set this to the broker server's UTC offset.
// Example:
// UTC+2 broker -> 2
// UTC+3 broker -> 3
// UTC-5 broker -> -5
input int     InpBrokerUtcOffsetHours     = 2;

// London
input int     InpLondonStartHour          = 7;
input int     InpLondonStartMinute        = 0;
input int     InpLondonRangeMinutes       = 15;

// New York
input int     InpNYStartHour              = 13;
input int     InpNYStartMinute            = 0;
input int     InpNYRangeMinutes           = 15;

//--------------------------------------------------------------------
// STRATEGY
//--------------------------------------------------------------------
input group "=== Strategy ==="

input int     InpAtrPeriod                = 14;
input int     InpEmaPeriod                = 50;
input double  InpMinDisplacementATR       = 0.50;
input double  InpRiskRewardRatio          = 3.50;

//--------------------------------------------------------------------
// RISK
//--------------------------------------------------------------------
input group "=== Risk Engine ==="

// 1% equity risk per trade
input double  InpRiskPerTradePercent      = 1.00;

// Hard daily loss lock
input double  InpMaxDailyDrawdownPercent  = 3.00;

// Hard peak-to-equity drawdown lock
input double  InpMaxTotalDrawdownPercent  = 6.00;

// Maximum total open risk for this EA
input double  InpMaxOpenRiskPercent       = 3.00;

// Optional maximum lot ceiling
input double  InpMaxLotSize               = 0.30;

// Fixed lot mode is useful for diagnostic testing.
// When false, risk engine determines volume.
input bool    InpUseFixedLot              = false;
input double  InpFixedLotSize             = 0.01;

// Reject structural stops outside these distances.
// These are price distances, not USD.
input double  InpMinStopDistancePoints    = 0.0;
input double  InpMaxStopDistancePoints    = 0.0;

//--------------------------------------------------------------------
// EXECUTION
//--------------------------------------------------------------------
input group "=== Execution ==="

input int     InpDeviationPoints          = 30;
input double  InpMaxSpreadPoints          = 0.0;

// If true, a kill switch will attempt to close this EA's positions.
input bool    InpClosePositionsOnKill     = false;

//--------------------------------------------------------------------
// STATE
//--------------------------------------------------------------------
input group "=== Persistent State ==="

input bool    InpPersistState             = true;

//====================================================================
// GLOBALS
//====================================================================

CTrade m_trade;

int h_atr = INVALID_HANDLE;
int h_ema = INVALID_HANDLE;

string g_prefix = "";

bool g_kill_switch = false;

datetime g_utc_day_start = 0;

double g_day_start_equity = 0.0;
double g_peak_equity      = 0.0;

bool g_london_processed = false;
bool g_ny_processed     = false;

//====================================================================
// ENUMS / STRUCTURES
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
   double loss_per_lot;

   double volume;

   double current_open_risk;
   double projected_open_risk;

   double daily_drawdown;
   double total_drawdown;

   string reason;
};

//====================================================================
// UTILITY
//====================================================================

string GVName(string suffix)
{
   return(g_prefix + suffix);
}

//--------------------------------------------------------------------
// Normalize price
//--------------------------------------------------------------------
double NormalizePrice(double price)
{
   return(NormalizeDouble(price, _Digits));
}

//--------------------------------------------------------------------
// Normalize volume DOWN to broker step
//--------------------------------------------------------------------
double NormalizeVolumeDown(double volume)
{
   double min_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step       = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(step <= 0.0)
      return(0.0);

   volume = MathMin(volume, max_volume);

   double normalized = MathFloor(volume / step + 1e-9) * step;

   if(normalized < min_volume)
      return(0.0);

   int digits = 2;

   if(step < 0.01)
      digits = 4;

   if(step < 0.001)
      digits = 5;

   return(NormalizeDouble(normalized, digits));
}

//--------------------------------------------------------------------
// Get current UTC time using configured broker offset
//--------------------------------------------------------------------
datetime GetUtcNow()
{
   datetime server_time = TimeCurrent();

   // Server time = UTC + offset
   return(server_time - InpBrokerUtcOffsetHours * 3600);
}

//--------------------------------------------------------------------
// Start of UTC calendar day
//--------------------------------------------------------------------
datetime GetUtcDayStart(datetime utc_time)
{
   MqlDateTime dt;
   TimeToStruct(utc_time, dt);

   dt.hour = 0;
   dt.min  = 0;
   dt.sec  = 0;

   return(StructToTime(dt));
}

//--------------------------------------------------------------------
// Create session timestamp on a UTC day
//--------------------------------------------------------------------
datetime BuildSessionTime(
   datetime day_start,
   int hour,
   int minute
)
{
   return(day_start + hour * 3600 + minute * 60);
}

//====================================================================
// FORWARD DECLARATIONS
//====================================================================
void CloseAllEAPositions();

//====================================================================
// PERSISTENT STATE
//====================================================================

void SaveState()
{
   if(!InpPersistState)
      return;

   GlobalVariableSet(GVName("DAY"),        (double)g_utc_day_start);
   GlobalVariableSet(GVName("DAY_EQUITY"), g_day_start_equity);
   GlobalVariableSet(GVName("PEAK"),       g_peak_equity);

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
void LoadState()
{
   datetime today = GetUtcDayStart(GetUtcNow());

   if(!InpPersistState)
   {
      g_utc_day_start     = today;
      g_day_start_equity  = AccountInfoDouble(ACCOUNT_EQUITY);
      g_peak_equity       = g_day_start_equity;
      g_london_processed  = false;
      g_ny_processed      = false;
      g_kill_switch       = false;
      return;
   }

   if(!GlobalVariableCheck(GVName("DAY")))
   {
      g_utc_day_start = today;
      g_day_start_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      g_peak_equity = g_day_start_equity;

      g_london_processed = false;
      g_ny_processed = false;
      g_kill_switch = false;

      SaveState();
      return;
   }

   datetime stored_day =
      (datetime)GlobalVariableGet(GVName("DAY"));

   if(stored_day != today)
   {
      g_utc_day_start = today;

      g_day_start_equity =
         AccountInfoDouble(ACCOUNT_EQUITY);

      g_london_processed = false;
      g_ny_processed = false;

      // Do not reset peak equity at the beginning of a day.
      if(GlobalVariableCheck(GVName("PEAK")))
         g_peak_equity =
            GlobalVariableGet(GVName("PEAK"));
      else
         g_peak_equity = g_day_start_equity;

      // Daily kill switch resets on a new UTC day.
      g_kill_switch = false;

      SaveState();
      return;
   }

   g_utc_day_start = stored_day;

   g_day_start_equity =
      GlobalVariableGet(GVName("DAY_EQUITY"));

   g_peak_equity =
      GlobalVariableGet(GVName("PEAK"));

   g_london_processed =
      GlobalVariableGet(GVName("LONDON")) > 0.5;

   g_ny_processed =
      GlobalVariableGet(GVName("NY")) > 0.5;

   g_kill_switch =
      GlobalVariableGet(GVName("KILL")) > 0.5;
}

//====================================================================
// RISK STATE
//====================================================================

double GetDailyDrawdownPercent()
{
   if(g_day_start_equity <= 0.0)
      return(0.0);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   double dd =
      (g_day_start_equity - equity)
      / g_day_start_equity
      * 100.0;

   return(MathMax(0.0, dd));
}

//--------------------------------------------------------------------
double GetTotalDrawdownPercent()
{
   if(g_peak_equity <= 0.0)
      return(0.0);

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   double dd =
      (g_peak_equity - equity)
      / g_peak_equity
      * 100.0;

   return(MathMax(0.0, dd));
}

//--------------------------------------------------------------------
void UpdateRiskState()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   if(equity <= 0.0)
      return;

   // Update peak equity.
   if(g_peak_equity <= 0.0 ||
      equity > g_peak_equity)
   {
      g_peak_equity = equity;
      SaveState();
   }

   double daily_dd = GetDailyDrawdownPercent();
   double total_dd = GetTotalDrawdownPercent();

   if(daily_dd >= InpMaxDailyDrawdownPercent)
   {
      if(!g_kill_switch)
      {
         PrintFormat(
            "QF RISK: DAILY KILL SWITCH. DD=%.2f%%",
            daily_dd
         );
      }

      g_kill_switch = true;
      SaveState();
   }

   if(total_dd >= InpMaxTotalDrawdownPercent)
   {
      if(!g_kill_switch)
      {
         PrintFormat(
            "QF RISK: TOTAL KILL SWITCH. DD=%.2f%%",
            total_dd
         );
      }

      g_kill_switch = true;
      SaveState();
   }

   if(g_kill_switch &&
      InpClosePositionsOnKill)
   {
      CloseAllEAPositions();
   }
}

//====================================================================
// POSITION / EXPOSURE
//====================================================================

int CountEAPositions()
{
   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if(PositionGetInteger(POSITION_MAGIC)
            != (long)InpMagicNumber)
         continue;

      count++;
   }

   return(count);
}

//--------------------------------------------------------------------
// Calculate monetary risk of one existing position
//--------------------------------------------------------------------
double CalculatePositionRisk(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
      return(0.0);

   string symbol =
      PositionGetString(POSITION_SYMBOL);

   ENUM_POSITION_TYPE type =
      (ENUM_POSITION_TYPE)
      PositionGetInteger(POSITION_TYPE);

   double volume =
      PositionGetDouble(POSITION_VOLUME);

   double open_price =
      PositionGetDouble(POSITION_PRICE_OPEN);

   double sl =
      PositionGetDouble(POSITION_SL);

   if(sl <= 0.0)
      return(0.0);

   double profit = 0.0;

   ENUM_ORDER_TYPE order_type;

   if(type == POSITION_TYPE_BUY)
      order_type = ORDER_TYPE_BUY;
   else
      order_type = ORDER_TYPE_SELL;

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
// Total open risk for this EA
//--------------------------------------------------------------------
double CalculateOpenRiskMoney()
{
   double total = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if(PositionGetInteger(POSITION_MAGIC)
            != (long)InpMagicNumber)
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

   // Shift 1 = last completed M1 candle.
   if(CopyBuffer(h_atr, 0, 1, 1, buffer) != 1)
      return(false);

   atr = buffer[0];

   if(atr <= 0.0)
      return(false);

   return(true);
}

//--------------------------------------------------------------------
bool GetEMA(double &ema)
{
   double buffer[];

   ArraySetAsSeries(buffer, true);

   // Shift 1 = last completed M15 candle.
   if(CopyBuffer(h_ema, 0, 1, 1, buffer) != 1)
      return(false);

   ema = buffer[0];

   if(ema <= 0.0)
      return(false);

   return(true);
}

//====================================================================
// OPENING RANGE
//====================================================================

bool BuildOpeningRange(
   datetime start,
   int minutes,
   OpeningRange &range
)
{
   range.valid = false;
   range.start = start;
   range.end   = start + minutes * 60;

   if(minutes <= 0)
      return(false);

   // The range must be completely closed.
   datetime utc_now = GetUtcNow();

   if(utc_now < range.end)
      return(false);

   // Convert UTC timestamps to server timestamps.
   datetime server_start =
      start + InpBrokerUtcOffsetHours * 3600;

   MqlRates rates[];

   ArraySetAsSeries(rates, false);

   int copied =
      CopyRates(
         _Symbol,
         PERIOD_M1,
         server_start,
         minutes,
         rates
      );

   if(copied != minutes)
   {
      PrintFormat(
         "QF DATA: Opening range unavailable. Expected=%d Got=%d",
         minutes,
         copied
      );

      return(false);
   }

   range.open  = rates[0].open;
   range.high  = rates[0].high;
   range.low   = rates[0].low;
   range.close = rates[minutes - 1].close;
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
   datetime now = GetUtcNow();

   datetime day =
      GetUtcDayStart(now);

   // London
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
      session_name = "LONDON";
      session_start = london_start;
      range_minutes = InpLondonRangeMinutes;

      return(true);
   }

   // New York
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
      session_name = "NEW_YORK";
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

   signal.valid = false;
   signal.direction = SIGNAL_NONE;
   signal.entry = 0.0;
   signal.stop = 0.0;
   signal.target = 0.0;
   signal.atr = atr;
   signal.ema = ema;
   signal.displacement = range.close - range.open;
   signal.session = session;
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

   if(ask <= 0.0 || bid <= 0.0)
   {
      signal.reason = "Invalid market price";
      return(signal);
   }

   double minimum_displacement =
      InpMinDisplacementATR * atr;

   // ---------------------------------------------------------------
   // BUY
   // ---------------------------------------------------------------
   if(signal.displacement > 0.0 &&
      signal.displacement >= minimum_displacement &&
      range.close > ema)
   {
      signal.direction = SIGNAL_BUY;
      signal.entry = ask;
      signal.stop = range.low;

      double stop_distance =
         signal.entry - signal.stop;

      if(stop_distance <= 0.0)
      {
         signal.reason = "Invalid BUY structural stop";
         return(signal);
      }

      signal.target =
         signal.entry +
         stop_distance *
         InpRiskRewardRatio;

      signal.valid = true;
      signal.reason = "BUY momentum + EMA confirmation";

      return(signal);
   }

   // ---------------------------------------------------------------
   // SELL
   // ---------------------------------------------------------------
   if(signal.displacement < 0.0 &&
      MathAbs(signal.displacement) >=
         minimum_displacement &&
      range.close < ema)
   {
      signal.direction = SIGNAL_SELL;
      signal.entry = bid;
      signal.stop = range.high;

      double stop_distance =
         signal.stop - signal.entry;

      if(stop_distance <= 0.0)
      {
         signal.reason = "Invalid SELL structural stop";
         return(signal);
      }

      signal.target =
         signal.entry -
         stop_distance *
         InpRiskRewardRatio;

      signal.valid = true;
      signal.reason = "SELL momentum + EMA confirmation";

      return(signal);
   }

   signal.reason =
      "No qualifying momentum/EMA signal";

   return(signal);
}

//====================================================================
// STOP VALIDATION
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

   double stop_level_points =
      (double)SymbolInfoInteger(
         _Symbol,
         SYMBOL_TRADE_STOPS_LEVEL
      );

   double freeze_level_points =
      (double)SymbolInfoInteger(
         _Symbol,
         SYMBOL_TRADE_FREEZE_LEVEL
      );

   double minimum_broker_distance =
      MathMax(
         stop_level_points,
         freeze_level_points
      ) * point;

   double stop_distance =
      MathAbs(signal.entry - signal.stop);

   if(stop_distance <= 0.0)
   {
      reason = "Zero/negative stop distance";
      return(false);
   }

   if(stop_distance < minimum_broker_distance)
   {
      reason =
         StringFormat(
            "Structural SL inside broker minimum distance %.5f",
            minimum_broker_distance
         );

      return(false);
   }

   if(InpMinStopDistancePoints > 0.0 &&
      stop_distance / point <
         InpMinStopDistancePoints)
   {
      reason = "Stop below configured minimum distance";
      return(false);
   }

   if(InpMaxStopDistancePoints > 0.0 &&
      stop_distance / point >
         InpMaxStopDistancePoints)
   {
      reason = "Structural stop exceeds configured maximum distance";
      return(false);
   }

   // Check TP direction.
   if(signal.direction == SIGNAL_BUY)
   {
      if(signal.stop >= signal.entry)
      {
         reason = "BUY SL is not below entry";
         return(false);
      }

      if(signal.target <= signal.entry)
      {
         reason = "BUY TP is not above entry";
         return(false);
      }
   }
   else if(signal.direction == SIGNAL_SELL)
   {
      if(signal.stop <= signal.entry)
      {
         reason = "SELL SL is not above entry";
         return(false);
      }

      if(signal.target >= signal.entry)
      {
         reason = "SELL TP is not below entry";
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
      reason = "Invalid point size";
      return(false);
   }

   double spread_points =
      (ask - bid) / point;

   if(spread_points > InpMaxSpreadPoints)
   {
      reason =
         StringFormat(
            "Spread %.1f > maximum %.1f points",
            spread_points,
            InpMaxSpreadPoints
         );

      return(false);
   }

   return(true);
}

//====================================================================
// POSITION SIZING
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
      decision.reason = "Invalid account equity";
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
      decision.reason = "Invalid stop distance";
      return(false);
   }

   //-----------------------------------------------------------------
   // Fixed-lot diagnostic mode
   //-----------------------------------------------------------------
   if(InpUseFixedLot)
   {
      decision.volume =
         NormalizeVolumeDown(
            MathMin(
               InpFixedLotSize,
               InpMaxLotSize
            )
         );

      if(decision.volume <= 0.0)
      {
         decision.reason =
            "Fixed lot below broker minimum";
         return(false);
      }

      double estimated_loss = 0.0;

      ENUM_ORDER_TYPE order_type;

      if(signal.direction == SIGNAL_BUY)
         order_type = ORDER_TYPE_BUY;
      else
         order_type = ORDER_TYPE_SELL;

      if(!OrderCalcProfit(
            order_type,
            _Symbol,
            decision.volume,
            signal.entry,
            signal.stop,
            estimated_loss))
      {
         decision.reason =
            "OrderCalcProfit failed";
         return(false);
      }

      decision.loss_per_lot =
         MathAbs(estimated_loss) /
         decision.volume;

      return(true);
   }

   //-----------------------------------------------------------------
   // Risk-based volume
   //-----------------------------------------------------------------

   ENUM_ORDER_TYPE order_type;

   if(signal.direction == SIGNAL_BUY)
      order_type = ORDER_TYPE_BUY;
   else
      order_type = ORDER_TYPE_SELL;

   double loss_one_lot = 0.0;

   if(!OrderCalcProfit(
         order_type,
         _Symbol,
         1.0,
         signal.entry,
         signal.stop,
         loss_one_lot))
   {
      decision.reason =
         "Unable to calculate 1-lot stop loss";
      return(false);
   }

   loss_one_lot =
      MathAbs(loss_one_lot);

   if(loss_one_lot <= 0.0)
   {
      decision.reason =
         "Calculated 1-lot loss is zero";
      return(false);
   }

   decision.loss_per_lot =
      loss_one_lot;

   double raw_volume =
      decision.risk_money /
      loss_one_lot;

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
      decision.reason =
         "Calculated volume below broker minimum";
      return(false);
   }

   return(true);
}

//====================================================================
// RISK ENGINE
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
   // Kill switch
   //-----------------------------------------------------------------
   if(g_kill_switch)
   {
      decision.reason =
         "Risk kill switch active";
      return(decision);
   }

   //-----------------------------------------------------------------
   // Daily DD
   //-----------------------------------------------------------------
   if(decision.daily_drawdown >=
      InpMaxDailyDrawdownPercent)
   {
      decision.reason =
         "Daily drawdown limit reached";
      return(decision);
   }

   //-----------------------------------------------------------------
   // Total DD
   //-----------------------------------------------------------------
   if(decision.total_drawdown >=
      InpMaxTotalDrawdownPercent)
   {
      decision.reason =
         "Total drawdown limit reached";
      return(decision);
   }

   //-----------------------------------------------------------------
   // Existing position on this EA
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
      decision.reason = reason;
      return(decision);
   }

   //-----------------------------------------------------------------
   // Structural stop validation
   //-----------------------------------------------------------------
   if(!ValidateStops(signal, reason))
   {
      decision.reason = reason;
      return(decision);
   }

   //-----------------------------------------------------------------
   // Position sizing
   //-----------------------------------------------------------------
   if(!CalculateRiskVolume(signal, decision))
   {
      return(decision);
   }

   //-----------------------------------------------------------------
   // Open-risk exposure
   //-----------------------------------------------------------------
   decision.current_open_risk =
      CalculateOpenRiskMoney();

   decision.projected_open_risk =
      decision.current_open_risk +
      decision.risk_money;

   double maximum_open_risk =
      decision.equity *
      InpMaxOpenRiskPercent /
      100.0;

   if(decision.projected_open_risk >
      maximum_open_risk)
   {
      decision.reason =
         StringFormat(
            "Open-risk cap exceeded: %.2f > %.2f",
            decision.projected_open_risk,
            maximum_open_risk
         );

      return(decision);
   }

   //-----------------------------------------------------------------
   // Margin check
   //-----------------------------------------------------------------
   double margin_required = 0.0;

   ENUM_ORDER_TYPE order_type;

   if(signal.direction == SIGNAL_BUY)
      order_type = ORDER_TYPE_BUY;
   else
      order_type = ORDER_TYPE_SELL;

   if(!OrderCalcMargin(
         order_type,
         _Symbol,
         decision.volume,
         signal.entry,
         margin_required))
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
            "Insufficient margin: %.2f required, %.2f free",
            margin_required,
            free_margin
         );

      return(decision);
   }

   //-----------------------------------------------------------------
   // Approved
   //-----------------------------------------------------------------
   decision.approved = true;
   decision.reason = "Risk approved";

   return(decision);
}

//====================================================================
// EXECUTION
//====================================================================

bool ExecuteTrade(
   TradeSignal &signal,
   RiskDecision &risk
)
{
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

   if(ask <= 0.0 || bid <= 0.0)
   {
      Print("QF EXECUTION: Invalid market prices");
      return(false);
   }

   // Refresh entry price immediately before execution.
   double entry;

   if(signal.direction == SIGNAL_BUY)
      entry = ask;
   else
      entry = bid;

   // Preserve structural stop distance.
   double stop_distance =
      MathAbs(
         signal.entry -
         signal.stop
      );

   if(signal.direction == SIGNAL_BUY)
   {
      signal.entry = entry;
      signal.stop =
         NormalizePrice(
            entry - stop_distance
         );

      signal.target =
         NormalizePrice(
            entry +
            stop_distance *
            InpRiskRewardRatio
         );
   }
   else
   {
      signal.entry = entry;
      signal.stop =
         NormalizePrice(
            entry + stop_distance
         );

      signal.target =
         NormalizePrice(
            entry -
            stop_distance *
            InpRiskRewardRatio
         );
   }

   //-----------------------------------------------------------------
   // Final stop validation after price refresh.
   //-----------------------------------------------------------------
   string reason;

   if(!ValidateStops(signal, reason))
   {
      PrintFormat(
         "QF EXECUTION: Final stop validation failed: %s",
         reason
      );

      return(false);
   }

   //-----------------------------------------------------------------
   // Recalculate actual volume because entry changed.
   //-----------------------------------------------------------------
   RiskDecision final_risk;

   if(!CalculateRiskVolume(
         signal,
         final_risk))
   {
      PrintFormat(
         "QF EXECUTION: Final sizing failed: %s",
         final_risk.reason
      );

      return(false);
   }

   if(final_risk.volume <= 0.0)
   {
      Print("QF EXECUTION: Final volume is zero");
      return(false);
   }

   //-----------------------------------------------------------------
   // Margin
   //-----------------------------------------------------------------
   double margin_required = 0.0;

   ENUM_ORDER_TYPE order_type;

   if(signal.direction == SIGNAL_BUY)
      order_type = ORDER_TYPE_BUY;
   else
      order_type = ORDER_TYPE_SELL;

   if(!OrderCalcMargin(
         order_type,
         _Symbol,
         final_risk.volume,
         signal.entry,
         margin_required))
   {
      Print("QF EXECUTION: Margin calculation failed");
      return(false);
   }

   if(margin_required >
      AccountInfoDouble(ACCOUNT_MARGIN_FREE))
   {
      Print("QF EXECUTION: Insufficient free margin");
      return(false);
   }

   //-----------------------------------------------------------------
   // Execute
   //-----------------------------------------------------------------

   string comment;

   if(signal.direction == SIGNAL_BUY)
      comment =
         StringFormat(
            "%s BUY",
            InpStrategyName
         );
   else
      comment =
         StringFormat(
            "%s SELL",
            InpStrategyName
         );

   bool sent = false;

   ResetLastError();

   if(signal.direction == SIGNAL_BUY)
   {
      sent =
         m_trade.Buy(
            final_risk.volume,
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
            final_risk.volume,
            _Symbol,
            0.0,
            signal.stop,
            signal.target,
            comment
         );
   }

   //-----------------------------------------------------------------
   // IMPORTANT:
   // CTrade returning true does not by itself guarantee execution.
   //-----------------------------------------------------------------
   uint retcode =
      m_trade.ResultRetcode();

   string ret_desc =
      m_trade.ResultRetcodeDescription();

   if(!sent)
   {
      PrintFormat(
         "QF EXECUTION FAILED: retcode=%u %s error=%d",
         retcode,
         ret_desc,
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
         ret_desc
      );

      return(false);
   }

   //-----------------------------------------------------------------
   // Audit log
   //-----------------------------------------------------------------

   PrintFormat(
      "QF EXECUTED | %s | %s | Vol=%.4f | Entry=%.*f | SL=%.*f | TP=%.*f | Risk=%.2f",
      signal.session,
      signal.direction == SIGNAL_BUY
         ? "BUY"
         : "SELL",
      final_risk.volume,
      _Digits,
      signal.entry,
      _Digits,
      signal.stop,
      _Digits,
      signal.target,
      final_risk.risk_money
   );

   return(true);
}

//====================================================================
// CLOSE EA POSITIONS
//====================================================================

void CloseAllEAPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(ticket == 0)
         continue;

      if(PositionGetInteger(POSITION_MAGIC)
            != (long)InpMagicNumber)
         continue;

      string symbol =
         PositionGetString(POSITION_SYMBOL);

      if(!m_trade.PositionClose(ticket))
      {
         PrintFormat(
            "QF KILL SWITCH: Failed to close ticket %I64u on %s: %s",
            ticket,
            symbol,
            m_trade.ResultRetcodeDescription()
         );
      }
      else
      {
         PrintFormat(
            "QF KILL SWITCH: Closed ticket %I64u on %s",
            ticket,
            symbol
         );
      }
   }
}

//====================================================================
// SESSION PROCESSING
//====================================================================

bool ProcessSession(
   string session_name,
   datetime session_start,
   int range_minutes
)
{
   //-----------------------------------------------------------------
   // Build completed opening range
   //-----------------------------------------------------------------

   OpeningRange range;

   if(!BuildOpeningRange(
         session_start,
         range_minutes,
         range))
   {
      return(false);
   }

   //-----------------------------------------------------------------
   // Indicators
   //-----------------------------------------------------------------

   double atr = 0.0;
   double ema = 0.0;

   if(!GetATR(atr))
   {
      Print(
         "QF DATA: ATR unavailable"
      );

      return(false);
   }

   if(!GetEMA(ema))
   {
      Print(
         "QF DATA: EMA unavailable"
      );

      return(false);
   }

   //-----------------------------------------------------------------
   // Strategy
   //-----------------------------------------------------------------

   TradeSignal signal =
      EvaluateSignal(
         range,
         atr,
         ema,
         session_name
      );

   if(!signal.valid)
   {
      PrintFormat(
         "QF SIGNAL: %s | %s | displacement=%.5f ATR=%.5f EMA=%.5f",
         session_name,
         signal.reason,
         signal.displacement,
         atr,
         ema
      );

      return(false);
   }

   //-----------------------------------------------------------------
   // Risk approval
   //-----------------------------------------------------------------

   RiskDecision risk =
      ApproveRisk(signal);

   if(!risk.approved)
   {
      PrintFormat(
         "QF RISK REJECTED | %s | %s",
         session_name,
         risk.reason
      );

      return(false);
   }

   //-----------------------------------------------------------------
   // Execution
   //-----------------------------------------------------------------

   bool executed =
      ExecuteTrade(
         signal,
         risk
      );

   return(executed);
}

//====================================================================
// INITIALIZATION
//====================================================================

int OnInit()
{
   //-----------------------------------------------------------------
   // Validate configuration
   //-----------------------------------------------------------------

   if(InpRiskPerTradePercent <= 0.0)
   {
      Print(
         "QF INIT ERROR: Risk per trade must be > 0"
      );

      return(INIT_FAILED);
   }

   if(InpRiskPerTradePercent >=
      InpMaxDailyDrawdownPercent)
   {
      Print(
         "QF INIT WARNING: Single-trade risk >= daily DD limit"
      );
   }

   if(InpRiskRewardRatio <= 0.0)
   {
      Print(
         "QF INIT ERROR: Risk/reward must be > 0"
      );

      return(INIT_FAILED);
   }

   if(InpLondonRangeMinutes <= 0 ||
      InpNYRangeMinutes <= 0)
   {
      Print(
         "QF INIT ERROR: Range minutes must be > 0"
      );

      return(INIT_FAILED);
   }

   //-----------------------------------------------------------------
   // Magic / trade setup
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
   // Indicator handles
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

   if(h_atr == INVALID_HANDLE)
   {
      Print(
         "QF INIT ERROR: ATR handle failed"
      );

      return(INIT_FAILED);
   }

   if(h_ema == INVALID_HANDLE)
   {
      Print(
         "QF INIT ERROR: EMA handle failed"
      );

      IndicatorRelease(h_atr);

      return(INIT_FAILED);
   }

   //-----------------------------------------------------------------
   // Persistent-state namespace
   //-----------------------------------------------------------------

   g_prefix =
      StringFormat(
         "QF_%I64u_%s_",
         InpMagicNumber,
         _Symbol
      );

   //-----------------------------------------------------------------
   // Load state
   //-----------------------------------------------------------------

   LoadState();

   //-----------------------------------------------------------------
   // Startup risk evaluation
   //-----------------------------------------------------------------

   UpdateRiskState();

   PrintFormat(
      "============================================================"
   );

   PrintFormat(
      "QuantForge Crabel Executor v8.0"
   );

   PrintFormat(
      "Symbol: %s",
      _Symbol
   );

   PrintFormat(
      "Magic: %I64u",
      InpMagicNumber
   );

   PrintFormat(
      "Broker UTC Offset: %+d",
      InpBrokerUtcOffsetHours
   );

   PrintFormat(
      "Risk/Trade: %.2f%%",
      InpRiskPerTradePercent
   );

   PrintFormat(
      "Daily DD Limit: %.2f%%",
      InpMaxDailyDrawdownPercent
   );

   PrintFormat(
      "Total DD Limit: %.2f%%",
      InpMaxTotalDrawdownPercent
   );

   PrintFormat(
      "Max Open Risk: %.2f%%",
      InpMaxOpenRiskPercent
   );

   PrintFormat(
      "R:R: 1:%.2f",
      InpRiskRewardRatio
   );

   PrintFormat(
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
// MAIN TICK
//====================================================================

void OnTick()
{
   //-----------------------------------------------------------------
   // Maintain risk state first.
   //-----------------------------------------------------------------

   datetime now =
      GetUtcNow();

   datetime today =
      GetUtcDayStart(now);

   //-----------------------------------------------------------------
   // Detect new UTC day
   //-----------------------------------------------------------------

   if(today != g_utc_day_start)
   {
      g_utc_day_start = today;

      g_day_start_equity =
         AccountInfoDouble(
            ACCOUNT_EQUITY
         );

      g_london_processed = false;
      g_ny_processed = false;

      // Kill switch resets for the new daily session.
      // Total drawdown is still independently monitored.
      g_kill_switch = false;

      SaveState();

      PrintFormat(
         "QF SESSION: New UTC day. Starting equity=%.2f",
         g_day_start_equity
      );
   }

   //-----------------------------------------------------------------
   // Risk engine has priority over everything.
   //-----------------------------------------------------------------

   UpdateRiskState();

   if(g_kill_switch)
      return;

   //-----------------------------------------------------------------
   // Only one active EA position at a time.
   //-----------------------------------------------------------------

   if(CountEAPositions() > 0)
      return;

   //-----------------------------------------------------------------
   // Ask session engine whether a completed session is ready.
   //-----------------------------------------------------------------

   string session_name;
   datetime session_start;
   int range_minutes;

   if(!GetReadySession(
         session_name,
         session_start,
         range_minutes))
   {
      return;
   }

   //-----------------------------------------------------------------
   // Process session.
   //-----------------------------------------------------------------

   bool executed =
      ProcessSession(
         session_name,
         session_start,
         range_minutes
      );

   //-----------------------------------------------------------------
   // IMPORTANT:
   // Mark session processed whether a trade happened or not.
   //
   // This prevents repeated evaluation every tick and makes the
   // session a deterministic once-per-day event.
   //-----------------------------------------------------------------

   if(session_name == "LONDON")
   {
      g_london_processed = true;
      SaveState();
   }
   else if(session_name == "NEW_YORK")
   {
      g_ny_processed = true;
      SaveState();
   }

   if(executed)
   {
      PrintFormat(
         "QF SESSION COMPLETE: %s trade executed.",
         session_name
      );
   }
   else
   {
      PrintFormat(
         "QF SESSION COMPLETE: %s evaluated, no trade executed.",
         session_name
      );
   }
}
//+------------------------------------------------------------------+
