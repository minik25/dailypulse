import streamlit as st
import requests
st.set_page_config(page_title="DailyPulse", layout="wide")

st.write("USDA key loaded:", "USDA_API_KEY" in st.secrets)

st.title("DailyPulse")
def usda_search_food(query: str, api_key: str, page_size: int = 10):
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {"api_key": api_key}
    payload = {"query": query, "pageSize": page_size}
    r = requests.post(url, params=params, json=payload, timeout=15)
    r.raise_for_status()
    return r.json().get("foods", [])

def usda_get_food_details(fdc_id: int, api_key: str):
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    params = {"api_key": api_key}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def extract_macros_from_usda(details: dict):
    calories = carbs = 0
    protein = None
    

    for n in details.get("foodNutrients", []):
        nutrient = n.get("nutrient", {}) or {}
        nutrient_id = nutrient.get("id")
        nutrient_name = (nutrient.get("name") or "").lower()
        amount = float(n.get("amount") or 0)

        # Energy
        if nutrient_id == 1008 or "energy" in nutrient_name:
            calories = amount

        # Carbs
        elif nutrient_id == 1005 or "carbohydrate" in nutrient_name:
            carbs = amount

        # Protein (pick smallest non-zero)
        elif nutrient_id == 1003 or "protein" in nutrient_name:
            if amount > 0 and (protein is None or amount < protein):
                protein = amount

        
    return float(calories), float(protein or 0), float(carbs)

tab_dash, tab_tasks, tab_fitness, tab_food = st.tabs(["Dashboard", "Tasks", "Fitness", "Food"])

from datetime import date

with tab_dash:
    st.subheader("🧭 DailyPulse Dashboard")

    dash_date = st.date_input("Dashboard date", value=date.today(), key="dash_date")

    st.markdown("### 🎯 Goals")

    g1, g2, g3, g4, g5 = st.columns(5)

    with g1:
        goal_steps = st.number_input(
            "Goal steps",
            min_value=0,
            step=500,
            value=st.session_state.get("goal_steps", 8000),
            key="goal_steps"
        )

    with g2:
        goal_workout_mins = st.number_input(
            "Goal workout mins",
            min_value=0,
            step=5,
            value=st.session_state.get("goal_workout_mins", 30),
            key="goal_workout_mins"
        )

    with g3:
        goal_calories = st.number_input(
            "Goal calories",
            min_value=0,
            step=50,
            value=st.session_state.get("goal_calories", 1800),
            key="goal_calories"
        )

    with g4:
        goal_protein = st.number_input(
            "Goal protein (g)",
            min_value=0,
            step=5,
            value=st.session_state.get("goal_protein", 120),
            key="goal_protein"
        )

    with g5:
        goal_carbs = st.number_input(
            "Goal carbs (g)",
            min_value=0,
            step=5,
            value=st.session_state.get("goal_carbs", 200),
            key="goal_carbs"
        )

    # ---------- FOOD ----------
    food_rows = st.session_state.get("food_data", [])
    food_today = [r for r in food_rows if r.get("date") == dash_date]

    total_cal = sum(float(r.get("calories", 0) or 0) for r in food_today)
    total_p   = sum(float(r.get("protein", 0) or 0) for r in food_today)
    total_c   = sum(float(r.get("carbs", 0) or 0) for r in food_today)
    
    # ---------- TASKS ----------
    tasks = st.session_state.get("tasks", [])
    tasks_today = [t for t in tasks if t.get("date") == dash_date]
    done_count = sum(1 for t in tasks_today if t.get("done"))
    total_tasks = len(tasks_today)

    # ---------- FITNESS ----------
    fitness_rows = st.session_state.get("fitness_data", [])
    fit_today = [r for r in fitness_rows if r.get("date") == dash_date]

    total_steps = sum(float(r.get("steps", 0) or 0) for r in fit_today)
    total_mins  = sum(float(r.get("minutes", 0) or 0) for r in fit_today)

    current_weight = st.session_state.get("current_weight", None)
    goal_weight = st.session_state.get("goal_weight", None)

    st.markdown("### ✅ Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Tasks done", f"{done_count}/{total_tasks}")

    c2.metric(
        "Steps (actual/goal)",
        f"{total_steps:.0f} / {st.session_state.get('goal_steps', 0):.0f}"
    )

    c3.metric(
        "Workout mins (actual/goal)",
        f"{total_mins:.0f} / {st.session_state.get('goal_workout_mins', 0):.0f}"
    )

    if current_weight is None or goal_weight is None or current_weight == 0 or goal_weight == 0:
        c4.metric("Weight (current/goal)", "—")
    else:
        c4.metric(
            "Weight (current/goal)",
            f"{current_weight:.1f} / {goal_weight:.1f}"
        )

    st.markdown("### 🍽️ Food Macros")

    f1, f2, f3 = st.columns(3)

    f1.metric(
        "Calories (actual/goal)",
        f"{total_cal:.0f} / {st.session_state.get('goal_calories', 0):.0f}"
    )

    f2.metric(
        "Protein g (actual/goal)",
        f"{total_p:.1f} / {st.session_state.get('goal_protein', 0):.0f}"
    )

    f3.metric(
        "Carbs g (actual/goal)",
        f"{total_c:.1f} / {st.session_state.get('goal_carbs', 0):.0f}"
    )
    
with tab_tasks:
    st.subheader("Tasks")

    # Initialize storage
    if "tasks" not in st.session_state:
        st.session_state.tasks = []

    # ------------------------
    # Add Task Form
    # ------------------------
    with st.form("add_task", clear_on_submit=True):
        title = st.text_input("Task title")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        task_date = st.date_input("Task date", value=date.today())
        submitted = st.form_submit_button("Add Task")

    if submitted and title.strip():
        st.session_state.tasks.append({
            "title": title.strip(),
            "priority": priority,
            "done": False,
            "date": task_date
        })

    # ------------------------
    # View Date Selector
    # ------------------------
    view_date = st.date_input("View date", value=date.today(), key="view_date")
    

    # Filter tasks by selected date
    tasks_for_day = [
        t for t in st.session_state.tasks
        if t.get("date") == view_date
    ]
    

    # ------------------------
    # Stats
    # ------------------------
    total_tasks = len(tasks_for_day)
    completed_tasks = len([t for t in tasks_for_day if t["done"]])
    remaining_tasks = total_tasks - completed_tasks

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", total_tasks)
    col2.metric("Completed", completed_tasks)
    col3.metric("Remaining", remaining_tasks)

    st.divider()

    show_completed = st.toggle("Show completed tasks", value=True)

    # ------------------------
    # Sort by Priority
    # ------------------------
    priority_order = {"High": 1, "Medium": 2, "Low": 3}

    sorted_tasks = sorted(
        tasks_for_day,
        key=lambda x: priority_order[x["priority"]]
    )

    # ------------------------
    # Display Tasks
    # ------------------------
    if len(sorted_tasks) == 0:
        st.info("No tasks for this date.")
    else:
        for i, task in enumerate(sorted_tasks):

            if not show_completed and task["done"]:
                continue

            col1, col2 = st.columns([0.15, 0.85])

            with col1:
                task["done"] = st.checkbox(
                    "Done",
                    value=task["done"],
                    key=f"{task['title']}_{task['date']}_{i}"
                )

            with col2:
                if task["done"]:
                    st.write(f"~~{task['title']}~~  ·  Priority: `{task['priority']}`")
                else:
                    st.write(f"**{task['title']}**  ·  Priority: `{task['priority']}`")

with tab_fitness:
    st.subheader("🏋️ Fitness Tracker")

    # -----------------------------
    # Initialize session state
    # -----------------------------
    if "fitness_data" not in st.session_state:
        st.session_state.fitness_data = []

    st.subheader("Weight")

    w1, w2 = st.columns(2)

    with w1:
        current_weight = st.number_input(
            "Current weight",
            min_value=0.0,
            step=0.1,
            format="%.1f",
            key="current_weight"
        )

    with w2:
        goal_weight = st.number_input(
            "Goal weight",
            min_value=0.0,
            step=0.1,
            format="%.1f",
            key="goal_weight"
        )

    # -----------------------------
    # Input Form
    # -----------------------------
    with st.form("fitness_form"):
        col1, col2 = st.columns(2)

        with col1:
            workout_date = st.date_input("Date")
            workout_type = st.selectbox(
                "Workout Type",
                ["Walk", "Run", "Gym", "Yoga", "Sports", "Other"]
            )

        with col2:
            duration = st.number_input("Duration (minutes)", min_value=0, step=5)
            steps = st.number_input("Steps", min_value=0, step=100)

        notes = st.text_input("Notes (optional)")

        submitted = st.form_submit_button("Add Workout")

        if submitted:
            st.session_state.fitness_data.append({
                "date": workout_date,
                "type": workout_type,
                "duration": duration,
                "steps": steps,
                "notes": notes
            })
            st.success("Workout logged successfully 💪")

    st.divider()

    # -----------------------------
    # View by Date
    # -----------------------------
    selected_date = st.date_input("View workouts for date", key="fit_view_date")

    filtered = [
        w for w in st.session_state.fitness_data
        if w["date"] == selected_date
    ]

        # -----------------------------
    # DAILY VIEW
    # -----------------------------
    if filtered:
        total_minutes = sum(w["duration"] for w in filtered)
        total_steps = sum(w["steps"] for w in filtered)

        st.markdown("### 📊 Daily Summary")
        col1, col2 = st.columns(2)
        col1.metric("Total Minutes", total_minutes)
        col2.metric("Total Steps", total_steps)

        st.markdown("### 🎯 Step Goal Progress")
        step_goal = st.number_input(
            "Daily Step Goal",
            min_value=1000,
            step=500,
            value=8000,
            key="fit_step_goal"
        )

        progress = min(total_steps / step_goal, 1.0) if step_goal else 0.0
        st.progress(progress)
        st.caption(f"{total_steps:,} / {step_goal:,} steps ({progress*100:.0f}%)")

        st.markdown("### 📝 Workouts")
        for w in filtered:
            st.write(f"**{w['type']}** | {w['duration']} mins | {w['steps']} steps")
            if w["notes"]:
                st.caption(w["notes"])
    else:
        st.info("No workouts logged for this date yet.")

    # -----------------------------
    # WEEKLY VIEW
    # -----------------------------
    st.divider()
    st.markdown("## 📈 Weekly Overview")

    from datetime import timedelta
    import pandas as pd

    today = selected_date
    week_ago = today - timedelta(days=6)

    week_data = [
        w for w in st.session_state.fitness_data
        if week_ago <= w["date"] <= today
    ]

    if week_data:
        df = pd.DataFrame(week_data)
        df_summary = df.groupby("date").sum(numeric_only=True).reset_index()

        total_week_minutes = df["duration"].sum()
        total_week_steps = df["steps"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Total Minutes (7 days)", total_week_minutes)
        col2.metric("Total Steps (7 days)", total_week_steps)

        st.line_chart(df_summary.set_index("date")[["duration", "steps"]])
    else:
        st.info("No fitness data for the past 7 days.")

with tab_food:
    st.subheader("🍽️ Food Log")

    # -----------------------------
    # Initialize session state
    # -----------------------------
    if "food_data" not in st.session_state:
        st.session_state.food_data = []

    # -----------------------------
    # Add Food Entry
    # -----------------------------
        # -----------------------------
    # USDA Search (OUTSIDE the form so it updates instantly)
    # -----------------------------
    USDA_API_KEY = st.secrets["USDA_API_KEY"]

    if "usda_last_fdc_id" not in st.session_state:
        st.session_state.usda_last_fdc_id = None

    st.markdown("### 🔎 Search & Autofill (USDA)")
    search_query = st.text_input(
        "Search food (e.g., banana, cooked rice, oatmeal)",
        key="usda_query"
    )

    foods = []
    if search_query.strip():
        try:
            foods = usda_search_food(search_query.strip(), USDA_API_KEY, page_size=10)
        except Exception as e:
            st.error(f"Search failed: {e}")

    selected_fdc_id = None
    if foods:
        options = [
            (
                f["fdcId"],
                f"{f.get('description','')}" + (f" — {f.get('brandOwner')}" if f.get("brandOwner") else "")
            )
            for f in foods
        ]

        chosen = st.selectbox(
            "Pick a result to autofill macros",
            options,
            format_func=lambda x: x[1],
            key="usda_pick"
        )
        selected_fdc_id = chosen[0]

    # If selection changed, fetch macros and push into session_state
    if selected_fdc_id and selected_fdc_id != st.session_state.usda_last_fdc_id:
        try:
            details = usda_get_food_details(selected_fdc_id, USDA_API_KEY)
            cal, p, c = extract_macros_from_usda(details)
            print("AUTOFILL VALUES:", cal, p, c)

            # Write directly into the input widget keys
            st.session_state.food_calories = float(cal)
            st.session_state.food_protein  = float(p)
            st.session_state.food_carbs    = float(c)

            # Optional: autofill the food item name too
            st.session_state.food_item = details.get("description", "")

            st.session_state.usda_last_fdc_id = selected_fdc_id
            st.rerun()

        except Exception as e:
            st.error(f"Could not fetch details: {e}")

    st.caption("Autofill note: USDA values are often per 100g unless serving size is provided.")
    st.divider()

    # -----------------------------
    # Add Food Entry (FORM)
    # -----------------------------
    with st.form("food_form"):
        col1, col2 = st.columns(2)

        with col1:
            food_date = st.date_input("Date", key="food_date")
            meal_type = st.selectbox(
                "Meal Type",
                ["Breakfast", "Lunch", "Dinner", "Snacks", "Other"],
                key="food_meal_type"
            )

        with col2:
            item = st.text_input("Food Item", key="food_item")
            calories = st.number_input(
                "Calories",
                min_value=0.0,
                step=1.0,
                key="food_calories"
            )
         

        col3, col4, col5 = st.columns(3)

        protein = col3.number_input(
            "Protein (g)",
            min_value=0.0,
            step=0.1,
            key="food_protein"
        )

        carbs = col4.number_input(
            "Carbs (g)",
            min_value=0.0,
            step=0.1,
            key="food_carbs"
        )

        
        notes = st.text_input("Notes (optional)", key="food_notes")
        servings = st.number_input(
            "Servings / Quantity",
            min_value=0.1,
            value=1.0,
            step=0.1,
            key="food_servings"
        )
        scaled_calories = calories * servings
        scaled_protein  = protein * servings
        scaled_carbs    = carbs * servings
        
        st.caption(
            f"Scaled for {servings:g} serving(s): "
            f"{scaled_calories:.0f} kcal • "
            f"P {scaled_protein:.2f}g • "
            f"C {scaled_carbs:.2f}g • "
            
        )

        submitted = st.form_submit_button("Add Food Log")

        if submitted:
            if not item.strip():
                st.warning("Please enter a Food Item.")
            else:
                st.session_state.food_data.append({
                    "date": food_date,
                    "meal_type": meal_type,
                    "item": item.strip(),
                    "servings": servings,
                    "calories": calories * servings,
                    "protein": protein * servings,
                    "carbs": carbs * servings,
                    "notes": notes
                })
                st.success("Food logged ✅")

    st.divider()

    # -----------------------------
    # View by Date
    # -----------------------------
    selected_food_date = st.date_input("View food for date", key="food_view_date")
    filtered_food = [f for f in st.session_state.food_data if f["date"] == selected_food_date]

    if filtered_food:
        total_cal = sum(f["calories"] for f in filtered_food)
        total_p = sum(f["protein"] for f in filtered_food)
        total_c = sum(f["carbs"] for f in filtered_food)
        

        st.markdown("### 📊 Daily Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Calories", f"{total_cal:.1f}")
        c2.metric("Protein (g)", f"{total_p:.2f}")
        c3.metric("Carbs (g)", f"{total_c:.1f}")

    st.markdown("### 🧾 Items")

    meal_order = ["Breakfast", "Lunch", "Dinner", "Snacks", "Other"]

    for mt in meal_order:
        items = [x for x in filtered_food if x["meal_type"] == mt]
        if items:
            st.markdown(f"**{mt}**")

            for x in items:
                st.write(
                    f"- {x.get('item','')}  •  "
                    f"{float(x.get('calories',0) or 0):.0f} cal  •  "
                    f"P{float(x.get('protein',0) or 0):.1f}g  •  "
                    f"C{float(x.get('carbs',0) or 0):.1f}g"
                )

                if x.get("notes"):
                    st.caption(x["notes"])
    else:
        st.info("No food logged for this date yet.")