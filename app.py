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
    if not data:
        return pd.DataFrame(columns=["id", "날짜", "건물명", "카테고리", "내역", "지출금액(원)"])
    return pd.DataFrame(data)

def load_history():
    res = supabase.table("history").select("*").execute()
    data = res.data
    if not data:
        return pd.DataFrame(columns=["건물명", "호실", "계약기간", "보증금", "월세", "매수가(원)", "매도가(원)"])
    df = pd.DataFrame(data)
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
    rename_map = {
        "building_name": "건물명", "room_number": "호실", "contract_period": "계약기간", 
        "deposit": "보증금", "rent": "월세", "purchase_price": "매수가(원)", "sale_price": "매도가(원)"
    }
    return df.rename(columns=rename_map)

contracts_df = load_contracts()
expenses_df = load_expenses()
history_df = load_history()

tab1, tab2, tab3 = st.tabs(["📋 임대 계약 및 관리", "💰 지출 및 공사 장부", "📁 지난 계약 및 매매 관리"])

# ==========================================
# [1페이지] 임대 계약 및 관리 (수정 버전)
# ==========================================
with tab1:
    st.subheader("현재 임대 계약 현황 및 관리")
    
    if len(contracts_df) > 0:
        # 오늘 날짜
        today = datetime.today().date()
        
        for idx, row in contracts_df.iterrows():
            row_id = row.get('id')
            
            # 1. 금액 천 단위 콤마 포맷팅 함수
            def format_num(val):
                try:
                    # 문자가 섞여있어도 숫자만 추출해서 콤마 붙임
                    clean_val = "".join(filter(str.isdigit, str(val)))
                    return f"{int(clean_val):,}"
                except:
                    return val

            # 2. 계약 만료일 자동 판정 로직
            end_d_str = str(row.get('만료일', ''))
            try:
                end_date_obj = pd.to_datetime(end_d_str).date()
                if today > end_date_obj:
                    status_badge = "🔴 계약만료"
                elif (end_date_obj - today).days <= 30: # 30일 이내 만료시
                    status_badge = "🟠 만료임박"
                else:
                    status_badge = "🟢 계약중"
            except:
                status_badge = row.get('상태', '계약중')
            
            with st.container(border=True):
                col_t1, col_t2 = st.columns([2, 1])
                with col_t1:
                    st.markdown(f"### 🏢 {row.get('건물명', '')} {row.get('호실', '')}")
                with col_t2:
                    st.markdown(f"**{status_badge}**") # 판정된 상태 출력
                
                # 포맷팅 적용된 금액 출력
                deposit_f = format_num(row.get('보증금(원)', '0'))
                rent_f = format_num(row.get('월세(원)', '0'))
                pay_day = row.get('납부일', '25일')
                
                st.markdown(f"💰 **보증금**: {deposit_f}원 &nbsp;|&nbsp; 💵 **월세**: {rent_f}원 (매월 **{pay_day}**)")
                
                # 나머지 임차인/부동산 정보는 동일
                t_name = row.get('임차인', '')
                t_phone = row.get('임차인연락처', '')
                r_name = row.get('부동산명', '')
                r_phone = row.get('부동산연락처', '')
                
                st.markdown(f"👤 **임차인**: {t_name} ([전화](tel:{t_phone}) | [문자](sms:{t_phone})) &nbsp;/&nbsp; 🏠 **부동산**: {r_name} ([전화](tel:{r_phone}) | [문자](sms:{r_phone}))")
                
                # 날짜 출력 (만료 시 붉은색 강조)
                start_d = row.get('계약일', '')
                date_color = "#d9534f" if status_badge == "🔴 계약만료" else "#1f77b4"
                
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-top: 5px; margin-bottom: 5px;">
                        🗓️ <b>계약 기간</b> : <span style="color: {date_color}; font-weight: bold;">{start_d} ~ {end_d_str}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                # ... (이하 수정/삭제 버튼 및 폼 영역은 기존 코드 유지)

# ==========================================
# [2페이지] 지출 및 공사 장부 (한글화 및 에러 방지 마스터 버전)
# ==========================================
with tab2:
    st.subheader("💰 건물 유지보수 및 지출 장부")
    
    # 1. 데이터 불러올 때 영문 컬럼을 한글 UI에 맞게 매핑
    def load_expenses_korean():
        try:
            res = supabase.table("expenses").select("*").execute()
            data = res.data
        except Exception:
            data = []
            
        if not data:
            return pd.DataFrame(columns=["id", "날짜", "건물명", "호실", "카테고리", "내역", "비용(원)"])
        
        df = pd.DataFrame(data)
        
        # Supabase 컬럼명을 한글 표기명으로 변환
        rename_map = {
            "expense_date": "날짜",
            "building_name": "건물명",
            "room_number": "호실",
            "category": "카테고리",
            "description": "내역",
            "amount": "비용(원)"
        }
        df = df.rename(columns=rename_map)
        
        # 가독성을 위한 컬럼 순서 정렬
        desired_cols = ["id", "날짜", "건물명", "호실", "카테고리", "내역", "비용(원)"]
        existing_cols = [col for col in desired_cols if col in df.columns]
        other_cols = [col for col in df.columns if col not in desired_cols]
        
        return df[existing_cols + other_cols]

    # 최신 데이터 실시간 로드
    current_expenses_df = load_expenses_korean()

    # 🔍 검색 기능
    exp_search = st.text_input("🔍 지출 내역 검색", placeholder="건물명, 호실, 내역 또는 카테고리 검색", key="exp_search_input")
    
    display_expenses = current_expenses_df.copy()
    if exp_search and not display_expenses.empty:
        mask = display_expenses.apply(lambda row: row.astype(str).str.contains(exp_search, case=False).any(), axis=1)
        display_expenses = display_expenses[mask]
    
    # 💵 비용 합산 기능 (컬럼명 유연성 확보)
    total_cost = 0
    target_col = "비용(원)" if "비용(원)" in display_expenses.columns else ("amount" if "amount" in display_expenses.columns else None)
    
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
    
    # 지출 장부 표 출력
    if not display_expenses.empty:
        st.dataframe(display_expenses, use_container_width=True, hide_index=True)
    else:
        st.info("조건에 맞는 지출 내역이 없습니다.")
        
    st.markdown("---")
    st.markdown("#### ➕ 새로운 지출 내역 등록")
    
    with st.form("expense_add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        ex_bname = col1.text_input("건물명", placeholder="예: 부산 센토빌")
        ex_rname = col2.text_input("호실", placeholder="예: 302호")
        
        col3, col4 = st.columns(2)
        ex_category = col3.selectbox("카테고리", ["수리비", "공사비", "세금", "중개수수료", "기타"])
        ex_date = col4.date_input("날짜", value=datetime.today())
        
        ex_desc = st.text_input("상세 내역", placeholder="예: 도어락 교체")
        ex_amount = st.text_input("비용(원)", value="100,000")
        
        ex_submitted = st.form_submit_button("지출 내역 저장", type="primary")
        
        if ex_submitted:
            if not ex_bname or not ex_desc:
                st.warning("건물명과 내역은 필수 입력 항목입니다!")
            else:
                clean_amount = "".join(filter(str.isdigit, str(ex_amount)))
                
                # Supabase 테이블 구조와 일치하는 안전한 인서트 데이터 구성
                insert_data = {
                    "building_name": ex_bname,
                    "room_number": ex_rname,
                    "category": ex_category,
                    "expense_date": str(ex_date),
                    "description": ex_desc,
                    "amount": clean_amount
                }
                
                try:
                    supabase.table("expenses").insert(insert_data).execute()
                    st.success("클라우드에 안전하게 저장되었습니다!")
                    st.rerun()
                except Exception as e:
                    # 만약 category나 room_number 컬럼이 DB에 없을 경우를 대비한 2차 안전장치
                    try:
                        fallback_data = {
                            "building_name": ex_bname,
                            "expense_date": str(ex_date),
                            "description": f"[{ex_rname}] {ex_desc} ({ex_category})",
                            "amount": clean_amount
                        }
                        supabase.table("expenses").insert(fallback_data).execute()
                        st.success("클라우드에 안전하게 저장되었습니다! (기본 양식 적용)")
                        st.rerun()
                    except Exception as err:
                        st.error(f"데이터 저장 실패: {err}")

# ==========================================
# [3페이지] 지난 계약 및 매매 관리 (마스터 버전)
# ==========================================
with tab3:
    st.subheader("📁 지난 계약 및 매매 이력 장부")
    search_query = st.text_input("🔍 항목별 검색", placeholder="검색어를 입력하세요")
    
    if search_query and len(history_df) > 0:
        mask = history_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        filtered_history = history_df[mask]
    else:
        filtered_history = history_df
        
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
