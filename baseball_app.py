import streamlit as st
import pandas as pd
from pybaseball import statcast_pitcher, playerid_lookup
import plotly.express as px
import plotly.graph_objects as go
import datetime  # 🌟 [신규] 날짜와 시간을 자동으로 계산해주는 도구

st.title("⚾ 밀워키 투수 실시간 전력분석기")
st.write("선수를 검색하면 이번 시즌 개막부터 오늘까지의 최신 데이터를 분석합니다!")

# --- 🌟 [신규] 사이드바(옆면 메뉴)에 달력 및 검색 기능 추가 ---
st.sidebar.header("🔍 검색 및 날짜 설정")
first_name = st.sidebar.text_input("투수 이름 (First Name)", "jacob")
last_name = st.sidebar.text_input("투수 성 (Last Name)", "misiorowski")

# 달력 위젯 생성 (시작일: 2026년 개막일 부근 / 종료일: 오늘 날짜 자동 세팅)
start_date = st.sidebar.date_input("분석 시작일", datetime.date(2026, 3, 26))
end_date = st.sidebar.date_input("분석 종료일 (기본값: 오늘)", datetime.date.today())

# 메인 화면 버튼
if st.button("최신 투구 데이터 가져오기"):
    st.write(f"서버에서 {start_date} ~ {end_date} 기간의 데이터를 가져오는 중... ⏳")

    player_info = playerid_lookup(last_name, first_name)
    
    if player_info.empty:
        st.error("선수를 찾을 수 없습니다. 철자를 확인해주세요.")
    else:
        mlbam_id = player_info['key_mlbam'].values[0]
        
        # 🌟 [신규] 고정된 날짜 대신 달력에서 선택한 날짜(start_date, end_date)를 문자열로 변환해 투입
        df = statcast_pitcher(str(start_date), str(end_date), player_id=mlbam_id)
        
        if df.empty:
            st.warning(f"선택하신 기간({start_date} ~ {end_date})에는 등판 기록이 없습니다.")
        else:
            st.success("데이터 업데이트 완료! 🎉")
            
            df['투구_결과'] = df['type'].replace({'S': '스트라이크 🎯', 'B': '볼 ⚾', 'X': '인플레이(타격) 💥'})
            
            df['game_date'] = pd.to_datetime(df['game_date'])
            df['월'] = df['game_date'].dt.month
            
            available_months = sorted(df['월'].unique())
            
            tab_titles = [f"{month}월" for month in available_months]
            tabs = st.tabs(tab_titles)
            
            for tab, month in zip(tabs, available_months):
                with tab:
                    month_df = df[df['월'] == month]
                    
                    st.write(f"### 📅 {month}월 투구 분석 (총 {len(month_df)}구)")
                    
                    st.subheader("📍 1. 릴리스 포인트 탄착군")
                    avg_x = month_df['release_pos_x'].mean()
                    avg_z = month_df['release_pos_z'].mean()

                    fig_release = px.scatter(
                        month_df, x='release_pos_x', y='release_pos_z', color='pitch_name',
                        hover_data=['release_speed', '투구_결과'] 
                    )
                    fig_release.update_layout(xaxis_title="좌우 위치 (피트)", yaxis_title="공의 높이 (피트)", width=600, height=500)
                    fig_release.add_vline(x=avg_x, line_dash="dot", line_color="rgba(255, 0, 0, 0.5)")
                    fig_release.add_hline(y=avg_z, line_dash="dot", line_color="rgba(255, 0, 0, 0.5)")
                    st.plotly_chart(fig_release)

                    st.subheader("📺 2. ABS 투구 궤적")
                    fig_abs = px.scatter(
                        month_df, x='plate_x', y='plate_z', color='pitch_name',
                        hover_data=['release_speed', '투구_결과']
                    )
                    fig_abs.add_shape(type="rect", x0=-0.71, y0=1.5, x1=0.71, y1=3.5, line=dict(color="black", width=3), fillcolor="rgba(0,0,0,0)")
                    fig_abs.add_shape(type="path", path="M -0.71 0 L 0.71 0 L 0.71 0.2 L 0 0.5 L -0.71 0.2 Z", fillcolor="lightgray", line_color="black")
                    fig_abs.update_layout(xaxis_title="좌우 위치 (피트)", yaxis_title="공의 높이 (피트)", xaxis_range=[-3, 3], yaxis_range=[-0.5, 5], width=600, height=600)
                    st.plotly_chart(fig_abs)

                    st.subheader(f"📊 {month}월 실제 데이터")
                    st.dataframe(month_df[['game_date', 'pitch_name', '투구_결과', 'release_speed', 'plate_x', 'plate_z']])