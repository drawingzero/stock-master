import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json

# 1. 사이트 설정 및 디자인
st.set_page_config(page_title="Stock Master AI", page_icon="🎨", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #fffafb; }
    .stButton>button { background-color: #ff4bb4; color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. API 키 세션 관리
if 'api_key' not in st.session_state:
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ 계정 설정")
    if not st.session_state.api_key:
        new_key = st.text_input("Gemini API Key를 입력해 주세요", type="password")
        if st.button("로그인 (키 저장)"):
            st.session_state.api_key = new_key
            st.rerun()
    else:
        st.success("✅ 로그인 상태입니다.")
        if st.button("로그아웃 (다른 키 입력)"):
            st.session_state.api_key = ""
            st.rerun()
    st.divider()
    st.info("비밀 금고(Secrets)를 설정하면 매번 입력할 필요가 없습니다.")

# 3. 메인 기능
st.title("🎨 스톡 마스터 AI")

if st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)
    
    try:
        # 모델 자동 선택
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in models else models[0]
        model = genai.GenerativeModel(model_name)

        uploaded_files = st.file_uploader("이미지를 업로드해 주세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        if uploaded_files and st.button("🚀 분석 및 데이터 생성 시작"):
            all_rows = []
            
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                
                # 프롬프트 문법 오류 방지를 위해 f-string 대신 깔끔한 삼중 따옴표 사용
                prompt = """당신은 스톡 전문가입니다. 이미지를 분석해 사이트별 최적화된 제목과 키워드를 JSON으로 대답하세요.
                반드시 아래 형식을 지키세요:
                {
                  "shutterstock": {"title": "영어제목", "keywords": "영문35개"},
                  "adobe_stock": {"title": "영어제목", "keywords": "영문30개,핵심10개앞으로"},
                  "tongro_utog": {"title": "한글제목", "keywords": "한글25개"},
                  "getty_images": {"title": "한글제목", "keywords": "한글20개"},
                  "miricanvas": {"title": "한글제목", "keywords": "한글10개"}
                }"""
                
                with st.spinner(f"'{uploaded_file.name}' 분석 중..."):
                    response = model.generate_content([prompt, image])
                    # JSON 데이터 추출 및 정제
                    clean_res = response.text.replace('```json', '').replace('```', '').strip()
                    raw_data = json.loads(clean_res)
                    
                    # 수직 구조로 데이터 재배열
                    for site, content in raw_data.items():
                        all_rows.append({
                            "파일명": uploaded_file.name,
                            "사이트": site,
                            "타이틀": content['title'],
                            "키워드": content['keywords']
                        })

            if all_rows:
                df = pd.DataFrame(all_rows)
                st.success("✨ 모든 분석이 완료되었습니다!")
                
                st.write("### 📊 수직형 결과 확인")
                st.dataframe(df, use_container_width=True)

                # CSV 다운로드 (세로형만 제공)
                csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 엑셀(CSV) 다운로드",
                    data=csv_data,
                    file_name="stock_master_vertical.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        st.info("AI 응답 형식이 맞지 않을 수 있습니다. 다시 한번 시도해 보세요.")
else:
    st.warning("왼쪽 사이드바에서 API 키를 입력하여 로그인해 주세요.")
