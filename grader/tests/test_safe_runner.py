"""
Offline tests for grader/safe_runner.py and the safe_runner switch of agent_loop.py (D41).
No OpenAI call. The walls that touch the database use the real read-only role (grader_ro).

Run from the grader folder:  python -m unittest discover -s tests -v
"""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agent_loop
import safe_runner
from executor import QueryError
from loader import load_questions
from safe_runner import Limits, SafeResult, check_static, load_limits, safe_execute

LIMITS = load_limits()


class TestWall1Attacks(unittest.TestCase):
    """Every one of these is stopped by the static check, before the database is touched."""

    def assertBlockedAtWall1(self, sql, expect=None):
        res = check_static(sql)
        self.assertIsNotNone(res, f"not blocked: {sql!r}")
        self.assertTrue(res.blocked)
        self.assertEqual(res.wall, 1)
        self.assertEqual(res.kind, "static")
        if expect:
            self.assertIn(expect, res.reason)
        # and through the full entry point: same answer, no exception, no database needed
        full = safe_execute(sql, LIMITS)
        self.assertTrue(full.blocked)
        self.assertEqual(full.wall, 1)

    def test_stacked_statement_drop(self):
        self.assertBlockedAtWall1("SELECT 1; DROP TABLE erzeugung")

    def test_comment_after_semicolon(self):
        self.assertBlockedAtWall1("SELECT * FROM erzeugung; -- comment")

    def test_delete_inside_cte(self):
        self.assertBlockedAtWall1("WITH x AS (DELETE FROM preise RETURNING *) SELECT * FROM x", "Delete")

    def test_select_into(self):
        self.assertBlockedAtWall1("SELECT * INTO copy_table FROM preise", "Into")

    def test_pg_catalog(self):
        self.assertBlockedAtWall1("SELECT * FROM pg_catalog.pg_user", "pg_catalog.pg_user")

    def test_pg_catalog_unqualified(self):
        self.assertBlockedAtWall1("SELECT * FROM pg_user", "pg_user")

    def test_information_schema(self):
        self.assertBlockedAtWall1("SELECT * FROM information_schema.tables", "information_schema.tables")

    def test_pg_sleep(self):
        self.assertBlockedAtWall1("SELECT pg_sleep(60)")
        self.assertBlockedAtWall1("SELECT pg_sleep(60) FROM erzeugung", "pg_sleep")

    def test_pg_read_file(self):
        self.assertBlockedAtWall1("SELECT pg_read_file('/etc/passwd')")
        self.assertBlockedAtWall1("SELECT pg_read_file('/etc/passwd') FROM preise", "pg_read_file")

    def test_select_without_table(self):
        self.assertBlockedAtWall1("SELECT 0", "none of the tables")
        self.assertBlockedAtWall1("SELECT 1 FROM generate_series(1, 3)", "none of the tables")
        self.assertBlockedAtWall1("WITH x AS (SELECT 1) SELECT * FROM x", "none of the tables")

    def test_comment_obfuscated_second_statement(self):
        self.assertBlockedAtWall1("select/**/*/**/from/**/preise; delete from preise")

    def test_copy(self):
        self.assertBlockedAtWall1("COPY preise TO '/tmp/x'", "Copy")

    def test_set_role(self):
        self.assertBlockedAtWall1("SET ROLE postgres")

    def test_update_inside_subquery(self):
        # The parser refuses an UPDATE inside a subquery, so it is stopped as unparseable.
        # If a future parser accepts it, the node walk (Update) stops it the same way.
        self.assertBlockedAtWall1("SELECT * FROM (SELECT * FROM preise WHERE id IN "
                                  "(UPDATE preise SET x = 1 RETURNING id)) t")

    def test_other_admin_statements(self):
        for sql in ("DO $$ BEGIN PERFORM 1; END $$", "VACUUM preise", "LOCK TABLE preise",
                    "CALL foo()", "TRUNCATE preise", "GRANT ALL ON preise TO PUBLIC",
                    "REVOKE SELECT ON preise FROM grader_ro", "CREATE TABLE t AS SELECT * FROM preise",
                    "ALTER TABLE preise ADD COLUMN x int", "INSERT INTO preise SELECT * FROM preise",
                    "UPDATE preise SET mwh = 0", "DELETE FROM preise", "EXPLAIN SELECT * FROM preise",
                    "BEGIN", "COMMIT", "SHOW ALL", "VALUES (1)"):
            with self.subTest(sql=sql):
                self.assertBlockedAtWall1(sql)

    def test_select_for_update(self):
        self.assertBlockedAtWall1("SELECT * FROM erzeugung FOR UPDATE", "Lock")

    def test_function_deny_list(self):
        for fn in ("pg_sleep_for('1 minute')", "pg_ls_dir('/')", "pg_read_binary_file('/etc/passwd')",
                   "lo_import('/etc/passwd')", "lo_export(1, '/tmp/x')", "dblink('host=x', 'select 1')",
                   "dblink_exec('host=x', 'drop table x')", "set_config('role', 'postgres', false)",
                   "current_setting('server_version')", "pg_terminate_backend(1)", "pg_cancel_backend(1)",
                   "pg_reload_conf()", "txid_current()", "pg_backend_pid()",
                   "query_to_xml('select * from pg_user', true, true, '')"):
            with self.subTest(fn=fn):
                self.assertBlockedAtWall1(f"SELECT {fn} FROM erzeugung")

    def test_function_name_tricks(self):
        self.assertBlockedAtWall1("SELECT pg_catalog.pg_sleep(1) FROM preise", "pg_sleep")   # schema-qualified
        self.assertBlockedAtWall1('SELECT "PG_SLEEP"(1) FROM preise', "pg_sleep")             # quoted, upper case
        self.assertBlockedAtWall1("SELECT * FROM pg_sleep(1), preise", "pg_sleep")           # in FROM
        self.assertBlockedAtWall1("SELECT * FROM erzeugung WHERE zeitpunkt IN "
                                  "(SELECT pg_sleep(1))", "pg_sleep")                       # in a subquery

    def test_cte_named_like_catalog_table(self):
        self.assertBlockedAtWall1("WITH pg_user AS (SELECT 1 FROM erzeugung) SELECT * FROM pg_user", "pg_user")

    def test_other_schema_or_database(self):
        self.assertBlockedAtWall1("SELECT * FROM other.erzeugung")
        self.assertBlockedAtWall1("SELECT * FROM smard.public.erzeugung")

    def test_table_not_in_the_three(self):
        self.assertBlockedAtWall1("SELECT * FROM users", "users")
        self.assertBlockedAtWall1("SELECT * FROM erzeugung JOIN secrets USING (id)", "secrets")

    def test_empty_and_garbage(self):
        for sql in ("", "   ", ";", "SELEKT * FROM preise", "SELECT * FROM", "-- just a comment", None):
            with self.subTest(sql=sql):
                self.assertBlockedAtWall1(sql)


class TestWall1Allows(unittest.TestCase):
    """What must NOT be blocked: ordinary data queries."""

    def test_allowed_shapes(self):
        for sql in (
            "SELECT 1 FROM erzeugung LIMIT 1",
            "SELECT count(*) FROM erzeugung;",                       # trailing semicolon
            "SELECT count(*) FROM erzeugung;\n  ",                   # trailing semicolon and spaces
            "SELECT count(*) FROM public.erzeugung",
            "SELECT count(*) -- comment inside\nFROM erzeugung",
            "WITH x AS (SELECT * FROM erzeugung) SELECT count(*) FROM x",
            "SELECT 1 FROM erzeugung UNION ALL SELECT 1 FROM preise",
            "SELECT * FROM erzeugung e JOIN preise p ON p.zeitpunkt = e.zeitpunkt",
            "SELECT * FROM (SELECT zeitpunkt FROM verbrauch) v",
            "SELECT date_trunc('month', zeitpunkt), avg(mwh) FROM erzeugung GROUP BY 1",
            "SELECT * FROM erzeugung WHERE zeitpunkt > (SELECT max(zeitpunkt) FROM preise)",
        ):
            with self.subTest(sql=sql):
                self.assertIsNone(check_static(sql), check_static(sql))

    def test_every_gold_query_passes_wall_1(self):
        for q in load_questions():
            if q.gold_sql:
                with self.subTest(id=q.id):
                    self.assertIsNone(check_static(q.gold_sql), check_static(q.gold_sql))


class TestWalls2And3(unittest.TestCase):
    def test_cross_join_is_blocked_by_plan_cost(self):
        res = safe_execute("SELECT a.zeitpunkt FROM erzeugung a CROSS JOIN erzeugung b", LIMITS)
        self.assertTrue(res.blocked)
        self.assertIn(res.wall, (2, 3))      # wall 2 in practice; wall 3 would also stop it
        self.assertEqual(res.wall, 2)
        self.assertEqual(res.kind, "plan_cost")
        self.assertGreater(res.plan_cost, LIMITS.max_plan_cost)

    def test_more_than_max_rows_is_too_many_rows(self):
        res = safe_execute("SELECT zeitpunkt FROM erzeugung", LIMITS)  # ~23000 rows, limit 20000
        self.assertTrue(res.blocked)
        self.assertEqual((res.wall, res.kind), (3, "too_many_rows"))
        self.assertIn("too_many_rows", res.reason)
        self.assertIsNone(res.rows)

    def test_row_cap_with_small_limit_fetches_one_row_more(self):
        small = Limits(max_plan_cost=LIMITS.max_plan_cost, max_rows=5, timeout_ms=LIMITS.timeout_ms)
        self.assertEqual(safe_execute("SELECT zeitpunkt FROM erzeugung LIMIT 5", small).n_rows, 5)
        res = safe_execute("SELECT zeitpunkt FROM erzeugung LIMIT 6", small)
        self.assertEqual((res.blocked, res.wall, res.kind), (True, 3, "too_many_rows"))

    def test_timeout_is_a_block(self):
        tiny = Limits(max_plan_cost=LIMITS.max_plan_cost, max_rows=LIMITS.max_rows, timeout_ms=1)
        res = safe_execute("SELECT count(*) FROM erzeugung a JOIN erzeugung b "
                           "ON a.zeitpunkt = b.zeitpunkt JOIN erzeugung c ON c.zeitpunkt = a.zeitpunkt", tiny)
        self.assertTrue(res.blocked)
        self.assertEqual(res.kind, "timeout")
        self.assertIn(res.wall, (2, 3))

    def test_normal_gold_query_passes(self):
        q = next(q for q in load_questions() if q.gold_sql)
        res = safe_execute(q.gold_sql, LIMITS)
        self.assertFalse(res.blocked, res.reason)
        self.assertIsNotNone(res.rows)
        self.assertEqual(res.n_rows, len(res.rows))
        self.assertIsNotNone(res.plan_cost)

    def test_postgres_error_is_a_query_error_not_a_block(self):
        with self.assertRaises(QueryError) as ctx:
            safe_execute("SELECT mwhh FROM erzeugung", LIMITS)
        self.assertEqual(agent_loop.format_pg_error(ctx.exception).splitlines()[0],
                         'column "mwhh" does not exist')

    def test_connection_is_read_only(self):
        conn = safe_runner.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SHOW transaction_read_only")
                self.assertEqual(cur.fetchone()[0], "on")
                with self.assertRaises(Exception):
                    cur.execute("CREATE TEMP TABLE t (x int)")   # wall 1 bypassed on purpose
        finally:
            conn.rollback()
            conn.close()

    def test_precheck_does_not_run_the_query(self):
        res = safe_runner.precheck("SELECT count(*) FROM erzeugung", LIMITS)
        self.assertFalse(res.blocked)
        self.assertIsNone(res.rows)
        self.assertIsNotNone(res.plan_cost)

    def test_no_fetchall_in_the_runner(self):
        text = (Path(safe_runner.__file__)).read_text(encoding="utf-8")
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(("#", '"""')))
        self.assertNotIn(".fetchall(", code)

    def test_all_gold_queries_pass_all_walls(self):
        rep = safe_runner.check_gold_against_limits(LIMITS)
        self.assertEqual(rep["failures"], [])
        self.assertEqual(rep["n_pass"], rep["n"])
        self.assertEqual(rep["n"], 76)

    def test_limits_file(self):
        lim = load_limits()
        self.assertEqual(lim.timeout_ms, 30000)
        self.assertEqual(lim.max_rows, 20000)
        self.assertGreater(lim.max_plan_cost, 0)


# ------------------------------------------------------------------ the loop switch

class FakeModel:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(copy.deepcopy(messages))
        if len(self.calls) > len(self.replies):
            raise AssertionError("the loop called the model more often than expected")
        return {"raw_model_output": self.replies[len(self.calls) - 1],
                "prompt_tokens": 100, "completion_tokens": 10, "latency_seconds": 0.5}


GOOD = "SELECT count(*) FROM erzeugung"
BLOCKED_TEXT = ("This query was blocked: function pg_sleep is not allowed\n"
                "Write a corrected query. Return only the SQL.")


class TestLoopSwitch(unittest.TestCase):
    def test_switch_exists_and_defaults_off(self):
        self.assertIn("safe_runner", agent_loop.SWITCH_NAMES)
        self.assertFalse(agent_loop.DEFAULT_SWITCHES["safe_runner"])

    def test_block_is_retried_like_an_error_with_the_exact_message(self):
        model = FakeModel(["SELECT pg_sleep(1) FROM erzeugung", GOOD])
        rec = agent_loop.run_question("q", {"error_retry": True, "safe_runner": True}, llm=model)
        self.assertEqual(rec["n_attempts"], 2)
        self.assertEqual(model.calls[1][-1], {"role": "user", "content": BLOCKED_TEXT})
        self.assertEqual(model.calls[1][-2]["role"], "assistant")
        a1, a2 = rec["attempts"]
        self.assertEqual((a1["blocked"], a1["wall"]), (True, 1))
        self.assertEqual(a1["reason"], "function pg_sleep is not allowed")
        self.assertEqual(a1["check_fired"], "error")
        self.assertEqual((a2["blocked"], a2["wall"], a2["reason"]), (False, None, None))
        self.assertTrue(rec["crashed_on_attempt_1"])
        self.assertTrue(rec["retried_after_error"])
        self.assertEqual(rec["final_sql"], GOOD)
        self.assertFalse(rec["cap_hit"])

    def test_postgres_error_still_uses_the_postgres_message(self):
        model = FakeModel(["SELECT mwhh FROM erzeugung", GOOD])
        rec = agent_loop.run_question("q", {"error_retry": True, "safe_runner": True}, llm=model)
        self.assertTrue(model.calls[1][-1]["content"].startswith(
            "This query failed with the following error from PostgreSQL:\ncolumn \"mwhh\" does not exist"))
        self.assertEqual(rec["attempts"][0]["blocked"], False)

    def test_blocked_every_time_hits_the_cap(self):
        bad = "SELECT * FROM pg_catalog.pg_user"
        model = FakeModel([bad, bad, bad])
        rec = agent_loop.run_question("q", {"error_retry": True, "safe_runner": True}, llm=model)
        self.assertEqual(rec["n_attempts"], 3)
        self.assertTrue(rec["cap_hit"])
        self.assertTrue(all(a["blocked"] for a in rec["attempts"]))

    def test_block_without_error_retry_is_not_retried(self):
        model = FakeModel(["SELECT 0"])
        rec = agent_loop.run_question("q", {"error_retry": False, "safe_runner": True}, llm=model)
        self.assertEqual(rec["n_attempts"], 1)
        self.assertTrue(rec["attempts"][0]["blocked"])

    def test_decline_is_not_a_block(self):
        model = FakeModel(["NO_QUERY: not in the data"])
        rec = agent_loop.run_question("q", {"error_retry": True, "safe_runner": True}, llm=model)
        self.assertTrue(rec["declined"])
        self.assertEqual(rec["attempts"][0]["blocked"], False)

    def test_injected_safe_execute_is_used(self):
        seen = []

        def fake_safe(sql):
            seen.append(sql)
            return SafeResult(blocked=True, wall=2, kind="plan_cost", reason="plan_cost: too big")

        model = FakeModel(["SELECT 1 FROM erzeugung", GOOD])
        rec = agent_loop.run_question("q", {"error_retry": True, "safe_runner": True}, llm=model,
                                      safe_execute=lambda s: fake_safe(s) if len(seen) == 0 else
                                      SafeResult(blocked=False, rows=[(1,)], n_rows=1))
        self.assertEqual(seen, ["SELECT 1 FROM erzeugung"])
        self.assertEqual(model.calls[1][-1]["content"],
                         "This query was blocked: plan_cost: too big\nWrite a corrected query. Return only the SQL.")
        self.assertEqual(rec["attempts"][0]["wall"], 2)

    def test_switch_off_leaves_records_unchanged(self):
        """With the switch off the attempt records have exactly the old keys, and the old
        run_query path is used even for a query the walls would block."""
        model = FakeModel(["SELECT 0", GOOD])
        calls = []

        def execute(sql):
            calls.append(sql)
            return [(1,)]

        rec = agent_loop.run_question("q", {"error_retry": True}, llm=model, execute=execute)
        self.assertEqual(calls, ["SELECT 0"])
        self.assertEqual(rec["n_attempts"], 1)
        for key in ("blocked", "wall", "reason"):
            self.assertNotIn(key, rec["attempts"][0])

    def test_a_blocked_query_is_never_executed_by_the_old_path(self):
        executed = []
        model = FakeModel(["SELECT pg_sleep(1) FROM erzeugung", GOOD])
        agent_loop.run_question("q", {"error_retry": True, "safe_runner": True}, llm=model,
                                execute=lambda sql: executed.append(sql) or [(1,)])
        self.assertEqual(executed, [])   # every query went through safe_execute instead


if __name__ == "__main__":
    unittest.main()
