//+------------------------------------------------------------------+
//| QuantForge Autonomous MT5 Trade Execution Bridge                |
//| Autonomous CTrade Order Execution for #BTCUSD & XAUUSD           |
//| v1.06 Ultra-Stable Wine Engine for macOS & VPS                  |
//+------------------------------------------------------------------+
#property copyright "QuantForge Systems"
#property link      "https://github.com/quantforge"
#property version   "1.06"
#property strict

#include <Trade/Trade.mqh>

//--- Input Parameters
input string BridgeUrl         = "http://127.0.0.1:8765";                  // QuantForge Bridge Base URL
input string BridgeToken       = "quantforge-live-token-2026";             // Bearer Auth Token
input string SymbolToReport    = "";                                       // Symbol (Empty = Auto-detect chart symbol)
input ulong  MagicNumber       = 7007;                                     // Magic Number for Bot Trades
input double MaxLotSize        = 0.05;                                     // Hard Cap Max Lot Size (Safe Micro-Lot)
input int    HeartbeatSeconds  = 2;                                        // Heartbeat interval (2s for Wine socket safety)
input bool   EnableAutoTrading = true;                                     // Allow EA to execute broker orders

//--- Internal State
CTrade   m_trade;
string   g_symbol;
bool     g_is_busy = false;
int      g_consecutive_errors = 0;
int      g_snapshots_sent = 0;
int      g_orders_executed = 0;
datetime g_last_comment_update = 0;

//+------------------------------------------------------------------+
//| Helper Utilities                                                 |
//+------------------------------------------------------------------+
string JsonEscape(string value)
  {
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return(value);
  }

string BoolJson(bool value)
  {
   return(value ? "true" : "false");
  }

string DoublePropertyJson(ENUM_SYMBOL_INFO_DOUBLE property_id)
  {
   ResetLastError();
   double value = SymbolInfoDouble(g_symbol, property_id);
   if(GetLastError() != 0) return("null");
   return(DoubleToString(value, 8));
  }

string IntegerPropertyJson(ENUM_SYMBOL_INFO_INTEGER property_id)
  {
   ResetLastError();
   long value = SymbolInfoInteger(g_symbol, property_id);
   if(GetLastError() != 0) return("null");
   return(IntegerToString(value));
  }

string StringPropertyJson(ENUM_SYMBOL_INFO_STRING property_id)
  {
   ResetLastError();
   string value = SymbolInfoString(g_symbol, property_id);
   if(GetLastError() != 0 || value == "") return("null");
   return("\"" + JsonEscape(value) + "\"");
  }

string UtcTimestamp(datetime value)
  {
   MqlDateTime dt;
   TimeToStruct(value, dt);
   return(StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ", dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec));
  }

string TerminalClock(datetime value)
  {
   MqlDateTime dt;
   TimeToStruct(value, dt);
   return(StringFormat("%04d.%02d.%02d %02d:%02d:%02d", dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec));
  }

string SupportedFillingModesJson()
  {
   uint flags = (uint)SymbolInfoInteger(g_symbol, SYMBOL_FILLING_MODE);
   string items[];
   if((flags & SYMBOL_FILLING_FOK) != 0)
     {
      ArrayResize(items, ArraySize(items) + 1);
      items[ArraySize(items) - 1] = "\"fok\"";
     }
   if((flags & SYMBOL_FILLING_IOC) != 0)
     {
      ArrayResize(items, ArraySize(items) + 1);
      items[ArraySize(items) - 1] = "\"ioc\"";
     }
   if((flags & SYMBOL_FILLING_BOC) != 0)
     {
      ArrayResize(items, ArraySize(items) + 1);
      items[ArraySize(items) - 1] = "\"boc\"";
     }
   if(ArraySize(items) == 0) return("[]");
   string joined = items[0];
   for(int i = 1; i < ArraySize(items); i++) joined += "," + items[i];
   return("[" + joined + "]");
  }

string CandleJson(const MqlRates &rate)
  {
   return(StringFormat(
      "{\"open_time_utc\":\"%s\",\"open\":%.4f,\"high\":%.4f,\"low\":%.4f,\"close\":%.4f,\"tick_volume\":%I64d}",
      UtcTimestamp(rate.time), rate.open, rate.high, rate.low, rate.close, rate.tick_volume
   ));
  }

string PositionsJson()
  {
   string json = "[";
   int count = PositionsTotal();
   int added = 0;

   for(int i = 0; i < count; i++)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_symbol) continue;

      if(added > 0) json += ",";
      string p_type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "buy" : "sell";
      json += StringFormat(
         "{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.4f,\"open_price\":%.4f,\"current_price\":%.4f,\"stop_loss\":%.4f,\"take_profit\":%.4f,\"profit\":%.4f,\"magic\":%I64d}",
         ticket, g_symbol, p_type,
         PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), PositionGetDouble(POSITION_PRICE_CURRENT),
         PositionGetDouble(POSITION_SL), PositionGetDouble(POSITION_TP), PositionGetDouble(POSITION_PROFIT), PositionGetInteger(POSITION_MAGIC)
      );
      added++;
     }
   json += "]";
   return(json);
  }

string OrdersJson()
  {
   string json = "[";
   int count = OrdersTotal();
   int added = 0;

   for(int i = 0; i < count; i++)
     {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != g_symbol) continue;

      if(added > 0) json += ",";
      string o_type = (OrderGetInteger(ORDER_TYPE) == ORDER_TYPE_BUY_LIMIT || OrderGetInteger(ORDER_TYPE) == ORDER_TYPE_BUY_STOP) ? "buy" : "sell";
      json += StringFormat(
         "{\"ticket\":\"%I64d\",\"symbol\":\"%s\",\"type\":\"%s\",\"volume_initial\":%.4f,\"volume_current\":%.4f,\"price_open\":%.4f,\"stop_loss\":%.4f,\"take_profit\":%.4f,\"magic\":%I64d}",
         ticket, g_symbol, o_type,
         OrderGetDouble(ORDER_VOLUME_INITIAL), OrderGetDouble(ORDER_VOLUME_CURRENT), OrderGetDouble(ORDER_PRICE_OPEN),
         OrderGetDouble(ORDER_SL), OrderGetDouble(ORDER_TP), OrderGetInteger(ORDER_MAGIC)
      );
      added++;
     }
   json += "]";
   return(json);
  }

string DealsJson()
  {
   return("[]");
  }

void UpdateChartComment(string status_text, bool force = false)
  {
   datetime now = TimeCurrent();
   if(!force && (now - g_last_comment_update < 4)) return; // Throttle to every 4s to prevent Wine GDI redraw leaks
   g_last_comment_update = now;

   Comment(StringFormat(
      "==========================================\n"
      "🤖 QuantForge Autonomous MT5 Bridge v1.06\n"
      "==========================================\n"
      "Symbol       : %s\n"
      "Bridge URL   : %s\n"
      "Auto-Trading : %s (Magic: %d)\n"
      "Snapshots    : %d | Executions: %d\n"
      "------------------------------------------\n"
      "%s\n"
      "==========================================",
      g_symbol, BridgeUrl,
      EnableAutoTrading ? "🟢 ENABLED" : "🟡 READ-ONLY",
      MagicNumber, g_snapshots_sent, g_orders_executed, status_text
   ));
  }

//+------------------------------------------------------------------+
//| Order Execution Handler                                          |
//+------------------------------------------------------------------+
void ProcessExecutionPayload(string json_str)
  {
   if(!EnableAutoTrading) return;

   int orders_idx = StringFind(json_str, "\"orders\":[");
   if(orders_idx < 0) return;

   int close_idx = StringFind(json_str, "]", orders_idx);
   if(close_idx <= orders_idx + 10) return;

   string orders_block = StringSubstr(json_str, orders_idx + 9, close_idx - orders_idx - 9);

   int search_pos = 0;
   while(true)
     {
      int item_start = StringFind(orders_block, "{", search_pos);
      if(item_start < 0) break;
      int item_end = StringFind(orders_block, "}", item_start);
      if(item_end < 0) break;

      string order_json = StringSubstr(orders_block, item_start, item_end - item_start + 1);
      ExecuteSingleOrder(order_json);
      search_pos = item_end + 1;
     }
  }

void ExecuteSingleOrder(string order_json)
  {
   string order_id = ExtractJsonString(order_json, "order_id");
   string side = ExtractJsonString(order_json, "side");
   double volume = ExtractJsonDouble(order_json, "volume");
   double sl = ExtractJsonDouble(order_json, "stop_loss");
   double tp = ExtractJsonDouble(order_json, "take_profit");

   if(volume <= 0 || volume > MaxLotSize)
     {
      Print(StringFormat("⚠️ Rejected order volume %.4f (Max allowed: %.2f)", volume, MaxLotSize));
      return;
     }

   if(side == "buy" || side == "BUY")
     {
      Print(StringFormat("🚀 [Auto-Execution] Firing BUY %.2f lots on %s (SL: %.2f, TP: %.2f, Magic: %d)", volume, g_symbol, sl, tp, MagicNumber));
      if(m_trade.Buy(volume, g_symbol, 0, sl, tp, "QuantForge Auto-Buy"))
        {
         g_orders_executed++;
         Print(StringFormat("✅ BUY ORDER FILLED SUCCESSFULLY! Deal Ticket: %I64d", m_trade.ResultDeal()));
        }
      else
        {
         Print(StringFormat("❌ BUY Execution Failed. Error: %d (%s)", m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription()));
        }
     }
   else if(side == "sell" || side == "SELL")
     {
      Print(StringFormat("🚀 [Auto-Execution] Firing SELL %.2f lots on %s (SL: %.2f, TP: %.2f, Magic: %d)", volume, g_symbol, sl, tp, MagicNumber));
      if(m_trade.Sell(volume, g_symbol, 0, sl, tp, "QuantForge Auto-Sell"))
        {
         g_orders_executed++;
         Print(StringFormat("✅ SELL ORDER FILLED SUCCESSFULLY! Deal Ticket: %I64d", m_trade.ResultDeal()));
        }
      else
        {
         Print(StringFormat("❌ SELL Execution Failed. Error: %d (%s)", m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription()));
        }
     }
  }

string ExtractJsonString(string json, string key)
  {
   string target = "\"" + key + "\":\"";
   int start = StringFind(json, target);
   if(start < 0) return("");
   start += StringLen(target);
   int end = StringFind(json, "\"", start);
   if(end < 0) return("");
   return(StringSubstr(json, start, end - start));
  }

double ExtractJsonDouble(string json, string key)
  {
   string target = "\"" + key + "\":";
   int start = StringFind(json, target);
   if(start < 0) return(0.0);
   start += StringLen(target);
   int end = StringFind(json, ",", start);
   if(end < 0) end = StringFind(json, "}", start);
   if(end < 0) return(0.0);
   string val_str = StringSubstr(json, start, end - start);
   StringReplace(val_str, "\"", "");
   return(StringToDouble(val_str));
  }

//+------------------------------------------------------------------+
//| Core Snapshot Sender                                             |
//+------------------------------------------------------------------+
void SendSnapshot()
  {
   if(g_is_busy) return;
   g_is_busy = true;

   MqlTick tick;
   if(!SymbolInfoTick(g_symbol, tick) || tick.bid <= 0 || tick.ask <= 0)
     {
      g_is_busy = false;
      UpdateChartComment("⚠️ Waiting for live ticks on " + g_symbol + "...");
      return;
     }

   MqlRates minute_bars[];
   ResetLastError();
   int copied = CopyRates(g_symbol, PERIOD_M1, 0, 2, minute_bars);
   bool has_completed_m1 = (copied >= 2);
   string missing = has_completed_m1 ? "[]" : "[\"completed_m1\"]";
   string candle = has_completed_m1 ? ("[" + CandleJson(minute_bars[0]) + "]") : "[]";

   string timestamp = UtcTimestamp(TimeGMT());

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

   string body = "{";
   body += StringFormat(
      "\"schema_version\":2,\"observed_at_utc\":\"%s\",\"source\":{\"adapter\":\"mt5_execution_bridge\",\"broker_profile_id\":\"mt5_live_exec\"},",
      timestamp
   );
   body += StringFormat(
      "\"time_provenance\":{\"terminal_server_time\":\"%s\",\"terminal_local_time\":\"%s\",\"terminal_utc_time\":\"%s\"},",
      TerminalClock(TimeCurrent()), TerminalClock(TimeLocal()), timestamp
   );
   body += StringFormat(
      "\"account\":{\"account_id\":\"%I64d\",\"server\":\"%s\",\"currency\":\"%s\",\"balance\":%.4f,\"equity\":%.4f,\"margin\":%.4f,\"free_margin\":%.4f},",
      AccountInfoInteger(ACCOUNT_LOGIN), JsonEscape(AccountInfoString(ACCOUNT_SERVER)), JsonEscape(AccountInfoString(ACCOUNT_CURRENCY)),
      AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoDouble(ACCOUNT_MARGIN), AccountInfoDouble(ACCOUNT_MARGIN_FREE)
   );
   body += StringFormat(
      "\"instrument\":{\"canonical_instrument\":\"%s\",\"broker_symbol\":\"%s\",\"specification\":{\"point\":%.8f,\"digits\":%d,\"volume_min\":%.4f,\"volume_max\":%.4f,\"volume_step\":%.4f,\"contract_size\":%.4f,",
      JsonEscape(g_symbol), JsonEscape(g_symbol), point, digits,
      SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN), SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX), SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP), contract_size
   );
   body += StringFormat(
      "\"supported_filling_modes\":%s,\"trade_mode\":%s,\"order_mode\":%s,\"stop_level\":%s,\"freeze_level\":%s,\"trade_calculation_mode\":%s,\"profit_currency\":%s,\"margin_currency\":%s,\"tick_size\":%s,\"tick_value\":%s,\"tick_value_loss\":%s,\"tick_value_profit\":%s}},",
      filling_modes, trade_mode, order_mode, stop_level, freeze_level, calculation_mode, profit_currency, margin_currency, tick_size, tick_value, tick_value_loss, tick_value_profit
   );
   body += StringFormat(
      "\"quote\":{\"bid\":%.4f,\"ask\":%.4f,\"tick_time_utc\":\"%s\",\"spread_points\":%.2f},",
      tick.bid, tick.ask, timestamp, (tick.ask - tick.bid) / point
   );
   body += "\"candles\":{\"timeframe\":\"M1\",\"forming\":null,\"completed\":" + candle + "},";
   body += "\"positions\":" + PositionsJson() + ",\"active_orders\":" + OrdersJson() + ",";
   body += StringFormat("\"deals\":{\"history_from_utc\":\"%s\",\"history_to_utc\":\"%s\",\"items\":%s},", timestamp, timestamp, DealsJson());
   body += StringFormat(
      "\"terminal\":{\"connected\":%s,\"trade_allowed\":%s},\"data_quality\":{\"adapter_status\":\"ok\",\"missing_data\":%s}}",
      BoolJson((bool)TerminalInfoInteger(TERMINAL_CONNECTED)), BoolJson((bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)), missing
   );

   string snapshot_url = BridgeUrl + "/v1/mt5/snapshots";
   char data[];
   int written = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(written <= 1) { g_is_busy = false; return; }
   ArrayResize(data, written - 1);

   char response[];
   string response_headers;
   string headers = "Content-Type: application/json\r\nAuthorization: Bearer " + BridgeToken + "\r\n";

   ResetLastError();
   int status = WebRequest("POST", snapshot_url, headers, 2000, data, response, response_headers);
   g_is_busy = false;

   if(status == 202)
     {
      g_snapshots_sent++;
      g_consecutive_errors = 0;
      string resp_json = CharArrayToString(response, 0, WHOLE_ARRAY, CP_UTF8);
      ProcessExecutionPayload(resp_json);

      UpdateChartComment(StringFormat(
         "🟢 [Auto-Trading Bridge ACTIVE & Live]\n"
         "Symbol: %s | Bid: %.2f | Ask: %.2f\n"
         "Snapshots Sent: %d | Status: 202 Accepted\n"
         "Server: %s | Account: %I64d",
         g_symbol, tick.bid, tick.ask, g_snapshots_sent, AccountInfoString(ACCOUNT_SERVER), AccountInfoInteger(ACCOUNT_LOGIN)
      ));
     }
   else
     {
      g_consecutive_errors++;
      if(g_consecutive_errors >= 2)
        UpdateChartComment(StringFormat("⚠️ Bridge connection retry (Status: %d)...", status));
     }
  }

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   g_symbol = (SymbolToReport == "") ? _Symbol : SymbolToReport;
   m_trade.SetExpertMagicNumber(MagicNumber);

   if(!SymbolSelect(g_symbol, true))
     {
      Print("❌ Cannot select symbol: ", g_symbol);
      return(INIT_FAILED);
     }

   EventSetTimer(HeartbeatSeconds);
   SendSnapshot();
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
  }

void OnTimer()
  {
   SendSnapshot();
  }

void OnTick()
  {
  }
