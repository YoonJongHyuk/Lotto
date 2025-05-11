# ------------------- 라이브러리 임포트 -------------------
import streamlit as st
import random
import requests
import re
import plotly.graph_objects as go
import pandas as pd
from bs4 import BeautifulSoup


# ------------------- 번호 조합 필터링 함수 -------------------
def generate_ultra_filtered_combinations(expected_numbers, fixed_numbers=[], num_sets=100):
    logs = []
    result = []
    seen = set()
    tries = 0
    max_tries = num_sets * 100

    if len(expected_numbers) < 6:
        logs.append("❌ 예상수는 최소 6개 이상이어야 합니다.")
        return [], logs

    valid_fixed = [n for n in fixed_numbers if n in expected_numbers]

    while len(result) < num_sets and tries < max_tries:
        tries += 1
        comb = random.sample(expected_numbers, 6)
        key = tuple(sorted(comb))

        if valid_fixed and not any(n in valid_fixed for n in comb):
            logs.append(f"✖️ 고정수 불포함: {comb}")
            continue

        if key in seen:
            logs.append(f"✖️ 중복 조합 제거: {comb}")
            continue

        seen.add(key)
        result.append(list(key))

    return result, logs


# ------------------- 등수 판별 함수 -------------------
def check_prize(user_numbers, winning_numbers, bonus_number):
    match_count = len(set(user_numbers) & set(winning_numbers))
    bonus_match = bonus_number in user_numbers
    if match_count == 6: return '1등'
    elif match_count == 5 and bonus_match: return '2등'
    elif match_count == 5: return '3등'
    elif match_count == 4: return '4등'
    elif match_count == 3: return '5등'
    else: return '꽝'


# ------------------- 최신 회차 번호 가져오기 -------------------
def get_latest_round_number():
    url = "https://dhlottery.co.kr/common.do?method=main"
    try:
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")
        max_numb = soup.find(name="strong", attrs={"id": "lottoDrwNo"}).text
        return int(max_numb)
    except Exception as e:
        print("최신 회차 가져오기 실패:", e)


# ------------------- 분석 결과 DataFrame 생성 -------------------
def build_analysis_result_dataframe(round_results, combinations):
    all_rows = []
    for round_no, winning_numbers, bonus_number in round_results:
        grade_counter = {'1등': 0, '2등': 0, '3등': 0, '4등': 0, '5등': 0, '꽝': 0}
        for comb in combinations:
            grade = check_prize(comb, winning_numbers, bonus_number)
            grade_counter[grade] += 1
        row = {
            "회차": round_no,
            "당첨번호": winning_numbers,
            "보너스번호": bonus_number,
            **grade_counter
        }
        all_rows.append(row)
    return pd.DataFrame(all_rows)


# ------------------- 숫자 강조용 스타일 함수 -------------------
def style_number(n, fixed_numbers):
    if n in fixed_numbers:
        return f'<span style="display:inline-block; background:#ff4d4d; color:white; padding:4px 8px; margin:2px; border-radius:6px;">{n}</span>'
    else:
        return f'<span style="display:inline-block; background:#333; color:white; padding:4px 8px; margin:2px; border-radius:6px;">{n}</span>'


# ------------------- HTML 표시용 테이블 변환 -------------------
def build_html_result_df(df, fixed_numbers):
    df_html = df.copy()
    df_html["당첨번호"] = df_html["당첨번호"].apply(
        lambda nums: " ".join([style_number(n, fixed_numbers) for n in nums])
    )
    return df_html


# ------------------- Streamlit UI 시작 -------------------

st.set_page_config(page_title="로또 초강화 필터", layout="wide")

# 세션 초기화
if 'combinations' not in st.session_state:
    st.session_state.combinations = []

# 사이드바 - 고정수 및 예상수 입력
st.sidebar.header("고정수 선택 (각 조합에 반드시 1개 이상 포함)")
fixed_numbers = st.sidebar.multiselect(
    "고정수", options=list(range(1, 46)), default=[]
)

st.sidebar.header("예상수 선택 (조합은 이 숫자들로만 구성)")
expected_numbers_raw = st.sidebar.multiselect(
    "예상수 (6개 이상)", options=list(range(1, 46)), default=[]
)

# 고정수를 예상수에 자동 포함
expected_numbers = sorted(set(expected_numbers_raw + fixed_numbers))

# 예상수 부족 시 에러
if len(expected_numbers_raw) < 6:
    st.error("예상수는 최소 6개 이상 선택해야 합니다.")

# 본문
st.title("🎯 로또 초강화 필터 조합 생성기")

st.subheader("1. 조합 생성")
num_sets = st.number_input("조합 개수 (10 ~ 500)", 10, 500, 100, step=10)

if st.button("✅ 조합 생성"):
    combinations, logs = generate_ultra_filtered_combinations(
        expected_numbers=expected_numbers,
        fixed_numbers=fixed_numbers,
        num_sets=num_sets
    )
    if combinations:
        st.session_state.combinations = combinations
        st.success(f"✨ 총 {len(combinations)}개 조합 생성 완료!")
    else:
        st.warning("조건을 만족하는 조합을 생성하지 못했습니다.")
        with st.expander("🔍 실패 로그 보기"):
            for line in logs[:50]:
                st.text(line)

# 조합 출력
if st.session_state.combinations:
    st.subheader("🔢 생성된 조합")
    for idx, comb in enumerate(st.session_state.combinations, 1):
        st.write(f"{idx:03d}: {comb}")

# 분석 기능
if st.session_state.combinations:
    st.subheader("2. 분석 모드")
    analysis_mode = st.radio("분석 선택", ["가상 모의추첨", "최근 회차 분석"])

    if analysis_mode == "가상 모의추첨":
        repeat_times = st.number_input("반복 횟수", 10, 100, 10, step=10)
        if st.button("🎲 모의추첨 실행"):
            sim_results = []
            for i in range(repeat_times):
                win_nums = random.sample(range(1, 46), 6)
                bonus = random.choice([n for n in range(1, 46) if n not in win_nums])
                result_counter = {'1등': 0, '2등': 0, '3등': 0, '4등': 0, '5등': 0, '꽝': 0}
                for comb in st.session_state.combinations:
                    grade = check_prize(comb, win_nums, bonus)
                    result_counter[grade] += 1
                sim_results.append((i + 1, win_nums, bonus))

            df_result = build_analysis_result_dataframe(sim_results, st.session_state.combinations)
            styled_df = build_html_result_df(df_result, fixed_numbers)
            st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    elif analysis_mode == "최근 회차 분석":
        num_recent = st.number_input("최근 몇 회 분석할까요?", 1, 50, 10)
        if st.button("📈 최근 회차 분석"):
            start_round = get_latest_round_number()
            round_results = []
            for drw_no in range(start_round, start_round - num_recent, -1):
                res = requests.get(f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={drw_no}")
                if res.status_code == 200 and res.json().get("returnValue") == "success":
                    data = res.json()
                    win_nums = [data[f'drwtNo{i}'] for i in range(1, 7)]
                    bonus = data['bnusNo']
                    round_results.append((drw_no, win_nums, bonus))

            df_result = build_analysis_result_dataframe(round_results, st.session_state.combinations)
            styled_df = build_html_result_df(df_result, expected_numbers)
            st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)
