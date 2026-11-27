DO $retention$
DECLARE
    expected record;
    existing record;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
            RAISE EXCEPTION 'pg_cron is available but not installed in this database; configure and install it before scheduling retention';
        END IF;
        RAISE WARNING 'pg_cron is unavailable: retention jobs are NOT scheduled';
        RETURN;
    END IF;

    IF current_setting('is_superuser') <> 'on' THEN
        RAISE EXCEPTION 'Retention scheduling requires a superuser to inspect existing jobs and run partition maintenance';
    END IF;

    FOR expected IN
        SELECT * FROM (VALUES
            ('drop-raw-partitions', '17 3 * * 1',
             'SELECT public.drop_expired_partitions(''public.ais_message_raw'', 14)'),
            ('drop-water-level-partitions', '23 3 * * 1',
             'SELECT public.drop_expired_partitions(''public.water_level'', 90)'),
            ('drop-position-partitions', '27 3 * * 1',
             'SELECT public.drop_expired_partitions(''public.position'', 90)')
        ) AS jobs(name, schedule, command)
    LOOP
        FOR existing IN SELECT * FROM cron.job WHERE jobname = expected.name
        LOOP
            IF existing.database <> current_database() OR existing.username <> current_user
               OR existing.schedule <> expected.schedule OR existing.command <> expected.command
               OR NOT existing.active THEN
                RAISE EXCEPTION 'Conflicting pg_cron job % (id %); inspect and reconcile it before scheduling retention',
                    expected.name, existing.jobid;
            END IF;
        END LOOP;

        IF NOT FOUND THEN
            PERFORM cron.schedule(expected.name, expected.schedule, expected.command);
        END IF;
    END LOOP;
END;
$retention$;
