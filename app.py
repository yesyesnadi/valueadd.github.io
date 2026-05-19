import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. 데이터베이스 초기화 및 테이블 생성
def init_db():
    conn = sqlite3.connect('valueup_incentive.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incentives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            customer_type TEXT,
            channel_group TEXT,
            channel_detail TEXT,
            item_name TEXT,
            sub_item TEXT,
            amount INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 2. 마스터 데이터 정의
CUSTOMER_TYPES = ["장기고객", "단기고객"]
CHANNELS = {
    "106": ["일반", "기술", "가입(유치)", "가입(이관)", "해지"],
    "CRM": ["신림", "BforU", "유무선결합실"],
    "홈앤서비스": ["서비스매니저", "HS"],
    "SKB": ["지역본부"],
    "SKT": ["대리점", "고객센터"]
}
ITEMS = {
    "Giga 전환": ["Smart3", "AI 기본", "AI4 STB", "일반"],
    "1G 전환": ["Smart3", "AI 기본", "AI4 STB"],
    "STB 교체": ["Smart3", "AI2", "AI4", "AI5", "ATV", "+3분 셀프 설치"],
    "Tier up": ["기본"],
    "B tv pop": ["pop230", "pop180", "pop100", "pop180/100"],
    "B tv pop Tier-up": ["pop230", "pop180/100"],
    "CA WiFi": ["기본"],
    "CA STB 교체": ["기본"],
    "윙즈": ["기본"],
    "B tv+": ["기본"],
    "안심": ["기본"],
    "WiFi": ["기본"]
}

# 3. 사이드바 - 메뉴 네비게이션
st.set_page_config(layout="wide", page_title="밸류업 인센티브 관리 대시보드")
st.sidebar.title("💰 밸류업 예산 관리")
menu = st.sidebar.radio("메뉴를 선택하세요", ["🏠 대시보드 및 시계열 분석", "✍️ 인센티브 입력/수정"])

# 메뉴 1: 대시보드 및 시계열 분석
if menu == "🏠 대시보드 및 시계열 분석":
    st.title("📊 인센티브 조회 및 시계열 추이 분석")
    
    conn = sqlite3.connect('valueup_incentive.db')
    df = pd.read_sql_query("SELECT * FROM incentives", conn)
    conn.close()

    if df.empty:
        st.warning("등록된 데이터가 없습니다. '인센티브 입력/수정' 메뉴에서 데이터를 먼저 입력해주세요.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_month = st.selectbox("조회 월 선택", sorted(df['month'].unique(), reverse=True))
        with col2:
            selected_type = st.selectbox("고객 유형", CUSTOMER_TYPES)
        with col3:
            selected_item = st.selectbox("분석 아이템(열)", list(ITEMS.keys()))

        st.subheader(f"📅 {selected_month} - {selected_type} 단가 테이블")
        month_df = df[(df['month'] == selected_month) & (df['customer_type'] == selected_type)]
        
        if not month_df.empty:
            pivot_df = month_df.pivot_table(
                index=['channel_group', 'channel_detail'], 
                columns=['item_name', 'sub_item'], 
                values='amount', 
                aggfunc='sum'
            ).fillna(0)
            
            st.dataframe(pivot_df, use_container_width=True)
            
            @st.cache_data
            def convert_df(df_to_convert):
                return df_to_convert.to_csv().encode('utf-8-sig')
            
            csv = convert_df(pivot_df)
            st.download_button(
                label="📥 해당 월 단가표 엑셀(CSV) 다운로드",
                data=csv,
                file_name=f"ValueUp_Incentive_{selected_month}_{selected_type}.csv",
                mime="text/csv",
            )
        else:
            st.info("해당 월 및 조건에 데이터가 존재하지 않습니다.")

        st.markdown("---")
        st.subheader(f"📈 {selected_item} 아이템 시계열 단가 변동 추이")
        trend_df = df[(df['customer_type'] == selected_type) & (df['item_name'] == selected_item)]
        
        if not trend_df.empty:
            trend_pivot = trend_df.pivot_table(
                index='month',
                columns=['channel_detail', 'sub_item'],
                values='amount',
                aggfunc='mean'
            ).fillna(0)
            
            st.line_chart(trend_pivot)
            st.caption("※ 상단 차트에서 마우스를 올리면 채널별/기기별 월간 단가 추이를 볼 수 있습니다.")
        else:
            st.info("시계열 분석을 위한 데이터가 부족합니다.")

# 메뉴 2: 인센티브 입력/수정
elif menu == "✍️ 인센티브 입력/수정":
    st.title("✍️ 월별 유통망 인센티브 입력 및 수정")
    st.write("엑셀 취합 필요 없이, 채널별 단가를 웹에서 바로 입력하여 저장합니다.")

    col1, col2, col3 = st.columns(3)
    with col1:
        input_month = st.date_input("적용 년월 선택", datetime.today()).strftime("%Y-%m")
    with col2:
        input_type = st.selectbox("고객 구분", CUSTOMER_TYPES)
    with col3:
        input_g_channel = st.selectbox("대분류 채널 (행)", list(CHANNELS.keys()))

    input_d_channel = st.selectbox("소분류 채널 (행)", CHANNELS[input_g_channel])

    st.markdown(f"### 📋 [{input_month} / {input_type}] {input_g_channel}_{input_d_channel} 단가 설정")
    
    form_data = {}
    cols = st.columns(3)
    idx = 0
    
    for item, subs in ITEMS.items():
        with cols[idx % 3]:
            st.markdown(f"**🔹 {item}**")
            for sub in subs:
                key = f"{item}_{sub}"
                form_data[key] = st.number_input(f"{sub} 단가 (원)", min_value=0, step=500, key=key)
        idx += 1

    if st.button("💾 이 채널 단가 저장하기", type="primary"):
        conn = sqlite3.connect('valueup_incentive.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM incentives 
            WHERE month=? AND customer_type=? AND channel_group=? AND channel_detail=?
        ''', (input_month, input_type, input_g_channel, input_d_channel))
        
        insert_data = []
        for key, amount in form_data.items():
            item_name, sub_item = key.split("_")
            insert_data.append((input_month, input_type, input_g_channel, input_d_channel, item_name, sub_item, amount))
            
        cursor.executemany('''
            INSERT INTO incentives (month, customer_type, channel_group, channel_detail, item_name, sub_item, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', insert_data)
        
        conn.commit()
        conn.close()
        st.success(f"🎉 {input_month} - {input_g_channel} ({input_d_channel}) 단가 저장이 완료되었습니다!")
