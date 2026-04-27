"""
pages/agent_chat.py
-------------------
AI Agent Chat — conversational interface to the /chat endpoint.
Maintains session history and renders a styled chat UI.
"""

import streamlit as st
from utils.api import send_chat
from utils.style_loader import section_header


SUGGESTED_PROMPTS = [
    "📊 How many jamming signals were detected today?",
    "🚨 What's the current threat level?",
    "📡 Show me the latest signal statistics",
    "🗺️ Where are the most alerts coming from?",
    "🤖 What model version is running?",
    "📈 What's the average confidence score?",
    "⚡ Are there any critical threats active?",
    "📬 How many email alerts were sent?",
]


def _render_message(role: str, content: str) -> None:
    """Render a single chat message bubble."""
    is_user = role == "user"
    bg      = "var(--bg-tertiary)"       if is_user else "var(--bg-secondary)"
    border  = "var(--accent-cyan)"       if is_user else "var(--border-subtle)"
    align   = "flex-end"                 if is_user else "flex-start"
    avatar  = "👤"                       if is_user else "🤖"
    name    = "You"                      if is_user else "SpectrumAgent"
    name_c  = "var(--accent-cyan)"       if is_user else "var(--accent-lime)"

    # Escape for safe rendering
    safe_content = content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

    st.markdown(f"""
    <div style="display:flex;justify-content:{align};margin-bottom:12px;">
        <div style="max-width:80%;">
            <div style="font-size:11px;color:{name_c};font-family:var(--font-mono);
                        letter-spacing:0.08em;margin-bottom:4px;
                        text-align:{'right' if is_user else 'left'};">
                {avatar} {name}
            </div>
            <div style="background:{bg};border:1px solid {border};
                        border-radius:var(--radius-lg);padding:14px 18px;
                        font-size:14px;line-height:1.6;color:var(--text-primary);
                        {'border-bottom-right-radius:4px;' if is_user else 'border-bottom-left-radius:4px;'}">
                {safe_content}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render():
    st.markdown("""
    <h1 class="h1" style="font-size:24px;">🤖 AGENT CHAT</h1>
    <div style="height:1px;background:linear-gradient(90deg,var(--accent-lime),transparent);
                margin-bottom:24px;"></div>
    """, unsafe_allow_html=True)

    # ── Init session ──────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "agent_thinking" not in st.session_state:
        st.session_state.agent_thinking = False

    # ── Layout ────────────────────────────────────────────────────
    chat_col, ctrl_col = st.columns([3, 1], gap="large")

    with ctrl_col:
        section_header("CONTROLS", "AGENT")

        st.markdown("""
        <div style="background:var(--bg-secondary);border:1px solid var(--border-subtle);
                    border-radius:var(--radius-lg);padding:16px;margin-bottom:16px;">
            <div style="font-size:10px;color:var(--text-tertiary);
                        letter-spacing:0.12em;text-transform:uppercase;
                        font-family:var(--font-mono);margin-bottom:8px;">Agent Status</div>
            <div class="system-status-online">SpectrumAgent</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**💡 Suggested Prompts**")
        for prompt in SUGGESTED_PROMPTS[:5]:
            if st.button(prompt, use_container_width=True, key=f"sp_{prompt[:20]}"):
                clean_prompt = prompt.split(" ", 1)[1]  # strip emoji
                st.session_state.chat_history.append({"role": "user", "content": clean_prompt})
                with st.spinner("🧠 Agent thinking…"):
                    response = send_chat(clean_prompt, st.session_state.chat_history[:-1])
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.metric("💬 Messages", len(st.session_state.chat_history))

    with chat_col:
        section_header("CONVERSATION", "LIVE")

        # ── Chat messages container ───────────────────────────────
        chat_container = st.container()
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("""
                <div style="text-align:center;padding:40px;
                            border:1px dashed var(--border-subtle);
                            border-radius:var(--radius-lg);
                            background:var(--bg-secondary);margin-bottom:16px;">
                    <div style="font-size:40px;margin-bottom:12px;">🤖</div>
                    <div style="font-family:var(--font-display);font-size:18px;
                                font-weight:700;letter-spacing:0.12em;
                                color:var(--accent-lime);text-transform:uppercase;">
                        SpectrumAgent Ready
                    </div>
                    <div style="color:var(--text-tertiary);font-size:13px;
                                margin-top:8px;font-family:var(--font-mono);">
                        Ask me anything about spectrum anomalies,<br>
                        alerts, predictions, and system status.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                for msg in st.session_state.chat_history:
                    _render_message(msg["role"], msg["content"])

        # ── Input bar ─────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            inp_col, btn_col = st.columns([5, 1])
            with inp_col:
                user_input = st.text_input(
                    "Message",
                    placeholder="Ask about spectrum anomalies, alerts, statistics…",
                    label_visibility="collapsed",
                )
            with btn_col:
                submitted = st.form_submit_button("Send 🚀", use_container_width=True)

        if submitted and user_input.strip():
            msg = user_input.strip()
            st.session_state.chat_history.append({"role": "user", "content": msg})

            with st.spinner("🧠 SpectrumAgent is thinking…"):
                history_for_api = st.session_state.chat_history[:-1]
                response = send_chat(msg, history_for_api)

            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

        # ── Export ────────────────────────────────────────────────
        if st.session_state.chat_history:
            import json
            export = json.dumps(st.session_state.chat_history, indent=2, ensure_ascii=False)
            st.download_button(
                "⬇️ Export Chat History",
                data=export.encode("utf-8"),
                file_name="agent_chat_export.json",
                mime="application/json",
            )
