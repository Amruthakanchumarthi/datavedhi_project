"""
Data Vedhi.Club - Core Team Recruitment Dashboard (Coordinator Edition)
Features: Modern Glassmorphism Login UI, Retractable Sidebar, Top Header Logo, Session Persistence, Audit Trail.

Run with:
    streamlit run app.py
"""

import sqlite3
import re
import urllib.parse
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st

DB_PATH = "recruitment.db"
LOGO_PATH = "logo.png"  # Ensure logo.png is saved in the same directory as app.py
PORTFOLIOS = ["Tech", "Design", "Content", "Events", "Marketing", "Outreach"]
STATUSES = ["Applied", "Shortlisted", "Task Assigned", "Task Submitted", "Selected", "Rejected"]
ACCESS_CODE = "datavedhi2026"

# ---------------------------------------------------------------------------
# DATABASE SETUP & TRANSACTIONS
# ---------------------------------------------------------------------------

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applicants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                portfolio_applied_for TEXT NOT NULL,
                why_join TEXT,
                experience TEXT,
                status TEXT NOT NULL DEFAULT 'Applied',
                applied_on TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant_id INTEGER NOT NULL,
                portfolio TEXT,
                task_description TEXT,
                assigned_on TEXT,
                deadline TEXT,
                submission_link TEXT,
                submission_notes TEXT,
                submitted_on TEXT,
                FOREIGN KEY (applicant_id) REFERENCES applicants (id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                reviewer TEXT NOT NULL,
                review_score INTEGER NOT NULL,
                reviewer_comments TEXT,
                reviewed_on TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS final_selection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                applicant_id INTEGER NOT NULL,
                portfolio TEXT,
                decision TEXT,
                decided_by TEXT,
                decided_on TEXT,
                remarks TEXT,
                FOREIGN KEY (applicant_id) REFERENCES applicants (id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT,
                action TEXT,
                target_type TEXT,
                target_id INTEGER,
                details TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()


def run_query(query, params=(), fetch=True, commit=False):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        result = None
        if fetch:
            result = cur.fetchall()
        if commit:
            conn.commit()
            result = cur.lastrowid
        return result


def log_action(action, target_type, target_id, details=""):
    actor = st.session_state.get("coordinator_name", "Coordinator")
    run_query(
        """INSERT INTO audit_log (actor, action, target_type, target_id, details, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (actor, action, target_type, target_id, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        fetch=False, commit=True
    )


def add_sno(df):
    """Adds a sequential S.No column starting at 1 to DataFrames."""
    if not df.empty:
        df = df.copy()
        df.insert(0, "S.No", range(1, 1 + len(df)))
    return df


def get_applicants_df(status_filter=None, portfolio_filter=None):
    query = "SELECT * FROM applicants WHERE 1=1"
    params = []
    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)
    if portfolio_filter and portfolio_filter != "All":
        query += " AND portfolio_applied_for = ?"
        params.append(portfolio_filter)
    query += " ORDER BY applied_on DESC"
    
    with get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_tasks_df():
    with get_conn() as conn:
        return pd.read_sql_query("""
            SELECT t.*, a.name as applicant_name, a.email,
                   COALESCE(AVG(r.review_score), 0) as avg_score,
                   COUNT(r.id) as review_count
            FROM tasks t
            JOIN applicants a ON t.applicant_id = a.id
            LEFT JOIN task_reviews r ON t.id = r.task_id
            GROUP BY t.id
            ORDER BY t.assigned_on DESC
        """, conn)


def get_audit_log_df():
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC", conn)


def update_applicant_status(applicant_id, new_status, reason=""):
    run_query("UPDATE applicants SET status = ? WHERE id = ?", (new_status, applicant_id), fetch=False, commit=True)
    log_action("Status Change", "applicant", applicant_id, f"New status: {new_status}. {reason}")


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


def generate_mailto(to_email, subject, body):
    encoded_subject = urllib.parse.quote(subject)
    encoded_body = urllib.parse.quote(body)
    return f"mailto:{to_email}?subject={encoded_subject}&body={encoded_body}"


def render_header(title_text):
    """Renders page title with logo neatly aligned in the top-right corner."""
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.title(title_text)
    with col_t2:
        try:
            st.image(LOGO_PATH, width=80)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# INITIALIZATION & GLOBAL CSS
# ---------------------------------------------------------------------------

try:
    st.set_page_config(
        page_title="Data Vedhi.Club - Recruitment Dashboard",
        page_icon=LOGO_PATH,
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception:
    st.set_page_config(
        page_title="Data Vedhi.Club - Recruitment Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )

init_db()

# PERSISTENT SESSION KEYS
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "coordinator_name" not in st.session_state:
    st.session_state["coordinator_name"] = ""
if "nav_selection" not in st.session_state:
    st.session_state["nav_selection"] = "Overview"

# ---------------------------------------------------------------------------
# CONDITION 1: REDESIGNED LOGIN UI (UNAUTHENTICATED)
# ---------------------------------------------------------------------------

if not st.session_state["logged_in"]:
    st.markdown("""
        <style>
        /* Modern Gradient Background */
        .stApp {
            background: radial-gradient(circle at 50% 20%, #1e293b 0%, #0f172a 100%);
        }
        
        /* Hide sidebar on login screen */
        section[data-testid="stSidebar"] {
            display: none !important;
        }

        /* Glassmorphic Login Card */
        div[data-testid="stForm"] {
            background: rgba(30, 41, 59, 0.75);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 2.5rem 2.5rem 2rem 2.5rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }

        /* Input Field Styling */
        div[data-testid="stForm"] input {
            background-color: #0f172a !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
            border-radius: 10px !important;
            padding: 0.65rem 1rem !important;
            font-size: 0.95rem !important;
        }
        div[data-testid="stForm"] input:focus {
            border-color: #ea580c !important;
            box-shadow: 0 0 0 2px rgba(234, 88, 12, 0.2) !important;
        }

        /* Full Width Vibrant Button */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 1rem;
            width: 100%;
            padding: 0.75rem 1rem;
            margin-top: 0.5rem;
            transition: all 0.2s ease-in-out;
            cursor: pointer;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
            box-shadow: 0 6px 20px rgba(234, 88, 12, 0.45);
            transform: translateY(-2px);
        }
        </style>
    """, unsafe_allow_html=True)

    c_left, c_center, c_right = st.columns([1, 1.4, 1])
    with c_center:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            # Header Branding Section
            head_col1, head_col2, head_col3 = st.columns([1, 1.2, 1])
            with head_col2:
                try:
                    st.image(LOGO_PATH, use_container_width=True)
                except Exception:
                    pass
            
            st.markdown("<h2 style='text-align: center; color: #f8fafc; margin-top: 10px; margin-bottom: 0px; font-weight: 700;'>Data Vedhi.Club</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 25px;'>Core Team Recruitment Portal</p>", unsafe_allow_html=True)
            
            name_input = st.text_input("Coordinator Name", placeholder="e.g. Amrutha")
            code_input = st.text_input("Access Code", type="password", placeholder="••••••••••••")
            
            st.markdown("<br>", unsafe_allow_html=True)
            login_btn = st.form_submit_button("Authenticate Portal")
            
            if login_btn:
                if not name_input.strip():
                    st.error("Please enter your coordinator name.")
                elif code_input != ACCESS_CODE:
                    st.error("Incorrect access code.")
                else:
                    st.session_state["logged_in"] = True
                    st.session_state["coordinator_name"] = name_input.strip()
                    log_action("Login", "session", 0, f"User {name_input} logged in.")
                    st.rerun()

# ---------------------------------------------------------------------------
# CONDITION 2: MAIN DASHBOARD (AUTHENTICATED)
# ---------------------------------------------------------------------------

else:
    # COMPACT RETRACTABLE SIDEBAR CSS
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] {
            width: 250px !important;
        }
        div[data-testid="column"]:nth-child(2) img {
            float: right;
            margin-top: 5px;
            filter: drop-shadow(0px 2px 6px rgba(0,0,0,0.4));
        }
        </style>
    """, unsafe_allow_html=True)

    # SIDEBAR NAVIGATION
    st.sidebar.title("Data Vedhi.Club")
    st.sidebar.caption("Recruitment Dashboard")
    st.sidebar.success(f"Logged in: **{st.session_state['coordinator_name']}**")

    if st.sidebar.button("Logout"):
        log_action("Logout", "session", 0, f"User {st.session_state['coordinator_name']} logged out.")
        st.session_state["logged_in"] = False
        st.session_state["coordinator_name"] = ""
        st.session_state["nav_selection"] = "Overview"
        st.rerun()

    nav = st.sidebar.radio(
        "Navigate",
        ["Overview", "Applications", "Shortlisting", "Task Tracking", "Final Selection", "Audit Log"],
        key="nav_selection"
    )

    # -----------------------------------------------------------------------
    # VIEW 1: OVERVIEW
    # -----------------------------------------------------------------------
    if nav == "Overview":
        render_header("Dashboard Overview")

        all_apps = get_applicants_df()
        all_tasks = get_tasks_df()

        total_apps = len(all_apps)
        shortlisted = len(all_apps[all_apps["status"].isin(["Shortlisted", "Task Assigned", "Task Submitted", "Selected"])])
        tasks_pending = len(all_tasks[all_tasks["submitted_on"].isna() | (all_tasks["submitted_on"] == "")])
        tasks_submitted = len(all_tasks[all_tasks["submitted_on"].notna() & (all_tasks["submitted_on"] != "")])
        selections_made = len(all_apps[all_apps["status"] == "Selected"])

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Applications", total_apps)
        c2.metric("Shortlisted", shortlisted)
        c3.metric("Tasks Pending", tasks_pending)
        c4.metric("Tasks Submitted", tasks_submitted)
        c5.metric("Final Selections", selections_made)

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Applications per Portfolio")
            if not all_apps.empty:
                port_df = all_apps["portfolio_applied_for"].value_counts().reset_index()
                port_df.columns = ["portfolio_applied_for", "count"]
                st.dataframe(add_sno(port_df), use_container_width=True, hide_index=True)
                st.bar_chart(all_apps["portfolio_applied_for"].value_counts())
            else:
                st.info("No applications recorded yet.")

        with col2:
            st.subheader("Pipeline Status Breakdown")
            if not all_apps.empty:
                stat_df = all_apps["status"].value_counts().reset_index()
                stat_df.columns = ["status", "count"]
                st.dataframe(add_sno(stat_df), use_container_width=True, hide_index=True)
                st.bar_chart(all_apps["status"].value_counts())
            else:
                st.info("No applications recorded yet.")

    # -----------------------------------------------------------------------
    # VIEW 2: APPLICATIONS
    # -----------------------------------------------------------------------
    elif nav == "Applications":
        render_header("Applications Management")

        with st.expander("Add New Applicant"):
            with st.form("add_applicant_form", clear_on_submit=True):
                fc1, fc2 = st.columns(2)
                name = fc1.text_input("Full Name *")
                email = fc2.text_input("Email *")
                fc3, fc4 = st.columns(2)
                phone = fc3.text_input("Phone")
                portfolio = fc4.selectbox("Portfolio Applied For *", PORTFOLIOS)
                why_join = st.text_area("Why do you want to join?")
                experience = st.text_area("Relevant Experience")
                submitted = st.form_submit_button("Add Applicant")

                if submitted:
                    clean_email = email.strip().lower()
                    if not name or not clean_email:
                        st.error("Name and Email are required.")
                    elif not is_valid_email(clean_email):
                        st.error("Please enter a valid email address.")
                    else:
                        try:
                            new_id = run_query(
                                """INSERT INTO applicants
                                   (name, email, phone, portfolio_applied_for, why_join, experience, status, applied_on)
                                   VALUES (?, ?, ?, ?, ?, ?, 'Applied', ?)""",
                                (name.strip(), clean_email, phone.strip(), portfolio, why_join, experience,
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                fetch=False, commit=True
                            )
                            log_action("Create", "applicant", new_id, f"Added applicant {name}")
                            st.toast(f"Applicant '{name}' added successfully!", icon="✅")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("An applicant with this email address already exists.")

        with st.expander("Bulk Import via CSV"):
            st.caption("CSV required columns: `name`, `email`, `portfolio_applied_for`. Optional: `phone`, `why_join`, `experience`.")
            csv_file = st.file_uploader("Upload CSV", type=["csv"])
            if csv_file is not None:
                try:
                    import_df = pd.read_csv(csv_file)
                    required_cols = {"name", "email", "portfolio_applied_for"}
                    if not required_cols.issubset(set(import_df.columns)):
                        st.error(f"CSV missing mandatory columns: {required_cols - set(import_df.columns)}")
                    else:
                        if st.button("Confirm Import"):
                            count = 0
                            duplicates = 0
                            with get_conn() as conn:
                                cur = conn.cursor()
                                for _, row in import_df.iterrows():
                                    try:
                                        clean_email = str(row.get("email")).strip().lower()
                                        cur.execute(
                                            """INSERT INTO applicants
                                               (name, email, phone, portfolio_applied_for, why_join, experience, status, applied_on)
                                               VALUES (?, ?, ?, ?, ?, ?, 'Applied', ?)""",
                                            (str(row.get("name")).strip(), clean_email, str(row.get("phone", "")).strip(),
                                             str(row.get("portfolio_applied_for")).strip(), str(row.get("why_join", "")),
                                             str(row.get("experience", "")), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                                        )
                                        count += 1
                                    except sqlite3.IntegrityError:
                                        duplicates += 1
                                conn.commit()
                            log_action("Bulk Import", "applicant", 0, f"Imported {count} applicants ({duplicates} duplicates skipped)")
                            st.toast(f"Imported {count} applicants successfully!", icon="🚀")
                            st.rerun()
                except Exception as e:
                    st.error(f"Failed to parse CSV file: {e}")

        st.divider()
        st.subheader("All Applicants")

        fc1, fc2, fc3 = st.columns(3)
        status_filter = fc1.selectbox("Filter by Status", ["All"] + STATUSES)
        portfolio_filter = fc2.selectbox("Filter by Portfolio", ["All"] + PORTFOLIOS)
        search_term = fc3.text_input("Search Name / Email")

        df = get_applicants_df(status_filter, portfolio_filter)
        if search_term:
            mask = (df["name"].str.contains(search_term, case=False, na=False) |
                    df["email"].str.contains(search_term, case=False, na=False))
            df = df[mask]

        st.dataframe(add_sno(df), use_container_width=True, hide_index=True)

        st.subheader("Edit or Delete Applicant")
        if not df.empty:
            edit_options = {f"{row['name']} ({row['email']})": row["id"] for _, row in df.iterrows()}
            edit_choice = st.selectbox("Select Applicant to Edit/Delete", list(edit_options.keys()))
            edit_id = edit_options[edit_choice]
            current = df[df["id"] == edit_id].iloc[0]

            with st.form("edit_applicant_form"):
                e_name = st.text_input("Name", value=current["name"])
                e_email = st.text_input("Email", value=current["email"])
                e_phone = st.text_input("Phone", value=current["phone"] or "")
                e_portfolio = st.selectbox("Portfolio", PORTFOLIOS,
                                            index=PORTFOLIOS.index(current["portfolio_applied_for"])
                                            if current["portfolio_applied_for"] in PORTFOLIOS else 0)
                e_why = st.text_area("Why join?", value=current["why_join"] or "")
                e_exp = st.text_area("Experience", value=current["experience"] or "")
                
                colA, colB = st.columns(2)
                save_btn = colA.form_submit_button("Save Changes")
                delete_confirm = colB.checkbox("Confirm Deletion")
                delete_btn = colB.form_submit_button("Delete Record")

                if save_btn:
                    clean_email = e_email.strip().lower()
                    if not is_valid_email(clean_email):
                        st.error("Invalid email address format.")
                    else:
                        try:
                            run_query(
                                """UPDATE applicants SET name=?, email=?, phone=?, portfolio_applied_for=?,
                                   why_join=?, experience=? WHERE id=?""",
                                (e_name.strip(), clean_email, e_phone.strip(), e_portfolio, e_why, e_exp, edit_id),
                                fetch=False, commit=True
                            )
                            log_action("Edit", "applicant", edit_id, f"Updated details for {e_name}")
                            st.toast("Applicant details updated!", icon="✏️")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Email update failed: Address is assigned to another candidate.")

                if delete_btn:
                    if not delete_confirm:
                        st.error("Check the confirmation box prior to deletion.")
                    else:
                        run_query("DELETE FROM applicants WHERE id=?", (edit_id,), fetch=False, commit=True)
                        log_action("Delete", "applicant", edit_id, f"Deleted applicant {current['name']}")
                        st.toast("Applicant record deleted.", icon="🗑️")
                        st.rerun()

        st.divider()
        st.subheader("Shortlist Candidate")
        applied_only = df[df["status"] == "Applied"]
        if not applied_only.empty:
            options = {f"{row['name']} ({row['email']}) - {row['portfolio_applied_for']}": row
                       for _, row in applied_only.iterrows()}
            choice_label = st.selectbox("Select Applicant to Shortlist", list(options.keys()))
            chosen_row = options[choice_label]
            
            c_short, c_mail = st.columns([1, 2])
            if c_short.button("Shortlist Selected Applicant"):
                update_applicant_status(chosen_row["id"], "Shortlisted")
                st.toast(f"{chosen_row['name']} shortlisted!", icon="⭐")
                st.rerun()
                
            mail_link = generate_mailto(
                chosen_row["email"],
                "Update on your application - Data Vedhi.Club",
                f"Hi {chosen_row['name']},\n\nWe are pleased to inform you that your application for the {chosen_row['portfolio_applied_for']} team has been shortlisted.\n\nBest,\nData Vedhi Core Team"
            )
            c_mail.markdown(f"[Send Shortlist Email Notification]({mail_link})")
        else:
            st.info("No candidates with status 'Applied' currently pending review.")

    # -----------------------------------------------------------------------
    # VIEW 3: SHORTLISTING
    # -----------------------------------------------------------------------
    elif nav == "Shortlisting":
        render_header("Shortlisting & Task Allocation")

        portfolio_filter = st.selectbox("Filter by Portfolio", ["All"] + PORTFOLIOS)

        query = """SELECT * FROM applicants
                   WHERE status IN ('Shortlisted', 'Task Assigned', 'Task Submitted', 'Selected', 'Rejected')"""
        params = []
        if portfolio_filter != "All":
            query += " AND portfolio_applied_for = ?"
            params.append(portfolio_filter)
            
        with get_conn() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        st.dataframe(add_sno(df), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Assign Portfolio Task")

        shortlisted_only = df[df["status"] == "Shortlisted"]
        if not shortlisted_only.empty:
            options = {f"{row['name']} ({row['email']}) - {row['portfolio_applied_for']}": row
                       for _, row in shortlisted_only.iterrows()}
            chosen_labels = st.multiselect("Select Candidate(s)", list(options.keys()))

            with st.form("assign_task_form"):
                task_description = st.text_area("Task Description *")
                deadline = st.date_input("Deadline", value=date.today() + timedelta(days=3))
                assign_submitted = st.form_submit_button("Assign Task")

                if assign_submitted:
                    if not chosen_labels:
                        st.error("Select at least one candidate.")
                    elif not task_description.strip():
                        st.error("Task description is required.")
                    else:
                        with get_conn() as conn:
                            cur = conn.cursor()
                            for label in chosen_labels:
                                cand = options[label]
                                cur.execute(
                                    """INSERT INTO tasks
                                       (applicant_id, portfolio, task_description, assigned_on, deadline)
                                       VALUES (?, ?, ?, ?, ?)""",
                                    (int(cand["id"]), cand["portfolio_applied_for"], task_description,
                                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(deadline))
                                )
                                cur.execute("UPDATE applicants SET status = 'Task Assigned' WHERE id = ?", (int(cand["id"]),))
                            conn.commit()
                        log_action("Assign Task", "applicant", 0, f"Task assigned to {len(chosen_labels)} candidate(s)")
                        st.toast("Task assigned successfully!", icon="📋")
                        st.rerun()

            if chosen_labels:
                st.subheader("Email Notifications for Assigned Candidates")
                for label in chosen_labels:
                    cand = options[label]
                    m_link = generate_mailto(
                        cand["email"],
                        "Task Assignment - Data Vedhi.Club Core Team",
                        f"Hi {cand['name']},\n\nYour task for the {cand['portfolio_applied_for']} team has been assigned.\nDeadline: {deadline}\n\nTask Details:\n{task_description}\n\nBest,\nData Vedhi Core Team"
                    )
                    st.markdown(f"* [Email Task Details to {cand['name']}]({m_link})")
        else:
            st.info("No candidates currently awaiting task assignment.")

        st.divider()
        st.subheader("Reject Candidate")
        active_only = df[df["status"].isin(["Shortlisted", "Task Assigned"])]
        if not active_only.empty:
            options2 = {f"{row['name']} ({row['email']})": row for _, row in active_only.iterrows()}
            reject_label = st.selectbox("Select Candidate to Reject", list(options2.keys()))
            reject_cand = options2[reject_label]
            reject_reason = st.text_input("Reason for rejection")
            
            c_rej, c_mail = st.columns([1, 2])
            if c_rej.button("Confirm Rejection"):
                update_applicant_status(reject_cand["id"], "Rejected", reason=reject_reason)
                st.toast(f"Candidate {reject_cand['name']} rejected.", icon="❌")
                st.rerun()
                
            m_link = generate_mailto(
                reject_cand["email"],
                "Application Update - Data Vedhi.Club",
                f"Hi {reject_cand['name']},\n\nThank you for applying for the {reject_cand['portfolio_applied_for']} team. Unfortunately, we will not be moving forward with your application at this time.\n\nBest of luck,\nData Vedhi Core Team"
            )
            c_mail.markdown(f"[Send Rejection Email to {reject_cand['name']}]({m_link})")
        else:
            st.info("No active candidates available to reject.")

    # -----------------------------------------------------------------------
    # VIEW 4: TASK TRACKING
    # -----------------------------------------------------------------------
    elif nav == "Task Tracking":
        render_header("Task Tracking & Evaluations")

        tasks_df = get_tasks_df()

        fc1, fc2 = st.columns(2)
        portfolio_filter = fc1.selectbox("Filter by Portfolio", ["All"] + PORTFOLIOS)
        sub_status_filter = fc2.selectbox("Filter by Submission Status", ["All", "Pending", "Submitted", "Reviewed"])

        display_df = tasks_df.copy()
        if portfolio_filter != "All":
            display_df = display_df[display_df["portfolio"] == portfolio_filter]
        
        if sub_status_filter == "Pending":
            display_df = display_df[(display_df["submitted_on"].isna()) | (display_df["submitted_on"] == "")]
        elif sub_status_filter == "Submitted":
            display_df = display_df[(display_df["submitted_on"].notna()) & (display_df["submitted_on"] != "") & (display_df["review_count"] == 0)]
        elif sub_status_filter == "Reviewed":
            display_df = display_df[display_df["review_count"] > 0]

        today_curr = date.today()
        
        def check_deadline_status(row):
            if row["submitted_on"]:
                return "Submitted"
            try:
                d_date = date.fromisoformat(row["deadline"])
                if d_date < today_curr:
                    return "OVERDUE"
                elif d_date == today_curr or d_date == today_curr + timedelta(days=1):
                    return "DUE SOON"
                return "On Track"
            except Exception:
                return "Unknown"

        if not display_df.empty:
            display_df["deadline_status"] = display_df.apply(check_deadline_status, axis=1)

        st.dataframe(add_sno(display_df), use_container_width=True, hide_index=True)

        if not display_df.empty:
            overdue_cnt = (display_df["deadline_status"] == "OVERDUE").sum()
            due_soon_cnt = (display_df["deadline_status"] == "DUE SOON").sum()
            
            if overdue_cnt > 0:
                st.error(f"Attention: {overdue_cnt} task(s) are overdue.")
            if due_soon_cnt > 0:
                st.warning(f"Reminder: {due_soon_cnt} task(s) are due within 24 hours.")

        st.divider()
        st.subheader("Log Task Submission")
        pending_tasks = tasks_df[(tasks_df["submitted_on"].isna()) | (tasks_df["submitted_on"] == "")]
        if not pending_tasks.empty:
            options = {f"{row['applicant_name']} - {row['portfolio']} (Task #{row['id']})": row
                       for _, row in pending_tasks.iterrows()}
            chosen_task_label = st.selectbox("Select Task", list(options.keys()))
            task_row = options[chosen_task_label]
            
            with st.form("submit_task_form"):
                link = st.text_input("Submission Link *")
                notes = st.text_area("Submission Notes")
                submit_task = st.form_submit_button("Mark as Submitted")
                
                if submit_task:
                    if not link.strip():
                        st.error("Submission link is required.")
                    else:
                        run_query(
                            """UPDATE tasks SET submission_link = ?, submission_notes = ?, submitted_on = ?
                               WHERE id = ?""",
                            (link.strip(), notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(task_row["id"])),
                            fetch=False, commit=True
                        )
                        update_applicant_status(int(task_row["applicant_id"]), "Task Submitted")
                        log_action("Submit Task", "task", int(task_row["id"]), f"Submission logged for task #{task_row['id']}")
                        st.toast("Task marked as submitted!", icon="📌")
                        st.rerun()
        else:
            st.info("No pending tasks awaiting submission.")

        st.divider()
        st.subheader("Review Submission")
        submitted_tasks = tasks_df[(tasks_df["submitted_on"].notna()) & (tasks_df["submitted_on"] != "")]
        if not submitted_tasks.empty:
            options3 = {f"{row['applicant_name']} - {row['portfolio']} (Task #{row['id']}) [Avg Score: {row['avg_score']:.1f}, Reviews: {row['review_count']}]": row
                        for _, row in submitted_tasks.iterrows()}
            chosen_review_label = st.selectbox("Select Submission to Review", list(options3.keys()))
            review_task_row = options3[chosen_review_label]
            
            with get_conn() as conn:
                existing_reviews_df = pd.read_sql_query(
                    "SELECT reviewer, review_score, reviewer_comments, reviewed_on FROM task_reviews WHERE task_id = ? ORDER BY reviewed_on DESC",
                    conn, params=(int(review_task_row["id"]),)
                )
                
            if not existing_reviews_df.empty:
                st.caption("Existing Coordinator Reviews:")
                st.dataframe(add_sno(existing_reviews_df), use_container_width=True, hide_index=True)

            with st.form("review_task_form"):
                score = st.slider("Review Score (1-10)", 1, 10, 5)
                comments = st.text_area("Reviewer Comments")
                review_submit = st.form_submit_button("Submit Review")
                
                if review_submit:
                    run_query(
                        """INSERT INTO task_reviews (task_id, reviewer, review_score, reviewer_comments, reviewed_on)
                           VALUES (?, ?, ?, ?, ?)""",
                        (int(review_task_row["id"]), st.session_state["coordinator_name"], score, comments,
                         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        fetch=False, commit=True
                    )
                    log_action("Review Task", "task", int(review_task_row["id"]), f"Score: {score} logged by {st.session_state['coordinator_name']}")
                    st.toast("Review saved successfully!", icon="📝")
                    st.rerun()
        else:
            st.info("No submissions available for review.")

    # -----------------------------------------------------------------------
    # VIEW 5: FINAL SELECTION
    # -----------------------------------------------------------------------
    elif nav == "Final Selection":
        render_header("Final Selection")

        with get_conn() as conn:
            candidates_df = pd.read_sql_query("""
                SELECT a.id as applicant_id, a.name, a.email, a.portfolio_applied_for,
                       AVG(r.review_score) as avg_score, COUNT(r.id) as review_count
                FROM applicants a
                JOIN tasks t ON a.id = t.applicant_id
                JOIN task_reviews r ON t.id = r.task_id
                WHERE a.status = 'Task Submitted'
                GROUP BY a.id
                ORDER BY a.portfolio_applied_for, avg_score DESC
            """, conn)

        if candidates_df.empty:
            st.info("No evaluated candidates ready for final selection.")
        else:
            for portfolio in candidates_df["portfolio_applied_for"].unique():
                st.subheader(f"Portfolio: {portfolio}")
                sub_df = candidates_df[candidates_df["portfolio_applied_for"] == portfolio]
                st.dataframe(
                    add_sno(sub_df[["name", "email", "avg_score", "review_count"]]),
                    use_container_width=True, hide_index=True
                )

                options = {f"{row['name']} ({row['email']}) - Avg Score: {row['avg_score']:.1f} ({row['review_count']} reviews)": row
                           for _, row in sub_df.iterrows()}
                chosen_key = st.selectbox(f"Select Core Team Member - {portfolio}", list(options.keys()), key=f"select_{portfolio}")
                chosen_cand = options[chosen_key]
                
                remarks = st.text_input("Remarks", key=f"remarks_{portfolio}")
                confirm = st.checkbox(f"I confirm this final selection for {portfolio}", key=f"confirm_{portfolio}")
                
                if st.button(f"Finalize Selection for {portfolio}", key=f"finalize_{portfolio}"):
                    if not confirm:
                        st.error("Please confirm before finalizing.")
                    else:
                        selected_id = int(chosen_cand["applicant_id"])
                        decided_by = st.session_state["coordinator_name"]
                        
                        with get_conn() as conn:
                            cur = conn.cursor()
                            cur.execute(
                                """INSERT INTO final_selection
                                   (applicant_id, portfolio, decision, decided_by, decided_on, remarks)
                                   VALUES (?, ?, 'Selected', ?, ?, ?)""",
                                (selected_id, portfolio, decided_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), remarks)
                            )
                            cur.execute("UPDATE applicants SET status = 'Selected' WHERE id = ?", (selected_id,))
                            
                            other_ids = [int(i) for i in sub_df["applicant_id"].tolist() if int(i) != selected_id]
                            for oid in other_ids:
                                cur.execute("UPDATE applicants SET status = 'Rejected' WHERE id = ?", (oid,))
                            conn.commit()
                            
                        log_action("Final Selection", "applicant", selected_id, f"Selected for {portfolio} by {decided_by}")
                        st.toast(f"Final Selection confirmed for {portfolio}!", icon="🎉")
                        st.rerun()
                st.divider()

        st.subheader("Selected Core Team Summary")
        with get_conn() as conn:
            summary_df = pd.read_sql_query("""
                SELECT fs.portfolio, a.name, a.email, fs.decided_by, fs.decided_on, fs.remarks
                FROM final_selection fs
                JOIN applicants a ON fs.applicant_id = a.id
                WHERE fs.decision = 'Selected'
                ORDER BY fs.portfolio
            """, conn)

        st.dataframe(add_sno(summary_df), use_container_width=True, hide_index=True)

        if not summary_df.empty:
            csv_data = summary_df.to_csv(index=False).encode("utf-8")
            st.download_button("Export Final List CSV", csv_data, "final_core_team.csv", "text/csv")

    # -----------------------------------------------------------------------
    # VIEW 6: AUDIT LOG
    # -----------------------------------------------------------------------
    elif nav == "Audit Log":
        render_header("Audit Log")
        st.caption("Action history of coordinator operations.")

        log_df = get_audit_log_df()

        fc1, fc2 = st.columns(2)
        actor_filter = fc1.selectbox("Filter by Coordinator", ["All"] + sorted(log_df["actor"].unique().tolist())
                                          if not log_df.empty else ["All"])
        action_filter = fc2.selectbox("Filter by Action Type", ["All"] + sorted(log_df["action"].unique().tolist())
                                           if not log_df.empty else ["All"])

        filtered = log_df.copy()
        if actor_filter != "All":
            filtered = filtered[filtered["actor"] == actor_filter]
        if action_filter != "All":
            filtered = filtered[filtered["action"] == action_filter]

        st.dataframe(add_sno(filtered), use_container_width=True, hide_index=True)