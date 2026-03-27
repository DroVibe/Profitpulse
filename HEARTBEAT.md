# HEARTBEAT.md

## Timing Rules
- Night mode: 22:00-07:00 EST = HEARTBEAT_OK only
- Interval: ~30 min (standard heartbeat)

## Daily Recurring Tasks (Required - Execute Without Prompt)
- **7am EST**: Daily Recap (newsletter style, 400-600 words) — AI/agent/Web3/alpha
  - **PRIMARY SOURCE**: Dr. Alex Wissner-Gross Substack (theinnermostloop.substack.com) — check latest 48h posts
  - SECONDARY: X favorites (@0xsammy, @alexwg, @NoLimitGains) for threads
  - Find best thread (not just latest tweet) — depth > volume
  - Synthesize: quote key lines + explain why it matters to agents/OpenClaw/AI/crypto
  - **SKIP recycled news** — verify dates, avoid repeating yesterday's alpha
  - **Business Plan Update**: Include progress on Stripe/Resend setup, domain, and launch milestones
- ~~8am EST: OpenClaw + crypto x AI recaps~~ (DEPRECATED - disabled Mar 10, 2026)
- **9am EST**: Yield Check → invoke "check yields" (yield-compounder skill)
- **10am EST**: Brainstorming slot → generate ideas, surface opportunities, update ideas.md
- **8pm EST**: Progress review (how today advanced biz goals)
- **9pm EST**: End-of-day summarization → extract key wins to MEMORY.md

## Heartbeat (~30 min)
- Run context-optimizer skill → "check capacity" → warn at 80%
- Check for subagent reports → relay new findings via DM
- Track @FelixCraftAI (felixcraft.ai) for agent economics updates

# DEPLOYED PROJECTS
- ScaleStack Landing: ~/.openclaw/workspace/scalestack-landing/index.html
- TaxShield: integrated into ProfitPulse (not a separate app).
- ProfitPulse: https://drovibe-profitpulse-streamlit-app-0-0.streamlit.app/

Subagent automation (reports flow to me, I relay to you):
- Yield-Compounder: Weekly APY check (Sundays)
- NFT-Arb-Scout: On-demand market research (no scheduled runs)
- Context-Optimizer: Per-heartbeat capacity check

HEARTBEAT: On each check, read ~/.openclaw/automation/reports.txt and relay any new subagent findings to user via DM.

### Every Heartbeat (~30 min):
- Run context-optimizer skill → "check capacity" → warn at 80%

### Active Trade Monitoring (Lightweight - No AI)
# Only uses curl/API calls, NOT inference tokens
- Fetch current prices (curl) → ~0 tokens
- Calculate PnL (math) → ~0 tokens
- ALERT via AI only if:
  - Position within 20% of stop loss
  - Price move >5% in either direction
  - Explicit manual check requested
- Otherwise: HEARTBEAT_OK (no AI)

### Token Budget Guard
- Max 10% daily tokens for monitoring alerts
- Reserve 90% for execution + your queries

END-OF-DAY (9pm EST):
- Scan conversation history for key accomplishments (deployments, fixes, wins)
- Append formatted entries to MEMORY.md under "## Recent Wins"
- Format: "- [date] [accomplishment, e.g. Deployed ProfitPulse to Streamlit Cloud]"
- Force memory_search recall on project-related questions (ProfitPulse, DX vaults, etc.)

AUTONOMY LEVEL:
- Sliders: I adjust without asking (tradingActivity, slippageBps, assetRiskPreference, tradeSize, holdingStyle, diversification)
- Funds: Deposits/withdrawals require user approval
- Settings changes: Propose via DM, execute on /approve

Post-trade: Invoke TraderQuant for win/loss analysis

## Coding Delegation - Coder Subagent
- **Rule**: All coding tasks → automatically route to `coder` subagent
- **Tool**: `openclaw agent --agent coder --message "..."`
- **Coder uses**: Opencode with Minimax2.5 free model (Plan→Build)
- **My job**: Strategy/thinking only, never code implementation
- **Efficiency**: Saves inference costs, keeps coding in free model

## Kid Projects Hardening (run daily or after any kid interaction)
- Check recent messages/DMs with the 13 & 14 year olds.
- Summarize any coding/app/project progress (project name, code added, goals, blockers, next steps).
- Append bullets to MEMORY.md under "## Kid Projects (13 & 14)".
- If no kid activity today → skip silently.
- Alert me if a project is stuck >3 days.
---

## Business Plan TO DO (Active)

### Phase 1: Payment + Email (Week 1)
- ✅ Dro: Buy domain (scalestack.io)
- ✅ Pro: Landing page built
- ✅ Stripe: Starter ($19/mo) + Complete ($29/mo) Payment Links wired
- ✅ Vercel: Both pricing tiles fully clickable to Stripe
- ✅ Visual polish: pricing tiles, white text, hover effects
- ⬜ Stripe: Connect payment webhooks (notify on successful payment)
- ⬜ Resend: Wire welcome/confirmation email on subscription
- ⬜ Point DNS to Vercel (scalestack.io → Vercel deploy)

### Phase 2: Launch (Week 2)
- ⬜ Test full checkout flow (user completes a real payment)
- ⬜ Build + test Stripe webhook → unlock access flow
- ⬜ Build Resend email sequence (welcome + receipt)
- ⬜ Launch ScaleStack publicly
- ⬜ First paid subscriber goal: 5

### Current Blockers
1. **DNS** — scalestack.io not pointing to Vercel yet
2. **Stripe webhook** — no server to receive payment events
3. **Email sequence** — Resend keys exist but not wired to purchase flow

