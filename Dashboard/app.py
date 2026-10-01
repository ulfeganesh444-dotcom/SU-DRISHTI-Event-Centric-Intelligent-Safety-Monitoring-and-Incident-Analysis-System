"""
SU-DRISHTI — Dark Glassmorphism Safety Dashboard (proper-working-project-5).

VISUAL redesign only. Structure, features, navigation targets, backend calls,
database schema and detection pipeline are preserved from avishkar4.
Backend runs through src/video_analysis.py (existing modules only).

Pages: Dashboard | Detection & Analysis | Upload Video | Live Webcam |
       Events / History | Analytics | Settings

Bug fix vs avishkar4: navigation state never writes to a widget key, so
clicking home-card buttons can no longer raise
StreamlitWidgetAlreadyInstantiatedError.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import (
    get_connection, init_db, get_db_path, update_event_status, clear_all_events,
)
from src.video_analysis import analyze_video

UPLOAD_DIR = PROJECT_ROOT / "videos" / "uploads"
ALLOWED_EXT = ["mp4", "avi", "mov", "mkv"]

st.set_page_config(page_title="SU-DRISHTI — Home Safety Dashboard",
                   page_icon=":shield:", layout="wide",
                   initial_sidebar_state="expanded")

# ----------------------------------------------------------- light theme ---
st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(900px 420px at 85% -5%, rgba(2,132,199,0.08), transparent 60%),
            radial-gradient(700px 380px at 10% 110%, rgba(37,99,235,0.06), transparent 60%),
            #F4F6FA;
        color: #1F2937;
    }
    html, body, [class*="css"] { font-family: 'Segoe UI', Arial, sans-serif; }
    h1, h2, h3, h4 { color: #0F172A !important; }
    .small-muted { color: #64748B; font-size: 13px; }
    .brand-name { font-size: 20px; font-weight: 800; color: #0F172A; }
    .brand-sub { font-size: 11px; color: #64748B; line-height: 1.35; }
    .glass {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 4px 12px rgba(15, 23, 42, 0.05);
    }
    .glass h4 { margin: 0 0 6px 0; font-size: 15px; color: #0F172A; }
    .stat-label { color: #64748B; font-size: 13px; }
    .stat-value { font-size: 34px; font-weight: 800; color: #0F172A; line-height: 1.1; }
    .delta-up-bad { color: #DC2626; font-size: 12px; font-weight: 700; }
    .delta-up-good { color: #15803D; font-size: 12px; font-weight: 700; }
    .delta-flat { color: #64748B; font-size: 12px; }
    .badge { display: inline-block; padding: 3px 12px; border-radius: 12px;
             font-size: 12px; font-weight: 700; white-space: nowrap; }
    .b-green { background: #E7F6EC; color: #15803D; border: 1px solid #BBE5C9; }
    .b-amber { background: #FDF3E2; color: #B45309; border: 1px solid #F0D9A8; }
    .b-orange { background: #FDEEE3; color: #C2410C; border: 1px solid #F3C39F; }
    .b-red { background: #FCECEC; color: #B91C1C; border: 1px solid #F0B8B8; }
    .b-blue { background: #E8F3FC; color: #0369A1; border: 1px solid #B9D9EF; }
    .b-gray { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
    .pill {
        display: inline-flex; align-items: center; gap: 8px;
        background: #FFFFFF; border: 1px solid #BFDBFE;
        border-radius: 10px; padding: 8px 16px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
    }
    .tl-time { font-family: monospace; font-weight: 700; color: #0284C7; }
    .pipe { font-family: monospace; font-size: 12.5px; color: #075985;
            background: #EFF6FF; border: 1px solid #BFDBFE;
            border-radius: 8px; padding: 10px 12px; }
    .legend-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
    section[data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    div[data-testid="stDataFrame"] { border: 1px solid #E2E8F0; border-radius: 10px; }
    .stButton > button { border-radius: 9px; }
    .stDownloadButton > button { border-radius: 9px; }
</style>
""", unsafe_allow_html=True)

RISK_BADGE = {"LOW": "b-green", "MEDIUM": "b-blue", "HIGH": "b-orange", "CRITICAL": "b-red"}
RISK_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
PAGES = ["Dashboard", "Detection & Analysis", "Upload Video", "Live Webcam",
         "Events / History", "Analytics", "Settings"]

ALERT_LABEL = {"person": "Person Detected", "intrusion": "Zone Breach Detected",
               "fall": "Possible Fall Detected", "fire": "Fire/Smoke Detected"}


def badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{text}</span>'


def risk_badge(risk: str) -> str:
    return badge(risk, RISK_BADGE.get(risk, "b-gray"))


# ------------------------------------------------------------- data access --
def load_history_df(limit: int = 1000) -> pd.DataFrame:
    init_db()
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM events ORDER BY id DESC LIMIT ?",
                               conn, params=(limit,))
    except Exception as e:
        st.error(f"Database query error: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()
    if not df.empty:
        if "risk_level" not in df.columns:
            df["risk_level"] = df.get("severity", "MEDIUM")
        df["risk_level"] = df["risk_level"].fillna("MEDIUM")
        for col, default in (("event_status", "CONFIRMED"), ("zone", "MONITORED"),
                             ("status", "NEW"), ("duration_sec", 0.0), ("notes", "")):
            if col not in df.columns:
                df[col] = default
            else:
                df[col] = df[col].fillna(default)
    return df


def video_meta(path: Path):
    cap = cv2.VideoCapture(str(path))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    s = int(n / fps) if fps else 0
    return f"{s // 60:02d}:{s % 60:02d}", n, round(fps, 1)


def delta_text(cur: int, prev: int):
    if prev <= 0:
        return ("new" if cur > 0 else "—", "delta-flat")
    pct = round(100.0 * (cur - prev) / prev)
    if pct == 0:
        return ("0%", "delta-flat")
    return (f"{pct:+d}%", "delta-up-bad" if pct > 0 else "delta-up-good")


# ------------------------------------------------------------------ sidebar --
with st.sidebar:
    st.markdown('<div style="display:flex;gap:10px;align-items:center;margin-bottom:4px;">'
                '<div style="width:42px;height:42px;border-radius:12px;background:#16233F;'
                'display:flex;align-items:center;justify-content:center;">'
                '<svg width="30" height="30" viewBox="0 0 42 42">'
                '<path d="M21 3 L35 9 V20 C35 30 28 36 21 39 C14 36 7 30 7 20 V9 Z" '
                'fill="#16233F" stroke="#C9A227" stroke-width="2"/>'
                '<path d="M12 20 Q21 12.5 30 20 Q21 27.5 12 20 Z" fill="#F8FAFC"/>'
                '<circle cx="21" cy="20" r="4.2" fill="#0D9488"/>'
                '<circle cx="21" cy="20" r="1.9" fill="#16233F"/>'
                '<circle cx="22.6" cy="18.4" r="0.9" fill="#FFFFFF"/>'
                "</svg></div>"
                '<div><div class="brand-name">SU-DRISHTI</div>'
                '<div class="brand-sub">See Beyond Vision,<br>Protect Beyond Detection.</div>'
                "</div></div>", unsafe_allow_html=True)
    st.markdown("")
    # Navigation: full-width buttons (active page highlighted blue).
    # No radio widget -> labels always render in native style, and there is
    # no widget key anyone could overwrite (crash fix preserved).
    st.session_state.setdefault("page", "Dashboard")
    if st.session_state.page not in PAGES:
        st.session_state.page = "Dashboard"
    for _p in PAGES:
        _label = _p + ("  (Soon)" if _p == "Live Webcam" else "")
        if st.button(_label, key=f"nav_{_p}", width="stretch",
                     type="primary" if _p == st.session_state.page else "secondary"):
            st.session_state.page = _p
            st.rerun()
    st.markdown("")
    st.markdown('<div class="glass" style="text-align:center;">'
                "<div style='font-size:15px;font-weight:800;color:#0F172A;'>Safer Homes<br>"
                "Smarter Tomorrow</div>"
                "<div class='small-muted'>Powered by AI</div></div>", unsafe_allow_html=True)

page = st.session_state.page


def goto(name: str):
    """Home-card navigation. Writes ONLY the non-widget 'page' key (crash fix)."""
    st.session_state.page = name
    st.rerun()


# ------------------------------------------------------- top status header --
df_all = load_history_df()
open_crit = 0 if df_all.empty else len(
    df_all[(df_all["risk_level"] == "CRITICAL") & (df_all["status"] != "RESOLVED")])
now = datetime.now()
h1, h2, h3 = st.columns([3, 1, 1])
with h1:
    st.markdown('<span class="pill"><span style="color:#15803D;font-size:16px;">&#9679;</span>'
                "<span><b style='color:#15803D;'>System Active</b><br>"
                "<span class='small-muted'>Detection pipeline ready</span></span></span>",
                unsafe_allow_html=True)
with h2:
    bell = f"&#128276; <span class='badge b-red'>{open_crit}</span>" if open_crit else "&#128276;"
    st.markdown(f"<div style='text-align:right;font-size:22px;'>{bell}</div>"
                f"<div class='small-muted' style='text-align:right;'>"
                f"{'open critical' if open_crit else 'no open critical'}</div>",
                unsafe_allow_html=True)
with h3:
    st.markdown(f"<div style='text-align:right;color:#475569;font-size:13px;'>"
                f"{now.strftime('%a, %d %b %Y')}<br>{now.strftime('%I:%M %p')}</div>",
                unsafe_allow_html=True)

WELCOME = "Operator"
st.markdown(f"## Welcome back, {WELCOME}")
st.markdown("<div style='color:#0369A1;font-weight:700;font-size:14px;'>"
            "See Beyond Vision, Protect Beyond Detection.</div>"
            "<div class='small-muted'>Here's what's happening with your home safety system today.</div>",
            unsafe_allow_html=True)
st.markdown("")


# ================================================================ DASHBOARD ==
if page == "Dashboard":
    total = len(df_all)
    incidents = 0 if df_all.empty else len(df_all[df_all["risk_level"].isin(["HIGH", "CRITICAL"])])
    avg_conf = 0.0 if df_all.empty else float(df_all["confidence"].mean())

    last7 = pd.DataFrame()
    prev7 = pd.DataFrame()
    if not df_all.empty:
        try:
            ts = pd.to_datetime(df_all["event_time"])
            last7 = df_all[ts >= (now - timedelta(days=7))]
            prev7 = df_all[(ts < (now - timedelta(days=7))) & (ts >= (now - timedelta(days=14)))]
            per_day = ts.dt.date.value_counts().sort_index()
        except Exception:
            per_day = pd.Series(dtype=int)
    else:
        per_day = pd.Series(dtype=int)

    d_total, c_total = delta_text(len(last7), len(prev7))
    d_inc, c_inc = delta_text(
        0 if last7.empty else len(last7[last7["risk_level"].isin(["HIGH", "CRITICAL"])]),
        0 if prev7.empty else len(prev7[prev7["risk_level"].isin(["HIGH", "CRITICAL"])]))

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(f'<div class="glass"><div class="stat-label">Total Detections</div>'
                    f'<div class="stat-value">{total}</div>'
                    f'<span class="{c_total}">{d_total}</span> '
                    f"<span class='small-muted'>vs. prior 7 days</span>", unsafe_allow_html=True)
        if len(per_day) >= 2:
            st.line_chart(per_day.tail(7), height=60, color="#0284C7")
    with s2:
        st.markdown(f'<div class="glass"><div class="stat-label">Incidents Detected</div>'
                    f'<div class="stat-value">{incidents}</div>'
                    f'<span class="{c_inc}">{d_inc}</span> '
                    f"<span class='small-muted'>vs. prior 7 days</span>", unsafe_allow_html=True)
        if not df_all.empty:
            hi = pd.to_datetime(df_all["event_time"],
                                errors="coerce").dt.date.value_counts().sort_index().tail(7)
            st.line_chart(df_all[df_all["risk_level"].isin(["HIGH", "CRITICAL"])]
                          .assign(d=pd.to_datetime(df_all["event_time"],
                                                   errors="coerce").dt.date)["d"]
                          .value_counts().sort_index().tail(7) if len(hi) else hi,
                          height=60, color="#DC2626")
    with s3:
        st.markdown(f'<div class="glass"><div class="stat-label">Detection Confidence (avg)</div>'
                    f'<div class="stat-value">{avg_conf:.0%}</div>'
                    f"<span class='small-muted'>mean model confidence</span>", unsafe_allow_html=True)
        if not df_all.empty:
            st.line_chart(df_all.sort_values("id")["confidence"].tail(20).reset_index(drop=True),
                          height=60, color="#15803D")
    with s4:
        dot = "#15803D" if open_crit == 0 else "#DC2626"
        state = "Online" if open_crit == 0 else "Attention"
        sub = "All systems running normally" if open_crit == 0 else f"{open_crit} open critical"
        st.markdown(f'<div class="glass"><div class="stat-label">System Status</div>'
                    f'<div class="stat-value">{state} '
                    f'<span style="color:{dot};font-size:18px;">&#9679;</span></div>'
                    f"<span class='small-muted'>{sub}</span>", unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left:
        st.markdown('<div class="glass"><h4>Detection Activity</h4>'
                    "<div class='small-muted'>Stored events per day</div>", unsafe_allow_html=True)
        rng = st.selectbox("Range", ["Last 7 Days", "Last 14 Days", "Last 30 Days"], key="act_rng")
        days = {"Last 7 Days": 7, "Last 14 Days": 14, "Last 30 Days": 30}[rng]
        try:
            import altair as alt
            if not df_all.empty:
                dd = pd.to_datetime(df_all["event_time"], errors="coerce")
                daily = dd.dt.date.value_counts().sort_index()
                idx = pd.date_range(end=now.date(), periods=days)
                series = pd.Series({d.date(): daily.get(d.date(), 0) for d in idx})
                chart_df = pd.DataFrame({"date": series.index.astype(str), "count": series.values})
            else:
                chart_df = pd.DataFrame({"date": [], "count": []})
            chart = (alt.Chart(chart_df).mark_area(point=True, opacity=0.35,
                                                   color="#0284C7",
                                                   line=alt.OverlayMarkDef(color="#0284C7"))
                     .encode(x=alt.X("date:O", title=None,
                                     axis=alt.Axis(labelColor="#5B6B7F", labelAngle=-30)),
                             y=alt.Y("count:Q", title=None,
                                     axis=alt.Axis(labelColor="#5B6B7F",
                                                   gridColor="rgba(148,163,184,0.15)")),
                             tooltip=["date", "count"])
                     .properties(height=260).configure_view(strokeWidth=0))
            st.altair_chart(chart)
        except Exception as e:
            st.caption(f"Chart unavailable: {e}")
            if not df_all.empty:
                st.bar_chart(per_day.tail(days))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass"><h4>Quick Access</h4>'
                    "<div class='small-muted'>Get started with key features</div>", unsafe_allow_html=True)
        q1, q2, q3 = st.columns(3)
        with q1:
            st.markdown("<b>Upload Video</b><div class='small-muted'>Analyze pre-recorded "
                        "videos for incidents</div>", unsafe_allow_html=True)
            if st.button("Open Upload", key="q_up"):
                goto("Upload Video")
        with q2:
            st.markdown("<b>Live Webcam</b> " + badge("Coming Soon", "b-amber") +
                        "<div class='small-muted'>Start real-time detection</div>",
                        unsafe_allow_html=True)
            if st.button("Open Live", key="q_live"):
                goto("Live Webcam")
        with q3:
            st.markdown("<b>Events / History</b><div class='small-muted'>View past detections "
                        "and incidents</div>", unsafe_allow_html=True)
            if st.button("Open History", key="q_hist"):
                goto("Events / History")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="glass"><h4>Recent Alerts</h4>', unsafe_allow_html=True)
        if df_all.empty:
            st.caption("No alerts yet. Analyze a video to populate this feed.")
        else:
            for _, row in df_all.head(4).iterrows():
                c1, c2, c3 = st.columns([1, 3, 1])
                with c1:
                    ip = PROJECT_ROOT / str(row["image_path"])
                    if ip.exists():
                        st.image(str(ip))
                with c2:
                    label = ALERT_LABEL.get(str(row["object_name"]),
                                            f"{str(row['object_name']).title()} Detected")
                    try:
                        tshort = pd.to_datetime(row["event_time"]).strftime("%I:%M %p")
                    except Exception:
                        tshort = str(row["event_time"])
                    st.markdown(f"**{label}**<div class='small-muted'>{row['zone']} · "
                                f"{tshort}</div>", unsafe_allow_html=True)
                with c3:
                    conf_pct = f"{float(row['confidence']):.0%}"
                    st.markdown(f"{badge(conf_pct, RISK_BADGE.get(row['risk_level'], 'b-gray'))}"
                                "<div class='small-muted'>Confidence</div>", unsafe_allow_html=True)
            if st.button("View All", key="view_all"):
                goto("Events / History")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass"><h4>Detection Summary</h4>', unsafe_allow_html=True)
        if df_all.empty:
            st.caption("Insufficient data.")
        else:
            try:
                import altair as alt
                grp = df_all["object_name"].value_counts()
                total_g = int(grp.sum())
                COLORS = {"person": "#0284C7", "fire": "#DC2626", "fall": "#EA580C",
                          "intrusion": "#7C3AED"}
                pie = pd.DataFrame({
                    "label": [g.title() for g in grp.index],
                    "count": grp.values,
                    "color": [COLORS.get(g, "#64748B") for g in grp.index]})
                donut = (alt.Chart(pie).mark_arc(innerRadius=58, outerRadius=88)
                         .encode(theta="count:Q",
                                 color=alt.Color("label:N", scale=None,
                                                 legend=None),
                                 tooltip=["label", "count"])
                         .properties(width=190, height=190).configure_view(strokeWidth=0))
                # altair scale=None needs explicit color field mapping:
                donut = (alt.Chart(pie).mark_arc(innerRadius=58, outerRadius=88)
                         .encode(theta="count:Q",
                                 color=alt.Color("color:N", scale=None, legend=None),
                                 tooltip=["label", "count"])
                         .properties(width=190, height=190).configure_view(strokeWidth=0))
                d1, d2 = st.columns([1, 1])
                with d1:
                    st.altair_chart(donut)
                    st.markdown(f"<div style='text-align:center;margin-top:-120px;"
                                f"margin-bottom:100px;'><b style='font-size:20px;'>{total_g}</b>"
                                f"<div class='small-muted'>Total</div></div>",
                                unsafe_allow_html=True)
                with d2:
                    for _, r in pie.iterrows():
                        pct = round(100.0 * r["count"] / total_g)
                        st.markdown(f"<span class='legend-dot' style='background:{r['color']};'>"
                                    f"</span>{r['label']} &nbsp;<b>{int(r['count'])}</b> "
                                    f"<span class='small-muted'>{pct}%</span>",
                                    unsafe_allow_html=True)
            except Exception as e:
                st.caption(f"Summary unavailable: {e}")
                st.bar_chart(df_all["object_name"].value_counts())
        st.markdown("</div>", unsafe_allow_html=True)


# =========================================== DETECTION & ANALYSIS / UPLOAD ==
def _uploader_block():
    st.markdown('<div class="glass"><h4>Upload Video</h4>', unsafe_allow_html=True)
    up = st.file_uploader("Choose safety video", type=ALLOWED_EXT, key="up5")
    if up is not None:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in up.name)
        sp = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe}"
        with open(sp, "wb") as f:
            f.write(up.getbuffer())
        st.session_state.video_path = str(sp)
        st.session_state.analysis = None
    st.markdown("</div>", unsafe_allow_html=True)


def _analysis_results():
    res = st.session_state.get("analysis")
    if not res:
        return
    s, incidents = res["summary"], res["incidents"]
    st.markdown('<div class="glass"><h4>Analysis Result</h4>', unsafe_allow_html=True)
    if incidents:
        top = max(incidents, key=lambda i: (RISK_RANK.get(i["risk_level"], 0), i["confidence"]))
        st.markdown(
            f"{badge('CONFIRMED INCIDENT', RISK_BADGE.get(top['risk_level'], 'b-gray'))}"
            f"<div style='font-size:22px;font-weight:800;margin:6px 0;'>"
            f"{top['event_type'].upper()} — {top['risk_level']}</div>"
            f"Confidence <b>{top['confidence']:.0%}</b> &nbsp;|&nbsp; "
            f"Video time <b>{top['video_time']}</b> &nbsp;|&nbsp; "
            f"Verification <b>{top['verification']}</b> &nbsp;|&nbsp; "
            f"Source <b>Uploaded Video</b> &nbsp;|&nbsp; Evidence <b>Captured</b> &nbsp;|&nbsp; "
            f"Alert <b>{'Email Sent' if top['alert_status'] == 'sent' else 'Not sent (' + top['alert_status'] + ')'}</b>",
            unsafe_allow_html=True)
    else:
        st.markdown(f"{badge('NO CONFIRMED INCIDENT', 'b-green')}"
                    f"<p>No confirmed safety incident was identified. Candidates observed: "
                    f"<b>{s['candidate_events']}</b>, dismissed: <b>{s['dismissed_candidates']}</b>.</p>",
                    unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="glass"><h4>Incident Timeline</h4>', unsafe_allow_html=True)
    for t in res["timeline"] or [{"time": "--", "event": "No timeline entries."}]:
        st.markdown(f"<span class='tl-time'>{t['time']}</span> &nbsp;{t['event']}",
                    unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if incidents:
        st.markdown('<div class="glass"><h4>Why This Event Was Flagged</h4>', unsafe_allow_html=True)
        labels = [f"#{i['db_id']} {i['event_type']} ({i['video_time']})" for i in incidents]
        sel = incidents[labels.index(st.selectbox("Incident", labels, key="why5"))]
        for text, ok in [
            (f"Confidence threshold reached ({sel['confidence']:.2f})", True),
            (f"Persistence threshold reached ({sel['persistence']}/{sel['required']} frames, "
             f"{sel['duration_sec']}s)", True),
            (f"Zone rule evaluated: {sel['zone']}"
             + (" (restricted-zone rule matched)" if sel["zone"] == "RESTRICTED" else ""), True),
            ("Verification completed (SUSPECTED → VERIFYING → CONFIRMED)", True),
            (f"Duplicate observations suppressed ({sel['suppressed_duplicates']})",
             sel["suppressed_duplicates"] > 0),
            ("Evidence captured and stored", (PROJECT_ROOT / sel["image_path"]).exists())]:
            st.markdown(f"<span style='color:{'#15803D' if ok else '#64748B'};'>"
                        f"{'&#9745;' if ok else '&#9744;'}</span> {text}", unsafe_allow_html=True)
        st.caption("Risk factors actually computed:")
        for r in sel["reasons"]:
            st.caption(f"— {r}")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass"><h4>Evidence</h4>', unsafe_allow_html=True)
        for i in incidents:
            with st.container(border=True):
                e1, e2 = st.columns([1, 2])
                with e1:
                    ip = PROJECT_ROOT / i["image_path"]
                    st.image(str(ip)) if ip.exists() else st.caption("Image missing")
                with e2:
                    st.markdown(f"**{i['event_type'].upper()}** {risk_badge(i['risk_level'])} "
                                f"{badge(i['verification'], 'b-gray')}", unsafe_allow_html=True)
                    st.caption(f"Video time {i['video_time']} | Confidence {i['confidence']:.2f} | "
                               f"Zone {i['zone']} | Duration {i['duration_sec']}s | "
                               f"Alert: {i['alert_status']}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="glass"><h4>Analysis Summary</h4>', unsafe_allow_html=True)
    m = st.columns(6)
    for col, v, lab in [(m[0], s["frames_analyzed"], "Frames"), (m[1], s["candidate_events"], "Candidates"),
                        (m[2], s["confirmed_incidents"], "Confirmed"), (m[3], s["high_risk"], "High-Risk"),
                        (m[4], s["critical"], "Critical"),
                        (m[5], f"{s['alert_reduction_pct']}%", "Alert Reduction")]:
        col.metric(lab, v)
    st.caption(f"Raw detections {s['raw_detections']} → stored {s['confirmed_incidents']} "
               f"({s['duplicates_suppressed']} suppressed, {s['dismissed_candidates']} dismissed) "
               f"in {s['processing_sec']}s.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.download_button("Download Analysis Report", data=res["report_md"].encode("utf-8"),
                       file_name=f"su_drishti_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                       mime="text/markdown", key="dl_rep5")
    if incidents:
        st.download_button("Download Incidents (CSV)",
                           data=pd.DataFrame(incidents).to_csv(index=False).encode("utf-8"),
                           file_name="su_drishti_incidents.csv", mime="text/csv", key="dl_csv5")


if page == "Upload Video":
    st.markdown("### Upload Video")
    st.markdown("<div class='small-muted'>Select a safety video, preview it, then continue to analysis.</div>",
                unsafe_allow_html=True)
    st.markdown("")
    _uploader_block()
    vp = st.session_state.get("video_path")
    if vp and Path(vp).exists():
        dur, nframes, fps = video_meta(Path(vp))
        st.markdown(f"**Selected:** `{Path(vp).name}` — {dur}, {nframes} frames @ {fps} fps")
        st.video(str(vp))
        if st.button("Continue to Analysis", type="primary", key="to_analysis"):
            goto("Detection & Analysis")


elif page == "Detection & Analysis":
    st.markdown("### Detection & Analysis")
    st.markdown("<div class='small-muted'>Run the verification pipeline on the selected video.</div>",
                unsafe_allow_html=True)
    st.markdown("")
    vp = st.session_state.get("video_path")
    if not (vp and Path(vp).exists()):
        st.markdown('<div class="glass">No video selected yet.</div>', unsafe_allow_html=True)
        if st.button("Go to Upload", key="go_up"):
            goto("Upload Video")
    else:
        dur, nframes, fps = video_meta(Path(vp))
        st.markdown(f"**Selected:** `{Path(vp).name}` — {dur}, {nframes} frames @ {fps} fps")
        st.video(str(vp))
        recip = st.text_input("Alert e-mail recipient (optional)",
                              value=st.session_state.get("alert_recipient",
                                                         os.getenv("SENTINEL_ALERT_RECIPIENT", "")),
                              placeholder="guard@example.com", key="ana_recip5")
        if recip:
            st.session_state.alert_recipient = recip
        if st.button("START AI ANALYSIS", type="primary", key="run5"):
            bar = st.progress(0.0)
            status = st.empty()

            def _cb(frac: float, text: str):
                bar.progress(min(1.0, max(0.0, frac)))
                status.caption(text)

            with st.spinner("Running detection, verification and risk analysis..."):
                try:
                    st.session_state.analysis = analyze_video(
                        str(vp), alert_recipient=st.session_state.get("alert_recipient") or None,
                        progress_cb=_cb)
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
                    st.session_state.analysis = None
            bar.progress(1.0)
            status.caption("Analysis complete.")
            st.rerun()
        _analysis_results()


# ================================================================ LIVE CAM ==
elif page == "Live Webcam":
    st.markdown("### Live Webcam")
    st.markdown('<div class="glass"><h4>Live Camera Monitoring</h4>'
                f"{badge('Coming Soon', 'b-amber')}"
                "<p>Real-time safety monitoring using webcam or camera input — "
                "applying the same detection, verification, context and risk pipeline.</p>"
                "</div>", unsafe_allow_html=True)
    if st.button("LIVE WEBCAM — COMING SOON", key="cam5"):
        st.info("Live camera monitoring is planned for the next development phase. "
                "The current prototype validates the safety-analysis pipeline using recorded video.")
    st.markdown('<div class="glass"><h4>Future-ready architecture</h4><div class="pipe">'
                "VIDEO FILE ─┐ → INPUT ADAPTER → SU-DRISHTI ENGINE "
                "(verify / risk / evidence) → ALERT ← LIVE CAMERA (future)</div>"
                "<p class='small-muted'>Recorded video validates the pipeline today; a live "
                "camera can supply frames through the same input adapter later.</p></div>",
                unsafe_allow_html=True)


# =========================================================== EVENTS/HISTORY ==
elif page == "Events / History":
    st.markdown("### Events / History")
    if df_all.empty:
        st.markdown('<div class="glass">No incidents recorded yet. Analyze a video first.</div>',
                    unsafe_allow_html=True)
    else:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            fr = st.selectbox("Risk", ["All"] + sorted(df_all["risk_level"].unique().tolist()), key="fr5")
        with f2:
            fe = st.selectbox("Event", ["All"] + sorted(df_all["object_name"].unique().tolist()), key="fe5")
        with f3:
            fz = st.selectbox("Zone", ["All"] + sorted(df_all["zone"].unique().tolist()), key="fz5")
        with f4:
            fs = st.selectbox("Status", ["All"] + sorted(df_all["status"].unique().tolist()), key="fs5")
        fdf = df_all.copy()
        if fr != "All":
            fdf = fdf[fdf["risk_level"] == fr]
        if fe != "All":
            fdf = fdf[fdf["object_name"] == fe]
        if fz != "All":
            fdf = fdf[fdf["zone"] == fz]
        if fs != "All":
            fdf = fdf[fdf["status"] == fs]

        st.markdown('<div class="glass"><h4>Recent Events</h4>', unsafe_allow_html=True)
        st.dataframe(fdf[["event_time", "object_name", "zone", "confidence",
                          "risk_level", "event_status", "status"]].rename(columns={
            "event_time": "Time", "object_name": "Event", "zone": "Zone",
            "confidence": "Confidence", "risk_level": "Risk",
            "event_status": "Verification", "status": "Operator Status"}), height=320)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass"><h4>Evidence</h4>', unsafe_allow_html=True)
        for _, row in fdf.head(10).iterrows():
            with st.container(border=True):
                e1, e2 = st.columns([1, 2])
                with e1:
                    ip = PROJECT_ROOT / str(row["image_path"])
                    st.image(str(ip)) if ip.exists() else st.caption("Image missing")
                with e2:
                    st.markdown(f"**#{row['id']} {str(row['object_name']).upper()}** "
                                f"{risk_badge(row['risk_level'])}", unsafe_allow_html=True)
                    st.caption(f"{row['event_time']} | Zone {row['zone']} | "
                               f"Conf {float(row['confidence']):.2f} | {row['event_status']}")
                    ns = st.selectbox("Operator status",
                                      ["ACKNOWLEDGED", "RESOLVED", "FALSE_ALARM"],
                                      key=f"op5_{row['id']}")
                    if st.button("Save", key=f"sv5_{row['id']}"):
                        update_event_status(int(row["id"]), ns, "")
                        st.success(f"Incident #{row['id']} → {ns}")
                        st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ================================================================ ANALYTICS ==
elif page == "Analytics":
    st.markdown("### Analytics")
    if df_all.empty:
        st.markdown('<div class="glass">Insufficient data for analytics.</div>',
                    unsafe_allow_html=True)
    else:
        try:
            import altair as alt

            def _dark_bar(series, color):
                d = pd.DataFrame({"k": series.index.astype(str), "v": series.values})
                return (alt.Chart(d).mark_bar(color=color, cornerRadius=4)
                        .encode(x=alt.X("k:O", title=None,
                                        axis=alt.Axis(labelColor="#5B6B7F", labelAngle=-25)),
                                y=alt.Y("v:Q", title=None,
                                        axis=alt.Axis(labelColor="#5B6B7F",
                                                      gridColor="rgba(148,163,184,0.15)")),
                                tooltip=["k", "v"])
                        .properties(height=240).configure_view(strokeWidth=0))

            a1, a2 = st.columns(2)
            with a1:
                st.markdown('<div class="glass"><h4>Events by Type</h4>', unsafe_allow_html=True)
                st.altair_chart(_dark_bar(df_all["object_name"].value_counts(), "#0284C7"))
                st.markdown("</div>", unsafe_allow_html=True)
            with a2:
                st.markdown('<div class="glass"><h4>Events by Risk</h4>', unsafe_allow_html=True)
                st.altair_chart(_dark_bar(df_all["risk_level"].value_counts(), "#DC2626"))
                st.markdown("</div>", unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            with b1:
                st.markdown('<div class="glass"><h4>Events by Zone</h4>', unsafe_allow_html=True)
                st.altair_chart(_dark_bar(df_all["zone"].value_counts(), "#7C3AED"))
                st.markdown("</div>", unsafe_allow_html=True)
            with b2:
                st.markdown('<div class="glass"><h4>Confirmed vs Other Verification</h4>',
                            unsafe_allow_html=True)
                st.altair_chart(_dark_bar(df_all["event_status"].value_counts(), "#15803D"))
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown('<div class="glass"><h4>Events Over Time</h4>', unsafe_allow_html=True)
            try:
                per = pd.to_datetime(df_all["event_time"]).dt.date.value_counts().sort_index()
                dd = pd.DataFrame({"d": per.index.astype(str), "v": per.values})
                st.altair_chart((alt.Chart(dd).mark_area(point=True, opacity=0.35,
                                                         color="#0284C7",
                                                         line=alt.OverlayMarkDef(color="#0284C7"))
                                 .encode(x=alt.X("d:O", title=None,
                                                 axis=alt.Axis(labelColor="#5B6B7F", labelAngle=-30)),
                                         y=alt.Y("v:Q", title=None,
                                                 axis=alt.Axis(labelColor="#5B6B7F",
                                                               gridColor="rgba(148,163,184,0.15)")))
                                 .properties(height=240).configure_view(strokeWidth=0)))
            except Exception:
                st.caption("Could not parse timestamps.")
            st.markdown("</div>", unsafe_allow_html=True)
        except Exception as e:
            st.caption(f"Charts unavailable: {e}")
        last = st.session_state.get("analysis")
        if last:
            s = last["summary"]
            st.markdown(f'<div class="glass">Last analysis: {s["candidate_events"]} candidates → '
                        f"{s['confirmed_incidents']} confirmed, {s['dismissed_candidates']} dismissed "
                        f"({s['alert_reduction_pct']}% alert reduction).</div>", unsafe_allow_html=True)


# ================================================================= SETTINGS ==
else:
    st.markdown("### Settings")
    st.markdown('<div class="glass"><h4>Alert E-mail</h4>', unsafe_allow_html=True)
    sr = st.text_input("Recipient", value=st.session_state.get(
        "alert_recipient", os.getenv("SENTINEL_ALERT_RECIPIENT", "")),
        placeholder="guard@example.com", key="set_recip5")
    if sr:
        st.session_state.alert_recipient = sr
    smtp_ready = bool(os.getenv("SENTINEL_SENDER_EMAIL") and os.getenv("SENTINEL_SENDER_PASS"))
    st.caption("SMTP sender: " + ("configured (from environment)"
                                  if smtp_ready else "not configured — alerts will be simulated"))
    st.caption("Passwords are never stored in code; use environment variables.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="glass"><h4>Pipeline</h4>', unsafe_allow_html=True)
    st.caption(f"Model file: {'found' if (PROJECT_ROOT / 'models' / 'yolov8n.pt').exists() else 'MISSING'} "
               "(models/yolov8n.pt)")
    st.caption("Verification: SUSPECTED → VERIFYING → CONFIRMED (+ dismissed candidates)")
    st.caption("Risk: LOW / MEDIUM / HIGH / CRITICAL (project-defined)")
    st.caption(f"Database: `{get_db_path().name}`")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="glass"><h4>Maintenance</h4>', unsafe_allow_html=True)
    if st.button("Clear all events (fresh demo)", key="clr5"):
        n = clear_all_events()
        st.success(f"Cleared {n} record(s).")
        st.rerun()
    st.caption("Research prototype for assisted monitoring — not a replacement for "
               "professional emergency systems.")
    st.markdown("</div>", unsafe_allow_html=True)
