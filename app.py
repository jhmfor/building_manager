import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client
import re

# 페이지 설정
st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (Simple & Fast)")
st.markdown("엑셀처럼 표에서 바로 수정하고, 체크해서 간편하게 삭제하세요!")

# 숫자 콤마 포맷팅 함수
def format_currency(value):
    try:
        clean_val = re.sub(r'[^\d]', '', str(value))
        return f"{int(clean_val):,}" if clean_val else "0"
    except:
        return str(value)

# Supabase 연결
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 데이터 로드 함수들
def load_contracts():
    res = supabase.table("contracts").select("*").execute()
    data = res.data
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    return df.rename(columns={
        "building_name": "건물명", "room_number": "호실", "tenant_name": "임차인", 
        "tenant_phone": "임차인연락처", "agency_name": "부동산명", "agency_phone": "부동산연락처", 
        "deposit_amount": "보증금", "monthly_rent": "월세", "pay_day": "납부일", 
        "start_date": "계약일", "end_date": "만료일", "special_notes": "특약사항", "status": "상태"
    })

def load_expenses():
    res = supabase.table("expenses").select("*").execute()
    data = res.data
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    return df.rename(columns={
        "expense_date": "날짜", "building_name": "건물명", "room_number": "호실",
        "category": "카테고리", "description": "내역", "amount": "비용"
    })

def load_history():
    res = supabase.table("history").select("*").execute()
    data = res.data
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    return df.rename(columns={
        "building_name": "건물명", "room_number": "호실", "contract_period": "계약기간", 
        "deposit": "보증금", "rent": "월세", "purchase_price": "매수가", "sale_price": "매도가"
    })

tab1, tab2, tab3 = st.tabs(["📋 임대 계약 관리", "💰 지출 장부", "📁 지난 계약·매매"])

# ==========================================
# [1페이지] 임대 계약 관리 (직관적 표 수정/삭제)
# ==========================================
with tab1:
    st.subheader("📋 임대 계약 현황 (표에서 직접 수정 가능)")
    df_c = load_contracts()
    
    if not df_c.empty:
        # st.data_editor를 이용해 표 안에서 직접 수정 가능하도록 제공
        edited_c_df = st.data_editor(
            df_c, 
            key="contract_editor", 
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 계약 수정 사항 클라우드에 일괄 저장", type="primary"):
                # 변경된 데이터 전체를 순회하며 Supabase 업데이트
                for _, row in edited_c_df.iterrows():
                    row_id = row.get("id")
                    if row_id:
                        supabase.table("contracts").update({
                            "building_name": str(row.get("건물명", "")),
                            "room_number": str(row.get("호실", "")),
                            "tenant_name": str(row.get("임차인", "")),
                            "tenant_phone": str(row.get("임차인연락처", "")),
                            "agency_name": str(row.get("부동산명", "")),
                            "agency_phone": str(row.get("부동산연락처", "")),
                            "deposit_amount": str(row.get("보증금", "")),
                            "monthly_rent": str(row.get("월세", "")),
                            "pay_day": str(row.get("납부일", "")),
                            "start_date": str(row.get("계약일", "")),
                            "end_date": str(row.get("만료일", "")),
                            "special_notes": str(row.get("특약사항", ""))
                        }).eq("id", row_id).execute()
                st.success("수정 사항이 클라우드에 반영되었습니다!")
                st.rerun()
                
        with col_s2:
            del_c_id = st.text_input("삭제할 계약의 ID 입력", placeholder="삭제할 항목의 id 번호 입력")
            if st.button("🗑️ 해당 ID 계약 삭제"):
                if del_c_id:
                    supabase.table("contracts").delete().eq("id", int(del_c_id)).execute()
                    st.warning(f"ID {del_c_id} 계약이 삭제되었습니다.")
                    st.rerun()
    else:
        st.info("등록된 계약 정보가 없습니다.")
        
    st.markdown("---")
    with st.expander("➕ 신규 계약 추가하기"):
        with st.form("new_c_form"):
            nb = st.text_input("건물명")
            nr = st.text_input("호실")
            nt = st.text_input("임차인")
            ntp = st.text_input("연락처")
            nd = st.text_input("보증금", "10000000")
            nrt = st.text_input("월세", "500000")
            if st.form_submit_button("추가 저장"):
                supabase.table("contracts").insert({
                    "building_name": nb, "room_number": nr, "tenant_name": nt,
                    "tenant_phone": ntp, "deposit_amount": nd, "monthly_rent": nrt, "status": "계약중"
                }).execute()
                st.success("추가되었습니다!")
                st.rerun()

# ==========================================
# [2페이지] 지출 장부 (표 형태 수정/삭제)
# ==========================================
with tab2:
    st.subheader("💰 지출 및 공사 장부")
    df_e = load_expenses()
    
    if not df_e.empty:
        edited_e_df = st.data_editor(
            df_e, 
            key="expense_editor", 
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
        
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            if st.button("💾 지출 수정 사항 일괄 저장", type="primary"):
                for _, row in edited_e_df.iterrows():
                    row_id = row.get("id")
                    if row_id:
                        supabase.table("expenses").update({
                            "building_name": str(row.get("건물명", "")),
                            "room_number": str(row.get("호실", "")),
                            "category": str(row.get("카테고리", "기타")),
                            "description": str(row.get("내역", "")),
                            "amount": str(row.get("비용", "0")),
                            "expense_date": str(row.get("날짜", ""))
                        }).eq("id", row_id).execute()
                st.success("지출 장부가 수정되었습니다!")
                st.rerun()
                
        with col_e2:
            del_e_id = st.text_input("삭제할 지출 ID 입력", placeholder="삭제할 항목의 id 번호 입력", key="del_e_input")
            if st.button("🗑️ 해당 ID 지출 삭제"):
                if del_e_id:
                    supabase.table("expenses").delete().eq("id", int(del_e_id)).execute()
                    st.warning(f"ID {del_e_id} 지출이 삭제되었습니다.")
                    st.rerun()
    else:
        st.info("지출 내역이 없습니다.")
        
    st.markdown("---")
    with st.expander("➕ 신규 지출 추가하기"):
        with st.form("new_e_form"):
            eb = st.text_input("건물명", key="ne_b")
            er = st.text_input("호실", key="ne_r")
            ec = st.selectbox("카테고리", ["수리비", "공사비", "세금", "중개수수료", "기타"])
            ed = st.text_input("내역", key="ne_d")
            ea = st.text_input("비용", "100000", key="ne_a")
            if st.form_submit_button("지출 추가"):
                supabase.table("expenses").insert({
                    "building_name": eb, "room_number": er, "category": ec,
                    "description": ed, "amount": ea, "expense_date": str(datetime.today().date())
                }).execute()
                st.success("추가되었습니다!")
                st.rerun()

# ==========================================
# [3페이지] 지난 계약 및 매매 (표 형태 수정/삭제)
# ==========================================
with tab3:
    st.subheader("📁 지난 계약 및 매매 이력")
    df_h = load_history()
    
    if not df_h.empty:
        edited_h_df = st.data_editor(
            df_h, 
            key="history_editor", 
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )
        
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            if st.button("💾 이력 수정 사항 일괄 저장", type="primary"):
                for _, row in edited_h_df.iterrows():
                    row_id = row.get("id")
                    if row_id:
                        supabase.table("history").update({
                            "building_name": str(row.get("건물명", "")),
                            "room_number": str(row.get("호실", "")),
                            "contract_period": str(row.get("계약기간", "")),
                            "deposit": str(row.get("보증금", "")),
                            "rent": str(row.get("월세", "")),
                            "purchase_price": str(row.get("매수가", "")),
                            "sale_price": str(row.get("매도가", ""))
                        }).eq("id", row_id).execute()
                st.success("이력이 수정되었습니다!")
                st.rerun()
                
        with col_h2:
            del_h_id = st.text_input("삭제할 이력 ID 입력", placeholder="삭제할 항목의 id 번호 입력", key="del_h_input")
            if st.button("🗑️ 해당 ID 이력 삭제"):
                if del_h_id:
                    supabase.table("history").delete().eq("id", int(del_h_id)).execute()
                    st.warning(f"ID {del_h_id} 이력이 삭제되었습니다.")
                    st.rerun()
    else:
        st.info("이력 장부가 비어 있습니다.")
