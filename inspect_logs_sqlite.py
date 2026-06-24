import os
import sqlite3


def main() -> None:
    path = os.path.expanduser(r"~\.codex\logs_2.sqlite")
    uri = "file:" + path.replace("\\", "/") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    print(f"path: {path}")
    print("objects:")
    for row in cur.execute(
        """
        select type, name, tbl_name, sql
        from sqlite_master
        where type in ('table', 'index', 'view', 'trigger')
        order by type, name
        """
    ):
        print(f"- {row['type']} {row['name']} on {row['tbl_name']}")
        print(f"  {row['sql']}")

    print("\ntables:")
    tables = [
        row["name"]
        for row in cur.execute(
            "select name from sqlite_master where type='table' order by name"
        )
    ]
    for table in tables:
        count = cur.execute(f'select count(*) as n from "{table}"').fetchone()["n"]
        print(f"- {table}: {count}")
        cols = cur.execute(f'pragma table_info("{table}")').fetchall()
        print("  columns: " + ", ".join(c["name"] for c in cols))

    # Heuristic summaries for likely log/event tables.
    for table in tables:
        cols = [c["name"] for c in cur.execute(f'pragma table_info("{table}")')]
        lower = {c.lower(): c for c in cols}
        level_col = next(
            (lower[k] for k in ("level", "severity", "log_level") if k in lower),
            None,
        )
        time_col = next(
            (
                lower[k]
                for k in (
                    "timestamp",
                    "ts",
                    "time",
                    "created_at",
                    "datetime",
                    "date",
                )
                if k in lower
            ),
            None,
        )
        msg_col = next(
            (
                lower[k]
                for k in (
                    "message",
                    "msg",
                    "body",
                    "text",
                    "content",
                    "event",
                    "target",
                )
                if k in lower
            ),
            None,
        )
        if not (level_col or time_col):
            continue

        print(f"\nsummary: {table}")
        if time_col:
            row = cur.execute(
                f'select min("{time_col}") as first, max("{time_col}") as last from "{table}"'
            ).fetchone()
            print(f"  {time_col}: {row['first']} -> {row['last']}")
        if level_col:
            print(f"  by {level_col}:")
            for row in cur.execute(
                f'''
                select "{level_col}" as level, count(*) as n
                from "{table}"
                group by "{level_col}"
                order by n desc
                limit 20
                '''
            ):
                print(f"    {row['level']}: {row['n']}")
        if time_col and level_col:
            print("  recent rows:")
            select_cols = [time_col, level_col]
            if msg_col and msg_col not in select_cols:
                select_cols.append(msg_col)
            sql_cols = ", ".join(f'"{c}"' for c in select_cols)
            for row in cur.execute(
                f'''
                select {sql_cols}
                from "{table}"
                order by "{time_col}" desc
                limit 10
                '''
            ):
                print("    " + " | ".join(str(row[c])[:180] for c in select_cols))

    if "logs" not in tables:
        return

    print("\nlogs detail:")
    latest = cur.execute("select max(ts) as ts from logs").fetchone()["ts"]
    print(f"  latest_ts: {latest}")
    for seconds in (60, 300, 900, 3600, 86400):
        print(f"  last {seconds}s by level:")
        for row in cur.execute(
            """
            select level, count(*) as n, sum(estimated_bytes) as bytes
            from logs
            where ts >= ?
            group by level
            order by n desc
            """,
            (latest - seconds,),
        ):
            print(f"    {row['level']}: {row['n']} rows, {row['bytes']} bytes")

    print("  top TRACE targets:")
    for row in cur.execute(
        """
        select target, count(*) as n, sum(estimated_bytes) as bytes
        from logs
        where level = 'TRACE'
        group by target
        order by n desc
        limit 15
        """
    ):
        print(f"    {row['target']}: {row['n']} rows, {row['bytes']} bytes")

    print("  recent minute buckets:")
    for row in cur.execute(
        """
        select (ts / 60) * 60 as minute, level, count(*) as n
        from logs
        where ts >= ?
        group by minute, level
        order by minute desc, n desc
        limit 80
        """,
        (latest - 3600,),
    ):
        print(f"    {row['minute']} | {row['level']}: {row['n']}")

    print("  busiest recent seconds:")
    for row in cur.execute(
        """
        select ts, level, count(*) as n
        from logs
        where ts >= ?
        group by ts, level
        order by ts desc, n desc
        limit 80
        """,
        (latest - 300,),
    ):
        print(f"    {row['ts']} | {row['level']}: {row['n']}")

    print("  recent full rows:")
    for row in cur.execute(
        """
        select id, ts, ts_nanos, level, target, module_path, file, line,
               thread_id, process_uuid, estimated_bytes,
               substr(coalesce(feedback_log_body, ''), 1, 240) as body
        from logs
        order by ts desc, ts_nanos desc, id desc
        limit 25
        """
    ):
        print(
            "    "
            + " | ".join(
                str(row[k])
                for k in (
                    "id",
                    "ts",
                    "level",
                    "target",
                    "module_path",
                    "line",
                    "estimated_bytes",
                    "body",
                )
            )
        )


if __name__ == "__main__":
    main()
