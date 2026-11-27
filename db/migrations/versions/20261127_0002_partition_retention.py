"""Use actual range bounds for partition retention and clean default partitions."""

from alembic import op

revision = "20261127_0002"
down_revision = "20241124_0001"
branch_labels = None
depends_on = None

UPGRADE_SQL = r"""
CREATE OR REPLACE FUNCTION drop_expired_partitions(p_table text, p_keep_days integer)
RETURNS integer
LANGUAGE plpgsql
SET DateStyle = 'ISO, YMD'
AS $$
DECLARE
    parent_oid oid;
    parent_schema text;
    parent_name text;
    time_column text;
    cutoff timestamptz;
    part record;
    upper_bound text;
    dropped integer := 0;
BEGIN
    IF p_keep_days IS NULL OR p_keep_days < 0 THEN
        RAISE EXCEPTION 'Retention days must be non-negative';
    END IF;

    parent_oid := to_regclass(p_table);
    SELECT n.nspname, c.relname, a.attname
      INTO parent_schema, parent_name, time_column
      FROM pg_partitioned_table pt
      JOIN pg_class c ON c.oid = pt.partrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = pt.partattrs[0]
     WHERE c.oid = parent_oid AND pt.partstrat = 'r' AND pt.partnatts = 1
       AND a.atttypid = 'timestamptz'::regtype;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Expected a single timestamptz range-partitioned table: %', p_table;
    END IF;

    EXECUTE format('LOCK TABLE %I.%I IN ACCESS EXCLUSIVE MODE', parent_schema, parent_name);
    IF to_regclass(format('%I.%I', parent_schema, parent_name))::oid <> parent_oid THEN
        RAISE EXCEPTION 'Partitioned table changed while acquiring lock: %', p_table;
    END IF;
    cutoff := now() - make_interval(days => p_keep_days);
    FOR part IN
        SELECT child.oid, child.relname, child.relkind, ns.nspname,
               pg_get_expr(child.relpartbound, child.oid) AS bounds
          FROM pg_inherits i
          JOIN pg_class child ON child.oid = i.inhrelid
          JOIN pg_namespace ns ON ns.oid = child.relnamespace
         WHERE i.inhparent = parent_oid
    LOOP
        IF part.relkind <> 'r' THEN
            RAISE EXCEPTION 'Unsupported partition type for %.%', part.nspname, part.relname;
        ELSIF part.bounds = 'DEFAULT' THEN
            EXECUTE format('DELETE FROM %I.%I WHERE %I < $1',
                           part.nspname, part.relname, time_column) USING cutoff;
        ELSIF part.bounds LIKE '% TO (MAXVALUE)' THEN
            CONTINUE;
        ELSE
            upper_bound := substring(part.bounds FROM 'TO \(''([^'']+)''\)$');
            IF upper_bound IS NULL THEN
                RAISE EXCEPTION 'Unsupported partition bound for %.%: %',
                    part.nspname, part.relname, part.bounds;
            END IF;
            IF upper_bound::timestamptz <= cutoff THEN
                EXECUTE format('DROP TABLE %I.%I', part.nspname, part.relname);
                dropped := dropped + 1;
            END IF;
        END IF;
    END LOOP;
    RETURN dropped;
END;
$$;
"""

DOWNGRADE_SQL = r"""
CREATE OR REPLACE FUNCTION drop_expired_partitions(p_table text, p_keep_days integer)
RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
    r record;
    v_dropped integer := 0;
    v_boundary date := (now() - (p_keep_days || ' days')::interval)::date;
BEGIN
    FOR r IN
        SELECT c.relname AS partition_name,
               to_date(substring(c.relname FROM '_p(\d{8})$'), 'YYYYMMDD')
                   + interval '1 day' AS range_end
        FROM pg_class c
        JOIN pg_inherits i ON i.inhrelid = c.oid
        JOIN pg_class p ON p.oid = i.inhparent
        JOIN pg_namespace n ON n.oid = p.relnamespace
        WHERE n.nspname = 'public'
          AND p.relname = p_table
          AND c.relname ~ ('^' || p_table || '_p\d{8}$')
          AND c.relname NOT LIKE '%_default'
    LOOP
        BEGIN
            IF r.range_end::date < v_boundary THEN
                EXECUTE format('DROP TABLE %I', r.partition_name);
                v_dropped := v_dropped + 1;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            CONTINUE;
        END;
    END LOOP;
    RETURN v_dropped;
END;
$$;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
