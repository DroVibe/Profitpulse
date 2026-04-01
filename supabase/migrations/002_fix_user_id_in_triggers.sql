-- ============================================================
-- ProfitPulse — Fix: set user_id = auth.uid() in all insert triggers
-- Run after 001 — patches the triggers that forgot to set user_id
-- ============================================================

-- Macro: set both username AND user_id on every insert
CREATE OR REPLACE FUNCTION public._upsert_ username_and_user_id(TABLE_NAME text)
RETURNS void AS $$
DECLARE
  col_user_id text := 'user_id';
BEGIN
  -- This is applied per-table below
END;
$$ LANGUAGE plpgsql;

-- user_sales trigger: add user_id = auth.uid()
CREATE OR REPLACE FUNCTION public.user_sales_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  NEW.user_id = COALESCE(
    NEW.user_id,
    (SELECT user_id FROM public.users
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

-- Backfill user_id for any existing rows that have username but NULL user_id
UPDATE public.user_sales
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_sales.username
    LIMIT 1
)
WHERE user_id IS NULL;

-- user_purchases
CREATE OR REPLACE FUNCTION public.user_purchases_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  NEW.user_id = COALESCE(
    NEW.user_id,
    (SELECT user_id FROM public.users
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

UPDATE public.user_purchases
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_purchases.username
    LIMIT 1
)
WHERE user_id IS NULL;

-- user_expenses
CREATE OR REPLACE FUNCTION public.user_expenses_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  NEW.user_id = COALESCE(
    NEW.user_id,
    (SELECT user_id FROM public.users
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

UPDATE public.user_expenses
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_expenses.username
    LIMIT 1
)
WHERE user_id IS NULL;

-- user_labor
CREATE OR REPLACE FUNCTION public.user_labor_set_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username = COALESCE(
    NEW.username,
    (SELECT username FROM public.users
     WHERE email = (SELECT email FROM auth.users WHERE id = auth.uid())
     LIMIT 1)
  );
  NEW.user_id = COALESCE(
    NEW.user_id,
    (SELECT user_id FROM public.users
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

UPDATE public.user_labor
SET user_id = (
    SELECT u.user_id FROM public.users u
    WHERE u.username = public.user_labor.username
    LIMIT 1
)
WHERE user_id IS NULL;

-- Verify: all should show 0 missing
SELECT 'user_sales' AS tbl,count(*) AS total,count(user_id) AS backed_up,count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_sales;
SELECT 'user_purchases' AS tbl,count(*) AS total,count(user_id) AS backed_up,count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_purchases;
SELECT 'user_expenses' AS tbl,count(*) AS total,count(user_id) AS backed_up,count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_expenses;
SELECT 'user_labor' AS tbl,count(*) AS total,count(user_id) AS backed_up,count(*) filter(WHERE user_id IS NULL) AS missing FROM public.user_labor;
