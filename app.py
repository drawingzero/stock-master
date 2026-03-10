import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json

# 1. 사이트 설정
st.set_page_config(page_title="Stock Master AI", page_icon="🎨", layout="wide")

# 디자인 테마 (핑크 포인트)
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

        uploaded_files = st.file_uploader("이미지를 업로드해 주세요 (다중 선택 가능)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        if uploaded_files and st.button("🚀 분석 및 표 생성"):
            all_rows = [] # 엑셀의 각 행이 될 리스트
            
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                
                # 사이트별로 각각 제목과 키워드를 생성하도록 지침 강화
                prompt = """
                스톡 전문가로서 이미지를 분석해 사이트별 최적화된 제목과 키워드를 JSON으로 대답하세요.
                반드시 아래 형식을 지키세요:
                {
                  "shutterstock": {"title": "영어제목", "keywords": "영문35개"},
