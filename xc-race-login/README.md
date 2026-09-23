# Sonoran Shred XC — public dashboard with officer login

This version keeps the dashboard public, adds approved-officer email/password login, and saves volunteer records, shifts, team-match decisions, and design online in Supabase. BikeReg registrations continue to update through GitHub Actions. Nothing is connected to a Supabase account until you complete the setup below.

## Fix the current GitHub error

Your repository currently has `test_sync.py` and `sync_bikereg.py` at the top level. The old workflow expects `tests/test_sync.py` and `scripts/sync_bikereg.py`. That is why it stops before fetching BikeReg.

For the current version, rename those files to those paths in GitHub, then rerun the workflow. For this new login version, upload the complete package using the structure below. Do not flatten its folders.

## 1. Create the database and your officer account

1. Create a Supabase project at https://supabase.com/dashboard. Keep its database password private.
2. In **SQL Editor**, paste and run `supabase/schema.sql`.
3. Paste and run `supabase/seed.sql`. This seeds the included roster, shifts, and design. Rerunning it does not replace existing shared data.
4. In **Authentication → Users**, create your user with your own email and a strong password. For an account you create yourself as project owner, use the confirmed-user option if offered. Do not put this password into any repository file.
5. Open `supabase/add-officer.sql`, replace `YOUR_EMAIL_HERE` with that exact account email, and run it in SQL Editor. Confirm that your email appears in the final query result. A login account alone does not grant editing rights.
6. Turn off public user signup in Supabase Authentication settings; create other officers from the project dashboard and explicitly add them with the same SQL procedure.

The website has no signup button. Postgres enforces the officer allowlist on every save. Visitors and unapproved accounts cannot save shared changes even if they modify their browser's HTML or JavaScript.

## 2. Connect this website

Open `config.js`. Set `supabaseUrl` to the project's HTTPS URL and `supabaseKey` to its **publishable key** (or legacy **anon key**). These two values are intended for browser use. Never use a secret/service_role key or database password here.

For your repository, the usual Pages URL is:

`https://joeypeshek.github.io/xc-race/`

Use the actual URL shown in GitHub Pages if you configured a different URL. In Supabase **Authentication → URL Configuration**, set the Site URL and allowed Redirect URLs to the actual dashboard URL. Also allow the version ending in `/index.html` if you open it that way. This is needed for password reset links.

Password login itself does not need email delivery. The **Forgot password?** flow does: configure an SMTP provider in Supabase for reliable email delivery to your officers. Supabase's default email service has limitations. Do not assume reset emails work until you test them with your account.

## 3. Upload and deploy

Upload the extracted contents to the root of `joeypeshek/xc-race` on its default branch, preserving these paths:

```text
index.html
app.js
config.js
package.json
package-lock.json
vendor/supabase.js
vendor/LICENSE
scripts/__init__.py
scripts/sync_bikereg.py
tests/__init__.py
tests/test_sync.py
tests/test_access.mjs
tests/test_client.cjs
supabase/schema.sql
supabase/seed.sql
supabase/add-officer.sql
.github/workflows/update.yml
```

Delete the old top-level `test_sync.py` and `sync_bikereg.py` after putting the new versions in their folders. Upload files, not the ZIP or an enclosing `login-dashboard` folder. If GitHub's upload skips `.github`, edit the existing `.github/workflows/update.yml` and paste the included workflow.

1. In **Settings → Pages**, choose **GitHub Actions** as the publishing source.
2. Open **Actions → Update and publish race dashboard → Run workflow** on the default branch.
3. Wait for a successful deployment. Visit the Pages URL and click **Officer sign in**.
4. Sign in, change one record, click **Save changes**, and check it in a signed-out browser window. This verifies your actual account, database policies, and public view together.

The workflow publishes only the generated `public/` directory. SQL setup files and tests are not deployed as website assets. They can still be seen in a public source repository; no secrets belong in them.

If migrating edits from the older offline dashboard, first export a JSON backup from that copy. After setting up this version and signing in, use **Restore backup**, review the records, and click **Save changes**. Browser-local drafts are not migrated automatically.

## Using the dashboard

- Public visitors do not sign in. Editing controls require an approved officer account.
- Changes are drafts until you click **Save changes**. They are then saved online; no HTML download or GitHub upload is needed for routine roster, volunteer, shift, or design edits.
- Other open dashboards check shared officer changes every **30 seconds**. A tab with unsaved edits keeps its draft instead of replacing it with another officer's changes.
- GitHub fetches BikeReg about every **15 minutes**, at minutes 7, 22, 37, and 52. Open pages check that published feed every **60 seconds**. Scheduled GitHub runs can be delayed; inactive public repositories can have schedules disabled after 60 days without activity.
- New team registrations appear automatically. Uncertain team spellings go to officer review. The known typo and common abbreviations are recognized.
- Automatic registration updates do not replace volunteer records, shifts, or design.
- If two officers save competing drafts, the second save is rejected instead of overwriting the first. Export your draft backup, click **Reload shared data**, and reapply the intended changes.
- If access is revoked, the database immediately rejects future saves even before the page next checks the user's role.
- Team notes are public, like the rest of the dashboard. They are labeled accordingly.
- Closing a tab with unsaved edits shows a browser warning. Drafts are kept only in that tab; export a backup if you need to keep an unsaved draft.

## Tests and limits

Tests cover the BikeReg parser, preservation of officer data, public read access, anonymous/non-officer write rejection, blocked self-promotion, officer saves, revoked access, and version conflicts. Database tests use embedded Postgres; your live Supabase account and email delivery still need the setup check above.

Run `python -m unittest tests.test_sync -v`. With Node.js installed, run `npm ci` and `npm test`. GitHub runs all tests on uploads/manual runs; scheduled updates run the Python sync tests. No Node.js server is needed for hosting.

An invalid or empty BikeReg response fails deployment and leaves the last successful site online. If BikeReg changes its endpoint or categories, update `scripts/sync_bikereg.py`. During Supabase outages, the dashboard may show its last loaded data or the embedded baseline and explains that live data is unavailable.

Documentation:
- https://supabase.com/docs/guides/auth/passwords
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://supabase.com/docs/guides/getting-started/api-keys
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
