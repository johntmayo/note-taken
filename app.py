import streamlit as st
import anthropic
import base64
import requests
from pathlib import Path
from datetime import datetime, timedelta
import extra_streamlit_components as stx  # type: ignore[import-not-found]

st.set_page_config(page_title="Note Taken", page_icon="📝", layout="wide")

# Check for required secrets
required = ["ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY"]
missing = [k for k in required if k not in st.secrets]
if missing:
    st.error(
        f"Missing secrets: {', '.join(missing)}. "
        "For local dev, create `.streamlit/secrets.toml`. "
        "For Streamlit Cloud, add them in Settings → Secrets."
    )
    st.stop()

# Initialize clients
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
ANTHROPIC_MODEL = st.secrets.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
SUPABASE_URL = st.secrets["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
NOTES_ENDPOINT = f"{SUPABASE_URL}/rest/v1/notes"
AUTH_BASE = f"{SUPABASE_URL}/auth/v1"
REFRESH_COOKIE = "note_taken_refresh_token"
COOKIE_DAYS = 30
cookie_manager = stx.CookieManager()


def render_global_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Chivo:wght@700;800;900&family=Merriweather:wght@400;700&display=swap');
        :root {
            --paper: #FDFBF7;
            --card: #FFFFFF;
            --ink: #1F2937;
            --ink-secondary: #4B5563;
            --navy: #314059;
            --line: #E5E7EB;
            --line-strong: #1F2937;
            --panel: #F0F4F8;
        }

        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        #MainMenu,
        footer {
            display: none !important;
        }

        .stApp {
            background: var(--paper);
            color: var(--ink);
        }

        .block-container {
            margin-top: 3rem;
            margin-bottom: 2rem;
            padding: 2rem;
            max-width: 900px;
            background: var(--card);
            border: 2px solid var(--line-strong);
            box-shadow: 6px 6px 0 var(--line-strong);
        }

        .stApp, .stApp p, .stApp span, .stApp li,
        .stApp input, .stApp textarea, .stApp [data-testid="stCaptionContainer"] {
            font-family: "Merriweather", Georgia, serif !important;
            color: var(--ink);
            line-height: 1.45;
        }

        h1, h2, h3, h4, h5, h6, button, label,
        div[data-testid="stTabs"] button {
            font-family: "Chivo", sans-serif !important;
            letter-spacing: 0;
        }

        h1, .nt-title-text {
            color: var(--navy);
            font-weight: 800;
            margin: 0;
            line-height: 1.06;
            letter-spacing: -0.01em;
            font-size: 2.1rem;
            font-family: "Chivo", sans-serif !important;
        }

        .nt-title-row {
            display: flex;
            align-items: center;
            gap: 0.62rem;
            margin-bottom: 0.42rem;
        }

        .nt-title-icon {
            width: 2.25rem;
            height: 2.25rem;
            flex-shrink: 0;
            display: block;
        }

        h2 {
            color: var(--navy);
            font-size: 1.45rem;
            font-weight: 700;
            margin-top: 0.15rem;
            margin-bottom: 0.6rem;
        }

        h3 {
            color: var(--navy);
            font-size: 1.2rem;
            font-weight: 700;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 0.6rem;
        }

        div[data-testid="stTabs"] button {
            border: 2px solid var(--line);
            border-bottom: 0;
            border-radius: 0;
            background: var(--card);
            color: var(--ink-secondary);
            font-weight: 700;
            padding: 0.5rem 0.95rem;
            font-size: 0.86rem;
            text-transform: none;
            letter-spacing: 0;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--navy);
            border-color: var(--navy);
            box-shadow: none;
            border-bottom: 2px solid var(--card);
            background: var(--card);
        }

        div[data-testid="stForm"] {
            background: var(--card);
            border: 2px solid var(--line);
            border-radius: 0;
            box-shadow: none;
            padding: 1rem 1rem 0.55rem 1rem;
            margin-top: 0.2rem;
        }

        div[data-testid="stForm"] label,
        div[data-testid="stWidgetLabel"] label {
            margin-top: 0.3rem;
            margin-bottom: 0.22rem;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--ink);
            font-weight: 700;
        }

        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div {
            background: var(--card);
            border: 2px solid var(--line);
            border-radius: 0;
            min-height: 2.1rem;
        }

        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="textarea"] > div:focus-within {
            border-color: var(--navy);
            box-shadow: none;
        }

        button[kind="primary"] {
            background: var(--navy) !important;
            border: 2px solid var(--line-strong) !important;
            color: #FFFFFF !important;
            border-radius: 0 !important;
            box-shadow: 4px 4px 0 var(--line-strong) !important;
            font-weight: 700 !important;
            letter-spacing: 0 !important;
        }

        button[kind="secondary"] {
            background: var(--card) !important;
            border: 2px solid var(--line) !important;
            color: var(--navy) !important;
            border-radius: 0 !important;
            font-weight: 700 !important;
            letter-spacing: 0 !important;
            box-shadow: none !important;
        }

        button[kind="primary"]:hover {
            transform: translate(-1px, -1px);
            box-shadow: 5px 5px 0 var(--line-strong) !important;
        }

        button[kind="secondary"]:hover {
            transform: none;
        }

        div[data-testid="stButton"] > button {
            min-height: 2.25rem;
            padding: 0.4rem 0.82rem;
            font-size: 0.9rem;
        }

        div[data-testid="stExpander"] {
            border: 2px solid var(--line);
            border-radius: 0;
            box-shadow: none;
            background: var(--card);
        }

        div[data-testid="stAlert"] {
            border: 2px solid var(--line);
            border-radius: 0;
        }

        div[data-testid="stRadio"] label {
            text-transform: none !important;
            letter-spacing: 0 !important;
            font-family: "Merriweather", Georgia, serif !important;
            font-size: 0.9rem !important;
            color: var(--ink-secondary) !important;
        }

        code, pre {
            font-family: "Merriweather", serif !important;
        }

        .nt-tagline {
            color: var(--ink-secondary);
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 0.76rem;
        }

        .nt-kicker {
            font-family: "Chivo", sans-serif !important;
            color: var(--navy);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-size: 0.74rem;
            font-weight: 700;
            margin-top: 0.45rem;
            margin-bottom: 0.15rem;
        }

        .nt-subtle {
            color: var(--ink-secondary);
            margin-bottom: 0.8rem;
            font-size: 0.84rem;
            background: var(--panel);
            border-left: 4px solid var(--navy);
            padding: 0.55rem 0.7rem;
        }

        .nt-divider {
            height: 2px;
            background: var(--line);
            margin: 0.85rem 0 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def supabase_headers(access_token: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def sign_in(email: str, password: str) -> dict:
    response = requests.post(
        f"{AUTH_BASE}/token?grant_type=password",
        headers=supabase_headers(),
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def sign_up(email: str, password: str) -> dict:
    response = requests.post(
        f"{AUTH_BASE}/signup",
        headers=supabase_headers(),
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_session(refresh_token: str) -> dict:
    response = requests.post(
        f"{AUTH_BASE}/token?grant_type=refresh_token",
        headers=supabase_headers(),
        json={"refresh_token": refresh_token},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_current_user(access_token: str) -> dict:
    response = requests.get(
        f"{AUTH_BASE}/user",
        headers=supabase_headers(access_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def save_note(content: str, access_token: str, user_id: str) -> None:
    response = requests.post(
        NOTES_ENDPOINT,
        headers={**supabase_headers(access_token), "Prefer": "return=minimal"},
        json={"content": content, "user_id": user_id},
        timeout=30,
    )
    response.raise_for_status()


def load_notes(access_token: str) -> list[dict]:
    response = requests.get(
        NOTES_ENDPOINT,
        headers=supabase_headers(access_token),
        params={"select": "id,created_at,content", "order": "created_at.desc"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def init_auth_state() -> None:
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("refresh_token", None)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("auth_cookie_checked", False)


def save_refresh_cookie(refresh_token: str) -> None:
    cookie_manager.set(
        REFRESH_COOKIE,
        refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=COOKIE_DAYS),
        same_site="lax",
    )


def clear_refresh_cookie() -> None:
    cookie_manager.delete(REFRESH_COOKIE)


def set_auth_state(payload: dict, remember_me: bool) -> None:
    st.session_state["access_token"] = payload["access_token"]
    st.session_state["refresh_token"] = payload.get("refresh_token")
    st.session_state["user"] = get_current_user(payload["access_token"])
    if remember_me and st.session_state["refresh_token"]:
        save_refresh_cookie(st.session_state["refresh_token"])
    elif not remember_me:
        clear_refresh_cookie()


def clear_auth_state() -> None:
    st.session_state["access_token"] = None
    st.session_state["refresh_token"] = None
    st.session_state["user"] = None
    clear_refresh_cookie()


def init_ui_state() -> None:
    st.session_state.setdefault("capture_nonce", 0)
    st.session_state.setdefault("latest_transcribed_text", "")
    st.session_state.setdefault("latest_transcribed_time", "")


def reset_capture_widgets() -> None:
    st.session_state["capture_nonce"] += 1


def restore_auth_from_cookie() -> None:
    if st.session_state["auth_cookie_checked"]:
        return

    st.session_state["auth_cookie_checked"] = True
    if st.session_state["access_token"]:
        return

    refresh_token = cookie_manager.get(REFRESH_COOKIE)
    if not refresh_token:
        return

    try:
        payload = refresh_session(refresh_token)
        # If refresh succeeds, rotate to latest refresh token and keep cookie alive.
        set_auth_state(payload, remember_me=True)
    except Exception:
        clear_refresh_cookie()


def render_auth_ui() -> None:
    st.subheader("Sign in to your notes")
    sign_in_tab, sign_up_tab = st.tabs(["Sign In", "Sign Up"])

    with sign_in_tab:
        with st.form("sign_in_form"):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_password")
            remember_me = st.checkbox("Remember me for 30 days", value=True)
            submitted = st.form_submit_button("Sign In")
        if submitted:
            try:
                payload = sign_in(email=email, password=password)
                set_auth_state(payload, remember_me=remember_me)
                st.success("Signed in.")
                st.rerun()
            except Exception as e:
                st.error(f"Sign in failed: {e}")

    with sign_up_tab:
        with st.form("sign_up_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            try:
                payload = sign_up(email=email, password=password)
                # If email confirmation is enabled, Supabase may return no session yet.
                if payload.get("access_token"):
                    set_auth_state(payload, remember_me=True)
                    st.success("Account created and signed in.")
                    st.rerun()
                else:
                    st.success("Account created. Check your email to confirm, then sign in.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")


init_auth_state()
init_ui_state()
restore_auth_from_cookie()
render_global_styles()

logo_data_uri = ""
logo_path = Path(__file__).with_name("note_taken.svg")
if logo_path.exists():
    logo_data_uri = base64.b64encode(logo_path.read_bytes()).decode("utf-8")

title_icon_html = ""
if logo_data_uri:
    title_icon_html = (
        f"<img src='data:image/svg+xml;base64,{logo_data_uri}' "
        "alt='' class='nt-title-icon' width='36' height='36' style='width:2.25rem;height:2.25rem;'>"
    )

st.markdown(
    f"<div class='nt-title-row'>{title_icon_html}<div class='nt-title-text'>Note Taken</div></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='nt-tagline'>Capture your notes on phone, review anywhere.</div>",
    unsafe_allow_html=True,
)

if st.session_state["access_token"] and not st.session_state["user"]:
    try:
        st.session_state["user"] = get_current_user(st.session_state["access_token"])
    except Exception:
        clear_auth_state()

if not st.session_state["access_token"]:
    render_auth_ui()
    st.stop()

user = st.session_state["user"]
top_left, top_right = st.columns([4.2, 1])
with top_left:
    st.caption(f"Signed in as: {user.get('email', 'unknown user')}")
with top_right:
    logout_clicked = st.button("Log out")
if logout_clicked:
    clear_auth_state()
    st.rerun()
st.markdown("<div class='nt-divider'></div>", unsafe_allow_html=True)

tab_new, tab_notes = st.tabs(["New Note", "My Notes"])

# --- New Note tab ---
with tab_new:
    st.markdown("<div class='nt-kicker'>New Note</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='nt-subtle'>Capture or upload a photo, then transcribe and store it.</div>",
        unsafe_allow_html=True,
    )
    capture_mode = st.radio(
        "Capture mode",
        options=["In-app camera", "Upload / phone camera"],
        horizontal=True,
    )

    uploaded_file = None
    camera_photo = None
    nonce = st.session_state["capture_nonce"]
    if capture_mode == "In-app camera":
        camera_photo = st.camera_input(
            "Take a photo (switch lens in camera controls if needed)",
            key=f"camera_{nonce}",
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload a photo",
            type=["jpg", "jpeg", "png"],
            key=f"uploader_{nonce}",
        )

    input_source = uploaded_file or camera_photo

    action_primary, action_secondary = st.columns([3, 2])
    with action_primary:
        transcribe_clicked = st.button(
            "Transcribe & Save",
            type="primary",
            use_container_width=True,
            disabled=not bool(input_source),
        )
    with action_secondary:
        reset_clicked = st.button(
            "Reset Photo",
            use_container_width=True,
            disabled=not bool(input_source),
        )

    if reset_clicked:
        reset_capture_widgets()
        st.rerun()

    if transcribe_clicked and input_source:
        with st.spinner("Claude is reading your handwriting..."):
            binary_data = input_source.getvalue()
            base64_image = base64.b64encode(binary_data).decode("utf-8")

            try:
                message = client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=1024,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": base64_image,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "Please transcribe these handwritten notes exactly as written. Only output the transcribed text.",
                                },
                            ],
                        }
                    ],
                )

                text = message.content[0].text

                # Save to Supabase
                save_note(
                    content=text,
                    access_token=st.session_state["access_token"],
                    user_id=user["id"],
                )

                st.session_state["latest_transcribed_text"] = text
                st.session_state["latest_transcribed_time"] = datetime.utcnow().strftime("%b %d, %Y %I:%M %p UTC")
                st.success("Saved.")
                reset_capture_widgets()
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")
                st.caption(
                    "Tip: check `ANTHROPIC_MODEL` in your Streamlit Cloud Secrets "
                    "if you need a different model."
                )

    if st.session_state["latest_transcribed_text"]:
        st.markdown("<div class='nt-kicker'>Latest Output</div>", unsafe_allow_html=True)
        st.subheader("Latest transcription")
        st.caption(f"Saved {st.session_state['latest_transcribed_time']}")
        st.code(st.session_state["latest_transcribed_text"])
        st.download_button(
            "Download as .txt",
            data=st.session_state["latest_transcribed_text"],
            file_name=f"note-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

# --- My Notes tab ---
with tab_notes:
    st.markdown("<div class='nt-kicker'>My Notes</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='nt-subtle'>Search, copy, or download any note you have saved.</div>",
        unsafe_allow_html=True,
    )
    try:
        notes = load_notes(st.session_state["access_token"])
    except Exception as e:
        st.error(f"Could not load notes: {e}")
        notes = []

    search_query = st.text_input("Search notes", placeholder="Filter by keyword")
    filtered_notes = notes
    if search_query:
        query = search_query.lower()
        filtered_notes = [n for n in notes if query in n["content"].lower()]

    if not filtered_notes:
        st.info("No notes yet. Take a photo in the New Note tab.")
    else:
        st.caption(f"{len(filtered_notes)} note(s)")
        for n in filtered_notes:
            dt = datetime.fromisoformat(n["created_at"].replace("Z", "+00:00")).strftime("%b %d, %Y at %I:%M %p")
            with st.expander(f"📄 {dt}", expanded=False):
                st.code(n["content"])
                st.caption("Use the copy icon in the code block, or download below.")
                st.download_button(
                    "Download note",
                    data=n["content"],
                    file_name=f"note-{n['id']}.txt",
                    mime="text/plain",
                    key=f"download_{n['id']}",
                    use_container_width=True,
                )
