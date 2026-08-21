import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client

# 설정
st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (Pro)")

# 1. Supabase 연결 (기존과 동일)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 2. 데이터 불러오기 함수 (기존 구조 완벽 복구)
def load_contracts():
    try:
        res = supabase.table("contracts").select("*").execute()
        data = res.data
        if not data: return pd.DataFrame(columns=["id", "건물명", "호실", "임차인", "임차인연락처", "부동산명", "부동산연락처", "보증금(원)", "월세(원)", "납부일", "계약일", "만료일", "특약사항", "상태"])
        df = pd.DataFrame(data)
        rename_map = {"building_name": "건물명", "room_number": "호실", "tenant_name": "임차인", "tenant_phone": "임차인연락처", "agency_name": "부동산명", "agency_phone": "부동산연락처", "deposit_amount": "보증금(원)", "monthly_rent": "월세(원)", "pay_day": "납부일", "start_date": "계약일", "end_date": "만료일", "special_notes": "특약사항", "status": "상태"}
        return df.rename(columns=rename_map)
    except: return pd.DataFrame()

def load_expenses():
    try:
        res = supabase.table("expenses").select("*").execute()
        data = res.data
        if not data: return pd.DataFrame(columns=["id", "건물명", "호실", "날짜", "내역", "비용"])
        df = pd.DataFrame(data)
        rename_map = {"building_name": "건물명", "category": "호실", "expense_date": "날짜", "description": "내역", "amount": "비용"}
        return df.rename(columns=rename_map)
    except: return pd.DataFrame()

def load_history():
    try:
        res = supabase.table("history").select("*").execute()
        data = res.data
        if not data: return pd.DataFrame(columns=["건물명", "호실", "계약기간", "보증금", "월세", "매수가(원)", "매도가(원)"])
        df = pd.DataFrame(data)
        rename_map = {"building_name": "건물명", "room_number": "호실", "contract_period": "계약기간", "deposit": "보증금", "rent": "월세", "purchase_price": "매수가(원)", "sale_price": "매도가(원)"}
        return df.rename(columns=rename_map)
    except: return pd.DataFrame()

# 데이터 로드
contracts_df = load_contracts()
expenses_df = load_expenses()
history_df = load_history()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📋 임대 계약 및 관리", "💰 지출 및 공사 장부", "📁 지난 계약 및 매매 관리"])

# TAB 1: 계약 관리
with tab1:
    st.subheader("새로운 임대 계약 등록")
    with st.form("contract_add_form", clear_on_submit=True):
        c_bname = st.text_input("건물명")
        c_rname = st.text_input("호실")
        c_tenant = st.text_input("임차인")
        c_deposit = st.text_input("보증금")
        c_rent = st.text_input("월세")
        if st.form_submit_button("등록"):
            supabase.table("contracts").insert({"building_name": c_bname, "room_number": c_rname, "tenant_name": c_tenant, "deposit_amount": c_deposit, "monthly_rent": c_rent}).execute()
            st.rerun()
    st.dataframe(contracts_df, use_container_width=True)

# TAB 2: 지출 장부 (중복 아코디언 제거, 표만 유지)
with tab2:
    st.subheader("지출 내역 요약")
    if not expenses_df.empty:
        st.dataframe(expenses_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.subheader("새로운 지출 내역 등록")
    with st.form("expense_add_form", clear_on_submit=True):
        ex_bname = st.text_input("건물명")
        ex_rname = st.text_input("호실")
        ex_date = st.date_input("날짜")
        ex_desc = st.text_input("내용")
        ex_amount = st.text_input("비용")
        if st.form_submit_button("등록"):
            supabase.table("expenses").insert({"building_name": ex_bname, "category": ex_rname, "expense_date": str(ex_date), "description": ex_desc, "amount": ex_amount}).execute()
            st.rerun()

# TAB 3: 히스토리
with tab3:
    st.subheader("지난 계약 및 매매 이력")
    st.dataframe(history_df, use_container_width=True)
