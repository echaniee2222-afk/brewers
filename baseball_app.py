import streamlit as st
import pandas as pd
from pybaseball import statcast_pitcher
import plotly.express as px
import plotly.graph_objects as go
import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="MLB Pitching Lab", layout="wide", page_icon="⚾")

# --- 커스텀 CSS ---
st.markdown("""
    <style>
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css");
    html, body, [class*="st-"] {
        font-family: "Pretendard Variable", Pretendard, -apple-system, sans-serif !important;
    }
    .stApp { background-color: #f4f6f9; }
    div[data-testid="stMetric"] {
        background-color: #ffffff; border-radius: 12px; padding: 20px 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;
        transition: transform 0.2s ease;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-2px); }
    div[data-testid="stMetricLabel"] { font-size: 0.95rem; font-weight: 600; color: #64748b; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 800; color: #0f172a; }
    div[data-testid="stButton"] button {
        background-color: #1e293b; color: #ffffff; border-radius: 8px;
        font-weight: 600; transition: all 0.2s ease; width: 100%;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.15); color: #ffffff;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #ffffff;
        border-radius: 8px 8px 0 0; padding: 10px 20px; font-weight: 600;
        border: 1px solid #e2e8f0; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { background-color: #1e293b; color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# --- 메모리(Session State) ---
for key in ['pitch_data', 'current_player_id', 'current_player_name', 'current_first_name', 'current_last_name']:
    if key not in st.session_state:
        st.session_state[key] = None if 'id' in key or 'data' in key else ""

korean_name_map = {
    "Jacob Misiorowski": "제이콥 미시오로우스키", "Jacob Degrom": "제이콥 디그롬",
    "Shohei Ohtani": "오타니 쇼헤이", "Hyun Jin Ryu": "류현진", "Corbin Burnes": "코빈 번스"
}

@st.cache_data(show_spinner="선수 데이터베이스를 연동 중입니다...")
def load_player_db():
    from pybaseball import chadwick_register
    df = chadwick_register().dropna(subset=['key_mlbam', 'name_first', 'name_last'])
    df['full_name'] = df['name_first'].str.title() + " " + df['name_last'].str.title()
    df['korean_name'] = df['full_name'].map(korean_name_map).fillna(df['full_name'])
    return df[['key_mlbam', 'full_name', 'korean_name', 'name_first', 'name_last']]

player_db = load_player_db()

pitch_translation = {
    '4-Seam Fastball': '포심 패스트볼', 'Slider': '슬라이더', 'Curveball': '커브',
    'Changeup': '체인지업', 'Cutter': '커터', 'Sinker': '싱커', 'Splitter': '스플리터',
    'Knuckle Curve': '너클 커브', 'Sweeper': '스위퍼', 'Slurve': '슬러브'
}

pitch_colors = {
    '포심 패스트볼': '#ef4444', '슬라이더': '#eab308', '체인지업': '#10b981',
    '커브': '#3b82f6', '커터': '#ec4899', '싱커': '#f97316', '스위퍼': '#8b5cf6', '스플리터': '#14b8a6'
}

def apply_chart_style(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0"), yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        margin=dict(t=30, b=20, l=10, r=10), font=dict(family="Pretendard", color="#334155")
    )
    return fig

# --- 사이드바 ---
st.sidebar.markdown("### ⚾ MLB Pitching Lab")
st.sidebar.caption("메이저리그 투구 트래킹 분석 시스템")
menu = st.sidebar.radio("메뉴 선택", ["투구 데이터 분석", "선수 프로필"])

if menu == "투구 데이터 분석":
    st.markdown("## MLB 정규시즌 투구 분석 대시보드")
    
    col_s1, col_s2, col_s3 = st.columns([1.5, 1.5, 1])
    with col_s1:
        search_term = st.text_input("선수 이름 검색 (한글/영어)", placeholder="예: 제이콥, ohtani")
    
    selected_player_id = None
    with col_s2:
        if search_term:
            matches = player_db[
                player_db['full_name'].str.contains(search_term, case=False, na=False) |
                player_db['korean_name'].str.contains(search_term, case=False, na=False)
            ]
            if not matches.empty:
                matches['display'] = matches['korean_name'] + " (MLB ID: " + matches['key_mlbam'].astype(int).astype(str) + ")"
                selected_option = st.selectbox("검색된 선수 목록에서 선택", matches['display'].tolist())
                if selected_option:
                    selected_player_id = int(selected_option.split("MLB ID: ")[1].replace(")", ""))
                    st.session_state.temp_name = selected_option.split(" (MLB")[0]
                    target_row = matches[matches['key_mlbam'] == selected_player_id].iloc[0]
                    st.session_state.temp_first = target_row['name_first']
                    st.session_state.temp_last = target_row['name_last']
            else:
                st.selectbox("검색 결과", ["일치하는 선수가 없습니다."], disabled=True)
        else:
            st.selectbox("검색 결과", ["이름을 검색하세요"], disabled=True)

    with col_s3:
        start_date = st.date_input("수집 시작일", datetime.date(2023, 1, 1))
        end_date = st.date_input("수집 종료일", datetime.date.today())

    if selected_player_id and st.button("데이터 분석 실행"):
        with st.spinner("정규시즌 데이터 렌더링 중..."):
            df = statcast_pitcher(str(start_date), str(end_date), player_id=selected_player_id)
            if df.empty:
                st.warning("투구 기록이 없습니다.")
                st.session_state.pitch_data = None
            else:
                # 🌟 [오직 정규시즌(R) 데이터만 엄격 필터링]
                df = df[df['game_type'] == 'R']
                
                if df.empty:
                    st.warning("해당 기간 내 정규시즌 등판 기록이 없습니다.")
                    st.session_state.pitch_data = None
                else:
                    df = df.dropna(subset=['pitch_type', 'release_speed'], how='any')
                    df = df[df['release_speed'] > 0]
                    
                    df['투구_결과'] = df['type'].replace({'S': '스트라이크', 'B': '볼', 'X': '인플레이(타격)'})
                    df['pitch_name'] = df['pitch_name'].replace(pitch_translation)
                    df['game_date'] = pd.to_datetime(df['game_date']).dt.date
                    df['year'] = pd.to_datetime(df['game_date']).dt.year
                    df['month'] = pd.to_datetime(df['game_date']).dt.month
                    df['inning'] = pd.to_numeric(df['inning'], errors='coerce').fillna(0)
                    
                    # 날짜순 정렬 후, 이닝 순서대로 정렬
                    df = df.sort_values(['game_date', 'inning']).reset_index(drop=True)
                    
                    st.session_state.pitch_data = df
                    st.session_state.current_player_id = selected_player_id
                    st.session_state.current_player_name = st.session_state.temp_name
                    st.session_state.current_first_name = st.session_state.temp_first
                    st.session_state.current_last_name = st.session_state.temp_last

    if st.session_state.pitch_data is not None:
        df = st.session_state.pitch_data
        
        st.markdown("<br><hr style='border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
        st.markdown(f"### {st.session_state.current_player_name} 정규시즌 세부 분석")
        
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        years = sorted(df['year'].unique(), reverse=True)
        selected_year = col_f1.selectbox("연도", ["전체"] + list(years))
        df_year = df if selected_year == "전체" else df[df['year'] == selected_year]
        
        months = sorted(df_year['month'].unique())
        selected_month = col_f2.selectbox("월", ["전체"] + [f"{m}월" for m in months])
        df_month = df_year if selected_month == "전체" else df_year[df_year['month'] == int(selected_month.replace("월", ""))]
            
        games = sorted(df_month['game_date'].unique())
        selected_game = col_f3.selectbox("특정 경기일", ["전체"] + list(games))
        df_game = df_month if selected_game == "전체" else df_month[df_month['game_date'] == selected_game]
        
        available_pitches = df_game['pitch_name'].dropna().unique().tolist()
        selected_pitch = col_f4.selectbox("특정 구종 정밀 분석", ["전체 구종"] + available_pitches)
        filtered_df = df_game if selected_pitch == "전체 구종" else df_game[df_game['pitch_name'] == selected_pitch]
        filtered_df = filtered_df.copy()

        total_pitches = len(filtered_df)
        num_games = len(filtered_df['game_date'].unique())
        avg_velo = round(filtered_df['release_speed'].mean(), 1) if total_pitches > 0 else 0
        max_velo = round(filtered_df['release_speed'].max(), 1) if total_pitches > 0 else 0
        strike_rate = round((len(filtered_df[filtered_df['type'].isin(['S', 'X'])]) / total_pitches) * 100, 1) if total_pitches > 0 else 0
        
        total_innings = 0
        avg_innings = 0
        if total_pitches > 0:
            game_innings = filtered_df.groupby('game_date')['inning'].max()
            total_innings = round(game_innings.sum(), 1)
            avg_innings = round(game_innings.mean(), 1)

        st.markdown("<br>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["📊 체력 및 워크로드 지표", "🔥 구위 및 제구 지표"])
        
        with tab1:
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("정규시즌 등판 경기", f"{num_games}경기")
            kpi2.metric("총 마운드 진입", f"{total_innings}회")
            kpi3.metric("평균 마운드 진입", f"{avg_innings}회")
            kpi4.metric("총 투구 수", f"{total_pitches}구")
            
        with tab2:
            kpi5, kpi6, kpi7 = st.columns(3)
            kpi5.metric("평균 구속", f"{avg_velo} mph")
            kpi6.metric("최고 구속", f"{max_velo} mph")
            kpi7.metric("스트라이크 비율", f"{strike_rate}%")
            
        st.markdown("<br>", unsafe_allow_html=True)

        if total_pitches > 0:
            if selected_game == "전체" and num_games > 1 and selected_pitch == "전체 구종":
                st.markdown("#### 정규시즌 경기별 이닝 소화 및 투구수 워크로드")
                
                workload_df = df_game.groupby('game_date').agg(
                    투구수=('pitch_name', 'count'),
                    최대이닝=('inning', 'max')
                ).reset_index()

                fig_workload = go.Figure()
                
                fig_workload.add_trace(go.Bar(
                    x=workload_df['game_date'], y=workload_df['투구수'],
                    name='투구수', marker_color='#cbd5e1', opacity=0.8,
                    hovertemplate='투구수: %{y}구<extra></extra>'
                ))
                
                fig_workload.add_trace(go.Scatter(
                    x=workload_df['game_date'], y=workload_df['최대이닝'],
                    name='마지막 투구 이닝', mode='lines+markers',
                    marker=dict(color='#ef4444', size=8), line=dict(width=3, color='#ef4444'),
                    yaxis='y2', hovertemplate='이닝: %{y}이닝<extra></extra>'
                ))
                
                fig_workload.add_trace(go.Scatter(
                    x=[workload_df['game_date'].min(), workload_df['game_date'].max()],
                    y=[avg_innings, avg_innings], name=f'평균 ({avg_innings}이닝)', mode='lines',
                    line=dict(color='rgba(239, 68, 68, 0.4)', width=2, dash='dash'), yaxis='y2', hoverinfo='skip'
                ))
                
                fig_workload.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
                    yaxis=dict(title="총 투구수", showgrid=True, gridcolor="#e2e8f0", side='left'),
                    yaxis2=dict(title="이닝", showgrid=False, overlaying='y', side='right', range=[0, 10]),
                    margin=dict(t=30, b=20, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    font=dict(family="Pretendard", color="#334155"), hovermode="x unified"
                )
                st.plotly_chart(fig_workload, use_container_width=True)
                st.markdown("---")

            col_top1, col_top2 = st.columns(2)
            with col_top1:
                st.markdown("#### 구종 구사율")
                pitch_counts = filtered_df['pitch_name'].value_counts().reset_index()
                pitch_counts.columns = ['pitch_name', 'count']
                fig_pie = px.pie(pitch_counts, values='count', names='pitch_name', hole=0.4, color='pitch_name', color_discrete_map=pitch_colors)
                st.plotly_chart(apply_chart_style(fig_pie), use_container_width=True)

            with col_top2:
                st.markdown(f"#### ABS 스트라이크 존 궤적 ({selected_pitch})")
                fig_abs = px.scatter(filtered_df, x='plate_x', y='plate_z', color='pitch_name', hover_data=['release_speed', '투구_결과'], color_discrete_map=pitch_colors)
                fig_abs.add_shape(type="rect", x0=-0.71, y0=1.5, x1=0.71, y1=3.5, line=dict(color="#64748b", width=2), fillcolor="rgba(0,0,0,0)")
                fig_abs.add_shape(type="path", path="M -0.71 0 L 0.71 0 L 0.71 0.2 L 0 0.5 L -0.71 0.2 Z", fillcolor="#e2e8f0", line_color="#94a3b8")
                fig_abs.update_layout(xaxis_title="플레이트 좌우 (ft)", yaxis_title="통과 높이 (ft)", xaxis_range=[-2.5, 2.5], yaxis_range=[-0.2, 4.8])
                st.plotly_chart(apply_chart_style(fig_abs), use_container_width=True)

            col_bot1, col_bot2 = st.columns(2)
            with col_bot1:
                st.markdown("#### 릴리스 포인트 탄착군")
                avg_x = filtered_df['release_pos_x'].mean()
                avg_z = filtered_df['release_pos_z'].mean()
                fig_rel = px.scatter(filtered_df, x='release_pos_x', y='release_pos_z', color='pitch_name', hover_data=['release_speed', '투구_결과'], color_discrete_map=pitch_colors)
                fig_rel.add_vline(x=avg_x, line_dash="dot", line_color="#94a3b8")
                fig_rel.add_hline(y=avg_z, line_dash="dot", line_color="#94a3b8")
                fig_rel.update_layout(xaxis_title="좌우 위치 (ft)", yaxis_title="공의 높이 (ft)")
                st.plotly_chart(apply_chart_style(fig_rel), use_container_width=True)
                
            with col_bot2:
                if selected_game == "전체" and num_games > 1:
                    st.markdown("#### 경기별 평균 구속 흐름")
                    velo_df = filtered_df.groupby([filtered_df['game_date'], 'pitch_name'])['release_speed'].mean().reset_index()
                    fig_velo = px.line(velo_df, x='game_date', y='release_speed', color='pitch_name', markers=True, color_discrete_map=pitch_colors)
                    fig_velo.update_layout(xaxis_title="경기 날짜", yaxis_title="평균 구속 (mph)")
                else:
                    st.markdown("#### 투구 순서별 구속 변화")
                    filtered_df['pitch_no'] = range(1, len(filtered_df) + 1)
                    fig_velo = px.line(filtered_df, x='pitch_no', y='release_speed', color='pitch_name', markers=True, color_discrete_map=pitch_colors)
                    fig_velo.update_layout(xaxis_title="투구 순서", yaxis_title="구속 (mph)")
                
                st.plotly_chart(apply_chart_style(fig_velo), use_container_width=True)
                
            st.markdown("---")
            st.markdown("#### 정규시즌 세부 투구 로그")
            st.dataframe(filtered_df[['game_date', 'inning', 'pitch_name', '투구_결과', 'release_speed', 'plate_x', 'plate_z']].rename(columns={'inning': '이닝'}), use_container_width=True, hide_index=True)

elif menu == "선수 프로필":
    if st.session_state.current_player_id:
        st.markdown(f"## {st.session_state.current_player_name} 공식 프로필")
        st.markdown("<br>", unsafe_allow_html=True)
        
        mlbam_id = st.session_state.current_player_id
        name_display = st.session_state.current_player_name
        first_name = st.session_state.current_first_name
        last_name = st.session_state.current_last_name
        
        img_url = f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current/w_426,q_auto:best/v1/people/{mlbam_id}/headshot/67/current"
        
        p_col1, p_col2 = st.columns([1, 2])
        with p_col1:
            st.image(img_url, use_container_width=True)
        with p_col2:
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <h4 style="color: #0f172a; margin-bottom: 16px;">등록 정보</h4>
                <ul style="color: #475569; font-size: 1.05rem; line-height: 1.8;">
                    <li><b>선수명:</b> {name_display}</li>
                    <li><b>MLB 고유 식별 번호:</b> <code>{mlbam_id}</code></li>
                    <li><b>데이터 출처:</b> Major League Baseball (MLBAM)</li>
                </ul>
                <hr style="border: 1px solid #f1f5f9; margin: 24px 0;">
                <h4 style="color: #0f172a; margin-bottom: 16px;">외부 전문 통계실 연동</h4>
                <ul style="color: #475569; font-size: 1.05rem; line-height: 1.8;">
                    <li><a href="https://www.baseball-reference.com/search/search.fcgi?search={first_name}+{last_name}" target="_blank" style="color: #2563eb; text-decoration: none;">Baseball-Reference ({name_display} 통산 성적 바로가기)</a></li>
                    <li><a href="https://www.fangraphs.com/players/{first_name}-{last_name}" target="_blank" style="color: #2563eb; text-decoration: none;">FanGraphs (세이버메트릭스 리포트 바로가기)</a></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.title("선수 프로필")
        st.info("투구 데이터 분석 메뉴에서 선수를 검색해 주세요.")