import streamlit as st
import pandas as pd
from pybaseball import statcast_pitcher, playerid_lookup
import plotly.express as px
import plotly.graph_objects as go
import datetime

# --- 1. 왼쪽 사이드바: 메뉴 선택 ---
st.sidebar.header(" 메뉴 선택")
menu = st.sidebar.radio("이동할 페이지를 선택하세요:", [" 투구 분석", " 선수 프로필"])

st.sidebar.header(" 검색 및 날짜 설정")
first_name = st.sidebar.text_input("투수 이름 (First Name)", "").strip()
last_name = st.sidebar.text_input("투수 성 (Last Name)", "").strip()
start_date = st.sidebar.date_input("분석 시작일", datetime.date(2026, 3, 26))
end_date = st.sidebar.date_input("분석 종료일", datetime.date.today())

is_searched = bool(first_name and last_name)
name_display = f"{first_name.title()} {last_name.title()}" if is_searched else ""

# ==========================================
# [페이지 1] 데이터 분석 페이지
# ==========================================
if menu == " 투구 분석":
    if is_searched:
        st.title(f" {name_display} 투구 분석")
        st.write(f"선택한 기간 동안 {name_display} 선수의 실시간 투구 데이터를 분석합니다.")
    else:
        st.title(" 밀워키 투수 실시간 분석기")
        st.info(" 왼쪽 사이드바에 투수 이름과 성을 영어로 입력해 주세요. (예: jacob / misiorowski)")

    if is_searched:
        if st.button("최신 투구 데이터 가져오기"):
            st.write("서버에서 데이터를 가져오는 중...")
            player_info = playerid_lookup(last_name, first_name)
            
            if player_info.empty:
                st.error("선수를 찾을 수 없습니다. 철자를 확인해주세요.")
            else:
                mlbam_id = player_info['key_mlbam'].values[0]
                df = statcast_pitcher(str(start_date), str(end_date), player_id=mlbam_id)
                
                if df.empty:
                    st.warning("이 기간에는 등판 기록이 없습니다.")
                else:
                    st.success("데이터 업데이트를 완료했습니다.")
                    df['투구_결과'] = df['type'].replace({'S': '스트라이크', 'B': '볼', 'X': '인플레이(타격)'})
                    df['game_date'] = pd.to_datetime(df['game_date'])
                    df['월'] = df['game_date'].dt.month
                    
                    available_months = sorted(df['월'].unique())
                    tabs = st.tabs([f"{month}월" for month in available_months])
                    
                    for tab, month in zip(tabs, available_months):
                        with tab:
                            month_df = df[df['월'] == month]
                            st.write(f"###  {month}월 투구 분석 (총 {len(month_df)}구)")
                            
                            st.subheader(" 1. 릴리스 포인트 탄착군")
                            avg_x = month_df['release_pos_x'].mean()
                            avg_z = month_df['release_pos_z'].mean()
                            fig_release = px.scatter(month_df, x='release_pos_x', y='release_pos_z', color='pitch_name', hover_data=['release_speed', '투구_결과'])
                            fig_release.update_layout(xaxis_title="좌우 위치 (피트)", yaxis_title="공의 높이 (피트)", width=600, height=500)
                            fig_release.add_vline(x=avg_x, line_dash="dot", line_color="rgba(255,0,0,0.5)")
                            fig_release.add_hline(y=avg_z, line_dash="dot", line_color="rgba(255,0,0,0.5)")
                            st.plotly_chart(fig_release)

                            st.subheader(" 2. ABS 투구 궤적")
                            fig_abs = px.scatter(month_df, x='plate_x', y='plate_z', color='pitch_name', hover_data=['release_speed', '투구_결과'])
                            fig_abs.add_shape(type="rect", x0=-0.71, y0=1.5, x1=0.71, y1=3.5, line=dict(color="black", width=3), fillcolor="rgba(0,0,0,0)")
                            fig_abs.add_shape(type="path", path="M -0.71 0 L 0.71 0 L 0.71 0.2 L 0 0.5 L -0.71 0.2 Z", fillcolor="lightgray", line_color="black")
                            fig_abs.update_layout(xaxis_title="좌우 위치 (피트)", yaxis_title="공의 높이 (피트)", xaxis_range=[-3, 3], yaxis_range=[-0.5, 5], width=600, height=600)
                            st.plotly_chart(fig_abs)

                            st.subheader(f" {month}월 실제 데이터")
                            st.dataframe(month_df[['game_date', 'pitch_name', '투구_결과', 'release_speed', 'plate_x', 'plate_z']])

# ==========================================
# [페이지 2] 선수 프로필 페이지 (MLB 공식 데이터로 변경)
# ==========================================
elif menu == " 선수 프로필":
    if is_searched:
        st.title(f" {name_display} 공식 프로필")
        player_info = playerid_lookup(last_name, first_name)
        
        if player_info.empty:
            st.warning("선수 정보를 찾을 수 없습니다. 이름 철자를 확인해 보세요.")
        else:
            mlbam_id = player_info['key_mlbam'].values[0]
            
            # MLB 공식 서버에서 선수의 고화질 헤드샷 사진을 실시간으로 가져오기
            img_url = f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/w_426,q_auto:best/v1/people/{mlbam_id}/headshot/67/current"
            
            # 화면을 왼쪽(사진)과 오른쪽(정보)으로 분할
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.image(img_url, caption=name_display, use_container_width=True)
                
            with col2:
                st.subheader("선수 기본 정보")
                st.write(f"**MLB 공식 고유 ID:** `{mlbam_id}`")
                
                st.write("---")
                st.subheader(" 야구 전문 데이터베이스 연결")
                st.write("아래 링크를 클릭하면 해당 선수의 세부 성적과 스카우팅 리포트 페이지로 바로 이동합니다.")
                
                # 선수 이름을 기반으로 외부 사이트 검색 결과 링크를 자동 생성
                st.markdown(f" **[Baseball-Reference ({name_display} 통산 기록 보기)](https://www.baseball-reference.com/search/search.fcgi?search={first_name}+{last_name})**")
                st.markdown(f" **[FanGraphs ({name_display} 스카우팅 리포트 보기)](https://www.fangraphs.com/players/{first_name}-{last_name})**")
                
    else:
        st.title(" 선수 프로필")
        st.info(" 왼쪽 사이드바에 투수 이름을 검색하면 메이저리그 공식 프로필 사진과 데이터 사이트 링크가 나타납니다.")