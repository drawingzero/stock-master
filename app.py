import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import pandas as pd
import json
import datetime

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

# 기본으로 사용할 모델 (목록 조회가 실패해도 이 값으로 동작)
DEFAULT_MODEL = "gemini-2.5-flash"

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
            uploaded_files = st.file_uploader("이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

            if uploaded_files and st.button("🚀 분석 시작"):
                all_rows = []

                prompt = """스톡 전문가로서 이미지를 분석해 셔터스톡(영문35개), 어도비(영문30개, 앞10개중요), 
                통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 검색량이 높은 단어로 구성된 키워드와 제목을 JSON으로 추출하세요.

                반드시 아래의 JSON 포맷을 그대로 준수하여 출력해야 하며, 다른 설명이나 마크다운 백틱은 절대 포함하지 마세요.

                {
                  "shutterstock": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."},
                  "adobe": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."},
                  "tongro": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."},
                  "getty": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."},
                  "miricanvas": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."}
                }"""

                for uploaded_file in uploaded_files:
                    image = Image.open(uploaded_file)

                    with st.spinner("'" + uploaded_file.name + "' 처리 중..."):
                        try:
                            response = client.models.generate_content(
                                model=selected_model_name,
                                contents=[prompt, image],
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                ),
                            )

                            content_text = response.text.strip()

                            # 안전장치: 마크다운 기호가 남아있다면 제거
                            if content_text.startswith("```"):
                                content_text = content_text.split("```")[1]
                                if content_text.startswith("json"):
                                    content_text = content_text[4:]

                            raw_data = json.loads(content_text.strip())

                            for site, content in raw_data.items():
                                title = content.get('title', '')
                                keywords = content.get('keywords', '')
                                all_rows.append({
                                    "파일명": uploaded_file.name,
                                    "사이트": site,
                                    "타이틀": title,
                                    "키워드": keywords
                                })
                        except json.JSONDecodeError:
                            st.error("파싱 실패: '" + uploaded_file.name + "' 이미지의 AI 응답 형식이 올바르지 않습니다.")
                            with st.expander("AI 원본 응답 보기"):
                                st.code(response.text)
                        except Exception as e:
                            st.error("오류 발생 (" + uploaded_file.name + "): " + str(e))

                if all_rows:
                    df = pd.DataFrame(all_rows)
                    st.success("완료!")
                    st.dataframe(df, use_container_width=True)

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
                        res = client.models.generate_content(
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
                        res = client.models.generate_content(
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
