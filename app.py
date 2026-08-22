import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client
import json
import re

# 페이지 설정
st.set_page_config(page_title="건물주 스마트 비서", page_icon="🏢", layout="centered")
st.title("🏢 건물주 스마트 비서 (Pro Version)")

# --- [UI 커스텀 CSS: 탭 글씨 크기 및 스타일 강화] ---
st.markdown("""
    <style>
    /* 1. 탭 스타일: 매우 크고 굵게 */
    button[data-baseweb="tab"] {
        font-size: 30px !important;      
        font-weight: 1200 !important;     
        padding: 20px 40px !important;   
    }
    
    /* 2. 폼 라벨(항목 이름): 굵고 눈에 띄게 */
    label {
        font-size: 30px !important;
        font-weight: 1200 !important;
        color: #2c3e50 !important;
    }
    
    /* 3. 입력창(Text Input) 내부 글씨 크기 조정 */
    input {
        font-size: 16px !important;
    }
    
    /* 4. 데이터 에디터 폰트 키우기 */
    [data-testid="stDataFrame"] {
        font-size: 16px !important;
    }
    
    /* 5. 마크다운 내 강조 텍스트(항목) 키우기 */
    b, strong {
        font-size: 17px !important;
    }
    </style>
""", unsafe_allow_html=True)

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
        return pd.DataFrame(columns=["id", "건물명", "호실", "카테고리", "임차인", "임차인연락처", "부동산명", "부동산연락처", "보증금(원)", "월세(원)", "매수금", "대출금", "납부일", "계약일", "만료일", "특약사항", "상태"])
    df = pd.DataFrame(data)
    rename_map = {
        "building_name": "건물명", "room_number": "호실", "property_type": "카테고리",
        "tenant_name": "임차인", "tenant_phone": "임차인연락처", "agency_name": "부동산명", 
        "agency_phone": "부동산연락처", "deposit_amount": "보증금(원)", "monthly_rent": "월세(원)", 
        "purchase_price": "매수금", "loan_amount": "대출금",
        "pay_day": "납부일", "start_date": "계약일", "end_date": "만료일", 
        "special_notes": "특약사항", "status": "상태"
    }
    if "property_type" not in df.columns:
        df["property_type"] = "원룸"
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
        "deposit": "보증금", "rent": "월세", "purchase_price": "매수가", "loan_amount": "대출금", "sale_price": "매도가"
    })

contracts_df = load_contracts()
expenses_df = load_expenses()
history_df = load_history()

tab1, tab2, tab3 = st.tabs(["📋 건물 계약 및 관리", "💰 지출 내역 관리", "📁 지난 계약 및 매매 관리"])

# ==========================================
# [1페이지] 임대 계약 및 관리
# ==========================================
with tab1:
    if len(contracts_df) > 0 and "카테고리" in contracts_df.columns:
        category_counts = contracts_df["카테고리"].value_counts()
        summary_badges = []
        for cat, cnt in category_counts.items():
            if pd.notnull(cat) and str(cat).strip() != "" and cnt > 0:
                summary_badges.append(f"<b>{cat}</b> {cnt}개")
        
        if summary_badges:
            badge_html = " &nbsp;|&nbsp; ".join(summary_badges)
            st.markdown(
                f"""
                <div style="background-color: #f8f9fa; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #e3e6f0; font-size: 0.95em;">
                    📊 <b>보유 건물:</b> {badge_html}
                </div>
                """,
                unsafe_allow_html=True
            )
    
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
                prop_cat = row.get('카테고리', '원룸')
                st.markdown(f"### 🏢 [{prop_cat}] {row.get('건물명', '')} {row.get('호실', '')}")
                
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
                
                btn_col1, btn_col2 = st.columns([3, 1])
                with btn_col1:
                    if is_expired:
                        st.markdown("🔴 **계약만료**", unsafe_allow_html=True)
                    else:
                        status_badge = row.get('상태', '계약중')
                        if status_badge == "계약중":
                            st.markdown(f"🟢 **{status_badge}**", unsafe_allow_html=True)
                        elif status_badge == "만료임박":
                            st.markdown(f"🟠 **⚠️ {status_badge}**", unsafe_allow_html=True)
                        else:
                            st.markdown(f"🔴 **{status_badge}**", unsafe_allow_html=True)
                
                with btn_col2:
                    if st.button("✏️ 수정/삭제", key=f"toggle_contract_{row_id}", use_container_width=True):
                        st.session_state[edit_state_key] = not st.session_state[edit_state_key]
                        st.rerun()
                
                if st.session_state[edit_state_key]:
                    with st.container(border=True):
                        st.markdown(f"#### 🛠️ 임대 계약 데이터 수정")
                        with st.form(f"edit_form_contract_{row_id}"):
                            categories = ["아파트", "빌라", "원룸", "오피스텔", "단독주택", "상가"]
                            curr_cat = str(row.get('카테고리', '원룸'))
                            cat_index = categories.index(curr_cat) if curr_cat in categories else 2
                            
                            e_cat = st.selectbox("카테고리 선택", categories, index=cat_index, key=f"ecat_{row_id}")
                            e_bname = st.text_input("건물명", value=str(row.get('건물명', '')), key=f"eb_{row_id}")
                            e_rname = st.text_input("호실", value=str(row.get('호실', '')), key=f"er_{row_id}")
                            e_tname = st.text_input("임차인 이름", value=str(row.get('임차인', '')), key=f"etn_{row_id}")
                            e_tphone = st.text_input("임차인 연락처", value=str(row.get('임차인연락처', '')), key=f"etp_{row_id}")
                            e_rename = st.text_input("부동산 이름", value=str(row.get('부동산명', '')), key=f"eran_{row_id}")
                            e_rephone = st.text_input("부동산 연락처", value=str(row.get('부동산연락처', '')), key=f"erap_{row_id}")
                            e_deposit = st.text_input("보증금", value=str(row.get('보증금(원)', '')), key=f"edep_{row_id}")
                            e_rent = st.text_input("월세", value=str(row.get('월세(원)', '')), key=f"erent_{row_id}")
                            e_purchase = st.text_input("매수금", value=str(row.get('매수금', '0')), key=f"epurchase_{row_id}")
                            e_loan = st.text_input("대출금", value=str(row.get('대출금', '0')), key=f"eloan_{row_id}")
                            e_pay_day = st.text_input("월세 납부일", value=str(row.get('납부일', '')), key=f"epay_{row_id}")
                            e_special = st.text_area("특약 사항", value=str(row.get('특약사항', '')), key=f"espec_{row_id}")
                            
                            try:
                                default_start = pd.to_datetime(start_d).date() if pd.notnull(start_d) and start_d != "" else datetime.today().date()
                            except:
                                default_start = datetime.today().date()
                                
                            try:
                                default_end = pd.to_datetime(end_d_str).date() if pd.notnull(end_d_str) and end_d_str != "" else datetime.today().date()
                            except:
                                default_end = datetime.today().date()

                            e_start_date = st.date_input("계약 시작일 수정", value=default_start, key=f"estart_{row_id}")
                            e_end_date = st.date_input("계약 만료일 수정", value=default_end, key=f"eend_{row_id}")
                            
                            update_btn = st.form_submit_button("클라우드에 수정 반영", type="primary")
                            delete_btn = st.form_submit_button("클라우드에서 계약 삭제")
                            
                            if update_btn:
                                update_payload = {
                                    "property_type": e_cat, 
                                    "building_name": e_bname, 
                                    "room_number": e_rname, 
                                    "tenant_name": e_tname, 
                                    "tenant_phone": e_tphone, 
                                    "agency_name": e_rename, 
                                    "agency_phone": e_rephone, 
                                    "deposit_amount": e_deposit, 
                                    "monthly_rent": e_rent, 
                                    "purchase_price": e_purchase,
                                    "loan_amount": e_loan,
                                    "pay_day": e_pay_day, 
                                    "start_date": str(e_start_date), 
                                    "end_date": str(e_end_date),
                                    "special_notes": e_special
                                }
                                try:
                                    supabase.table("contracts").update(update_payload).eq("id", row_id).execute()
                                    st.session_state[edit_state_key] = False
                                    st.success("클라우드 서버에 수정 사항이 반영되었습니다!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"업데이트 중 데이터베이스 오류 발생: {e}")
                                    
                            if delete_btn:
                                supabase.table("contracts").delete().eq("id", row_id).execute()
                                st.session_state[edit_state_key] = False
                                st.warning("클라우드 서버에서 계약이 삭제되었습니다.")
                                st.rerun()
    else:
        st.info("클라우드에 등록된 계약 정보가 없습니다.")
    
    st.markdown("---")
    st.markdown("#### ➕ 새 계약 등록 (클라우드 저장)")
    
    with st.form("contract_form_cloud", clear_on_submit=True):
        property_category = st.selectbox("부동산 카테고리 선택", ["아파트", "빌라", "원룸", "오피스텔", "단독주택", "상가"])
        
        col1, col2 = st.columns(2)
        b_name = col1.text_input("건물명", placeholder="예: 부산 센토빌")
        r_name = col2.text_input("호실", placeholder="예: 302호")
        
        # 신규 추가된 매수금 및 대출금 입력 필드
        c_p1, c_p2 = st.columns(2)
        purchase_val_input = c_p1.text_input("매수금 (원)", value="0")
        loan_val_input = c_p2.text_input("대출금 (원)", value="0")
        
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
                
                try:
                    # contracts 테이블 저장 (매수금, 대출금 포함)
                    supabase.table("contracts").insert({
                        "property_type": property_category, "building_name": b_name, "room_number": r_name, 
                        "tenant_name": t_name, "tenant_phone": t_phone, "agency_name": re_name, 
                        "agency_phone": re_phone, "deposit_amount": deposit_val_input, "monthly_rent": rent_val_input, 
                        "purchase_price": purchase_val_input, "loan_amount": loan_val_input,
                        "pay_day": pay_day_input, "start_date": start_str, "end_date": end_str, 
                        "special_notes": special_input, "status": "계약중"
                    }).execute()
                    
                    # history 테이블 연동 저장 (매수금, 대출금 연동)
                    supabase.table("history").insert({
                        "building_name": f"[{property_category}] {b_name}", "room_number": r_name,
                        "contract_period": f"{start_str} ~ {end_str}",
                        "deposit": deposit_val_input, "rent": rent_val_input,
                        "purchase_price": purchase_val_input, "loan_amount": loan_val_input, "sale_price": "0"
                    }).execute()
                    
                    st.success("클라우드 서버에 안전하게 저장되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 중 에러 발생: {e}")

# ==========================================
# [2페이지] 지출 내역 관리
# ==========================================
with tab2:
    if st.session_state.get("clear_expense_input", False):
        st.session_state["del_e_input"] = ""
        st.session_state["clear_expense_input"] = False

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
        
        col_e1, col_e2_input, col_e2_btn = st.columns([2, 2, 1])
        with col_e1:
            if st.button("💾 지출 수정 사항 일괄 저장", type="primary", use_container_width=True, key="save_expense_btn"):
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
                
        with col_e2_input:
            del_e_id = st.text_input("삭제할 ID", placeholder="삭제할 ID 번호 입력", key="del_e_input", label_visibility="collapsed")
        with col_e2_btn:
            if st.button("🗑️ 삭제", use_container_width=True, key="del_expense_btn"):
                if del_e_id:
                    supabase.table("expenses").delete().eq("id", int(del_e_id)).execute()
                    st.session_state["clear_expense_input"] = True
                    st.warning(f"ID {del_e_id} 삭제됨")
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
# [3페이지] 지난 계약 및 매매 이력 장부
# ==========================================
with tab3:
    if st.session_state.get("clear_history_input", False):
        st.session_state["del_h_input"] = ""
        st.session_state["clear_history_input"] = False

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
        
        col_h1, col_h2_input, col_h2_btn = st.columns([2, 2, 1])
        with col_h1:
            if st.button("💾 이력 수정 사항 일괄 저장", type="primary", use_container_width=True, key="save_history_btn"):
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
                            "loan_amount": str(row.get("대출금", "")),
                            "sale_price": str(row.get("매도가", ""))
                        }).eq("id", row_id).execute()
                st.success("이력이 수정되었습니다!")
                st.rerun()
                
        with col_h2_input:
            del_h_id = st.text_input("삭제할 ID", placeholder="삭제할 ID 번호 입력", key="del_h_input", label_visibility="collapsed")
        with col_h2_btn:
            if st.button("🗑️ 삭제", use_container_width=True, key="del_history_btn"):
                if del_h_id:
                    supabase.table("history").delete().eq("id", int(del_h_id)).execute()
                    st.session_state["clear_history_input"] = True
                    st.warning(f"ID {del_h_id} 삭제됨")
                    st.rerun()
    else:
        st.info("검색 결과와 일치하는 이력 장부가 없습니다.")

    def create_excel(df1, df2, df3):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df1.to_excel(writer, index=False, sheet_name='건물 계약 및 관리')
            df2.to_excel(writer, index=False, sheet_name='지출 내역 관리')
            df3.to_excel(writer, index=False, sheet_name='지난 계약 및 매매 관리')
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
