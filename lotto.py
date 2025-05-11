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
    logs = []  # ✅ 로그 수집용 리스트

    def get_band(num):
        if 1 <= num <= 10:
            return '1-10'
        elif 11 <= num <= 20:
            return '11-20'
        elif 21 <= num <= 30:
            return '21-30'
        elif 31 <= num <= 40:
            return '31-40'
        elif 41 <= num <= 45:
            return '41-45'
        return 'out-of-range'

    def has_too_many_consecutive(numbers):
        numbers = sorted(numbers)
        consecutive_count = 0
        for i in range(len(numbers) - 1):
            if numbers[i + 1] - numbers[i] == 1:
                consecutive_count += 1
        return consecutive_count >= 2


    result = []
    tries = 0
    max_tries = num_sets * 100

    if len(expected_numbers) < 6:
        logs.append("❌ 예상수는 최소 6개 이상이어야 합니다.")
        return [], logs

    valid_fixed = [n for n in fixed_numbers if n in expected_numbers]

    while len(result) < num_sets and tries < max_tries:
        tries += 1
        comb = random.sample(expected_numbers, 6)

        if valid_fixed and not any(n in valid_fixed for n in comb):
            logs.append(f"✖️ 고정수 불포함: {comb}")
            continue


        if sorted(comb) in result:
            logs.append(f"✖️ 중복 조합 제거: {comb}")
            continue

        result.append(sorted(comb))

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


# ------------------- 여러 회차 데이터 가져오기 -------------------
def get_multiple_lotto_data(start_drw_no, count):
    base_url = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo="
    lotto_data_list = []
    for drw_no in range(start_drw_no, start_drw_no - count, -1):
        res = requests.get(base_url + str(drw_no))
        if res.status_code == 200:
            data = res.json()
            if data['returnValue'] == 'success':
                winning_numbers = [data[f'drwtNo{i}'] for i in range(1, 7)]
                bonus_number = data['bnusNo']
                lotto_data_list.append((winning_numbers, bonus_number))
                print(f"{drw_no}회 결과: {winning_numbers} + 보너스 {bonus_number}")
    return lotto_data_list


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


# ------------------- 제외수 포함 여부 확인 -------------------
def is_excluded(combo, excluded):
    return any(n in excluded for n in combo)


# ------------------- Streamlit UI 시작 -------------------


# ------------------- Streamlit UI 시작 -------------------


st.sidebar.header("고정수 선택 (각 조합에 반드시 1개 이상 포함)")
if 'fixed_numbers' not in st.session_state:
    st.session_state.fixed_numbers = []

# 예상수 선택 전에 세션에 expected_numbers_raw 초기화
if 'expected_numbers_raw' not in st.session_state:
    st.session_state.expected_numbers_raw = []

# 고정수 UI
fixed_numbers = st.sidebar.multiselect(
    "고정수", options=list(range(1, 46)), default=st.session_state.fixed_numbers
)
st.session_state.fixed_numbers = fixed_numbers

# 🔁 고정수 추가 시 예상수 raw에 자동 추가
for fn in fixed_numbers:
    if fn not in st.session_state.expected_numbers_raw:
        st.session_state.expected_numbers_raw.append(fn)

st.sidebar.header("예상수 선택 (조합은 이 숫자들로만 구성)")
expected_numbers_raw = st.sidebar.multiselect(
    "예상수 (6개 이상)", options=list(range(1, 46)), default=st.session_state.expected_numbers_raw
)

expected_numbers = list(set(expected_numbers_raw + fixed_numbers))
expected_numbers.sort()
st.session_state.expected_numbers_raw = expected_numbers_raw

auto_added = [n for n in fixed_numbers if n not in expected_numbers_raw]
if auto_added:
    st.sidebar.info(f"🧩 고정수 {auto_added} 는 예상수에 자동 포함되었습니다.")






# ------------------- 조합 생성 UI -------------------

st.title("로또 초강화 필터 조합 생성기")

if len(expected_numbers) < 6:
    st.error("예상수는 최소 6개 이상이어야 조합을 생성할 수 있습니다.")
else:
    st.subheader("1. 초강화 필터 조합 생성")
    num_sets = st.number_input("생성할 초강화 조합 개수 (10개 ~ 500개)", 10, 500, 100, step=10)

    if st.button("초강화 조합 생성"):
        combinations, logs = generate_ultra_filtered_combinations(
            expected_numbers=expected_numbers,
            fixed_numbers=fixed_numbers,
            num_sets=num_sets
        )

        if combinations:
            st.session_state['combinations'] = combinations
            st.success(f"{len(combinations)}개 조합 생성 완료!")
        else:
            st.warning("조건을 만족하는 조합을 생성하지 못했습니다. 예상수/고정수를 확인해주세요.")

            with st.expander("📄 상세 실패 로그 보기"):
                for line in logs[:50]:  # 최대 50개까지만 출력
                    st.text(line)



# ------------------- 조합 출력 -------------------
if 'combinations' in st.session_state:
    st.subheader("현재 생성된 초강화 조합 목록")
    for idx, comb in enumerate(st.session_state['combinations'], start=1):
        st.write(f"{idx:03d}: {comb}")

# ------------------- 분석 기능 (가상 또는 실제) -------------------
if 'combinations' in st.session_state:
    st.subheader("2. 모의추첨 / 실제 분석")
    analysis_mode = st.radio("분석 모드 선택", ["가상 모의추첨", "최근 회차 분석"])

    # ------------------- 가상 모의추첨 -------------------
    if analysis_mode == "가상 모의추첨":
        repeat_times = st.number_input("반복횟수(10~100)", 10, 100, 10, step=10)
        if st.button("가상 모의추첨 실행"):
            sim_results = []
            for i in range(repeat_times):
                win_nums = random.sample(range(1, 46), 6)
                bonus = random.choice([n for n in range(1, 46) if n not in win_nums])
                result_counter = {'1등': 0, '2등': 0, '3등': 0, '4등': 0, '5등': 0, '꽝': 0}
                for comb in st.session_state['combinations']:
                    prize = check_prize(comb, win_nums, bonus)
                    result_counter[prize] += 1
                sim_results.append({
                    "시뮬레이션": i + 1,
                    "당첨번호": sorted(win_nums),
                    "보너스번호": bonus,
                    **result_counter
                })

            # 결과 표시
            converted_results = [
                (entry["시뮬레이션"], entry["당첨번호"], entry["보너스번호"])
                for entry in sim_results
            ]
            df_recent = build_analysis_result_dataframe(converted_results, st.session_state['combinations'])
            styled_df = build_html_result_df(df_recent, fixed_numbers)
            st.subheader("📊 최근 회차 분석 결과 (고정수 하이라이트 포함)")
            st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)

            # 시각화 그래프
            grades = ['1등', '2등', '3등', '4등', '5등', '꽝']
            total_counts = df_recent[grades].sum()
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=grades, y=total_counts, name='총합',
                text=[f"{v}회" for v in total_counts], textposition='outside',
                marker_color='lightskyblue'
            ))
            fig.update_layout(
                barmode='group',
                title="최근 회차 분석 총계 결과",
                yaxis_title="당첨 횟수", xaxis_title="등수",
                template='plotly_dark', height=500
            )
            st.plotly_chart(fig)

    # ------------------- 실제 최근 회차 분석 -------------------
    elif analysis_mode == "최근 회차 분석":
        num_recent = st.number_input("최근 몇 회 분석?", 1, 50, 10)
        if st.button("최근 회차 분석 시작"):
            start_round = get_latest_round_number()
            round_results = []
            for drw_no in range(start_round, start_round - num_recent, -1):
                res = requests.get(f"https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={drw_no}")
                if res.status_code == 200 and res.json().get("returnValue") == "success":
                    data = res.json()
                    win_nums = [data[f'drwtNo{i}'] for i in range(1, 7)]
                    bonus = data['bnusNo']
                    round_results.append((drw_no, win_nums, bonus))

            df_recent = build_analysis_result_dataframe(round_results, st.session_state['combinations'])
            styled_df = build_html_result_df(df_recent, fixed_numbers)
            st.subheader("📊 최근 회차 분석 결과 (고정수 하이라이트 포함)")
            st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)

            # 막대 그래프
            grades = ['1등', '2등', '3등', '4등', '5등', '꽝']
            total_counts = df_recent[grades].sum()
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=grades, y=total_counts, name='총합',
                text=[f"{v}회" for v in total_counts], textposition='outside',
                marker_color='lightskyblue'
            ))
            fig.update_layout(
                barmode='group',
                title="최근 회차 분석 총계 결과",
                yaxis_title="당첨 횟수", xaxis_title="등수",
                template='plotly_dark', height=500
            )
            st.plotly_chart(fig)
