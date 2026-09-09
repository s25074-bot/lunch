import calendar
import datetime
import re
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 디자인 CSS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="월간 학교 급식 달력", page_icon="📅", layout="wide")

ALLERGY_MAP = {
    1: "난류", 2: "우유", 3: "메밀", 4: "땅콩", 5: "대두",
    6: "밀", 7: "고등어", 8: "게", 9: "새우", 10: "돼지고기",
    11: "복숭아", 12: "토마토", 13: "아황산류", 14: "호두", 15: "닭고기",
    16: "쇠고기", 17: "오징어", 18: "조개류(굴/전복/홍합 포함)", 19: "잣",
}

# 🔥 인기 메뉴 키워드 리스트 (자동 감지용)
POPULAR_KEYWORDS = [
    "돈까스", "돈가스", "치킨", "닭강정", "떡볶이", "마라탕", "스파게티", 
    "파스타", "피자", "햄버거", "삼겹살", "갈비", "탕수육", "우동", 
    "짜장", "짬뽕", "연유", "푸딩", "아이스크림", "와플", "소세지", "소시지"
]

def replace_allergy_codes(dish_text, convert_to_text=True):
    """메뉴명 뒤의 알레르기 번호를 감지하여 한글 식재료명으로 치환합니다."""
    if not convert_to_text or not dish_text:
        return dish_text

    def convert_match(match):
        raw = match.group(0)
        nums = re.findall(r"\d+", raw)
        allergens = [ALLERGY_MAP[int(n)] for n in nums if int(n) in ALLERGY_MAP]
        if allergens:
            return f" :orange[[{', '.join(allergens)}]]"
        return raw

    pattern = r"\(?(\d+\.)+\)?"
    return re.sub(pattern, convert_match, dish_text)

def highlight_popular_dish(dish_name):
    """인기 메뉴 키워드가 들어있으면 🔥 뱃지를 추가합니다."""
    for keyword in POPULAR_KEYWORDS:
        if keyword in dish_name:
            return f"{dish_name} 🔥"
    return dish_name

# -----------------------------------------------------------------------------
# 2. 사이드바 설정
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 학교 정보 설정")
office_code = st.sidebar.text_input("시도교육청코드", value="T10", help="기본값: 제주특별자치도교육청(T10)")
school_code = st.sidebar.text_input("표준학교코드", value="9290088", help="기본값: 제주중앙고등학교(9290088)")

st.sidebar.markdown("---")
st.sidebar.subheader("🍽️ 알레르기 표시 설정")
show_allergen_names = st.sidebar.toggle(
    "알레르기 식품명으로 변환", value=True,
    help="체크 시 숫자(예: 1. 5.) 대신 [난류, 대두] 형태로 변환하여 표시합니다.",
)

with st.sidebar.expander("📖 나이스 알레르기 번호 안내표"):
    table_md = "\n".join([f"- **{k}번**: {v}" for k, v in ALLERGY_MAP.items()])
    st.markdown(table_md)

# -----------------------------------------------------------------------------
# 3. 세션 상태 관리 (연도/월 이동 버튼용)
# -----------------------------------------------------------------------------
today = datetime.date.today()

if "selected_year" not in st.session_state:
    st.session_state.selected_year = today.year
if "selected_month" not in st.session_state:
    st.session_state.selected_month = today.month

# 연월 변경 함수
def change_month(delta):
    new_m = st.session_state.selected_month + delta
    if new_m > 12:
        st.session_state.selected_month = 1
        st.session_state.selected_year += 1
    elif new_m < 1:
        st.session_state.selected_month = 12
        st.session_state.selected_year -= 1
    else:
        st.session_state.selected_month = new_m

# -----------------------------------------------------------------------------
# 4. 상단 헤더 및 연월 선택 / 빠른 이동 컨트롤
# -----------------------------------------------------------------------------
st.title("📅 우리 학교 월간 급식 달력")

col_prev, col_title, col_next = st.columns([1, 4, 1])
with col_prev:
    st.button("◀ 이전 달", on_click=change_month, args=(-1,), use_container_width=True)
with col_title:
    st.markdown(
        f"<h3 style='text-align: center; margin: 0;'>{st.session_state.selected_year}년 {st.session_state.selected_month}월 급식표</h3>", 
        unsafe_allow_html=True
    )
with col_next:
    st.button("다음 달 ▶", on_click=change_month, args=(1,), use_container_width=True)

st.markdown("")

col_y, col_m, col_filter = st.columns([1, 1, 2])
with col_y:
    year = st.selectbox(
        "연도 선택", options=list(range(today.year - 1, today.year + 2)), 
        key="selected_year"
    )
with col_m:
    month = st.selectbox(
        "월 선택", options=list(range(1, 13)), 
        key="selected_month"
    )
with col_filter:
    meal_filter = st.radio(
        "급식 종류 선택", options=["전체 보기", "중식만 보기", "석식만 보기"], index=0, horizontal=True
    )

# -----------------------------------------------------------------------------
# 5. API 요청 함수
# -----------------------------------------------------------------------------
def fetch_monthly_meals(key, ofcdc_code, schul_code, yr, mo):
    _, last_day = calendar.monthrange(yr, mo)
    from_ymd = f"{yr}{mo:02d}01"
    to_ymd = f"{yr}{mo:02d}{last_day:02d}"

    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": key, "Type": "json", "pIndex": 1, "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ofcdc_code, "SD_SCHUL_CODE": schul_code,
        "MLSV_FROM_YMD": from_ymd, "MLSV_TO_YMD": to_ymd,
    }
    response = requests.get(url, params=params, timeout=7)
    return response.json()

if "NEIS_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 `NEIS_KEY`가 설정되어 있지 않습니다.")
    st.stop()

neis_key = st.secrets["NEIS_KEY"]

# -----------------------------------------------------------------------------
# 6. 데이터 파싱 및 메인 달력 출력
# -----------------------------------------------------------------------------
try:
    with st.spinner(f"{year}년 {month}월 급식 정보를 불러오는 중..."):
        res_data = fetch_monthly_meals(neis_key, office_code, school_code, year, month)

    meal_dict = {}
    popular_count = 0  # 이번 달 인기 메뉴 총 갯수 통계용
    
    if "mealServiceDietInfo" in res_data:
        rows = res_data["mealServiceDietInfo"][1]["row"]
        for row in rows:
            ymd = row.get("MLSV_YMD")
            meal_type = row.get("MMEAL_SC_NM", "급식")
            dish = row.get("DDISH_NM", "")

            formatted_dish = replace_allergy_codes(dish, convert_to_text=show_allergen_names)
            dish_lines = [d.strip() for d in formatted_dish.replace("<br/>", "\n").split("\n") if d.strip()]
            
            # 인기 메뉴 하이라이팅 처리
            highlighted_lines = []
            for d in dish_lines:
                h_dish = highlight_popular_dish(d)
                if "🔥" in h_dish:
                    popular_count += 1
                highlighted_lines.append(h_dish)

            meal_dict.setdefault(ymd, {})[meal_type] = highlighted_lines

    # 💡 참신한 기능 1: 오늘의 급식 요약 카드 (상단 배치)
    today_ymd = today.strftime("%Y%m%d")
    if year == today.year and month == today.month and today_ymd in meal_dict:
        st.info("💡 **오늘의 급식 요약**")
        today_meals = meal_dict[today_ymd]
        t_cols = st.columns(len(today_meals))
        for idx, (m_type, dishes) in enumerate(today_meals.items()):
            with t_cols[idx]:
                st.markdown(f"**[{m_type}]**")
                st.write(", ".join([d.split(" :orange")[0] for d in dishes]))

    # 💡 참신한 기능 2: 사이드바 식단 통계 요약
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 이번 달 식단 통계")
    st.sidebar.metric("총 급식 일수", f"{len(meal_dict)}일")
    st.sidebar.metric("인기 메뉴(🔥) 등장 횟수", f"{popular_count}회")

    # 달력 구성
    month_cal = calendar.monthcalendar(year, month)
    weekdays_kr = ["월", "화", "수", "목", "금"]

    st.markdown("---")

    # 요일 헤더
    header_cols = st.columns(5)
    for idx, w_name in enumerate(weekdays_kr):
        header_cols[idx].markdown(f"<h4 style='text-align: center; color: #4A5568;'>{w_name}</h4>", unsafe_allow_html=True)

    # 텍스트 파일 다운로드용 문자열 누적
    download_text = f"=== {year}년 {month}월 급식표 ===\n\n"

    for week in month_cal:
        cols = st.columns(5)
        has_school_day = False

        for i in range(5):
            day = week[i]
            with cols[i]:
                if day == 0:
                    st.empty()
                else:
                    has_school_day = True
                    ymd_str = f"{year}{month:02d}{day:02d}"
                    day_meals = meal_dict.get(ymd_str, {})
                    is_today = (year == today.year and month == today.month and day == today.day)

                    download_text += f"[{month}월 {day}일 ({weekdays_kr[i]})]\n"

                    with st.container(border=True):
                        if is_today:
                            st.markdown(f"**{month}월 {day}일 ({weekdays_kr[i]})** :orange-background[**TODAY**]")
                        else:
                            st.markdown(f"**{month}월 {day}일 ({weekdays_kr[i]})**")

                        st.divider()

                        if not day_meals:
                            st.caption("급식 없음 (휴업/방학)")
                            download_text += " 급식 없음\n"
                        else:
                            displayed_count = 0

                            # 중식 출력
                            if meal_filter in ["전체 보기", "중식만 보기"] and "중식" in day_meals:
                                displayed_count += 1
                                st.markdown(":blue[**🍱 중식**]")
                                download_text += " <중식>\n"
                                for dish in day_meals["중식"]:
                                    st.markdown(f"<span style='font-size:0.85rem;'>• {dish}</span>", unsafe_allow_html=True)
                                    download_text += f"  - {dish.split(' :orange')[0]}\n"

                            # 석식 출력
                            if meal_filter in ["전체 보기", "석식만 보기"] and "석식" in day_meals:
                                displayed_count += 1
                                if meal_filter == "전체 보기" and "중식" in day_meals:
                                    st.write("")
                                st.markdown(":red[**🌙 석식**]")
                                download_text += " <석식>\n"
                                for dish in day_meals["석식"]:
                                    st.markdown(f"<span style='font-size:0.85rem;'>• {dish}</span>", unsafe_allow_html=True)
                                    download_text += f"  - {dish.split(' :orange')[0]}\n"

                            # 기타 급식 (조식 등)
                            if meal_filter == "전체 보기":
                                for m_type, dishes in day_meals.items():
                                    if m_type not in ["중식", "석식"]:
                                        displayed_count += 1
                                        st.markdown(f":green[**🍴 {m_type}**]")
                                        download_text += f" <{m_type}>\n"
                                        for dish in dishes:
                                            st.markdown(f"<span style='font-size:0.85rem;'>• {dish}</span>", unsafe_allow_html=True)
                                            download_text += f"  - {dish.split(' :orange')[0]}\n"

                            if displayed_count == 0:
                                st.caption("해당 식단 없음")
                                download_text += " 해당 식단 없음\n"

                    download_text += "\n"

        if has_school_day:
            st.write("")

    # 💡 참신한 기능 3: 월간 식단표 텍스트 다운로드 버튼 (하단)
    st.markdown("---")
    st.download_button(
        label="📄 이번 달 식단표 텍스트(.txt)로 다운로드",
        data=download_text,
        file_name=f"{year}년_{month}월_급식표.txt",
        mime="text/plain",
    )

except requests.exceptions.RequestException as e:
    st.error(f"⚠️ 나이스 API 통신 오류: 네트워크 상태를 확인해 주세요. ({e})")
except Exception as e:
    st.error(f"⚠️ 화면 구성 중 오류가 발생했습니다: {e}")
