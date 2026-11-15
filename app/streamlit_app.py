"""
The Streamlit page (D44, step 3c).   streamlit run app/streamlit_app.py   (from the project folder)

The page only draws. The logic lives in answer.py (answer_question, sql_to_show), summary.py
(summarize), format.py, charts.py (pick_chart) and units.py (unit_for_columns, header_names).
Answers are kept in st.session_state under the question text, so a rerun (opening an expander,
a download, typing in the box) never calls the model again. Only the Ask button does.
"""

import sys
import uuid
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
import yaml  # noqa: E402

import answer  # noqa: E402
import summary  # noqa: E402
import tracing  # noqa: E402
from charts import pick_chart  # noqa: E402
from format import format_cell, format_table, to_csv  # noqa: E402
from units import header_names, unit_for_columns  # noqa: E402

INTRO = ("An AI writes SQL, the SQL runs behind four safety checks, and you see everything it did. "
         "On the development exam this setup was right about 7 to 8 times out of 10, so check the SQL.")
SUMMARY_LABEL = "AI summary (every number checked against the table)"
FOOTER_TIME = "Times are German local time. On the autumn clock-change days one hour appears twice in the data."
FOOTER_SOURCE = "Data source: Bundesnetzagentur | SMARD.de"


def load_examples() -> list[dict]:
    return yaml.safe_load((APP_DIR / "examples.yaml").read_text(encoding="utf-8"))["examples"]


def set_question(text: str) -> None:
    st.session_state["question_text"] = text


@st.cache_resource
def process_tracer():
    """One tracer per app process (D45): Langfuse if the three LANGFUSE_* variables are set, else off."""
    return tracing.get_tracer()


FEEDBACK_STATUSES = ("answered", "declined_model", "declined_system")
SCORE_NAME = "user_says_correct"


def save_feedback(trace_id, value: int) -> None:
    """Button callback: save the score on the trace. Never calls the model."""
    tracer = process_tracer()
    saved = bool(tracer.score(trace_id, SCORE_NAME, value))
    if saved:
        tracer.flush()
    st.session_state["feedback"][trace_id] = "saved" if saved else "not saved"


def draw_feedback(result) -> None:
    if result.status not in FEEDBACK_STATUSES:
        return
    tracer = process_tracer()
    trace_id = result.trace_id
    state = st.session_state["feedback"].get(trace_id) if trace_id else None
    if state == "saved":
        st.caption("Thanks, saved.")
        return
    if state == "not saved":
        st.caption("Not saved: tracing is off.")
        return
    st.markdown("**Was this answer right?**")
    off = (not tracer.enabled) or trace_id is None
    yes, no, _ = st.columns([1, 1, 6])
    key = trace_id or f"none_{abs(hash(result.question))}"
    yes.button("Yes", key=f"fb_yes_{key}", disabled=off, on_click=save_feedback, args=(trace_id, 1))
    no.button("No", key=f"fb_no_{key}", disabled=off, on_click=save_feedback, args=(trace_id, 0))
    if off:
        st.caption("tracing off")


def money(x: float) -> str:
    return f"${x:.5f}"


# ---------------------------------------------------------------- drawing

def draw_status(result) -> None:
    if result.status == "answered":
        if result.rewritten_after_empty:
            st.warning(result.message)
    elif result.status in ("no_rows", "declined_system", "declined_model"):
        st.info(result.message)
    else:  # blocked, error
        st.error(result.message)


def draw_summary(summ) -> None:
    if summ is not None and summ.shown:
        st.markdown(f"**{SUMMARY_LABEL}**")
        st.write(summ.text)


def draw_chart(kind, details, columns, rows, units) -> None:
    if kind == "metric":
        unit = units[0]
        value = format_cell(details["value"]) + (f" {unit}" if unit else "")
        st.metric(label=details["label"], value=value)
    elif kind == "line":
        fig = go.Figure()
        for name, i in zip(details["y"], details["y_indexes"]):
            label = f"{name} ({units[i]})" if units[i] else name
            fig.add_trace(go.Scatter(x=[r[details["x_index"]] for r in rows],
                                     y=[None if r[i] is None else float(r[i]) for r in rows],
                                     mode="lines+markers", name=label))
        shared = {units[i] for i in details["y_indexes"]}
        fig.update_layout(xaxis_title=details["x"], yaxis_title=shared.pop() if len(shared) == 1 and None not in shared else None,
                          showlegend=len(details["y"]) > 1, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")
    elif kind == "bar":
        i = details["y_index"]
        fig = go.Figure(go.Bar(x=[str(r[details["x_index"]]) for r in rows],
                               y=[None if r[i] is None else float(r[i]) for r in rows]))
        # a category axis keeps the rows in the SQL's order (never sorted by the chart)
        fig.update_layout(xaxis_title=details["x"], yaxis_title=units[i], xaxis_type="category",
                          margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")


def draw_table(result, headers) -> None:
    if not result.rows:
        return
    formatted = format_table(result.columns, result.rows)
    st.dataframe([dict(zip(headers, row)) for row in formatted], hide_index=True, width="stretch")
    st.caption(f"{result.row_count} row" + ("" if result.row_count == 1 else "s"))
    st.download_button("Download CSV (raw values)", to_csv(headers, result.rows).encode("utf-8"),
                       file_name="result.csv", mime="text/csv", on_click="ignore")


def draw_behind_the_scenes(result, summ) -> None:
    with st.expander("Behind the scenes"):
        st.markdown("**Tracing**")
        st.write(f"{result.tracing_status}. Trace id: {result.trace_id or 'none'}")
        st.markdown("**Attempts**")
        for a in result.attempts:
            line = f"Attempt {a.number}: {a.outcome}"
            if a.reason:
                line += f" — {a.reason}"
            if a.wall is not None:
                line += f" (wall {a.wall})"
            if a.row_count is not None:
                line += f" — {a.row_count} row" + ("" if a.row_count == 1 else "s")
            st.markdown(line)
            if a.sql:
                st.code(a.sql, language="sql")
        st.markdown("**AI summary**")
        if summ is None:
            st.write("Not made.")
        elif summ.shown:
            st.write("Shown.")
        else:
            st.write(f"Hidden: {summ.hidden_reason}")
            if summ.unknown_numbers:
                st.write("Not found in the table or the question: " + ", ".join(str(n) for n in summ.unknown_numbers))
        st.markdown("**Time, tokens, cost**")
        st.write(f"Time: {result.seconds_total:.2f} s in total, {result.seconds_model:.2f} s of it in the model.")
        s_prompt, s_completion, s_cost = ((summ.prompt_tokens, summ.completion_tokens, summ.cost_usd)
                                          if summ is not None else (0, 0, 0.0))
        st.write(f"Answer: {result.prompt_tokens} prompt + {result.completion_tokens} completion tokens, "
                 f"{money(result.cost_usd)}")
        st.write(f"Summary: {s_prompt} prompt + {s_completion} completion tokens, {money(s_cost)}")
        st.write(f"Total: {result.prompt_tokens + s_prompt} prompt + {result.completion_tokens + s_completion} "
                 f"completion tokens, {money(result.cost_usd + s_cost)}")
        st.markdown("**Model**")
        st.write(f"{result.model} (system fingerprint: {result.system_fingerprint})")


def draw_result(result, summ) -> None:
    draw_status(result)
    draw_summary(summ)
    units = unit_for_columns(result.final_sql) if result.final_sql else None
    if units is None or len(units) != len(result.columns):
        units = [None] * len(result.columns)
    if result.status == "answered":
        kind, details = pick_chart(result.columns, result.rows)
        draw_chart(kind, details, result.columns, result.rows, units)
    if result.status in ("answered", "no_rows"):
        draw_table(result, header_names(result.columns, units))
    sql = answer.sql_to_show(result)
    if sql:
        st.markdown("**SQL**")
        st.code(sql, language="sql")
    draw_feedback(result)
    draw_behind_the_scenes(result, summ)


# ---------------------------------------------------------------- the page

st.set_page_config(page_title="SMARD question answering", layout="centered")
st.title("Ask the German electricity data (SMARD)")
st.write(INTRO)

st.session_state.setdefault("question_text", "")
st.session_state.setdefault("answers", {})  # question text -> (AnswerResult, Summary)
st.session_state.setdefault("shown_question", None)
st.session_state.setdefault("feedback", {})                        # trace id -> "saved" | "not saved"
st.session_state.setdefault("session_id", str(uuid.uuid4()))       # one per browser tab (D45)

examples = load_examples()
columns = st.columns(3)
for n, ex in enumerate(examples):
    with columns[n % 3]:
        st.button(ex["label"], key=f"example_{ex['id']}", help=ex["question"],
                  on_click=set_question, args=(ex["question"],), width="stretch")

st.text_area("Your question", key="question_text", height=80)
asked = st.button("Ask", type="primary")

if asked:
    question = st.session_state["question_text"].strip()
    if not question:
        st.warning("Type a question first.")
    else:
        try:
            with st.spinner("Writing and checking the SQL ..."):
                tracer = process_tracer()
                result = answer.answer_question(question, tracer=tracer, session_id=st.session_state["session_id"])
                summ = summary.summarize(result, tracer=tracer)
            st.session_state["answers"][question] = (result, summ)
            st.session_state["shown_question"] = question
        except Exception as exc:  # no database, no API key, network error: say so, do not crash
            st.session_state["shown_question"] = None
            st.error(f"Something went wrong before an answer could be made ({type(exc).__name__}): {exc}")

shown = st.session_state["shown_question"]
if shown is not None and shown in st.session_state["answers"]:
    st.divider()
    st.subheader(shown)
    draw_result(*st.session_state["answers"][shown])

st.divider()
st.caption(FOOTER_TIME)
st.caption(FOOTER_SOURCE)
