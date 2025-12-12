# OCR Business Revision Buddy

A streamlined Streamlit app that delivers a ChatGPT style revision helper for OCR GCSE Business. It supports student onboarding, topic revision, quizzes, exam style prompts, key term explanations, note uploads, and a teacher dashboard.

## Running locally
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Launch the app:
   ```bash
   streamlit run app.py
   ```
4. The sidebar is collapsed by default. Use the on page controls and chat input to interact.

## Deploying to Streamlit Community Cloud
1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create a new app and point it to `app.py` on your main branch.
3. Set Python version to 3.11 or later and add the repository secret `TEACHER_PASSCODE` if you want a passcode gate.
4. Deploy. The layout will default to centred chat bubbles with suggestion chips.

## Admin and teacher features
- Teacher dashboard unlocks if the URL includes `?admin=true` or if the correct passcode is entered in the Teacher passcode box.
- Passcode order of precedence: Streamlit `st.secrets['teacher_passcode']` then environment variable `TEACHER_PASSCODE`.
- In admin mode you can view the tracking table, export CSV, and reset tracking (reset is only visible when `admin=true`).
- Uploaded notes are stored per session and used for responses with a short hint showing the referenced snippets.

## Key behaviours
- Onboarding collects `Name, Class` in one message before any revision starts. The first student message appears instantly and is not replayed.
- Chat history is stored with timestamps to avoid replay issues.
- Suggestion chips provide quick actions: revise a topic, quick quiz, explain a term, exam style question, upload notes, or help.
- Quiz mode presents one question at a time, stores scores, and offers an End quiz summary.
- Teacher tracking logs first seen date, message counts, topics revised, and quiz averages per student and class.
