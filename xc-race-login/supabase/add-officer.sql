-- First create the user in Supabase Authentication > Users > Add user.
-- Replace the address below with the actual officer's account email.
-- Run only in the Supabase SQL Editor. Never expose a service_role key to the website.
insert into public.dashboard_officers (user_id)
select id from auth.users where lower(email) = lower('YOUR_EMAIL_HERE')
on conflict (user_id) do nothing;

-- Confirm that a row was added. If the result is empty, check the email and create the user first.
select u.email, o.created_at
from public.dashboard_officers o join auth.users u on u.id = o.user_id;

-- To revoke access later, run this with the actual email:
-- delete from public.dashboard_officers
-- where user_id in (select id from auth.users where lower(email) = lower('OFFICER_EMAIL_HERE'));
