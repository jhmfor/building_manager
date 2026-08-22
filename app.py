import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client
import re

# 페이지 설정
st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (Pro Version)")


# --- 유틸리티 함수: 천 단위 콤마 자동 포맷팅 ---
def format_currency(value):
    try:
        clean_val = re.sub(r'[^\d]', '', str(value))
        return f"{int(clean_val):,}" if clean_val else "0"
    except:
        return str(value)

# 1. Supabase 클라우드 연결 설정
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 2. 클라우드 데이터 불러오기 함수들
def load_contracts():
    res = supabase.table("contracts").select("*").execute()
    data = res.data
    if not data:
        return pd.DataFrame(columns=["id", "건물명", "호실", "임차인", "임차인연락처", "부동산명", "부동산연락처", "보증금(원)", "월세(원)", "납부일", "계약일", "만료일", "특약사항", "상태"])
    df = pd.DataFrame(data)
    rename_map = {
        "building_name": "건물명", "room_number": "호실", "tenant_name": "임차인", 
        "tenant_phone": "임차인연락처", "agency_name": "부동산명", "agency_phone": "부동산연락처", 
        "deposit_amount": "보증금(원)", "monthly_rent": "월세(원)", "pay_day": "납부일", 
        "start_date": "계약일", "end_date": "만료일", "special_notes": "특약사항", "status": "상태"
    }
    return df.rename(columns=rename_map)

def load_expenses():
    res = supabase.table("expenses").select("*").execute()
    data = res.data
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    df = df.rename(columns={
        "expense_date": "날짜", "building_name": "건물명", "room_number": "호실",
        "category": "카테고리", "description": "내역", "amount": "비용"
    })
    # 비용 컬럼 천 단위 콤마 포맷팅 적용
    if "비용" in df.columns:
        df["비용"] = df["비용"].apply(format_currency)
    return df

def load_history():
    res = supabase.table("history").select("*").execute()
    data = res.data
    if not data: return pd.DataFrame()
    df = pd.DataFrame(data)
    return df.rename(columns={
        "building_name": "건물명", "room_number": "호실", "contract_period": "계약기간", 
        "deposit": "보증금", "rent": "월세", "purchase_price": "매수가", "sale_price": "매도가"
    })

contracts_df = load_contracts()
expenses_df = load_expenses()
history_df = load_history()

tab1, tab2, tab3 = st.tabs(["📋 임대 계약 및 관리", "💰 지출 및 공사 장부", "📁 지난 계약 및 매매 관리"])

# ==========================================
# [1페이지] 임대 계약 및 관리 (기존 마스터 카드형 UI)
# ==========================================
with tab1:
    st.subheader("현재 임대 계약 현황 및 관리")
    
    if len(contracts_df) > 0:
        for idx, row in contracts_df.iterrows():
            row_id = row.get('id')
            
            end_d_str = row.get('만료일', '1900-01-01')
            try:
                end_date_obj = pd.to_datetime(end_d_str)
                is_expired = end_date_obj < datetime.now()
            except:
                is_expired = False

            with st.container(border=True):
                col_t1, col_t2 = st.columns([2, 1])
                with col_t1:
                    st.markdown(f"### 🏢 {row.get('건물명', '')} {row.get('호실', '')}")
                with col_t2:
                    if is_expired:
                        st.markdown("🔴 **계약만료**")
                    else:
                        status_badge = row.get('상태', '계약중')
                        if status_badge == "계약중":
                            st.markdown(f"🟢 **{status_badge}**")
                        elif status_badge == "만료임박":
                            st.markdown(f"🟠 **⚠️ {status_badge}**")
                        else:
                            st.markdown(f"🔴 **{status_badge}**")
                
                deposit_val = format_currency(row.get('보증금(원)', '0'))
                rent_val = format_currency(row.get('월세(원)', '0'))
                pay_day = row.get('납부일', '25일')
                
                st.markdown(f"💰 **보증금**: {deposit_val}원 &nbsp;|&nbsp; 💵 **월세**: {rent_val}원 (매월 **{pay_day}**)")
                
                t_name = row.get('임차인', '')
                t_phone = row.get('임차인연락처', '')
                r_name = row.get('부동산명', '')
                r_phone = row.get('부동산연락처', '')
                
                combined_info = f"👤 **임차인**: {t_name} ([전화](tel:{t_phone}) | [문자](sms:{t_phone})) &nbsp;/&nbsp; 🏠 **부동산**: {r_name} ([전화](tel:{r_phone}) | [문자](sms:{r_phone}))"
                st.markdown(combined_info)
                
                start_d = row.get('계약일', '')
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-top: 5px; margin-bottom: 5px;">
                        🗓️ <b>계약 기간</b> : <span style="color: #1f77b4; font-weight: bold;">{start_d} ~ {end_d_str}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                special_note = row.get('특약사항', '')
                if pd.notnull(special_note) and str(special_note).strip() != "":
                    st.info(f"📝 **특약 사항**: {special_note}")
                
                edit_state_key = f"is_editing_contract_{row_id}"
                if edit_state_key not in st.session_state:
                    st.session_state[edit_state_key] = False
                
                btn_col1, btn_col2 = st.columns([4, 1])
                with btn_col2:
                    if st.button("✏️ 수정/삭제", key=f"toggle_contract_{row_id}"):
                        st.session_state[edit_state_key] = not st.session_state[edit_state_key]
                        st.rerun()
                
                if st.session_state[edit_state_key]:
                    with st.container(border=True):
                        st.markdown(f"#### 🛠️ 임대 계약 데이터 수정")
                        with st.form(f"edit_form_contract_{row_id}"):
                            e_bname = st.text_input("건물명", value=str(row.get('건물명', '')))
                            e_rname = st.text_input("호실", value=str(row.get('호실', '')))
                            e_tname = st.text_input("임차인 이름", value=str(row.get('임차인', '')))
                            e_tphone = st.text_input("임차인 연락처", value=str(row.get('임차인연락처', '')))
                            e_rename = st.text_input("부동산 이름", value=str(row.get('부동산명', '')))
                            e_rephone = st.text_input("부동산 연락처", value=str(row.get('부동산연락처', '')))
                            e_deposit = st.text_input("보증금", value=str(row.get('보증금(원)', '')))
                            e_rent = st.text_input("월세", value=str(row.get('월세(원)', '')))
                            e_pay_day = st.text_input("월세 납부일", value=str(row.get('납부일', '')))
                            
                            try:
                                default_start = pd.to_datetime(start_d).date() if pd.notnull(start_d) and start_d != "" else datetime.today().date()
                            except:
                                default_start = datetime.today().date()
                                
                            try:
                                default_end = pd.to_datetime(end_d_str).date() if pd.notnull(end_d_str) and end_d_str != "" else datetime.today().date()
                            except:
                                default_end = datetime.today().date()

                            e_start_date = st.date_input("계약 시작일 수정", value=default_start)
                            e_end_date = st.date_input("계약 만료일 수정", value=default_end)
                            
                            update_btn = st.form_submit_button("클라우드에 수정 반영", type="primary")
                            delete_btn = st.form_submit_button("클라우드에서 계약 삭제")
                            
                            if update_btn:
                                supabase.table("contracts").update({
                                    "building_name": e_bname, "room_number": e_rname, "tenant_name": e_tname,
                                    "tenant_phone": e_tphone, "agency_name": e_rename, "agency_phone": e_rephone,
                                    "deposit_amount": e_deposit, "monthly_rent": e_rent, "pay_day": e_pay_day,
                                    "start_date": str(e_start_date), "end_date": str(e_end_date)
                                }).eq("id", row_id).execute()
                                st.session_state[edit_state_key] = False
                                st.success("클라우드 서버에 수정 사항이 반영되었습니다!")
                                st.rerun()
                                
                            if delete_btn:
                                supabase.table("contracts").delete().eq("id", row_id).execute()
                                st.session_state[edit_state_key] = False
                                st.warning("클라우드 서버에서 계약이 삭제되었습니다.")
                                st.rerun()
    else:
        st.info("클라우드에 등록된 계약 정보가 없습니다.")
    
    st.markdown("---")
    st.markdown("#### ➕ 새로운 계약 등록 (클라우드 저장)")
    
    with st.form("contract_form_cloud", clear_on_submit=True):
        col1, col2 = st.columns(2)
        b_name = col1.text_input("건물명", placeholder="예: 부산 센토빌")
        r_name = col2.text_input("호실", placeholder="예: 302호")
        
        col3, col4 = st.columns(2)
        t_name = col3.text_input("임차인 이름", placeholder="예: 김세은")
        t_phone = col4.text_input("임차인 연락처", placeholder="예: 010-1234-5678")
        
        col5, col6 = st.columns(2)
        re_name = col5.text_input("부동산 이름", placeholder="예: 친절공인중개사")
        re_phone = col6.text_input("부동산 연락처", placeholder="예: 051-123-4567")
        
        r_col1, r_col2, r_col3 = st.columns(3)
        deposit_val_input = r_col1.text_input("보증금", value="10,000,000")
        rent_val_input = r_col2.text_input("월세", value="500,000")
        pay_day_input = r_col3.text_input("월세 납부일", value="25일")
        
        d_col1, d_col2 = st.columns(2)
        start_date = d_col1.date_input("계약 시작일")
        end_date = d_col2.date_input("계약 만료일", value=pd.to_datetime(start_date) + pd.DateOffset(years=2))
        
        special_input = st.text_area("특약 사항 (선택 입력)")
        submitted = st.form_submit_button("신규 계약 클라우드 저장", type="primary")
        
        if submitted:
            if not b_name or not r_name or not t_name or not t_phone:
                st.warning("필수 항목을 모두 입력해주세요!")
            else:
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                
                supabase.table("contracts").insert({
                    "building_name": b_name, "room_number": r_name, "tenant_name": t_name,
                    "tenant_phone": t_phone, "agency_name": re_name, "agency_phone": re_phone,
                    "deposit_amount": deposit_val_input, "monthly_rent": rent_val_input, "pay_day": pay_day_input,
                    "start_date": start_str, "end_date": end_str, "special_notes": special_input, "status": "계약중"
                }).execute()
                
                supabase.table("history").insert({
                    "building_name": b_name, "room_number": r_name,
                    "contract_period": f"{start_str} ~ {end_str}",
                    "deposit": deposit_val_input, "rent": rent_val_input,
                    "purchase_price": "0", "sale_price": "0"
                }).execute()
                
                st.success("클라우드 서버에 안전하게 저장되었습니다!")
                st.rerun()

# ==========================================
# [2페이지] 지출 및 공사 장부 (검색 + 천 단위 콤마 + 총지출 + 표 수정)
# ==========================================
with tab2:
    st.subheader("💰 건물 유지보수 및 지출 장부")
    
    current_expenses_df = expenses_df.copy()
    exp_search = st.text_input("🔍 지출 내역 검색", placeholder="건물명, 호실, 내역 또는 카테고리 검색", key="exp_search_input")
    
    display_expenses = current_expenses_df.copy()
    if exp_search and not display_expenses.empty:
        mask = display_expenses.apply(lambda row: row.astype(str).str.contains(exp_search, case=False).any(), axis=1)
        display_expenses = display_expenses[mask]
    
    total_cost = 0
    target_col = "비용" if "비용" in display_expenses.columns else None
    
    if not display_expenses.empty and target_col:
        numeric_costs = display_expenses[target_col].astype(str).str.replace(r'[^\d]', '', regex=True)
        total_cost = pd.to_numeric(numeric_costs, errors='coerce').sum()
    
    st.markdown(
        f"""
        <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #1f77b4;">
            📊 현재 검색된 내역 <b>총 지출 비용</b>: <span style="color: #d9534f; font-size: 1.2em; font-weight: bold;">{total_cost:,.0f} 원</span>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    if not display_expenses.empty:
        edited_e_df = st.data_editor(
            display_expenses, 
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
                        clean_amt = re.sub(r'[^\d]', '', str(row.get("비용", "0")))
                        supabase.table("expenses").update({
                            "building_name": str(row.get("건물명", "")),
                            "room_number": str(row.get("호실", "")),
                            "category": str(row.get("카테고리", "기타")),
                            "description": str(row.get("내역", "")),
                            "amount": clean_amt,
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
        st.info("조건에 맞는 지출 내역이 없습니다.")
        
    st.markdown("---")
    with st.expander("➕ 신규 지출 추가하기"):
        with st.form("new_e_form"):
            eb = st.text_input("건물명", key="ne_b")
            er = st.text_input("호실", key="ne_r")
            ec = st.selectbox("카테고리", ["수리비", "공사비", "세금", "중개수수료", "기타"])
            ed = st.text_input("내역", key="ne_d")
            ea = st.text_input("비용", "100000", key="ne_a")
            if st.form_submit_button("지출 추가"):
                clean_amount = re.sub(r'[^\d]', '', str(ea))
                supabase.table("expenses").insert({
                    "building_name": eb, "room_number": er, "category": ec,
                    "description": ed, "amount": clean_amount, "expense_date": str(datetime.today().date())
                }).execute()
                st.success("추가되었습니다!")
                st.rerun()

# ==========================================
# [3페이지] 지난 계약 및 매매 (검색 + 표 수정)
# ==========================================
with tab3:
    st.subheader("📁 지난 계약 및 매매 이력 장부")
    search_query = st.text_input("🔍 항목별 검색", placeholder="검색어를 입력하세요", key="history_search")
    
    filtered_history = history_df.copy()
    if search_query and len(filtered_history) > 0:
        mask = filtered_history.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        filtered_history = filtered_history[mask]
    
    if not filtered_history.empty:
        edited_h_df = st.data_editor(
            filtered_history, 
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
        st.info("검색 결과와 일치하는 이력 장부가 없습니다.")

    def create_excel(df1, df2, df3):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df1.to_excel(writer, index=False, sheet_name='임대계약_관리')
            df2.to_excel(writer, index=False, sheet_name='지출_공사_장부')
            df3.to_excel(writer, index=False, sheet_name='지난계약_매매이력')
        return output.getvalue()
    
    st.markdown("---")
    excel_file = create_excel(contracts_df, expenses_df, history_df)
    st.download_button(
        label="📊 전체 세무 및 매매 장부 엑셀 다운로드 (.xlsx)",
        data=excel_file,
        file_name=f"건물종합관리장부_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
