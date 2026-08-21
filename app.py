import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client

st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (지출 장부 Pro)")
st.markdown("건물별 지출 내역 및 유지보수 비용을 한눈에 관리하고 클라우드에 안전하게 동기화합니다.")

# 1. Supabase 클라우드 연결 설정
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 2. 클라우드에서 데이터 불러오기 함수들
def load_contracts():
    try:
        res = supabase.table("contracts").select("*").execute()
        data = res.data
    except:
        data = []
    if not data:
        return pd.DataFrame(columns=["id", "건물명", "호실", "임차인", "임차인연락처", "부동산명", "부동산연락처", "보증금(원)", "월세(원)", "납부일", "계약일", "만료일", "특약사항", "상태"])
    df = pd.DataFrame(data)
    rename_map = {
        "building_name": "건물명",
        "room_number": "호실",
        "tenant_name": "임차인",
        "tenant_phone": "임차인연락처",
        "agency_name": "부동산명",
        "agency_phone": "부동산연락처",
        "deposit_amount": "보증금(원)",
        "monthly_rent": "월세(원)",
        "pay_day": "납부일",
        "start_date": "계약일",
        "end_date": "만료일",
        "special_notes": "특약사항",
        "status": "상태"
    }
    return df.rename(columns=rename_map)

def load_expenses():
    try:
        res = supabase.table("expenses").select("*").execute()
        data = res.data
    except:
        data = []
    
    if not data:
        return pd.DataFrame(columns=["id", "건물명", "호실", "날짜", "내역", "비용"])
    
    df = pd.DataFrame(data)
    
    # DB 컬럼을 화면 표시용 한글 순서로 유연하게 매핑
    rename_map = {}
    if "building_name" in df.columns: rename_map["building_name"] = "건물명"
    if "room_number" in df.columns: rename_map["room_number"] = "호실"
    elif "category" in df.columns: rename_map["category"] = "호실"
    if "expense_date" in df.columns: rename_map["expense_date"] = "날짜"
    if "description" in df.columns: rename_map["description"] = "내역"
    if "amount" in df.columns: rename_map["amount"] = "비용"
    
    df = df.rename(columns=rename_map)
    
    expected_cols = ["id", "건물명", "호실", "날짜", "내역", "비용"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
            
    return df[expected_cols]

def load_history():
    try:
        res = supabase.table("history").select("*").execute()
        data = res.data
    except:
        data = []
    if not data:
        return pd.DataFrame(columns=["건물명", "호실", "계약기간", "보증금", "월세", "매수가(원)", "매도가(원)"])
    df = pd.DataFrame(data)
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
    rename_map = {
        "building_name": "건물명",
        "room_number": "호실",
        "contract_period": "계약기간",
        "deposit": "보증금",
        "rent": "월세",
        "purchase_price": "매수가(원)",
        "sale_price": "매도가(원)"
    }
    return df.rename(columns=rename_map)

contracts_df = load_contracts()
expenses_df = load_expenses()
history_df = load_history()

tab1, tab2, tab3 = st.tabs(["📋 임대 계약 및 관리", "💰 지출 및 공사 장부", "📁 지난 계약 및 매매 관리"])

with tab1:
    st.subheader("현재 임대 계약 현황 및 관리")
    if len(contracts_df) > 0:
        for idx, row in contracts_df.iterrows():
            row_id = row.get('id')
            with st.container(border=True):
                col_t1, col_t2 = st.columns([2, 1])
                with col_t1:
                    st.markdown(f"### 🏢 {row.get('건물명', '')} {row.get('호실', '')}")
                with col_t2:
                    status_badge = row.get('상태', '계약중')
                    st.markdown(f"🟢 **{status_badge}**")
                
                deposit_val = row.get('보증금(원)', '0')
                rent_val = row.get('월세(원)', '0')
                st.markdown(f"💰 **보증금**: {deposit_val}원 &nbsp;|&nbsp; 💵 **월세**: {rent_val}원")
                
                edit_state_key = f"is_editing_{row_id}"
                if edit_state_key not in st.session_state:
                    st.session_state[edit_state_key] = False
                
                if st.button("✏️ 수정/삭제", key=f"toggle_btn_{row_id}"):
                    st.session_state[edit_state_key] = not st.session_state[edit_state_key]
                    st.rerun()
                
                if st.session_state[edit_state_key]:
                    with st.form(f"edit_form_{row_id}"):
                        e_bname = st.text_input("건물명", value=str(row.get('건물명', '')))
                        e_rname = st.text_input("호실", value=str(row.get('호실', '')))
                        e_deposit = st.text_input("보증금", value=str(row.get('보증금(원)', '')))
                        e_rent = st.text_input("월세", value=str(row.get('월세(원)', '')))
                        
                        update_btn = st.form_submit_button("수정 반영", type="primary")
                        delete_btn = st.form_submit_button("계약 삭제")
                        
                        if update_btn:
                            supabase.table("contracts").update({
                                "building_name": e_bname,
                                "room_number": e_rname,
                                "deposit_amount": e_deposit,
                                "monthly_rent": e_rent
                            }).eq("id", row_id).execute()
                            st.session_state[edit_state_key] = False
                            st.success("수정되었습니다!")
                            st.rerun()
                        if delete_btn:
                            supabase.table("contracts").delete().eq("id", row_id).execute()
                            st.session_state[edit_state_key] = False
                            st.warning("삭제되었습니다.")
                            st.rerun()
    else:
        st.info("등록된 계약 정보가 없습니다.")

with tab2:
    st.subheader("💰 건물 유지보수 및 지출 장부")
    
    # 🔍 검색 기능
    exp_search = st.text_input("🔍 지출 내역 검색", placeholder="건물명, 호실 또는 내역을 입력하세요", key="exp_search_input")
    
    display_expenses = expenses_df.copy()
    if exp_search and not display_expenses.empty:
        mask = display_expenses.apply(lambda row: row.astype(str).str.contains(exp_search, case=False).any(), axis=1)
        display_expenses = display_expenses[mask]
    
    # 💵 비용 합산 기능
    total_cost = 0
    if not display_expenses.empty and "비용" in display_expenses.columns:
        numeric_costs = display_expenses["비용"].astype(str).str.replace(r'[^\d]', '', regex=True)
        total_cost = pd.to_numeric(numeric_costs, errors='coerce').sum()
    
    st.markdown(
        f"""
        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #1f77b4;">
            📊 현재 검색된 내역 <b>총 지출 비용</b>: <span style="color: #d9534f; font-size: 1.2em; font-weight: bold;">{total_cost:,.0f} 원</span>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # 중복 출력되던 아코디언(expander) 반복문 영역을 완전히 삭제했습니다!
    
    if not display_expenses.empty:
        st.markdown("##### 📋 지출 장부 요약표 (건물명, 호실, 날짜, 내역, 비용 순)")
        safe_cols = [c for c in ["건물명", "호실", "날짜", "내역", "비용"] if c in display_expenses.columns]
        st.dataframe(display_expenses[safe_cols], use_container_width=True, hide_index=True)
    else:
        st.info("조건에 맞는 지출 내역이 없습니다.")
        
    st.markdown("---")
    st.markdown("#### ➕ 새로운 지출 내역 등록")
    with st.form("expense_add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        ex_bname = col1.text_input("건물명", placeholder="예: 부산 센토빌")
        ex_rname = col2.text_input("호실", placeholder="예: 302호")
        
        col3, col4, col5 = st.columns(3)
        ex_date = col3.date_input("날짜", value=datetime.today())
        ex_desc = col4.text_input("내용", placeholder="예: 도어락 교체")
        ex_amount = col5.text_input("비용(원)", value="100000")
        
        ex_submitted = st.form_submit_button("지출 내역 저장", type="primary")
        if ex_submitted:
            if not ex_bname or not ex_desc:
                st.warning("건물명과 내용은 필수 입력입니다!")
            else:
                clean_amount = "".join(filter(str.isdigit, str(ex_amount)))
                
                try:
                    test_res = supabase.table("expenses").select("*").limit(1).execute()
                    first_row = test_res.data[0] if test_res.data else {}
                except:
                    first_row = {}
                
                insert_data = {
                    "building_name": ex_bname,
                    "expense_date": str(ex_date),
                    "description": ex_desc,
                    "amount": clean_amount
                }
                
                if "room_number" in first_row:
                    insert_data["room_number"] = ex_rname
                elif "category" in first_row:
                    insert_data["category"] = ex_rname
                else:
                    insert_data["category"] = ex_rname

                supabase.table("expenses").insert(insert_data).execute()
                st.success("클라우드에 안전하게 저장되었습니다!")
                st.rerun()

with tab3:
    st.subheader("📁 지난 계약 및 매매 이력 장부")
    search_query = st.text_input("🔍 이력 검색", placeholder="검색어를 입력하세요", key="history_search")
    filtered_history = history_df.copy()
    if search_query and not filtered_history.empty:
        mask = filtered_history.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        filtered_history = filtered_history[mask]
    st.dataframe(filtered_history, use_container_width=True, hide_index=True)
