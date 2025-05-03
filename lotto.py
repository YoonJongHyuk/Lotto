import streamlit as st
import random
import requests
import re
import plotly.graph_objects as go
import pandas as pd

# import os
# os.system("streamlit run lotto.py")

# ------------------- 함수 정의 먼저 -------------------

def generate_ultra_filtered_combinations(fixed_numbers, num_sets=100):
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

    def has_too_many_consecutive(numbers):
        numbers = sorted(numbers)
        consecutive_count = 0
        for i in range(len(numbers)-1):
            if numbers[i+1] - numbers[i] == 1:
                consecutive_count += 1
        return consecutive_count >= 2

    result = []
    tries = 0
    max_tries = num_sets * 50

    while len(result) < num_sets and tries < max_tries:
        tries += 1
        comb = random.sample(fixed_numbers, 6)

        even = [n for n in comb if n % 2 == 0]
        if not (3 <= len(even) <= 4):
            continue

        bands = {get_band(n) for n in comb}
        if len(bands) < 4:
            continue

        band_counter = {}
        for n in comb:
            b = get_band(n)
            band_counter[b] = band_counter.get(b, 0) + 1
        if any(count > 2 for count in band_counter.values()):
            continue

        if max(comb) - min(comb) < 15:
            continue

        far_apart = [abs(a-b) >= 10 for a in comb for b in comb if a != b]
        if far_apart.count(True) < 2:
            continue

        if has_too_many_consecutive(comb):
            continue

        total_sum = sum(comb)
        if not (100 <= total_sum <= 200):
            continue

        if sorted(comb) in result:
            continue

        result.append(sorted(comb))

    return result

def check_prize(user_numbers, winning_numbers, bonus_number):
    match_count = len(set(user_numbers) & set(winning_numbers))
    bonus_match = bonus_number in user_numbers

    if match_count == 6:
        return '1등'
    elif match_count == 5 and bonus_match:
        return '2등'
    elif match_count == 5:
        return '3등'
    elif match_count == 4:
        return '4등'
    elif match_count == 3:
        return '5등'
    else:
        return '꽝'

def get_latest_round_number():
    url = "https://www.dhlottery.co.kr/gameResult.do?method=byWin"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            match = re.search(r"제(\d+)회", res.text)
            if match:
                return int(match.group(1))
    except Exception as e:
        print("최신 회차 가져오기 실패:", e)
    return 1168  # 기본값


def get_multiple_lotto_data(start_drw_no, count):
    base_url = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo="
    lotto_data_list = []
    for drw_no in range(start_drw_no, start_drw_no - count, -1):
        res = requests.get(base_url + str(drw_no))
        if res.status_code == 200:
            data = res.json()
            if data['returnValue'] == 'success':
                winning_numbers = [
                    data['drwtNo1'],
                    data['drwtNo2'],
                    data['drwtNo3'],
                    data['drwtNo4'],
                    data['drwtNo5'],
                    data['drwtNo6']
                ]
                bonus_number = data['bnusNo']
                lotto_data_list.append((winning_numbers, bonus_number))
                print(f"{drw_no}회 결과: {winning_numbers} + 보너스 {bonus_number}")



    return lotto_data_list

def build_analysis_result_dataframe(round_results, combinations):
    """
    round_results: List of tuples → [(회차, 당첨번호, 보너스번호), ...]
    combinations: 필터링된 조합 리스트
    """
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
            **grade_counter  # 등수별 카운트 삽입
        }
        all_rows.append(row)

    return pd.DataFrame(all_rows)


def highlight_fixed_numbers(val):
    try:
        numbers = list(map(int, val.split(", ")))
        if any(num in fixed_numbers for num in numbers):
            return "background-color: #ffcccc"
    except:
        pass
    return ""


def style_number(n, fixed_numbers):
    if n in fixed_numbers:
        return f'<span style="display:inline-block; background:#ff4d4d; color:white; padding:4px 8px; margin:2px; border-radius:6px;">{n}</span>'
    else:
        return f'<span style="display:inline-block; background:#333; color:white; padding:4px 8px; margin:2px; border-radius:6px;">{n}</span>'


def build_html_result_df(df, fixed_numbers):
    df_html = df.copy()
    df_html["당첨번호"] = df_html["당첨번호"].apply(
        lambda nums: " ".join([style_number(n, fixed_numbers) for n in nums])
    )
    return df_html


# ------------------- 여기까지 함수 영역 -------------------

# ------------------- Streamlit UI 영역 시작 -------------------

st.sidebar.header("고정수 직접 선택")

fixed_numbers_selected = st.sidebar.multiselect(
    "고정수 선택 (6개 이상 12개 이하)", 
    options=list(range(1, 46)),
    default=[7, 27, 14, 23, 10, 33, 12, 31, 38, 42]
)

if len(fixed_numbers_selected) < 6 or len(fixed_numbers_selected) > 12:
    st.sidebar.error("고정수는 6개 이상 12개 이하로 선택해주세요.")
    fixed_numbers = None
else:
    fixed_numbers = fixed_numbers_selected

st.title("로또 초강화 필터 조합 생성기")

# ------------------- 초강화 조합 생성 -------------------

# --------------------- 초강화 조합 생성 ---------------------

if fixed_numbers:
    st.subheader("1. 초강화 필터 조합 생성")

    num_sets = st.number_input(
        "생성할 초강화 조합 개수 (10개 ~ 500개)", 
        min_value=10, 
        max_value=500, 
        value=100, 
        step=10
    )

    if st.button("초강화 조합 생성"):
        combinations = generate_ultra_filtered_combinations(fixed_numbers, num_sets=num_sets)
        st.session_state['combinations'] = combinations
        st.success(f"초강화 조합 {len(combinations)}개 생성 완료!")

# ✅ 생성 여부와 관계 없이 항상 표시
if 'combinations' in st.session_state:
    st.subheader("현재 생성된 초강화 조합 목록")
    for idx, comb in enumerate(st.session_state['combinations'], start=1):
        st.write(f"{idx:03d}: {comb}")




# ------------------- 모의추첨 및 분석 -------------------

if 'combinations' in st.session_state:
    st.subheader("2. 모의추첨 / 실제 분석")

    analysis_mode = st.radio("분석 모드 선택", ["가상 모의추첨", "최근 회차 분석"])

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

            converted_results = [
                (entry["시뮬레이션"], entry["당첨번호"], entry["보너스번호"])
                for entry in sim_results
            ]

            df_recent = build_analysis_result_dataframe(converted_results, st.session_state['combinations'])
  
            styled_df = build_html_result_df(df_recent, fixed_numbers)
            st.subheader("📊 최근 회차 분석 결과 (고정수 하이라이트 포함)")
            st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)


            # 시각화
            grades = ['1등', '2등', '3등', '4등', '5등', '꽝']
            total_counts = df_recent[grades].sum()

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=grades,
                    y=total_counts,
                    name='총합',
                    text=[f"{v}회" for v in total_counts],  # ← 숫자 표시용 텍스트
                    textposition='outside',                # ← 막대 바깥쪽에 표시
                    marker_color='lightskyblue'
                )
            )

            fig.update_layout(
                barmode='group',
                title="최근 회차 분석 총계 결과",
                yaxis_title="당첨 횟수",
                xaxis_title="등수",
                template='plotly_dark',
                height=500,
                uniformtext_minsize=8,
                uniformtext_mode='hide'
            )

            st.plotly_chart(fig)

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

            def build_analysis_result_dataframe(round_results, combinations):
                all_rows = []
                for round_no, win_nums, bonus in round_results:
                    result_counter = {'1등': 0, '2등': 0, '3등': 0, '4등': 0, '5등': 0, '꽝': 0}
                    for comb in combinations:
                        prize = check_prize(comb, win_nums, bonus)
                        result_counter[prize] += 1
                    all_rows.append({
                        "회차": round_no,
                        "당첨번호": win_nums,
                        "보너스번호": bonus,
                        **result_counter
                    })
                return pd.DataFrame(all_rows)

            df_recent = build_analysis_result_dataframe(round_results, st.session_state['combinations'])  
            styled_df = build_html_result_df(df_recent, fixed_numbers)
            st.subheader("📊 최근 회차 분석 결과 (고정수 하이라이트 포함)")
            st.write(styled_df.to_html(escape=False, index=False), unsafe_allow_html=True)

            # 시각화
            grades = ['1등', '2등', '3등', '4등', '5등', '꽝']
            total_counts = df_recent[grades].sum()

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=grades,
                    y=total_counts,
                    name='총합',
                    text=[f"{v}회" for v in total_counts],  # ← 숫자 표시용 텍스트
                    textposition='outside',                # ← 막대 바깥쪽에 표시
                    marker_color='lightskyblue'
                )
            )

            fig.update_layout(
                barmode='group',
                title="최근 회차 분석 총계 결과",
                yaxis_title="당첨 횟수",
                xaxis_title="등수",
                template='plotly_dark',
                height=500,
                uniformtext_minsize=8,
                uniformtext_mode='hide'
            )

            st.plotly_chart(fig)

    
