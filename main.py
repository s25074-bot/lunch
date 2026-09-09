import calendar
import datetime
import requests
import re
import streamlit as st

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 디자인 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="우리 학교 월간 급식 달력",
    page_icon="🍱",
    layout="wide"
)

st.markdown("""
<style>
    .meal-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        background-color: #ffffff;
        min-height: 180px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .meal-card-today {
        border: 2px solid #3182ce;
        background-color: #f7fafc;
    }
    .card-header {
        font-weight: bold;
        font-size: 1rem;
        margin-bottom: 8px;
        border-bottom: 1px solid #edf2f7;
        padding-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .today-badge {
        background-color: #3182ce;
        color: white;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
    }
    .meal-type-lunch {
        color: #2b6cb0;
        font-weight: bold;
        margin-top: 6px;
        margin-bottom: 2px;
    }
    .meal-type-dinner {
        color: #c53030;
        font-weight: bold;
        margin-top: 6px;
        margin-bottom: 2px;
    }
    .meal-type-other {
        color: #2f855a;
        font-weight: bold;
        margin-top: 6px;
        margin-bottom: 2px;
    }
    .meal-item {
        font-size: 0.85rem;
        color: #4a5568;
        line-height: 1.3;
    }
    .no-meal {
        color: #a0aec0;
        font-size: 0.85rem;
        font-style: italic;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 알레르기 식재료 대응표 정의
# -----------------------------------------------------------------------------
ALLERGY_MAP = {
    "1": "난류", "2": "우유", "3": "메밀", "4": "땅콩", "5": "대두",
    "6": "밀", "7": "게", "8": "새우", "9": "돼지고기", "10": "복숭아",
    "11": "토마토", "12": "아황산류", "13": "호두", "14": "닭고기",
    "15": "쇠고기", "16": "오징어", "17": "조개류", "18": "잣", "19": "새우"
}

# -----------------------------------------------------------------------------
# 3. 사이드바 설정
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ 설정")

if "NEIS_KEY" not in st.secrets:
    st.error("⚠️ Streamlit Secrets에 'NEIS_KEY'가 설정되지 않았습니다.")
    st.info("`.streamlit/secrets.toml` 파일 또는 Cloud Secrets에 `NEIS_KEY = '발급받은키'`를 등록해 주세요.")
    st.stop()

neis_key = st.secrets["NEIS_KEY"]

st.sidebar.subheader("학교 정보")
atpt_code = st.sidebar.text_input("시도교육청코드", value="B10", help="예: 서울 B10, 경기 J10 등")
sd_sch_code = st.sidebar.text_input("표준학교코드", value="7010057", help="예: 서울고등학교 7010057")

st.sidebar.markdown("---")
st.sidebar.subheader("알레르기 표시 설정")
convert_allergy = st.sidebar.toggle("알레르기 식품명으로 변환", value=False)

with st.sidebar.expander("ℹ️ 알레르기 번호-식재료 대응표"):
    for code, name in ALLERGY_MAP.items():
        st.write(f"**{code}**: {name}")

# -----------------------------------------------------------------------------
# 4. 데이터 파싱 및 API 요청 함수
# -----------------------------------------------------------------------------
def fetch_meal_data(api_key, office_code, school_code, year, month):
    _, last_day = calendar.monthrange(year, month)
    from_ymd = f"{year}{month:02d}01"
    to_ymd = f"{year}{month:02d}{last_day:02d}"
    
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCH_HOUL_VALUE": school_code,  # 파라미터명 수정 (CLEAN -> HOUL)
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # JSON 형식 응답인지 안전하게 확인
        try:
            data = response.json()
        except Exception:
            raise Exception("NEIS API가 JSON 형태가 아닌 응답을 반환했습니다. API KEY나 학교 코드를 확인해 주세요.")
        
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
        elif "RESULT" in data:
            if data["RESULT"]["CODE"] == "INFO-200":
                return []
            raise Exception(f"API 응답 에러 [{data['RESULT']['CODE']}]: {data['RESULT']['MESSAGE']}")
        return []
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"API 통신 실패: 인터넷 연결 또는 요청 URL/KEY를 확인해 주세요. ({e})")

def parse_menu(menu_str, convert_flag):
    if not menu_str:
        return []
    
    items = menu_str.split("<br/>")
    parsed_items = []
    
    for item in items:
        item = item.strip()
        if not item:
            continue
            
        if convert_flag:
            numbers = re.findall(r'\d+', item)
            clean_name = re.sub(r'[\d\.\s]+$', '', item).strip()
            
            if numbers:
                allergy_names = [ALLERGY_MAP.get(num, num) for num in numbers if num in ALLERGY_MAP]
                if allergy_names:
                    item = f"{clean_name} ({', '.join(allergy_names)})"
                else:
                    item = clean_name
            else:
                item = clean_name
                
        parsed_items.append(item)
        
    return parsed_items

# -----------------------------------------------------------------------------
# 5. 메인 화면 구성 및 상단 필터
# -----------------------------------------------------------------------------
st.title("🍱 우리 학교 월간 급식 달력")

now = datetime.datetime.now()
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    selected_year = st.selectbox("연도 선택", list(range(now.year - 1, now.year + 2)), index=1)
with col2:
    selected_month = st.selectbox("월 선택", list(range(1, 13)), index=now.month - 1)
with col3:
    meal_filter = st.radio(
        "급식 종류",
        ["전체 보기", "중식만 보기", "석식만 보기"],
        horizontal=True
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. 달력 그리드 출력
# -----------------------------------------------------------------------------
try:
    with st.spinner("급식 데이터를 가져오는 중입니다..."):
        raw_meals = fetch_meal_data(neis_key, atpt_code, sd_sch_code, selected_year, selected_month)
    
    meals_by_date = {}
    for row in raw_meals:
        ymd = row["MLSV_YMD"]
        meal_type = row["MMEAL_SC_NM"]
        menu_raw = row["DDISH_NM"]
        
        if ymd not in meals_by_date:
            meals_by_date[ymd] = []
            
        meals_by_date[ymd].append({
            "type": meal_type,
            "menu": parse_menu(menu_raw, convert_allergy)
        })

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(selected_year, selected_month)
    
    days_header = ["월", "화", "수", "목", "금"]
    cols = st.columns(5)
    for i, day_name in enumerate(days_header):
        cols[i].markdown(f"<h4 style='text-align: center; color: #4a5568;'>{day_name}</h4>", unsafe_allow_html=True)

    today_str = now.strftime("%Y%m%d")

    for week in month_days:
        week_cols = st.columns(5)
        for idx in range(5):
            day = week[idx]
            with week_cols[idx]:
                if day == 0:
                    st.write("")
                    continue
                
                date_ymd = f"{selected_year}{selected_month:02d}{day:02d}"
                is_today = (date_ymd == today_str)
                
                today_badge_html = '<span class="today-badge">TODAY</span>' if is_today else ''
                card_class = "meal-card meal-card-today" if is_today else "meal-card"
                
                card_html = f"""
                <div class="{card_class}">
                    <div class="card-header">
                        <span>{day}일</span>
                        {today_badge_html}
                    </div>
                """
                
                if date_ymd not in meals_by_date:
                    card_html += '<div class="no-meal">급식 없음</div>'
                else:
                    day_meals = meals_by_date[date_ymd]
                    
                    filtered_meals = []
                    for m in day_meals:
                        if meal_filter == "전체 보기":
                            filtered_meals.append(m)
                        elif meal_filter == "중식만 보기" and m["type"] == "중식":
                            filtered_meals.append(m)
                        elif meal_filter == "석식만 보기" and m["type"] == "석식":
                            filtered_meals.append(m)
                    
                    if not filtered_meals:
                        card_html += '<div class="no-meal">해당 식단 없음</div>'
                    else:
                        for m in filtered_meals:
                            if m["type"] == "중식":
                                type_class = "meal-type-lunch"
                            elif m["type"] == "석식":
                                type_class = "meal-type-dinner"
                            else:
                                type_class = "meal-type-other"
                                
                            card_html += f'<div class="{type_class}">[{m["type"]}]</div>'
                            for item in m["menu"]:
                                card_html += f'<div class="meal-item">• {item}</div>'
                                
                card_html += "</div>"
                st.markdown(card_html, unsafe_allow_html=True)

except Exception as e:
    st.error("⚠️ 화면 처리 또는 데이터를 불러오는 중 에러가 발생했습니다.")
    st.caption(f"상세 정보: {e}")
