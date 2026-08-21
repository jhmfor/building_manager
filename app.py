import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client

st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (진단 모드)")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 데이터 및 스키마 진단
st.markdown("### 🔍 Supabase 'expenses' 테이블 구조 진단")
try:
    res = supabase.table("expenses").select("*").limit(1).execute()
    if res.data:
        st.success(f"현재 'expenses' 테이블의 실제 데이터 샘플 및 컬럼 키값:")
        st.write(res.data[0])
    else:
        # 데이터가 없을 경우 빈 구조라도 확인 시도
        st.warning("테이블에 데이터가 없어 컬럼을 유추합니다. 아래 입력 테스트를 진행해 주세요.")
except Exception as e:
    st.error(f"테이블 조회 중 에러 발생: {e}")

st.markdown("---")
st.markdown("#### ➕ 지출 내역 강제 테스트 입력")

with st.form("test_expense_form"):
    ex_bname = st.text_input("건물명", value="테스트 건물")
    ex_date = st.date_input("지출 날짜", value=datetime.today())
    ex_amount = st.text_input("지출 비용(원)", value="100,000")
    ex_desc = st.text_input("지출 내역", value="테스트 내역")
    
    test_submitted = st.form_submit_button("단일 키로 저장 테스트", type="primary")
    if test_submitted:
        # 가장 표준적인 컬럼명들로 각각 테스트해보고 어떤 게 먹히는지 확인
        tries = [
            {"building_name": ex_bname, "expense_date": str(ex_date), "description": ex_desc, "amount": ex_amount},
            {"building": ex_bname, "date": str(ex_date), "content": ex_desc, "cost": ex_amount},
            {"building_name": ex_bname, "date": str(ex_date), "memo": ex_desc, "price": ex_amount}
        ]
        
        success_flag = False
        for i, payload in enumerate(tries):
            try:
                supabase.table("expenses").insert(payload).execute()
                st.success(f"성공! 성공한 시도 번호: {i+1} / 사용된 데이터 구조: {payload}")
                success_flag = True
                break
            except Exception as err:
                st.write(f"시도 {i+1} 실패 에러: {err}")
                
        if not success_flag:
            st.error("모든 표준 키 조합이 실패했습니다. Supabase 대시보드에서 'expenses' 테이블의 정확한 컬럼 영문명을 확인해 주세요.")
