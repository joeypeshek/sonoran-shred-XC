// Exercises real Postgres permissions and RPCs in an embedded test database.
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const {PGlite}=await import(process.env.PGLITE_MODULE || '@electric-sql/pglite');
const db=new PGlite();
const sql=name=>readFile(new URL('../supabase/'+name,import.meta.url),'utf8');
await db.exec(`
  create role anon;
  create role authenticated;
  create schema auth;
  create table auth.users(id uuid primary key, email text);
  create function auth.uid() returns uuid language sql stable as $$
    select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid;
  $$;
  grant usage on schema auth, public to anon, authenticated;
  grant execute on function auth.uid() to anon, authenticated;
  insert into auth.users values
    ('00000000-0000-0000-0000-000000000001','officer@example.com'),
    ('00000000-0000-0000-0000-000000000002','visitor@example.com');
`);
await db.exec(await sql('schema.sql'));
await db.exec(await sql('seed.sql'));
await db.exec(`insert into public.dashboard_officers(user_id) values('00000000-0000-0000-0000-000000000001')`);
const [{state:seed}]=(await db.query('select state from public.dashboard_state')).rows;
const reject=async(query,params=[])=>assert.rejects(db.query(query,params),e=>e.code==='42501');
await db.exec('set role anon');
assert.equal((await db.query('select id,state,version,updated_at from public.dashboard_state')).rows.length,1);
await reject("update public.dashboard_state set version=99");
await reject("select public.save_dashboard($1::jsonb,0)",[JSON.stringify(seed)]);
await reject("insert into public.dashboard_officers values('00000000-0000-0000-0000-000000000002',now())");
await db.exec("reset role; set role authenticated; set request.jwt.claim.sub='00000000-0000-0000-0000-000000000002'");
assert.equal((await db.query('select public.is_dashboard_officer() as allowed')).rows[0].allowed,false);
await reject('select public.save_dashboard($1::jsonb,0)',[JSON.stringify(seed)]);
await reject('update public.dashboard_state set version=99');
await reject('select * from public.dashboard_officers');
await db.exec("set request.jwt.claim.sub='00000000-0000-0000-0000-000000000001'");
assert.equal((await db.query('select public.is_dashboard_officer() as allowed')).rows[0].allowed,true);
const changed=structuredClone(seed);changed.members[0].volunteer='complete';changed.design.heading='Shared edit';
const result=(await db.query('select public.save_dashboard($1::jsonb,0) as saved',[JSON.stringify(changed)])).rows[0].saved;
assert.equal(result.version,1);assert.equal(result.state.members[0].volunteer,'complete');
await assert.rejects(db.query('select public.save_dashboard($1::jsonb,0)',[JSON.stringify(seed)]),e=>e.code==='40001');
await assert.rejects(db.query("select public.save_dashboard('{}'::jsonb,1)"),e=>e.code==='22023');
await db.exec('reset role; set role anon');
assert.equal((await db.query('select state from public.dashboard_state')).rows[0].state.design.heading,'Shared edit');
await db.exec("reset role; delete from public.dashboard_officers; set role authenticated; set request.jwt.claim.sub='00000000-0000-0000-0000-000000000001'");
await reject('select public.save_dashboard($1::jsonb,1)',[JSON.stringify(changed)]);
await db.close();
console.log('PASS: public read; anonymous and non-officer write rejection; no self-promotion; officer save; conflict rejection; invalid input; public visibility; revoked access.');
