# MEMORY

## Current Focus
- ScaleStack is the brand and main business focus.
- ProfitPulse is the core product.
- TaxShield is an integrated ProfitPulse module, not a separate product.
- ScaleStack On-Premises is a separate white-glove service line.

## Active Projects
- `scalestack-landing/`: landing page deployed via Vercel/GitHub workflow.
- `Profitpulse/profitpulse.py`: main app, live on Streamlit Cloud.
- `fl-tax-shield/`: **DEPRECATED** — TaxShield is fully integrated into ProfitPulse, not a separate app. The FL Tax Shield codebase can be archived.
- `scalestack-context/phase-0-summary.md`: source of truth for completed Phase 0 decisions.
- `expense-tracker/` (separate GitHub repo: DroVibe/expense-tracker): co-parent expense tracker, live at familyexpensetracker.streamlit.app. Supabase-backed, two-page layout. See `memory/expense-tracker.md` for full details.

## Product Decisions To Preserve
- Keep the product story centered on one dashboard, one login, one operating view.
- Plan structure is Starter vs Complete.
- Permit tracking is out of near-term scope.
- White-glove pricing is separate from SaaS pricing.
- Tax features must remain informational/planning-oriented, not legal or filing services.

## Business Status
- Landing page: live at scalestack-landing.vercel.app. Dark mode, On-Premises section, fully clickable pricing tiles.
- Stripe: Starter ($19/mo) and Complete ($29/mo) Payment Links wired and working.
- ProfitPulse: live at profitpulse1.streamlit.app. Auth flow fixed (init_state guard, signup rerun, authenticated gate in main). Demo login (admin/pilot2026) works. Onboarding wizard loads demo data correctly.
- TaxShield: integrated into ProfitPulse (not a separate app).
- DNS (scalestack.io → Vercel): pending
- Stripe webhook: pending (needs Vercel serverless function)
- Resend email sequences: pending

## Workflow Notes
- OpenCode/OpenClaw edits locally in WSL, pushes to GitHub, and Vercel auto-deploys.
- Prometheus should maintain context across ScaleStack, ProfitPulse, TaxShield, landing page, deployment, and launch work.
- For coding tasks, prefer `coder`, but if it stalls or produces no files, recover quickly instead of waiting silently.
- **Expense Tracker** is a SEPARATE project from ScaleStack/ProfitPulse. Do not mix context. See `memory/expense-tracker.md` for project details.

## User Context Worth Keeping
- Telegram bot is `@Prometheusclawbot`.
- User is actively building ScaleStack and related products and wants continuity across sessions.
- User asked for a co-parent expense tracker app backed by Google Sheets; current sheet URL was provided in chat and the idea is still active.

## Recent Wins
- [2026-03-26] Expense tracker settlement proof feature built and deployed (`224dd21`): settling parent must upload a payment screenshot (Venmo/PayPal/Zelle/bank) before an expense can be marked settled. New columns: `settlement_proof_url`, `settled_by`, `settled_at`, `settlement_note`. Migration in `migrations/001_add_settlement_proof.sql`. Also: Python 3.8 walrus operator bug fixed (`cc4f3aa`) — Streamlit Cloud uses Python 3.8, walrus operators in f-strings error there.
- [2026-03-26] Expense tracker: (1) Fixed split calculation bug, (2) deduplicated all shared logic into shared.py, (3) added search/filter + CSV export + delete confirmation dialogs. Committed as `92af93e`. Also built 30-case unit test suite for balance math — all passing — committed as `463a921`. Both pushed to DroVibe/expense-tracker.
- [2026-03-25] Stripe Payment Links wired (Starter $19 + Complete $29/mo), both pricing tiles fully clickable, font colors fixed to white, Streamlit URL corrected to profitpulse1.streamlit.app. Landing page conversion path fully functional.
- [2026-03-25] ProfitPulse auth fully fixed — 12 commits today across 4 sub-issues: (1) init_state() guard, (2) signup st.rerun, (3) authenticated gate in main(), (4) users.py returns DataFrames not lists, (5) removed non-existent 'id' column refs, (6) removed all profiles/users table deps, (7) switched login to email (Supabase Auth standard). Login now uses email+password directly, no service role key needed.
- [2026-03-24] Built co-parent expense tracker from scratch (GitHub: DroVibe/expense-tracker, live at familyexpensetracker.streamlit.app). Supabase backend, two-page layout (Dashboard + Records), receipt uploads, one-click settle, neutral Dad/Mom payer model with correct balance math for both parents.

## Keep In Mind
- Preserve business/project context first.
- Remove stale trading history before sacrificing current project context.
## Workflow Notes
