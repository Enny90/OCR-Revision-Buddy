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

# Custom CSS for light ChatGPT-style interface
st.markdown("""
<style>
    /* Hide all Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    section[data-testid="stSidebar"] {display: none;}
    [data-testid="stHeader"] {display: none;}
    
    /* Main app background - light grey like ChatGPT */
    .stApp {
        background-color: #f7f7f8;
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 6rem;
        max-width: 900px;
    }
    
    /* Hero section - centered */
    .hero-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 3rem 1rem 2rem 1rem;
        position: relative;
    }
    
    .hero-icon {
        font-size: 48px;
        margin-bottom: 1rem;
    }
    
    .hero-title {
        font-size: 32px;
        font-weight: 600;
        color: #202123;
        margin-bottom: 0.5rem;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .hero-subtitle {
        font-size: 16px;
        color: #6e6e80;
        margin-bottom: 2.5rem;
        max-width: 600px;
        line-height: 1.5;
    }
    
    /* Restart button - top right of hero */
    .restart-container {
        position: absolute;
        top: 1rem;
        right: 1rem;
    }
    
    .stButton button {
        background-color: white;
        border: 1px solid #d1d5db;
        color: #374151;
        border-radius: 24px;
        padding: 0.5rem 1rem;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        background-color: #f9fafb;
        border-color: #9ca3af;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Suggestion chips - ONE ROW */
    .chips-container {
        display: flex;
        justify-content: center;
        gap: 0.75rem;
        flex-wrap: nowrap;
        max-width: 900px;
        margin: 0 auto 3rem auto;
        padding: 0 1rem;
    }
    
    .chip-button {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 24px;
        padding: 0.65rem 1.25rem;
        font-size: 13px;
        color: #374151;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        min-width: 0;
        text-align: center;
        line-height: 1.4;
    }
    
    .chip-button:hover {
        background-color: #f9fafb;
        border-color: #d1d5db;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Chat messages */
    .chat-message {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        max-width: 750px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .chat-message.user {
        background-color: #f9fafb;
    }
    
    .chat-message.assistant {
        background-color: white;
    }
    
    .message-role {
        font-weight: 600;
        font-size: 14px;
        color: #374151;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .message-content {
        color: #374151;
        line-height: 1.7;
        font-size: 15px;
    }
    
    .message-content p {
        margin-bottom: 0.75rem;
    }
    
    /* Chat input - fixed at bottom */
    .stChatInputContainer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(to top, #f7f7f8 60%, transparent);
        padding: 1.5rem 1rem 1.5rem 1rem;
        z-index: 100;
    }
    
    .stChatInput {
        max-width: 720px;
        margin: 0 auto;
    }
    
    .stChatInput textarea {
        background-color: white;
        border: 1px solid #d1d5db;
        border-radius: 24px;
        color: #374151;
        padding: 0.75rem 3rem 0.75rem 1rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        font-size: 15px;
    }
    
    .stChatInput textarea:focus {
        border-color: #9ca3af;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    }
    
    .stChatInput button {
        background-color: #10a37f;
        border: none;
        border-radius: 12px;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .stChatInput button:hover {
        background-color: #0d8a6a;
    }
    
    /* Typing indicator */
    .typing-indicator {
        color: #6e6e80;
        font-size: 14px;
        font-style: italic;
        text-align: center;
        padding: 1rem;
    }
    
    /* Remove extra padding */
    .element-container {
        margin-bottom: 0;
    }
    
    /* Ensure no scrollbar on main container */
    .main {
        overflow-x: hidden;
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

# Landing page or chat view
if len(st.session_state.messages) == 0:
    # Hero section
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col3:
        # Restart button (even though no messages yet, for consistency)
        if st.button("↻ Restart"):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="hero-container">
            <div class="hero-icon">📘</div>
            <h1 class="hero-title">OCR Business Revision Buddy</h1>
            <p class="hero-subtitle">
                Friendly GCSE OCR Business revision helper with interactive questions and feedback
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Suggestion chips - ONE ROW
    st.markdown('<div class="chips-container">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📚 Aims & objectives (1.4)", key="chip1", use_container_width=True):
            prompt = "Explain business aims and objectives (Unit 1.4)"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with col2:
        if st.button("👥 Test me on Unit 1.5", key="chip2", use_container_width=True):
            prompt = "Test me on Unit 1.5 - Stakeholders in business"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with col3:
        if st.button("📊 5 MCQs on Unit 2.2", key="chip3", use_container_width=True):
            prompt = "Give me 5 MCQs on Unit 2.2 - Market research"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    with col4:
        if st.button("📝 Mark my 9-mark answer", key="chip4", use_container_width=True):
            prompt = "I have a 9-mark answer to be marked"
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # Show restart button at top right when in chat mode
    col1, col2 = st.columns([9, 1])
    with col2:
        if st.button("↻ Restart", key="restart_chat"):
            st.session_state.messages = []
            st.rerun()
    
    # Display chat messages
    for message in st.session_state.messages:
        role = "You" if message["role"] == "user" else "OCR Business Buddy"
        role_class = message["role"]
        icon = "👤" if message["role"] == "user" else "📘"
        
        st.markdown(f"""
        <div class="chat-message {role_class}">
            <div class="message-role">{icon} {role}</div>
            <div class="message-content">{message["content"]}</div>
        </div>
        """, unsafe_allow_html=True)

# Chat input (always at bottom)
if prompt := st.chat_input("Ask a Business question or request a quiz…"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get AI response
    with st.spinner("✏️ Thinking..."):
        response = call_ai(prompt)
    
    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
