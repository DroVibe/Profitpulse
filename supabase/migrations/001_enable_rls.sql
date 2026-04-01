-- ============================================================
-- ProfitPulse — RLS Security Hardening
-- Run in Supabase SQL Editor (one-time, production critical)
--
-- WHAT THIS DOES:
--   1. Adds user_id column linking each table to auth.users(id)
--   2. Backfills user_id by joining on email
--   3. Enables RLS on every table
--   4. Creates policies scoped to auth.uid()
--
-- IMPORTANT: Run as the service role (supabase_service_key) so
-- the backfill can read auth.users without hitting RLS itself.
-- ============================================================

-- ── 1. users table ─────────────────────────────────────────────────────────────
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- Backfill: match public.users rows to auth.users by email
UPDATE public.users
SET user_id = auth.users.id
FROM auth.users
WHERE public.users.email = auth.users.email
  AND public.users.user_id IS NULL;

-- Enable RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Users can only see/edit their own row
CREATE POLICY "users_own_row"
ON public.users
FOR ALL
TO authenticated
USING (id = auth.uid());


-- ── 2. settings table ──────────────────────────────────────────────────────────
ALTER TABLE public.settings ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- Backfill settings.user_id by joining to public.users on username
UPDATE public.settings
SET user_id = public.users.user_id
FROM public.users
WHERE public.settings.username = public.users.username
  AND public.settings.user_id IS NULL;

-- Auto-set username on insert from auth context (so future inserts are safe)
CREATE OR REPLACE FUNCTION settings_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users WHERE user_id = auth.uid() LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_settings_set_username
  BEFORE INSERT ON public.settings
  FOR EACH ROW EXECUTE FUNCTION settings_set_username();

ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "settings_own_rows"
ON public.settings
FOR ALL
TO authenticated
USING (user_id = auth.uid());


-- ── 3. user_sales ──────────────────────────────────────────────────────────────
ALTER TABLE public.user_sales ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_sales
SET user_id = public.users.user_id
FROM public.users
WHERE public.user_sales.username = public.users.username
  AND public.user_sales.user_id IS NULL;

CREATE OR REPLACE FUNCTION user_sales_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users WHERE user_id = auth.uid() LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_user_sales_set_username
  BEFORE INSERT ON public.user_sales
  FOR EACH ROW EXECUTE FUNCTION user_sales_set_username();

ALTER TABLE public.user_sales ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_sales_own_rows"
ON public.user_sales
FOR ALL
TO authenticated
USING (user_id = auth.uid());


-- ── 4. user_purchases ─────────────────────────────────────────────────────────
ALTER TABLE public.user_purchases ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_purchases
SET user_id = public.users.user_id
FROM public.users
WHERE public.user_purchases.username = public.users.username
  AND public.user_purchases.user_id IS NULL;

CREATE OR REPLACE FUNCTION user_purchases_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users WHERE user_id = auth.uid() LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_user_purchases_set_username
  BEFORE INSERT ON public.user_purchases
  FOR EACH ROW EXECUTE FUNCTION user_purchases_set_username();

ALTER TABLE public.user_purchases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_purchases_own_rows"
ON public.user_purchases
FOR ALL
TO authenticated
USING (user_id = auth.uid());


-- ── 5. user_expenses ──────────────────────────────────────────────────────────
ALTER TABLE public.user_expenses ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_expenses
SET user_id = public.users.user_id
FROM public.users
WHERE public.user_expenses.username = public.users.username
  AND public.user_expenses.user_id IS NULL;

CREATE OR REPLACE FUNCTION user_expenses_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users WHERE user_id = auth.uid() LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_user_expenses_set_username
  BEFORE INSERT ON public.user_expenses
  FOR EACH ROW EXECUTE FUNCTION user_expenses_set_username();

ALTER TABLE public.user_expenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_expenses_own_rows"
ON public.user_expenses
FOR ALL
TO authenticated
USING (user_id = auth.uid());


-- ── 6. user_labor ─────────────────────────────────────────────────────────────
ALTER TABLE public.user_labor ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

UPDATE public.user_labor
SET user_id = public.users.user_id
FROM public.users
WHERE public.user_labor.username = public.users.username
  AND public.user_labor.user_id IS NULL;

CREATE OR REPLACE FUNCTION user_labor_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users WHERE user_id = auth.uid() LIMIT 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trg_user_labor_set_username
  BEFORE INSERT ON public.user_labor
  FOR EACH ROW EXECUTE FUNCTION user_labor_set_username();

ALTER TABLE public.user_labor ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_labor_own_rows"
ON public.user_labor
FOR ALL
TO authenticated
USING (user_id = auth.uid());


-- ── 7. Verify ─────────────────────────────────────────────────────────────────
SELECT 'users'        AS table_name, COUNT(*) AS total_rows,
       COUNT(user_id)  AS with_user_id, COUNT(*) FILTER (WHERE user_id IS NULL) AS missing
FROM public.users;
SELECT 'settings'      AS table_name, COUNT(*) AS total_rows, COUNT(user_id) AS with_user_id, COUNT(*) FILTER (WHERE user_id IS NULL) AS missing FROM public.settings;
SELECT 'user_sales'   AS table_name, COUNT(*) AS total_rows, COUNT(user_id) AS with_user_id, COUNT(*) FILTER (WHERE user_id IS NULL) AS missing FROM public.user_sales;
SELECT 'user_purchases' AS table_name, COUNT(*) AS total_rows, COUNT(user_id) AS with_user_id, COUNT(*) FILTER (WHERE user_id IS NULL) AS missing FROM public.user_purchases;
SELECT 'user_expenses'  AS table_name, COUNT(*) AS total_rows, COUNT(user_id) AS with_user_id, COUNT(*) FILTER (WHERE user_id IS NULL) AS missing FROM public.user_expenses;
SELECT 'user_labor'     AS table_name, COUNT(*) AS total_rows, COUNT(user_id) AS with_user_id, COUNT(*) FILTER (WHERE user_id IS NULL) AS missing FROM public.user_labor;
