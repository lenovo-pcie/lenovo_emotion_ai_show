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
    
    def render_battery_html(level: int, status_text: str = "", status_color: str = "#111", status_emoji: str = "", extra_lines: list | None = None) -> str:
        """Render a vertical battery icon (left) and the number/status (right) as HTML.
        Battery level is 0-100. The battery is vertical with fill height matching level.
        """
        level = max(0, min(100, int(level)))
        # Color by level
        if level <= 20:
            fill_color = "#ff4444"
        elif level <= 50:
            fill_color = "#ffaa00"
        else:
            fill_color = "#44ff44"
        # Sizes
        case_width = 90
        case_height = 220
        border = 6
        cap_width = 38
        cap_height = 14
        # Compose extra lines HTML
        extra_html = ""
        if extra_lines:
            items = []
            for line in extra_lines:
                items.append(f"<div style='font-size:14px; color:#111; margin-top:2px;'>{line}</div>")
            extra_html = "".join(items)
        # HTML layout: left battery (vertical), right number/status
        html = f"""
<div style='display:flex; align-items:center; gap:24px;'>
  <!-- Vertical Battery -->
  <div style='display:flex; flex-direction:column; align-items:center;'>
    <div style='width:{cap_width}px; height:{cap_height}px; background:#333; border-radius:4px 4px 0 0;'></div>
    <div style='position:relative; width:{case_width}px; height:{case_height}px; border:{border}px solid #333; border-radius:16px; box-sizing:border-box; overflow:hidden; background:#f8f8f8;'>
      <div style='position:absolute; bottom:0; left:0; width:100%; height:{level}%; background:{fill_color}; transition:height 300ms ease;'></div>
    </div>
  </div>
  <!-- Number and Status -->
  <div style='display:flex; flex-direction:column; justify-content:center;'>
    <div style='font-size:20px; font-weight:700; margin-bottom:6px;'>{status_emoji} Current Battery Level</div>
    <div style='font-size:64px; font-weight:900; line-height:1; color:{status_color};'>{level}%</div>
    <div style='font-size:18px; color:#222; margin-top:8px;'>Status: <span style='font-weight:700;'>{status_text}</span></div>
    {extra_html}
  </div>
</div>
"""
        return html
    
    # ---- Monthly cache helpers (defined early so they are available during initial render) ----
    def ensure_monthly_cache_table():
        conn = sqlite3.connect('emotion_data.db')
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS emotion_monthly_daily_avg (
                month TEXT NOT NULL,           -- YYYY-MM
                day   TEXT NOT NULL,           -- YYYY-MM-DD
                avg_battery REAL,              -- average battery
                created_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (month, day)
            )
            """
        )
        conn.commit()
        conn.close()

    def read_month_cache(month_str: str):
        ensure_monthly_cache_table()
        conn = sqlite3.connect('emotion_data.db')
        df = pd.read_sql_query(
            "SELECT day, avg_battery FROM emotion_monthly_daily_avg WHERE month = ? ORDER BY day",
            conn,
            params=[month_str]
        )
        conn.close()
        if df.empty:
            return None
        # Map missing (NaN) to fixed default 80.0
        rows = [[row['day'], 80.0 if pd.isna(row['avg_battery']) else float(round(row['avg_battery'], 1))] for _, row in df.iterrows()]
        return rows

    def write_month_cache(month_str: str, rows):
        ensure_monthly_cache_table()
        conn = sqlite3.connect('emotion_data.db')
        cur = conn.cursor()
        # Replace cache for this month
        cur.execute("DELETE FROM emotion_monthly_daily_avg WHERE month = ?", (month_str,))
        # Insert rows
        data = [(month_str, r[0], None if r[1] is None else float(r[1])) for r in rows]
        cur.executemany(
            "INSERT INTO emotion_monthly_daily_avg (month, day, avg_battery) VALUES (?, ?, ?)",
            data
        )
        conn.commit()
        conn.close()

    def clear_month_cache(month_str: str):
        ensure_monthly_cache_table()
        conn = sqlite3.connect('emotion_data.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM emotion_monthly_daily_avg WHERE month = ?", (month_str,))
        conn.commit()
        conn.close()

    def _rows_to_bar_figure(rows, month_str: str):
        # rows: [ [date_str, avg or None], ... ]
        try:
            x_vals = [r[0] for r in rows]
            y_vals = [None if (len(r) < 2 or r[1] is None) else float(r[1]) for r in rows]
            # Prepare text labels: show value on top of each bar; blank when None
            text_vals = ["" if v is None else f"{v:.1f}" for v in y_vals]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=x_vals,
                y=y_vals,
                marker_color="#44aaff",
                name="Avg Battery",
                text=text_vals,
                textposition="outside"
            ))
            fig.update_layout(
                title=f"Daily Avg Emotion Battery ({month_str})",
                xaxis_title="Date",
                yaxis_title="Avg Emotion Battery",
                yaxis=dict(range=[20, 100]),
                bargap=0.2,
                xaxis=dict(type="category", tickangle=-45),
                height=360
            )
            return fig
        except Exception as e:
            fig = go.Figure()
            fig.add_annotation(text=f"Error: {e}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig

    def create_monthly_avg_figure(month_str: str):
        """Compute each day's average Emotion Battery for the month (YYYY-MM)
        by looping days and averaging per-day 10-minute battery_list results.
        Uses cache when available.
        """
        try:
            # Parse month bounds
            if not month_str:
                month_str = datetime.now().strftime('%Y-%m')

            # Try cache first
            cached = read_month_cache(month_str)
            if cached is not None and len(cached) > 0:
                # Validate cached rows against DB; force 80.0 for days with zero records
                month_dt_tmp = pd.to_datetime(month_str + "-01")
                start_day_tmp = month_dt_tmp.replace(day=1)
                next_month_tmp = (start_day_tmp + pd.offsets.MonthBegin(1))
                end_day_tmp = next_month_tmp - pd.Timedelta(days=1)
                dates_tmp = pd.date_range(start=start_day_tmp, end=end_day_tmp, freq='D')
                # Build quick lookup from cached
                cached_map = {r[0]: r[1] for r in cached}
                changed = False
                conn_v = sqlite3.connect('emotion_data.db')
                cur_v = conn_v.cursor()
                rows_v = []
                for d in dates_tmp:
                    day_disp = d.strftime('%Y-%m-%d')
                    day_key = d.strftime('%Y%m%d')
                    try:
                        cur_v.execute("SELECT COUNT(*) FROM emotion_records WHERE has_face = 1 AND substr(timestamp,1,8) = ?", (day_key,))
                        cnt = cur_v.fetchone()[0]
                    except Exception:
                        cnt = None
                    val = cached_map.get(day_disp)
                    if cnt is None or cnt == 0:
                        if val != 80.0:
                            changed = True
                        rows_v.append([day_disp, 80.0])
                    else:
                        rows_v.append([day_disp, val])
                conn_v.close()
                if changed:
                    write_month_cache(month_str, rows_v)
                    return _rows_to_bar_figure(rows_v, month_str)
                return _rows_to_bar_figure(cached, month_str)

            month_dt = pd.to_datetime(month_str + "-01")
            start_day = month_dt.replace(day=1)
            next_month = (start_day + pd.offsets.MonthBegin(1))
            end_day = next_month - pd.Timedelta(days=1)

            # Loop through days and compute average via analyze_emotion_battery
            dates = pd.date_range(start=start_day, end=end_day, freq='D')
            rows = []
            # Open one connection to count per-day rows quickly
            conn = sqlite3.connect('emotion_data.db')
            cur = conn.cursor()
            for d in dates:
                day_key = d.strftime('%Y%m%d')
                # Count records for this day
                try:
                    cur.execute("SELECT COUNT(*) FROM emotion_records WHERE has_face = 1 AND substr(timestamp,1,8) = ?", (day_key,))
                    cnt = cur.fetchone()[0]
                except Exception:
                    cnt = None
                if cnt is None or cnt == 0:
                    # No data for this day: fixed default 80
                    rows.append([d.strftime('%Y-%m-%d'), 80.0])
                else:
                    x_labels, battery_list, impact_list, _ = analyze_emotion_battery(
                        day_key, show_log=False, plot=False, db_path='emotion_data.db'
                    )
                    if battery_list:
                        avg_battery = float(pd.Series(battery_list).mean())
                        rows.append([d.strftime('%Y-%m-%d'), round(avg_battery, 1)])
                    else:
                        rows.append([d.strftime('%Y-%m-%d'), 80.0])
            conn.close()

            # Write cache and return figure
            write_month_cache(month_str, rows)
            return _rows_to_bar_figure(rows, month_str)
        except Exception as e:
            fig = go.Figure()
            fig.add_annotation(text=f"Error: {e}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig

    # Create plot with default current month figure
    monthly_initial_fig = create_monthly_avg_figure(datetime.now().strftime('%Y-%m'))
    monthly_avg_plot = gr.Plot(value=monthly_initial_fig, label="Monthly Daily Averages (Bar Chart)")

    # Create Gradio interface
    with gr.Blocks(title="Emotion Battery", theme=gr.themes.Soft()) as interface:
        gr.Markdown("# Emotion Battery Analysis")
        
        # Today's Battery Section
        #gr.Markdown("## 📊 Today's Emotion Battery")
        gr.Markdown("This module shows your emotion battery level.")
        
        with gr.Row():
            with gr.Column(scale=1):
                # Battery level display
                gr.Markdown("## Today's Emotion Battery")
                battery_level = get_today_battery_level()
                status_text, status_emoji, status_color = get_battery_status(battery_level)
                
                # Vertical battery on the left, number on the right
                battery_display = gr.HTML(value=render_battery_html(
                    battery_level,
                    status_text,
                    status_color,
                    status_emoji,
                    extra_lines=["8% higher than last week", "9% higher than community average"]
                ), label="Battery")
                
                # Update button
                with gr.Row():
                    with gr.Column(scale=1):
                        update_btn = gr.Button("🔄 Refresh Battery Level", variant="primary")
                    with gr.Column(scale=2):
                        gr.HTML("", visible=True)
            
            # Right side: This Month's Average Emotion Battery (1/3 width)
            with gr.Column(scale=1):
                def get_current_month_average_battery() -> int:
                    """Read current month's daily averages from cache; if missing, compute, then average."""
                    month_key = datetime.now().strftime('%Y-%m')
                    rows = read_month_cache(month_key)
                    if rows is None or len(rows) == 0:
                        # trigger compute to populate cache
                        _ = create_monthly_avg_figure(month_key)
                        rows = read_month_cache(month_key)
                    if not rows:
                        return 80
                    values = [r[1] if r[1] is not None else 80.0 for r in rows]
                    try:
                        avg_val = int(round(float(pd.Series(values).mean())))
                    except Exception:
                        avg_val = 80
                    return max(20, min(100, avg_val))

                month_avg_level = get_current_month_average_battery()
                m_status_text, m_status_emoji, m_status_color = get_battery_status(month_avg_level)
                gr.Markdown("## Month's Average Emotion Battery")
                monthly_battery_display = gr.HTML(
                    value=render_battery_html(
                        month_avg_level,
                        m_status_text,
                        m_status_color,
                        m_status_emoji,
                        extra_lines=["8% higher than last week", "9% higher than community average"]
                    ),
                    label="Monthly Avg Battery"
                )

        with gr.Row():        
            with gr.Column(scale=1):
                # Battery chart
                chart_output = gr.Plot(
                    value=create_today_battery_chart(),
                    label="Today's Emotion Battery Chart"
                )
        
        gr.Markdown("---")
        
        # Monthly per-day average Emotion Battery (above single-day analysis)
        gr.Markdown("## 📆 Monthly Daily Average Emotion Battery")
        with gr.Row():
            with gr.Column(scale=1):
                month_input = gr.Textbox(
                    label="Month (YYYY-MM)",
                    placeholder="e.g., 2025-07",
                    value=datetime.now().strftime('%Y-%m')
                )
                month_calc_btn = gr.Button("📊 Calculate Monthly Averages", variant="primary")
                clear_cache_btn = gr.Button("🗑️ Clear Cache for Month", variant="secondary")
            with gr.Column(scale=2):
                gr.HTML("", visible=True)
        
        # Replace table with plot for monthly daily averages (will be created after function definition with initial value)

        # ---- Monthly cache helpers ----
        # These functions are now defined earlier in the script.

        # Create plot with default current month figure
        monthly_initial_fig = create_monthly_avg_figure(datetime.now().strftime('%Y-%m'))
        monthly_avg_plot = gr.Plot(value=monthly_initial_fig, label="Monthly Daily Averages (Bar Chart)")

        month_calc_btn.click(
            fn=create_monthly_avg_figure,
            inputs=[month_input],
            outputs=monthly_avg_plot
        )

        def on_clear_month_cache(month_str: str):
            if not month_str:
                month_str = datetime.now().strftime('%Y-%m')
            clear_month_cache(month_str)
            # Return an empty placeholder figure
            fig = go.Figure()
            fig.add_annotation(text="Cache cleared. Click Calculate to regenerate.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(height=360)
            return fig

        clear_cache_btn.click(
            fn=on_clear_month_cache,
            inputs=[month_input],
            outputs=monthly_avg_plot
        )

        gr.Markdown("---")

        # Single Day Analysis Section
        gr.Markdown("## 📅 Single Day Emotion Battery Analysis")
        gr.Markdown("Analyze emotion battery for any specific day with detailed 10-minute breakdown.")
        
        with gr.Row():
            with gr.Column(scale=1):
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
                
            with gr.Column(scale=2):
                gr.HTML("", visible=True)
        
        # Single day chart output
        single_day_chart = gr.Plot(
            value=create_single_day_battery_chart(None, False),
            label="Single Day Emotion Battery Analysis"
        )
        
        gr.Markdown("---")
        
        # Event handlers
        def update_battery():
            """Update battery level and chart"""
            new_level = get_today_battery_level()
            st_text, st_emoji, st_color = get_battery_status(new_level)
            new_chart = create_today_battery_chart()
            return render_battery_html(
                new_level,
                st_text,
                st_color,
                st_emoji,
                extra_lines=["8% higher than last week", "9% higher than community average"]
            ), new_chart
        
        def analyze_single_day(date_str, use_fake_db):
            """Analyze single day emotion battery"""
            return create_single_day_battery_chart(date_str, use_fake_db)
        
        update_btn.click(
            fn=update_battery,
            outputs=[battery_display, chart_output]
        )
        
        analyze_btn.click(
            fn=analyze_single_day,
            inputs=[date_input, fake_db_checkbox],
            outputs=single_day_chart
        )
        
        gr.Markdown("---")
        
        # Debug: Per-day aggregation details (counts/ratios/impact)
        gr.Markdown("## 🧪 Debug: Day Aggregation Details")
        with gr.Row():
            with gr.Column(scale=1):
                debug_day_input = gr.Textbox(
                    label="Date (YYYY-MM-DD or YYYYMMDD)",
                    value=datetime.now().strftime('%Y-%m-%d'),
                    placeholder="e.g., 2025-07-17"
                )
                debug_btn = gr.Button("🔎 Show Details", variant="secondary")
            with gr.Column(scale=2):
                gr.HTML("", visible=True)
        debug_table = gr.Dataframe(
            headers=["emotion", "count", "ratio", "weight", "contrib"],
            datatype=["str", "number", "number", "number", "number"],
            label="Per-Emotion Aggregation"
        )
        debug_summary = gr.Markdown()

        def show_day_aggregation_details(date_str: str):
            try:
                # Parse date to yyyymmdd
                if not date_str:
                    return [], "Please input a date"
                if isinstance(date_str, str):
                    if '-' in date_str:
                        dt = pd.to_datetime(date_str)
                    else:
                        dt = pd.to_datetime(date_str, format='%Y%m%d')
                else:
                    dt = pd.to_datetime(date_str)
                day_key = dt.strftime('%Y%m%d')

                # Query records
                conn = sqlite3.connect('emotion_data.db')
                sql = """
                    SELECT emotion FROM emotion_records
                    WHERE substr(timestamp,1,8) = ? AND has_face = 1
                """
                df = pd.read_sql_query(sql, conn, params=[day_key])
                conn.close()

                if df.empty:
                    msg = f"No data for {dt.strftime('%Y-%m-%d')}"
                    print(msg)
                    return [], f"### {msg}"

                # Normalize and aggregate
                df['emotion_norm'] = df['emotion'].astype(str).map(lambda x: EMOTION_LABEL_MAP_ZH2EN.get(x, x))
                counts = df.groupby('emotion_norm').size().reset_index(name='count')
                total = int(counts['count'].sum())
                counts['ratio'] = counts['count'] / total
                counts['weight'] = counts['emotion_norm'].map(lambda e: EMOTION_WEIGHT.get(e, 0))
                counts['contrib'] = counts['ratio'] * counts['weight']
                impact_avg = float(counts['contrib'].sum())

                # Compute n_bins and downV from global params
                n_bins = int(((pd.to_datetime(timeE, format='%H:%M') - pd.to_datetime(timeS, format='%H:%M'))
                              / pd.Timedelta(minutes=timeP)))
                n_bins = max(n_bins, 1)
                downV_local = (startV - endV) / n_bins
                delta = impact_avg - downV_local

                # Predict average with clipping as monthly approximation does
                def avg_for_day_local(impact_val: float) -> float:
                    dlt = impact_val - downV_local
                    values = []
                    for i in range(1, n_bins + 1):
                        cur = startV + i * dlt
                        cur = 20 if cur < 20 else (100 if cur > 100 else cur)
                        values.append(cur)
                    return float(pd.Series(values).mean())

                predicted_avg = avg_for_day_local(impact_avg)

                # Prepare table rows
                table_rows = []
                for _, r in counts.sort_values('emotion_norm').iterrows():
                    table_rows.append([
                        str(r['emotion_norm']),
                        int(r['count']),
                        round(float(r['ratio']), 4),
                        float(r['weight']),
                        round(float(r['contrib']), 4)
                    ])

                # Summary markdown
                summary_md = (
                    f"### Aggregation for {dt.strftime('%Y-%m-%d')}\n"
                    f"- Total records: {total}\n"
                    f"- impact_avg: {impact_avg:.4f}\n"
                    f"- n_bins: {n_bins}, downV: {downV_local:.4f}, delta: {delta:.4f}\n"
                    f"- Predicted daily average battery: {predicted_avg:.1f}\n"
                )

                # Also print to console as requested
                print(summary_md)
                print("Per-emotion details:")
                print(counts[['emotion_norm','count','ratio','weight','contrib']])

                return table_rows, summary_md
            except Exception as e:
                err = f"Error: {e}"
                print(err)
                return [], f"### {err}"

        debug_btn.click(
            fn=show_day_aggregation_details,
            inputs=[debug_day_input],
            outputs=[debug_table, debug_summary]
        )
        
    return interface

if __name__ == "__main__":
    print("Starting Emotion Battery Interface...")
    interface = create_emotion_battery_interface()
    print("Interface created successfully!")
    interface.launch()
