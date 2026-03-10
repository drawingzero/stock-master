import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json

st.set_page_config(page_title="Stock Master AI", page_icon="🎨")
st.title("🎨 스톡 마스터 AI (에러 해결 버전)")

# 1. API 키 설정 (Secrets 또는 사이드바)
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key를 입력해 주세요", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    try:
        # 2. 내 키로 사용 가능한 모델 목록 가져오기
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        st.sidebar.success("✅ API 연결 성공!")
        selected_model = st.sidebar.selectbox("사용할 모델을 선택해 주세요", models)
        st.sidebar.write(f"현재 선택된 모델: `{selected_model}`")
        
        # 3. 모델 설정
        model = genai.GenerativeModel(selected_model)

        uploaded_files = st.file_uploader("이미지를 올려주세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        if uploaded_files and st.button("🚀 분석 시작"):
            all_results = []
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                prompt = "이 이미지를 분석해서 짧은 한글 제목 1개만 지어줘. 결과는 반드시 JSON 형식으로: {'title': '제목'}"
                
                with st.spinner(f"'{uploaded_file.name}' 테스트 중..."):
                    # 여기서 에러가 나면 모델 이름 문제일 확률 99%
                    response = model.generate_content([prompt, image])
                    st.write(response.text) # 결과 확인용
                    
            st.success("테스트 완료! 잘 작동한다면 전체 지침(Prompt)을 다시 넣어줄게.")

    except Exception as e:
        st.error(f"모델 목록을 가져오는 중 에러 발생: {e}")
        st.info("API 키가 올바른지, 혹은 구글 AI 스튜디오에서 서비스 중인 지역인지 확인이 필요해요.")
else:
    st.warning("사이드바에 API 키를 넣어주세요!")
