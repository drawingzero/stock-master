import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import pandas as pd
import json
import datetime
import time
import re

# 1. 사이트 설정 및 디자인
st.set_page_config(page_title="Stock Master AI", page_icon="🎨", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { background-color: #ff4bb4; color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    .stTab { font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. API 키 세션 관리
if 'api_key' not in st.session_state:
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

if 'theme_result' not in st.session_state:
    st.session_state.theme_result = ""

with st.sidebar:
    st.header("⚙️ Account")
    if not st.session_state.api_key:
        new_key = st.text_input("Gemini API Key를 입력하세요", type="password")
        if st.button("로그인"):
            st.session_state.api_key = new_key
            st.rerun()
    else:
        st.success("✅ 연결됨")
        if st.button("로그아웃"):
            st.session_state.api_key = ""
            st.session_state.theme_result = ""
            st.rerun()
    st.divider()
    st.caption("비밀 금고(Secrets) 설정 시 자동 로그인됩니다.")

# 3. 메인 콘텐츠
st.title("🎨 Stock Master AI")

# 사이트별 설정 (라벨 / 프롬프트 지시문 / JSON 예시 포맷)
SITE_INFO = {
    "shutterstock": {
        "label": "셔터스톡 (영문 35개)",
        "instruction": "셔터스톡(영문35개)",
        "example": '"shutterstock": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."}',
    },
    "adobe": {
        "label": "어도비 (영문 30개, 앞10개 중요)",
        "instruction": "어도비(영문30개, 앞10개중요)",
        "example": '"adobe": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."}',
    },
    "tongro": {
        "label": "통로/유토 (한글 25개)",
        "instruction": "통로/유토(한글25개)",
        "example": '"tongro": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."}',
    },
    "getty": {
        "label": "게티 (한글 20개)",
        "instruction": "게티(한글20개)",
        "example": '"getty": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."}',
    },
    "miricanvas": {
        "label": "미리캔버스 (한글 10개)",
        "instruction": "미리캔버스(한글10개)",
        "example": '"miricanvas": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."}',
    },
}
SITE_KEYS = ["shutterstock", "adobe", "tongro", "getty", "miricanvas"]

# 기본으로 사용할 모델 (목록 조회가 실패해도 이 값으로 동작)
DEFAULT_MODEL = "gemini-2.5-flash"

# 무료 요금제는 분당 요청 수가 제한돼 있어서(429 RESOURCE_EXHAUSTED),
# 에러가 나면 구글이 알려주는 대기 시간만큼 자동으로 기다렸다가 다시 시도합니다.
def generate_with_retry(client, spinner_label, max_retries=5, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as e:
            err_text = str(e)
            is_quota_error = ("RESOURCE_EXHAUSTED" in err_text) or ("429" in err_text)
            if not is_quota_error or attempt == max_retries:
                raise  # 할당량 문제가 아니거나, 재시도를 다 써버렸으면 그대로 에러 발생시킴

            # 에러 메시지 안의 'retryDelay': '52s' 같은 값을 찾아서 대기 시간으로 사용
            match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)", err_text)
            wait_seconds = int(match.group(1)) if match else 20
            wait_seconds += 2  # 여유 시간 살짝 추가

            with st.spinner(
                spinner_label + f" — 무료 요금제 사용량 한도에 걸려서 {wait_seconds}초 대기 후 자동 재시도합니다 "
                f"({attempt}/{max_retries})..."
            ):
                time.sleep(wait_seconds)
    return None  # 이론상 도달하지 않음


# 대기 없이 딱 한 번만 시도. 사용량 한도(429)에 걸리면 나중에 재시도하도록 표시만 해두고 넘어갑니다.
def try_generate_once(client, **kwargs):
    try:
        return True, client.models.generate_content(**kwargs), None
    except Exception as e:
        err_text = str(e)
        is_quota_error = ("RESOURCE_EXHAUSTED" in err_text) or ("429" in err_text)
        return False, None, (err_text, is_quota_error)


# AI 응답(JSON 텍스트)을 표에 넣을 행(row) 리스트로 변환
def parse_rows_from_response(response, file_name, selected_sites):
    content_text = response.text.strip()
    if content_text.startswith("```"):
        content_text = content_text.split("```")[1]
        if content_text.startswith("json"):
            content_text = content_text[4:]

    raw_data = json.loads(content_text.strip())
    rows = []
    for site, content in raw_data.items():
        if site not in selected_sites:
            continue  # 선택 안 한 사이트는 결과에 안전하게 제외
        rows.append({
            "파일명": file_name,
            "사이트": site,
            "타이틀": content.get('title', ''),
            "키워드": content.get('keywords', ''),
        })
    return rows

if st.session_state.api_key:
    client = genai.Client(api_key=st.session_state.api_key)

    try:
        # 사용 가능한 flash 모델 자동 탐색 (실패하면 DEFAULT_MODEL 사용)
        selected_model_name = DEFAULT_MODEL
        try:
            candidates = []
            for m in client.models.list():
                actions = getattr(m, "supported_actions", None) or []
                name = getattr(m, "name", "") or ""
                if "generateContent" in actions and "flash" in name.lower():
                    candidates.append(name)
            if candidates:
                selected_model_name = candidates[0].replace("models/", "")
        except Exception:
            pass  # 목록 조회 실패해도 DEFAULT_MODEL로 계속 진행

        tab1, tab2 = st.tabs(["🔍 키워드 생성", "💡 시장 분석 & 테마 기획"])

        with tab1:
            st.subheader("이미지 분석 및 사이트별 키워드 추출")

            st.write("**생성할 사이트 선택**")
            cols = st.columns(len(SITE_KEYS))
            selected_sites = []
            for col, key in zip(cols, SITE_KEYS):
                with col:
                    checked = st.checkbox(SITE_INFO[key]["label"], value=True, key="chk_" + key)
                    if checked:
                        selected_sites.append(key)

            uploaded_files = st.file_uploader("이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

            run_clicked = st.button("🚀 분석 시작")

            if run_clicked and not selected_sites:
                st.warning("사이트를 최소 1개 이상 선택해주세요.")

            if uploaded_files and run_clicked and selected_sites:
                all_rows = []
                pending = []  # 사용량 한도(429)로 나중에 재시도할 (파일, 이미지) 목록

                instructions = ", ".join(SITE_INFO[key]["instruction"] for key in selected_sites)
                examples = ",\n                  ".join(SITE_INFO[key]["example"] for key in selected_sites)

                prompt = (
                    "스톡 전문가로서 이미지를 분석해 " + instructions +
                    " 검색량이 높은 단어로 구성된 키워드와 제목을 JSON으로 추출하세요.\n\n"
                    "반드시 아래의 JSON 포맷을 그대로 준수하여 출력해야 하며, 다른 설명이나 마크다운 백틱은 절대 포함하지 마세요.\n\n"
                    "{\n                  " + examples + "\n                }"
                )

                status_placeholder = st.empty()
                results_placeholder = st.empty()

                def render_results():
                    with results_placeholder.container():
                        if all_rows:
                            st.dataframe(pd.DataFrame(all_rows), use_container_width=True)

                # 1차: 대기 없이 빠르게 한 번씩만 시도. 성공하는 대로 바로 표에 띄웁니다.
                status_placeholder.info(f"이미지 {len(uploaded_files)}개 처리 중 (1차 시도)...")
                for uploaded_file in uploaded_files:
                    image = Image.open(uploaded_file)
                    ok, response, err = try_generate_once(
                        client,
                        model=selected_model_name,
                        contents=[prompt, image],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        ),
                    )
                    if ok:
                        try:
                            all_rows.extend(parse_rows_from_response(response, uploaded_file.name, selected_sites))
                            render_results()
                        except json.JSONDecodeError:
                            st.error("파싱 실패: '" + uploaded_file.name + "' 이미지의 AI 응답 형식이 올바르지 않습니다.")
                            with st.expander("AI 원본 응답 보기 (" + uploaded_file.name + ")"):
                                st.code(response.text)
                    else:
                        err_text, is_quota_error = err
                        if is_quota_error:
                            pending.append((uploaded_file, image))
                        else:
                            st.error("오류 발생 (" + uploaded_file.name + "): " + err_text)

                # 2차: 사용량 한도에 걸렸던 파일들만 대기하면서 재시도
                if pending:
                    status_placeholder.warning(
                        f"{len(pending)}개 파일이 무료 사용량 한도에 걸렸어요. 대기 후 순서대로 재시도할게요..."
                    )
                    for uploaded_file, image in pending:
                        response = generate_with_retry(
                            client,
                            "'" + uploaded_file.name + "' 재시도 중",
                            model=selected_model_name,
                            contents=[prompt, image],
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                            ),
                        )
                        try:
                            all_rows.extend(parse_rows_from_response(response, uploaded_file.name, selected_sites))
                            render_results()
                        except json.JSONDecodeError:
                            st.error("파싱 실패: '" + uploaded_file.name + "' 이미지의 AI 응답 형식이 올바르지 않습니다.")
                            with st.expander("AI 원본 응답 보기 (" + uploaded_file.name + ")"):
                                st.code(response.text)

                status_placeholder.success("모든 처리가 완료됐어요! ✅")

                if all_rows:
                    df = pd.DataFrame(all_rows)
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    st.download_button(
                        label="📥 CSV 다운로드",
                        data=csv_data,
                        file_name="stock_vertical.csv",
                        mime="text/csv"
                    )

        with tab2:
            st.subheader("📅 데이터 기반 전략 기획")
            curr_date = datetime.date.today()
            target_date = curr_date + datetime.timedelta(days=60)

            c1, c2 = st.columns(2)
            with c1:
                st.write("### 💎 Blue Ocean")
                st.caption(str(curr_date.month) + "월 기준 틈새 테마")
                if st.button("🔍 블루오션 분석"):
                    with st.spinner("분석 중..."):
                        query_bo = (
                            str(curr_date.year) + "년 " + str(curr_date.month) +
                            "월 현재 이미지스톡 시장에서 검색량 대비 검색결과 공급이 부족한 "
                            "고수요 저공급 블루오션 일러스트 테마 3개를 추천 이유, 템플릿 예시와 함께 상세히 추천해줘."
                        )
                        res = generate_with_retry(
                            client,
                            "블루오션 분석 중",
                            model=selected_model_name,
                            contents=query_bo,
                        )
                        st.session_state.theme_result = res.text

            with c2:
                st.write("### 🔥 Steady")
                st.caption(str(target_date.month) + "월 기준 스테디 테마")
                btn_label = "📈 " + str(target_date.month) + "월 분석"
                if st.button(btn_label):
                    spinner_msg = str(target_date.month) + "월 분석 중..."
                    with st.spinner(spinner_msg):
                        query_st = (
                            str(target_date.year) + "년 " + str(target_date.month) +
                            "월의 한국과 전세계 공통 기념일/행사를 알려주고, 이를 기반으로 해당 달에 "
                            "검색량이 많을 일러스트 스테디셀러 테마 3개를 추천 이유, 템플릿 예시와 함께 상세히 추천해줘."
                        )
                        res = generate_with_retry(
                            client,
                            "스테디 분석 중",
                            model=selected_model_name,
                            contents=query_st,
                        )
                        st.session_state.theme_result = res.text

            if st.session_state.theme_result:
                st.divider()
                st.markdown(st.session_state.theme_result)

                escaped = (
                    st.session_state.theme_result
                    .replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("$", "\\$")
                )
                st.components.v1.html("""
                    <button onclick="
                        navigator.clipboard.writeText(`""" + escaped + """`)
                        .then(() => alert('클립보드에 복사되었습니다! ✨'))
                        .catch(() => alert('복사 실패: 브라우저 권한을 확인해주세요.'));
                    "
                    style="background-color:#ff4bb4; color:white; border:none; border-radius:8px;
                           padding:10px 20px; font-weight:bold; cursor:pointer; font-size:14px; margin-top:8px;">
                        📋 추천 내용 전체 복사하기
                    </button>
                """, height=55)

    except Exception as e:
        st.error("시스템 오류가 발생했습니다: " + str(e))
else:
    st.warning("사이드바에서 로그인해 주세요.")
