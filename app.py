with tab1:
            st.subheader("이미지 분석 및 사이트별 키워드 추출")
            uploaded_files = st.file_uploader("이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

            if uploaded_files and st.button("🚀 분석 시작"):
                all_rows = []
                
                # 1. Gemini에게 기대하는 JSON 구조를 Pydantic 등으로 정의하는 대신, 
                # API 호출 시 response_mime_type을 지정하여 안정적인 JSON을 받도록 설정합니다.
                generation_config = {
                    "response_mime_type": "application/json",
                }

                for uploaded_file in uploaded_files:
                    image = Image.open(uploaded_file)
                    
                    # 프롬프트에 JSON 스키마 예시를 아주 명확하게 제공합니다.
                    prompt = """스톡 전문가로서 이미지를 분석해 셔터스톡(영문35개), 어도비(영문30개, 앞10개중요), 
                    통로/유토(한글25개), 게티(한글20개), 미리캔버스(한글10개) 검색량이 높은 단어로 구성된 키워드와 제목을 JSON으로 추출하세요.
                    
                    반드시 아래의 JSON 포맷을 그대로 준수하여 출력해야 하며, 다른 설명이나 마크다운 백틱(```)은 절대 포함하지 마세요.

                    {
                      "shutterstock": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."},
                      "adobe": {"title": "영어 제목", "keywords": "키워드1, 키워드2, ..."},
                      "tongro": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."},
                      "getty": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."},
                      "miricanvas": {"title": "한글 제목", "keywords": "키워드1, 키워드2, ..."}
                    }"""

                    with st.spinner(f"'{uploaded_file.name}' 처리 중..."):
                        try:
                            # generation_config를 추가하여 JSON 출력을 강제합니다.
                            response = model.generate_content(
                                [prompt, image],
                                generation_config=generation_config
                            )
                            
                            content_text = response.text.strip()
                            
                            # 혹시 모를 마크다운 기호가 남아있다면 제거
                            if content_text.startswith("```"):
                                content_text = content_text.split("```")[1]
                                if content_text.startswith("json"):
                                    content_text = content_text[4:]
                            
                            raw_data = json.loads(content_text.strip())
                            
                            for site, content in raw_data.items():
                                # 타이틀과 키워드가 안전하게 존재하는지 확인하며 추가
                                title = content.get('title', '')
                                keywords = content.get('keywords', '')
                                all_rows.append({
                                    "파일명": uploaded_file.name, 
                                    "사이트": site, 
                                    "타이틀": title, 
                                    "키워드": keywords
                                })
                        except json.JSONDecodeError as je:
                            st.error(f"'{uploaded_file.name}' 파싱 실패: AI 응답 형식이 올바르지 않습니다. 다시 시도해 주세요.")
                            # 디버깅용 로그 출력
                            with st.expansion("AI 원본 응답 보기"):
                                st.code(response.text)
                        except Exception as e:
                            st.error(f"'{uploaded_file.name}' 처리 중 오류 발생: {e}")

                if all_rows:
                    df = pd.DataFrame(all_rows)
                    st.success("완료!")
                    st.dataframe(df, use_container_width=True)
                    st.download_button("📥 CSV 다운로드", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "stock_vertical.csv", "text/csv")
