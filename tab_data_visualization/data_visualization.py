import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import numpy as np

# Define all possible emotion types
ALL_EMOTIONS = ["Neutral", "Happy", "Angry", "Sad", "Surprised", "Worried"]

# 英文转中文映射
emotion_en2zh = {
    "Neutral": "中立",
    "Happy": "快乐",
    "Angry": "愤怒",
    "Sad": "悲伤",
    "Surprised": "惊讶",
    "Worried": "担忧"
}

EMOTION_COLOR_MAP = {
    "Neutral": "#7f7f7f",
    "Happy": "#FFD700",
    "Angry": "#d62728",
    "Sad": "#1f77b4",
    "Surprised": "#ff7f0e",
    "Worried": "#9467bd"
}

def parse_date_input(date_str):
    """Parse various date input formats and return YYYYMMDD-000000 format"""
    if not date_str:
        return None
    
    try:
        # Try YYYY-MM-DD format
        if '-' in date_str:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        # Try YYYY/MM/DD format
        elif '/' in date_str:
            dt = datetime.strptime(date_str, '%Y/%m/%d')
        # Try YYYYMMDD format
        elif len(date_str) == 8:
            dt = datetime.strptime(date_str, '%Y%m%d')
        else:
            return None
        return dt.strftime('%Y%m%d-000000')
    except ValueError:
        return None

def parse_date_input_end(date_str):
    """Parse various date input formats and return YYYYMMDD-235959 format"""
    if not date_str:
        return None
    
    try:
        # Try YYYY-MM-DD format
        if '-' in date_str:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        # Try YYYY/MM/DD format
        elif '/' in date_str:
            dt = datetime.strptime(date_str, '%Y/%m/%d')
        # Try YYYYMMDD format
        elif len(date_str) == 8:
            dt = datetime.strptime(date_str, '%Y%m%d')
        else:
            return None
        return dt.strftime('%Y%m%d-235959')
    except ValueError:
        return None

def get_all_usernames(db_path='emotion_data.db'):
    """Get all unique usernames from database"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT DISTINCT username FROM emotion_records WHERE username IS NOT NULL", conn)
        usernames = df['username'].dropna().unique().tolist()
        usernames = [u for u in usernames if u]
        usernames.sort()
        conn.close()
        return usernames
    except Exception:
        return []

def get_data_with_username(start_date, end_date, emotion_filter, username, db_path='emotion_data.db'):
    """Get data from database with filters"""
    try:
        conn = sqlite3.connect(db_path)
        query = "SELECT * FROM emotion_records WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND substr(timestamp, 1, 13) >= ?"
            params.append(start_date[:13])
        
        if end_date:
            query += " AND substr(timestamp, 1, 13) <= ?"
            params.append(end_date[:13])
        
        # 多选情绪过滤
        if emotion_filter and isinstance(emotion_filter, list) and len(emotion_filter) > 0:
            emotion_filter_db = [emotion_en2zh.get(e, e) for e in emotion_filter]
            placeholders = ','.join(['?'] * len(emotion_filter_db))
            query += f" AND emotion IN ({placeholders})"
            params.extend(emotion_filter_db)
        
        if username and username != 'All':
            query += " AND username = ?"
            params.append(username)
        
        query += " ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        # Convert timestamp format and map emotion
        if not df.empty:
            # 只取前15位，保证格式统一
            df['datetime'] = pd.to_datetime(df['timestamp'].str[:15], format='%Y%m%d-%H%M%S', errors='coerce')
            df['date'] = df['datetime'].dt.date
            df['hour'] = df['datetime'].dt.hour
            
            emotion_mapping = {
                "中立": "Neutral",
                "中性": "Neutral",
                "快乐": "Happy",
                "愤怒": "Angry",
                "悲伤": "Sad",
                "惊讶": "Surprised",
                "担忧": "Worried",
                "无": "None"
            }
            df['emotion_en'] = df['emotion'].map(emotion_mapping).fillna(df['emotion'])
            df['emotion_en'] = df['emotion_en'].replace({"中性": "Neutral", "中立": "Neutral"})
        
        return df
    except Exception as e:
        print(f"Database query error: {e}")
        return pd.DataFrame()

def create_daily_emotion_distribution_chart(start_date, end_date, emotion_filter, username):
    """Create Daily Emotion Distribution (Percentage) chart"""
    if not start_date or not end_date:
        return go.Figure().add_annotation(
            text="Please select start and end dates",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    start_str = parse_date_input(start_date)
    end_str = parse_date_input_end(end_date)
    
    if not start_str or not end_str:
        return go.Figure().add_annotation(
            text="Invalid date format. Use YYYY-MM-DD, YYYY/MM/DD, or YYYYMMDD",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    df = get_data_with_username(start_str, end_str, emotion_filter, username)
    
    # 过滤无效日期和1970年及以前的异常数据
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df[df['date'].notnull()]
        df = df[df['date'] > pd.Timestamp('1980-01-01')]
    
    if df.empty:
        return go.Figure().add_annotation(
            text="No daily emotion data available for selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # 统计每天每种情绪的数量
    daily_emotions = df.groupby(['date', 'emotion_en']).size().reset_index(name='count')
    
    # 确保所有日期和所有情绪类型都有数据
    date_min = pd.to_datetime(df['date']).min()
    date_max = pd.to_datetime(df['date']).max()
    all_dates = pd.date_range(date_min, date_max)
    all_emotions = ALL_EMOTIONS
    
    idx = pd.MultiIndex.from_product([all_dates, all_emotions], names=['date', 'emotion_en'])
    daily_emotions = daily_emotions.set_index(['date', 'emotion_en']).reindex(idx, fill_value=0).reset_index()
    
    # 绘制分组柱状图（基于百分比）
    fig = go.Figure()
    min_bar_height = 0.01  # 0数据的柱子最小高度（百分比）
    
    for emotion in ALL_EMOTIONS:
        emotion_data = daily_emotions[daily_emotions['emotion_en'] == emotion]
        
        # 计算每日总数和百分比
        emotion_data = emotion_data.copy()
        total_per_day = daily_emotions.groupby('date')['count'].transform('sum')
        emotion_data['percent'] = emotion_data['count'] / total_per_day[emotion_data.index]
        
        # 标签：数量和百分比
        emotion_data['label'] = emotion_data.apply(
            lambda row: f"{int(row['count'])} ({row['percent']:.0%})" if total_per_day[row.name] > 0 else "0 (0%)", 
            axis=1
        )
        
        # 使用百分比作为柱子高度，0数据的柱子显示最小高度
        y_vals = [v if v > 0 else min_bar_height for v in emotion_data['percent']]
        
        fig.add_trace(go.Bar(
            x=emotion_data['date'],
            y=y_vals,
            name=emotion,
            marker_color=EMOTION_COLOR_MAP.get(emotion, None),
            text=emotion_data['label'],
            textposition='auto',
            customdata=emotion_data[['count', 'percent']].values.tolist(),
            hovertemplate='Date: %{x}<br>Emotion: %{name}<br>Count: %{customdata[0]}<br>Percentage: %{customdata[1]:.1%}<extra></extra>'
        ))
    
    fig.update_layout(
        barmode='group',
        title="Daily Emotion Distribution (Percentage)",
        xaxis_title="Date",
        yaxis_title="Percentage",
        xaxis_tickformat='%Y-%m-%d',
        yaxis_tickformat='.0%',
        yaxis=dict(
            range=[0, 1.1],  # 百分比范围0-110%
            dtick=0.1  # 每10%显示一个刻度
        ),
        legend_title="Emotion",
        height=500,
        margin=dict(t=100, b=100, l=80, r=80)
    )
    
    return fig

def create_data_visualization_interface():
    """Create data visualization interface with Daily Emotion Distribution chart"""
    
    with gr.Blocks(title="Data Visualization", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 📊 Data Visualization Module")
        gr.Markdown("Interactive emotion analysis data visualization dashboard")
        
        # Filters Section
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📅 Date Range")
                start_date = gr.Textbox(
                    label="Start Date",
                    placeholder="YYYY-MM-DD, YYYY/MM/DD, or YYYYMMDD",
                    value=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                )
                end_date = gr.Textbox(
                    label="End Date", 
                    placeholder="YYYY-MM-DD, YYYY/MM/DD, or YYYYMMDD",
                    value=datetime.now().strftime('%Y-%m-%d')
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### 👤 User Filter")
                username_filter = gr.Dropdown(
                    label="Username",
                    choices=["All"] + get_all_usernames(),
                    value="All",
                    interactive=True
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### 😊 Emotion Filter")
                emotion_filter = gr.Checkboxgroup(
                    label="Select Emotions",
                    choices=ALL_EMOTIONS,
                    value=[e for e in ALL_EMOTIONS if e != "Neutral"],
                    interactive=True
                )
        
        # Control Buttons
        with gr.Row():
            update_btn = gr.Button("🔄 Update Chart", variant="primary", size="lg")
            refresh_users_btn = gr.Button("🔄 Refresh Users", variant="secondary")
        
        # Chart Display
        gr.Markdown("### 📈 Daily Emotion Distribution (Percentage)")
        gr.Markdown("This chart shows the daily distribution of emotions as percentages over the selected time period.")
        
        chart_output = gr.Plot(
            value=create_daily_emotion_distribution_chart(
                (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                datetime.now().strftime('%Y-%m-%d'),
                [e for e in ALL_EMOTIONS if e != "Neutral"],
                "All"
            ),
            label="Daily Emotion Distribution Chart"
        )
        
        # Information Panel
        with gr.Accordion("ℹ️ Chart Information", open=False):
            gr.Markdown("""
            **Chart Features:**
            - **Grouped Bar Chart**: Each date shows all emotion types side by side
            - **Percentage-based**: Y-axis shows percentage (0-100%) of each emotion per day
            - **Interactive**: Hover over bars to see exact counts and percentages
            - **Color-coded**: Each emotion type has a consistent color
            - **Data Completion**: Missing dates/emotions are filled with 0 values
            
            **Filter Options:**
            - **Date Range**: Select start and end dates for analysis
            - **Username**: Filter data by specific user or view all users
            - **Emotion Types**: Select which emotions to include in the analysis
            
            **Data Source:** emotion_data.db
            """)
        
        # Event Handlers
        def update_chart(start, end, emotions, username):
            return create_daily_emotion_distribution_chart(start, end, emotions, username)
        
        def refresh_user_list():
            users = ["All"] + get_all_usernames()
            return gr.Dropdown(choices=users, value="All")
        
        update_btn.click(
            fn=update_chart,
            inputs=[start_date, end_date, emotion_filter, username_filter],
            outputs=chart_output
        )
        
        refresh_users_btn.click(
            fn=refresh_user_list,
            outputs=username_filter
        )
        
        # Auto-update on filter changes
        start_date.change(
            fn=update_chart,
            inputs=[start_date, end_date, emotion_filter, username_filter],
            outputs=chart_output
        )
        
        end_date.change(
            fn=update_chart,
            inputs=[start_date, end_date, emotion_filter, username_filter],
            outputs=chart_output
        )
        
        emotion_filter.change(
            fn=update_chart,
            inputs=[start_date, end_date, emotion_filter, username_filter],
            outputs=chart_output
        )
        
        username_filter.change(
            fn=update_chart,
            inputs=[start_date, end_date, emotion_filter, username_filter],
            outputs=chart_output
        )
    
    return interface

if __name__ == "__main__":
    interface = create_data_visualization_interface()
    interface.launch()
