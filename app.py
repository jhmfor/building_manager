import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client

st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (Pro)")

# 1. Supabase 클라우드 연결 설정 (기존과 동일)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 2. 데이터 불러오기 함수들
def load_contracts():
    try:
        res = supabase.table("contracts").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

def load_expenses():
    try:
        res = supabase.table("expenses").select("*").execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            # 화면 표시를 위해 컬럼명 변경
            rename_map = {"building_name": "건물명", "category": "호실", "expense_date": "날짜", "description": "내역", "amount": "비용"}
            df = df.rename(columns=rename_map)
        return df
    except: return pd.DataFrame()

contracts_df = load_contracts()
expenses_df = load_expenses()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📋 임대 계약 및 관리", "💰 지출 및 공사 장부", "📁 지난 계약 및 매매 관리"])

with tab1:
    st.subheader("➕ 새로운 임대 계약 등록")
    with st.form("contract_add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        c_bname = col1.text_input("건물명")
        c_rname = col2.text_input("호실")
        c_tenant = col1.text_input("임차인 성함")
        c_deposit = col2.text_input("보증금(원)")
        c_rent = col1.text_input("월세(원)")
        
        if st.form_submit_button("계약 정보 저장"):
            supabase.table("contracts").insert({
                "building_name": c_bname, "room_number": c_rname, 
                "tenant_name": c_tenant, "deposit_amount": c_deposit, "monthly_rent": c_rent
            }).execute()
            st.success("저장 완료!")
            st.rerun()

    st.markdown("---")
    st.subheader("현재 계약 목록")
    st.dataframe(contracts_df, use_container_width=True)

with tab2:
    st.subheader("💰 지출 및 공사 장부")
    
    # 💵 총 지출 합산 표시
    if not expenses_df.empty and "비용" in expenses_df.columns:
        # 문자열로 변환 후 숫자만 추출하여 합산
        numeric_costs = expenses_df["비용"].astype(str).str.replace(r'[^\d]', '', regex=True)
        total_cost = pd.to_numeric(numeric_costs, errors='coerce').sum()
        st.markdown(f"### 📊 총 지출 비용: {total_cost:,.0f} 원")
        
        # 엑셀식 데이터프레임 출력 (중복 카드 삭제 완료)
        st.dataframe(expenses_df, use_container_width=True, hide_index=True)
    else:
        st.info("지출 내역이 없습니다.")

    st.markdown("---")
    st.subheader("➕ 새로운 지출 내역 등록")
    with st.form("expense_add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        ex_bname = col1.text_input("건물명")
        ex_rname = col2.text_input("호실")
        ex_date = col1.date_input("날짜", value=datetime.today())
        ex_desc = col2.text_input("내용")
        ex_amount = st.text_input("비용(원)")
        
        if st.form_submit_button("지출 내역 저장"):
            supabase.table("expenses").insert({
                "building_name": ex_bname, "category": ex_rname, 
                "expense_date": str(ex_date), "description": ex_desc, "amount": ex_amount
            }).execute()
            st.success("저장 완료!")
            st.rerun()

with tab3:
    st.write("지난 계약 및 매매 관리 화면입니다.")
