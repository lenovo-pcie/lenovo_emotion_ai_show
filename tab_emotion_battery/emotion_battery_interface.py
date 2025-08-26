#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emotion Battery Analysis Interface
"""

def create_emotion_battery_interface():
    """Create emotion battery interface with Today's Emotion Battery and Single Day Analysis functionality"""
    
    import gradio as gr
    import plotly.graph_objects as go
    import sqlite3
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Emotion constants and mappings
    ALL_EMOTIONS = ["Neutral", "Happy", "Angry", "Sad", "Surprised", "Worried"]
    
    EMOTION_WEIGHT = {
        "Happy": 500,        # 快乐：+500 分
        "Surprised": 300,    # 惊讶：+300 分
        "Sad": -300,         # 悲伤：-300 分
        "Angry": -400,       # 愤怒：-400 分
        "Worried": -300,     # 担忧：-300 分
        "Neutral": 0         # 中性：0 分
    }

    # Map Chinese labels from DB to English keys used in EMOTION_WEIGHT
    EMOTION_LABEL_MAP_ZH2EN = {
        "中立": "Neutral",
        "开心": "Happy",
        "高兴": "Happy",
        "愤怒": "Angry",
        "生气": "Angry",
        "悲伤": "Sad",
        "伤心": "Sad",
        "惊讶": "Surprised",
        "担忧": "Worried",
        "忧虑": "Worried"
    }

    # Also accept English passthrough (no-op); unmapped labels remain as-is
    
    # Battery analysis parameters
    startV = 90    # Starting battery level: 90%
    endV = 60      # Ending battery level: 60%
    timeS = "08:00"  # Start time: 08:00
    timeE = "17:59"  # End time: 17:59
    timeP = 10       # Time period in minutes
    
    def analyze_emotion_battery(day, show_log=False, plot=False, db_path='emotion_data.db'):
        """Analyze emotion battery for a specific day"""
        try:
            print(f"Starting analysis for day: {day}, database: {db_path}")
            
            start_dt = datetime.strptime(f"{day}{timeS}", "%Y%m%d%H:%M")
            end_dt = datetime.strptime(f"{day}{timeE}", "%Y%m%d%H:%M")
            
            # Generate time bins
            bins = []
            cur = start_dt
            while cur < end_dt:
                bins.append(cur)
                cur += timedelta(minutes=timeP)
            bins.append(end_dt)
            n_bins = len(bins) - 1
            
            print(f"Generated {n_bins} time bins from {start_dt} to {end_dt}")
            
            # Calculate decrement per period
            if n_bins > 0:
                downV = (startV - endV) / n_bins
            else:
                downV = 0
            
            # Read database data
            conn = sqlite3.connect(db_path)
            query = f"""
            SELECT timestamp, emotion FROM emotion_records
            WHERE substr(timestamp, 1, 8) = ? AND has_face = 1
            """
            print(f"Executing query: {query} with day: {day}")
            
            df = pd.read_sql_query(query, conn, params=[day])
            conn.close()
            
            print(f"Database query returned {len(df)} records")
            if not df.empty:
                print(f"Sample timestamps: {df['timestamp'].head().tolist()}")
            
            # Parse timestamps
            if not df.empty:
                df['dt'] = pd.to_datetime(df['timestamp'].str[:13], format='%Y%m%d-%H%M', errors='coerce')
                # Normalize emotion labels to English keys used in EMOTION_WEIGHT
                df['emotion_norm'] = df['emotion'].astype(str).map(lambda x: EMOTION_LABEL_MAP_ZH2EN.get(x, x))
                # Remove rows with invalid timestamps
                df = df.dropna(subset=['dt'])
                print(f"After timestamp parsing: {len(df)} valid records")
            else:
                df['dt'] = []
                df['emotion_norm'] = []
            
            dataTotal = len(df)
            battery_list = []
            impact_list = []
            x_labels = []
            curV = startV
            now = datetime.now()
            is_today = (day == now.strftime('%Y%m%d'))
            current_battery = None
            
            print(f"Processing {n_bins} time bins with {dataTotal} total records")
            
            for i in range(n_bins):
                bin_start = bins[i]
                bin_end = bins[i+1]
                x_labels.append(bin_start.strftime('%H:%M'))
                
                # If it's today and time period is in the future, battery = 0
                if is_today and bin_start > now:
                    battery_list.append(0)
                    impact_list.append('0.00')
                    continue
                
                # Get data for this time bin
                bin_df = df[(df['dt'] >= bin_start) & (df['dt'] < bin_end)]
                if not bin_df.empty and 'emotion_norm' in bin_df.columns:
                    # Count using normalized labels
                    emotion_counts = bin_df['emotion_norm'].value_counts().to_dict()
                else:
                    emotion_counts = {}
                
                # Calculate emotional impact
                impact = 0
                impact_detail = []
                for emo, weight in EMOTION_WEIGHT.items():
                    count = emotion_counts.get(emo, 0)
                    ratio = count / dataTotal if dataTotal > 0 else 0
                    emo_impact = ratio * weight
                    impact += emo_impact
                    if count > 0:
                        impact_detail.append(f"{emo}:{emo_impact:+.2f}")
                
                impact_str = ', '.join(impact_detail) if impact_detail else '0.00'
                impact_list.append(impact_str)
                
                # Update battery level
                if curV < 50:
                    curV = curV + downV + impact
                else:
                    curV = curV - downV + impact
                
                curV = max(20, min(100, curV))
                battery_val = int(round(curV))
                battery_list.append(battery_val)
                
                # Record current battery level if this is the current time period
                if is_today and bin_start <= now < bin_end:
                    current_battery = battery_val
                
                if show_log:
                    print(f"\n==== Time Period {bin_start.strftime('%H:%M')} - {bin_end.strftime('%H:%M')} ====")
                    print(f"Raw data:\n{bin_df[['timestamp','emotion','emotion_norm','dt']] if not bin_df.empty else 'None'}")
                    print(f"Emotion counts: {emotion_counts}")
                    print(f"Impact details: {impact_str}")
                    print(f"Battery level: {battery_val}")
            
            print(f"Analysis completed. Generated {len(x_labels)} labels, {len(battery_list)} battery values, {len(impact_list)} impact values")
            return x_labels, battery_list, impact_list, current_battery
            
        except Exception as e:
            print(f"Error in analyze_emotion_battery: {e}")
            import traceback
            traceback.print_exc()
            if show_log:
                print(f"Error in analyze_emotion_battery: {e}")
            return [], [], [], None
    
    def create_today_battery_chart():
        """Create Today's Emotion Battery chart"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            x_labels, battery_list, impact_list, current_battery = analyze_emotion_battery(
                today, show_log=False, plot=False, db_path='emotion_data.db'
            )
            
            if not battery_list:
                # Return empty chart with message
                fig = go.Figure()
                fig.add_annotation(
                    text="No data for today",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16)
                )
                fig.update_layout(
                    title="Today's Emotion Battery by 10min",
                    xaxis_title="Time",
                    yaxis_title="Emotion Battery",
                    height=400
                )
                return fig
            
            # Create bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=x_labels,
                y=battery_list,
                marker_color='#44aaff',
                text=[f"{v}" for v in battery_list],
                textposition='auto',
                customdata=impact_list,
                hovertemplate='Time: %{x}<br>Battery: %{y}<br>Impact: %{customdata}<extra></extra>',
                name="Today's Battery"
            ))
            
            fig.update_layout(
                title="Today's Emotion Battery by 10min",
                xaxis_title="Time",
                yaxis_title="Emotion Battery",
                yaxis=dict(range=[20, 100]),
                bargap=0.2,
                height=400
            )
            
            return fig
            
        except Exception as e:
            # Return error chart
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color='red')
            )
            fig.update_layout(
                title="Today's Emotion Battery by 10min",
                xaxis_title="Time",
                yaxis_title="Emotion Battery",
                height=400
            )
            return fig
    
    def create_single_day_battery_chart(selected_date, use_fake_db=False):
        """Create Single Day Emotion Battery Analysis chart"""
        try:
            # Determine database path
            db_path = 'emotion_data_fake.db' if use_fake_db else 'emotion_data.db'
            
            # Check if database file exists
            import os
            if not os.path.exists(db_path):
                # Return error chart for missing database
                fig = go.Figure()
                fig.add_annotation(
                    text=f"Database file not found: {db_path}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color='red')
                )
                fig.update_layout(
                    title="Single Day Emotion Battery Analysis",
                    xaxis_title="Time",
                    yaxis_title="Emotion Battery",
                    height=400
                )
                return fig
            
            if use_fake_db:
                # For fake database, try to find a date with data
                day = '20250721'  # Default fake data date
                
                # Try to find any available date in the fake database
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT substr(timestamp, 1, 8) FROM emotion_records WHERE has_face = 1 LIMIT 1")
                    result = cursor.fetchone()
                    if result:
                        day = result[0]
                    conn.close()
                except Exception as e:
                    print(f"Error finding date in fake database: {e}")
                    day = '20250721'  # Fallback to default
            else:
                if not selected_date:
                    # Return empty chart with message
                    fig = go.Figure()
                    fig.add_annotation(
                        text="Please select a date",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16)
                    )
                    fig.update_layout(
                        title="Single Day Emotion Battery Analysis",
                        xaxis_title="Time",
                        yaxis_title="Emotion Battery",
                        height=400
                    )
                    return fig
                
                try:
                    # Convert date string to required format
                    if isinstance(selected_date, str):
                        # Handle different date formats
                        if '-' in selected_date:
                            dt = pd.to_datetime(selected_date)
                        else:
                            dt = pd.to_datetime(selected_date, format='%Y%m%d')
                    else:
                        dt = pd.to_datetime(selected_date)
                    day = dt.strftime('%Y%m%d')
                except Exception:
                    # Return error chart
                    fig = go.Figure()
                    fig.add_annotation(
                        text="Invalid date format",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16)
                    )
                    fig.update_layout(
                        title="Single Day Emotion Battery Analysis",
                        xaxis_title="Time",
                        yaxis_title="Emotion Battery",
                        height=400
                    )
                    return fig
            
            print(f"Analyzing day: {day} with database: {db_path}")
            
            # Analyze emotion battery for the selected day
            x_labels, battery_list, impact_list, _ = analyze_emotion_battery(
                day, show_log=True, plot=False, db_path=db_path  # Enable logging for debugging
            )
            
            print(f"Analysis results - x_labels: {len(x_labels)}, battery_list: {len(battery_list)}, impact_list: {len(impact_list)}")
            
            if not x_labels:
                # Return empty chart with message
                fig = go.Figure()
                fig.add_annotation(
                    text=f"No data for this day ({day}) in {db_path}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16)
                )
                fig.update_layout(
                    title="Single Day Emotion Battery Analysis",
                    xaxis_title="Time",
                    yaxis_title="Emotion Battery",
                    height=400
                )
                return fig
            
            # Create bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=x_labels,
                y=battery_list,
                marker_color='#44aaff',
                text=[f"{int(round(v))}" for v in battery_list],
                textposition='auto',
                customdata=impact_list,
                hovertemplate='Time: %{x}<br>Battery: %{y}<br>Impact: %{customdata}<extra></extra>',
                name='Emotion Battery'
            ))
            
            fig.update_layout(
                title=f"Emotion Battery by 10min ({day})",
                xaxis_title="Time",
                yaxis_title="Emotion Battery",
                yaxis=dict(range=[20, 100]),
                bargap=0.2,
                height=400
            )
            
            return fig
            
        except Exception as e:
            # Return error chart
            fig = go.Figure()
            fig.add_annotation(
                text=f"Analysis error: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color='red')
            )
            fig.update_layout(
                title="Single Day Emotion Battery Analysis",
                xaxis_title="Time",
                yaxis_title="Emotion Battery",
                height=400
            )
            return fig
    
    def get_today_battery_level():
        """Get today's current battery level"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            x_labels, battery_list, impact_list, current_battery = analyze_emotion_battery(
                today, show_log=False, plot=False, db_path='emotion_data.db'
            )
            
            if current_battery is not None:
                return current_battery
            elif battery_list:
                return int(round(battery_list[-1]))
            else:
                return 80  # Default neutral level
                
        except Exception as e:
            return 80  # Default on error
    
    def get_battery_status(battery_level):
        """Get battery status description"""
        if battery_level >= 80:
            return "Excellent", "🟢", "#44ff44"
        elif battery_level >= 60:
            return "Good", "🟡", "#ffaa00"
        elif battery_level >= 40:
            return "Fair", "🟠", "#ff8800"
        else:
            return "Low", "🔴", "#ff4444"
    
    # Create Gradio interface
    with gr.Blocks(title="Emotion Battery", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# 🔋 Emotion Battery Analysis")
        
        # Today's Battery Section
        gr.Markdown("## 📊 Today's Emotion Battery")
        gr.Markdown("This module shows your current emotion battery level and hourly breakdown for today.")
        
        with gr.Row():
            with gr.Column(scale=1):
                # Battery level display
                battery_level = get_today_battery_level()
                status_text, status_emoji, status_color = get_battery_status(battery_level)
                
                gr.Markdown(f"### {status_emoji} Current Battery Level")
                gr.Markdown(f"## <span style='color: {status_color}; font-size: 48px; font-weight: bold;'>{battery_level}%</span>")
                gr.Markdown(f"**Status:** {status_text}")
                
                # Update button
                update_btn = gr.Button("🔄 Refresh Battery Level", variant="primary")
                
            with gr.Column(scale=2):
                # Battery chart
                chart_output = gr.Plot(
                    value=create_today_battery_chart(),
                    label="Today's Emotion Battery Chart"
                )
        
        gr.Markdown("---")
        
        # Single Day Analysis Section
        gr.Markdown("## 📅 Single Day Emotion Battery Analysis")
        gr.Markdown("Analyze emotion battery for any specific day with detailed 10-minute breakdown.")
        
        with gr.Row():
            with gr.Column(scale=2):
                # Date input
                date_input = gr.Textbox(
                    label="Date (YYYY-MM-DD or YYYYMMDD)",
                    placeholder="e.g., 2025-01-15 or 20250115",
                    value=datetime.now().strftime('%Y-%m-%d')
                )
                
                # Fake database toggle
                fake_db_checkbox = gr.Checkbox(
                    label="Use emotion_data_fake.db (for testing)",
                    value=False
                )
                
                # Analysis button
                analyze_btn = gr.Button("🔍 Analyze Selected Day", variant="primary")
                
            with gr.Column(scale=1):
                # Status info
                gr.Markdown("### 📋 Analysis Options")
                gr.Markdown("- **Date Selection**: Choose any date to analyze")
                gr.Markdown("- **Database**: Switch between real and test data")
                gr.Markdown("- **10-min Intervals**: Detailed time breakdown")
                gr.Markdown("- **Impact Analysis**: See emotional influences")
        
        # Single day chart output
        single_day_chart = gr.Plot(
            value=create_single_day_battery_chart(None, False),
            label="Single Day Emotion Battery Analysis"
        )
        
        gr.Markdown("---")
        gr.Markdown("### 📋 Chart Features")
        gr.Markdown("- **Real-time Data**: Shows your emotion battery level throughout the day")
        gr.Markdown("- **10-Minute Intervals**: Detailed breakdown by time periods")
        gr.Markdown("- **Interactive**: Hover over bars to see impact details")
        gr.Markdown("- **Current Status**: Displays your current battery level")
        gr.Markdown("- **Historical Analysis**: Analyze any specific day")
        gr.Markdown("- **Auto-update**: Click refresh to get latest data")
        
        # Event handlers
        def update_battery():
            """Update battery level and chart"""
            new_level = get_today_battery_level()
            new_chart = create_today_battery_chart()
            return str(new_level), new_chart
        
        def analyze_single_day(date_str, use_fake_db):
            """Analyze single day emotion battery"""
            return create_single_day_battery_chart(date_str, use_fake_db)
        
        update_btn.click(
            fn=update_battery,
            outputs=[gr.Textbox(value=str(get_today_battery_level())), chart_output]
        )
        
        analyze_btn.click(
            fn=analyze_single_day,
            inputs=[date_input, fake_db_checkbox],
            outputs=single_day_chart
        )
    
    return interface

if __name__ == "__main__":
    print("Starting Emotion Battery Interface...")
    interface = create_emotion_battery_interface()
    print("Interface created successfully!")
    interface.launch()
