def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        import PyPDF2
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            try:
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            except:
                text += f"[Error reading page {page_num + 1}]\n"
        return text if len(text.strip()) > 100 else f"⚠️ Only {len(text)} characters extracted."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def process_uploaded_file(uploaded_file, doc_type):
    """Process uploaded file"""
    try:
        if uploaded_file.type == "application/pdf":
            text_content = extract_text_from_pdf(uploaded_file)
        else:
            text_content = uploaded_file.read().decode('utf-8')
        
        return {
            'name': uploaded_file.name,
            'type': doc_type,
            'content': text_content,
            'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    except Exception as e:
        return {
            'name': uploaded_file.name,
            'type': doc_type,
            'content': f"Error: {str(e)}",
            'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M")
        }

def show_admin_panel():
    """Show admin panel for document management"""
    st.markdown("---")
    st.markdown("## 🔧 Admin Panel - Document Management")
    st.info("👨‍🏫 Teacher Mode: Upload OCR materials for the AI to use")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### Upload Documents")
        
        # Document upload sections
        doc_type = st.selectbox(
            "Document Type:",
            ["OCR Specification", "Past Paper/Mark Scheme", "Textbook", "Revision Guide", "Other"]
        )
        
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            key="admin_upload"
        )
        
        if uploaded_files:
            if st.button("📤 Process Documents", type="primary"):
                with st.spinner("Processing documents..."):
                    for uploaded_file in uploaded_files:
                        doc_data = process_uploaded_file(uploaded_file, doc_type)
                        doc_id = f"doc_{len(st.session_state.uploaded_documents)}"
                        st.session_state.uploaded_documents[doc_id] = doc_data
                        
                        chars = len(doc_data['content'])
                        if chars > 1000:
                            st.success(f"✅ {uploaded_file.name}: {chars:,} characters")
                        else:
                            st.warning(f"⚠️ {uploaded_file.name}: Only {chars} characters")
    
    with col2:
        st.markdown("### Quick Actions")
        
        if st.button("🔄 Exit Admin Mode"):
            st.session_state.admin_mode = False
            st.rerun()
        
        if st.button("🗑️ Clear All Documents"):
            st.session_state.uploaded_documents = {}
            st.success("Documents cleared!")
            st.rerun()
    
    # Show uploaded documents
    st.markdown("---")
    st.markdown("### 📋 Current Documents")
    
    if st.session_state.uploaded_documents:
        for doc_id, doc in st.session_state.uploaded_documents.items():
            with st.expander(f"📄 {doc['name']} ({doc['type']})"):
                st.write(f"**Characters:** {len(doc.get('content', '')):,}")
                st.write(f"**Uploaded:** {doc['uploaded_at']}")
                st.text_area(
                    "Preview:",
                    doc.get('content', '')[:500] + "...",
                    height=100,
                    key=f"preview_{doc_id}"
                )
                if st.button(f"🗑️ Delete", key=f"delete_{doc_id}"):
                    del st.session_state.uploaded_documents[doc_id]
                    st.rerun()
        
        st.success(f"✅ {len(st.session_state.uploaded_documents)} documents loaded")
        
        # Generate save code
        st.markdown("---")
        st.markdown("### 💾 Save Permanently to Secrets")
        
        if st.button("📋 Generate Save Code", type="primary"):
            docs_json = json.dumps(st.session_state.uploaded_documents, separators=(',', ':'))
            
            st.code(f'DOCUMENTS_JSON = """{docs_json}"""', language="toml")
            
            st.info("""
            **To save permanently:**
            1. Copy the code above
            2. Go to Settings → Secrets
            3. Paste at the bottom
            4. Click Save
            5. Documents will load automatically!
            """)
    else:
        st.warning("⚠️ No documents uploaded yet")
    
    st.markdown("---")
    st.caption("💡 Tip: Add `?admin=true` to the URL to access this panel anytime")

# System promptimport streamlit as st
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="OCR Business Revision Buddy",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Check for admin mode via URL parameter
query_params = st.query_params
is_admin = query_params.get("admin") == "true"

# Also check session state for admin mode
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = is_admin
elif is_admin:
    st.session_state.admin_mode = True

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
    
    /* Typing cursor animation */
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    .blinking-cursor {
        animation: blink 1s step-start infinite;
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

def call_ai(user_message, stream_placeholder=None):
    """Call AI with document context and streaming"""
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
        
        # Try OpenAI with streaming
        if openai_key:
            import openai
            import time
            client = openai.OpenAI(api_key=openai_key)
            
            system_msg = SYSTEM_PROMPT
            if doc_context:
                system_msg += f"\n\n{doc_context}"
            
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_msg}] + messages,
                max_tokens=1500,
                temperature=0.7,
                stream=True
            )
            
            # Stream the response
            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    if stream_placeholder:
                        stream_placeholder.markdown(f"""
                        <div class="chat-message assistant">
                            <div class="message-role">📘 OCR Business Buddy</div>
                            <div class="message-content">{full_response}▊</div>
                        </div>
                        """, unsafe_allow_html=True)
                    time.sleep(0.05)  # More deliberate typing speed
            
            return full_response
        
        # Try Anthropic with streaming
        elif anthropic_key:
            import anthropic
            import time
            client = anthropic.Anthropic(api_key=anthropic_key)
            
            full_msg = user_message
            if doc_context:
                full_msg = f"{doc_context}\n\nStudent: {user_message}"
            
            full_response = ""
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=messages[:-1] + [{"role": "user", "content": full_msg}]
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    if stream_placeholder:
                        stream_placeholder.markdown(f"""
                        <div class="chat-message assistant">
                            <div class="message-role">📘 OCR Business Buddy</div>
                            <div class="message-content">{full_response}▊</div>
                        </div>
                        """, unsafe_allow_html=True)
                    time.sleep(0.05)  # More deliberate typing speed
            
            return full_response
        
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
if st.session_state.admin_mode:
    # Show admin panel
    st.markdown("""
    <div style="text-align: center; padding: 2rem 1rem;">
        <h1 style="color: #202123; font-size: 32px; font-weight: 600; margin-bottom: 0.5rem;">
            📚 OCR Business Revision Buddy
        </h1>
        <p style="color: #6e6e80; font-size: 16px; margin-bottom: 2rem;">
            Admin Panel - Document Management
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    show_admin_panel()

elif len(st.session_state.messages) == 0:
    # Hero section
    col1, col2, col3 = st.columns([1, 6, 1])
    
    with col3:
        # Secret admin button (looks like restart)
        if st.button("⚙️", key="secret_admin", help="Admin Panel"):
            st.session_state.admin_mode = True
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
    col1, col2, col3 = st.columns([8, 1, 1])
    
    with col2:
        # Secret admin button
        if st.button("⚙️", key="admin_chat", help="Admin"):
            st.session_state.admin_mode = True
            st.rerun()
    
    with col3:
        if st.button("↻", key="restart_chat", help="Restart"):
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
    
    # Show user message immediately
    st.markdown(f"""
    <div class="chat-message user">
        <div class="message-role">👤 You</div>
        <div class="message-content">{prompt}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Create placeholder for streaming response
    response_placeholder = st.empty()
    
    # Show typing indicator
    response_placeholder.markdown("""
    <div class="typing-indicator">✏️ Thinking...</div>
    """, unsafe_allow_html=True)
    
    # Get AI response with streaming
    response = call_ai(prompt, stream_placeholder=response_placeholder)
    
    # Clear placeholder and show final message
    response_placeholder.empty()
    
    # Add assistant message to history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
