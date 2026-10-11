from pathlib import Path

import pandas as pd
import streamlit as st

from agent import app

st.set_page_config(page_title="Blog Writing Agent", layout="wide")
st.title("Blog Writing Agent")


def open_saved_blog():
    path = st.session_state["picked"]
    st.session_state["out"] = {"final": path.read_text(encoding="utf-8"), "file": path.name}


with st.sidebar:
    topic = st.text_area("Topic", height=100, placeholder="e.g. State of Multimodal LLMs in 2026")
    generate = st.button("Generate blog", type="primary")

    st.divider()
    st.subheader("Saved blogs")
    saved = sorted(Path("blogs").glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    st.selectbox("Open a saved blog", saved, format_func=lambda p: p.stem, index=None,
                 key="picked", on_change=open_saved_blog)

if generate and topic.strip():
    out = {}
    done = 0
    with st.status("Writing your blog...", expanded=True) as status:
        # stream_mode="updates" yields {node_name: what_that_node_returned} after each node
        for update in app.stream({"topic": topic.strip()}, stream_mode="updates"):
            for node, data in update.items():
                if node == "router":
                    st.write(f"Router: `{data['mode']}`, {len(data['queries'])} search queries")
                elif node == "research":
                    st.write(f"Research: {len(data['evidence'])} sources found")
                elif node == "orchestrator":
                    st.write(f"Plan: {len(data['plan'].tasks)} sections")
                elif node == "worker":
                    done += 1
                    st.write(f"Wrote section {done}/{len(out['plan'].tasks)}")
                elif node == "reducer":
                    st.write("Merged and saved")
                out.update(data)
        status.update(label="Blog ready", state="complete", expanded=False)

    title = out["plan"].blog_title
    out["file"] = "".join(c for c in title.lower() if c.isalnum() or c == " ").replace(" ", "_") + ".md"
    st.session_state["out"] = out

out = st.session_state.get("out")
if not out:
    st.info("Enter a topic in the sidebar and click **Generate blog**, or open a saved blog.")
    st.stop()

blog_tab, plan_tab, evidence_tab = st.tabs(["Blog", "Plan", "Evidence"])

with blog_tab:
    st.download_button("Download .md", out["final"], file_name=out["file"], mime="text/markdown")
    st.markdown(out["final"])

with plan_tab:
    plan = out.get("plan")
    if plan:
        st.write(f"**Audience:** {plan.audience}  \n**Tone:** {plan.tone}  \n**Kind:** {plan.blog_kind}")
        tasks = pd.DataFrame([t.model_dump() for t in plan.tasks])
        st.dataframe(tasks[["id", "title", "target_words", "requires_research", "requires_code"]], hide_index=True)
    else:
        st.info("The plan is only shown for blogs generated in this session.")

with evidence_tab:
    evidence = out.get("evidence")
    if evidence:
        st.dataframe(pd.DataFrame([e.model_dump() for e in evidence])[["title", "url"]], hide_index=True,
                     column_config={"url": st.column_config.LinkColumn()})
    else:
        st.info("No web research for this blog (evergreen topic, or a saved blog).")
