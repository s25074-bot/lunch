# 1. 상단 급식 종류 선택 라디오 버튼
meal_filter = st.radio(
    "급식 종류",
    ["전체 보기", "중식만 보기", "석식만 보기"],
    horizontal=True
)

# 2. 선택한 필터에 따라 해당 날짜 카드에 메뉴 필터링
filtered_meals = []
for m in day_meals:
    if meal_filter == "전체 보기":
        filtered_meals.append(m)
    elif meal_filter == "중식만 보기" and m["type"] == "중식":
        filtered_meals.append(m)
    elif meal_filter == "석식만 보기" and m["type"] == "석식":
        filtered_meals.append(m)

# 필터에 걸러진 메뉴가 없다면 "해당 식단 없음" 표시
if not filtered_meals:
    card_html += '<div class="no-meal">해당 식단 없음</div>'
