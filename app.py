import streamlit as st
import anthropic
import base64
import requests
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
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 900px;
        }
        h1, h2, h3 {
            letter-spacing: -0.01em;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.5rem;
        }
        div[data-testid="stTabs"] button {
            font-weight: 600;
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

st.title("📝 Note Taken")

if st.session_state["access_token"] and not st.session_state["user"]:
    try:
        st.session_state["user"] = get_current_user(st.session_state["access_token"])
    except Exception:
        clear_auth_state()

if not st.session_state["access_token"]:
    render_auth_ui()
    st.stop()

user = st.session_state["user"]
top_left, top_right = st.columns([3, 1])
with top_left:
    st.caption(f"Signed in as: {user.get('email', 'unknown user')}")
with top_right:
    logout_clicked = st.button("Log out", use_container_width=True)
if logout_clicked:
    clear_auth_state()
    st.rerun()

tab_new, tab_notes = st.tabs(["New Note", "My Notes"])

# --- New Note tab ---
with tab_new:
    st.caption("Use upload mode on mobile for the fastest capture flow.")
    capture_mode = st.radio(
        "Capture mode",
        options=["Upload / phone camera", "In-app camera"],
        horizontal=True,
    )

    uploaded_file = None
    camera_photo = None
    nonce = st.session_state["capture_nonce"]
    if capture_mode == "Upload / phone camera":
        uploaded_file = st.file_uploader(
            "Upload a photo",
            type=["jpg", "jpeg", "png"],
            key=f"uploader_{nonce}",
        )
    else:
        camera_photo = st.camera_input(
            "Take a photo (switch lens in camera controls if needed)",
            key=f"camera_{nonce}",
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
