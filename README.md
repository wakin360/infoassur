# UA Lost & Found

## Shared storage for Vercel

The application stores found-item records in Supabase so the staff portal and student portal share the same data across devices and Vercel function instances.

1. Create a Supabase project.
2. In the Supabase SQL Editor, run the SQL in `supabase_schema.sql`.
3. In Supabase Project Settings, copy the Project URL and the `service_role` API key. Keep the service-role key private; never put it in browser JavaScript or commit it to GitHub.
4. In the Vercel project settings, add these Environment Variables for Production (and Preview if used):
	- `SUPABASE_URL`: the Supabase Project URL.
	- `SUPABASE_SERVICE_ROLE_KEY`: the Supabase `service_role` key.
	- `ENCRYPTION_KEY`: a randomly generated 64-character hexadecimal key.
	- `FLASK_SECRET_KEY`: a separate, strong random secret for Flask sessions.
	- `STAFF_PASSWORD`: a strong staff-only password.
5. Generate separate secrets locally with Python, then enter the output directly in Vercel:

	```text
	python -c "import secrets; print(secrets.token_hex(32))"
	```

	Run it once for `ENCRYPTION_KEY` and again for `FLASK_SECRET_KEY`; choose a different strong value for `STAFF_PASSWORD`.
6. Redeploy the Vercel project after adding the variables.

Do not change or regenerate `ENCRYPTION_KEY` after items have been registered. Existing encrypted proof answers cannot be decrypted with a different key. The old in-memory items were not persisted and cannot be recovered by this change; register them again after Supabase is configured.

The Supabase table has row-level security enabled and no public policies. The application accesses it only from the server using the private service-role key.
