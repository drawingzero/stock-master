import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import json
import io

st.set_page_config(page_title="Stock Master AI", page_icon="🎨", layout="wide")

# 1. 자동 API 설정 (Streamlit Cloud의 Secrets를 먼저 찾습니다)
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    with st.sidebar:
        st.header("⚙️ 설정")
        api_key = st.text_input("API 키를 입력해 주세요 (최초 1회)", type="password")
        st.info("관리자 페이지의 Secrets에 저장하면 이 창이 더 이상 뜨지 않습니다.")

if api_key:
    genai.configure(api_key=api_key)
    
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in models else models[0]
        model = genai.GenerativeModel(model_name)

        st.title("🎨 스톡 마스터")
        uploaded_files = st.file_uploader("이미지를 업로드해 주세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

        if uploaded_files and st.button("🚀 분석 및 키워드 생성 시작"):
            all_results = []
            for uploaded_file in uploaded_files:
                image = Image.open(uploaded_file)
                prompt = "당신은 스톡 전문가입니다. 이미지 분석 후 셔터스톡(영문30개), 어도비(영문30개, 앞10개중요), 통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 키워드를 JSON으로 추출하세요."
                
                with st.spinner(f"'{uploaded_file.name}' 분석 중..."):
                    response = model.generate_content([prompt, image])
                    data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                    data['파일명'] = uploaded_file.name
                    all_results.append(data)

            st.success("분석 완료!")
            df = pd.DataFrame(all_results)

            # --- 앙다를 위한 엑셀 형식 선택 및 다운로드 ---
            st.subheader("📊 결과 다운로드")
            
            # 1. 사이트 업로드용 (가로형)
            csv_horiz = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 업로드용 (가로형) 다운로드", csv_horiz, "upload_horizontal.csv", "text/csv")
            
            # 2. 앙다 확인용 (세로형 - 행열 전환)
            df_vert = df.set_index('파일명').T
            csv_vert = df_vert.to_csv(encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 확인용 (세로형) 다운로드", csv_vert, "viewer_vertical.csv", "text/csv")

            st.write("### 미리보기 (세로형)")
            st.dataframe(df_vert)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
