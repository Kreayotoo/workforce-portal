-- ============================================================
-- WorkForce Portal — Supabase Database Schema
-- HOW TO USE:
--   1. Go to https://supabase.com → open your project
--   2. Click "SQL Editor" in the left sidebar
--   3. Click "New query"
--   4. Copy everything below and paste it in
--   5. Click the green "Run" button
--   Done! All tables will be created with sample data.
-- ============================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ─── EMPLOYEES ───────────────────────────────────────────────
create table if not exists employees (
  id uuid primary key default uuid_generate_v4(),
  emp_id text unique not null,
  name text not null,
  email text unique not null,
  phone text,
  department text not null,
  role text not null,
  status text default 'Active' check (status in ('Active','Pending','Inactive')),
  salary numeric default 30000,
  date_of_joining date,
  created_at timestamptz default now()
);

-- ─── ATTENDANCE ──────────────────────────────────────────────
create table if not exists attendance (
  id uuid primary key default uuid_generate_v4(),
  employee_id uuid references employees(id) on delete cascade,
  employee_name text not null,
  date date not null,
  status text default 'Present' check (status in ('Present','Absent','Half Day','Not marked')),
  in_time time,
  out_time time,
  created_at timestamptz default now(),
  unique(employee_id, date)
);

-- ─── LEAVES ──────────────────────────────────────────────────
create table if not exists leaves (
  id uuid primary key default uuid_generate_v4(),
  employee_id uuid references employees(id) on delete cascade,
  employee_name text not null,
  leave_type text not null check (leave_type in ('Casual','Sick','Earned','Maternity','Paternity')),
  from_date date not null,
  to_date date not null,
  days integer not null,
  reason text,
  status text default 'Pending' check (status in ('Pending','Approved','Rejected')),
  created_at timestamptz default now()
);

-- ─── EXPENSES ────────────────────────────────────────────────
create table if not exists expenses (
  id uuid primary key default uuid_generate_v4(),
  employee_id uuid references employees(id) on delete cascade,
  employee_name text not null,
  category text not null check (category in ('Travel','Food','Training','Accommodation','Other')),
  amount numeric not null,
  expense_date date not null,
  description text,
  status text default 'Pending' check (status in ('Pending','Approved','Rejected')),
  created_at timestamptz default now()
);

-- ─── PERFORMANCE ─────────────────────────────────────────────
create table if not exists performance (
  id uuid primary key default uuid_generate_v4(),
  employee_id uuid references employees(id) on delete cascade,
  employee_name text not null,
  quarter text not null,
  rating numeric check (rating >= 1 and rating <= 5),
  goals_set integer default 0,
  goals_achieved integer default 0,
  review_notes text,
  created_at timestamptz default now()
);

-- ─── NOTIFICATIONS ───────────────────────────────────────────
create table if not exists notifications (
  id uuid primary key default uuid_generate_v4(),
  message text not null,
  type text default 'info' check (type in ('info','warning','success','danger')),
  is_read boolean default false,
  created_at timestamptz default now()
);

-- ─── COMPANY SETTINGS ────────────────────────────────────────
create table if not exists settings (
  id uuid primary key default uuid_generate_v4(),
  company_name text default 'My Company',
  company_email text default 'hr@mycompany.com',
  timezone text default 'Asia/Kolkata',
  currency text default 'INR',
  work_hours integer default 9,
  office_lat numeric default 17.3850,
  office_lng numeric default 78.4867,
  office_radius integer default 500,
  updated_at timestamptz default now()
);

-- ─── LOGIN LOGS ──────────────────────────────────────────────
create table if not exists login_logs (
  id uuid primary key default uuid_generate_v4(),
  user_name text,
  user_email text,
  login_time timestamptz default now(),
  latitude numeric,
  longitude numeric,
  accuracy numeric,
  address text,
  in_office boolean,
  method text default 'password' check (method in ('password','face')),
  created_at timestamptz default now()
);

-- ============================================================
-- SAMPLE DATA — edit or delete as needed
-- ============================================================

insert into settings (company_name, company_email) 
values ('My Company', 'hr@mycompany.com') 
on conflict do nothing;

insert into employees (emp_id, name, email, phone, department, role, status, salary, date_of_joining) values
  ('EMP-101','Kiran Kumar',   'kiran.kumar@company.com',  '9876543210','Engineering','Lead Developer',   'Active', 75000,'2023-01-15'),
  ('EMP-102','Priya Sharma',  'priya.sharma@company.com', '9876543211','HR',         'HR Manager',       'Active', 65000,'2023-02-01'),
  ('EMP-103','Ravi Nair',     'ravi.nair@company.com',    '9876543212','Sales',      'Sales Executive',  'Active', 55000,'2023-03-10'),
  ('EMP-104','Ananya Reddy',  'ananya.reddy@company.com', '9876543213','Finance',    'Accountant',       'Pending',50000,'2024-01-05'),
  ('EMP-105','Suresh Babu',   'suresh.babu@company.com',  '9876543214','Operations', 'Ops Manager',      'Active', 60000,'2023-04-20'),
  ('EMP-106','Deepa Menon',   'deepa.menon@company.com',  '9876543215','Marketing',  'Marketing Lead',   'Active', 58000,'2023-05-15'),
  ('EMP-107','Arjun Pillai',  'arjun.pillai@company.com', '9876543216','Engineering','Software Engineer','Active', 52000,'2023-06-01'),
  ('EMP-108','Lakshmi Das',   'lakshmi.das@company.com',  '9876543217','Finance',    'Sr. Accountant',   'Active', 62000,'2023-07-10')
on conflict do nothing;

insert into leaves (employee_id, employee_name, leave_type, from_date, to_date, days, reason, status)
select id, name, 'Casual', '2026-04-18', '2026-04-19', 2, 'Personal work', 'Pending'
from employees where emp_id = 'EMP-102'
on conflict do nothing;

insert into leaves (employee_id, employee_name, leave_type, from_date, to_date, days, reason, status)
select id, name, 'Sick', '2026-04-15', '2026-04-15', 1, 'Fever', 'Approved'
from employees where emp_id = 'EMP-103'
on conflict do nothing;

insert into expenses (employee_id, employee_name, category, amount, expense_date, description, status)
select id, name, 'Travel', 4500, '2026-04-10', 'Client visit Hyderabad', 'Approved'
from employees where emp_id = 'EMP-101'
on conflict do nothing;

insert into expenses (employee_id, employee_name, category, amount, expense_date, description, status)
select id, name, 'Food', 850, '2026-04-12', 'Team lunch', 'Pending'
from employees where emp_id = 'EMP-103'
on conflict do nothing;

insert into notifications (message, type, is_read) values
  ('Welcome to WorkForce Portal! Set up your company profile in Settings.', 'success', false),
  ('2 employees have pending account activation.',                           'warning', false),
  ('Sample data loaded — edit or delete employees as needed.',               'info',    true)
on conflict do nothing;

-- ============================================================
-- ROW LEVEL SECURITY
-- Allows all authenticated (logged-in) users to read/write.
-- Tighten these policies in production if needed.
-- ============================================================

alter table employees     enable row level security;
alter table attendance    enable row level security;
alter table leaves        enable row level security;
alter table expenses      enable row level security;
alter table performance   enable row level security;
alter table notifications enable row level security;
alter table settings      enable row level security;
alter table login_logs    enable row level security;

create policy "authenticated full access" on employees     for all to authenticated using (true) with check (true);
create policy "authenticated full access" on attendance    for all to authenticated using (true) with check (true);
create policy "authenticated full access" on leaves        for all to authenticated using (true) with check (true);
create policy "authenticated full access" on expenses      for all to authenticated using (true) with check (true);
create policy "authenticated full access" on performance   for all to authenticated using (true) with check (true);
create policy "authenticated full access" on notifications for all to authenticated using (true) with check (true);
create policy "authenticated full access" on settings      for all to authenticated using (true) with check (true);
create policy "authenticated full access" on login_logs    for all to authenticated using (true) with check (true);

-- ============================================================
-- All done! Your database is ready.
-- ============================================================
