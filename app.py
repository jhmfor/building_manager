import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client
import re

st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (한글 Pro Version)")

# 1. Supabase 클라우드 연결 설정
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 유틸리티: 숫자 콤마 제거 및 정수 변환
def clean_number(value):
    return re.sub(r'[^\d]', '', str(value))

# 데이터 로드 함수들
def load_contracts():
    res = supabase.table("contracts").select("*").execute()
    data = res.data
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # 데이터 출력 시 콤마 적용
    for col in ["deposit_amount", "monthly_rent"]:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"{int(clean_number(x)):,}" if clean_number(x) else "0")
    return df

contracts_df = load_contracts()
expenses_df = supabase.table("expenses").select("*").execute().data
history_df = supabase.table("history").select("*").execute().data

tab1, tab2, tab3 = st.tabs(["📋 임대 계약 및 관리", "💰 지출 및 공사 장부", "📁 지난 계약 및 매매 관리"])

# ==========================================
# [1페이지] 임대 계약 및 관리
# ==========================================
with tab1:
    st.subheader("현재 임대 계약 현황")
    if not contracts_df.empty:
        for idx, row in contracts_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### 🏢 {row.get('building_name')} {row.get('room_number')}호")
                st.markdown(f"💰 **보증금**: {row.get('deposit_amount')}원 | 💵 **월세**: {row.get('monthly_rent')}원")
                st.markdown(f"👤 **임차인**: {row.get('tenant_name')} ({row.get('tenant_phone')})")
    
    st.markdown("---")
    st.markdown("#### ➕ 신규 계약 등록")
    with st.form("contract_form_new", clear_on_submit=True):
        col1, col2 = st.columns(2)
        b_name = col1.text_input("건물명")
        r_name = col2.text_input("호실")
        
        col3, col4 = st.columns(2)
        deposit = col3.text_input("보증금 (숫자만 입력)", "10000000")
        rent = col4.text_input("월세 (숫자만 입력)", "500000")
        
        start_date = st.date_input("계약 시작일")
        submitted = st.form_submit_button("저장", type="primary")
        
        if submitted:
            supabase.table("contracts").insert({
                "building_name": b_name, "room_number": r_name, 
                "deposit_amount": clean_number(deposit), 
                "monthly_rent": clean_number(rent),
                "start_date": str(start_date), "status": "계약중"
            }).execute()
            st.success("등록 완료!")
            st.rerun()

# ==========================================
# [2페이지] 지출 장부
# ==========================================
with tab2:
    st.subheader("💰 지출 장부")
    if expenses_df:
        exp_df = pd.DataFrame(expenses_df)
        exp_df['amount'] = exp_df['amount'].apply(lambda x: int(clean_number(x)))
        st.metric("총 지출", f"{exp_df['amount'].sum():,.0f} 원")
        st.dataframe(exp_df, use_container_width=True)

    with st.form("expense_form", clear_on_submit=True):
        desc = st.text_input("내역")
        amt = st.text_input("비용 (숫자만 입력)")
        if st.form_submit_button("지출 등록"):
            supabase.table("expenses").insert({
                "description": desc, "amount": clean_number(amt)
            }).execute()
            st.rerun()

# ==========================================
# [3페이지] 이력 및 다운로드
# ==========================================
with tab3:
    st.subheader("📁 이력 관리")
    if history_df:
        st.dataframe(pd.DataFrame(history_df), use_container_width=True)
