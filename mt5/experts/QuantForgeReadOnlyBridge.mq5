//+------------------------------------------------------------------+
//| QuantForge read-only MT5 connectivity bridge                    |
//| This Expert Advisor never calls OrderSend, PositionClose, or    |
//| any other trading operation. It only POSTs local observations.  |
//+------------------------------------------------------------------+
#property copyright "QuantForge"
#property version   "1.01"
#property strict

input string BridgeUrl = "http://127.0.0.1:8765/v1/mt5/snapshots";
input string BridgeToken = "";
input string SymbolToReport = "XAUUSD";
input int HeartbeatSeconds = 30;

int OnInit()
  {
   if(BridgeToken == "")
     {
      Print("QuantForge bridge token is required. No snapshot will be sent.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(HeartbeatSeconds < 5)
     {
      Print("HeartbeatSeconds must be at least 5.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!SymbolSelect(SymbolToReport, true))
     {
      Print("Cannot select symbol: ", SymbolToReport);
      return(INIT_FAILED);
     }
   EventSetTimer(HeartbeatSeconds);
   SendSnapshot();
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

void OnTimer()
  {
   SendSnapshot();
  }

void SendSnapshot()
  {
   MqlTick tick;
   if(!SymbolInfoTick(SymbolToReport, tick))
     {
      Print("No tick available for ", SymbolToReport);
      return;
     }

   // Request the forming and preceding M1 bars as one contiguous range. MQL5
   // stores copied data oldest-first, so element zero is the completed bar.
   // This avoids relying on a standalone shift-one request while history is
   // being synchronized.
   MqlRates minute_bars[];
   ResetLastError();
   int copied = CopyRates(SymbolToReport, PERIOD_M1, 0, 2, minute_bars);
   bool has_completed_m1 = copied >= 2;
   string missing = has_completed_m1 ? "[]" : "[\"completed_m1\"]";
   string candle = has_completed_m1 ? CandleJson(minute_bars[0]) : "[]";
   if(!has_completed_m1)
     {
      Print("QuantForge M1 history unavailable. CopyRates copied=", copied, " error=", GetLastError());
     }
   string timestamp = UtcTimestamp(TimeGMT());
   // Preserve all three terminal clocks. Server time is intentionally not
   // labelled UTC: evidence derives any offset explicitly.
   string server_clock = TerminalClock(TimeCurrent());
   string local_clock = TerminalClock(TimeLocal());
   string utc_clock = UtcTimestamp(TimeGMT());
   double point = SymbolInfoDouble(SymbolToReport, SYMBOL_POINT);
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
   string body = StringFormat(
      "{\"schema_version\":2,\"observed_at_utc\":\"%s\","
      "\"time_provenance\":{\"terminal_server_time\":\"%s\",\"terminal_local_time\":\"%s\",\"terminal_utc_time\":\"%s\"},"
      "\"source\":{\"adapter\":\"mt5_read_only_ea\",\"broker_profile_id\":\"mt5_runtime_observed\"},"
      "\"account\":{\"account_id\":\"%I64d\",\"server\":\"%s\",\"currency\":\"%s\",\"balance\":%.8f,\"equity\":%.8f,\"margin\":%.8f,\"free_margin\":%.8f},"
      "\"instrument\":{\"canonical_instrument\":\"%s\",\"broker_symbol\":\"%s\",\"specification\":{\"point\":%.10f,\"digits\":%d,\"volume_min\":%.8f,\"volume_max\":%.8f,\"volume_step\":%.8f,\"contract_size\":%.8f,\"supported_filling_modes\":%s,\"trade_mode\":%s,\"order_mode\":%s,\"stop_level\":%s,\"freeze_level\":%s,\"trade_calculation_mode\":%s,\"profit_currency\":%s,\"margin_currency\":%s,\"tick_size\":%s,\"tick_value\":%s,\"tick_value_loss\":%s,\"tick_value_profit\":%s}},"
      "\"quote\":{\"bid\":%.8f,\"ask\":%.8f,\"tick_time_utc\":\"%s\",\"spread_points\":%.8f},"
      "\"candles\":{\"timeframe\":\"M1\",\"forming\":null,\"completed\":%s},\"positions\":%s,\"active_orders\":%s,"
      "\"deals\":{\"history_from_utc\":\"%s\",\"history_to_utc\":\"%s\",\"items\":%s},\"terminal\":{\"connected\":%s,\"trade_allowed\":%s},\"data_quality\":{\"adapter_status\":\"ok\",\"missing_data\":%s}}",
      timestamp, server_clock, local_clock, utc_clock, AccountInfoInteger(ACCOUNT_LOGIN), JsonEscape(AccountInfoString(ACCOUNT_SERVER)), JsonEscape(AccountInfoString(ACCOUNT_CURRENCY)),
      AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoDouble(ACCOUNT_MARGIN), AccountInfoDouble(ACCOUNT_MARGIN_FREE),
      JsonEscape(SymbolToReport), JsonEscape(SymbolToReport), point, (int)SymbolInfoInteger(SymbolToReport, SYMBOL_DIGITS),
      SymbolInfoDouble(SymbolToReport, SYMBOL_VOLUME_MIN), SymbolInfoDouble(SymbolToReport, SYMBOL_VOLUME_MAX), SymbolInfoDouble(SymbolToReport, SYMBOL_VOLUME_STEP), SymbolInfoDouble(SymbolToReport, SYMBOL_TRADE_CONTRACT_SIZE), filling_modes, trade_mode, order_mode, stop_level, freeze_level, calculation_mode, profit_currency, margin_currency, tick_size, tick_value, tick_value_loss, tick_value_profit,
      tick.bid, tick.ask, timestamp, (tick.ask-tick.bid)/point, candle, PositionsJson(), OrdersJson(), timestamp, timestamp, DealsJson(),
      BoolJson((bool)TerminalInfoInteger(TERMINAL_CONNECTED)), BoolJson((bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)), missing
   );

   char data[];
   int written = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(written <= 1)
     {
      Print("Unable to encode QuantForge snapshot.");
      return;
     }
   ArrayResize(data, written - 1); // Exclude the terminating null byte.
   char response[];
   string response_headers;
   string headers = "Content-Type: application/json\r\n";
   headers += "Authorization: Bearer " + BridgeToken + "\r\n";
   ResetLastError();
   int status = WebRequest("POST", BridgeUrl, headers, 5000, data, response, response_headers);
   if(status != 202)
     {
      Print("QuantForge snapshot rejected. HTTP=", status, " error=", GetLastError());
     }
  }

string UtcTimestamp(datetime value)
  {
   return(TimeToString(value, TIME_DATE|TIME_SECONDS) + "Z");
  }

string TerminalClock(datetime value)
  {
   return(TimeToString(value, TIME_DATE|TIME_SECONDS));
  }

string SupportedFillingModesJson()
  {
   int modes=(int)SymbolInfoInteger(SymbolToReport,SYMBOL_FILLING_MODE);
   string result="[";
   if((modes & SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
     result+="\"fill_or_kill\"";
   if((modes & SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
     {
      if(StringLen(result)>1) result+=",";
      result+="\"immediate_or_cancel\"";
     }
   if((modes & SYMBOL_FILLING_BOC)==SYMBOL_FILLING_BOC)
     {
      if(StringLen(result)>1) result+=",";
      result+="\"book_or_cancel\"";
     }
   return(result+"]");
  }

string IntegerPropertyJson(const ENUM_SYMBOL_INFO_INTEGER property)
  {
   long value=0;
   if(!SymbolInfoInteger(SymbolToReport,property,value)) return("null");
   return(StringFormat("%I64d",value));
  }

string DoublePropertyJson(const ENUM_SYMBOL_INFO_DOUBLE property)
  {
   double value=0.0;
   if(!SymbolInfoDouble(SymbolToReport,property,value)) return("null");
   return(StringFormat("%.10f",value));
  }

string StringPropertyJson(const ENUM_SYMBOL_INFO_STRING property)
  {
   string value="";
   if(!SymbolInfoString(SymbolToReport,property,value)) return("null");
   return("\""+JsonEscape(value)+"\"");
  }

string CandleJson(const MqlRates &bar)
  {
   datetime utc_open = bar.time + (TimeGMT() - TimeCurrent());
   return(StringFormat("[{\"open_time_utc\":\"%s\",\"open\":%.8f,\"high\":%.8f,\"low\":%.8f,\"close\":%.8f,\"tick_volume\":%I64d}]", UtcTimestamp(utc_open), bar.open, bar.high, bar.low, bar.close, bar.tick_volume));
  }

string PositionsJson()
  {
   string result = "[";
   for(int i=0; i<PositionsTotal(); i++)
     {
      ulong ticket=PositionGetTicket(i); if(ticket==0) continue;
      if(StringLen(result)>1) result+=",";
      string side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? "buy" : "sell";
      datetime opened_utc=(datetime)PositionGetInteger(POSITION_TIME)+(TimeGMT()-TimeCurrent());
      result+=StringFormat("{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"side\":\"%s\",\"volume\":%.8f,\"price_open\":%.8f,\"price_current\":%.8f,\"sl\":%.8f,\"tp\":%.8f,\"profit\":%.8f,\"opened_at_utc\":\"%s\"}", ticket, JsonEscape(PositionGetString(POSITION_SYMBOL)), side, PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), PositionGetDouble(POSITION_PRICE_CURRENT), PositionGetDouble(POSITION_SL), PositionGetDouble(POSITION_TP), PositionGetDouble(POSITION_PROFIT), UtcTimestamp(opened_utc));
     }
   return(result+"]");
  }

string OrdersJson()
  {
   string result = "[";
   for(int i=0; i<OrdersTotal(); i++)
     {
      ulong ticket=OrderGetTicket(i); if(ticket==0) continue;
      if(StringLen(result)>1) result+=",";
      ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      result+=StringFormat("{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"side\":\"%s\",\"type\":\"%s\",\"volume\":%.8f,\"price\":%.8f,\"sl\":%.8f,\"tp\":%.8f}", ticket, JsonEscape(OrderGetString(ORDER_SYMBOL)), OrderSide(type), OrderTypeText(type), OrderGetDouble(ORDER_VOLUME_CURRENT), OrderGetDouble(ORDER_PRICE_OPEN), OrderGetDouble(ORDER_SL), OrderGetDouble(ORDER_TP));
     }
   return(result+"]");
  }

string OrderSide(const ENUM_ORDER_TYPE type)
  {
   if(type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_BUY_STOP_LIMIT)
      return("buy");
   return("sell");
  }

string OrderTypeText(const ENUM_ORDER_TYPE type)
  {
   if(type==ORDER_TYPE_BUY_LIMIT) return("buy_limit");
   if(type==ORDER_TYPE_SELL_LIMIT) return("sell_limit");
   if(type==ORDER_TYPE_BUY_STOP) return("buy_stop");
   if(type==ORDER_TYPE_SELL_STOP) return("sell_stop");
   if(type==ORDER_TYPE_BUY_STOP_LIMIT) return("buy_stop_limit");
   if(type==ORDER_TYPE_SELL_STOP_LIMIT) return("sell_stop_limit");
   return("unknown");
  }

string DealsJson()
  {
   datetime now=TimeCurrent(); if(!HistorySelect(now-60, now)) return("[]");
   string result="[";
   for(int i=0; i<HistoryDealsTotal(); i++)
     {
      ulong ticket=HistoryDealGetTicket(i); if(ticket==0) continue;
      if(StringLen(result)>1) result+=",";
      result+=StringFormat("{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"volume\":%.8f,\"price\":%.8f,\"profit\":%.8f}", ticket, JsonEscape(HistoryDealGetString(ticket, DEAL_SYMBOL)), HistoryDealGetDouble(ticket, DEAL_VOLUME), HistoryDealGetDouble(ticket, DEAL_PRICE), HistoryDealGetDouble(ticket, DEAL_PROFIT));
     }
   return(result+"]");
  }

string BoolJson(const bool value)
  {
   return(value ? "true" : "false");
  }

string JsonEscape(string value)
  {
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return(value);
  }
