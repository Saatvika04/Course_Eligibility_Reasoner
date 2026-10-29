import streamlit as st

from explain import explain
from kb_loader import load_kb, detect_prereq_cycles
from reasoning_engine import backward_chain, forward_chain
from visualize import render_backward_svg, render_forward_svg

ALGORITHMS = {"Backward chaining": backward_chain, "Forward chaining": forward_chain}
RENDERERS = {"Backward chaining": render_backward_svg, "Forward chaining": render_forward_svg}


@st.cache_data
def get_kb(path):
    return load_kb(path)


def main():
    st.set_page_config(page_title="CourseLogic 2.0", layout="wide")
    st.title("CourseLogic 2.0 — Explainable Course Eligibility")

    with st.sidebar:
        st.header("Knowledge base")
        kb_path = st.text_input("Path", "data/knowledge_base.json")
        try:
            kb = get_kb(kb_path)
        except (OSError, ValueError) as exc:
            st.error(f"Could not load KB: {exc}")
            st.stop()

        cycles = detect_prereq_cycles(kb)
        if cycles:
            st.warning("Prerequisite cycle:\n" + "\n".join(" -> ".join(c) for c in cycles))

        st.header("Query")
        student = st.selectbox("Student", sorted(kb.get("students", {})))
        course = st.selectbox("Course", sorted(kb.get("courses", {})))

    for name, engine in ALGORITHMS.items():
        result = engine(kb, student, course)
        st.subheader(name)
        verdict = "✅ ELIGIBLE" if result["eligible"] else "❌ NOT ELIGIBLE"
        st.markdown(f"### {verdict}")
        st.text(explain(kb, result))
        svg, width, height = RENDERERS[name](result["graph"])
        st.caption("Inference trace")
        st.components.html(svg, width=width + 30, height=min(height + 30, 1000), scrolling=True)
        with st.expander("Counters"):
            st.write({k: result[k] for k in ("inference_steps", "rules_examined", "derived_facts")})
        with st.expander("Raw trace"):
            st.code("\n".join(result["trace"]))


if __name__ == "__main__":
    main()
