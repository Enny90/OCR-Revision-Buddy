import os
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from helpers import (
    DEFAULT_TOPICS,
    add_message,
    extract_text_from_upload,
    generate_quiz_question,
    init_state,
    parse_identity,
    record_quiz_attempt,
    score_answer,
    search_notes,
    tracking_table,
    update_tracking,
)


st.set_page_config(
    page_title="OCR Business Revision Buddy",
    page_icon="📘",
    layout="centered",
    initial_sidebar_state="collapsed",
)

init_state(st.session_state)

# Styling for centred layout and chat look
st.markdown(
    """
    <style>
    .block-container {max-width: 900px; margin: 0 auto;}
    .suggestion-chip button {border-radius: 16px; border: 1px solid #d0d7de; background: #f6f8fa; color: #111;}
    .suggestion-chip button:hover {background: #e9ecef;}
    .chat-header {font-size: 1.3rem; font-weight: 700; margin-bottom: 0.4rem;}
    .chat-subtitle {color: #444; margin-bottom: 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

query_params = st.query_params if hasattr(st, "query_params") else st.experimental_get_query_params()
admin_param = query_params.get("admin", "")
if isinstance(admin_param, list):
    admin_param = admin_param[0] if admin_param else ""
is_admin_flag = str(admin_param).lower() == "true"
if is_admin_flag:
    st.session_state.admin_unlocked = True

# Minimal header
st.markdown("<div class='chat-header'>OCR Business Revision Buddy</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='chat-subtitle'>Chat through GCSE OCR Business topics with quizzes, exam style prompts and note support.</div>",
    unsafe_allow_html=True,
)


# Helper functions ------------------------------------------------------------

def prompt_actions():
    actions = [
        ("Revise a topic", "revise"),
        ("Quick quiz", "quiz"),
        ("Explain a key term", "term"),
        ("Exam style question", "exam"),
        ("Upload my notes", "upload"),
        ("Help", "help"),
    ]
    cols = st.columns(len(actions))
    for col, (label, action_key) in zip(cols, actions):
        with col:
            if st.button(label, use_container_width=True, key=f"chip_{action_key}"):
                st.session_state.pending_action = action_key
                handle_user_prompt(label)


def render_chat():
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def add_assistant_message(text: str):
    add_message(st.session_state, "assistant", text)


# Conversation logic ---------------------------------------------------------

def onboarding_response(prompt: str):
    name, class_name = parse_identity(prompt)
    if name and class_name:
        st.session_state.student_name = name
        st.session_state.student_class = class_name
        st.session_state.onboarding_complete = True
        greeting = (
            f"Thanks **{name}** from **{class_name}**. What do you fancy doing today? "
            "Choose an option below or type your own request."
        )
        add_assistant_message(greeting)
    else:
        add_assistant_message(
            "Welcome. Tell me your first name or initials and your class in one message, for example `A.J., 10B1`."
        )


def prepare_notes_hint(prompt: str) -> str:
    snippets = search_notes(st.session_state.uploaded_notes, prompt)
    if not snippets:
        return ""
    hint_lines = ["Using your uploaded notes:"] + [f"- {snippet}" for snippet in snippets]
    return "\n".join(hint_lines)


def craft_response(prompt: str) -> str:
    lower_prompt = prompt.lower()
    topic = st.session_state.selected_topic
    if "barbour" in lower_prompt and "location" in lower_prompt:
        return "Barbour is a strong example of a brand using location based segmentation, focusing on countryside markets."
    base = [f"Topic focus: {topic}."]
    exam_question_map = {
        "Unit 1 - Business Activity": "Discuss how setting SMART objectives supports a start up in its first year (6 marks).",
        "Unit 2 - Marketing": "Analyse whether a sportswear brand should use digital promotion for a new trainer launch (8 marks).",
        "Unit 3 - People": "Evaluate the impact of flexible working on staff motivation in a small business (8 marks).",
        "Unit 4 - Operations": "Assess the benefits and drawbacks of using just in time stock control for a manufacturer (10 marks).",
        "Unit 5 - Finance": "Calculate and comment on the break even point given fixed costs and contribution (10 marks).",
        "Unit 6 - External influences": "Evaluate how a change in exchange rates could affect an exporter (12 marks).",
        "General revision": "Discuss one ethical issue a business might face and how it could respond (8 marks).",
    }
    if "define" in lower_prompt or "what is" in lower_prompt or st.session_state.pending_action == "term":
        base.append("Here is a clear definition followed by an exam ready sentence.")
        base.append("- Definition: a concise explanation of the term.")
        base.append("- Application: link it to a business example to show understanding.")
    elif st.session_state.pending_action == "exam":
        base.append("Exam style practice: plan your answer with a point, evidence and a short conclusion.")
        base.append(f"Try this question: {exam_question_map.get(topic, exam_question_map['General revision'])}")
    elif st.session_state.pending_action == "revise":
        base.append("Quick recap: recall key points, connect to stakeholders and consider exam command words.")
    else:
        base.append("Structured help: ask for examples, calculations or revision tips.")
    notes_hint = prepare_notes_hint(prompt)
    if notes_hint:
        base.append(notes_hint)
    st.session_state.pending_action = None
    return "\n".join(base)


def start_quiz():
    st.session_state.quiz_active = True
    st.session_state.pending_action = None
    question = generate_quiz_question(st.session_state.selected_topic)
    st.session_state.current_question = question
    add_assistant_message(
        f"Quiz time. One question at a time.\n\n**{question['question']}**\n\nType your answer or press End quiz to stop."
    )


def end_quiz(summary_note: Optional[str] = None):
    st.session_state.quiz_active = False
    st.session_state.current_question = None
    st.session_state.pending_action = None
    if not st.session_state.quiz_history:
        add_assistant_message("Quiz ended. No answers recorded yet.")
        return
    scores = [item["score"] for item in st.session_state.quiz_history]
    average = round(sum(scores) / len(scores), 2)
    summary_lines = ["Quiz summary:", f"- Questions answered: {len(scores)}", f"- Average score: {average} / 2"]
    if summary_note:
        summary_lines.append(summary_note)
    add_assistant_message("\n".join(summary_lines))


def handle_quiz_answer(prompt: str):
    question = st.session_state.current_question
    if not question:
        add_assistant_message("Quiz question missing. Starting a new one.")
        start_quiz()
        return
    score, feedback = score_answer(question["model_answer"], prompt)
    record_quiz_attempt(
        st.session_state,
        st.session_state.selected_topic,
        question["question"],
        prompt,
        feedback,
        score,
    )
    update_tracking(st.session_state, st.session_state.selected_topic, score=score)
    add_assistant_message(f"Feedback: {feedback} (Score {score}/2).")
    # Next question
    start_quiz()


def handle_user_prompt(prompt: str):
    add_message(st.session_state, "user", prompt)
    if st.session_state.onboarding_complete:
        update_tracking(st.session_state, st.session_state.selected_topic)
    if not st.session_state.onboarding_complete:
        onboarding_response(prompt)
        return
    if st.session_state.quiz_active:
        handle_quiz_answer(prompt)
        return
    # Action buttons
    if st.session_state.pending_action == "quiz":
        start_quiz()
        return
    if st.session_state.pending_action == "upload":
        add_assistant_message("Upload your notes using the uploader below and I will use them when you ask questions.")
        st.session_state.pending_action = None
        return
    if st.session_state.pending_action == "help":
        help_text = (
            "I can recap topics, set quick quizzes, craft exam style prompts, explain key terms and weave in your uploaded notes."
        )
        add_assistant_message(help_text)
        st.session_state.pending_action = None
        return
    # General crafting
    response = craft_response(prompt)
    add_assistant_message(response)


# UI ------------------------------------------------------------------------

selected_topic = st.selectbox(
    "OCR GCSE Business topic",
    DEFAULT_TOPICS,
    index=DEFAULT_TOPICS.index(st.session_state.selected_topic)
    if st.session_state.selected_topic in DEFAULT_TOPICS
    else 0,
    key="topic_select",
)
st.session_state.selected_topic = selected_topic

prompt_actions()

render_chat()

end_quiz_col, admin_col = st.columns([3, 1])
with end_quiz_col:
    if st.session_state.quiz_active:
        if st.button("End quiz", key="end_quiz"):
            end_quiz()

with admin_col:
    passcode = st.text_input("Teacher passcode", type="password", label_visibility="collapsed", key="passcode_input")
    stored_passcode = st.secrets.get("teacher_passcode", os.getenv("TEACHER_PASSCODE", ""))
    if passcode and passcode == stored_passcode:
        st.session_state.admin_unlocked = True
    elif passcode and stored_passcode and passcode != stored_passcode:
        st.info("Passcode not recognised.")

# Uploader area
with st.expander("Upload revision notes (pdf, txt, docx)"):
    uploads = st.file_uploader("Add files", type=["pdf", "txt", "docx"], accept_multiple_files=True)
    if uploads:
        for file in uploads:
            text = extract_text_from_upload(file)
            if text:
                st.session_state.uploaded_notes[file.name] = text
        st.success("Notes stored. I will use them when answering.")

# Teacher dashboard
if st.session_state.admin_unlocked:
    st.divider()
    st.markdown("### Teacher dashboard")
    table = tracking_table(st.session_state)
    if not table.empty:
        st.dataframe(table, use_container_width=True)
        csv_data = table.to_csv(index=False).encode("utf-8")
        st.download_button("Export CSV", csv_data, file_name="tracking.csv", mime="text/csv")
    else:
        st.info("No student data yet.")
    if is_admin_flag:
        if st.button("Reset tracking", type="primary"):
            st.session_state.tracking = {}
            st.success("Tracking cleared.")
        if st.button("Reset session state"):
            preserved_admin = st.session_state.admin_unlocked
            st.session_state.clear()
            init_state(st.session_state)
            st.session_state.admin_unlocked = preserved_admin
            st.experimental_rerun()
        with st.expander("Session state (admin only)"):
            st.write(dict(st.session_state))

chat_prompt = st.chat_input("Type your message")
if chat_prompt:
    handle_user_prompt(chat_prompt)
    st.rerun()

