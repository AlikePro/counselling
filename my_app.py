# college_planner_app.py
import streamlit as st
import json
from datetime import datetime, date
import pandas as pd
from pathlib import Path
import os
import requests
import socket
import io
import streamlit as st
from streamlit_elements import elements, mui, html

st.set_page_config(layout="wide")

# state
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = True

if "sidebar_side" not in st.session_state:
    st.session_state.sidebar_side = "left"  # or "right"


def toggle_sidebar():
    st.session_state.sidebar_open = not st.session_state.sidebar_open


def switch_side():
    st.session_state.sidebar_side = (
        "right" if st.session_state.sidebar_side == "left" else "left"
    )


with elements("ui"):

    # ===== HEADER =====
    mui.AppBar(
        position="fixed",
        sx={
            "height": "64px",
            "justifyContent": "center",
            "background": "rgba(248,250,252,0.95)",
            "backdropFilter": "blur(12px)",
            "boxShadow": "0 2px 12px rgba(15,23,42,0.08)",
            "zIndex": 1300,
        },
    )(
        mui.Toolbar()(
            mui.IconButton(
                mui.Icon("menu"),
                onClick=toggle_sidebar,
                sx={"color": "#0F172A"},
            ),
            mui.Box(
                sx={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                    "margin": "0 auto",
                }
            )(
                html.img(
                    src="https://avatars.mds.yandex.net/i?id=e78477e103c7040b0e7b81a3b99954790e332c98-5895977-images-thumbs&n=13",
                    style={"height": "36px"},
                ),
                mui.Typography(
                    "College Planner",
                    variant="h6",
                    sx={"fontWeight": 600, "color": "#0F172A"},
                ),
            ),
            mui.IconButton(
                mui.Icon("swap_horiz"),
                onClick=switch_side,
                sx={"color": "#0F172A"},
            ),
        )
    )

    # ===== SIDEBAR =====
    mui.Drawer(
        variant="persistent",
        anchor=st.session_state.sidebar_side,
        open=st.session_state.sidebar_open,
        sx={
            "width": 260,
            "& .MuiDrawer-paper": {
                "width": 260,
                "top": "64px",
                "height": "calc(100% - 64px)",
                "background": "#F1F5F9",
                "borderRight": "1px solid #E5E7EB",
            },
        },
    )(
        mui.Box(sx={"padding": "16px"})(
            mui.Typography("Navigation", sx={"fontWeight": 600}),
            mui.List()(
                mui.ListItem(button=True)("Career Test"),
                mui.ListItem(button=True)("Profile"),
                mui.ListItem(button=True)("Universities"),
                mui.ListItem(button=True)("Deadlines"),
            )
        )
    )

    # ===== MAIN CONTENT =====
    mui.Box(
        sx={
            "marginTop": "64px",
            "padding": "24px",
            "marginLeft": "260px" if st.session_state.sidebar_open and st.session_state.sidebar_side == "left" else "0",
            "marginRight": "260px" if st.session_state.sidebar_open and st.session_state.sidebar_side == "right" else "0",
            "transition": "margin 0.3s ease",
        }
    )(
        mui.Typography(
            "Welcome to College Planner",
            variant="h4",
            sx={"fontWeight": 600, "marginBottom": "16px"},
        ),
        mui.Card(
            sx={
                "borderRadius": "18px",
                "boxShadow": "0 10px 30px rgba(15,23,42,0.08)",
                "padding": "20px",
            }
        )(
            mui.Typography(
                "This is clean, comfortable, real UI.",
                sx={"color": "#475569"},
            )
        ),
    )

# ReportLab PDF support (optional)
REPORTLAB_AVAILABLE = True
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
except Exception:
    REPORTLAB_AVAILABLE = False

# ---------------------------------------
# Environment / constants
# ---------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------
# Session state init (do this BEFORE using session_state)
# ---------------------------------------
if "holland_scores" not in st.session_state:
    st.session_state.holland_scores = None

if "holland_code" not in st.session_state:
    st.session_state.holland_code = None

if "career_test_current_block" not in st.session_state:
    st.session_state.career_test_current_block = 0

if "career_test_answers" not in st.session_state:
    st.session_state.career_test_answers = {}

if "profile" not in st.session_state:
    st.session_state.profile = {}

if "tasks" not in st.session_state:
    st.session_state.tasks = []

# Regions for tasks board (default columns)
if "task_regions" not in st.session_state:
    st.session_state.task_regions = ["Canada", "USA", "Europe", "Asia"]

# ID counter for tasks (ensures stable keys)
if "task_id_counter" not in st.session_state:
    st.session_state.task_id_counter = 0

if "uni_favorites" not in st.session_state:
    st.session_state.uni_favorites = []

if "uni_notes" not in st.session_state:
    st.session_state.uni_notes = {}  # keyed by university name

if "deadlines" not in st.session_state:
    st.session_state.deadlines = []  # list of dicts: uni, type, date, note

if "selected_uni" not in st.session_state:
    st.session_state.selected_uni = None

if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

if "use_offline_ai" not in st.session_state:
    st.session_state["use_offline_ai"] = False

if "groq_api_url" not in st.session_state:
    st.session_state["groq_api_url"] = GROQ_API_URL

# Ensure legacy tasks have region and id
for t in st.session_state.tasks:
    if "region" not in t:
        t["region"] = st.session_state.task_regions[0] if st.session_state.task_regions else "Default"
    if "id" not in t:
        st.session_state.task_id_counter += 1
        t["id"] = st.session_state.task_id_counter

# ---------------------------------------
# Global page config & header
# ---------------------------------------
st.set_page_config(
    page_title="Orken+ College Planner",
    layout="wide",
)

# Nicely formatted PDF generator (placed before UI so sidebar can call it)
def generate_export_pdf(export_payload: dict) -> bytes:
    """Generate a nicely formatted PDF (bytes) containing full export payload."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is not installed. Install with 'pip install reportlab'")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = styles["Heading2"]
    small = ParagraphStyle("Small", parent=normal, fontSize=9)

    story = []
    story.append(Paragraph("College Planner — Full Export", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", small))
    story.append(Spacer(1, 12))

    # Profile
    profile = export_payload.get("profile", {})
    story.append(Paragraph("Profile", heading))
    def add_kv(k, v):
        story.append(Paragraph(f"<b>{k}:</b> {v}", normal))
    add_kv("GPA", profile.get("gpa", "—"))
    add_kv("GPA scale", profile.get("gpa_scale", "—"))
    add_kv("Intended major", profile.get("major", "—"))
    add_kv("School", profile.get("school", "—"))

    # Awards / activities as numbered list
    awards = profile.get("awards", [])
    if awards:
        story.append(Paragraph("Honors / Activities:", normal))
        numbered = ListFlowable([
            ListItem(Paragraph(str(item), normal), value=i+1) for i, item in enumerate(awards)
        ], bulletType="1", start="1")
        story.append(numbered)
    else:
        story.append(Paragraph("Honors / Activities: None", normal))
    story.append(Spacer(1, 12))

    # Exams
    exams = profile.get("exams", {})
    story.append(Paragraph("Exams & Scores", heading))
    if exams:
        for i, (ename, edata) in enumerate(exams.items(), 1):
            parts = [f"{ename} — {edata.get('status', 'N/A')}"]
            if edata.get("score"):
                parts.append(f"score: {edata.get('score')}")
            if edata.get("expected"):
                parts.append(f"expected: {edata.get('expected')}")
            if edata.get("date"):
                parts.append(f"date: {edata.get('date')}")
            if edata.get("planned_date"):
                parts.append(f"planned: {edata.get('planned_date')}")
            story.append(Paragraph(f"{i}. " + "; ".join(parts), normal))
    else:
        story.append(Paragraph("No exam data", normal))
    story.append(Spacer(1, 12))

    # Tasks
    story.append(Paragraph("Tasks", heading))
    tasks = export_payload.get("tasks", [])
    if tasks:
        numbered_tasks = ListFlowable([
            ListItem(Paragraph(f"{t.get('title')} — due: {t.get('due')} — done: {t.get('done')}", normal))
            for t in tasks
        ], bulletType="1", start="1")
        story.append(numbered_tasks)
    else:
        story.append(Paragraph("No tasks", normal))
    story.append(Spacer(1, 12))

    # Favorites
    story.append(Paragraph("Favorites", heading))
    favs = export_payload.get("favorites", [])
    if favs:
        for f in favs:
            story.append(Paragraph(f"- {f.get('name')} ({f.get('country_code','')}) — {f.get('url')}", normal))
    else:
        story.append(Paragraph("No favorites", normal))
    story.append(Spacer(1, 12))

    # Deadlines as table
    story.append(Paragraph("Deadlines", heading))
    dls = export_payload.get("deadlines", [])
    if dls:
        table_data = [["University", "Type", "Date", "Note"]]
        for d in dls:
            table_data.append([d.get("uni", ""), d.get("type", ""), d.get("date", ""), d.get("note", "")])
        tbl = Table(table_data, colWidths=[150, 120, 80, 180])
        tbl.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No deadlines", normal))
    story.append(Spacer(1, 12))

    # Notes
    story.append(Paragraph("Notes", heading))
    notes = export_payload.get("notes", {})
    if notes:
        for uni, note in notes.items():
            story.append(Paragraph(f"- {uni}: {note}", normal))
    else:
        story.append(Paragraph("No notes", normal))

    doc.build(story)
    return buf.getvalue()

with st.container():
    left, right = st.columns([1, 5])
    with left:
        st.markdown("## 🎓")
    with right:
        st.markdown(
            """
            # College Planner  
            <span style="font-size:14px;color:gray;">
            Track your profile, exams, universities, deadlines and chat with an AI advisor.
            </span>
            """,
            unsafe_allow_html=True,
        )
st.write("")  # small spacing

# ---------------------------------------
# Sidebar overview
# ---------------------------------------
with st.sidebar:
    st.markdown("### 📌 Overview")

    sidebar_profile = st.session_state.get("profile", {})
    st.metric("GPA", sidebar_profile.get("gpa", "—"))
    st.metric("Intended major", sidebar_profile.get("major", "—"))

    total_tasks = len(st.session_state.get("tasks", []))
    done_tasks = sum(1 for t in st.session_state.get("tasks", []) if t.get("done"))
    st.progress(done_tasks / total_tasks if total_tasks else 0.0)
    st.caption(f"Tasks: {done_tasks}/{total_tasks} done")

    st.markdown("---")
    st.markdown("### ⚙️ Data")

    # Export (PDF only)
    export_payload = {
        "profile": st.session_state.profile,
        "tasks": st.session_state.tasks,
        "favorites": st.session_state.uni_favorites,
        "deadlines": st.session_state.deadlines,
        "notes": st.session_state.uni_notes,
    }
    if REPORTLAB_AVAILABLE:
        try:
            pdf_bytes_side = generate_export_pdf(export_payload)
            st.download_button(
                "⬇️ Export data (PDF)",
                data=pdf_bytes_side,
                file_name="college_planner_export.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error("PDF export failed: " + str(e))
    else:
        st.warning("PDF export unavailable — install 'reportlab' and redeploy to enable PDF export.")

# ---------------------------------------
# Utility functions
# ---------------------------------------
def _try_extract_assistant_text(data):
    """Robust extraction of assistant text from various provider responses."""
    try:
        if isinstance(data, dict):
            choices = data.get("choices")
            if choices and isinstance(choices, list) and len(choices) > 0:
                msg = choices[0].get("message") or choices[0]
                if isinstance(msg, dict):
                    if "content" in msg:
                        return msg["content"]
                    if "text" in msg:
                        return msg["text"]
            if "output" in data:
                return str(data["output"])
            if "text" in data:
                return data["text"]
    except Exception:
        pass
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return str(data)


def _groq_post_with_auth_variants(api_url, key, body, timeout=50):
    """Try multiple auth header variants for GROQ; return (status_code, text, parsed_json_or_None)."""
    variants = [
        {"Authorization": f"Bearer {key}"},
        {"X-API-Key": key},
        {"Cookie": f"session={key}"},
        {"X-API-Key": key, "Cookie": f"session={key}"},
        {"Authorization": f"Bearer {key}", "Cookie": f"session={key}"},
    ]

    last_status = None
    last_text = None
    for hdrs in variants:
        headers = hdrs.copy()
        headers.setdefault("Content-Type", "application/json")
        try:
            r = requests.post(api_url, headers=headers, json=body, timeout=timeout)
        except Exception as e:
            cause = getattr(e, "__cause__", None)
            txt = str(e)
            if isinstance(cause, socket.gaierror) or "getaddrinfo" in txt.lower():
                return None, f"Network/DNS error: {txt}", None
            last_status = None
            last_text = f"Request error: {txt}"
            continue
        last_status = r.status_code
        last_text = r.text or ""
        if r.status_code == 200:
            try:
                return 200, r.text, r.json()
            except Exception:
                return 200, r.text, None
        if r.status_code == 401:
            continue
        try:
            return r.status_code, r.text, r.json()
        except Exception:
            return r.status_code, r.text, None
    return last_status, last_text, None


def groq_post_with_auth_variants_sync(api_url, key, body, timeout=50):
    """Sync version of auth-variant POST for GROQ. Returns (status, text, parsed_json_or_None)."""
    variants = [
        {"Authorization": f"Bearer {key}"},
        {"X-API-Key": key},
        {"Cookie": f"session={key}"},
        {"X-API-Key": key, "Cookie": f"session={key}"},
        {"Authorization": f"Bearer {key}", "Cookie": f"session={key}"},
    ]
    last_status = None
    last_text = None
    for hdrs in variants:
        headers = hdrs.copy()
        headers.setdefault("Content-Type", "application/json")
        try:
            r = requests.post(api_url, headers=headers, json=body, timeout=timeout)
        except Exception as e:
            cause = getattr(e, "__cause__", None)
            txt = str(e)
            if isinstance(cause, socket.gaierror) or "getaddrinfo" in txt.lower():
                return None, f"Network/DNS error: {txt}", None
            last_status = None
            last_text = f"Request error: {txt}"
            continue
        last_status = r.status_code
        last_text = r.text or ""
        if r.status_code == 200:
            try:
                return 200, r.text, r.json()
            except Exception:
                return 200, r.text, None
        if r.status_code == 401:
            continue
        try:
            return r.status_code, r.text, r.json()
        except Exception:
            return r.status_code, r.text, None
    return last_status, last_text, None


def generate_export_pdf(export_payload: dict) -> bytes:
    """Generate a nicely formatted PDF (bytes) containing full export payload."""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is not installed. Install with 'pip install reportlab'")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    heading = styles["Heading2"]
    small = ParagraphStyle("Small", parent=normal, fontSize=9)

    story = []
    story.append(Paragraph("College Planner — Full Export", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", small))
    story.append(Spacer(1, 12))

    # Profile
    profile = export_payload.get("profile", {})
    story.append(Paragraph("Profile", heading))
    def add_kv(k, v):
        story.append(Paragraph(f"<b>{k}:</b> {v}", normal))
    add_kv("GPA", profile.get("gpa", "—"))
    add_kv("GPA scale", profile.get("gpa_scale", "—"))
    add_kv("Intended major", profile.get("major", "—"))
    add_kv("School", profile.get("school", "—"))

    # Awards / activities as numbered list
    awards = profile.get("awards", [])
    if awards:
        story.append(Paragraph("Honors / Activities:", normal))
        numbered = ListFlowable([
            ListItem(Paragraph(str(item), normal), value=i+1) for i, item in enumerate(awards)
        ], bulletType="1", start="1")
        story.append(numbered)
    else:
        story.append(Paragraph("Honors / Activities: None", normal))
    story.append(Spacer(1, 12))

    # Exams
    exams = profile.get("exams", {})
    story.append(Paragraph("Exams & Scores", heading))
    if exams:
        for i, (ename, edata) in enumerate(exams.items(), 1):
            parts = [f"{ename} — {edata.get('status', 'N/A')}"]
            if edata.get("score"):
                parts.append(f"score: {edata.get('score')}")
            if edata.get("expected"):
                parts.append(f"expected: {edata.get('expected')}")
            if edata.get("date"):
                parts.append(f"date: {edata.get('date')}")
            if edata.get("planned_date"):
                parts.append(f"planned: {edata.get('planned_date')}")
            story.append(Paragraph(f"{i}. " + "; ".join(parts), normal))
    else:
        story.append(Paragraph("No exam data", normal))
    story.append(Spacer(1, 12))

    # Tasks
    story.append(Paragraph("Tasks", heading))
    tasks = export_payload.get("tasks", [])
    if tasks:
        numbered_tasks = ListFlowable([
            ListItem(Paragraph(f"{t.get('title')} — due: {t.get('due')} — done: {t.get('done')}", normal))
            for t in tasks
        ], bulletType="1", start="1")
        story.append(numbered_tasks)
    else:
        story.append(Paragraph("No tasks", normal))
    story.append(Spacer(1, 12))

    # Favorites
    story.append(Paragraph("Favorites", heading))
    favs = export_payload.get("favorites", [])
    if favs:
        for f in favs:
            story.append(Paragraph(f"- {f.get('name')} ({f.get('country_code','')}) — {f.get('url')}", normal))
    else:
        story.append(Paragraph("No favorites", normal))
    story.append(Spacer(1, 12))

    # Deadlines as table
    story.append(Paragraph("Deadlines", heading))
    dls = export_payload.get("deadlines", [])
    if dls:
        table_data = [["University", "Type", "Date", "Note"]]
        for d in dls:
            table_data.append([d.get("uni", ""), d.get("type", ""), d.get("date", ""), d.get("note", "")])
        tbl = Table(table_data, colWidths=[150, 120, 80, 180])
        tbl.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("No deadlines", normal))
    story.append(Spacer(1, 12))

    # Notes
    story.append(Paragraph("Notes", heading))
    notes = export_payload.get("notes", {})
    if notes:
        for uni, note in notes.items():
            story.append(Paragraph(f"- {uni}: {note}", normal))
    else:
        story.append(Paragraph("No notes", normal))

    doc.build(story)
    return buf.getvalue()


async def get_ai_advice(profile: dict) -> str:
    """Call LLM provider (GROQ) for personalized advice."""
    if not GROQ_API_KEY:
        return "API key not found. Set GROQ_API_KEY in server environment or in .env."

    key = GROQ_API_KEY
    api_url = st.session_state.get("groq_api_url", GROQ_API_URL)
    model_name = GROQ_MODEL

    gpa = profile.get("gpa", "Unknown")
    major = profile.get("major", "Unknown")
    extras = profile.get("extras_level", "Unknown")
    awards = ", ".join(profile.get("awards", []))
    exams = profile.get("exams", {})

    exam_summary = []
    for name, data in exams.items():
        txt = f"{name}: {data.get('status')}"
        if data.get("score"):
            txt += f" (score {data['score']})"
        if data.get("expected"):
            txt += f" (expected {data['expected']})"
        exam_summary.append(txt)
    exam_summary = "; ".join(exam_summary) if exam_summary else "None"

    prompt = f"""
You are an educational advisor. Using the student's profile, suggest:

1) 35 suitable university specialties (majors)
2) Example universities worldwide
3) Why each is a good match
4) Suggested next steps

Student profile:
- GPA: {gpa}
- Intended major: {major}
- Extracurricular strength: {extras}/5
- Awards: {awards}
- Exams: {exam_summary}

Give the answer in clear sections with bullet points.
""".strip()

    body = {
        "messages": [
            {"role": "system", "content": "You are a helpful university and major advisor."},
            {"role": "user", "content": prompt},
        ],
        "model": model_name,
    }

    try:
        status, text, data = await _groq_post_with_auth_variants(api_url, key, body, timeout=40)
        if status is None:
            mock = generate_mock_advice(profile)
            return f"(offline fallback — network error: {text})\n\n{mock}"
        if status == 200:
            return _try_extract_assistant_text(data) if data is not None else text
        if status == 401:
            return (
                f"API 401: {text[:800]}\n"
                "Проверь GROQ_API_KEY и GROQ_API_URL в .env. Попробуй другой формат ключа."
            )
        return f"API error {status}: {text}"
    except Exception as e:
        return f"Error contacting AI: {e}"


def test_groq_endpoint(api_url, timeout=5):
    """Sync test: DNS resolution + simple HEAD request. Returns (ok: bool, msg: str)."""
    try:
        host = api_url.split("://")[-1].split("/")[0]
        socket.getaddrinfo(host, None)
    except Exception as e:
        return False, f"DNS error: {e}"
    try:
        r = requests.head(api_url, timeout=timeout)
        if 200 <= r.status_code < 400:
            return True, f"OK — {r.status_code}"
        return False, f"HTTP {r.status_code}: {r.text[:300]}"
    except Exception as e:
        txt = str(e)
        if "getaddrinfo" in txt.lower():
            return False, f"Network/DNS error: {txt}"
        return False, f"Request error: {txt}"


@st.cache_data
def load_universities():
    """
    Load world-universities.csv.
    Accept both headered CSVs (with columns like CountryCode, UniversityName, Website)
    and headerless files (country_code, name, url).
    Normalize column names to: country_code, name, url when possible.
    """
    p = Path("world-universities.csv")
    if not p.exists():
        return None

    # Try reading with header and normalizing common column names
    try:
        df_try = pd.read_csv(p)
        if df_try.shape[1] >= 2:
            # map possible header names to standard columns
            cols = list(df_try.columns)
            cols_low = [str(c).lower().strip() for c in cols]
            country_col = None
            name_col = None
            url_col = None
            for i, c in enumerate(cols_low):
                if "country" in c or c in ("countrycode", "country_code", "cc"):
                    country_col = cols[i]
                if "name" in c or "university" in c or "institution" in c or "title" in c:
                    name_col = cols[i]
                if "website" in c or "url" in c or "site" in c:
                    url_col = cols[i]
            # If we found a plausible name column, rename detected columns to standard names
            if name_col:
                rename_map = {}
                rename_map[name_col] = "name"
                if country_col:
                    rename_map[country_col] = "country_code"
                if url_col:
                    rename_map[url_col] = "url"
                # Apply rename
                df_try = df_try.rename(columns=rename_map)
                # Ensure columns exist (avoid KeyErrors later)
                if "country_code" not in df_try.columns:
                    df_try["country_code"] = ""
                if "url" not in df_try.columns:
                    df_try["url"] = ""
                return df_try

        # if header exists but no clear name column, fall through to headerless attempt
    except Exception:
        pass

    # Fallback: try headerless read and force column names
    try:
        df = pd.read_csv(p, header=None, names=["country_code", "name", "url"], usecols=[0, 1, 2])
        df["country_code"] = df["country_code"].astype(str)
        return df
    except Exception:
        # last resort: read whatever and coerce names if possible
        try:
            df_any = pd.read_csv(p, header=None)
            if df_any.shape[1] >= 3:
                df_any = df_any.rename(columns={0: "country_code", 1: "name", 2: "url"})
            return df_any
        except Exception:
            return None


def try_load(path):
    p = Path(path)
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            return None
    return None


def ensure_name_column(df):
    """
    Ensure dataframe has a 'name' column.
    If it already has, return that name.
    Else try common candidates or fallback to column index 1.
    """
    cols = list(df.columns)
    lower = [c.lower() for c in cols]
    for cand in ["name", "university", "institution", "title"]:
        if cand in lower:
            idx = lower.index(cand)
            return cols[idx]
    if len(cols) >= 2:
        return cols[1]
    return cols[0]


def ensure_country_code_column(df):
    """Ensure dataframe has a 'country_code' column with valid data. Do not overwrite existing codes."""
    if "country_code" not in df.columns:
        # Try to extract from URL domain or create placeholder
        if "url" in df.columns:
            def extract_country(url):
                if pd.isna(url) or str(url).strip() == "":
                    return "UN"
                url_str = str(url).lower()
                if ".uk" in url_str or ".co.uk" in url_str:
                    return "GB"
                if ".de" in url_str:
                    return "DE"
                if ".fr" in url_str:
                    return "FR"
                if ".ch" in url_str:
                    return "CH"
                if ".au" in url_str:
                    return "AU"
                if ".ca" in url_str:
                    return "CA"
                if ".us" in url_str or ".edu" in url_str:
                    return "US"
                if ".kz" in url_str:
                    return "KZ"
                if ".ru" in url_str:
                    return "RU"
                if ".cn" in url_str:
                    return "CN"
                if ".jp" in url_str:
                    return "JP"
                if ".in" in url_str:
                    return "IN"
                return "UN"
            df["country_code"] = df["url"].apply(extract_country)
        else:
            df["country_code"] = "UN"
    else:
        # Fill ONLY NaN/empty values with extraction, don't overwrite existing non-empty data
        def fill_empty_country(row):
            existing = row.get("country_code")
            if pd.isna(existing) or str(existing).strip() == "":
                url_str = str(row.get("url", "")).lower()
                if ".uk" in url_str or ".co.uk" in url_str:
                    return "GB"
                if ".de" in url_str:
                    return "DE"
                if ".fr" in url_str:
                    return "FR"
                if ".ch" in url_str:
                    return "CH"
                if ".au" in url_str:
                    return "AU"
                if ".ca" in url_str:
                    return "CA"
                if ".us" in url_str or ".edu" in url_str:
                    return "US"
                if ".kz" in url_str:
                    return "KZ"
                if ".ru" in url_str:
                    return "RU"
                if ".cn" in url_str:
                    return "CN"
                if ".jp" in url_str:
                    return "JP"
                if ".in" in url_str:
                    return "IN"
                return "UN"
            return existing
        df["country_code"] = df.apply(fill_empty_country, axis=1)
    return df


def parse_profile_gpa(profile):
    """Return numeric GPA and scale if present."""
    gpa = profile.get("gpa", "")
    scale = profile.get("gpa_scale", None)
    if isinstance(gpa, str) and "/" in gpa:
        try:
            a, b = gpa.split("/")
            return float(a), float(b)
        except Exception:
            pass
    try:
        return float(gpa), float(scale) if scale else None
    except Exception:
        return None, None

def generate_mock_advice(profile: dict, question: str = None) -> str:
    """Simple offline mock: produce a helpful-but-generic response when API is unreachable."""
    name = profile.get("school", "student")
    gpa = profile.get("gpa", "Unknown")
    major = profile.get("major", "Undeclared")
    extras = profile.get("extras_level", 0)
    best = [
        "Уточни интересы и предметы, которые нравятся — это поможет сузить специальности.",
        "Сосредоточься на сильных предметах и примерах достижений в мотивационном письме.",
        "Если GPA ~4+, рассматривай варианты топ-университетов; при меньшем — ищи программы по профилю и стипендии.",
        "Подготовься к TOEFL/IELTS и/или SAT/ACT — это откроет больше опций.",
    ]
    resp = f"Offline mock advice for {name} (GPA: {gpa}, major: {major}, extras: {extras}):\n\n"
    if question:
        resp += f"Question: {question}\n\n"
    resp += "Recommendations:\n"
    for i, r in enumerate(best[:4], 1):
        resp += f"- {i}. {r}\n"
    resp += "\n(Это локальная заглушка — при восстановлении сети приложение использует реальную модель.)"
    return resp

# Helper functions for task board
def move_task_region(task_id: int, direction: int):
    """Move task to neighboring region: direction -1 (left), +1 (right)."""
    regions = st.session_state.get("task_regions", [])
    for t in st.session_state.tasks:
        if t.get("id") == task_id:
            try:
                idx = regions.index(t.get("region")) if t.get("region") in regions else 0
                new_idx = max(0, min(len(regions) - 1, idx + direction))
                t["region"] = regions[new_idx]
            except Exception:
                t["region"] = regions[0] if regions else t.get("region")
            break


def reorder_task_in_region(task_id: int, up: bool = True):
    """Move task up or down within its region."""
    tasks = st.session_state.tasks
    # find global index
    for i, t in enumerate(tasks):
        if t.get("id") == task_id:
            region = t.get("region")
            region_indices = [j for j, it in enumerate(tasks) if it.get("region") == region]
            pos = region_indices.index(i)
            if up and pos > 0:
                j_swap = region_indices[pos - 1]
                tasks[i], tasks[j_swap] = tasks[j_swap], tasks[i]
            if (not up) and (pos < len(region_indices) - 1):
                j_swap = region_indices[pos + 1]
                tasks[i], tasks[j_swap] = tasks[j_swap], tasks[i]
            break


def toggle_task_done(task_id: int, done_value: bool):
    for t in st.session_state.tasks:
        if t.get("id") == task_id:
            t["done"] = bool(done_value)
            break

# ---------------------------------------
# Load data
# -------
universities_df = load_universities()
# Don't call ensure_country_code_column here yet — load_universities may already have country_code

qs_df = try_load("qs-ranking.csv")
the_df = try_load("the-ranking.csv")
nytimes_df = try_load("nytimes-ranking.csv")

# Merge rankings best-effort
if universities_df is not None:
    uni_df = universities_df.copy()
    name_col_main = ensure_name_column(uni_df)
    uni_df = ensure_country_code_column(uni_df)  # Ensure country_code before merging
    uni_df["__name_l"] = uni_df[name_col_main].astype(str).str.lower()

    if qs_df is not None:
        qs_name_col = ensure_name_column(qs_df)
        qs_df = qs_df.copy()
        qs_df["__name_l"] = qs_df[qs_name_col].astype(str).str.lower()
        rank_col = None
        for c in ["rank", "ranking", "position"]:
            if c in qs_df.columns:
                rank_col = c
                break
        if rank_col:
            qs_merge = qs_df[["__name_l", rank_col]].rename(columns={rank_col: "ranking_qs"})
            uni_df = uni_df.merge(qs_merge, on="__name_l", how="left")

    if the_df is not None:
        the_name_col = ensure_name_column(the_df)
        the_df = the_df.copy()
        the_df["__name_l"] = the_df[the_name_col].astype(str).str.lower()
        the_rank_col = None
        for c in ["rank", "ranking", "position"]:
            if c in the_df.columns:
                the_rank_col = c
                break
        if the_rank_col:
            the_merge = the_df[["__name_l", the_rank_col]].rename(columns={the_rank_col: "ranking_the"})
            uni_df = uni_df.merge(the_merge, on="__name_l", how="left")

    if nytimes_df is not None:
        ny_name_col = ensure_name_column(nytimes_df)
        nytimes_df = nytimes_df.copy()
        nytimes_df["__name_l"] = nytimes_df[ny_name_col].astype(str).str.lower()
        ny_rank_col = None
        for c in ["rank", "ranking", "position", "score"]:
            if c in nytimes_df.columns:
                ny_rank_col = c
                break
        if ny_rank_col:
            ny_merge = nytimes_df[["__name_l", ny_rank_col]].rename(columns={ny_rank_col: "ranking_nyt"})
            uni_df = uni_df.merge(ny_merge, on="__name_l", how="left")

    if "__name_l" in uni_df.columns:
        uni_df = uni_df.drop(columns=["__name_l"])
    universities_df = uni_df

# ---------------------------------------
# Holland RIASEC Career Test Questions
# -------
HOLLAND_QUESTIONS = {
    "R": [
        "I like working with tools and machines",
        "I enjoy repairing or assembling things",
        "I prefer practical tasks over theory",
        "I like working outdoors",
        "I enjoy technical activities",
        "I like hands-on problem solving",
        "I enjoy mechanical tasks",
        "I like operating equipment",
        "I enjoy building things",
        "I prefer physical activity at work",
    ],
    "I": [
        "I enjoy solving complex problems",
        "I like scientific experiments",
        "I enjoy analyzing data",
        "I like working independently",
        "I enjoy math or physics",
        "I like researching topics deeply",
        "I enjoy logical thinking",
        "I like theoretical discussions",
        "I enjoy learning new concepts",
        "I prefer thinking over doing",
    ],
    "A": [
        "I enjoy creative expression",
        "I like drawing, writing, or music",
        "I enjoy original ideas",
        "I like unstructured tasks",
        "I enjoy design",
        "I like expressing emotions",
        "I enjoy creative freedom",
        "I like visual thinking",
        "I enjoy storytelling",
        "I dislike rigid rules",
    ],
    "S": [
        "I like helping people",
        "I enjoy teaching or explaining",
        "I am a good listener",
        "I enjoy teamwork",
        "I like supporting others emotionally",
        "I enjoy social projects",
        "I communicate easily",
        "I enjoy mentoring",
        "I care about community impact",
        "I prefer people over things",
    ],
    "E": [
        "I like leading others",
        "I enjoy persuading people",
        "I am comfortable making decisions",
        "I enjoy business topics",
        "I like taking responsibility",
        "I enjoy competition",
        "I like organizing people",
        "I enjoy public speaking",
        "I like setting goals",
        "I want to influence outcomes",
    ],
    "C": [
        "I like structure and order",
        "I enjoy working with data",
        "I follow instructions carefully",
        "I like planning tasks",
        "I enjoy working with documents",
        "I value stability",
        "I like predictable routines",
        "I pay attention to details",
        "I enjoy organizing information",
        "I like clear rules",
    ],
}

def calculate_holland_code():
    """Calculate Holland code from answers."""
    scores = {letter: 0 for letter in "RIASEC"}
    
    for q_idx, (letter, questions) in enumerate(HOLLAND_QUESTIONS.items()):
        for q_num in range(10):
            answer_key = f"{letter}_{q_num}"
            if answer_key in st.session_state.career_test_answers:
                scores[letter] += st.session_state.career_test_answers[answer_key]
    
    st.session_state.holland_scores = scores
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    st.session_state.holland_code = "-".join([item[0] for item in sorted_scores[:3]])

# ---------------------------------------
# UI Layout: Tabs
# -------
tabs = st.tabs([
    "🧭 Career Test",
    "👤 Profile",
    "✅ Tasks",
    "🏫 Universities",
    "📅 Deadlines",
    "📚 Preparation",
    "💡 AI Advisor",
])

# -------
# Career Test Tab
# -------
with tabs[0]:
    st.header("🧭 Holland Career Orientation Test")
    st.caption("Discover your career type using the Holland RIASEC model. Answer 60 questions in 6 blocks.")
    current_block = st.session_state.career_test_current_block
    holland_types = {"R": "Realistic", "I": "Investigative", "A": "Artistic", "S": "Social", "E": "Enterprising", "C": "Conventional"}
    all_blocks = list(HOLLAND_QUESTIONS.keys())
    if current_block < len(all_blocks):
        block_letter = all_blocks[current_block]
        block_type = holland_types[block_letter]
        st.subheader(f"Step {current_block + 1} of {len(all_blocks)}: {block_letter} - {block_type} Type")
        st.caption(f"Rate each statement from 1 (Not me at all) to 5 (Very much me)")
        st.progress((current_block + 1) / len(all_blocks))
        questions = HOLLAND_QUESTIONS[block_letter]
        st.markdown("---")
        for q_idx, question in enumerate(questions):
            q_key = f"{block_letter}_{q_idx}"
            current_answer = st.session_state.career_test_answers.get(q_key, 3)
            st.session_state.career_test_answers[q_key] = st.select_slider(
                f"{q_idx + 1}. {question}",
                options=[1, 2, 3, 4, 5],
                value=current_answer,
                format_func=lambda x: {1: "1: Not me", 2: "2: Slightly not", 3: "3: Neutral", 4: "4: Somewhat", 5: "5: Very much"}[x],
                key=q_key,
            )
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if current_block > 0 and st.button("← Previous Block"):
                st.session_state.career_test_current_block -= 1
                st.rerun()
        with col3:
            if current_block < len(all_blocks) - 1:
                if st.button("Next Block →"):
                    st.session_state.career_test_current_block += 1
                    st.rerun()
            else:
                if st.button("🎯 Complete Test"):
                    calculate_holland_code()
                    st.session_state.career_test_current_block = len(all_blocks)
                    st.rerun()
    else:
        st.success("✅ Career test completed!")
        if st.session_state.holland_code and st.session_state.holland_scores:
            st.markdown(f"### Your Holland Code: **{st.session_state.holland_code}**")
            st.markdown("#### Your RIASEC Scores:")
            scores_data = [{"Type": f"{letter} - {holland_types[letter]}", "Score": st.session_state.holland_scores.get(letter, 0)} for letter in "RIASEC"]
            scores_df = pd.DataFrame(scores_data)
            st.dataframe(scores_df, use_container_width=True)
            st.markdown("#### What does this mean?")
            code_letters = st.session_state.holland_code.split("-")
            explanations = {
                "R": "**Realistic** - You prefer practical, hands-on work with tools, machines, or nature.",
                "I": "**Investigative** - You prefer analytical, scientific, and research-oriented work.",
                "A": "**Artistic** - You prefer creative, unstructured work that allows self-expression.",
                "S": "**Social** - You prefer helping, teaching, and working with people.",
                "E": "**Enterprising** - You prefer leading, persuading, and business-oriented activities.",
                "C": "**Conventional** - You prefer structured, organized work with clear procedures and data.",
            }
            for i, letter in enumerate(code_letters, 1):
                st.write(f"{i}. {explanations.get(letter, '')}")
            st.markdown("---")
            if st.button("🔄 Retake Test"):
                st.session_state.career_test_current_block = 0
                st.session_state.career_test_answers = {}
                st.session_state.holland_code = None
                st.session_state.holland_scores = None
                st.rerun()

# -------
# Profile Tab (merged with Exams)
# -------
with tabs[1]:
    st.header("🧭 Career Orientation")
    if st.session_state.holland_code:
        st.success(f"Holland Type: **{st.session_state.holland_code}**")
        explanations = {
            "R": "Realistic - Practical, hands-on work",
            "I": "Investigative - Analytical, research work",
            "A": "Artistic - Creative, expressive work",
            "S": "Social - Helping, teaching, people-oriented work",
            "E": "Enterprising - Leading, business-oriented work",
            "C": "Conventional - Structured, organized work",
        }
        for letter in st.session_state.holland_code.split("-"):
            st.write(f"**{letter}:** {explanations.get(letter, '')}")
    else:
        st.info("Career test not completed yet. Visit the 🧭 Career Test tab to discover your Holland type.")
    
    st.markdown("---")
    st.header("👤 Profile")
    st.caption("We'll use this to estimate chances and personalize AI advice.")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Academics")
            gpa_display = st.text_input(
                "GPA",
                value=st.session_state.profile.get("gpa", ""),
                placeholder="4.8/5.0 or 4.8",
                help="You can write either 4.8/5.0 or just 4.8",
            )
            gpa_scale = st.selectbox(
                "GPA scale",
                options=[None, 4, 5, 10, 100],
                index=0,
                help="Optional: choose if you wrote only the raw GPA above",
            )
            major = st.text_input(
                "Intended major",
                st.session_state.profile.get("major", ""),
                placeholder="Computer Science, Economics...",
            )

        with col2:
            st.subheader("School & Activities")
            school = st.text_input("School", st.session_state.profile.get("school", ""))
            awards = st.text_area(
                "Awards & activities",
                value="\n".join(st.session_state.profile.get("awards", [])),
                placeholder="Olympiad in math – national\nVolunteering – local community",
                height=120,
            )
            extras_level = st.select_slider(
                "Extracurricular strength (0–5)",
                options=[0, 1, 2, 3, 4, 5],
                value=st.session_state.profile.get("extras_level", 0),
            )

        save = st.form_submit_button("💾 Save profile")

        if save:
            st.session_state.profile.update({
                "gpa": gpa_display.strip(),
                "gpa_scale": gpa_scale,
                "major": major.strip(),
                "school": school.strip(),
                "awards": [a.strip() for a in awards.splitlines() if a.strip()],
                "extras_level": extras_level,
                "updated": datetime.now().isoformat(),
            })
            st.success("Profile saved")

    

    # --- Exams subsection ---
    st.markdown("---")
    st.subheader("🧪 Exams & Scores")
    st.caption("Manage test results and planned exam dates.")

    exams_existing = st.session_state.profile.get("exams", {})
    exam_options = ["SAT", "IELTS", "TOEFL", "ACT", "UNT"]
    selected_exams = st.multiselect("Choose exams to manage", exam_options, key="exams_select")

    exam_results = exams_existing.copy() if isinstance(exams_existing, dict) else {}

    for exam in selected_exams:
        st.markdown(f"#### 📝 {exam}")
        col1, col2 = st.columns([2, 3])
        with col1:
            status = st.selectbox(
                f"{exam} status",
                ["N/A", "Already taken", "Planned"],
                key=f"{exam}_status",
                index=0,
            )
        with col2:
            if status == "Already taken":
                score = st.text_input(
                    f"{exam} Score",
                    key=f"{exam}_score",
                    value=exam_results.get(exam, {}).get("score", ""),
                )
                date_val = st.date_input(
                    f"{exam} Test Date",
                    key=f"{exam}_date",
                    value=pd.to_datetime(
                        exam_results.get(exam, {}).get("date", datetime.now().date())
                    ),
                )
            elif status == "Planned":
                exp = st.text_input(
                    f"Expected {exam} Score",
                    key=f"{exam}_expected",
                    value=exam_results.get(exam, {}).get("expected", ""),
                )
                pdate = st.date_input(
                    f"Planned {exam} Date",
                    key=f"{exam}_planned_date",
                    value=pd.to_datetime(
                        exam_results.get(exam, {}).get("planned_date", datetime.now().date())
                    ),
                )
            else:
                score = ""
                date_val = None

        exam_results[exam] = {"status": status}
        if status == "Already taken":
            exam_results[exam]["score"] = score
            exam_results[exam]["date"] = str(date_val)
        elif status == "Planned":
            exam_results[exam]["expected"] = exp
            exam_results[exam]["planned_date"] = str(pdate)

    if st.button("Save exams to profile", key="save_exams_btn"):
        st.session_state.profile["exams"] = exam_results
        st.success("Exams saved to profile.")

    # Display exams summary (readable text instead of JSON)
    if exam_results:
        st.markdown("#### 📊 Exams Summary")
        for exam_name, exam_data in exam_results.items():
            status = exam_data.get("status")
            if status == "N/A":
                continue
            elif status == "Already taken":
                score = exam_data.get("score", "—")
                date_str = exam_data.get("date", "—")
                st.write(f"✅ **{exam_name}**: {score} (taken {date_str})")
            elif status == "Planned":
                expected = exam_data.get("expected", "—")
                planned_date = exam_data.get("planned_date", "—")
                st.write(f"⏳ **{exam_name}**: Expected {expected} (planned {planned_date})")

# ---------------------------------------
# Tasks Tab — Regional Kanban
# ---------------------------------------
with tabs[2]:
    st.header("✅ Tasks — Regional Board")
    st.caption("Organize tasks by region. Add custom regions and manage tasks (move, reorder, complete).")

    # Regions manager
    st.subheader("Regions")
    col_r1, col_r2 = st.columns([3, 1])
    with col_r1:
        st.write(", ".join(st.session_state.task_regions))
        new_region = st.text_input("Add region", key="add_region_input")
    with col_r2:
        if st.button("Add region", key="add_region_btn"):
            nr = new_region.strip()
            if nr and nr not in st.session_state.task_regions:
                st.session_state.task_regions.append(nr)
                st.success(f"Region '{nr}' added.")
                st.rerun()

    rem_region = st.selectbox("Remove region", [""] + st.session_state.task_regions, key="remove_region_select")
    if rem_region:
        if st.button("Remove region", key="remove_region_btn"):
            if rem_region in st.session_state.task_regions:
                # move tasks in removed region to first region
                target = st.session_state.task_regions[0] if st.session_state.task_regions else None
                for t in st.session_state.tasks:
                    if t.get("region") == rem_region:
                        t["region"] = target
                st.session_state.task_regions.remove(rem_region)
                st.success(f"Region '{rem_region}' removed.")
                st.rerun()

    st.markdown("---")

    # Add task form
    with st.form("add_task_form"):
        c1, c2, c3 = st.columns([4, 2, 1])
        with c1:
            task_title = st.text_input("Task title", key="new_task_title")
        with c2:
            task_due = st.date_input("Due date", value=date.today(), key="new_task_due")
        with c3:
            task_region = st.selectbox("Region", st.session_state.task_regions, key="new_task_region")
        added = st.form_submit_button("➕ Add task")
        if added and task_title.strip():
            st.session_state.task_id_counter = st.session_state.get("task_id_counter", 0) + 1
            st.session_state.tasks.append({
                "id": st.session_state.task_id_counter,
                "title": task_title.strip(),
                "due": str(task_due),
                "done": False,
                "region": task_region,
            })
            st.success("Task added.")
            st.rerun()

    st.markdown("---")

    # Board
    regions = st.session_state.task_regions
    if not regions:
        st.info("No regions defined. Add a region to get started.")
    else:
        cols = st.columns(len(regions))
        for idx, region in enumerate(regions):
            with cols[idx]:
                st.subheader(region)
                region_tasks = [t for t in st.session_state.tasks if t.get("region") == region]
                if not region_tasks:
                    st.info("No tasks here. Add one above.")
                else:
                    for t in list(region_tasks):
                        st.markdown("---")
                        st.markdown(f"**{t.get('title')}**")
                        st.caption(f"Due: {t.get('due')}")

                        # Done checkbox
                        checked = st.checkbox("Done", value=t.get("done", False), key=f"done_{t['id']}")
                        if checked != t.get("done", False):
                            toggle_task_done(t["id"], checked)
                            st.rerun()

                        b1, b2, b3, b4 = st.columns([0.25, 0.25, 0.25, 0.25])
                        if b1.button("◀", key=f"left_{t['id']}"):
                            move_task_region(t["id"], -1)
                            st.rerun()
                        if b2.button("▶", key=f"right_{t['id']}"):
                            move_task_region(t["id"], 1)
                            st.rerun()
                        if b3.button("🔼", key=f"up_{t['id']}"):
                            reorder_task_in_region(t["id"], up=True)
                            st.rerun()
                        if b4.button("🔽", key=f"down_{t['id']}"):
                            reorder_task_in_region(t["id"], up=False)
                            st.rerun()

                        e1, e2 = st.columns([3,1])
                        if e2.button("🗑", key=f"del_{t['id']}"):
                            st.session_state.tasks = [x for x in st.session_state.tasks if x.get("id") != t["id"]]
                            st.rerun()

                        # Edit inline
                        if st.button("✏️ Edit", key=f"edit_{t['id']}"):
                            st.session_state._edit_task = t['id']
                            st.rerun()

                        if st.session_state.get("_edit_task") == t['id']:
                            with st.form(f"edit_form_{t['id']}"):
                                new_title = st.text_input("Title", value=t['title'], key=f"edit_title_{t['id']}")
                                new_due = st.date_input("Due", value=pd.to_datetime(t['due']).date(), key=f"edit_due_{t['id']}")
                                new_region = st.selectbox("Region", st.session_state.task_regions, index=st.session_state.task_regions.index(t['region']) if t['region'] in st.session_state.task_regions else 0, key=f"edit_region_{t['id']}")
                                save_edit = st.form_submit_button("Save")
                                if save_edit:
                                    for task in st.session_state.tasks:
                                        if task.get('id') == t['id']:
                                            task['title'] = new_title.strip()
                                            task['due'] = str(new_due)
                                            task['region'] = new_region
                                    st.session_state._edit_task = None
                                    st.rerun()


# ---------------------------------------
# Universities Tab
# ---------------------------------------

with tabs[3]:
    st.header("Universities 🌍")
    st.caption("Ищи университеты по названию или коду страны и сразу переходи на их сайт. Плюс — избранное и рандомный выбор.")

    if universities_df is None:
        st.error("Файл world-universities.csv не найден. Положи его рядом с этим скриптом и перезапусти приложение.")
    else:
        # Верхняя панель поиска
        search_col1, search_col2, search_col3 = st.columns([2, 1, 1])

        with search_col1:
            query = st.text_input(
                "🔎 Search by university name",
                placeholder="e.g. Harvard, Nazarbayev, Oxford"
            )
        with search_col2:
            country_filter = st.text_input(
                "Country code (e.g. US, GB, KZ)",
                placeholder="Leave empty for all"
            )
        with search_col3:
            random_btn = st.button("🎲 Random university")

        # Фильтрация таблицы
        filtered = universities_df.copy()

        if query:
            filtered = filtered[
                filtered["name"].str.contains(query, case=False, na=False)
            ]

        if country_filter:
            cf = country_filter.strip().upper()
            filtered = filtered[
                filtered["country_code"].str.upper().str.contains(cf)
            ]

        # Статистика
        stats_col1, stats_col2 = st.columns(2)
        with stats_col1:
            st.metric("Universities found", len(filtered))
        with stats_col2:
            st.metric("In favorites", len(st.session_state.uni_favorites))

        # Рандом
        if random_btn:
            if len(filtered) > 0:
                row = filtered.sample(1).iloc[0]
                st.success(
                    f"🎓 Random pick: [{row['name']}]({row['url']}) — {row['country_code']}"
                )
            else:
                st.warning("Ничего не нашлось для рандома — измени фильтры 🙂")

        # ---- РЕЗУЛЬТАТЫ ----
        st.markdown("### Results")

        if filtered.empty:
            st.info("Нет результатов. Попробуй изменить запрос или код страны.")
        else:
            max_rows = 50
            if len(filtered) > max_rows:
                st.caption(f"Показаны первые {max_rows} результатов из {len(filtered)}.")

            for idx, row in filtered.head(max_rows).iterrows():
                c1, c2, c3 = st.columns([4, 2, 1])

                with c1:
                    st.markdown(f"**{row['name']}**")
                    st.markdown(f"[🌐 Open website]({row['url']})")

                with c2:
                    st.caption(f"Country code: {row['country_code']}")

                with c3:
                    is_fav = any(
                        fav["name"] == row["name"] and fav["url"] == row["url"]
                        for fav in st.session_state.uni_favorites
                    )

                    btn_label = "⭐ Add" if not is_fav else "✅ In favorites"
                    if st.button(btn_label, key=f"fav_{idx}", disabled=is_fav):
                        st.session_state.uni_favorites.append({
                            "country_code": row["country_code"],
                            "name": row["name"],
                            "url": row["url"]
                        })
                        st.success(f"Added to favorites: {row['name']}")

        # ---- FAVORITES ----
        st.markdown("### ⭐ Favorites")

        if not st.session_state.uni_favorites:
            st.caption("Пока пусто. Добавь универы из списка выше.")
        else:
            for i, uni in enumerate(st.session_state.uni_favorites):
                fc1, fc2 = st.columns([4, 1])
                with fc1:
                    st.markdown(
                        f"- [{uni['name']}]({uni['url']}) ({uni['country_code']})"
                    )
                with fc2:
                    if st.button("🗑 Remove", key=f"fav_del_{i}"):
                        st.session_state.uni_favorites.pop(i)
                        st.rerun()


# ---------------------------------------
# Deadlines & Dashboard Tab
# ---------------------------------------
with tabs[4]:
    st.header("📅 Deadlines")
    st.caption("Track application, scholarship and other important dates.")

    st.subheader("Add new deadline")
    with st.form("deadline_form"):
        d_uni = st.text_input("University name (type or paste)")
        d_type = st.selectbox(
            "Deadline type",
            ["Application (EA/ED)", "Regular decision", "Scholarship", "Supplement", "Other"],
        )
        d_date = st.date_input("Deadline date", date.today())
        d_note = st.text_input("Note (optional)")
        add_deadline = st.form_submit_button("Add deadline")
        if add_deadline and d_uni.strip():
            st.session_state.deadlines.append({
                "uni": d_uni.strip(),
                "type": d_type,
                "date": str(d_date),
                "note": d_note.strip(),
            })
            st.success("Deadline added!")

    st.markdown("### Upcoming deadlines (next 90 days)")
    df_dead = pd.DataFrame(st.session_state.deadlines)
    if df_dead.empty:
        st.info("No deadlines yet. Add some above.")
    else:
        df_dead["date_dt"] = pd.to_datetime(df_dead["date"])
        upcoming = df_dead[df_dead["date_dt"] >= pd.Timestamp.today()]
        upcoming = upcoming.sort_values("date_dt")
        upcoming_90 = upcoming[
            upcoming["date_dt"] <= (pd.Timestamp.today() + pd.Timedelta(days=90))
        ]
        if upcoming_90.empty:
            st.write("Нет дедлайнов в ближайшие 90 дней.")
        else:
            for i, row in upcoming_90.iterrows():
                days_left = (row["date_dt"].date() - date.today()).days
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    st.write(f"**{row['uni']}** — {row['type']} — {row['date']}")
                    if row.get("note"):
                        st.caption(row.get("note"))
                with c2:
                    st.metric("Days left", days_left)
                with c3:
                    if st.button("Delete", key=f"del_dead_{i}"):
                        st.session_state.deadlines.pop(i)
                        st.rerun()

    st.markdown("---")
    st.header("Progress Dashboard")
    col1, col2, col3 = st.columns(3)
    with col1:
        total_tasks = len(st.session_state.tasks)
        done_tasks = sum(1 for t in st.session_state.tasks if t.get("done"))
        st.metric("Tasks done", f"{done_tasks}/{total_tasks}")
        exams = st.session_state.profile.get("exams", {})
        planned = sum(1 for k, v in exams.items() if v.get("status") == "Planned")
        taken = sum(1 for k, v in exams.items() if v.get("status") == "Already taken")
        st.metric("Exams taken / planned", f"{taken} / {planned}")
    with col2:
        st.subheader("Favorites snapshot")
        if st.session_state.uni_favorites:
            for f in st.session_state.uni_favorites[:5]:
                st.write(f"- {f.get('name')} ({f.get('country_code','')})")
        else:
            st.write("No favorites yet.")
    with col3:
        st.subheader("Estimated chances (favorites)")
        rows = []
        for fav in st.session_state.uni_favorites:
            uni_row = None
            if universities_df is not None:
                name_col_main2 = ensure_name_column(universities_df)
                matches = universities_df[
                    universities_df[name_col_main2].astype(str).str.lower()
                    == str(fav.get("name", "")).lower()
                ]
                if not matches.empty:
                    uni_row = matches.iloc[0].to_dict()
            rows.append({"uni": fav.get("name"), "score": score})
        if rows:
            df_scores = pd.DataFrame(rows).set_index("uni")
            st.table(df_scores)
        else:
            st.write("No favorites to evaluate.")

    st.markdown("---")
    export_payload_full = {
        "profile": st.session_state.profile,
        "tasks": st.session_state.tasks,
        "favorites": st.session_state.uni_favorites,
        "deadlines": st.session_state.deadlines,
        "notes": st.session_state.uni_notes,
    }
    if REPORTLAB_AVAILABLE:
        try:
            pdf_bytes = generate_export_pdf(export_payload_full)
            st.download_button(
                "Export all data (profile, tasks, favorites, deadlines, notes) as PDF",
                data=pdf_bytes,
                file_name="college_planner_export.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error("PDF export failed: " + str(e))
            st.download_button(
                "Export all data (profile, tasks, favorites, deadlines, notes) (JSON fallback)",
                data=json.dumps(export_payload_full, indent=2),
                file_name="college_planner_export.json",
            )
    else:
        st.warning("PDF export unavailable — 'reportlab' is not installed. Run `pip install reportlab` or add it to requirements.txt and redeploy.")
        st.download_button(
            "Export all data (profile, tasks, favorites, deadlines, notes) (JSON)",
            data=json.dumps(export_payload_full, indent=2),
            file_name="college_planner_export.json",
        )

    # JSON import removed (PDF-only workflow)

# --- NEW: Preparation Tab (fixed with proper with/expander structure) ---
with tabs[5]:
    st.header("📚 Preparation Materials")
    st.caption("Resources, guides and practice materials for popular exams. Раскрой секции для деталей.")

    # Ensure session lists for user-added resources
    if "prep_user_resources" not in st.session_state:
        st.session_state.prep_user_resources = {"SAT": [], "IELTS": [], "TOEFL": [], "ACT": []}

    prep_tabs = st.tabs(["SAT", "IELTS", "TOEFL", "ACT"])

    def render_resource_group(title, items):
        if items:
            st.markdown(f"**{title}:**")
            for it in items:
                st.markdown(f"- {it}")

    # SAT tab
    with prep_tabs[0]:
        with st.expander("About SAT — формат и что важно знать", expanded=False):
            st.write(
                "SAT — это вступительный экзамен, используемый большинством колледжей и университетов при принятии решений о зачислении. "
                "SAT — это компьютерный тест с несколькими вариантами ответов, разработанный и администрируемый College Board."
            )
            st.write(
                "SAT применяется для оценки готовности школьника к обучению в колледже и предоставляет колледжам единый показатель, "
                "с помощью которого можно сравнивать всех поступающих. Приёмные комиссии рассматривают результаты стандартизированных тестов "
                "наряду с вашим школьным GPA, перечнем пройденных курсов, рекомендациями от учителей или наставников, внеклассной деятельностью, "
                "интервью при приёме и личными эссе. Значимость результатов SAT в процессе приёма варьируется в зависимости от университета."
            )
            st.write(
                "В целом: чем выше ваш результат по SAT (и/или ACT), тем больше у вас опций для поступления и получения финансовой поддержки."
            )
            sat_rows = [
                ("Длительность", "2 часа 14 минут"),
                ("Разделы", "Evidence-Based Reading and Writing; Math"),
                ("Стоимость — локальные студенты", "$68"),
                ("Стоимость — международные студенты", "$111"),
                ("Максимальный балл", "1600"),
                ("Средний балл", "1060"),
            ]
            sat_df = pd.DataFrame(sat_rows, columns=["Показатель", "Значение"]).set_index("Показатель")
            st.table(sat_df)

        with st.expander("SAT — Resources", expanded=True):
            render_resource_group("Official", [
                "[SAT Official Website](https://www.sat.org/)",
                "[College Board SAT Suite](https://collegereadiness.collegeboard.org/)"
            ])
            render_resource_group("Free practice", [
                "[Khan Academy SAT Prep](https://www.khanacademy.org/test-prep/sat)"
            ])
            render_resource_group("Practice & Question banks", [
                "[OnePrep Question Bank & Practice Tests](https://oneprep.xyz)",
                "[PlayNTest Practice Tests](https://playntest.com)",
                "[The Official SAT Study Guide](https://www.sat.org/shop/official-sat-study-guide)",
            ])
            render_resource_group("Paid services", [
                "[Princeton Review](https://www.princetonreview.com/)",
                "[Kaplan Test Prep](https://www.kaptest.com/sat)",
                "[Prep Scholar](https://www.prepscholar.com/sat)"
            ])
            st.markdown("---")
            st.write("Добавить свой ресурс (URL или описание):")
            user_sat = st.text_input("", key="prep_user_sat")
            if st.button("Add SAT resource", key="prep_add_sat"):
                if user_sat.strip():
                    st.session_state.prep_user_resources["SAT"].append(user_sat.strip())
                    st.success("Resource added.")
                else:
                    st.warning("Введите URL или описание ресурса.")

            if st.session_state.prep_user_resources["SAT"]:
                st.markdown("**Your SAT resources:**")
                for r in st.session_state.prep_user_resources["SAT"]:
                    st.markdown(f"- {r}")

    # IELTS tab
    with prep_tabs[1]:
        with st.expander("About IELTS — формат и советы", expanded=False):
            st.write(
                "IELTS оценивает навыки аудирования, чтения, письма и говорения. "
                "Разделяй подготовку по навыкам: регулярная практика аудио и реальных заданий повышает результат."
            )

        with st.expander("IELTS — Resources", expanded=True):
            render_resource_group("Official", [
                "[IELTS Official Website](https://www.ielts.org/)",
                "[British Council IELTS Preparation](https://www.britishcouncil.org/exam/ielts/preparation)",
                "[IDP IELTS](https://www.idpielts.com/)"
            ])
            render_resource_group("Courses & Practice", [
                "[Udemy IELTS Courses](https://www.udemy.com/courses/search/?q=IELTS)",
                "[Coursera IELTS Prep](https://www.coursera.org/search?query=IELTS)",
                "[E2Language IELTS Prep](https://www.e2language.com/)"
            ])
            render_resource_group("Practice materials & guides", [
                "[IELTS Practice Tests (sample questions)](https://www.ielts.org/about-the-test/sample-test-questions)",
                "[Cambridge IELTS Books](https://www.cambridge.org/us/cambridgeenglish/catalog/ielts-preparation)",
                "[IELTS Listening Practice](https://listeningpractice.org/)",
                "[IELTS Advantage Guides & Tips](https://ieltsadvantage.com)"
            ])
            st.markdown("---")
            st.write("Добавить свой ресурс (URL или описание):")
            user_ielts = st.text_input("", key="prep_user_ielts")
            if st.button("Add IELTS resource", key="prep_add_ielts"):
                if user_ielts.strip():
                    st.session_state.prep_user_resources["IELTS"].append(user_ielts.strip())
                    st.success("Resource added.")
                else:
                    st.warning("Введите URL или описание ресурса.")
            if st.session_state.prep_user_resources["IELTS"]:
                st.markdown("**Your IELTS resources:**")
                for r in st.session_state.prep_user_resources["IELTS"]:
                    st.markdown(f"- {r}")

    # TOEFL tab
    with prep_tabs[2]:
        with st.expander("About TOEFL — что важно", expanded=False):
            st.write(
                "TOEFL фокусируется на академическом английском (чит./ауд./письмо/говорение). "
                "Полноформатные пробники и работа с тайм-менеджментом критичны."
            )

        with st.expander("TOEFL — Resources", expanded=True):
            render_resource_group("Official", [
                "[TOEFL Official Website](https://www.ets.org/toefl)",
                "[ETS Official TOEFL Guide](https://www.ets.org/toefl/test-takers/ibt/prepare/materials/official-guide)"
            ])
            render_resource_group("Courses", [
                "[Magoosh TOEFL Prep](https://magoosh.com/toefl/)",
                "[Kaplan TOEFL](https://www.kaptest.com/toefl)",
                "[Coursera TOEFL Preparation](https://www.coursera.org/search?query=TOEFL)"
            ])
            render_resource_group("Practice & materials", [
                "[TOEFL Practice Tests (ETS)](https://www.ets.org/toefl/test-takers/ibt/prepare/full-length-practice-tests)",
                "[English Central TOEFL](https://www.englishcentral.com/courses)",
                "[TST Prep TOEFL Resources](https://www.tstprep.com/)"
            ])
            st.markdown("---")
            st.write("Добавить свой ресурс (URL или описание):")
            user_toefl = st.text_input("", key="prep_user_toefl")
            if st.button("Add TOEFL resource", key="prep_add_toefl"):
                if user_toefl.strip():
                    st.session_state.prep_user_resources["TOEFL"].append(user_toefl.strip())
                    st.success("Resource added.")
                else:
                    st.warning("Введите URL или описание ресурса.")
            if st.session_state.prep_user_resources["TOEFL"]:
                st.markdown("**Your TOEFL resources:**")
                for r in st.session_state.prep_user_resources["TOEFL"]:
                    st.markdown(f"- {r}")

    # ACT tab
    with prep_tabs[3]:
        with st.expander("About ACT — кратко", expanded=False):
            st.write(
                "ACT включает английский, математику, чтение, науку и опциональный эссe. "
                "Раздели подготовку по секциям и тренируй пробные тесты под таймер."
            )

        with st.expander("ACT — Resources", expanded=True):
            render_resource_group("Official", [
                "[ACT Official Website](https://www.act.org/)",
                "[ACT Academy (free)](https://academy.act.org/)"
            ])
            render_resource_group("Paid & Courses", [
                "[Princeton Review ACT Prep](https://www.princetonreview.com/)",
                "[Kaplan ACT Test Prep](https://www.kaptest.com/act)",
                "[TestU ACT Tutoring](https://www.testuacademy.com/)"
            ])
            render_resource_group("Practice", [
                "[ACT Practice Tests](https://www.act.org/content/act/en/products-and-services/act-full-length-practice-tests.html)",
                "[Barron's ACT Tests](https://www.barronseduc.com/)"
            ])
            st.markdown("---")
            st.write("Добавить свой ресурс (URL или описание):")
            user_act = st.text_input("", key="prep_user_act")
            if st.button("Add ACT resource", key="prep_add_act"):
                if user_act.strip():
                    st.session_state.prep_user_resources["ACT"].append(user_act.strip())
                    st.success("Resource added.")
                else:
                    st.warning("Введите URL или описание ресурса.")
            if st.session_state.prep_user_resources["ACT"]:
                st.markdown("**Your ACT resources:**")
                for r in st.session_state.prep_user_resources["ACT"]:
                    st.markdown(f"- {r}")

# ---------------------------------------
# AI Advisor Tab
# ---------------------------------------
with tabs[6]:
    st.header("💡 AI Advisor — персональные советы")
    st.caption("Задай вопрос по профориентации, выбору вуза или подготовке к экзаменам.")

    profile = st.session_state.profile
    if not profile.get("gpa"):
        st.warning("⚠️ Сначала заполни профиль в табе 'Profile'.")
        st.stop()

    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    col_chat, col_info = st.columns([2, 1])

    with col_info:
        st.markdown("### 📋 Твой профиль")
        st.metric("GPA", profile.get("gpa", "—"))
        st.metric("Специальность", profile.get("major", "—"))
        st.metric("Активности (0–5)", profile.get("extras_level", "—"))

        exams = profile.get("exams", {})
        passed = len([x for x in exams.values() if x.get("status") == "Already taken"])
        st.metric("Сдано экзаменов", passed)

        if st.button("🔄 Очистить историю"):
            st.session_state.ai_messages = []
            st.success("История очищена.")
            st.rerun()

    with col_chat:
        st.markdown("### 💬 Чат")

        for msg in st.session_state.ai_messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_input = st.chat_input("Задай вопрос…")

        if user_input:
            st.session_state.ai_messages.append({"role": "user", "content": user_input})

            profile_summary = json.dumps(profile, ensure_ascii=False, indent=2)
            system_prompt = {
                "role": "system",
                "content": (
                    "Ты опытный консультант по поступлению в вузы. "
                    "Отвечай конкретно, ясно и полезно. "
                    "Пиши по-русски, если вопрос задан по-русски."
                ),
            }

            messages = [system_prompt] + st.session_state.ai_messages[-6:]
            messages[-1]["content"] = (
                f"Профиль студента:\n{profile_summary}\n\n"
                f"Вопрос: {messages[-1]['content']}"
            )

            try:
                with st.spinner("🤖 Думаю..."):
                    response = requests.post(
                        GROQ_API_URL,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": GROQ_MODEL,
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 900,
                        },
                        timeout=30,
                    )
                data = response.json()
                ai_text = data["choices"][0]["message"]["content"]
            except Exception as e:
                ai_text = f"❌ Ошибка при запросе к Groq: {e}"

            st.session_state.ai_messages.append(
                {"role": "assistant", "content": ai_text}
            )
            st.rerun()
