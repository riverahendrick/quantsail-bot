# QuantSail Bot - Quick Reference & Action Checklist
## TL;DR: What to Do Right Now

**Version:** 1.0  
**Date:** February 5, 2026

---

## IMMEDIATE ACTIONS (Next 48 Hours)

### 1. SECURITY (CRITICAL - Do First!)
```bash
# On your local machine
cd quantsail-bot-main

# Remove all secrets from repo
rm env/*.env
git rm env/*.env
git commit -m "Remove secrets from repo"

# Create .gitignore if not exists
echo "env/*.env" >> .gitignore
echo "*.key" >> .gitignore
echo "*.pem" >> .gitignore
git add .gitignore
git commit -m "Add secret files to gitignore"
```

**Rotate ALL keys immediately:**
- [ ] Generate new Binance API keys (with IP whitelist + no withdrawal)
- [ ] Generate new Firebase service account
- [ ] Change all passwords in docker-compose.yml
- [ ] Store in `~/secrets/` with chmod 600

### 2. VPS Setup
```bash
# 1. Get Contabo VPS (or similar)
# Plan: VPS M (4 vCPU, 8GB RAM, ~$10/month)

# 2. SSH in and run:
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose ufw

# 3. Firewall
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp  # API (optional)
sudo ufw enable

# 4. Create user
sudo adduser quantsail
sudo usermod -aG sudo,docker quantsail
```

### 3. Deploy Infrastructure
```bash
# Upload your code to VPS, then:
cd quantsail-bot-main/infra/docker
docker-compose up -d

# Verify
docker ps
# Should see: postgres and redis running
```

---

## PROFIT TARGET REALITY CHECK

| Account | Daily Target | Difficulty | Monthly Net (After Costs) |
|---------|-------------|------------|---------------------------|
| **$1,000** | $2.00/day | ❌ Too Hard | ~$0 (costs eat profit) |
| **$2,000** | $2.00/day | ✅ Achievable | ~$24/month |
| **$5,000** | $2.00/day | ✅ Comfortable | ~$24/month |

**Reality:** Start with **$2K minimum** or you'll fight execution costs.

---

## COST PER TRADE (Binance with BNB)

```
Trade Size: $100
├── Fee: $0.15 (0.075% × 2 sides)
├── Spread: $0.02 (0.02%)
└── Slippage: $0.03 (0.03%)
───────────────────────
Total Cost: $0.20 (0.20%)

Need to make >$0.20 profit just to break even!
```

**Solution:** Only trade when expected profit > $0.25-0.30

---

## RECOMMENDED PAIRS (Ranked by Profitability)

1. **BNB/USDT** ⭐⭐⭐ (You said profitable)
2. **ADA/USDT** ⭐⭐⭐ (You said profitable)
3. **ETH/USDT** ⭐⭐ (Lower fees than BTC)
4. **SOL/USDT** ⭐⭐ (Good volatility)

**Avoid initially:** BTC/USDT (high costs relative to edge)

---

## CRITICAL CONFIG SETTINGS

```yaml
# config.yml (production settings for $2K account)

execution:
  mode: "dry-run"  # Start here!
  min_profit_usd: 0.15  # Dynamic: adjust per trade size

risk:
  max_risk_per_trade_pct: 0.5  # Risk 0.5% per trade
  max_position_pct_equity: 10  # Max 10% position size
  min_notional_usd: 50

portfolio:
  max_concurrent_positions: 3
  max_daily_trades: 10
  max_daily_loss_usd: 15  # HARD STOP at -$15

daily_lock:
  enabled: true
  daily_target_usd: 2.00
  mode: "STOP"  # Lock profits when hit
  daily_floor_usd: -15  # Emergency stop

breakers:
  consecutive_losses:
    max_losses: 3  # Pause after 3 losses
    pause_minutes: 120
```

---

## STRATEGY VALIDATION WORKFLOW

### Week 1-2: Get Data & Setup Backtest
```python
# 1. Fetch 24 months data
from quantsail_engine.research.data_fetcher import HistoricalDataFetcher

fetcher = HistoricalDataFetcher()
data = fetcher.fetch_ohlcv('BNB/USDT', '5m', since=datetime(2024,1,1))
fetcher.save_to_parquet({' BNB/USDT': data}, './data/historical')
```

### Week 3-5: Run Walk-Forward Analysis
```python
# 2. Test strategy
from quantsail_engine.research.walk_forward import WalkForwardAnalyzer
from quantsail_engine.strategies.trend_production import TrendStrategy

wfa = WalkForwardAnalyzer(train_days=90, test_days=30)
results = wfa.run_wfa(
    data=data,
    strategy_class=TrendStrategy,
    param_grid={'atr_period': [10, 14, 20], 'adx_period': [10, 14, 20]},
    cost_model=BinanceCostModel(use_bnb=True),
    initial_capital=2000
)

# Must pass:
# - Positive windows: >70%
# - Avg profit factor: >1.1
# - Total PnL: >$200 (for 24 month test period)
```

### Week 6-7: Run Monte Carlo
```python
# 3. Stress test
from quantsail_engine.research.monte_carlo import MonteCarloAnalyzer

mc = MonteCarloAnalyzer(trades=backtest_result['trades'], initial_capital=2000)
mc_results = mc.run_all_tests(iterations=1000)

# Must pass:
# - Trade shuffle: P95 max DD < 20%
# - Cost jitter (1.5x): >60% still profitable
```

### Week 8-10: Dry-Run on VPS
```bash
# 4. Deploy and watch
sudo systemctl start quantsail-engine
sudo journalctl -u quantsail-engine -f

# Run for 15 days, verify:
# - Simulated daily PnL: $1.50-2.50/day
# - No crashes
# - Decisions match backtest logic
```

### Week 11+: Go Live Small
- Start with $500 test capital
- Max $50 positions, 3 trades/day
- Daily loss limit: $5
- Scale slowly if profitable

---

## MONTHLY REVIEW QUESTIONS

**After each month, answer these:**

1. **Profitability:**
   - [ ] Did we hit daily target (avg $2/day)?
   - [ ] What was actual avg daily PnL?
   - [ ] Which pairs were profitable?
   - [ ] Which strategies worked best?

2. **Risk:**
   - [ ] Max drawdown within limits (<20%)?
   - [ ] Any daily loss limit hits?
   - [ ] Any circuit breaker triggers?
   - [ ] Position sizing appropriate?

3. **Execution:**
   - [ ] Actual fees vs estimated?
   - [ ] Slippage as expected?
   - [ ] Gate rejection rate reasonable?
   - [ ] Overtrading (too many trades)?

4. **Technical:**
   - [ ] Any crashes/downtime?
   - [ ] Engine performance OK?
   - [ ] API rate limits hit?
   - [ ] Data quality issues?

**If 2+ months consistently profitable → Scale up!**

---

## TELEGRAM ALERTS SETUP (5 Minutes)

```bash
# 1. Create Telegram bot
# - Message @BotFather on Telegram
# - Send: /newbot
# - Follow instructions
# - Save bot token

# 2. Get chat ID
# - Message your bot
# - Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
# - Find "chat":{"id": YOUR_CHAT_ID}

# 3. Add to secrets
echo "TELEGRAM_BOT_TOKEN=your_token_here" >> ~/secrets/engine.env
echo "TELEGRAM_CHAT_ID=your_chat_id_here" >> ~/secrets/engine.env
```

**Test:**
```python
from quantsail_engine.monitoring.telegram_alerts import TelegramAlerter

alerter = TelegramAlerter(bot_token='...', chat_id='...')
alerter.send_alert("Test alert!", 'INFO')
```

---

## COMMON MISTAKES TO AVOID

### ❌ Don't Do This:
1. **Skip backtesting** → "Just run it live and see"
2. **Ignore costs** → "0.10% fee is nothing"
3. **Overtrade** → "More trades = more profit"
4. **Start with $1K** → Costs will eat you alive
5. **Trade BTC first** → High fees, hard to profit small account
6. **No daily loss limit** → One bad day wipes out week of gains
7. **Ignore circuit breakers** → Let bot trade during exchange outage

### ✅ Do This Instead:
1. **Validate everything** with walk-forward + Monte Carlo
2. **Model costs realistically** and include in profitability gate
3. **Trade selectively** (5-10 quality trades/day max)
4. **Start $2K minimum** for crypto, $5K for forex
5. **Start with BNB/ADA** (your profitable pairs)
6. **Set HARD daily loss limit** ($15 for $2K account)
7. **Respect all safety controls** (they exist for a reason)

---

## FILES YOU NEED TO READ

**Priority 1 (Must Read):**
1. `QUANTSAIL_COMPLETE_IMPLEMENTATION_GUIDE.md` (this directory)
   - Full strategy, deployment, and profitability plan
   
2. `TECHNICAL_IMPLEMENTATION_CODE.md` (this directory)
   - Copy-paste ready code examples

**Priority 2 (Reference):**
3. Your existing `docs/01_PRD.md`
   - Product requirements
   
4. Your existing `docs/13_ENGINE_SPEC.md`
   - Engine behavior spec

5. Your existing `docs/09_CONFIG_SPEC.md`
   - Config parameters

---

## KEY FORMULAS (Keep These Handy)

### Profitability Gate
```
net_profit = gross_profit - fees - slippage - spread
trade_only_if: net_profit >= min_profit_usd
```

### Position Size
```
risk_amount = equity × 0.5%  (0.5% risk per trade)
price_risk = |entry - stop| / entry
quantity = risk_amount / (price_risk × entry)
quantity = min(quantity, equity × 10% / entry)  (max 10% position)
```

### Break-Even Win Rate (Given Costs)
```
avg_win = $0.50
avg_loss = $0.30
cost_per_trade = $0.20

break_even: (WR × 0.50) + ((1-WR) × -0.30) - 0.20 = 0
solve: WR ≈ 62.5%

Need >62.5% win rate just to break even!
```

---

## EMERGENCY CONTACTS

**If things go wrong:**

1. **Kill Switch:** Dashboard → 🚨 EMERGENCY STOP
   - Closes all positions immediately

2. **Manual Intervention:**
   ```bash
   # Stop engine
   sudo systemctl stop quantsail-engine
   
   # Check positions on Binance web/app
   # Close manually if needed
   ```

3. **Check Logs:**
   ```bash
   sudo journalctl -u quantsail-engine --since "1 hour ago"
   ```

4. **Database Backup:**
   ```bash
   /home/quantsail/scripts/backup_db.sh
   ```

---

## SUCCESS CRITERIA (6 Month Targets)

**If after 6 months you have:**
- ✅ **Average $1.50-2.00/day** (allow for losing days)
- ✅ **Max drawdown < 20%**
- ✅ **No catastrophic losses** (no single day > $50 loss)
- ✅ **Uptime > 99%** (minimal crashes)
- ✅ **Positive 4+ months** out of 6

**Then you have a working, profitable system! 🎉**

**Next:** Scale capital, add more pairs, explore forex

---

## SUPPORT & RESOURCES

**Documentation:**
- [Binance API](https://developers.binance.com/docs/binance-spot-api-docs)
- [CCXT](https://docs.ccxt.com/)
- [TA-Lib](https://www.ta-lib.org/function.html)

**Communities:**
- r/algotrading
- Freqtrade Discord
- QuantConnect Forum

**This Guide:**
- All files in `/mnt/user-data/outputs/`
- 2 complete markdown files + code examples

---

## FINAL WORDS

### The Hard Truth
- 90% of retail traders lose money
- 99% of trading bots fail within 6 months
- Most fail because: overfit backtests, ignored costs, no discipline

### Your Advantages
- ✅ Cost-aware architecture from day 1
- ✅ Strong safety controls (gates, breakers, locks)
- ✅ This comprehensive, research-backed implementation plan
- ✅ Realistic expectations ($2/day, not $200/day)

### The Plan Works IF:
1. You **actually backtest** (don't skip this!)
2. You **start with dry-run** (test for weeks before live)
3. You **follow risk limits** (don't override gates/breakers)
4. You **start small** ($500-2K) and scale slowly
5. You **review monthly** and adjust based on data

### If You Get Stuck
1. Check logs (`journalctl -u quantsail-engine`)
2. Review the implementation guides
3. Re-run backtests (market conditions change)
4. Reduce risk (smaller positions, fewer trades)
5. Reach out to algo trading communities

---

**Good luck! You have everything you need. Now execute the plan. 🚀**

---

## APPENDIX: 12-Week Timeline (One-Page View)

| Week | Phase | Key Tasks | Deliverable |
|------|-------|-----------|-------------|
| 1 | Security & Infra | Rotate keys, setup VPS, deploy DB/Redis | Secure VPS running |
| 2 | Data & Pipeline | Fetch 24mo data, build backtest framework | Data + backtest ready |
| 3 | Strategy Dev | Implement 3 strategies, backtest each | 3 coded strategies |
| 4-5 | Validation | Walk-forward analysis on 2 pairs | WFA results |
| 6 | Monte Carlo | Stress test, Go/No-Go decision | MC pass/fail |
| 7 | Ensemble | Test multi-strategy ensemble | Ensemble validated |
| 8 | Dry-Run Deploy | Run on VPS, dry-run mode, 7 days | No crashes |
| 9-10 | Paper Trade | Continue dry-run, 15 days total | Consistent sim PnL |
| 11 | First Live | $500 capital, BNB only, 3 trades/day | First real profits |
| 12 | Scale | Increase to $1-2K, add ADA | Stable live trading |

**After Week 12:** Continue live, review monthly, scale gradually

---

**Document End**  
**Version:** 1.0  
**Last Updated:** February 5, 2026  
**Status:** Ready for Production**
