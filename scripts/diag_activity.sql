-- Who is connected to Supabase right now?
SELECT
  coalesce(application_name, '') AS app,
  usename,
  CASE WHEN client_addr IS NULL THEN 'internal' ELSE host(client_addr) END AS client,
  state,
  count(*) AS n,
  max(state_change)::time AS last_state_change
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY 1,2,3,4
ORDER BY n DESC;
