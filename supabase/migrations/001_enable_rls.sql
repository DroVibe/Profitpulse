-- ============================================================
-- ProfitPulse — RLS Security Hardening
-- Run in Supabase SQL Editor (one-time, production critical)
--
-- Key note: public.users has NO 'id' column — linked to auth.users via 'email'.
-- All backfills and policies use email as the join key for users table.
--
-- Idempotent: safe to re-run if interrupted.
-- ============================================================

-- ── Create settings table if it doesn't exist ───────────────────────────────────
CREATE TABLE IF NOT EXISTS public.settings (
    username      TEXT PRIMARY KEY,
    business_type TEXT,
    user_id       UUID REFERENCES auth.users(id),
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ── 1. users ───────────────────────────────────────────────────────────────────
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.users
SET user_id = auth.users.id
FROM auth.users
WHERE public.users.email = auth.users.email
  AND public.users.user_id IS NULL;

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "users_own_row" ON public.users;
CREATE POLICY "users_own_row"
ON public.users FOR ALL TO authenticated
USING (
  email = (SELECT email FROM auth.users WHERE id = auth.uid())
);

-- ── 2. settings ───────────────────────────────────────────────────────────────
ALTER TABLE public.settings ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.settings
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.settings.username
    LIMIT 1
)
WHERE public.settings.user_id IS NULL;

CREATE OR REPLACE FUNCTION public.settings_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
DROP TRIGGER IF EXISTS trg_settings_set_username ON public.settings;
CREATE TRIGGER trg_settings_set_username
  BEFORE INSERT ON public.settings
  FOR EACH ROW EXECUTE FUNCTION public.settings_set_username();

ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "settings_own_rows" ON public.settings;
CREATE POLICY "settings_own_rows"
ON public.settings FOR ALL TO authenticated
USING (user_id = auth.uid());

-- ── 3. user_sales ────────────────────────────────────────────────────────────
ALTER TABLE public.user_sales ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_sales
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_sales.username
    LIMIT 1
)
WHERE public.user_sales.user_id IS NULL;

CREATE OR REPLACE FUNCTION public.user_sales_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
DROP TRIGGER IF EXISTS trg_user_sales_set_username ON public.user_sales;
CREATE TRIGGER trg_user_sales_set_username
  BEFORE INSERT ON public.user_sales
  FOR EACH ROW EXECUTE FUNCTION user_sales_set_username();

ALTER TABLE public.user_sales ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_sales_own_rows" ON public.user_sales;
CREATE POLICY "user_sales_own_rows"
ON public.user_sales FOR ALL TO authenticated
USING (user_id = auth.uid());

-- ── 4. user_purchases ────────────────────────────────────────────────────────
ALTER TABLE public.user_purchases ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_purchases
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_purchases.username
    LIMIT 1
)
WHERE public.user_purchases.user_id IS NULL;

CREATE OR REPLACE FUNCTION public.user_purchases_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
DROP TRIGGER IF EXISTS trg_user_purchases_set_username ON public.user_purchases;
CREATE TRIGGER trg_user_purchases_set_username
  BEFORE INSERT ON public.user_purchases
  FOR EACH ROW EXECUTE FUNCTION user_purchases_set_username();

ALTER TABLE public.user_purchases ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_purchases_own_rows" ON public.user_purchases;
CREATE POLICY "user_purchases_own_rows"
ON public.user_purchases FOR ALL TO authenticated
USING (user_id = auth.uid());

-- ── 5. user_expenses ──────────────────────────────────────────────────────────
ALTER TABLE public.user_expenses ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_expenses
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_expenses.username
    LIMIT 1
)
WHERE public.user_expenses.user_id IS NULL;

CREATE OR REPLACE FUNCTION public.user_expenses_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
DROP TRIGGER IF EXISTS trg_user_expenses_set_username ON public.user_expenses;
CREATE TRIGGER trg_user_expenses_set_username
  BEFORE INSERT ON public.user_expenses
  FOR EACH ROW EXECUTE FUNCTION user_expenses_set_username();

ALTER TABLE public.user_expenses ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_expenses_own_rows" ON public.user_expenses;
CREATE POLICY "user_expenses_own_rows"
ON public.user_expenses FOR ALL TO authenticated
USING (user_id = auth.uid());

-- ── 6. user_labor ────────────────────────────────────────────────────────────
ALTER TABLE public.user_labor ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_labor
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_labor.username
    LIMIT 1
)
WHERE public.user_labor.user_id IS NULL;

CREATE OR REPLACE FUNCTION public.user_labor_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
DROP TRIGGER IF EXISTS trg_user_labor_set_username ON public.user_labor;
CREATE TRIGGER trg_user_labor_set_username
  BEFORE INSERT ON public.user_labor
  FOR EACH ROW EXECUTE FUNCTION user_labor_set_username();

ALTER TABLE public.user_labor ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_labor_own_rows" ON public.user_labor;
CREATE POLICY "user_labor_own_rows"
ON public.user_labor FOR ALL TO authenticated
USING (user_id = auth.uid());

-- ── Verify ───────────────────────────────────────────────────────────────────
SELECT 'users'         AS tbl, count(*) AS total, count(user_id) AS backed_up, count(*) filter(WHERE user_id IS NULL) AS missing FROM public.users;
SELECT 'settings'      AS tbl, count(*) AS total, count(user_id) AS backed_up, count(*) filter(WHERE user_id IS NULL) AS missing FROM public.settings;
SELECT 'user_sales'    AS tbl, count(*) AS total, count(user_id) AS backed_up, count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_sales;
SELECT 'user_purchases' AS tbl, count(*) AS total, count(user_id) AS backed_up, count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_purchases;
SELECT 'user_expenses'  AS tbl, count(*) AS total, count(user_id) AS backed_up, count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_expenses;
SELECT 'user_labor'     AS tbl, count(*) AS total, count(user_id) AS backed_up, count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_labor;
