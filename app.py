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
            st.session_state.theme_result = "" # 로그아웃 시 결과도 삭제
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
                for uploaded_file in uploaded_files:
                    image = Image.open(uploaded_file)
                    prompt = """스톡 전문가로서 이미지를 분석해 셔터스톡(영문35개), 어도비(영문30개, 앞10개중요), 
                    통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 검색량이 높은 단어로 구성된 키워드와 제목을 JSON으로 추출하세요. 
                    형식: {"shutterstock": {"title": "..", "keywords": ".."}, ...}"""
                    
                    with st.spinner(f"'{uploaded_file.name}' 처리 중..."):
                        response = model.generate_content([prompt, image])
                        content_text = response.text.replace('```json', '').replace('```', '').strip()
                        raw_data = json.loads(content_text)
                        for site, content in raw_data.items():
                            all_rows.append({"파일명": uploaded_file.name, "사이트": site, "타이틀": content['title'], "키워드": content['keywords']})
                
                df = pd.DataFrame(all_rows)
                st.success("완료!")
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 CSV 다운로드", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "stock_vertical.csv", "text/csv")

        with tab2:
            st.subheader("📅 데이터 기반 전략 기획")
            curr_date = datetime.date.today()
            target_date = curr_date + datetime.timedelta(days=60)
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("### 💎 Blue Ocean")
                st.caption(f"{curr_date.month}월 기준 틈새 테마")
                if st.button("🔍 블루오션 분석"):
                    with st.spinner("분석 중..."):
                        res = model.generate_content(f"2026년 {curr_date.month}월 현재 이미지스톡 시장에서 검색량에 비해 데이터가 부족한 고수요 저공급 블루오션 일러스트 테마 3개를 추천 이유, 템플릿 예시와 함께 상세히 추천해줘.")
                        st.session_state.theme_result = res.text # 결과를 세션에 저장
            
            with c2:
                st.write("### 🔥 Steady")
                st.caption(f"{target_date.month}월 기준 스테디 테마")
                if st.button(f"📈 {target_date.month}월 분석"):
                    with st.spinner(f"{target_date.month}월 분석 중..."):
                        res = model.generate_content(f"2026년 {target_date.month}월의 한국과 전세계 공통 기념일/행사를 알려주고, 이를 기반으로 해당 달에 검색량이 많을 일러스트 스테디셀러 테마 3개를 추천 이유, 템플릿 예시와 함께 상세히 추천해줘.")
                        st.session_state.theme_result = res.text # 결과를 세션에 저장

            # --- 추천 결과 출력 및 복사 기능 ---
if st.session_state.theme_result:
    st.divider()
    st.markdown("### ✨ 분석 결과")
    
    # 결과 내용을 코드 박스에 넣으면 자동으로 복사 버튼이 생겨!
    st.code(st.session_state.theme_result, language="markdown")
    
    st.info("💡 코드 박스 오른쪽 위의 복사 아이콘을 누르면 전체 복사돼!")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
else:
    st.warning("사이드바에서 로그인해 주세요.")
