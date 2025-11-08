import os
from typing import Any, Dict, Optional

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
CHAT_HISTORY_KEY = "assistant_chat_history"


def _init_history():
    if CHAT_HISTORY_KEY not in st.session_state:
        st.session_state[CHAT_HISTORY_KEY] = []


def _render_history():
    history = st.session_state.get(CHAT_HISTORY_KEY, [])
    base_url = API_BASE_URL.rstrip("/")
    for entry in history[-12:]:  # show last 12 turns
        role = entry.get("role", "assistant")
        content = entry.get("content", "")
        if role == "user":
            st.markdown(f"**You:** {content}")
        else:
            st.markdown(f"**Assistant:** {content}")
            sources = entry.get("sources") or []
            if sources:
                with st.expander("Sources", expanded=False):
                    for src in sources:
                        src_type = src.get("type", "source").title()
                        title = src.get("title") or src.get("id", "")
                        url = src.get("url")
                        display_title = title or "Untitled"
                        if url:
                            if not url.startswith("http"):
                                normalized = url if url.startswith("/") else f"/{url}"
                                url = f"{base_url}{normalized}"
                            st.markdown(f"- {src_type}: [{display_title}]({url})")
                        else:
                            st.write(f"- {src_type}: {display_title}")
                        snippet = src.get("snippet")
                        if snippet:
                            st.caption(snippet)


def render_chat_sidebar(page_label: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Render the governance assistant chat in the sidebar."""
    _init_history()
    st.markdown("---")
    st.markdown("### 💬 Governance Assistant")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Clear", key=f"assistant_clear_{page_label}"):
            st.session_state[CHAT_HISTORY_KEY] = []
            st.experimental_rerun()

    _render_history()

    with st.form(key=f"assistant_form_{page_label}", clear_on_submit=True):
        message = st.text_area("Ask a question", height=80)
        submitted = st.form_submit_button("Send")

    if submitted and message.strip():
        user_message = message.strip()
        st.session_state[CHAT_HISTORY_KEY].append({"role": "user", "content": user_message})

        payload = {
            "message": user_message,
            "page": page_label,
            "context": context or {},
            "history": [
                {"role": entry.get("role", "assistant"), "content": entry.get("content", "")}
                for entry in st.session_state[CHAT_HISTORY_KEY][-10:]
            ],
        }

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(f"{API_BASE_URL}/assistant/chat", json=payload)
            if response.status_code == 200:
                data = response.json()
                st.session_state[CHAT_HISTORY_KEY].append(
                    {
                        "role": "assistant",
                        "content": data.get("reply", ""),
                        "sources": data.get("sources", []),
                    }
                )
            else:
                st.session_state[CHAT_HISTORY_KEY].append(
                    {
                        "role": "assistant",
                        "content": f"[Error {response.status_code}] {response.text}",
                        "sources": [],
                    }
                )
        except Exception as exc:
            st.session_state[CHAT_HISTORY_KEY].append(
                {
                    "role": "assistant",
                    "content": f"Request failed: {exc}",
                    "sources": [],
                }
            )

        st.experimental_rerun()
