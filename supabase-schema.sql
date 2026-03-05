-- ============================================
-- INCREASE TEAM — Supabase Schema
-- Projeto: obbxihwnpgpdpusumvfs
-- Execute no SQL Editor do Supabase Dashboard
-- ============================================

-- Tabela: users_profile
CREATE TABLE IF NOT EXISTS users_profile (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT DEFAULT '',
  whatsapp TEXT DEFAULT '',
  role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
  referral TEXT DEFAULT '',
  onboarded_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela: companies
CREATE TABLE IF NOT EXISTS companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
  company_name TEXT NOT NULL,
  sector TEXT DEFAULT '',
  team_size TEXT DEFAULT '',
  revenue TEXT DEFAULT '',
  challenges JSONB DEFAULT '[]'::jsonb,
  main_challenge TEXT DEFAULT '',
  goals TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_companies_user_id ON companies(user_id);
CREATE INDEX IF NOT EXISTS idx_users_profile_email ON users_profile(email);

-- RLS (Row Level Security)
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

-- Policies: users_profile
CREATE POLICY "Users can view own profile"
  ON users_profile FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON users_profile FOR INSERT
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON users_profile FOR UPDATE
  USING (auth.uid() = id);

-- Admin pode ver todos os perfis
CREATE POLICY "Admin can view all profiles"
  ON users_profile FOR SELECT
  USING (
    auth.jwt() ->> 'email' IN ('jose@increaseteam.com', 'josepassinato@gmail.com')
  );

-- Policies: companies
CREATE POLICY "Users can view own company"
  ON companies FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own company"
  ON companies FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own company"
  ON companies FOR UPDATE
  USING (auth.uid() = user_id);

-- Admin pode ver todas as empresas
CREATE POLICY "Admin can view all companies"
  ON companies FOR SELECT
  USING (
    auth.jwt() ->> 'email' IN ('jose@increaseteam.com', 'josepassinato@gmail.com')
  );
