import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import io

# 1. 웹사이트 기본 설정
st.set_page_config(page_title="Stock Master AI", page_icon="🎨")

# 디자인 테마 (핑크색 포인트)
st.markdown("""
    <style>
    .main { background-color: #fff5f7; }
    .stButton>button { background-color: #ff4bb4; color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎨 스톡 마스터 AI 비서")
st.write("이미지를 업로드하시면 사이트별 최적화된 키워드를 자동으로 생성해 드립니다.")

# 2. 사이드바 설정 (API 키 입력)
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Gemini API Key를 입력해 주세요", type="password")
    st.info("API 키는 Google AI Studio에서 무료로 발급받으실 수 있습니다.")

# 3. 메인 로직
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-3-flash')

    uploaded_files = st.file_uploader("이미지 파일들을 선택해 주세요 (PNG, JPG, JPEG)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("🚀 분석 시작하기"):
            all_results = []
            progress_bar = st.progress(0)
            
            for i, uploaded_file in enumerate(uploaded_files):
                # 이미지 읽기
                image = Image.open(uploaded_file)
                
                # AI 지침서 (Prompt)
                prompt = """
                당신은 스톡 이미지 키워드 전문가입니다. 이미지를 분석하여 규칙을 지켜 작성하세요.
                결과는 반드시 JSON 형식으로만 응답하세요:
                {
                  "title_en": "영어 제목",
                  "title_ko": "한글 제목",
                  "shutterstock": "영문 키워드 35개 (쉼표 구분)",
                  "adobe": "영문 키워드 30개 (중요 단어 10개를 앞배치, 쉼표 구분)",
                  "tongro_uto_getty": "한글 키워드 25개 (쉼표 구분)",
                  "miricanvas": "한글 핵심 키워드 딱 10개 (쉼표 구분)"
                }
                """
                
                with st.spinner(f"'{uploaded_file.name}' 분석 중..."):
                    response = model.generate_content([prompt, image])
                    try:
                        clean_text = response.text.replace('```json', '').replace('```', '').strip()
                        data = json.loads(clean_text)
                        data['파일명'] = uploaded_file.name
                        all_results.append(data)
                    except:
                        st.error(f"{uploaded_file.name} 분석 중 오류가 발생했습니다.")
                
                progress_bar.progress((i + 1) / len(uploaded_files))

            # 결과 리포트
            st.success("모든 분석이 완료되었습니다!")
            df = pd.DataFrame(all_results)
            st.dataframe(df)

            # 엑셀(CSV) 다운로드 버튼
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 분석 결과(CSV) 다운로드",
                data=csv,
                file_name="stock_keywords.csv",
                mime="text/csv"
            )
else:
    st.warning("먼저 왼쪽 사이드바에서 API 키를 입력해 주세요!")
