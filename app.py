import streamlit as st
import anthropic
import base64
import requests
from datetime import datetime

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
    st.session_state.setdefault("user", None)


def clear_auth_state() -> None:
    st.session_state["access_token"] = None
    st.session_state["user"] = None


def render_auth_ui() -> None:
    st.subheader("Sign in to your notes")
    sign_in_tab, sign_up_tab = st.tabs(["Sign In", "Sign Up"])

    with sign_in_tab:
        with st.form("sign_in_form"):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_password")
            submitted = st.form_submit_button("Sign In")
        if submitted:
            try:
                payload = sign_in(email=email, password=password)
                st.session_state["access_token"] = payload["access_token"]
                st.session_state["user"] = get_current_user(payload["access_token"])
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
                    st.session_state["access_token"] = payload["access_token"]
                    st.session_state["user"] = get_current_user(payload["access_token"])
                    st.success("Account created and signed in.")
                    st.rerun()
                else:
                    st.success("Account created. Check your email to confirm, then sign in.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")


init_auth_state()

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
st.caption(f"Signed in as: {user.get('email', 'unknown user')}")
if st.button("Log out"):
    clear_auth_state()
    st.rerun()

tab_new, tab_notes = st.tabs(["New Note", "My Notes"])

# --- New Note tab ---
with tab_new:
    uploaded_file = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"])
    camera_photo = st.camera_input("Or take a photo")
    input_source = uploaded_file or camera_photo

    if input_source:
        if st.button("Transcribe & Save"):
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

                    st.success("Saved!")
                    st.subheader("Transcribed:")
                    st.text_area("", value=text, height=200, disabled=True, label_visibility="collapsed")

                except Exception as e:
                    st.error(f"Error: {e}")
                    st.caption(
                        "Tip: set ANTHROPIC_MODEL in `.streamlit/secrets.toml` "
                        "if you need a different model."
                    )

# --- My Notes tab ---
with tab_notes:
    try:
        notes = load_notes(st.session_state["access_token"])
    except Exception as e:
        st.error(f"Could not load notes: {e}")
        notes = []

    if not notes:
        st.info("No notes yet. Take a photo in the New Note tab.")
    else:
        for n in notes:
            dt = datetime.fromisoformat(n["created_at"].replace("Z", "+00:00")).strftime("%b %d, %Y at %I:%M %p")
            with st.expander(f"📄 {dt}", expanded=False):
                st.text_area(
                    "Content",
                    value=n["content"],
                    height=120,
                    disabled=True,
                    key=n["id"],
                    label_visibility="collapsed",
                )
                st.caption("Select and copy the text above.")
