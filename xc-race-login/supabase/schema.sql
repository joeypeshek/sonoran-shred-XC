-- Run this in your Supabase project's SQL Editor, then run seed.sql.
begin;

create table if not exists public.dashboard_officers (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table public.dashboard_officers enable row level security;
revoke all on public.dashboard_officers from public, anon, authenticated;
-- No browser role can add itself or read the officer list.

create or replace function public.is_dashboard_officer()
returns boolean language sql stable security definer set search_path = ''
as $$
  select exists (select 1 from public.dashboard_officers where user_id = (select auth.uid()));
$$;
revoke all on function public.is_dashboard_officer() from public, anon;
grant execute on function public.is_dashboard_officer() to authenticated;

create table if not exists public.dashboard_state (
  id text primary key check (id = '76688'),
  state jsonb not null,
  version bigint not null default 0,
  updated_at timestamptz not null default now(),
  updated_by uuid references auth.users(id) on delete set null
);
alter table public.dashboard_state enable row level security;
revoke all on public.dashboard_state from public, anon, authenticated;
grant select (id, state, version, updated_at) on public.dashboard_state to anon, authenticated;
drop policy if exists "Everyone can view the dashboard" on public.dashboard_state;
create policy "Everyone can view the dashboard" on public.dashboard_state for select to anon, authenticated using (id = '76688');

-- Only this guarded function writes shared data. No client gets table write grants.
create or replace function public.save_dashboard(p_state jsonb, p_expected_version bigint)
returns jsonb language plpgsql security definer set search_path = ''
as $$
declare saved public.dashboard_state;
begin
  if not public.is_dashboard_officer() then
    raise exception 'Only approved officers can save changes.' using errcode = '42501';
  end if;
  if p_state is null or jsonb_typeof(p_state) <> 'object'
     or jsonb_typeof(p_state->'members') is distinct from 'array'
     or jsonb_typeof(p_state->'shifts') is distinct from 'array'
     or jsonb_typeof(p_state->'design') is distinct from 'object'
     or jsonb_typeof(p_state->'matchDecisions') is distinct from 'object'
     or octet_length(p_state::text) > 2000000 then
    raise exception 'Invalid dashboard data.' using errcode = '22023';
  end if;
  if jsonb_array_length(p_state->'members') > 5000 or jsonb_array_length(p_state->'shifts') > 1000 then
    raise exception 'Dashboard data is too large.' using errcode = '22023';
  end if;
  -- Registration data is owned by the BikeReg feed, not this RPC.
  p_state := jsonb_build_object('members',p_state->'members','shifts',p_state->'shifts','design',p_state->'design','matchDecisions',p_state->'matchDecisions');
  update public.dashboard_state set state = p_state, version = version + 1,
    updated_at = now(), updated_by = auth.uid()
    where id = '76688' and version = p_expected_version
    returning * into saved;
  if not found then
    raise exception 'Dashboard changed since you loaded it. Reload the shared version before saving.' using errcode = '40001';
  end if;
  return jsonb_build_object('state',saved.state,'version',saved.version,'updated_at',saved.updated_at);
end;
$$;
revoke all on function public.save_dashboard(jsonb,bigint) from public, anon;
grant execute on function public.save_dashboard(jsonb,bigint) to authenticated;
commit;
