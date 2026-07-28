import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import os
import re
import json
import time
from collections import Counter
from dotenv import load_dotenv

try:
    from streamlit_local_storage import LocalStorage
    _ls = LocalStorage()
    LOCAL_STORAGE_OK = True
except Exception:
    _ls = None
    LOCAL_STORAGE_OK = False

FAV_STORAGE_KEY = "termai_favorites_v1"
HIST_STORAGE_KEY = "termai_history_v1"

# =====================================================================
# إعداد الصفحة
# =====================================================================
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

st.set_page_config(
    page_title="TechWiki",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

SUGGESTIONS = ["HTML", "CSS", "JavaScript", "Python", "API", "REST API", "JSON", "SQL", "Machine Learning"]

TERMS_CATALOG = {
    "🧑‍💻 لغات البرمجة": [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "Go", "Rust",
        "Kotlin", "Swift", "PHP", "Ruby", "Dart", "R", "MATLAB", "Scala", "Perl", "Lua",
    ],
    "🌐 تطوير الويب": [
        "HTML", "CSS", "React", "Vue.js", "Angular", "Next.js", "Node.js", "Django",
        "Flask", "Express.js", "Tailwind CSS", "Bootstrap", "WebSocket", "REST API",
        "GraphQL", "AJAX", "DOM", "SPA", "Webpack", "SSR", "PWA", "jQuery",
    ],
    "🗄️ قواعد البيانات": [
        "SQL", "NoSQL", "MongoDB", "MySQL", "PostgreSQL", "Redis", "Firebase",
        "SQLite", "ORM", "Database Indexing", "ACID", "Data Normalization",
        "Stored Procedure", "Database Schema",
    ],
    "🤖 الذكاء الاصطناعي وتعلم الآلة": [
        "Machine Learning", "Deep Learning", "Neural Network", "NLP", "Computer Vision",
        "LLM", "Transformer", "Generative AI", "Reinforcement Learning", "Data Mining",
        "Chatbot", "Prompt Engineering", "Overfitting", "Supervised Learning",
        "Unsupervised Learning", "TensorFlow", "PyTorch",
    ],
    "☁️ الحوسبة السحابية و DevOps": [
        "Cloud Computing", "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes",
        "Serverless", "CI/CD", "DevOps", "Microservices", "Load Balancer", "CDN",
        "Virtual Machine", "API Gateway", "Container",
    ],
    "🔐 أمن المعلومات": [
        "Cybersecurity", "Encryption", "Firewall", "VPN", "Phishing", "Malware",
        "SQL Injection", "Two-Factor Authentication", "SSL/TLS", "Penetration Testing",
        "DDoS Attack", "Zero-Day Vulnerability", "Hashing",
    ],
    "📊 علم البيانات": [
        "Big Data", "Data Science", "Data Analysis", "Pandas", "NumPy",
        "Data Visualization", "ETL", "Data Warehouse", "Business Intelligence",
        "Data Cleaning", "Regression",
    ],
    "🧩 هياكل البيانات والخوارزميات": [
        "Algorithm", "Data Structure", "Array", "Linked List", "Stack", "Queue",
        "Binary Tree", "Hash Table", "Recursion", "Big O Notation",
        "Sorting Algorithm", "Graph", "Dynamic Programming",
    ],
    "📡 الشبكات": [
        "Networking", "IP Address", "DNS", "HTTP", "HTTPS", "TCP/IP", "Router",
        "Bandwidth", "Latency", "Proxy Server", "Port",
    ],
    "⚙️ مفاهيم عامة": [
        "Git", "GitHub", "Version Control", "JSON", "XML", "IDE", "Compiler",
        "Debugging", "Framework", "Library", "Open Source", "Agile", "Unit Testing",
        "UI/UX", "Operating System", "API", "Software Architecture",
    ],
}
SECTION_ICONS = {"1": "🧠", "2": "🎯", "3": "💻", "4": "🚀"}
NAV_ITEMS = [
    ("home", None, "الرئيسية"),
    ("history", None, "السجل"),
    ("favorites", None, "المفضلة"),
    ("terms", None, "المصطلحات"),
    ("settings", "⚙️", "الإعدادات"),
]

# =====================================================================
# حالة الجلسة
# =====================================================================
_DEFAULTS = {
    "theme": "dark",
    "page": "home",
    "history": [],
    "favorites": [],
    "current_result": None,
    "last_click_time": 0,
    "_fav_loaded_from_ls": False,
    "_fav_load_attempts": 0,
    "_fav_save_ctr": 0,
    "_hist_loaded_from_ls": False,
    "_hist_load_attempts": 0,
    "_hist_save_ctr": 0,
    "theme_radio_side": "dark",
    "theme_radio_settings": "dark",
    "theme_radio_mobile": "dark",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------------------------------------------------------------
# حفظ المفضلة في Local Storage الخاص بالمتصفح (لكل مستخدم/متصفح خصوصيته)
# ---------------------------------------------------------------------
def load_favorites_from_local_storage():
    """يقرأ المفضلة من Local Storage مرة واحدة عند بداية الجلسة.
    نظرًا لطبيعة المكوّن غير المتزامنة، قد تحتاج القيمة الحقيقية لجولة
    تحديث إضافية (rerun) قبل أن تظهر، لذلك نعيد المحاولة عدة مرات قبل
    الاستسلام بافتراض أن لا يوجد مفضلات محفوظة أصلاً."""
    if not LOCAL_STORAGE_OK or st.session_state["_fav_loaded_from_ls"]:
        return
    try:
        raw = _ls.getItem(FAV_STORAGE_KEY)
    except Exception:
        st.session_state["_fav_loaded_from_ls"] = True
        return

    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                st.session_state.favorites = data
            st.session_state["_fav_loaded_from_ls"] = True
        except Exception:
            st.session_state["_fav_loaded_from_ls"] = True
    else:
        st.session_state["_fav_load_attempts"] += 1
        if st.session_state["_fav_load_attempts"] > 5:
            st.session_state["_fav_loaded_from_ls"] = True


def save_favorites_to_local_storage():
    if not LOCAL_STORAGE_OK:
        return
    try:
        st.session_state["_fav_save_ctr"] += 1
        _ls.setItem(
            FAV_STORAGE_KEY,
            json.dumps(st.session_state.favorites, ensure_ascii=False),
            key=f"ls_save_fav_{st.session_state['_fav_save_ctr']}",
        )
    except Exception:
        pass


load_favorites_from_local_storage()


# ---------------------------------------------------------------------
# حفظ السجل في Local Storage الخاص بالمتصفح (نفس منطق المفضلة تمامًا)
# ---------------------------------------------------------------------
def load_history_from_local_storage():
    """يقرأ السجل من Local Storage مرة واحدة عند بداية الجلسة."""
    if not LOCAL_STORAGE_OK or st.session_state["_hist_loaded_from_ls"]:
        return
    try:
        raw = _ls.getItem(HIST_STORAGE_KEY)
    except Exception:
        st.session_state["_hist_loaded_from_ls"] = True
        return

    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, list):
                st.session_state.history = data
            st.session_state["_hist_loaded_from_ls"] = True
        except Exception:
            st.session_state["_hist_loaded_from_ls"] = True
    else:
        st.session_state["_hist_load_attempts"] += 1
        if st.session_state["_hist_load_attempts"] > 5:
            st.session_state["_hist_loaded_from_ls"] = True


def save_history_to_local_storage():
    if not LOCAL_STORAGE_OK:
        return
    try:
        st.session_state["_hist_save_ctr"] += 1
        _ls.setItem(
            HIST_STORAGE_KEY,
            json.dumps(st.session_state.history, ensure_ascii=False),
            key=f"ls_save_hist_{st.session_state['_hist_save_ctr']}",
        )
    except Exception:
        pass


load_history_from_local_storage()


def _sync_theme_from_sidebar():
    st.session_state.theme = st.session_state.theme_radio_side
    st.session_state.theme_radio_settings = st.session_state.theme_radio_side
    st.session_state.theme_radio_mobile = st.session_state.theme_radio_side


def _sync_theme_from_settings():
    st.session_state.theme = st.session_state.theme_radio_settings
    st.session_state.theme_radio_side = st.session_state.theme_radio_settings
    st.session_state.theme_radio_mobile = st.session_state.theme_radio_settings


def _sync_theme_from_mobile():
    st.session_state.theme = st.session_state.theme_radio_mobile
    st.session_state.theme_radio_side = st.session_state.theme_radio_mobile
    st.session_state.theme_radio_settings = st.session_state.theme_radio_mobile


def trigger_new_search(term):
    """يعبّئ مربع البحث ويشغّل بحثًا فعليًا جديدًا (اقتراحات / صفحة المصطلحات).
    لا يمكن تعديل st.session_state.term_input مباشرة بعد إنشاء العنصر (widget) في
    نفس الجولة، لذلك نستخدم متغيّرًا وسيطًا (pending_term) يُطبَّق في بداية
    الجولة التالية قبل إنشاء مربع البحث."""
    st.session_state.pending_term = term
    st.session_state.trigger_search = True
    st.session_state.page = "home"
    st.rerun()


def show_existing_result(entry):
    """يعيد عرض شرح محفوظ مسبقًا من السجل أو المفضلة بدون استدعاء الـ API من جديد."""
    st.session_state.current_result = entry
    st.session_state.pending_term = entry["term"]
    st.session_state.page = "home"
    st.rerun()


# =====================================================================
# الألوان حسب الثيم
# =====================================================================
THEMES = {
    "dark": dict(
        bg="#0B0C17", bg_elev="#131526", bg_elev2="#1A1D33",
        text="#F5F5F7", text_muted="#A1A1AA", border="rgba(255,255,255,.08)",
        card_bg="linear-gradient(180deg, rgba(19,21,38,0.92), rgba(19,21,38,0.78))",
        input_bg="rgba(19,21,38,0.65)", grid_op="0.035", blob_op="0.28", shadow="rgba(0,0,0,0.45)",
    ),
    "light": dict(
        bg="#F3F4FA", bg_elev="#FFFFFF", bg_elev2="#F3F1FC",
        text="#15161F", text_muted="#5B5E6E", border="rgba(20,20,40,.09)",
        card_bg="linear-gradient(180deg, rgba(255,255,255,0.97), rgba(255,255,255,0.88))",
        input_bg="rgba(255,255,255,0.85)", grid_op="0.05", blob_op="0.16", shadow="rgba(60,60,110,0.12)",
    ),
}
T = THEMES[st.session_state.theme]
ACTIVE_PAGE = st.session_state.page

# =====================================================================
# CSS — تصميم Premium AI SaaS
# =====================================================================
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

    :root {{
        --bg: {T['bg']};
        --bg-elev: {T['bg_elev']};
        --bg-elev2: {T['bg_elev2']};
        --accent: #F5A524;
        --accent-soft: rgba(245,165,36,0.15);
        --violet: #8B5CF6;
        --violet-soft: rgba(139,92,246,0.16);
        --violet-glow: rgba(139,92,246,0.45);
        --blue: #4F8CFF;
        --text: {T['text']};
        --text-muted: {T['text_muted']};
        --border: {T['border']};
        --shadow: {T['shadow']};
    }}

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'Tajawal', sans-serif !important;
        font-size: 18px !important;
    }}
    .block-container p, .block-container li, .block-container span {{ font-size: 1rem; }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    #MainMenu, footer {{ visibility: hidden; }}

    /* ملاحظة: كل تنسيقات أزرار طي/فتح القائمة الجانبية (للوضعين الفاتح
       والداكن) وتخطيط الشريط للجوال/سطح المكتب موجودة بكتلة واحدة نظيفة
       في نهاية الملف — راجعها هناك بدل البحث في أكثر من مكان. */
    * {{ direction: rtl; text-align: right; }}

    .block-container {{ padding-top: 2.2rem; max-width: min(900px, 92vw); width: 100%; margin: 0 auto; position: relative; z-index: 1; }}

    /* ---------- خلفية حية ---------- */
    .bg-fx {{ position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none; }}
    .bg-fx .grid {{
        position: absolute; inset: 0;
        background-image:
            linear-gradient(rgba(139,92,246,{T['grid_op']}) 1px, transparent 1px),
            linear-gradient(90deg, rgba(139,92,246,{T['grid_op']}) 1px, transparent 1px);
        background-size: 42px 42px;
        mask-image: radial-gradient(ellipse 70% 60% at 50% 10%, #000 30%, transparent 90%);
    }}
    .bg-fx .blob {{ position: absolute; width: 420px; height: 420px; border-radius: 50%; filter: blur(110px); opacity: {T['blob_op']}; }}
    .bg-fx .blob-1 {{ background: var(--violet); top: -140px; right: -100px; }}
    .bg-fx .blob-2 {{ background: var(--blue); bottom: -160px; left: -120px; }}
    .bg-fx .blob-3 {{ background: var(--accent); top: 40%; left: 45%; opacity: 0.10; }}
    .bg-fx .dot {{ position: absolute; width: 3px; height: 3px; border-radius: 50%; background: var(--violet);
        box-shadow: 0 0 6px 1px var(--violet); animation: floatDot 9s ease-in-out infinite; opacity: 0.6; }}
    .bg-fx .dot:nth-child(4) {{ top: 15%; left: 20%; animation-delay: 0s; }}
    .bg-fx .dot:nth-child(5) {{ top: 30%; left: 75%; background: var(--blue); box-shadow: 0 0 6px 1px var(--blue); animation-delay: 2s; }}
    .bg-fx .dot:nth-child(6) {{ top: 65%; left: 15%; background: var(--accent); box-shadow: 0 0 6px 1px var(--accent); animation-delay: 4s; }}
    .bg-fx .dot:nth-child(7) {{ top: 75%; left: 65%; animation-delay: 1s; }}
    .bg-fx .dot:nth-child(8) {{ top: 50%; left: 85%; background: var(--blue); box-shadow: 0 0 6px 1px var(--blue); animation-delay: 3s; }}
    @keyframes floatDot {{ 0%,100% {{ transform: translateY(0) translateX(0); opacity:.3; }} 50% {{ transform: translateY(-18px) translateX(8px); opacity:.9; }} }}

    @keyframes fadeIn {{ from {{ opacity:0; transform: translateY(-8px); }} to {{ opacity:1; transform: translateY(0); }} }}
    @keyframes slideUpFade {{ from {{ opacity:0; transform: translateY(22px); }} to {{ opacity:1; transform: translateY(0); }} }}

    /* ملاحظة: قواعد إرساء الشريط الجانبي على اليمين (order) وسلوك الجوال
       (تراكب/hamburger) موجودة في كتلة <style> مُحقنة في نهاية الملف عمدًا
       — لأن Streamlit يولّد CSS الخاص بالشريط الجانبي وقت رندره الفعلي
       (قرب نهاية السكربت)، فحقن قواعدنا مبكرًا هنا يجعلها تُهزم في
       التعادل بين أنماط !important. راجع نهاية الملف. */

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, var(--bg-elev), var(--bg)) !important;
        border-left: 1px solid var(--border);
    }}
    section[data-testid="stSidebar"] .block-container {{ padding-top: 1.6rem; max-width: 100%; }}
    .brand {{ font-size: 1.6rem; font-weight: 900; color: var(--text); display:flex; gap:.5rem; align-items:center; }}
    .brand span {{ background: linear-gradient(90deg, var(--violet), var(--accent)); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }}
    .brand-sub {{ color: var(--text-muted); font-size: .95rem; margin-bottom: .5rem; }}
    .nav-spacer {{ height: 1px; background: var(--border); margin: 1rem 0; }}
    .theme-label, .panel-title, .page-title {{ font-weight: 800; color: var(--text); }}
    .theme-label {{ font-size: 1rem; color: var(--text-muted); margin-bottom: .2rem; }}
    .sidebar-stats {{ display:flex; flex-direction:column; gap:.4rem; font-size:1rem; color: var(--text-muted); font-family:'JetBrains Mono',monospace; }}

    section[data-testid="stSidebar"] div[data-testid="stButton"] button {{
        background: transparent !important;
        color: var(--text) !important;
        border: 1px solid transparent !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-family: 'Tajawal', sans-serif !important;
        font-size: 1.1rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        padding: .75rem .9rem !important;
        box-shadow: none !important;
        transition: all .2s ease;
        width: 100% !important;
    }}
    /* عمود العنصر داخل الزر (أيقونة + نص) — نفس تخطيط اللابتوب تمامًا،
       فقط نغيّر المقاسات بالإعلام (media query) لا البنية. */
    section[data-testid="stSidebar"] div[data-testid="stButton"] button > div[data-testid="stMarkdownContainer"] {{
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: .65rem !important;
        width: 100% !important;
        overflow: hidden !important;
    }}
    /* الأيقونة: عرض ثابت دائمًا كي تتحاذى كل الأسطر رأسيًا مع بعضها */
    section[data-testid="stSidebar"] div[data-testid="stButton"] button [data-testid^="stIcon"] {{
        flex: 0 0 auto !important;
        width: 1.5rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.15rem !important;
        line-height: 1 !important;
    }}
    /* النص: يتمدد في المساحة المتبقية، بدون التفاف، ومحاذاة رأسية للوسط */
    section[data-testid="stSidebar"] div[data-testid="stButton"] button p {{
        flex: 1 1 auto !important;
        margin: 0 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        text-align: right !important;
        line-height: 1.2 !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {{
        background: var(--violet-soft) !important;
        transform: translateX(-2px);
    }}
    .st-key-navwrap_{ACTIVE_PAGE} div[data-testid="stButton"] button {{
        background: var(--violet-soft) !important;
        border: 1px solid var(--violet) !important;
        box-shadow: 0 0 18px var(--violet-glow) !important;
        color: var(--violet) !important;
    }}

    /* ---------- عناوين الصفحات ---------- */
    .page-title {{ font-size: 2rem; margin-bottom: .3rem; animation: fadeIn .5s ease; }}
    .page-sub {{ color: var(--text-muted); margin-bottom: 1.2rem; font-size: 1.1rem; }}
    .empty-state {{ color: var(--text-muted); background: var(--bg-elev); border: 1px dashed var(--border); border-radius: 16px; padding: 2rem; text-align:center; }}

    /* ---------- Hero ---------- */
    .term-hero {{ border-bottom: 1px solid var(--border); padding-bottom: 1.3rem; margin-bottom: 1.6rem; animation: fadeIn .6s ease; }}
    .term-eyebrow {{ font-family:'JetBrains Mono',monospace; color: var(--accent); font-size:1rem; letter-spacing:.12em; direction:ltr; text-align:right; text-shadow: 0 0 12px rgba(245,165,36,.5); }}
    .term-title {{ font-weight:900; font-size:2.8rem; margin:.4rem 0 .4rem 0;
        background: linear-gradient(90deg, var(--text) 20%, var(--violet) 75%, var(--blue) 100%);
        -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
        filter: drop-shadow(0 0 22px rgba(139,92,246,.3)); }}
    .term-sub {{
        color: var(--text);
        font-size: 1.3rem;
        font-weight: 700;
        line-height: 1.6;
        max-width: 46rem;
        opacity: .92;
    }}

    /* ---------- مربع البحث ---------- */
    div[data-testid="stTextInput"] {{ position: relative; padding-bottom: 1.4rem; box-sizing: border-box; }}
    div[data-testid="stTextInput"] label {{ color: var(--text-muted) !important; font-size:.9rem; }}
    div[data-testid="stTextInput"] > div {{ position: relative; width: 100%; box-sizing: border-box; }}
    div[data-testid="stTextInput"] input {{
        background-color: var(--input-bg, {T['input_bg']}) !important;
        backdrop-filter: blur(10px);
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 18px !important;
        padding: 1.15rem 3.4rem 1.15rem 1.3rem !important;
        font-family:'JetBrains Mono',monospace !important;
        font-size: 1.2rem !important;
        caret-color: var(--violet) !important;
        width: 100% !important;
        box-sizing: border-box !important;
        transition: border-color .2s ease, box-shadow .2s ease;
    }}
    div[data-testid="stTextInput"] input:focus {{
        border-color: var(--violet) !important;
        box-shadow: 0 0 0 4px var(--violet-soft) !important;
    }}
    /* أيقونة البحث الزخرفية: تُترك مساحة كافية لها ضمن padding الحقل نفسه
       (padding-right أعلاه) بحيث لا يصل إليها نص المستخدم المكتوب مطلقًا،
       وتُرسم فوق الحقل فقط بلا أي تفاعل (pointer-events: none). */
    div[data-testid="stTextInput"]::after {{
        content: "🔍"; position:absolute; top: 2.55rem; right: 1.2rem; font-size:1.15rem; opacity:.55; pointer-events:none; z-index: 2;
    }}
    /* تلميح Streamlit الأصلي "Press Enter to apply": هذا العنصر يأتي من
       Streamlit نفسه (لا من كودنا)، وكان يُرسم فوق نص الإدخال والأيقونة
       مسبّبًا التداخل. الحل الجذري هو نقله بالكامل خارج صندوق الحقل إلى
       سطر مستقل أسفله (لا فوقه ولا فوق الأيقونة)، مع حجز مساحة كافية له
       عبر padding-bottom في الحاوية الأم أعلاه، بدل إخفائه بالقص/overflow. */
    div[data-testid="stTextInput"] div[data-testid="InputInstructions"] {{
        position: absolute !important;
        top: 100% !important;
        bottom: auto !important;
        right: .2rem !important;
        left: auto !important;
        margin-top: .3rem !important;
        max-width: calc(100% - .4rem);
        text-align: right !important;
        direction: rtl !important;
        font-family: 'Tajawal', sans-serif !important;
        font-size: .72rem !important;
        color: var(--text-muted) !important;
        opacity: .85 !important;
        white-space: normal !important;
        pointer-events: none;
        z-index: 1;
    }}
    div[data-testid="stTextInput"] div[data-testid="InputInstructions"] * {{
        color: inherit !important;
        font-size: inherit !important;
        visibility: visible !important;
    }}

    /* ---------- زر اشرح لي ---------- */
    div[data-testid="stButton"] button {{
        background: var(--bg-elev2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-family:'Tajawal',sans-serif !important;
        transition: transform .2s ease, box-shadow .2s ease, background-position .4s ease, border-color .2s ease;
    }}
    div[data-testid="stButton"] button:hover {{
        border-color: var(--violet) !important;
        color: var(--violet) !important;
        box-shadow: 0 0 14px var(--violet-soft);
    }}
    div[data-testid="stButton"] button p {{ color: inherit !important; }}
    .st-key-main_search_btn div[data-testid="stButton"] button, div[data-testid="stButton"] button#main_search {{ }}
    .st-key-search_btn_wrap div[data-testid="stButton"] button {{
        background: linear-gradient(135deg, var(--violet), var(--accent)) !important;
        background-size: 170% 170% !important;
        color: #fff !important;
        border: none !important;
        padding: 1rem 1.8rem !important;
        font-size: 1.25rem !important;
        width: 100%;
    }}
    .st-key-search_btn_wrap div[data-testid="stButton"] button:hover {{
        transform: translateY(-3px) scale(1.01);
        box-shadow: 0 10px 30px rgba(139,92,246,.4), 0 0 30px rgba(245,165,36,.25);
        background-position: 100% 0 !important;
    }}
    .st-key-search_btn_wrap div[data-testid="stButton"] button:active {{ transform: translateY(-1px) scale(.99); }}

    /* أزرار الاقتراحات / المصطلحات */
    .st-key-suggestions_panel div[data-testid="stButton"] button,
    .st-key-terms_grid div[data-testid="stButton"] button {{
        background: var(--bg-elev2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        padding: .65rem .8rem !important;
        margin-bottom: .5rem;
    }}
    /* ---------- Accordion (المصطلحات) ---------- */
    div[data-testid="stExpander"] {{
        background: var(--bg-elev) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        overflow: hidden;
        margin-bottom: .6rem;
    }}
    div[data-testid="stExpander"] summary {{
        background: var(--bg-elev) !important;
        color: var(--text) !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        padding: .9rem 1.1rem !important;
        transition: background .2s ease, color .2s ease;
    }}
    div[data-testid="stExpander"] summary:hover {{
        background: var(--violet-soft) !important;
        color: var(--violet) !important;
    }}
    div[data-testid="stExpander"] summary[aria-expanded="true"],
    div[data-testid="stExpander"] details[open] > summary {{
        background: var(--violet-soft) !important;
        color: var(--violet) !important;
        border-bottom: 1px solid var(--border) !important;
    }}
    div[data-testid="stExpander"] summary svg {{ fill: currentColor !important; }}
    div[data-testid="stExpanderDetails"] {{
        background: var(--bg-elev) !important;
        color: var(--text) !important;
        padding: .9rem 1rem !important;
    }}
    div[data-testid="stExpander"] p,
    div[data-testid="stExpander"] span,
    div[data-testid="stExpander"] label {{
        color: var(--text) !important;
    }}
    .st-key-suggestions_panel div[data-testid="stButton"] button:hover,
    .st-key-terms_grid div[data-testid="stButton"] button:hover {{
        border-color: var(--violet) !important;
        color: var(--violet) !important;
        box-shadow: 0 0 14px var(--violet-soft);
        transform: translateY(-2px);
    }}

    /* ---------- لوحات عامة (Panels) ---------- */
    .st-key-result_panel, .st-key-suggestions_panel, .st-key-stats_panel, .st-key-settings_panel {{
        background: {T['card_bg']} !important;
        border: 1px solid var(--border) !important;
        border-radius: 20px !important;
        padding: 1.7rem 1.9rem !important;
        margin-top: 1.4rem !important;
        box-shadow: 0 0 0 1px rgba(139,92,246,.06), 0 20px 50px var(--shadow), 0 0 40px rgba(139,92,246,.06);
        animation: slideUpFade .5s cubic-bezier(.2,.8,.2,1);
        transition: box-shadow .25s ease;
    }}
    .st-key-result_panel {{ border-right: 3px solid var(--violet) !important; }}
    .st-key-result_panel:hover, .st-key-stats_panel:hover {{ box-shadow: 0 0 0 1px rgba(139,92,246,.14), 0 20px 50px var(--shadow), 0 0 55px rgba(139,92,246,.14); }}

    .panel-title {{ font-size: 1.4rem; margin-bottom: 1rem; color: var(--text); }}
    .result-head {{ font-size: 1.7rem; font-weight: 800; color: var(--violet); margin-bottom: 1.1rem; }}

    /* ---------- أقسام النتيجة ---------- */
    .sec-num {{
        width: 40px; height: 40px; border-radius: 10px;
        background: linear-gradient(135deg, var(--violet), var(--blue));
        color: #fff; display:flex; align-items:center; justify-content:center;
        font-weight: 800; font-family:'JetBrains Mono',monospace; font-size: 1.1rem;
        box-shadow: 0 0 16px var(--violet-glow);
        margin-top: .1rem;
    }}
    .sec-title {{ font-size: 1.5rem; font-weight: 800; color: var(--violet); padding-top: .3rem; }}
    .sec-divider {{ height: 1px; background: var(--border); margin: 1.2rem 0; }}

    .st-key-result_panel p, .st-key-result_panel li {{ color: var(--text) !important; line-height: 2.05; font-size: 1.15rem; }}
    .st-key-result_panel code {{
        background: var(--violet-soft) !important; color: var(--violet) !important;
        padding: .15rem .4rem; border-radius: 5px; font-family:'JetBrains Mono',monospace !important;
    }}

    /* ---------- بلوك الكود VS Code Style ---------- */
    .code-tab {{
        display:flex; align-items:center; justify-content:space-between;
        background:#151822; border:1px solid var(--border); border-bottom:none;
        border-radius: 12px 12px 0 0; padding:.55rem 1rem; margin-top: .6rem; direction: ltr;
    }}
    .code-dots {{ color:#5b5f73; letter-spacing:3px; font-size:.7rem; }}
    .code-lang {{ font-family:'JetBrains Mono',monospace; color: var(--accent); font-size:.78rem; letter-spacing:.05em; }}
    div[data-testid="stCode"] {{
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
        margin-top: -1px !important;
        overflow: hidden;
        box-shadow: 0 10px 30px var(--shadow);
    }}
    div[data-testid="stCode"] pre {{ background:#0D0D14 !important; }}

    /* ---------- إحصائيات ---------- */
    .stat-box {{ background: var(--bg-elev2); border:1px solid var(--border); border-radius:14px; padding:1rem .6rem; text-align:center; transition: all .2s ease; }}
    .stat-box:hover {{ border-color: var(--violet); box-shadow: 0 0 16px var(--violet-soft); transform: translateY(-2px); }}
    .stat-num {{ font-size: 2rem; font-weight:900; color: var(--violet); font-family:'JetBrains Mono',monospace; }}
    .stat-num-sm {{ font-size: 1.1rem; font-weight:800; color: var(--violet); overflow-wrap:anywhere; }}
    .stat-label {{ font-size:.9rem; color: var(--text-muted); margin-top:.3rem; }}

    /* ---------- السجل / المفضلة ---------- */
    .st-key-hist_item_0, .st-key-hist_item_1, .st-key-hist_item_2 {{}}
    div[data-testid="stVerticalBlockBorderWrapper"] {{}}
    .hist-term, .fav-head {{ font-weight:700; font-size:1.02rem; color: var(--text); padding-top:.4rem; }}
    .hist-time {{ color: var(--text-muted); font-family:'JetBrains Mono',monospace; font-size:.8rem; padding-top:.55rem; }}
    .fav-term {{ color: var(--text-muted); font-weight:500; font-size:.85rem; }}

    [class*="st-key-hist_item_"], [class*="st-key-fav_item_"] {{
        background: var(--bg-elev) !important; border:1px solid var(--border) !important;
        border-radius: 14px !important; padding: .8rem 1.1rem !important; margin-bottom: .7rem !important;
        animation: slideUpFade .4s ease; transition: all .2s ease;
    }}
    [class*="st-key-hist_item_"]:hover, [class*="st-key-fav_item_"]:hover {{
        border-color: var(--violet) !important; box-shadow: 0 0 16px var(--violet-soft);
    }}

    /* ---------- شاشة التحميل ---------- */
    .ai-loading {{ display:flex; align-items:center; gap:.8rem; background: var(--bg-elev); border:1px solid var(--border);
        border-radius:16px; padding:1rem 1.3rem; margin-top:1rem; backdrop-filter: blur(8px); }}
    .ai-loading-icon {{ font-size:1.4rem; animation: pulseIcon 1.4s ease-in-out infinite; }}
    @keyframes pulseIcon {{ 0%,100% {{ transform:scale(1); filter: drop-shadow(0 0 4px var(--violet)); }} 50% {{ transform:scale(1.18); filter: drop-shadow(0 0 12px var(--violet)); }} }}
    .ai-loading-text {{ position:relative; height:1.5rem; flex:1; font-family:'JetBrains Mono',monospace; font-size:.92rem; color: var(--text-muted); }}
    .ai-loading-text span {{ position:absolute; inset:0; opacity:0; animation: cycleFade 4.8s ease-in-out infinite; }}
    .ai-loading-text span:nth-child(1) {{ animation-delay:0s; }}
    .ai-loading-text span:nth-child(2) {{ animation-delay:1.2s; }}
    .ai-loading-text span:nth-child(3) {{ animation-delay:2.4s; }}
    .ai-loading-text span:nth-child(4) {{ animation-delay:3.6s; }}
    @keyframes cycleFade {{ 0% {{ opacity:0; transform:translateY(6px); }} 6% {{ opacity:1; transform:translateY(0); }} 20% {{ opacity:1; }} 26% {{ opacity:0; transform:translateY(-6px); }} 100% {{ opacity:0; }} }}

    /* ---------- Toggle (المظهر) ---------- */
    div[data-testid="stRadio"] label p,
    div[data-testid="stRadio"] label span,
    div[data-testid="stRadio"] div[data-testid="stWidgetLabel"] p {{
        color: var(--text) !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stToggle"] label p {{ color: var(--text) !important; font-weight:600; }}

    /* =====================================================================
       دعم الجوال — الشريط الجانبي مخفي افتراضيًا، ويظهر كطبقة منبثقة
       (overlay) من اليمين عند فتحه عبر زر الهامبرغر (☰)، بدل ما يبقى محجوز
       مساحته دائمًا كما كان سابقًا. تفاصيل التراكب الفعلية (position:fixed
       عند aria-expanded=true) موجودة بالكتلة المتأخرة آخر الملف لضمان
       فوزها في ترتيب الحقن. هنا فقط مقاسات محتوى الشريط عند فتحه —
       بما إنه صار عرضه العادي (~280-300px) مو شريط أيقونات ضيق، لا داعي
       لتصغير الخط بشكل قوي كالسابق. */
    @media (max-width: 768px) {{
        html, body {{ overflow-x: hidden !important; }}

        section[data-testid="stSidebar"] .block-container {{
            padding: 1rem .9rem !important;
        }}
        section[data-testid="stSidebar"] .brand {{
            font-size: 1.15rem !important;
        }}

        /* المحتوى الرئيسي يستخدم باقي المساحة تلقائيًا */
        .block-container {{
            padding-left: clamp(.6rem, 3vw, .9rem) !important;
            padding-right: clamp(.6rem, 3vw, .9rem) !important;
            padding-top: clamp(.7rem, 3vw, 1rem) !important;
        }}

        /* ---------- شبكة عمودين لكل الأقسام (اقتراحات / إحصائيات / مصطلحات) ----------
           سبب فشل flex-wrap سابقًا: Streamlit يفرض flex-direction: column تلقائيًا
           على div[data-testid="stHorizontalBlock"] بالشاشات الضيقة، فنجبر
           flex-direction: row صراحة هنا فوق سلوكه الافتراضي. */
        .st-key-suggestions_panel div[data-testid="stHorizontalBlock"],
        .st-key-stats_panel div[data-testid="stHorizontalBlock"],
        .st-key-terms_grid div[data-testid="stHorizontalBlock"] {{
            flex-direction: row !important;
            flex-wrap: wrap !important;
            row-gap: clamp(.4rem, 2vw, .6rem) !important;
            column-gap: clamp(.4rem, 2vw, .6rem) !important;
        }}
        .st-key-suggestions_panel div[data-testid="stHorizontalBlock"] > div,
        .st-key-stats_panel div[data-testid="stHorizontalBlock"] > div,
        .st-key-terms_grid div[data-testid="stHorizontalBlock"] > div {{
            flex: 0 0 47% !important;
            width: 47% !important;
            min-width: 47% !important;
            box-sizing: border-box !important;
        }}
        .st-key-terms_grid div[data-testid="stButton"] button {{
            height: 100%;
            min-height: clamp(2.6rem, 11vw, 3.1rem);
        }}

        /* ---------- عنوان المصطلح والصفحة ---------- */
        .term-hero {{ padding-bottom: clamp(.7rem, 3vw, .9rem); margin-bottom: clamp(.9rem, 4vw, 1.1rem); }}
        .term-title {{ font-size: clamp(1.2rem, 6.5vw, 1.6rem) !important; line-height: 1.25 !important; }}
        .term-sub {{ font-size: clamp(.82rem, 3.6vw, .95rem) !important; font-weight: 700 !important; line-height: 1.55 !important; max-width: 100% !important; }}
        .term-eyebrow {{ font-size: clamp(.68rem, 2.6vw, .76rem) !important; }}
        .page-title {{ font-size: clamp(1.1rem, 5vw, 1.3rem) !important; }}
        .page-sub {{ font-size: clamp(.76rem, 3.2vw, .85rem) !important; margin-bottom: clamp(.7rem, 3vw, .9rem) !important; }}
        .empty-state {{ padding: clamp(1rem, 4.5vw, 1.3rem) !important; font-size: clamp(.8rem, 3.4vw, .9rem) !important; }}

        /* ---------- مربع البحث ---------- */
        div[data-testid="stTextInput"] {{
            padding-bottom: clamp(1.3rem, 6vw, 1.6rem) !important;
        }}
        div[data-testid="stTextInput"] input {{
            padding: clamp(.6rem, 2.8vw, .8rem) clamp(2.3rem, 9vw, 2.9rem) clamp(.6rem, 2.8vw, .8rem) clamp(.7rem, 3.4vw, .9rem) !important;
            font-size: clamp(.82rem, 3.2vw, .95rem) !important;
            border-radius: 14px !important;
        }}
        div[data-testid="stTextInput"]::after {{
            top: clamp(1.75rem, 6.5vw, 2.05rem) !important;
            right: clamp(.8rem, 3.2vw, 1rem) !important;
            font-size: clamp(.9rem, 3.2vw, 1rem) !important;
        }}
        div[data-testid="stTextInput"] div[data-testid="InputInstructions"] {{
            font-size: clamp(.62rem, 2.8vw, .7rem) !important;
            margin-top: clamp(.2rem, 1.2vw, .3rem) !important;
            right: .15rem !important;
        }}

        /* ---------- زر اشرح لي ---------- */
        .st-key-search_btn_wrap div[data-testid="stButton"] button {{
            padding: clamp(.65rem, 2.8vw, .8rem) clamp(.9rem, 4vw, 1.2rem) !important;
            font-size: clamp(.88rem, 3.4vw, 1rem) !important;
        }}

        /* ---------- أزرار الاقتراحات / المصطلحات ---------- */
        .st-key-suggestions_panel div[data-testid="stButton"] button,
        .st-key-terms_grid div[data-testid="stButton"] button {{
            font-size: clamp(.78rem, 3.2vw, .88rem) !important;
            padding: clamp(.45rem, 2.2vw, .55rem) clamp(.5rem, 2.6vw, .65rem) !important;
        }}

        /* ---------- Accordion (المصطلحات) ---------- */
        div[data-testid="stExpander"] summary {{
            font-size: clamp(.85rem, 3.6vw, .95rem) !important;
            padding: clamp(.55rem, 2.6vw, .7rem) clamp(.7rem, 3.2vw, .9rem) !important;
        }}
        div[data-testid="stExpanderDetails"] {{
            padding: clamp(.6rem, 2.8vw, .75rem) clamp(.65rem, 3vw, .8rem) !important;
        }}

        /* ---------- اللوحات العامة (نتيجة الشرح / السجل / المفضلة / الإحصائيات) ---------- */
        .st-key-result_panel, .st-key-suggestions_panel, .st-key-stats_panel, .st-key-settings_panel {{
            padding: clamp(.85rem, 4vw, 1.15rem) clamp(.7rem, 3.4vw, .95rem) !important;
            margin-top: clamp(.75rem, 3.2vw, 1rem) !important;
            border-radius: 16px !important;
            box-sizing: border-box !important;
        }}
        .panel-title {{ font-size: clamp(.95rem, 4vw, 1.1rem) !important; margin-bottom: .6rem !important; }}
        .result-head {{ font-size: clamp(1.05rem, 4.6vw, 1.25rem) !important; margin-bottom: .7rem !important; }}

        /* ---------- أقسام النتيجة ---------- */
        .sec-num {{
            width: clamp(28px, 7vw, 34px) !important; height: clamp(28px, 7vw, 34px) !important;
            font-size: clamp(.8rem, 3.2vw, .92rem) !important;
        }}
        .sec-title {{ font-size: clamp(.95rem, 4vw, 1.1rem) !important; }}
        .sec-divider {{ margin: clamp(.6rem, 2.8vw, .85rem) 0 !important; }}
        .st-key-result_panel p, .st-key-result_panel li {{
            font-size: clamp(.82rem, 3.4vw, .92rem) !important;
            line-height: 1.8 !important;
        }}

        /* ---------- بلوك الكود — قابل للتمرير الأفقي بدل ما يكسر الصفحة ---------- */
        .code-tab {{ padding: clamp(.35rem, 1.8vw, .5rem) clamp(.55rem, 2.6vw, .8rem) !important; }}
        .code-lang {{ font-size: clamp(.64rem, 2.6vw, .74rem) !important; }}
        div[data-testid="stCode"] {{
            overflow-x: auto !important;
            max-width: 100% !important;
            -webkit-overflow-scrolling: touch;
        }}
        div[data-testid="stCode"] pre, div[data-testid="stCode"] code {{
            font-size: clamp(.72rem, 2.8vw, .82rem) !important;
            white-space: pre !important;
        }}

        /* ---------- الصور — تتقلص مع الشاشة دائمًا ---------- */
        .block-container img {{ max-width: 100% !important; height: auto !important; }}

        /* ---------- إحصائيات ---------- */
        .stat-box {{ padding: clamp(.55rem, 2.6vw, .75rem) clamp(.3rem, 1.6vw, .45rem) !important; border-radius: 12px !important; }}
        .stat-num {{ font-size: clamp(1.15rem, 5.4vw, 1.5rem) !important; }}
        .stat-num-sm {{ font-size: clamp(.78rem, 3.2vw, .9rem) !important; }}
        .stat-label {{ font-size: clamp(.66rem, 2.8vw, .76rem) !important; }}

        /* ---------- السجل / المفضلة ---------- */
        .hist-term, .fav-head {{ font-size: clamp(.82rem, 3.4vw, .92rem) !important; }}
        .hist-time {{ font-size: clamp(.64rem, 2.6vw, .72rem) !important; }}
        .fav-term {{ font-size: clamp(.72rem, 3vw, .8rem) !important; }}
    }}
    </style>

    <div class="bg-fx">
        <div class="grid"></div>
        <div class="blob blob-1"></div>
        <div class="blob blob-2"></div>
        <div class="blob blob-3"></div>
        <div class="dot"></div><div class="dot"></div><div class="dot"></div>
        <div class="dot"></div><div class="dot"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# منطق الذكاء الاصطناعي (Groq) — بدون أي تغيير في المنطق
# =====================================================================
if not api_key:
    st.error("⚠️ لم يتم العثور على مفتاح API. تأكد من ملف .env (المتغير GROQ_API_KEY)")
    st.stop()

client = Groq(api_key=api_key)


def generate_with_retry(client, model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            is_last_attempt = attempt == max_retries - 1
            if ("503" in str(e) or "429" in str(e)) and not is_last_attempt:
                time.sleep(3 * (attempt + 1))
                continue
            raise e


def contains_forbidden_language(text):
    forbidden_patterns = [
        r'[\u0400-\u04FF]',  # Cyrillic (Russian...)
        r'[\u4E00-\u9FFF]',  # Chinese
        r'[\u3040-\u30FF]',  # Japanese
        r'[\uAC00-\uD7AF]',  # Korean
        r'[\u0E00-\u0E7F]',  # Thai
        r'[\u0900-\u097F]',  # Devanagari (Hindi...)
        r'[\u0590-\u05FF]',  # Hebrew
        r'[\u0370-\u03FF]',  # Greek
        r'[\u0530-\u058F]',  # Armenian
        r'[\u10A0-\u10FF]',  # Georgian
        r'[\u1780-\u17FF]',  # Khmer
        r'[\u1000-\u109F]',  # Myanmar
        r'[\u0E80-\u0EFF]',  # Lao
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, text):
            return True
    vietnamese_chars = "ăâđêôơưắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    text_lower = text.lower()
    for ch in vietnamese_chars:
        if ch in text_lower:
            return True
    return False


def strip_forbidden_words(text):
    """إجراء أخير: إزالة أي كلمة تحتوي على حرف من لغة غير مسموحة، لضمان
    عدم ظهور خليط لغات في الشرح النهائي حتى لو فشلت كل محاولات إعادة التوليد."""
    cleaned_words = [w for w in text.split() if not contains_forbidden_language(w)]
    cleaned = " ".join(cleaned_words)
    cleaned = re.sub(r"\s+([:.,،؛؟!])", r"\1", cleaned)
    return cleaned


LOADING_HTML = """
<div class="ai-loading">
    <div class="ai-loading-icon">🧠</div>
    <div class="ai-loading-text">
        <span>🧠 تحليل المصطلح...</span>
        <span>📚 البحث في المعرفة...</span>
        <span>⚡ توليد الشرح...</span>
        <span>✨ تنسيق الإجابة...</span>
    </div>
</div>
"""


def run_search(term):
    now = time.time()
    if now - st.session_state.last_click_time < 10:
        st.warning("⏳ انتظر ثواني بسيطة قبل الطلب التالي.")
        return
    st.session_state.last_click_time = now

    loading_placeholder = st.empty()
    loading_placeholder.markdown(LOADING_HTML, unsafe_allow_html=True)

    prompt = f"""أنت خبير علوم حاسب ومترجم تقني متخصص، تشرح المصطلحات التقنية لطالب علوم حاسب باللغة العربية الفصحى الأكاديمية، بدقة علمية وبأسلوب طبيعي غير حرفي في الترجمة.

المصطلح: {term}

قبل الكتابة، نفّذ داخليًا (بدون أن تُظهر هذه الخطوة في الإجابة):
- حدّد أولاً المجال التقني الدقيق لهذا المصطلح تحديدًا (برمجة، ذكاء اصطناعي/تعلم آلة، قواعد بيانات، شبكات، أمن معلومات، أنظمة تشغيل، تطوير ويب، هندسة برمجيات، بنى بيانات وخوارزميات، حوسبة سحابية...) وتأكد من فهمك الصحيح والدقيق للمفهوم نفسه قبل شرحه.
- إذا كان هذا المصطلح يُشبه أو يُشتبه بمصطلح آخر قريب منه (مثل: Process مقابل Thread، Authentication مقابل Authorization، Compiler مقابل Interpreter، Stack مقابل Queue، Encryption مقابل Hashing، إلخ)، ميّز شرحك بوضوح عن ذلك المصطلح القريب، ولا تعطِ تعريفًا عامًا يصلح لأي منهما.
- اختر الترجمة العربية الصحيحة والمتعارف عليها أكاديميًا لهذا المصطلح تحديدًا، لا ترجمة حرفية كلمة بكلمة. مثال على الخطأ المرفوض: ترجمة "Data Format" حرفيًا إلى "تعبير عن البيانات"؛ والصحيح الطبيعي هو "تنسيق لتمثيل البيانات". طبّق هذا المبدأ على أي مصطلح آخر: اسأل نفسك ما هو المعنى التقني الفعلي المقصود، ثم عبّر عنه بعربية تقنية سليمة ومتداولة، لا بترجمة آلية للكلمات.

قواعد المصطلحات (الأهم لدقة الشرح):
- استخدم المصطلح العربي التقني الصحيح والشائع أكاديميًا، لا صياغة مرتجلة أو غير مألوفة.
- عند الحاجة أو عند احتمال اللبس في الترجمة العربية، أضِف المصطلح الإنجليزي الأصلي بين قوسين بعد أول ذكر للترجمة العربية، مثل: "التوابع الاشتقاقية (Recursion)". لا تضع القوسين إذا كانت الترجمة واضحة تمامًا ولا لبس فيها.
- التزم بنفس المصطلح العربي المختار لنفس المفهوم في كل أجزاء الشرح؛ لا تستخدم أكثر من ترجمة عربية للمفهوم نفسه داخل الإجابة الواحدة.
- لا تخترع أي حقيقة تقنية أو رقمًا أو خاصية غير مؤكدة عن المصطلح؛ إن لم تكن متأكدًا من تفصيل ما، اذكر فقط ما هو مؤكد ومعروف عن المفهوم دون تخمين.
- عدّل صياغة كل قسم بما يلائم طبيعة هذا المصطلح تحديدًا (هل هو لغة برمجة، مفهوم نظري، بروتوكول، خوارزمية، أداة، هجوم أمني...)؛ ممنوع استخدام نفس القالب اللغوي العام لكل المصطلحات (مثل تكرار نفس الجمل الافتتاحية أو نفس نوع التشبيه لكل شيء).

قواعد إلزامية بخصوص اللغة:
- اللغتان المسموحتان في هذا النص هما العربية الفصحى والإنجليزية فقط. أي أبجدية ثالثة (روسية، صينية، يابانية، كورية، فيتنامية، تايلاندية، هندية، عبرية، يونانية، أو أي لغة غير العربية والإنجليزية) ممنوعة منعًا باتًا في كل النص، بلا أي استثناء، حتى لو كانت كلمة واحدة أو حرفًا واحدًا.
- خارج أسوار الكود (code block)، يجب أن يكون النص عربيًا فصيحًا 100%، باستثناء الحالات التالية فقط بالإنجليزية: اسم المصطلح نفسه، أو اسم لغة برمجة/مكتبة/تقنية معروفة (مثل Python أو CSS)، أو المصطلح الإنجليزي الموضوع بين قوسين توضيحًا للترجمة، وتُكتب ككلمة إنجليزية مستقلة كاملة بمسافة قبلها وبعدها، لا مدمجة أو مصرّفة مع أحرف عربية.
- ممنوع كتابة أي جمع أو صفة أو فعل عربي ملتصق مباشرة بكلمة إنجليزية بلا مسافة (مثل: كلمة+ًا ملتصقة بكلمة إنجليزية، أو "tags HTML"، أو "Sites"). إذا احتاج الأمر صفة لكلمة إنجليزية، استخدم "وسوم HTML" مثلاً بدل "HTML tags"، وترجم كل صفة أو حال إلى عربي كامل.
- قبل تسليم الإجابة النهائية، راجع كل كلمة كتبتها كلمة كلمة، وتأكد أن كل كلمة إما عربية فصيحة أو إنجليزية مصرّح بها ضمن الاستثناءات أعلاه، وأنه لا توجد أي كلمة من أي لغة ثالثة؛ إن وُجدت أي كلمة مخالفة أعد صياغة الجملة بالكامل قبل الإخراج النهائي.

قواعد الإيجاز:
- كل نقطة من النقاط 1، 2، 4 لا تتجاوز جملتين قصيرتين (حد أقصى تقريبي 30 كلمة للنقطة الواحدة). ممنوع الحشو أو التكرار.
- في النقطة 3، جملة الشرح بعد الكود لا تتجاوز جملة واحدة قصيرة ومباشرة.

قواعد التنسيق:
- لا تكتب أي مقدمة أو تمهيد قبل النقطة الأولى. ابدأ مباشرة بالعنوان "1. التعريف المبسط".
- التزم بالترقيم والعناوين التالية بالضبط بدون إضافة أو حذف:

1. التعريف المبسط: تعريف علمي دقيق ومختصر جدًا، بالمصطلح العربي الصحيح المتفق عليه للمفهوم، مميّزًا عن أي مفهوم مشابه له.
2. مثال من الحياة الواقعية: تشبيه واحد مختصر يقرّب المفهوم للذهن، ويعكس الخاصية التقنية الفعلية للمصطلح لا تشبيهًا عامًا فضفاضًا.
3. نظرة سريعة: قرر أولاً هل المصطلح له صياغة برمجية (Syntax) فعلية (لغة برمجة، مكتبة، أمر، دالة...). إذا كان كذلك، أعطِ مقطع كود قصيرًا (٢-٤ أسطر) داخل code block، صحيحًا نحويًا (Syntax سليم فعليًا) ويوضّح المصطلح تحديدًا لا مثالًا عامًا عن البرمجة، متبوعًا مباشرة بجملة واحدة قصيرة تشرح ماذا يفعل هذا الكود تحديدًا. إذا لم يكن للمصطلح صياغة برمجية، أعطِ بدلاً من الكود مثالاً تطبيقيًا عمليًا واضحًا وموجزًا جدًا بلا كود، يوضّح فعليًا كيفية عمل المفهوم لا وصفًا عامًا له.
4. أين يُستخدم هذا المصطلح فعليًا؟ تطبيق أو مجال حقيقي واحد أو اثنان فقط، بدقة لا بعبارات فضفاضة، ومرتبط تحديدًا بهذا المصطلح لا بمجاله التقني العام.

خلّ الشرح منظمًا ومختصرًا وعلميًا دون إخلال بالدقة، متسق المصطلحات، خاليًا من الترجمة الحرفية غير الطبيعية، ومراجَعًا لغويًا وتقنيًا بالكامل قبل الإخراج."""

    try:
        response = generate_with_retry(client, "llama-3.3-70b-versatile", prompt)
        result_text = response.choices[0].message.content

        retry_note = """
تنبيه مهم جدًا:
الإجابة السابقة احتوت على لغة غير مسموحة.
أعد كتابة الإجابة كاملة من البداية.
استخدم العربية الفصحى والإنجليزية فقط.
لا تستخدم أي حرف واحد من الروسية أو الصينية أو اليابانية أو الكورية أو الفيتنامية أو التايلاندية أو الهندية أو العبرية أو اليونانية أو أي لغة أخرى غير العربية والإنجليزية.
راجع كل كلمة حرفًا حرفًا قبل إرسال الإجابة.
"""
        attempts = 0
        while contains_forbidden_language(result_text) and attempts < 2:
            response = generate_with_retry(client, "llama-3.3-70b-versatile", prompt + retry_note)
            result_text = response.choices[0].message.content
            attempts += 1

        if contains_forbidden_language(result_text):
            # إجراء أخير: إزالة أي كلمة متبقية من لغة غير مسموحة بدل إظهار خليط لغات للمستخدم
            result_text = strip_forbidden_words(result_text)

        loading_placeholder.empty()
        entry = {"term": term, "text": result_text, "ts": time.strftime("%H:%M — %d/%m")}
        st.session_state.history.insert(0, entry)
        save_history_to_local_storage()
        st.session_state.current_result = entry
    except Exception as e:
        loading_placeholder.empty()
        st.error("⚠️ صار خطأ أثناء الاتصال بالـ API.")
        st.exception(e)


# =====================================================================
# عرض النتيجة بتنسيق الأقسام الاحترافي
# =====================================================================
def parse_sections(text):
    pattern = re.compile(r'(?m)^\s*(\d+)\.\s*([^:\n]+):\s*')
    matches = list(pattern.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append({"num": m.group(1), "title": m.group(2).strip(), "content": text[start:end].strip()})
    if not sections:
        sections = [{"num": "1", "title": "الشرح", "content": text.strip()}]
    return sections


def render_code_block(code, lang):
    lang = lang or "python"
    st.markdown(
        f'<div class="code-tab"><span class="code-dots">●●●</span><span class="code-lang">{lang}</span></div>',
        unsafe_allow_html=True,
    )
    st.code(code.strip("\n"), language=lang)


def render_section_content(content):
    code_pattern = re.compile(r"```(\w*)\n?(.*?)```", re.DOTALL)
    last_end = 0
    for m in code_pattern.finditer(content):
        pre = content[last_end:m.start()].strip()
        if pre:
            st.markdown(pre)
        render_code_block(m.group(2), m.group(1))
        last_end = m.end()
    tail = content[last_end:].strip()
    if tail:
        st.markdown(tail)


def render_sections_only(text):
    """يعرض كل أقسام الشرح (التعريف، المثال، النظرة السريعة، الاستخدام) دون زر حفظ."""
    sections = parse_sections(text)
    for idx, sec in enumerate(sections):
        icon = SECTION_ICONS.get(sec["num"], "📌")
        c_num, c_title = st.columns([0.9, 9])
        with c_num:
            st.markdown(f'<div class="sec-num">{sec["num"]}</div>', unsafe_allow_html=True)
        with c_title:
            st.markdown(f'<div class="sec-title">{icon} {sec["title"]}</div>', unsafe_allow_html=True)
        render_section_content(sec["content"])
        if idx < len(sections) - 1:
            st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)


def render_result(term, text):
    """يعرض الشرح الكامل مع زر واحد لحفظ الصفحة كاملة (كل الأقسام) في المفضلة."""
    c_title, c_bm = st.columns([9, 1])
    with c_title:
        st.markdown(f'<div class="result-head">📖 {term}</div>', unsafe_allow_html=True)
    with c_bm:
        already_saved = any(f["term"] == term for f in st.session_state.favorites)
        if st.button("🔖" if not already_saved else "✅", key=f"bm_full_{term}",
                     help="حفظ الشرح كاملاً في المفضلة" if not already_saved else "محفوظ بالفعل"):
            if not already_saved:
                st.session_state.favorites.insert(0, {"term": term, "text": text})
                save_favorites_to_local_storage()
                st.toast("⭐ تم حفظ الشرح كاملاً في المفضلة")
    render_sections_only(text)


# =====================================================================
# الشريط الجانبي
# =====================================================================
def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="brand">🖥️ <span>TechWiki</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-sub">Learn Technical Terms with AI</div>', unsafe_allow_html=True)
        st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)

        for key, icon, label in NAV_ITEMS:
            with st.container(key=f"navwrap_{key}"):
                btn_kwargs = {"key": f"navbtn_{key}", "use_container_width": True}
                if icon:
                    btn_kwargs["icon"] = icon
                if st.button(label, **btn_kwargs):
                    st.session_state.page = key
                    st.rerun()

        st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)
        st.markdown('<div class="theme-label">المظهر</div>', unsafe_allow_html=True)
        st.radio(
            "المظهر", options=["dark", "light"],
            format_func=lambda v: "🌙 داكن" if v == "dark" else "☀️ فاتح",
            key="theme_radio_side", on_change=_sync_theme_from_sidebar,
            horizontal=True, label_visibility="collapsed",
        )

        st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""<div class="sidebar-stats">
                <div>🔎 {len(st.session_state.history)} عملية بحث</div>
                <div>⭐ {len(st.session_state.favorites)} عنصر محفوظ</div>
            </div>""",
            unsafe_allow_html=True,
        )


def page_home():
    if "pending_term" in st.session_state:
        st.session_state.term_input = st.session_state.pop("pending_term")

    st.markdown(
        """
        <div class="term-hero">
            <div class="term-eyebrow">// TECHWIKI</div>
            <div class="term-title">🖥️ TechWiki</div>
            <div class="term-sub">اكتب أي مصطلح تقني، وسيشرحه لك الذكاء الاصطناعي بالعربي مع أمثلة توضيحية.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    term = st.text_input("اكتب المصطلح هنا 👇", key="term_input", placeholder="مثال: Machine Learning")

    with st.container(key="search_btn_wrap"):
        clicked = st.button("اشرح لي 🚀", key="main_search")

    trigger = st.session_state.pop("trigger_search", False)
    if (clicked or trigger) and term.strip():
        run_search(term.strip())

    if st.session_state.current_result:
        with st.container(key="result_panel"):
            render_result(st.session_state.current_result["term"], st.session_state.current_result["text"])

    with st.container(key="suggestions_panel"):
        st.markdown('<div class="panel-title">💡 اقتراحات للمصطلحات</div>', unsafe_allow_html=True)
        cols = st.columns(3)
        for i, t in enumerate(SUGGESTIONS):
            with cols[i % 3]:
                if st.button(t, key=f"sugg_{i}", use_container_width=True):
                    trigger_new_search(t)

    hist = st.session_state.history
    most_searched = Counter([h["term"] for h in hist]).most_common(1)[0][0] if hist else "—"
    last_search = hist[0]["term"] if hist else "—"
    with st.container(key="stats_panel"):
        st.markdown('<div class="panel-title">📊 إحصائيات سريعة</div>', unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f'<div class="stat-box"><div class="stat-num">{len(hist)}</div><div class="stat-label">عمليات البحث</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="stat-box"><div class="stat-num">{len(st.session_state.favorites)}</div><div class="stat-label">عناصر محفوظة</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="stat-box"><div class="stat-num-sm">{last_search}</div><div class="stat-label">آخر بحث</div></div>', unsafe_allow_html=True)
        s4.markdown(f'<div class="stat-box"><div class="stat-num-sm">{most_searched}</div><div class="stat-label">الأكثر بحثًا</div></div>', unsafe_allow_html=True)


def page_history():
    st.markdown('<div class="page-title">🕒 السجل</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">كل عمليات البحث السابقة — اضغط على أي عنصر لإعادة عرض شرحه</div>', unsafe_allow_html=True)
    if not st.session_state.history:
        st.markdown('<div class="empty-state">لا توجد عمليات بحث سابقة بعد.</div>', unsafe_allow_html=True)
        return
    for i, entry in enumerate(st.session_state.history):
        with st.container(key=f"hist_item_{i}"):
            c1, c2, c3 = st.columns([6, 2, 2])
            c1.markdown(f'<div class="hist-term">📄 {entry["term"]}</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="hist-time">{entry.get("ts","")}</div>', unsafe_allow_html=True)
            with c3:
                if st.button("عرض الشرح ↩", key=f"hist_view_{i}", use_container_width=True):
                    show_existing_result(entry)


def page_favorites():
    st.markdown('<div class="page-title">⭐ المفضلة</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">الشروحات الكاملة التي تم حفظها (التعريف، المثال، النظرة السريعة، والاستخدام)</div>', unsafe_allow_html=True)
    if not st.session_state.favorites:
        st.markdown('<div class="empty-state">لا توجد عناصر محفوظة بعد.</div>', unsafe_allow_html=True)
        return
    for i, fav in enumerate(st.session_state.favorites):
        with st.container(key=f"fav_item_{i}"):
            c1, c2 = st.columns([9, 1])
            with c1:
                st.markdown(f'<div class="result-head" style="font-size:1.3rem;">📖 {fav["term"]}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("🗑️", key=f"fav_remove_{i}", help="إزالة من المفضلة"):
                    st.session_state.favorites.pop(i)
                    save_favorites_to_local_storage()
                    st.rerun()
            render_sections_only(fav["text"])


def page_terms():
    total = sum(len(v) for v in TERMS_CATALOG.values())
    st.markdown('<div class="page-title">📚 المصطلحات</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-sub">أكثر من {total} مصطلحًا تقنيًا مصنّفة — اضغط على أي مصطلح لعرض شرحه فورًا</div>', unsafe_allow_html=True)
    with st.container(key="terms_grid"):
        for cat, terms in TERMS_CATALOG.items():
            with st.expander(f"{cat}  ({len(terms)})", expanded=False):
                cols = st.columns(4)
                for i, t in enumerate(terms):
                    with cols[i % 4]:
                        if st.button(t, key=f"term_grid_{cat}_{i}", use_container_width=True):
                            trigger_new_search(t)


def page_settings():
    st.markdown('<div class="page-title">⚙️ الإعدادات</div>', unsafe_allow_html=True)
    with st.container(key="settings_panel"):
        st.markdown('<div class="panel-title">المظهر</div>', unsafe_allow_html=True)
        st.radio(
            "المظهر", options=["dark", "light"],
            format_func=lambda v: "🌙 الوضع الداكن" if v == "dark" else "☀️ الوضع الفاتح",
            key="theme_radio_settings", on_change=_sync_theme_from_settings,
            horizontal=True,
        )

        st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">البيانات</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ مسح السجل", use_container_width=True):
                st.session_state.history = []
                save_history_to_local_storage()
                st.rerun()
        with c2:
            if st.button("🗑️ مسح المفضلة", use_container_width=True):
                st.session_state.favorites = []
                save_favorites_to_local_storage()
                st.rerun()

        st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)
        if LOCAL_STORAGE_OK:
            st.markdown(
                '<div class="hist-time">💾 السجل والمفضلة محفوظان في متصفحك (Local Storage) ويبقيان بعد التحديث أو إغلاق الصفحة والرجوع لاحقًا.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="hist-time">⚠️ مكتبة الحفظ الدائم غير مثبّتة — نفّذي: <code>pip install streamlit-local-storage</code> ثم أعد تشغيل التطبيق ليتم حفظ السجل والمفضلة بشكل دائم.</div>',
                unsafe_allow_html=True,
            )


# =====================================================================
# التشغيل
# =====================================================================
render_sidebar()

_PAGES = {
    "home": page_home,
    "history": page_history,
    "favorites": page_favorites,
    "terms": page_terms,
    "settings": page_settings,
}
_PAGES.get(st.session_state.page, page_home)()

# =====================================================================
# ⬇️ الشريط الجانبي — تطبيق واحد لكل من سطح المكتب والجوال، بلا تكرار ⬇️
# محقونة متأخرًا عمدًا (بعد render_sidebar وكل الصفحات) لأن Streamlit يولّد
# CSS الخاص بالشريط وقت رندره الفعلي، فتُضاف أنماطه بعد أنماطنا لو حقنّاها
# مبكرًا — وعند تعادل !important يفوز الأحدث في ترتيب المستند. حقنها هنا
# يضمن أنها الأحدث فعليًا.
# =====================================================================
st.markdown(
    """
    <style>
    /* ---------- عناصر التحكم بالطي/الفتح: ☰ للفتح، ✕ للإغلاق ---------- */
    /* مهم: نحصر الـ selector داخل section[data-testid="stSidebar"] فقط —
       button[kind="header"] بدون حصر كان يطال أزرار أخرى غير متعلقة
       بالشريط (مثل GitHub/Fork في شريط أدوات الاستضافة)، فيلوّنها بالخطأ
       ولا يلوّن الزر الصحيح. كما نتجاهل أيقونة Streamlit الأصلية (SVG)
       ونعرض حرفنا الخاص (☰ / ✕) عبر ::after لضمان الشكل المطلوب بدقة.
       الألوان هنا ثابتة (خلفية فاتحة + حدّ أسود) لا تعتمد على الثيم، حتى
       تبقى واضحة تمامًا فوق أي خلفية (فاتحة أو داكنة). */
    [data-testid="stSidebarCollapsedControl"] button,
    section[data-testid="stSidebar"] button[kind="header"] {
        background: #f2f2f5 !important;
        border: 2px solid #000 !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,.28) !important;
        position: relative !important;
    }
    [data-testid="stSidebarCollapsedControl"] button svg,
    [data-testid="stSidebarCollapsedControl"] button path,
    section[data-testid="stSidebar"] button[kind="header"] svg,
    section[data-testid="stSidebar"] button[kind="header"] path {
        display: none !important;
    }
    [data-testid="stSidebarCollapsedControl"] button::after {
        content: "☰";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        color: #000;
        line-height: 1;
    }
    section[data-testid="stSidebar"] button[kind="header"]::after {
        content: "✕";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        font-weight: 700;
        color: #000;
        line-height: 1;
    }
    [data-testid="stSidebarCollapsedControl"] {
        position: fixed !important;
        top: 0.6rem !important;
        right: 0.6rem !important;
        left: auto !important;
        z-index: 999999 !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    /* =================== سطح المكتب (min-width: 769px) ===================
       الشريط جزء دائم من تخطيط flex، مرسى على اليمين عبر order. */
    @media (min-width: 769px) {
        [data-testid="stAppViewContainer"] {
            display: flex !important;
            flex-wrap: nowrap !important;
        }
        section[data-testid="stSidebar"] {
            order: -9999 !important;
            position: relative !important;
            flex: 0 0 auto !important;
            left: auto !important;
            right: auto !important;
            margin: 0 !important;
            transform: none !important;
        }
        [data-testid="stAppViewContainer"] > *:not(section[data-testid="stSidebar"]) {
            order: 9999 !important;
            position: relative !important;
            flex: 1 1 0% !important;
            width: auto !important;
            min-width: 0 !important;
        }
    }

    /* =================== الجوال (max-width: 768px) ===================
       الشريط لا يشارك إطلاقًا في تخطيط flex الرئيسي. مطويًا = صفر مساحة
       تمامًا. مفتوحًا = طبقة منبثقة (position:fixed) من اليمين، لا تُزيح
       ولا تُصغّر المحتوى الرئيسي إطلاقًا. */
    @media (max-width: 768px) {
        /* لا order ولا flex هنا إطلاقًا — الشريط خارج حسبة flex كليًا */
        [data-testid="stAppViewContainer"] > *:not(section[data-testid="stSidebar"]) {
            width: 100% !important;
            max-width: 100% !important;
            margin: 0 !important;
        }

        /* مطويًا: صفر مساحة فعليًا، لا يظهر كشريط ضيق على أي جهة */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            flex: 0 0 0 !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
            overflow: hidden !important;
        }
        section[data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
            width: 0 !important;
        }

        /* مفتوحًا: تراكب حقيقي من اليمين (RTL)، فوق المحتوى بدون إزاحته */
        section[data-testid="stSidebar"][aria-expanded="true"] {
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            left: auto !important;
            height: 100vh !important;
            width: min(75vw, 320px) !important;
            max-width: min(75vw, 320px) !important;
            margin: 0 !important;
            transform: none !important;
            z-index: 999600 !important;
            box-shadow: -14px 0 46px rgba(0,0,0,.55) !important;
            overflow-y: auto !important;
        }
        section[data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
            width: 100% !important;
            max-width: 100% !important;
            margin-left: 0 !important;
        }

        /* طبقة تعتيم خلف الشريط عند فتحه */
        [data-testid="stAppViewContainer"]:has(section[data-testid="stSidebar"][aria-expanded="true"])::before {
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,.55);
            z-index: 999500;
            animation: fadeIn .18s ease;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# طبقة شفافة حقيقية خلف الشريط عند فتحه على الجوال — الضغط عليها يغلق
# الشريط، عبر محاكاة ضغط زر الطي الأصلي (button[kind="header"]) بدل مجرد
# إخفاء بصري، كي تتحدث حالة Streamlit الداخلية فعليًا.
# =====================================================================
components.html(
    """
    <script>
    (function () {
        const doc = window.parent.document;

        /* إغلاق تلقائي عند التنقّل: هذا الجزء ينفّذ فقط لما تتغيّر الصفحة
           فعليًا (راجع تعليق تمرير st.session_state.page أسفل الكتلة)،
           لأن Streamlit لا يعيد تحميل مكوّن components.html إلا إذا تغيّر
           محتواه الفعلي — وربط المحتوى برقم/اسم الصفحة يضمن إعادة التنفيذ
           عند كل تنقّل فقط، لا عند أي تفاعل آخر. */
        (function autoCloseOnNav() {
            const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
            const isMobile = window.parent.innerWidth <= 768;
            if (sidebar && isMobile && sidebar.getAttribute('aria-expanded') === 'true') {
                const closeBtn =
                    sidebar.querySelector('button[kind="header"]') ||
                    sidebar.querySelector('button');
                if (closeBtn) closeBtn.click();
            }
        })();

        function ensureBackdrop() {
            let bd = doc.getElementById('twiki-sidebar-backdrop');
            if (!bd) {
                bd = doc.createElement('div');
                bd.id = 'twiki-sidebar-backdrop';
                bd.style.cssText =
                    'position:fixed;inset:0;z-index:999550;display:none;background:transparent;';
                bd.addEventListener('click', function () {
                    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                    if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
                        const closeBtn =
                            sidebar.querySelector('button[kind="header"]') ||
                            sidebar.querySelector('button');
                        if (closeBtn) closeBtn.click();
                    }
                });
                doc.body.appendChild(bd);
            }
            return bd;
        }
        function sync() {
            const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
            const bd = ensureBackdrop();
            const isMobile = window.parent.innerWidth <= 768;
            if (sidebar && isMobile && sidebar.getAttribute('aria-expanded') === 'true') {
                bd.style.display = 'block';
            } else {
                bd.style.display = 'none';
            }
        }
        sync();
        const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
        if (sidebar) {
            const mo = new MutationObserver(sync);
            mo.observe(sidebar, { attributes: true, attributeFilter: ['aria-expanded'] });
        }
        window.parent.addEventListener('resize', sync);
    })();
    </script>
    """
    + f"<!-- page:{st.session_state.page} -->",
    height=0,
)
