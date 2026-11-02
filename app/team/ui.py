import streamlit as st
from app.team import approval

st.title("Case review")
case_id = st.text_input("Case ID", "case-A-1001")
alert = st.text_area("Alert", "Alert A-1001: three cash deposits in 7 days.")
if st.button("Investigate"):
    with st.spinner("The team is working…"):
        approval.start(case_id, alert)

state = approval.app.get_state(approval.cfg(case_id)).values
if state:
    st.subheader("Steps")
    st.write(" → ".join(state.get("route", [])))
    st.subheader("Narrative")
    st.write(state.get("narrative", ""))
ask = approval.waiting(case_id)
if ask:
    st.warning(f"Approve **{ask['action']['tool']}** with {ask['action']['args']}?")
    reviewer = st.text_input("Reviewer")
    reason = st.text_input("Reason (for a rejection)")
    c1, c2 = st.columns(2)
    if c1.button("Approve", disabled=not reviewer):
        approval.decide(case_id, True, reviewer)
        st.rerun()
    if c2.button("Reject", disabled=not reviewer):
        approval.decide(case_id, False, reviewer, reason)
        st.rerun()
elif state.get("outcome"):
    st.success(state["outcome"])

kill = approval.KILL_SWITCH
if st.sidebar.toggle("Kill switch (no actions execute)", value=kill.exists()):
    kill.touch()
else:
    kill.unlink(missing_ok=True)
