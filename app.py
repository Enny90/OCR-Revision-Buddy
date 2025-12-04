import streamlit as st
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="OCR Business Revision Buddy",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for ChatGPT-style interface
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Chat container */
    .stApp {
        background-color: #343541;
    }
    
    /* Header styling */
    [data-testid="stHeader"] {
        background-color: #202123;
        border-bottom: 1px solid #4d4d4f;
    }
    
    /* Hide sidebar by default */
    section[data-testid="stSidebar"] {
        display: none;
    }
    
    /* Chat messages */
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        gap: 1rem;
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .chat-message.user {
        background-color: #343541;
    }
    
    .chat-message.assistant {
        background-color: #444654;
    }
    
    .chat-avatar {
        width: 32px;
        height: 32px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
    }
    
    .chat-avatar.user {
        background-color: #10a37f;
    }
    
    .chat-avatar.assistant {
        background-color: #5436DA;
    }
    
    .chat-content {
        flex: 1;
        color: #ececf1;
        line-height: 1.7;
        font-size: 16px;
    }
    
    /* Landing page */
    .landing-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
        padding: 3rem 1.5rem;
    }
    
    .landing-icon {
        font-size: 64px;
        margin-bottom: 1rem;
    }
    
    .landing-title {
        font-size: 32px;
        font-weight: 600;
        color: #ececf1;
        margin-bottom: 0.5rem;
    }
    
    .landing-subtitle {
        font-size: 16px;
        color: #c5c5d2;
        margin-bottom: 3rem;
        max-width: 600px;
    }
    
    /* Suggestion chips */
    .stButton button {
        background-color: #40414f;
        border: 1px solid #565869;
        color: #ececf1;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        width: 100%;
        text-align: left;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        background-color: #4d4d4f;
        border-color: #8e8ea0;
    }
    
    /* Input styling */
    .stChatInputContainer {
        background-color: #343541;
        border-top: 1px solid #4d4d4f;
    }
    
    .stChatInput textarea {
        background-color: #40414f;
        border: 1px solid #565869;
        border-radius: 12px;
        color: #ececf1;
    }
    
    .stChatInput textarea:focus {
        border-color: #8e8ea0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'uploaded_documents' not in st.session_state:
    try:
        if 'DOCUMENTS_JSON' in st.secrets:
            st.session_state.uploaded_documents = json.loads(st.secrets['DOCUMENTS_JSON'])
        else:
            st.session_state.uploaded_documents = {}
    except:
        st.session_state.uploaded_documents = {}

# System prompt
SYSTEM_PROMPT = """You are the OCR Business Revision Buddy, a friendly AI tutor for OCR GCSE Business (J204).

🎓 BEHAVIOUR RULES:
- Only answer OCR GCSE Business (J204) questions
- Use British English always
- Be friendly, supportive, encouraging, clear and structured
- Use OCR command words: Identify, State, Explain, Analyse, Evaluate, Justify

📚 CONTENT:
- Component 1 (Units 1.1-1.6): Business Activity, Marketing, People
- Component 2 (Units 2.1-2.4): Operations, Finance, Influences on Business
- Use real business examples (cafés, gyms, shops, services)
- Keep explanations concise and exam-focused

📝 QUIZ/TEST BEHAVIOUR - CRITICAL:
When student asks for tests/quizzes/MCQs/practice questions:
1. Generate 3-5 exam-style questions
2. Mix AO1 (1-2 marks), AO2 (2-3 marks), AO3 (3-6+ marks)
3. ⚠️ DO NOT give answers in same response
4. Say: "Here are your questions. Try them first, then send me your answers and I'll mark them."
5. Only reveal answers when student submits their answers

✅ MARKING BEHAVIOUR:
When student submits answers:
- Mark each question separately
- State AO level (AO1/AO2/AO3)
- Show: ✅ What was good, ❌ What was missing
- Provide model answer
- Give "💡 Next time" tip

Example:
**Q1 (AO1 - 2 marks)**
Score: 1/2
✅ Good: Correct identification
❌ Missing: Full definition
Model answer: [answer]
💡 Next time: Include full definition

🚫 SAFETY:
If non-Business topics: "I'm designed for OCR GCSE Business (J204). What Business topic would you like to revise?"

Use uploaded documents if available for accuracy."""

def call_ai(user_message):
    """Call AI with document context"""
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", "")
        anthropic_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        
        # Build document context
        doc_context = ""
        if st.session_state.uploaded_documents:
            for doc_id, doc in st.session_state.uploaded_documents.items():
                content = doc.get('content', '')[:15000]
                doc_context += f"\n[OCR Document: {doc['name']}]\n{content}\n"
        
        messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        messages.append({"role": "user", "content": user_message})
        
        # Try OpenAI
        if openai_key:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            system_msg = SYSTEM_PROMPT
            if doc_context:
                system_msg += f"\n\n{doc_context}"
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_msg}] + messages,
                max_tokens=1500,
                temperature=0.7
            )
            return response.choices[0].message.content
        
        # Try Anthropic
        elif anthropic_key:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            
            full_msg = user_message
            if doc_context:
                full_msg = f"{doc_context}\n\nStudent: {user_message}"
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=messages[:-1] + [{"role": "user", "content": full_msg}]
            )
            return response.content[0].text
        
        else:
            return """👋 **Welcome to OCR Business Revision Buddy!**

I'm here to help you with OCR GCSE Business (J204) revision.

**To enable full AI features:**
Add your API key in Streamlit Settings → Secrets:
```
OPENAI_API_KEY = "your-key"
```
or
```
ANTHROPIC_API_KEY = "your-key"
```

**I can help with:**
- Explaining any OCR Business topic
- Generating practice questions and MCQs  
- Marking your answers with detailed feedback
- All Units from 1.1 to 2.4

What would you like to revise? 📚"""
    
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# Header with restart button
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown("<h2 style='color: #ececf1; margin: 0; padding: 0.5rem 0;'>📘 OCR Business Revision Buddy</h2>", unsafe_allow_html=True)
with col2:
    if st.button("↻ Restart"):
        st.session_state.messages = []
        st.rerun()

# Landing page or chat
if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="landing-container">
        <div class="landing-icon">📘</div>
        <h1 class="landing-title">OCR Business Revision Buddy</h1>
        <p class="landing-subtitle">
            Friendly GCSE OCR Business revision helper with interactive questions and feedback
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Suggestion chips
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📚 Explain aims & objectives (Unit 1.4)", use_container_width=True):
            prompt = "Explain business aims and objectives (Unit 1.4)"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
        
        if st.button("📊 Give me 5 MCQs on Unit 2.2", use_container_width=True):
            prompt = "Give me 5 MCQs on Unit 2.2 - Market research"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with col2:
        if st.button("👥 Test me on Unit 1.5 (Stakeholders)", use_container_width=True):
            prompt = "Test me on Unit 1.5 - Stakeholders in business"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
        
        if st.button("📝 Mark my 9-mark answer", use_container_width=True):
            prompt = "I have a 9-mark answer to be marked"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

else:
    # Display chat messages
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user">
                    <div class="chat-avatar user">👤</div>
                    <div class="chat-content">{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                content = message["content"].replace("\n", "<br>")
                content = content.replace("**", "<strong>").replace("**", "</strong>")
                st.markdown(f"""
                <div class="chat-message assistant">
                    <div class="chat-avatar assistant">📘</div>
                    <div class="chat-content">{content}</div>
                </div>
                """, unsafe_allow_html=True)

# Chat input (always at bottom)
if prompt := st.chat_input("Ask a Business question or request a quiz…"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get AI response
    with st.spinner("✏️ OCR Business Revision Buddy is typing..."):
        response = call_ai(prompt)
    
    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
