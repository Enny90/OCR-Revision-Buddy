{\rtf1\ansi\ansicpg1252\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import os\
import time\
import textwrap\
from pathlib import Path\
\
from dotenv import load_dotenv\
from pypdf import PdfReader\
import streamlit as st\
from openai import OpenAI, APIError, RateLimitError\
\
# ============================================================\
# PAGE CONFIG + GLOBAL STYLING\
# ============================================================\
st.set_page_config(\
    page_title="OCR Business Revision Buddy",\
    page_icon="\uc0\u55357 \u56536 ",\
    layout="wide",\
)\
\
st.markdown(\
    """\
    <style>\
    /* Slightly larger global font */\
    html, body, .stApp \{\
        font-size: 19px !important;\
        background-color: #f4f4f5 !important;\
    \}\
\
    .block-container \{\
        max-width: 960px;              /* a bit wider */\
        margin: 0 auto;\
        padding-top: 2.8rem;\
        padding-bottom: 7rem;          /* space above fixed input */\
    \}\
\
    /* Landing icon + title */\
    .landing-icon \{\
        font-size: 4.1rem;\
        text-align: center;\
        margin-bottom: 0.35rem;\
    \}\
    .landing-title \{\
        text-align: center;\
        font-size: 2.7rem;             /* bigger title */\
        font-weight: 800;\
        color: #0f172a;\
        margin-bottom: 0.45rem;\
    \}\
    .landing-subtitle \{\
        text-align: center;\
        font-size: 1.15rem;            /* bigger subtitle */\
        color: #4b5563;\
        margin-bottom: 1.4rem;\
    \}\
\
    /* Suggestion chips row */\
    .chip-row \{\
        display: flex;\
        flex-wrap: wrap;\
        gap: 0.75rem;\
        justify-content: center;\
        margin-top: 0.75rem;\
        margin-bottom: 1.25rem;\
    \}\
\
    /* Buttons & chips */\
    .chip-btn button,\
    .stButton button \{\
        border-radius: 999px !important;\
        padding: 0.6rem 1.2rem !important;\
        font-size: 1.05rem !important;  /* bigger button text */\
        white-space: nowrap;\
    \}\
\
    /* Chat bubbles */\
    [data-testid="stChatMessage"] \{\
        background-color: #ffffff;\
        border-radius: 0.9rem;\
        padding: 1.05rem 1.25rem;\
        margin-bottom: 0.9rem;\
        border: 1px solid #e5e7eb;\
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);\
        font-size: 1.02rem;             /* bigger bubble text */\
        line-height: 1.55;\
    \}\
    [data-testid="stChatMessage"] p \{\
        margin-bottom: 0.4rem;\
    \}\
\
    /* Bottom chat input \'96 ChatGPT style */\
    div[data-testid="stChatInput"] \{\
        position: fixed;\
        left: 0;\
        right: 0;\
        bottom: 0;\
        padding: 1rem 0 1.6rem 0;\
        background: linear-gradient(to top, #f4f4f5 60%, rgba(244,244,245,0));\
        z-index: 999;\
    \}\
    div[data-testid="stChatInput"] > div \{\
        max-width: 780px;  /* slightly wider but still shorter than full */\
        margin: 0 auto;\
    \}\
    div[data-testid="stChatInput"] textarea \{\
        border-radius: 999px !important;\
        padding: 0.85rem 1.15rem !important;\
        font-size: 1.05rem !important;  /* bigger input text */\
        border: 1px solid #d4d4d8 !important;\
        background-color: #ffffff !important;\
        box-shadow: 0 0 0 1px rgba(24, 24, 27, 0.02),\
                    0 2px 4px rgba(15, 23, 42, 0.08);\
        min-height: 48px;\
    \}\
    div[data-testid="stChatInput"] textarea:focus \{\
        border-color: #6366f1 !important;\
        box-shadow: 0 0 0 1px #6366f1,\
                    0 2px 8px rgba(79, 70, 229, 0.28);\
    \}\
    div[data-testid="stChatInput"] button \{\
        border-radius: 999px !important;\
        padding: 0.4rem 0.55rem !important;\
        min-width: 0 !important;\
        height: 2.4rem;\
        margin-left: 0.5rem;\
    \}\
\
    .typing-indicator \{\
        font-size: 0.9rem;\
        color: #6b7280;\
        margin-top: 0.2rem;\
        text-align: left;\
    \}\
\
    /* Fix overflowing text in suggestion chips */\
    .chip-btn button, .stButton > button \{\
        font-size: 0.78rem !important;     /* smaller text */\
        padding: 0.25rem 0.75rem !important;\
        line-height: 1.1 !important;\
        white-space: normal !important;    /* allow wrapping */\
        word-break: break-word !important; /* break long words */\
        max-width: 180px !important;       /* limit bubble width */\
        text-align: center !important;\
    \}\
    </style>\
    """,\
    unsafe_allow_html=True,\
)\
\
# ============================================================\
# LOAD API KEY\
# ============================================================\
load_dotenv()\
api_key = os.getenv("OPENAI_API_KEY")\
if not api_key:\
    st.error("OPENAI_API_KEY not found. Please add it to your .env file.")\
    st.stop()\
\
client = OpenAI(api_key=api_key)\
\
# ============================================================\
# RAG: LOAD OCR PDFs (simple text search version)\
# ============================================================\
DATA_DIR = Path("data")\
\
\
@st.cache_resource(show_spinner="searching my knowledge\'85")\
def load_documents():\
    docs = []\
    if not DATA_DIR.exists():\
        return docs\
\
    for pdf_path in DATA_DIR.glob("*.pdf"):\
        try:\
            reader = PdfReader(str(pdf_path))\
            raw_text = ""\
            max_pages = 30  # speed limit\
\
            for i, page in enumerate(reader.pages):\
                if i >= max_pages:\
                    break\
                page_text = page.extract_text() or ""\
                raw_text += page_text + "\\n"\
\
            docs.append(\{"text": raw_text, "source": pdf_path.name\})\
        except Exception as e:\
            print(f"Error reading \{pdf_path\}: \{e\}")\
    return docs\
\
\
def get_business_snippets(query: str, max_chars: int = 2500) -> str:\
    docs = load_documents()\
    if not docs:\
        return ""\
\
    query_lower = query.lower()\
    ignore_words = \{\
        "test",\
        "quiz",\
        "questions",\
        "question",\
        "explain",\
        "revise",\
        "me",\
        "on",\
        "please",\
        "the",\
        "a",\
        "an",\
        "to",\
        "unit",\
        "for",\
    \}\
    keywords = [w for w in query_lower.split() if w not in ignore_words]\
\
    snippets = []\
    total_chars = 0\
\
    for doc in docs:\
        text = doc["text"]\
        text_lower = text.lower()\
        matches = []\
\
        # Match unit numbers, e.g. "1.4"\
        for part in query_lower.split():\
            if "." in part and part.replace(".", "").isdigit():\
                idx = text_lower.find(part)\
                if idx != -1:\
                    matches.append(idx)\
\
        # Fallback: keywords\
        if not matches:\
            for kw in keywords:\
                idx = text_lower.find(kw)\
                if idx != -1:\
                    matches.append(idx)\
\
        for idx in matches:\
            start = max(0, idx - 500)\
            end = min(len(text), idx + 800)\
            chunk = text[start:end].strip()\
            if chunk:\
                snippets.append(f"[Source: \{doc['source']\}]\\n\{chunk\}\\n")\
                total_chars += len(chunk)\
                if total_chars >= max_chars:\
                    break\
        if total_chars >= max_chars:\
            break\
\
    if not snippets:\
        first = docs[0]\
        chunk = first["text"][:max_chars]\
        snippets.append(f"[Source: \{first['source']\}]\\n\{chunk\}\\n")\
\
    return "\\n---\\n".join(snippets)\
\
\
# ============================================================\
# OCR BUSINESS UNIT LOGIC\
# ============================================================\
BUSINESS_UNITS = \{\
    "1.1": \{\
        "name": "The role of business enterprise and entrepreneurship",\
        "topic": "business enterprise and entrepreneurship",\
        "key_concepts": [\
            "business purpose",\
            "added value",\
            "risk",\
            "reward",\
            "entrepreneur characteristics",\
            "entrepreneur objectives",\
        ],\
        "keywords": ["enterprise", "entrepreneur", "risk", "reward", "added value"],\
        "question_styles": "Short AO1 definitions, AO2 start-up scenarios, AO3 risk vs reward.",\
    \},\
    "1.2": \{\
        "name": "Business planning",\
        "topic": "business planning",\
        "key_concepts": [\
            "business plan",\
            "cash flow",\
            "forecast",\
            "purpose of planning",\
            "benefits and drawbacks of a business plan",\
        ],\
        "keywords": ["business plan", "cash flow", "forecast", "planning"],\
        "question_styles": "Purpose of a business plan, analyse benefits/limitations in context.",\
    \},\
    "1.3": \{\
        "name": "Business ownership",\
        "topic": "different forms of business ownership",\
        "key_concepts": [\
            "sole trader",\
            "partnership",\
            "private limited company",\
            "public limited company",\
            "franchise",\
            "liability",\
        ],\
        "keywords": [\
            "sole trader",\
            "partnership",\
            "franchise",\
            "limited company",\
            "plc",\
            "ltd",\
            "liability",\
        ],\
        "question_styles": "Compare ownership types, justify a suitable ownership for a given business.",\
    \},\
    "1.4": \{\
        "name": "Business aims and objectives",\
        "topic": "business aims and objectives",\
        "key_concepts": [\
            "aim",\
            "objective",\
            "survival",\
            "profit",\
            "growth",\
            "market share",\
            "customer satisfaction",\
        ],\
        "keywords": ["aim", "objective", "survival", "profit", "market share"],\
        "question_styles": "Define aims/objectives, explain choices, analyse how they change over time.",\
    \},\
    "1.5": \{\
        "name": "Stakeholders in business",\
        "topic": "stakeholders in business",\
        "key_concepts": [\
            "stakeholder",\
            "internal stakeholder",\
            "external stakeholder",\
            "conflicting objectives",\
            "stakeholder influence",\
        ],\
        "keywords": [\
            "stakeholder",\
            "stakeholders",\
            "local community",\
            "supplier",\
            "owners",\
            "shareholders",\
        ],\
        "question_styles": "Identify stakeholders, explain objectives, analyse stakeholder conflicts.",\
    \},\
    "1.6": \{\
        "name": "Business growth",\
        "topic": "business growth",\
        "key_concepts": [\
            "internal growth",\
            "external growth",\
            "merger",\
            "takeover",\
            "economies of scale",\
            "diseconomies of scale",\
        ],\
        "keywords": ["growth", "merger", "takeover", "economies of scale"],\
        "question_styles": "Explain ways to grow, analyse advantages/disadvantages of growth.",\
    \},\
    "2.1": \{\
        "name": "The role of marketing",\
        "topic": "role of marketing",\
        "key_concepts": [\
            "purpose of marketing",\
            "meeting customer needs",\
            "market",\
            "market share",\
        ],\
        "keywords": ["marketing", "market share", "customer needs"],\
        "question_styles": "Explain purpose of marketing, apply to a business and its customers.",\
    \},\
    "2.2": \{\
        "name": "Market research",\
        "topic": "market research",\
        "key_concepts": [\
            "primary research",\
            "secondary research",\
            "quantitative",\
            "qualitative",\
            "reliability",\
            "bias",\
        ],\
        "keywords": [\
            "market research",\
            "survey",\
            "questionnaire",\
            "focus group",\
            "primary research",\
            "secondary research",\
        ],\
        "question_styles": "Identify methods, analyse strengths/weaknesses in context.",\
    \},\
    "2.3": \{\
        "name": "Market segmentation",\
        "topic": "market segmentation",\
        "key_concepts": [\
            "segment",\
            "demographic",\
            "geographic",\
            "income",\
            "lifestyle",\
            "target market",\
        ],\
        "keywords": ["market segment", "segmentation", "target market"],\
        "question_styles": "Explain segmentation, analyse benefits for a given business.",\
    \},\
    "2.4": \{\
        "name": "The marketing mix",\
        "topic": "the marketing mix",\
        "key_concepts": ["product", "price", "promotion", "place", "4Ps", "mix"],\
        "keywords": ["4ps", "product", "price", "promotion", "place", "marketing mix"],\
        "question_styles": "Analyse how the 4Ps work together, justify changes in context.",\
    \},\
\}\
\
\
def detect_unit_from_text(text: str):\
    t = text.lower()\
\
    for code, info in BUSINESS_UNITS.items():\
        if f"unit \{code\}" in t:\
            return code, info\
\
    for code, info in BUSINESS_UNITS.items():\
        if code in t:\
            return code, info\
\
    for code, info in BUSINESS_UNITS.items():\
        for kw in info["keywords"]:\
            if kw in t:\
                return code, info\
\
    return None, None\
\
\
def choose_model(user_text: str) -> str:\
    t = user_text.lower()\
    heavy_triggers = [\
        "9 mark",\
        "9-mark",\
        "9 marker",\
        "evaluate",\
        "assess",\
        "to what extent",\
        "mark my answer",\
        "mark my response",\
        "mark this",\
        "grade this",\
        "feedback on my answer",\
        "case study",\
    ]\
    if any(phrase in t for phrase in heavy_triggers):\
        return "gpt-4.1"\
    if len(user_text) > 400:\
        return "gpt-4.1"\
    return "gpt-4.1-mini"\
\
\
def is_quiz_request(text: str) -> bool:\
    t = text.lower()\
    triggers = [\
        "test me",\
        "quiz me",\
        "give me questions",\
        "exam practice",\
        "practice questions",\
        "past paper",\
        "mcq",\
        "mcqs",\
        "multiple choice",\
        "revision questions",\
    ]\
    return any(phrase in t for phrase in triggers)\
\
\
# ============================================================\
# SYSTEM PROMPT (internal)\
# ============================================================\
SYSTEM_PROMPT = textwrap.dedent(\
    """\
    You are the OCR Business Revision Buddy, a friendly and highly knowledgeable digital tutor for OCR GCSE Business (J204).\
\
    \'95 Only answer questions related to OCR GCSE Business (J204).\
    \'95 Always use British English.\
    \'95 Explain content clearly and concisely with examples.\
    \'95 When students ask for a quiz, exam practice, MCQs or \'93test me\'94:\
      - Generate 3\'965 exam-style questions.\
      - Include a mix of AO1, AO2 and AO3.\
      - Base the questions on a single OCR unit where possible.\
      - Do NOT include answers or explanations in the same response.\
      - Wait for the student to send their answers or ask for the answers before revealing any marking or model responses.\
\
    When marking answers:\
    \'95 Mark each question separately.\
    \'95 State the AO level (AO1 / AO2 / AO3).\
    \'95 Explain what was good and what was missing.\
    \'95 Give a model answer and a short tip for improvement.\
    """\
)\
\
USE_RAG = True  # always use OCR PDFs if available\
\
# ============================================================\
# SUGGESTION CHIPS (landing examples)\
# ============================================================\
SUGGESTIONS = \{\
    "\uc0\u55357 \u56538  Aims & objectives (1.4)": (\
        "Explain business aims and objectives (Unit 1.4) with a clear example."\
    ),\
    "\uc0\u55357 \u56421  Test me on Unit 1.5": (\
        "Test me on Unit 1.5 stakeholders in business with a short mixed AO1/AO2/AO3 quiz."\
    ),\
    "\uc0\u55357 \u56522  5 MCQs on Unit 2.2": (\
        "Give me 5 multiple choice questions on Unit 2.2 market research (no answers yet)."\
    ),\
    "\uc0\u55357 \u56541  Mark my 9-mark answer": (\
        "I will paste a 9-mark answer. Please mark it with AO1, AO2 and AO3 and give feedback."\
    ),\
\}\
\
# ============================================================\
# SESSION STATE INITIALISATION\
# ============================================================\
if "messages" not in st.session_state:\
    st.session_state.messages = []\
if "initial_question" not in st.session_state:\
    st.session_state.initial_question = ""\
if "selected_suggestion" not in st.session_state:\
    st.session_state.selected_suggestion = ""\
\
# ============================================================\
# HEADER: ICON + TITLE + RESTART BUTTON\
# ============================================================\
st.markdown('<div class="landing-icon">\uc0\u55357 \u56536 </div>', unsafe_allow_html=True)\
title_row = st.columns([4, 1])\
with title_row[0]:\
    st.markdown(\
        '<div class="landing-title">OCR Business Revision Buddy</div>',\
        unsafe_allow_html=True,\
    )\
    st.markdown(\
        '<div class="landing-subtitle">'\
        "Friendly GCSE OCR Business revision helper with interactive questions and feedback."\
        "</div>",\
        unsafe_allow_html=True,\
    )\
with title_row[1]:\
\
    def clear_conversation():\
        st.session_state.messages = []\
        st.session_state.initial_question = ""\
        st.session_state.selected_suggestion = ""\
        # st.rerun()  # optional; can be uncommented in newer Streamlit versions\
\
    st.button("Restart", on_click=clear_conversation)\
\
# ============================================================\
# LANDING / FIRST-INTERACTION LOGIC\
# ============================================================\
user_just_asked_initial = bool(st.session_state.initial_question)\
user_just_clicked_suggestion = bool(st.session_state.selected_suggestion)\
has_history = len(st.session_state.messages) > 0\
user_first_interaction = user_just_asked_initial or user_just_clicked_suggestion\
\
if not user_first_interaction and not has_history:\
    # Landing chat input at centre (not pinned yet)\
    st.chat_input("Ask a Business question\'85", key="initial_question")\
\
    # Suggestion chips row\
    st.write("")\
    cols = st.columns(len(SUGGESTIONS))\
    for (label, _prompt), col in zip(SUGGESTIONS.items(), cols):\
        with col:\
            if st.button(label, use_container_width=True, key=f"chip-\{label\}"):\
                st.session_state.selected_suggestion = label\
                st.rerun()\
\
    st.caption(\
        "\uc0\u9888 \u65039  This assistant can make mistakes. Always check important answers with your teacher or official OCR materials."\
    )\
\
    st.stop()\
\
# ============================================================\
# NORMAL CHAT MODE FROM HERE\
# ============================================================\
\
# Show previous chat history\
for msg in st.session_state.messages:\
    with st.chat_message(msg["role"]):\
        st.markdown(msg["content"])\
\
# Bottom input (pinned, short)\
user_message = st.chat_input("Ask a follow-up or request a quiz\'85")\
\
# If nothing typed this turn, consume initial question or suggestion once\
if not user_message:\
    if user_just_asked_initial:\
        user_message = st.session_state.initial_question\
        st.session_state.initial_question = ""\
    elif user_just_clicked_suggestion:\
        label = st.session_state.selected_suggestion\
        user_message = SUGGESTIONS.get(label, "")\
        st.session_state.selected_suggestion = ""\
\
if user_message:\
    st.session_state.messages.append(\{"role": "user", "content": user_message\})\
\
    with st.chat_message("user"):\
        st.markdown(user_message)\
\
    # Build message payload\
    messages_for_api = [\{"role": "system", "content": SYSTEM_PROMPT\}]\
    messages_for_api.extend(st.session_state.messages)\
\
    # Quiz detection\
    quiz_mode = is_quiz_request(user_message)\
    if quiz_mode:\
        messages_for_api.append(\
            \{\
                "role": "system",\
                "content": (\
                    "The student has asked for a quiz or exam-style questions. "\
                    "In THIS response only, generate questions (including MCQs or short answers) "\
                    "but do NOT provide any answers, solutions or explanations. "\
                    "Wait for the student to submit their answers or ask for the answers."\
                ),\
            \}\
        )\
\
    # Unit context\
    unit_code, unit_info = detect_unit_from_text(user_message)\
    if unit_code and unit_info:\
        unit_context = (\
            f"You are helping with OCR GCSE Business unit \{unit_code\}: \{unit_info['name']\}.\\n"\
            f"Topic focus: \{unit_info['topic']\}.\\n"\
            f"Key concepts: \{', '.join(unit_info['key_concepts'])\}.\\n"\
            f"Typical question styles: \{unit_info['question_styles']\}."\
        )\
        messages_for_api.append(\{"role": "system", "content": unit_context\})\
\
    # RAG context\
    context_used = ""\
    if USE_RAG:\
        context_used = get_business_snippets(user_message)\
        if context_used:\
            messages_for_api.append(\
                \{\
                    "role": "system",\
                    "content": (\
                        "Use the following OCR Business reference extracts when answering. "\
                        "If they conflict with other knowledge, prefer these extracts.\\n\\n"\
                        + context_used\
                    ),\
                \}\
            )\
\
    # Choose model\
    selected_model = choose_model(user_message)\
\
    # =======================================================\
    # ChatGPT-style streaming with animated typing dots\
    # =======================================================\
    with st.chat_message("assistant"):\
        import random\
\
        # Placeholder for the "typing..." line\
        typing_indicator = st.empty()\
\
        reply = ""\
        try:\
            placeholder = st.empty()\
\
            # Stream response from OpenAI\
            stream = client.chat.completions.create(\
                model=selected_model,\
                messages=messages_for_api,\
                stream=True,\
            )\
\
            # For animated dots\
            dots = 0\
\
            for chunk in stream:\
                delta = chunk.choices[0].delta\
                if not delta.content:\
                    continue\
\
                piece = delta.content\
                lower_piece = piece.lower()\
\
                # In quiz mode, prevent leaking answers\
                if quiz_mode and (\
                    "correct answer" in lower_piece\
                    or "answer:" in lower_piece\
                    or "answers:" in lower_piece\
                    or "mark scheme" in lower_piece\
                    or "explanation:" in lower_piece\
                ):\
                    break\
\
                # Append new text and show it\
                reply += piece\
                placeholder.markdown(reply)\
\
                # Update animated typing dots: "", ".", "..", "..."\
                dots = (dots + 1) % 4\
                dot_str = "." * dots\
                typing_indicator.markdown(\
                    f'<div class="typing-indicator">'\
                    f'\uc0\u9999 \u65039  OCR Business Revision Buddy is typing\{dot_str\}'\
                    f'</div>',\
                    unsafe_allow_html=True,\
                )\
\
                # ChatGPT-style typing delay with slight variation\
                time.sleep(0.04 + random.uniform(-0.015, 0.015))\
\
            # Clear typing indicator once finished\
            typing_indicator.empty()\
\
        except RateLimitError:\
            typing_indicator.empty()\
            st.error(\
                "Your OpenAI API quota has been exceeded. "\
                "Check your plan and billing at https://platform.openai.com."\
            )\
        except APIError as e:\
            typing_indicator.empty()\
            st.error(f"An API error occurred: \{e\}")\
        except Exception as e:\
            typing_indicator.empty()\
            st.error(f"Something went wrong: \{e\}")\
\
    st.session_state.messages.append(\{"role": "assistant", "content": reply.strip()\})\
}
