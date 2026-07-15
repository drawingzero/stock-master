import streamlit as st
import google.generativeai as genai
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

# 결과 저장을 위한 세션 상태 초기화
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
            st.session_state.theme_result = ""  # 로그아웃 시 결과도 삭제
            st.rerun()
    st.divider()
    st.caption("비밀 금고(Secrets) 설정 시 자동 로그인됩니다.")

# 3. 메인 콘텐츠
st.title("🎨 Stock Master AI")

if st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)

    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in models if 'flash' in m.lower()]
        selected_model_name = flash_models[0] if flash_models else models[0]
        model = genai.GenerativeModel(selected_model_name)

        tab1, tab2 = st.tabs(["🔍 키워드 생성", "💡 시장 분석 & 테마 기획"])

        with tab1:
            st.subheader("이미지 분석 및 사이트별 키워드 추출")
            uploaded_files = st.file_uploader("이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

            if uploaded_files and st.button("🚀 분석 시작"):
                all_rows = []
                
                # Gemini에게 JSON 출력을 강제하는 설정
                generation_config = {
                    "response_mime_type": "application/json",
                }

                for uploaded_file in uploaded_files:
                    image = Image.open(uploaded_file)
                    prompt = """스톡 전문가로서 이미지를 분석해 셔터스톡(영문35개), 어도비(영문30개, 앞10개중요), 
                    통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 검색량이 높은 단어로 구성된 키워드와 제목을 JSON으로 추출하세요.
                    
                    반드시 아래의 JSON 포맷을 그대로 준수하여 출력해야 하며, 다른 설명이나 마크다운 백틱(```)은 절대 포함하지 마세요.

                    {
                      "shutterstock": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."},
                      "adobe": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."},
                      "tongro": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."},
                      "getty": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."},
                      "miricanvas": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."}
                    }"""

                    # f-string 대신 문자열 더하기 사용 (오류 원천 방지)
                    with st.spinner("'" + uploaded_file.name + "' 처리 중..."):
                        try:
                            # generation_config 추가하여 호출
                            response = model.generate_content(
                                [prompt, image],
                                generation_config=generation_config
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
                    
                    # 다운로드 버튼 인코딩 부분도 완전히 단일 변수로 분리하여 안전하게 처리
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
                st.caption(f"{curr_date
