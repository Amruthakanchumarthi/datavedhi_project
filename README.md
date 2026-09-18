# Data Vedhi.Club - Core Team Recruitment Dashboard

A Streamlit-based web application built for **Data Vedhi.Club** coordinators to streamline, track, and manage the core team recruitment workflow across multiple portfolios.

---

## Features

- **Authentication & Security:** Coordinator portal access restricted via secure access credentials.
- **Applicant Tracking System (ATS):** Add, update, search, filter, and manage applicant profiles with CRUD operations.
- **Bulk CSV Import:** Quickly import candidate data using CSV uploads with automatic deduplication.
- **Task Management & Scoring:** Assign portfolio-specific tasks, track deadlines, log submissions, and multi-reviewer scoring.
- **Final Selection Pipeline:** Aggregated candidate performance views for decision-making and final core team list exports.
- **Automated Mailto Links:** One-click pre-formatted email notifications for shortlisting, task details, and updates.
- **Audit Logging:** System logging to track coordinator actions and maintain operational accountability.

---

## Tech Stack

- **Frontend / Framework:** [Streamlit](https://streamlit.io/)
- **Backend / Database:** SQLite 
- **Data Processing:** Pandas
- **Language:** Python 3.x

---

## Coordinator Access Credentials

To log in and access the dashboard:

- **Access Code:** `datavedhi2026`
- **Coordinator Name:** Enter your name (e.g., `Amrutha`)

---

## Repository Structure

```text
├── app.py              # Main Streamlit application code
├── logo.png            # Data Vedhi.Club branding logo
├── requirements.txt    # Python dependency specifications
└── recruitment.db      # SQLite database (auto-generated on first run)
