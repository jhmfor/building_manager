import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client

# 1. 페이지 설정
st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (Pro Version)")
st.markdown("임대 관리, 지출 장부, 매매 이력을 클라우드에서 안전하게 관리하세요.")

# 2. Supabase 클라우드 연결
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 3. 데이터 로드 함수 (한글 컬럼 매핑)
def load_contracts():
    res = supabase.table("contracts").select("*").execute()
    data = res.data
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data).rename(columns={
        "building_name": "건물명", "room_number": "호실", "tenant_name": "임차인",
        "tenant_phone": "임차인연락처", "agency_name": "부동산명", "agency_phone": "부동산연락처",
        "deposit_amount": "보증금(원)", "monthly_rent": "월세(원)", "pay_day": "납부일",
        "start_date": "계약일", "end_date": "만료일", "special_notes": "특약사항", "status": "상태"
    })
    return df

def load_expenses():
    res = supabase.table("expenses").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def load_history():
    res = supabase.table("history").select("*").execute()
    data = res.data
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data).rename(columns={
        "building_name": "건물명", "room_number": "호실", "contract_period": "계약기간",
        "deposit": "보증금", "rent": "월세", "purchase_price": "매수가(원)", "sale_price": "매도가(원)"
    })
    return df

# 데이터 동기화
contracts_df = load_contracts()
expenses_df = load_expenses()
history_df = load_history()

# 4. UI 탭 구성
tab1, tab2, tab3 = st.tabs(["📋 임대 계약 관리", "💰 지출 장부", "📁 지난 이력"])

with tab1:
    st.subheader("현재 임대 계약 현황")
    if not contracts_df.empty:
        for idx, row in contracts_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### 🏢 {row.get('건물명')} {row.get('호실')}")
                st.markdown(f"👤 **{row.get('임차인')}** | 💰 **보증금**: {row.get('보증금(원)')}원 / **월세**: {row.get('월세(원)')}원")
                st.markdown(f"🗓️ **계약**: {row.get('계약일')} ~ {row.get('만료일')}")
    else:
        st.info("등록된 계약 정보가 없습니다.")

    with st.form("new_contract", clear_on_submit=True):
        st.subheader("➕ 신규 계약 등록")
        col1, col2 = st.columns(2)
        b_name = col1.text_input("건물명")
        r_name = col2.text_input("호실")
        t_name = st.text_input("임차인 이름")
        t_phone = st.text_input("임차인 연락처")
        submitted = st.form_submit_button("클라우드 저장", type="primary")
        if submitted:
            supabase.table("contracts").insert({"building_name": b_name, "room_number": r_name, "tenant_name": t_name, "tenant_phone": t_phone, "status": "계약중"}).execute()
            st.success("저장 완료!"); st.rerun()

with tab2:
    st.subheader("건물 지출 장부")
    st.dataframe(expenses_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📁 지난 계약 및 매매 이력")
    if not history_df.empty:
        # id열과 인덱스 제외한 깔끔한 데이터 출력
        display_df = history_df.drop(columns=['id'], errors='ignore')
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # 엑셀 다운로드
    def create_excel():
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            contracts_df.to_excel(writer, index=False, sheet_name='임대계약')
            history_df.to_excel(writer, index=False, sheet_name='지난이력')
        return output.getvalue()
    
    st.download_button("📊 전체 데이터 엑셀 다운로드", create_excel(), "건물관리장부.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
