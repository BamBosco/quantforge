//+------------------------------------------------------------------+
//| QuantForge Read-Only MT5 Connectivity Bridge                     |
//| Supports 24/7 Crypto (#BTCUSD) & Forex/Metals (XAUUSD)           |
//| Auto-detects chart symbol, streams real-time ticks & M1 bars.    |
//| NEVER executes orders or closes positions — pure read-only feed. |
//+------------------------------------------------------------------+
#property copyright "QuantForge Systems"
#property link      "https://github.com/quantforge"
#property version   "2.03"
#property strict

//--- Input Parameters
input string BridgeUrl         = "http://127.0.0.1:8765/v1/mt5/snapshots"; // QuantForge Bridge URL
input string BridgeToken       = "quantforge-live-token-2026";             // Bearer Auth Token
input string SymbolToReport    = "";                                       // Symbol (Empty = Auto-detect chart symbol)
input int    HeartbeatSeconds  = 3;                                        // Snapshot interval in seconds (Default: 3)
input bool   SendOnNewTick     = true;                                     // Stream live on price changes (Throttled)

//--- Internal State
string g_symbol;
uint   g_last_send_tick_ms = 0;
bool   g_is_sending = false;
int    g_consecutive_errors = 0;
int    g_snapshots_sent = 0;

//+------------------------------------------------------------------+
//| Helper Utilities (Declared first for MQL5 compiler compatibility)|
//+------------------------------------------------------------------+
string JsonEscape(string value)
  {
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return(value);
  }

string BoolJson(const bool value)
  {
   return(value ? "true" : "false");
  }

string UtcTimestamp(datetime value)
  {
   return(TimeToString(value, TIME_DATE|TIME_SECONDS) + "Z");
  }

string TerminalClock(datetime value)
  {
   return(TimeToString(value, TIME_DATE|TIME_SECONDS));
  }

string OrderSide(const ENUM_ORDER_TYPE type)
  {
   if(type == ORDER_TYPE_BUY_LIMIT || type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_BUY_STOP_LIMIT)
      return("buy");
   return("sell");
  }

string OrderTypeText(const ENUM_ORDER_TYPE type)
  {
   if(type == ORDER_TYPE_BUY_LIMIT) return("buy_limit");
   if(type == ORDER_TYPE_SELL_LIMIT) return("sell_limit");
   if(type == ORDER_TYPE_BUY_STOP) return("buy_stop");
   if(type == ORDER_TYPE_SELL_STOP) return("sell_stop");
   if(type == ORDER_TYPE_BUY_STOP_LIMIT) return("buy_stop_limit");
   if(type == ORDER_TYPE_SELL_STOP_LIMIT) return("sell_stop_limit");
   return("unknown");
  }

string IntegerPropertyJson(const ENUM_SYMBOL_INFO_INTEGER property)
  {
   long value = 0;
   if(!SymbolInfoInteger(g_symbol, property, value)) return("null");
   return(StringFormat("%I64d", value));
  }

string DoublePropertyJson(const ENUM_SYMBOL_INFO_DOUBLE property)
  {
   double value = 0.0;
   if(!SymbolInfoDouble(g_symbol, property, value)) return("null");
   return(StringFormat("%.8f", value));
  }

string StringPropertyJson(const ENUM_SYMBOL_INFO_STRING property)
  {
   string value = "";
   if(!SymbolInfoString(g_symbol, property, value)) return("null");
   return("\"" + JsonEscape(value) + "\"");
  }

string SupportedFillingModesJson()
  {
   int modes = (int)SymbolInfoInteger(g_symbol, SYMBOL_FILLING_MODE);
   string result = "[";
   if((modes & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      result += "\"fill_or_kill\"";
   if((modes & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
     {
      if(StringLen(result) > 1) result += ",";
      result += "\"immediate_or_cancel\"";
     }
   if((modes & SYMBOL_FILLING_BOC) == SYMBOL_FILLING_BOC)
     {
      if(StringLen(result) > 1) result += ",";
      result += "\"book_or_cancel\"";
     }
   return(result + "]");
  }

string CandleJson(const MqlRates &bar)
  {
   datetime utc_open = bar.time + (TimeGMT() - TimeCurrent());
   return(StringFormat("[{\"open_time_utc\":\"%s\",\"open\":%.4f,\"high\":%.4f,\"low\":%.4f,\"close\":%.4f,\"tick_volume\":%I64d}]", UtcTimestamp(utc_open), bar.open, bar.high, bar.low, bar.close, bar.tick_volume));
  }

string PositionsJson()
  {
   string result = "[";
   for(int i = 0; i < PositionsTotal(); i++)
     {
      ulong ticket = PositionGetTicket(i); if(ticket == 0) continue;
      if(StringLen(result) > 1) result += ",";
      string side = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "buy" : "sell";
      datetime opened_utc = (datetime)PositionGetInteger(POSITION_TIME) + (TimeGMT() - TimeCurrent());
      result += StringFormat("{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"side\":\"%s\",\"volume\":%.4f,\"price_open\":%.4f,\"price_current\":%.4f,\"sl\":%.4f,\"tp\":%.4f,\"profit\":%.2f,\"opened_at_utc\":\"%s\"}", ticket, JsonEscape(PositionGetString(POSITION_SYMBOL)), side, PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), PositionGetDouble(POSITION_PRICE_CURRENT), PositionGetDouble(POSITION_SL), PositionGetDouble(POSITION_TP), PositionGetDouble(POSITION_PROFIT), UtcTimestamp(opened_utc));
     }
   return(result + "]");
  }

string OrdersJson()
  {
   string result = "[";
   for(int i = 0; i < OrdersTotal(); i++)
     {
      ulong ticket = OrderGetTicket(i); if(ticket == 0) continue;
      if(StringLen(result) > 1) result += ",";
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      result += StringFormat("{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"side\":\"%s\",\"type\":\"%s\",\"volume\":%.4f,\"price\":%.4f,\"sl\":%.4f,\"tp\":%.4f}", ticket, JsonEscape(OrderGetString(ORDER_SYMBOL)), OrderSide(type), OrderTypeText(type), OrderGetDouble(ORDER_VOLUME_CURRENT), OrderGetDouble(ORDER_PRICE_OPEN), OrderGetDouble(ORDER_SL), OrderGetDouble(ORDER_TP));
     }
   return(result + "]");
  }

string DealsJson()
  {
   datetime now = TimeCurrent(); if(!HistorySelect(now - 60, now)) return("[]");
   string result = "[";
   for(int i = 0; i < HistoryDealsTotal(); i++)
     {
      ulong ticket = HistoryDealGetTicket(i); if(ticket == 0) continue;
      if(StringLen(result) > 1) result += ",";
      result += StringFormat("{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"volume\":%.4f,\"price\":%.4f,\"profit\":%.2f}", ticket, JsonEscape(HistoryDealGetString(ticket, DEAL_SYMBOL)), HistoryDealGetDouble(ticket, DEAL_VOLUME), HistoryDealGetDouble(ticket, DEAL_PRICE), HistoryDealGetDouble(ticket, DEAL_PROFIT));
     }
   return(result + "]");
  }

void UpdateChartComment(string text)
  {
   Comment("\n=======================================================\n" +
           "  🚀 QUANTFORGE READ-ONLY BRIDGE v2.03 (BTC & XAU)  \n" +
           "=======================================================\n" +
           text + "\n" +
           "=======================================================");
  }

//+------------------------------------------------------------------+
//| Core Snapshot Sender                                             |
//+------------------------------------------------------------------+
void SendSnapshot()
  {
   // Concurrency lock & throttle: prevent Wine WebRequest socket collisions
   if(g_is_sending) return;
   uint now_ms = GetTickCount();
   if(now_ms - g_last_send_tick_ms < 1500) return;

   g_is_sending = true;
   g_last_send_tick_ms = now_ms;

   MqlTick tick;
   if(!SymbolInfoTick(g_symbol, tick))
     {
      g_is_sending = false;
      UpdateChartComment("⚠️ Waiting for live ticks on " + g_symbol + "...");
      return;
     }

   MqlRates minute_bars[];
   ResetLastError();
   int copied = CopyRates(g_symbol, PERIOD_M1, 0, 2, minute_bars);
   bool has_completed_m1 = (copied >= 2);
   string missing = has_completed_m1 ? "[]" : "[\"completed_m1\"]";
   string candle = has_completed_m1 ? CandleJson(minute_bars[0]) : "[]";

   string timestamp = UtcTimestamp(TimeGMT());
   string server_clock = TerminalClock(TimeCurrent());
   string local_clock = TerminalClock(TimeLocal());
   string utc_clock = UtcTimestamp(TimeGMT());

   double point = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   if(point <= 0) point = 0.01;
   int digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);

   string filling_modes = SupportedFillingModesJson();
   string trade_mode = IntegerPropertyJson(SYMBOL_TRADE_MODE);
   string order_mode = IntegerPropertyJson(SYMBOL_ORDER_MODE);
   string stop_level = IntegerPropertyJson(SYMBOL_TRADE_STOPS_LEVEL);
   string freeze_level = IntegerPropertyJson(SYMBOL_TRADE_FREEZE_LEVEL);
   string calculation_mode = IntegerPropertyJson(SYMBOL_TRADE_CALC_MODE);
   string profit_currency = StringPropertyJson(SYMBOL_CURRENCY_PROFIT);
   string margin_currency = StringPropertyJson(SYMBOL_CURRENCY_MARGIN);
   string tick_size = DoublePropertyJson(SYMBOL_TRADE_TICK_SIZE);
   string tick_value = DoublePropertyJson(SYMBOL_TRADE_TICK_VALUE);
   string tick_value_loss = DoublePropertyJson(SYMBOL_TRADE_TICK_VALUE_LOSS);
   string tick_value_profit = DoublePropertyJson(SYMBOL_TRADE_TICK_VALUE_PROFIT);

   double contract_size = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract_size <= 0) contract_size = (StringFind(g_symbol, "BTC") >= 0) ? 1.0 : 100.0;

   string body = StringFormat(
      "{\"schema_version\":2,\"observed_at_utc\":\"%s\","
      "\"time_provenance\":{\"terminal_server_time\":\"%s\",\"terminal_local_time\":\"%s\",\"terminal_utc_time\":\"%s\"},"
      "\"source\":{\"adapter\":\"mt5_read_only_ea\",\"broker_profile_id\":\"mt5_live_stream\"},"
      "\"account\":{\"account_id\":\"%I64d\",\"server\":\"%s\",\"currency\":\"%s\",\"balance\":%.4f,\"equity\":%.4f,\"margin\":%.4f,\"free_margin\":%.4f},"
      "\"instrument\":{\"canonical_instrument\":\"%s\",\"broker_symbol\":\"%s\",\"specification\":{\"point\":%.8f,\"digits\":%d,\"volume_min\":%.4f,\"volume_max\":%.4f,\"volume_step\":%.4f,\"contract_size\":%.4f,\"supported_filling_modes\":%s,\"trade_mode\":%s,\"order_mode\":%s,\"stop_level\":%s,\"freeze_level\":%s,\"trade_calculation_mode\":%s,\"profit_currency\":%s,\"margin_currency\":%s,\"tick_size\":%s,\"tick_value\":%s,\"tick_value_loss\":%s,\"tick_value_profit\":%s}},"
      "\"quote\":{\"bid\":%.4f,\"ask\":%.4f,\"tick_time_utc\":\"%s\",\"spread_points\":%.2f},"
      "\"candles\":{\"timeframe\":\"M1\",\"forming\":null,\"completed\":%s},\"positions\":%s,\"active_orders\":%s,"
      "\"deals\":{\"history_from_utc\":\"%s\",\"history_to_utc\":\"%s\",\"items\":%s},\"terminal\":{\"connected\":%s,\"trade_allowed\":%s},"
      "\"data_quality\":{\"adapter_status\":\"ok\",\"missing_data\":%s}}",
      timestamp, server_clock, local_clock, utc_clock, AccountInfoInteger(ACCOUNT_LOGIN), JsonEscape(AccountInfoString(ACCOUNT_SERVER)), JsonEscape(AccountInfoString(ACCOUNT_CURRENCY)),
      AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoDouble(ACCOUNT_MARGIN), AccountInfoDouble(ACCOUNT_MARGIN_FREE),
      JsonEscape(g_symbol), JsonEscape(g_symbol), point, digits,
      SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX), SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP), contract_size, filling_modes, trade_mode, order_mode, stop_level, freeze_level, calculation_mode, profit_currency, margin_currency, tick_size, tick_value, tick_value_loss, tick_value_profit,
      tick.bid, tick.ask, timestamp, (tick.ask - tick.bid) / point, candle, PositionsJson(), OrdersJson(), timestamp, timestamp, DealsJson(),
      BoolJson((bool)TerminalInfoInteger(TERMINAL_CONNECTED)), BoolJson((bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)), missing
   );

   char data[];
   int written = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(written <= 1)
     {
      g_is_sending = false;
      return;
     }
   ArrayResize(data, written - 1);

   char response[];
   string response_headers;
   string headers = "Content-Type: application/json\r\n";
   headers += "Authorization: Bearer " + BridgeToken + "\r\n";

   ResetLastError();
   int status = WebRequest("POST", BridgeUrl, headers, 2500, data, response, response_headers);
   g_is_sending = false;

   if(status == 202)
     {
      g_snapshots_sent++;
      g_consecutive_errors = 0;
      UpdateChartComment(StringFormat(
         "🟢 [QuantForge Connected & Streaming Live]\n"
         "Symbol: %s | Bid: %.2f | Ask: %.2f\n"
         "Snapshots Sent: %d | Status: 202 Accepted\n"
         "Server: %s | Account: %I64d",
         g_symbol, tick.bid, tick.ask, g_snapshots_sent, AccountInfoString(ACCOUNT_SERVER), AccountInfoInteger(ACCOUNT_LOGIN)
      ));
     }
   else
     {
      g_consecutive_errors++;
      // Only show error message if it fails 3 consecutive times to avoid transient UI flicker
      if(g_consecutive_errors >= 3)
        {
         if(status == 401)
           UpdateChartComment("🔴 ERROR 401: Unauthorized Bearer Token!\nEnter 'quantforge-live-token-2026' into EA inputs.");
         else if(status == -1 && GetLastError() == 4014)
           UpdateChartComment("🔴 ERROR 4014: WebRequest not allowed in MT5 Options!");
         else
           UpdateChartComment(StringFormat("⚠️ Bridge connection retry (Status: %d)...", status));
        }
     }
  }

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   // Auto-detect symbol from the chart if left empty
   g_symbol = (SymbolToReport == "") ? _Symbol : SymbolToReport;

   if(BridgeToken == "")
     {
      Print("❌ [QuantForge] BridgeToken is required! Enter token from your terminal bridge.");
      UpdateChartComment("🔴 ERROR: BridgeToken is required in EA inputs!\nEnter: quantforge-live-token-2026");
      return(INIT_PARAMETERS_INCORRECT);
     }

   if(HeartbeatSeconds < 1)
     {
      Print("❌ [QuantForge] HeartbeatSeconds must be at least 1.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   if(!SymbolSelect(g_symbol, true))
     {
      Print("❌ [QuantForge] Cannot select symbol: ", g_symbol);
      UpdateChartComment("🔴 ERROR: Cannot select symbol " + g_symbol);
      return(INIT_FAILED);
     }

   EventSetTimer(HeartbeatSeconds);
   SendSnapshot();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

//+------------------------------------------------------------------+
//| Expert timer function                                            |
//+------------------------------------------------------------------+
void OnTimer()
  {
   SendSnapshot();
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!SendOnNewTick) return;
   SendSnapshot();
  }
