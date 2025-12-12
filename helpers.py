import re
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd


DEFAULT_TOPICS: List[str] = [
    "Unit 1 - Business Activity",
    "Unit 2 - Marketing",
    "Unit 3 - People",
    "Unit 4 - Operations",
    "Unit 5 - Finance",
    "Unit 6 - External influences",
    "General revision",
]


def init_state(state):
    state.setdefault("chat_history", [])
    state.setdefault("student_name", "")
    state.setdefault("student_class", "")
    state.setdefault("onboarding_complete", False)
    state.setdefault("selected_topic", DEFAULT_TOPICS[0])
    state.setdefault("quiz_active", False)
    state.setdefault("current_question", None)
    state.setdefault("quiz_history", [])
    state.setdefault("uploaded_notes", {})
    state.setdefault("tracking", {})
    state.setdefault("admin_unlocked", False)
    state.setdefault("pending_action", None)


def add_message(state, role: str, content: str):
    state.chat_history.append(
        {
            "role": role,
            "content": content,
            "ts": datetime.utcnow().isoformat(),
        }
    )


def parse_identity(text: str) -> Tuple[str, str]:
    if "," not in text:
        return "", ""
    name, class_name = [part.strip() for part in text.split(",", 1)]
    if not name or not class_name:
        return "", ""
    if len(name) > 40 or len(class_name) > 40:
        return "", ""
    return name, class_name


def generate_quiz_question(topic: str) -> Dict[str, str]:
    topic_bank = {
        "Unit 1 - Business Activity": [
            (
                "Define enterprise and give one reason why entrepreneurs start a business.",
                "Enterprise refers to taking initiative to set up and manage a business. Reasons include spotting a gap in the market or wanting independence.",
            ),
            (
                "Explain one advantage of a franchise model for a new entrepreneur.",
                "Franchises offer an established brand and support which reduces risk compared to starting alone.",
            ),
        ],
        "Unit 2 - Marketing": [
            (
                "State two methods a business can use for market research and explain one benefit of using them together.",
                "Primary research such as surveys and secondary data like industry reports can be combined to validate findings.",
            ),
            (
                "What is market segmentation and how could a trainer brand segment by geography?",
                "Segmentation splits the market into groups; a trainer brand could target urban regions differently to rural areas.",
            ),
        ],
        "Unit 3 - People": [
            (
                "Give two reasons why a business appraises staff performance annually.",
                "Appraisals identify training needs and set objectives which can improve motivation.",
            ),
            (
                "Explain one financial and one non financial method of motivation.",
                "A bonus rewards output while job rotation keeps roles varied and engaging.",
            ),
        ],
        "Unit 4 - Operations": [
            (
                "Describe one benefit of just in time stock control for a retailer.",
                "It reduces storage costs because items arrive when needed.",
            ),
            (
                "How can quality assurance support brand reputation?",
                "Checking processes prevents faults reaching customers, which protects trust.",
            ),
        ],
        "Unit 5 - Finance": [
            (
                "Calculate profit given revenue of £12 000 and costs of £8 500.",
                "Profit is £3 500 because profit equals revenue minus costs.",
            ),
            (
                "Explain one advantage of retained profit as a source of finance.",
                "It avoids interest charges so the business keeps control.",
            ),
        ],
        "Unit 6 - External influences": [
            (
                "Give one way a rise in interest rates may affect a small business loan repayment.",
                "Higher rates increase repayment amounts which can reduce cash flow.",
            ),
            (
                "How can environmental legislation influence business costs?",
                "Firms may need cleaner equipment which increases spending in the short term.",
            ),
        ],
        "General revision": [
            (
                "State two aims a start up might have in its first year.",
                "Typical aims include survival and building market share.",
            ),
            (
                "Give one benefit of social media promotion for a local business.",
                "It is low cost and can target nearby customers quickly.",
            ),
        ],
    }
    prompts = topic_bank.get(topic, topic_bank["General revision"])
    from random import choice

    question, model_answer = choice(prompts)
    return {"question": question, "model_answer": model_answer}


def score_answer(model_answer: str, learner_answer: str) -> Tuple[int, str]:
    model_words = set(re.findall(r"[a-zA-Z]+", model_answer.lower()))
    learner_words = set(re.findall(r"[a-zA-Z]+", learner_answer.lower()))
    overlap = len(model_words.intersection(learner_words))
    if overlap >= max(3, len(model_words) // 3):
        score = 2
        feedback = "Strong response - you covered the core points."
    elif overlap >= 2:
        score = 1
        feedback = "Partially correct. Add more detail or examples."
    else:
        score = 0
        feedback = "Key ideas are missing. Revisit the definition and try again."
    return score, feedback


def record_quiz_attempt(state, topic: str, question: str, answer: str, feedback: str, score: int):
    entry = {
        "topic": topic,
        "question": question,
        "answer": answer,
        "feedback": feedback,
        "score": score,
        "timestamp": datetime.utcnow().isoformat(),
    }
    state.quiz_history.append(entry)


def extract_text_from_upload(file) -> str:
    name = file.name.lower()
    if name.endswith(".txt"):
        return file.read().decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except Exception:
            return ""
        reader = PdfReader(file)
        text_chunks = []
        for page in reader.pages:
            try:
                text_chunks.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(text_chunks)
    if name.endswith(".docx"):
        try:
            import docx
        except Exception:
            return ""
        document = docx.Document(file)
        return "\n".join([p.text for p in document.paragraphs])
    return ""


def search_notes(notes: Dict[str, str], query: str, max_snippets: int = 2) -> List[str]:
    if not notes:
        return []
    keywords = [word for word in re.findall(r"[a-zA-Z]+", query.lower()) if len(word) > 3]
    if not keywords:
        return []
    ranked: List[Tuple[str, int]] = []
    for filename, text in notes.items():
        lower_text = text.lower()
        score = sum(lower_text.count(word) for word in keywords)
        if score > 0:
            ranked.append((filename, score))
    ranked.sort(key=lambda x: x[1], reverse=True)
    snippets: List[str] = []
    for filename, _ in ranked[:max_snippets]:
        text = notes[filename]
        sentences = re.split(r"(?<=[.!?]) +", text)
        for sentence in sentences:
            if any(word in sentence.lower() for word in keywords):
                snippets.append(f"{filename}: {sentence.strip()[:180]}")
                break
    return snippets[:max_snippets]


def update_tracking(state, topic: str, score: int = None):
    if not state.student_name or not state.student_class:
        return
    key = f"{state.student_name} | {state.student_class}"
    record = state.tracking.get(key, {
        "name": state.student_name,
        "class": state.student_class,
        "first_seen": datetime.utcnow().date().isoformat(),
        "message_count": 0,
        "topics_revised": set(),
        "quiz_attempts": 0,
        "average_score": 0.0,
    })
    record["message_count"] += 1
    if topic:
        record["topics_revised"].add(topic)
    if score is not None:
        total_score = record["average_score"] * record["quiz_attempts"] + score
        record["quiz_attempts"] += 1
        record["average_score"] = round(total_score / record["quiz_attempts"], 2)
    state.tracking[key] = record


def tracking_table(state) -> pd.DataFrame:
    rows = []
    for record in state.tracking.values():
        rows.append(
            {
                "Student": record["name"],
                "Class": record["class"],
                "First seen": record["first_seen"],
                "Messages": record["message_count"],
                "Topics revised": ", ".join(sorted(record["topics_revised"])),
                "Quiz attempts": record["quiz_attempts"],
                "Average score": record["average_score"],
            }
        )
    return pd.DataFrame(rows)
