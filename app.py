import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import datetime

# 1. 사이트 설정 및 디자인
st.set_page_config(page_title="Stock Master AI v3.1", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #ff4bb4; color: white; border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. API 키 세션 관리
if 'api_key' not in st.session_state:
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ Settings")
    if not st.session_state.api_key:
        new_key = st.text_input("Gemini API Key를 입력해 주세요", type="password")
        if st.button("로그인 (키 저장)"):
            st.session_state.api_key = new_key
            st.rerun()
    else:
        st.success("✅ 로그인 완료")
        if st.button("로그아웃"):
            st.session_state.api_key = ""
            st.rerun()

# 3. 메인 화면 구성
st.title("🚀 Stock Master AI: Market Analyzer")

if st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)
    
    try:
        # [핵심 수정] 사용 가능한 모델 목록을 실시간으로 가져와서 설정합니다.
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 'flash' 모델이 있으면 우선 선택, 없으면 첫 번째 모델 선택
        flash_models = [m for m in models if 'flash' in m.lower()]
        selected_model_name = flash_models[0] if flash_models else models[0]
        model = genai.GenerativeModel(selected_model_name)
        
        with st.sidebar:
            st.caption(f"현재 연결된 모델: {selected_model_name}")

        tab1, tab2, tab3 = st.tabs(["🔍 키워드 생성", "💡 시장 분석 & 테마 기획", "📊 수익 통합 대시보드"])

        # --- TAB 1: 키워드 생성기 ---
        with tab1:
            st.subheader("이미지 분석 및 키워드 추출")
            uploaded_files = st.file_uploader("이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            
            if uploaded_files and st.button("🚀 키워드 추출 시작"):
                all_rows = []
                for uploaded_file in uploaded_files:
                    image = Image.open(uploaded_file)
                    prompt = """스톡 전문가로서 이미지를 분석해 셔터스톡(영문35개), 어도비(영문30개, 앞10개중요), 
                    통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 키워드와 제목을 JSON으로 추출하세요. 
                    형식: {"shutterstock": {"title": "..", "keywords": ".."}, ...}"""
                    
                    with st.spinner(f"'{uploaded_file.name}' 분석 중..."):
                        response = model.generate_content([prompt, image])
                        # JSON 응답 정제 로직 강화
                        content_text = response.text.replace('```json', '').replace('```', '').strip()
                        raw_data = json.loads(content_text)
                        for site, content in raw_data.items():
                            all_rows.append({"파일명": uploaded_file.name, "사이트": site, "타이틀": content['title'], "키워드": content['keywords']})
                
                df = pd.DataFrame(all_rows)
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 세로형 CSV 다운로드", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "stock_vertical.csv", "text/csv")

        # --- TAB 2: 시장 분석 & 테마 기획 ---
        with tab2:
            st.subheader("📅 2개월 뒤 블루오션 테마 찾기")
            target_date = datetime.date.today() + datetime.timedelta(days=60)
            if st.button("🌟 고수요/저공급 테마 10개 추천받기"):
                plan_prompt = f"{target_date.month}월 스톡 시장을 분석하여 수요가 높은 블루오션 테마 10개를 상세히 추천해 주세요."
                with st.spinner("시장 데이터를 분석 중입니다..."):
                    response = model.generate_content(plan_prompt)
                    st.markdown(response.text)

        # --- TAB 3: 수익 통합 대시보드 ---
        with tab3:
            st.subheader("💰 통합 수익 관리")
            st.info("현재 노션에서 관리 중인 정산 파일(CSV)의 컬럼명(제목들)을 알려주시면 합산 기능을 만들어 드릴게요!")

    except Exception as e:
        st.error(f"설정 중 오류가 발생했습니다: {e}")
        st.info("사이드바에서 API 키를 다시 확인하거나 잠시 후 시도해 보세요.")
else:
    st.warning("왼쪽 사이드바에서 로그인해 주세요.")
