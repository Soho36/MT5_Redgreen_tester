//=====================================================
// ACCOUNT STARTER CONFIG
//=====================================================

#define MAX_ACCOUNTS            20

input double START_CAPITAL             = 1500;
input double TRAILING_DD               = 1500;
input double DD_FREEZE_EXTRA           = 100;   // same as Python +100
input double START_IF_DD_THRESHOLD     = 500;   // positive like Python
input double START_IF_PROFIT_THRESHOLD = 1500;
input int    MIN_DAYS_BETWEEN_STARTS   = 5;
input double RECOVERY_LEVEL            = 0;

struct VirtualAccount
{
   double equity;
   double rolling_max;
   double drawdown;
   bool   alive;
   datetime start_time;
};

VirtualAccount accounts[MAX_ACCOUNTS];
int acc_count = 0;

// Internal control
datetime last_start_time = 0;
bool waiting_for_recovery = false;

double ComputeDDFloor(VirtualAccount &acc)
{
   double freeze_trigger = START_CAPITAL + TRAILING_DD + DD_FREEZE_EXTRA;

   if (acc.rolling_max < freeze_trigger)
   {
      return acc.rolling_max - TRAILING_DD;   // trailing mode
   }
   else
   {
      return START_CAPITAL + DD_FREEZE_EXTRA; // frozen mode
   }
}


void StartNewAccount(datetime t)
{
   if (acc_count >= MAX_ACCOUNTS)
      return;

   accounts[acc_count].equity      = START_CAPITAL;
   accounts[acc_count].rolling_max = START_CAPITAL;
   accounts[acc_count].drawdown    = 0;
   accounts[acc_count].alive       = true;
   accounts[acc_count].start_time  = t;

   acc_count++;
   last_start_time = t;
   waiting_for_recovery = true;

   Print("🚀 New virtual account started at ", TimeToString(t));
}

void AccountStarter_OnTradeClosed(double profit, datetime t)
{
   if (acc_count == 0)
      StartNewAccount(t);   // initialize first

   // Update every alive account
   for(int i=0; i<acc_count; i++)
   {
      VirtualAccount &acc = accounts[i];
      if (!acc.alive) continue;

      acc.equity += profit;
      if (acc.equity > acc.rolling_max) 
         acc.rolling_max = acc.equity;

      acc.drawdown = acc.equity - acc.rolling_max;

      double dd_floor = ComputeDDFloor(acc);

      if (acc.equity <= dd_floor || acc.equity <= 0)
      {
         acc.alive = false;
         Print("💥 Virtual account #", i+1, " blown at ", TimeToString(t));
      }
   }

   // Now evaluate starting new account
   TryStartNewAccount(t);
}


void TryStartNewAccount(datetime t)
{
   if (acc_count >= MAX_ACCOUNTS)
      return;

   // Convert time to days difference
   if (last_start_time != 0)
   {
      int days = (int)((t - last_start_time) / 86400);
      if (days < MIN_DAYS_BETWEEN_STARTS)
         return;
   }

   // Collect DD from alive accounts
   double current_dd = 0;
   bool has_alive = false;

   for(int i=0; i<acc_count; i++)
   {
      VirtualAccount &acc = accounts[i];
      if (!acc.alive) continue;
      has_alive = true;

      if (acc.drawdown < current_dd)
         current_dd = acc.drawdown;
   }

   // ----- RECOVERY RULE -----
   if (waiting_for_recovery)
   {
      if (current_dd >= RECOVERY_LEVEL)
         waiting_for_recovery = false;
      else
         return;
   }

   // ----------------------------------
   // START TRIGGER LOGIC (same as Python)
   // ----------------------------------

   bool trigger_dd = false;
   bool trigger_profit = false;

   // DD trigger
   if (START_IF_DD_THRESHOLD > 0)
   {
      if (current_dd <= -START_IF_DD_THRESHOLD)
         trigger_dd = true;
   }

   // Profit trigger
   if (START_IF_PROFIT_THRESHOLD > 0)
   {
      if (has_alive)
      {
         // last alive account
         for(int i=acc_count-1; i>=0; i--)
         {
            if (accounts[i].alive)
            {
               double profit_since_start = accounts[i].equity - START_CAPITAL;
               if (profit_since_start >= START_IF_PROFIT_THRESHOLD)
                  trigger_profit = true;
               break;
            }
         }
      }
      else
      {
         // if all accounts are blown, allow immediate start
         trigger_profit = true;
      }
   }

   // Combined
   if (trigger_dd || trigger_profit)
      StartNewAccount(t);
}


void OnTradeTransaction(const MqlTradeTransaction &tx,
                        const MqlTradeRequest &req,
                        const MqlTradeResult &res)
{
   if (tx.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      // only closed trades
      if (tx.deal_type == DEAL_TYPE_BUY || tx.deal_type == DEAL_TYPE_SELL)
      {
         HistorySelect(tx.time, tx.time);
         double profit = HistoryDealGetDouble(tx.deal, DEAL_PROFIT);
         AccountStarter_OnTradeClosed(profit, tx.time);
      }
   }
}
