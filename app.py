import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client

st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (한글 Pro Version)")
st.markdown("임대 계약, 지출 장부, 그리고 지난 계약 및 매매 이력 관리까지 클라우드 서버와 실시간 연동됩니다.")

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
        return pd.DataFrame(columns=["id", "건물명", "날짜", "내역", "지출금액(원)"])
    df = pd.DataFrame(data)
    
    # DB 필드명을 한글 표기용으로 유연하게 매핑
    col_mapping = {}
    for c in df.columns:
        if "building" in c.lower(): col_mapping[c] = "건물명"
        elif "date" in c.lower(): col_mapping[c] = "날짜"
        elif "desc" in c.lower(): col_mapping[c] = "내역"
        elif "amount" in c.lower() or "cost" in c.lower() or "price" in c.lower(): col_mapping[c] = "지출금액(원)"
        
    df = df.rename(columns=col_mapping)
    
    # 필수 컬럼 보장
    for req in ["건물명", "날짜", "내역", "지출금액(원)"]:
        if req not in df.columns:
            df[req] = ""
            
    return df

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
                    if status_badge == "계약중":
                        st.markdown(f"🟢 **{status_badge}**")
                    elif status_badge == "만료임박":
                        st.markdown(f"🟠 **⚠️ {status_badge}**")
                    else:
                        st.markdown(f"🔴 **{status_badge}**")
                
                deposit_val = row.get('보증금(원)', '0')
                rent_val = row.get('월세(원)', '0')
                pay_day = row.get('납부일', '25일')
                
                st.markdown(f"💰 **보증금**: {deposit_val}원 &nbsp;|&nbsp; 💵 **월세**: {rent_val}원 (매월 **{pay_day}**) 통보")
                
                t_name = row.get('임차인', '')
                t_phone = row.get('임차인연락처', '')
                r_name = row.get('부동산명', '')
                r_phone = row.get('부동산연락처', '')
                
                combined_info = f"👤 **임차인**: {t_name} ([전화](tel:{t_phone}) | [문자](sms:{t_phone})) &nbsp;/&nbsp; 🏠 **부동산**: {r_name} ([전화](tel:{r_phone}) | [문자](sms:{r_phone}))"
                st.markdown(combined_info)
                
                start_d = row.get('계약일', '')
                end_d = row.get('만료일', '')
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-top: 5px; margin-bottom: 5px;">
                        🗓️ <b>계약 기간</b> : <span style="color: #1f77b4; font-weight: bold;">{start_d} ~ {end_d}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                special_note = row.get('특약사항', '')
                if pd.notnull(special_note) and str(special_note).strip() != "":
                    st.info(f"📝 **특약 사항**: {special_note}")
                
                edit_state_key = f"is_editing_{row_id}"
                if edit_state_key not in st.session_state:
                    st.session_state[edit_state_key] = False
                
                btn_col1, btn_col2 = st.columns([4, 1])
                with btn_col2:
                    if st.button("✏️ 수정/삭제", key=f"toggle_btn_{row_id}"):
                        st.session_state[edit_state_key] = not st.session_state[edit_state_key]
                        st.rerun()
                
                if st.session_state[edit_state_key]:
                    with st.container(border=True):
                        st.markdown(f"#### 🛠️ 클라우드 데이터 수정")
                        with st.form(f"edit_form_{row_id}"):
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
                                default_end = pd.to_datetime(end_d).date() if pd.notnull(end_d) and end_d != "" else datetime.today().date()
                            except:
                                default_end = datetime.today().date()

                            e_start_date = st.date_input("계약 시작일 수정", value=default_start)
                            e_end_date = st.date_input("계약 만료일 수정", value=default_end)
                            
                            update_btn = st.form_submit_button("클라우드에 수정 반영", type="primary")
                            delete_btn = st.form_submit_button("클라우드에서 계약 삭제")
                            
                            if update_btn:
                                supabase.table("contracts").update({
                                    "building_name": e_bname,
                                    "room_number": e_rname,
                                    "tenant_name": e_tname,
                                    "tenant_phone": e_tphone,
                                    "agency_name": e_rename,
                                    "agency_phone": e_rephone,
                                    "deposit_amount": e_deposit,
                                    "monthly_rent": e_rent,
                                    "pay_day": e_pay_day,
                                    "start_date": str(e_start_date),
                                    "end_date": str(e_end_date)
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
                    "building_name": b_name,
                    "room_number": r_name,
                    "tenant_name": t_name,
                    "tenant_phone": t_phone,
                    "agency_name": re_name,
                    "agency_phone": re_phone,
                    "deposit_amount": deposit_val_input,
                    "monthly_rent": rent_val_input,
                    "pay_day": pay_day_input,
                    "start_date": start_str,
                    "end_date": end_str,
                    "special_notes": special_input,
                    "status": "계약중"
                }).execute()
                
                supabase.table("history").insert({
                    "building_name": b_name,
                    "room_number": r_name,
                    "contract_period": f"{start_str} ~ {end_str}",
                    "deposit": deposit_val_input,
                    "rent": rent_val_input,
                    "purchase_price": "0",
                    "sale_price": "0"
                }).execute()
                
                st.success("클라우드 서버에 안전하게 저장되었습니다!")
                st.rerun()

with tab2:
    st.subheader("💰 건물 유지보수 및 지출 장부")
    
    exp_search = st.text_input("🔍 지출 내역 검색", placeholder="건물명 또는 내역을 입력하세요", key="exp_search_input")
    
    display_expenses = expenses_df.copy()
    if exp_search and not display_expenses.empty:
        mask = display_expenses.apply(lambda row: row.astype(str).str.contains(exp_search, case=False).any(), axis=1)
        display_expenses = display_expenses[mask]
    
    total_cost = 0
    if not display_expenses.empty and "지출금액(원)" in display_expenses.columns:
        numeric_costs = display_expenses["지출금액(원)"].astype(str).str.replace(r'[^\d]', '', regex=True)
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
        valid_cols = ["건물명", "날짜", "내역", "지출금액(원)"]
        valid_cols = [c for c in valid_cols if c in display_expenses.columns]
        
        try:
            res_raw = supabase.table("expenses").select("*").execute()
            raw_list = res_raw.data if res_raw.data else []
        except:
            raw_list = []
        
        for idx, row in display_expenses.iterrows():
            raw_item = raw_list[idx] if idx < len(raw_list) else {}
            row_id = raw_item.get('id')
            
            with st.expander(f"🏢 {row.get('건물명', '')} | 📅 {row.get('날짜', '')} | 📝 {row.get('내역', '')} ({row.get('지출금액(원)', '')}원)"):
                if row_id is not None:
                    with st.form(f"edit_expense_{row_id}_{idx}"):
                        ed_bname = st.text_input("건물명", value=str(row.get('건물명', '')))
                        ed_date = st.text_input("날짜", value=str(row.get('날짜', '')))
                        ed_desc = st.text_input("내역", value=str(row.get('내역', '')))
                        ed_amount = st.text_input("지출금액(원)", value=str(row.get('지출금액(원)', '')))
                        
                        col_b1, col_b2 = st.columns(2)
                        up_exp = col_b1.form_submit_button("지출 수정 반영", type="primary")
                        del_exp = col_b2.form_submit_button("지출 내역 삭제")
                        
                        if up_exp:
                            supabase.table("expenses").update({
                                "building_name": ed_bname,
                                "expense_date": ed_date,
                                "description": ed_desc,
                                "amount": ed_amount
                            }).eq("id", row_id).execute()
                            st.success("지출 내역이 수정되었습니다!")
                            st.rerun()
                            
                        if del_exp:
                            supabase.table("expenses").delete().eq("id", row_id).execute()
                            st.warning("지출 내역이 삭제되었습니다.")
                            st.rerun()
                else:
                    st.warning("이 항목은 고유 ID가 없어 수정할 수 없습니다.")
        
        st.markdown("---")
        st.markdown("##### 📋 전체 지출 장부 요약표")
        st.dataframe(display_expenses[valid_cols], use_container_width=True, hide_index=True)
    else:
        st.info("조건에 맞는 지출 내역이 없습니다.")
        
    st.markdown("---")
    st.markdown("#### ➕ 새로운 지출 내역 등록")
    with st.form("expense_add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        ex_bname = col1.text_input("건물명", placeholder="예: 부산 센토빌")
        ex_date = col2.date_input("지출 날짜", value=datetime.today())
        
        col3, col4 = st.columns(2)
        ex_amount = col3.text_input("지출 비용(원)", value="100,000")
        ex_desc = col4.text_input("지출 내역", placeholder="예: 도어락 교체 및 수리비")
        
        ex_submitted = st.form_submit_button("지출 내역 저장", type="primary")
        if ex_submitted:
            if not ex_bname or not ex_desc:
                st.warning("건물명과 내역은 필수 입력입니다!")
            else:
                # [핵심 방어 코드] Supabase 테이블 스키마에 맞춰 유연하게 키 이름을 자동 매핑하여 인서트 시도
                success = False
                payload_candidates = [
                    {"building_name": ex_bname, "expense_date": str(ex_date), "description": ex_desc, "amount": ex_amount},
                    {"building": ex_bname, "date": str(ex_date), "content": ex_desc, "amount": ex_amount},
                    {"building_name": ex_bname, "date": str(ex_date), "description": ex_desc, "cost": ex_amount}
                ]
                
                for payload in payload_candidates:
                    try:
                        supabase.table("expenses").insert(payload).execute()
                        success = True
                        break
                    except:
                        continue
                
                if success:
                    st.success("지출 장부가 클라우드에 저장되었습니다!")
                    st.rerun()
                else:
                    st.error("저장에 실패했습니다. Supabase의 'expenses' 테이블 컬럼명을 확인해 주세요.")

with tab3:
    st.subheader("📁 지난 계약 및 매매 이력 장부")
    search_query = st.text_input("🔍 이력 검색", placeholder="검색어를 입력하세요", key="history_search")
    
    filtered_history = history_df.copy()
    if search_query and not filtered_history.empty:
        mask = filtered_history.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        filtered_history = filtered_history[mask]
        
    st.dataframe(filtered_history, use_container_width=True, hide_index=True)
    
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
