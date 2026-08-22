import streamlit as st
import pandas as pd
from database import (
    get_all_members, update_deposit_status, 
    get_all_meetings, get_rsvps_for_meeting, get_attendances_for_meeting
)

def render_admin():
    st.subheader("👑 관리자 대시보드")
    st.caption("회원 예치금 승인 및 모임별 출석 관리")

    members = get_all_members()
    meetings = get_all_meetings()

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("전체 회원", f"{len(members)}명")
    with k2:
        st.metric("승인 완료", f"{len([m for m in members if m['deposit_status']=='승인'])}명")
    with k3:
        st.metric("승인 대기", f"{len([m for m in members if m['deposit_status']=='대기'])}명")

    tab1, tab2 = st.tabs(["💰 예치금 입금 승인", "📊 모임별 출석 리스트"])

    with tab1:
        if members:
            for m in members:
                st.markdown(f"**{m['name']}** ({m['phone']}) | 상태: `{m['deposit_status']}`")
                c1, c2 = st.columns(2)
                with c1:
                    if m['deposit_status'] != '승인':
                        if st.button("✅ 입금 승인", key=f"adm_app_{m['id']}", use_container_width=True):
                            update_deposit_status(m['id'], '승인')
                            st.success("승인되었습니다.")
                            st.rerun()
                with c2:
                    if m['deposit_status'] != '차감':
                        if st.button("⚠️ 예치금 차감", key=f"adm_ded_{m['id']}", use_container_width=True):
                            update_deposit_status(m['id'], '차감')
                            st.warning("차감되었습니다.")
                            st.rerun()
                st.markdown("<hr style='margin:8px 0;'/>", unsafe_allow_html=True)
        else:
            st.info("등록된 회원이 없습니다.")

    with tab2:
        if meetings:
            for meeting in meetings:
                st.markdown(f"**📖 [{meeting['meeting_date']}] {meeting['title']}**")
                rsvps = get_rsvps_for_meeting(meeting['id'])
                attendances = get_attendances_for_meeting(meeting['id'])
                att_ids = [a['member_id'] for a in attendances]

                if rsvps:
                    recs = []
                    for r in rsvps:
                        recs.append({
                            "부원 성함": r['member_name'],
                            "출석 여부": "🟢 출석 완료" if r['member_id'] in att_ids else "🔴 미출석"
                        })
                    st.dataframe(pd.DataFrame(recs), use_container_width=True, hide_index=True)
                else:
                    st.caption("신청자가 없습니다.")
                st.markdown("---")
