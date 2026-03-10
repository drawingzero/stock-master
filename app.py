import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import io

# 1. 사이트 설정 및 디자인
st.set_page_config(page_title="Stock Master AI", page_icon="🎨", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #fffafb; }
    .stButton>button { background-color: #ff4bb4; color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #ff4bb4; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎨 스톡 마스터 AI 비서")
st.write("이미지를 업로드하시면 사이트별 최적화된 키워드를 자동으로 생성해 드립니다.")

# 2. API 및 모델 설정
api_key = st.secrets.get("GEMINI_API_KEY", "")
if not api_key:
    with st.sidebar:
        st.header("⚙️ 설정")
        api_key = st.text_input("Gemini API Key를 입력해 주세요", type="password")

if api_key:
    genai.configure(api_key=api_key)
    
    try:
        # 사용 가능한 모델 목록 가져오기
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        default_model = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in available_models else available_models[0]
        
        with st.sidebar:
            st.success("✅ API 연결 성공!")
            selected_model = st.selectbox("사용할 모델을 선택하세요", available_models, index=available_models.index(default_model))
        
        model = genai.GenerativeModel(selected_model)

        # 3. 이미지 업로드 및 분석
        uploaded_files = st.file_uploader("이미지 파일들을 선택해 주세요 (여러 장 가능)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        if uploaded_files:
            if st.button("🚀 분석 및 키워드 생성 시작"):
                all_results = []
                progress_bar = st.progress(0)
                
                for i, uploaded_file in enumerate(uploaded_files):
                    image = Image.open(uploaded_file)
                    
                    # 앙다의 6개 사이트 규칙 집약 프롬프트
                    prompt = """
                    당신은 스톡 이미지 키워드 전문가입니다. 이미지를 분석하여 다음 규칙을 엄격히 지켜 작성해 주세요.
                    
                    [공통] 이미지와 무관하거나 반복적인 키워드 금지. 가장 핵심적인 10개 키워드를 우선 선정할 것.
                    1. 셔터스톡: 영문 제목, 영문 키워드 30~40개 (연관성 높게).
                    2. 어도비스톡: 영문 제목, 영문 키워드 25~35개. **가장 중요한 10개를 반드시 1~10번에 배치**.
                    3. 통로이미지/유토이미지: 한글 제목, 한글 키워드 20~30개.
                    4. 게티이미지: 한글 제목, 한글 키워드 20~30개 (정확도 우선).
                    5. 미리캔버스: 한글 제목, 한글 키워드 딱 10개 (가장 핵심적인 단어만).
                    
                    결과는 반드시 아래 JSON 형식으로만 응답해 주세요:
                    {
                      "title_en": "영문 제목",
                      "title_ko": "한글 제목",
                      "shutterstock": "키워드1, 키워드2...",
                      "adobe": "키워드1, 키워드2...",
                      "tongro_uto_getty": "키워드1, 키워드2...",
                      "miricanvas": "키워드1, 키워드2..."
                    }
                    """
                    
                    with st.spinner(f"'{uploaded_file.name}' 분석 중..."):
                        try:
                            response = model.generate_content([prompt, image])
                            clean_text = response.text.replace('```json', '').replace('```', '').strip()
                            data = json.loads(clean_text)
                            data['파일명'] = uploaded_file.name
                            all_results.append(data)
                        except Exception as e:
                            st.error(f"{uploaded_file.name} 처리 중 오류: {e}")
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))

                st.success("✨ 모든 분석이 완료되었습니다!")
                
                # 결과 데이터프레임 생성 및 표시
                df = pd.DataFrame(all_results)
                # 컬럼 순서 조정
                cols = ['파일명', 'title_ko', 'title_en', 'miricanvas', 'adobe', 'shutterstock', 'tongro_uto_getty']
                st.dataframe(df[cols])

                # CSV 다운로드 버튼
                csv = df[cols].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="📥 분석 결과(CSV) 다운로드 하여 엑셀로 확인하기",
                    data=csv,
                    file_name="stock_master_results.csv",
                    mime="text/csv"
                )
    except Exception as e:
        st.error(f"초기 설정 에러: {e}")
else:
    st.warning("먼저 API 키를 설정해 주세요 (사이드바 혹은 Secrets).")
