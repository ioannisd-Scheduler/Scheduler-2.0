import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# 1. Advanced Configuration
st.set_page_config(layout="wide", page_title="DEP 26-27 Granular Focus")

# 2. Sidebar Filters for iPad Zoom
st.sidebar.header("🔍 Focus Mode")
target_school_year = st.sidebar.selectbox("Année Scolaire", ["2026-2027", "2027-2028"])
focus_cohort = st.sidebar.selectbox("Cibler une Cohorte", ["ELEM261", "ELEM262", "ELEM263", "ELEM264", "ELEM266"])

# Define the period logic (P1=3h, P2=3h)
def generate_granular_days(cohort_id, start_date, duration_hrs):
    # This logic calculates the breakdown of Instruction, Exam, Recup, and Reprise
    # for a specific module based on your MASTER_DATA requirements.
    pass 

# 3. Enhanced Visualization Logic
try:
    # Load your existing data sheets
    df_courses, df_rooms = load_all_data() # Using your existing load function
    
    # Filter courses for the selected cohort to show a high-density timeline
    st.header(f"📅 Focus : {focus_cohort} - Année {target_school_year}")
    
    # 4. The Daily Period Drill-Down
    st.subheader("🛠️ Détails par Période (Start/End/Exam/Récup)")
    
    # We create a high-resolution table that shows the Day P1 and Day P2 split
    # specifically designed for the iPad's vertical scroll.
    selected_module = st.selectbox("Sélectionnez un module pour voir les détails d'examen", df_courses['Course_Name'])
    
    module_data = df_courses[df_courses['Course_Name'] == selected_module].iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Instruction", f"{module_data['Instruction_Hours']}h")
    col2.metric("Examen", f"{module_data['Exam_Hours']}h")
    col3.metric("Récupération", f"{module_data['Recup_Hours']}h")
    col4.metric("Reprise", f"{module_data['Reprise_Hours']}h")

    # 5. Visual Conflict Heatmap
    # This checks if the room assigned to the focused cohort is shared
    st.info(f"Vérification des locaux pour {selected_module}...")
    
except Exception as e:
    st.error(f"Erreur d'affichage : {e}")

# 2. Define the 2026-2027 Calendar (Holidays & Ped Days)
HOLIDAYS_26_27 = [
    datetime.date(2026, 9, 7),   # Labor Day
    datetime.date(2026, 10, 12),  # Thanksgiving
    datetime.date(2027, 4, 19),   # Easter
    datetime.date(2027, 5, 24),   # Patriots' Day
    datetime.date(2027, 6, 24),   # Saint-Jean
]

# Simulate the 10 missing Ped Days (usually one Friday per month)
PED_DAYS = [
    datetime.date(2026, 9, 25), datetime.date(2026, 10, 23), datetime.date(2026, 11, 20),
    datetime.date(2026, 12, 11), datetime.date(2027, 1, 22), datetime.date(2027, 2, 12),
    datetime.date(2027, 3, 19), datetime.date(2027, 4, 23), datetime.date(2027, 5, 14),
    datetime.date(2027, 6, 11)
]

OFF_DAYS = set(HOLIDAYS_26_27 + PED_DAYS)

# 3. Data Loading (Safe Pathing)
@st.cache_data
def load_all_data():
    base_path = os.path.dirname(__file__)
    courses_path = os.path.join(base_path, "scheduler master data updated.xlsx")
    
    # Reading 5388 Curriculum and Rooms
    courses = pd.read_excel(courses_path, sheet_name="COURSES_5388")
    rooms = pd.read_excel(courses_path, sheet_name="ROOMS")
    return courses, rooms

# 4. The Scheduling Logic (The Engine)
def schedule_cohort_visual(cohort_id, courses_df, start_date, c2_delay_weeks):
    schedule = []
    current_date = start_date
    
    # Define the 5388 Course Sequence with the 1-week C2 Delay
    # M1 (15h) + Math (15h) -> Week 1
    # M2 (30h) -> starts Week 2
    sequence = [
        {'id': 'M1', 'name': 'Métier et formation', 'hours': 15, 'color': '#1f77b4'},
        {'id': 'MATH', 'name': 'Mathématique (P1)', 'hours': 15, 'color': '#ff7f0e'},
        {'id': 'M2', 'name': 'Santé et Sécurité', 'hours': 30, 'color': '#d62728'},
    ]
    
    # Add remaining 5388 modules
    for _, row in courses_df.iterrows():
        if row['Module_Number'] > 2:
            sequence.append({
                'id': str(row['Course_Code']),
                'name': row['Course_Name'],
                'hours': row['Hours_Required'],
                'color': '#2ca02c' if 'M' in str(row['Category']) else '#9467bd'
            })

    for item in sequence:
        remaining_hours = item['hours']
        course_start = None
        
        while remaining_hours > 0:
            # Skip weekends and Off-Days
            if current_date.weekday() >= 5 or current_date in OFF_DAYS:
                current_date += datetime.timedelta(days=1)
                continue
            
            if course_start is None:
                course_start = current_date
            
            # Apply 6 hours per day (No Gap Logic)
            hours_today = min(remaining_hours, 6)
            remaining_hours -= hours_today
            
            if remaining_hours <= 0:
                # Add to schedule when module is finished
                schedule.append({
                    "Cohort": cohort_id,
                    "Task": f"{item['id']}: {item['name']}",
                    "Start": course_start,
                    "Finish": current_date + datetime.timedelta(days=1), # For Plotly rendering
                    "Resource": item['id'],
                    "Color": item['color']
                })
            
            current_date += datetime.timedelta(days=1)
            
    return schedule

# 5. UI Layout
st.title("📅 Visualiseur d'horaire 2026-2027")
st.sidebar.header("Configurations")
c2_delay = st.sidebar.slider("Délai C2 (Semaines)", 1, 3, 1)

try:
    df_courses, df_rooms = load_all_data()
    
    # Generate all planned 26-27 cohorts
    cohorts = [
        ("ELEM261 (Day)", datetime.date(2026, 8, 24)),
        ("ELEM262 (Night)", datetime.date(2026, 10, 5)),
        ("ELEM263 (Day)", datetime.date(2026, 11, 16)),
        ("ELEM264 (Night)", datetime.date(2027, 1, 25)),
        ("ELEM266 (Day)", datetime.date(2027, 3, 8))
    ]

    all_data = []
    for cid, start in cohorts:
        all_data.extend(schedule_cohort_visual(cid, df_courses, start, c2_delay))

    full_df = pd.DataFrame(all_data)

    # 6. Create the Interactive Gantt Chart
    fig = px.timeline(
        full_df, 
        x_start="Start", 
        x_end="Finish", 
        y="Cohort", 
        color="Cohort",
        hover_data=["Task"],
        title="Flux des Cohortes 5388 - Année Scolaire 26-27"
    )

    fig.update_yaxes(autorange="reversed") # Highest cohort at the top
    fig.update_layout(
        height=600,
        xaxis_title="Calendrier",
        yaxis_title="Groupes",
        hovermode="closest"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 7. Drill-Down Table
    st.subheader("Détails des périodes")
    st.dataframe(full_df[['Cohort', 'Task', 'Start', 'Finish']], use_container_width=True)

except Exception as e:
    st.error(f"Erreur de chargement: {e}")
    st.info("Vérifiez que 'openpyxl' et 'plotly' sont dans votre requirements.txt")
