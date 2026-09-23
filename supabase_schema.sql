create table if not exists public.records (
  id text primary key,
  date date not null,
  name text,
  record_type text not null,
  value numeric,
  amount numeric,
  sponsor text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists records_date_idx on public.records (date);
create index if not exists records_type_idx on public.records (record_type);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists records_set_updated_at on public.records;
create trigger records_set_updated_at
before update on public.records
for each row
execute function public.set_updated_at();

alter table public.records enable row level security;

-- For production use, prefer authenticated-only access.
-- Run these policies if your web/mobile users will sign in with Supabase Auth.
drop policy if exists "authenticated users can read records" on public.records;
create policy "authenticated users can read records"
on public.records
for select
to authenticated
using (true);

drop policy if exists "authenticated users can insert records" on public.records;
create policy "authenticated users can insert records"
on public.records
for insert
to authenticated
with check (true);

drop policy if exists "authenticated users can update records" on public.records;
create policy "authenticated users can update records"
on public.records
for update
to authenticated
using (true)
with check (true);

drop policy if exists "authenticated users can delete records" on public.records;
create policy "authenticated users can delete records"
on public.records
for delete
to authenticated
using (true);
