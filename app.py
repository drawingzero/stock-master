import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import io

# 1. 사이트 설정
st.set_page_config(page_title="Stock Master AI", page_icon="🎨", layout="wide")

# 디자인 테마
st.markdown("""
    <style>
    .main { background-color: #fffafb; }
    .stButton>button { background-color: #ff4bb4; color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. API 키 관리 로직 (세션 상태 이용)
if 'api_key' not in st.session_state:
    # 1순위: 비밀 금고(Secrets) 확인, 2순위: 비어있음
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 계정 설정")
    if not st.session_state.api_key:
        new_key = st.text_input("Gemini API Key를 입력해 주세요", type="password")
        if st.button("로그인 (키 저장)"):
            st.session_state.api_key = new_key
            st.rerun()
    else:
        st.success("✅ 로그인 상태입니다.")
        if st.button("로그아웃 (키 초기화)"):
            st.session_state.api_key = ""
            st.rerun()
    st.divider()
    st.info("API 키를 바꾸려면 '로그아웃' 후 다시 입력하세요.")

# 3. 메인 화면
st.title("🎨 스톡 마스터")

if st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)
    
    try:
        # 모델 자동 설정
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in models else models[0]
        model = genai.GenerativeModel(model_name)

        uploaded_files = st.file_uploader("이미지를 업로드해 주세요 (다중 선택 가능)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        if uploaded_files and st.button("🚀 분석 및 결과 생성"):
            all_results = []
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                prompt = """당신은 스톡 전문가입니다. 이미지 분석 후 셔터스톡(영문30개), 어도비(영문30개, 앞10개중요), 
                통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 키워드와 제목을 JSON으로 추출하세요."""
                
                with st.spinner(f"'{uploaded_file.name}' 분석 중..."):
                    response = model.generate_content([prompt, image])
                    data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                    data['파일명'] = uploaded_file.name
                    all_results.append(data)

            # 데이터 가공 (세로형 전환)
            df = pd.DataFrame(all_results)
            df_vert = df.set_index('파일명').T # 행과 열을 바꿈 (Transpose)

            st.success("✨ 분석 완료!")
            st.write("### 📊 키워드 확인")
            st.dataframe(df_vert, use_container_width=True)

            # 세로형 CSV 다운로드 전용
            csv_vert = df_vert.to_csv(encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 결과(CSV) 다운로드",
                data=csv_vert,
                file_name="stock_keywords_vertical.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
else:
    st.warning("왼쪽 사이드바에서 API 키를 입력하여 로그인해 주세요.")
