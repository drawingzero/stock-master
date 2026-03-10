import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import datetime

# 1. 사이트 설정 및 디자인
st.set_page_config(page_title="Stock Master AI v3", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #2e7d32; color: white; border-radius: 8px; font-weight: bold; }
    .stTab { font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. API 키 세션 관리
if 'api_key' not in st.session_state:
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ Settings")
    if not st.session_state.api_key:
        new_key = st.text_input("Gemini API Key", type="password")
        if st.button("Login"):
            st.session_state.api_key = new_key
            st.rerun()
    else:
        st.success("✅ Logged In")
        if st.button("Logout"):
            st.session_state.api_key = ""
            st.rerun()

# 3. 메인 화면 구성
st.title("🚀 Stock Master AI: Market Analyzer")

if st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)
    model = genai.GenerativeModel('models/gemini-1.5-flash')

    # 탭 메뉴 구성
    tab1, tab2, tab3 = st.tabs(["🔍 키워드 생성", "💡 시장 분석 & 테마 기획", "📊 수익 통합 대시보드"])

    # --- TAB 1: 키워드 생성기 ---
    with tab1:
        st.subheader("이미지 분석 및 세로형 키워드 추출")
        uploaded_files = st.file_uploader("이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="uploader")
        
        if uploaded_files and st.button("🚀 키워드 추출 시작"):
            all_rows = []
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                prompt = """스톡 전문가로서 이미지를 분석해 셔터스톡(영문35개), 어도비(영문30개, 앞10개중요), 
                통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 키워드와 제목을 JSON으로 추출하세요. 
                형식: {"shutterstock": {"title": "..", "keywords": ".."}, ...}"""
                
                with st.spinner(f"'{uploaded_file.name}' 분석 중..."):
                    response = model.generate_content([prompt, image])
                    clean_res = response.text.replace('```json', '').replace('```', '').strip()
                    raw_data = json.loads(clean_res)
                    for site, content in raw_data.items():
                        all_rows.append({"파일명": uploaded_file.name, "사이트": site, "타이틀": content['title'], "키워드": content['keywords']})
            
            df = pd.DataFrame(all_rows)
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 CSV 다운로드", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "stock_vertical.csv", "text/csv")

    # --- TAB 2: 시장 분석 & 테마 기획 ---
    with tab2:
        st.subheader("📅 2개월 뒤 블루오션 테마 찾기")
        target_date = datetime.date.today() + datetime.timedelta(days=60)
        st.info(f"현재 {target_date.strftime('%Y년 %m월')}의 수요가 높은 시장을 분석합니다.")
        
        if st.button("🌟 고수요/저공급 테마 10개 추천받기"):
            plan_prompt = f"""
            2026년 {target_date.month}월 스톡 시장을 분석하세요. 
            캐릭터나 특정 브랜드에 구애받지 말고 '상업적 수요'가 가장 높은 주제를 찾으세요.
            - 검색량은 폭증하지만 고품질 이미지가 부족한 '블루오션' 테마 3개 포함.
            - 글로벌 시즌 이슈와 한국형 특수 키워드 조합.
            - 각 테마별로 왜 이 주제가 돈이 되는지(수요 배경) 설명하세요.
            결과는 10개의 리스트로 상세히 작성하세요.
            """
            with st.spinner("시장 데이터를 분석 중입니다..."):
                response = model.generate_content(plan_prompt)
                st.markdown(response.text)

    # --- TAB 3: 수익 통합 대시보드 ---
    with tab3:
        st.subheader("💰 통합 수익 관리")
        st.write("각 사이트에서 받은 정산 파일을 업로드하면 자동으로 합산 분석해 드립니다.")
        revenue_files = st.file_uploader("정산 CSV 파일을 업로드하세요", type=['csv'], accept_multiple_files=True)
        
        if revenue_files:
            # 여러 파일을 하나로 합치는 간단한 로직 (샘플)
            combined_df = pd.concat([pd.read_csv(f) for f in revenue_files])
            st.write("### 📈 전체 수익 현황")
            st.line_chart(combined_df.iloc[:, 1]) # 예시 차트
            st.dataframe(combined_df)
            st.info("정산 파일의 형식이 사이트마다 다르므로, 앙다의 파일 양식을 알려주시면 자동 합산 기능을 더 정교하게 만들어 드릴 수 있어요!")

else:
    st.warning("Please Login in the sidebar first.")
