"""insight-engine dashboard.

Run from repo root:  streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import desc

from app.db import SessionLocal, init_db
from app.models import Brief, Feedback, Theme
from scripts.load_sample_data import load_sample_data

st.set_page_config(page_title="insight-engine", page_icon="🔍", layout="wide")
init_db()
session = SessionLocal()

st.title("🔍 insight-engine — Voice of Customer")

themes = session.query(Theme).order_by(desc(Theme.size)).all()
if not themes:
    with st.spinner("First run — ingesting sample feedback and building themes (ingest → cluster → score → brief)..."):
        load_sample_data(session)
    themes = session.query(Theme).order_by(desc(Theme.size)).all()

if not themes:
    st.error("Pipeline ran but produced no themes — check the app logs.")
    st.stop()

# ---- KPI row ----
records_total = session.query(Feedback).count()
fix_count = sum(1 for t in themes if t.suggested_action == "fix")
avg_sent = sum(t.avg_sentiment * t.size for t in themes) / max(1, sum(t.size for t in themes))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Feedback records", records_total)
c2.metric("Themes", len(themes))
c3.metric("Needs fix", fix_count)
c4.metric("Weighted sentiment", f"{avg_sent:+.2f}")

# ---- Theme overview ----
df = pd.DataFrame([{
    "Theme": t.label,
    "Size": t.size,
    "Sentiment": t.avg_sentiment,
    "Urgency": t.avg_urgency,
    "Action": t.suggested_action,
} for t in themes])

left, right = st.columns([3, 2])
with left:
    st.subheader("Themes by size and sentiment")
    fig = px.bar(
        df, x="Size", y="Theme", orientation="h", color="Sentiment",
        color_continuous_scale="RdYlGn", range_color=[-1, 1], hover_data=["Urgency", "Action"],
    )
    fig.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("Priority map")
    fig2 = px.scatter(
        df, x="Sentiment", y="Urgency", size="Size", color="Action", text="Theme",
        color_discrete_map={"fix": "#e74c3c", "investigate": "#f39c12", "monitor": "#2ecc71"},
    )
    fig2.update_traces(textposition="top center")
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)

# ---- Drill-down ----
st.subheader("Drill down")
selected = st.selectbox("Theme", [t.label for t in themes])
theme = next(t for t in themes if t.label == selected)
records = (
    session.query(Feedback)
    .filter(Feedback.theme_id == theme.id)
    .order_by(desc(Feedback.urgency))
    .limit(50)
    .all()
)
st.dataframe(
    pd.DataFrame([{
        "id": r.id, "source": r.source, "rating": r.rating,
        "sentiment": r.sentiment, "urgency": r.urgency, "text": r.text,
    } for r in records]),
    use_container_width=True, hide_index=True,
)

# ---- Latest brief ----
st.subheader("Latest Voice-of-Customer brief")
brief = session.query(Brief).order_by(desc(Brief.id)).first()
if brief:
    st.caption(f"Generated via: {brief.generator}")
    st.markdown(brief.content)
else:
    st.info("No brief yet — run the loader script or POST /brief.")

session.close()
