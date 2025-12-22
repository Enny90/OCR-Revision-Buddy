import streamlit as st
from datetime import datetime
import json
import time

# Typing speed control
TYPING_DELAY = 0.06

def get_dynamic_delay(message):
    length = len(message)
    if length < 80:
        return 0.005  # Much faster for short messages
    elif length < 300:
        return 0.01   # Faster for medium messages
    else:
        return 0.015  # Still reasonably fast for long messages

# Page config - MUST BE FIRST
st.set_page_config(
    page_title="OCR Business Revision Buddy",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state for password
if 'password_attempts' not in st.session_state:
    st.session_state.password_attempts = 0

# Check for admin mode via URL parameter
query_params = st.query_params
is_admin = query_params.get("admin") == "true"

# Initialize session state
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = is_admin
elif is_admin:
    st.session_state.admin_mode = True

if 'messages' not in st.session_state:
    st.session_state.messages = []

# Student identity & session metadata
if 'student_name' not in st.session_state:
    st.session_state.student_name = ""
if 'student_class' not in st.session_state:
    st.session_state.student_class = ""
if 'student_topic' not in st.session_state:
    st.session_state.student_topic = ""
if 'student_info_submitted' not in st.session_state:
    st.session_state.student_info_submitted = False
if 'awaiting_student_info' not in st.session_state:
    st.session_state.awaiting_student_info = True
if 'awaiting_topic' not in st.session_state:
    st.session_state.awaiting_topic = False

# Quiz mode and history
if 'quiz_mode' not in st.session_state:
    st.session_state.quiz_mode = False
if 'quiz_history' not in st.session_state:
    st.session_state.quiz_history = []
if 'current_quiz_set' not in st.session_state:
    st.session_state.current_quiz_set = None

# Pending prompt state
if 'pending_prompt' not in st.session_state:
    st.session_state.pending_prompt = None
if 'pending_source' not in st.session_state:
    st.session_state.pending_source = None

# Flag to hide hero/chips after any interaction
if 'setup_started' not in st.session_state:
    st.session_state.setup_started = False

# NEW: Track which message should show typing effect (store message index)
if 'typing_message_index' not in st.session_state:
    st.session_state.typing_message_index = None

# GitHub document loading function
def load_documents_from_github():
    """Load documents from GitHub using credentials in secrets"""
    error_log = []
    
    try:
        if 'github' not in st.secrets:
            error_log.append("❌ No 'github' section in secrets")
            st.session_state['github_error'] = error_log
            return {}
        
        github_token = st.secrets['github'].get('token', '')
        repo_name = st.secrets['github'].get('repo_name', '')
        
        if not github_token or not repo_name:
            error_log.append("❌ Missing token or repo_name")
            st.session_state['github_error'] = error_log
            return {}
        
        error_log.append(f"📡 Connecting to GitHub repo: {repo_name}")
        
        from github import Github
        import base64
        
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        
        error_log.append(f"✅ Connected to repository: {repo.full_name}")
        
        def get_all_files(path=""):
            all_files = []
            try:
                contents = repo.get_contents(path)
                error_log.append(f"📂 Scanning folder: '{path if path else 'root'}' - found {len(contents)} items")
                for content in contents:
                    if content.type == "dir":
                        error_log.append(f"📁 Entering subfolder: {content.path}")
                        all_files.extend(get_all_files(content.path))
                    elif content.name.endswith(('.txt', '.pdf', '.docx', '.doc', '.md')):
                        error_log.append(f"📄 Found file: {content.name}")
                        all_files.append(content)
                    else:
                        error_log.append(f"⏭️ Skipped (wrong type): {content.name}")
            except Exception as e:
                error_log.append(f"⚠️ Error reading path '{path}': {str(e)}")
            return all_files
        
        files = get_all_files()
        error_log.append(f"📊 Total files to process: {len(files)}")
        documents = {}
        
        for idx, content in enumerate(files):
            try:
                # Handle different file types
                if content.name.endswith('.txt') or content.name.endswith('.md'):
                    text = content.decoded_content.decode('utf-8', errors='ignore')
                    error_log.append(f"✅ Loaded text file: {content.name} ({len(text)} chars)")
                elif content.name.endswith('.pdf'):
                    # For PDFs, we need to decode and extract text
                    import PyPDF2
                    from io import BytesIO
                    pdf_content = BytesIO(content.decoded_content)
                    pdf_reader = PyPDF2.PdfReader(pdf_content)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n\n"
                    error_log.append(f"✅ Loaded PDF: {content.name} ({len(text)} chars)")
                elif content.name.endswith(('.docx', '.doc')):
                    # For Word docs, note that they're present but need conversion
                    text = f"[Word document: {content.name}]\nNote: Word documents need to be converted to .txt or .pdf for processing."
                    error_log.append(f"⚠️ Word doc found (needs conversion): {content.name}")
                else:
                    continue
                
                documents[f"doc_{idx}"] = {
                    'name': content.name,
                    'type': 'GitHub Document',
                    'content': text,
                    'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            except Exception as e:
                error_log.append(f"❌ Error loading {content.name}: {str(e)}")
                continue
        
        error_log.append(f"✅ Successfully loaded {len(documents)} documents")
        st.session_state['github_error'] = error_log
        return documents
    except Exception as e:
        error_log.append(f"❌ Fatal error: {str(e)}")
        st.session_state['github_error'] = error_log
        return {}

# Initialize uploaded documents
if 'uploaded_documents' not in st.session_state:
    try:
        github_docs = load_documents_from_github()
        if github_docs:
            st.session_state.uploaded_documents = github_docs
        elif 'DOCUMENTS_JSON' in st.secrets:
            st.session_state.uploaded_documents = json.loads(st.secrets['DOCUMENTS_JSON'])
        else:
            st.session_state.uploaded_documents = {}
    except:
        st.session_state.uploaded_documents = {}

# Custom CSS
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    section[data-testid="stSidebar"] {display: none;}
    [data-testid="stHeader"] {display: none;}
    
    .stApp {
        background-color: #f7f7f8;
    }
    
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 6rem;
        max-width: 900px;
    }
    
    .hero-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 3rem 1rem 2rem 1rem;
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
    }
    
    .hero-subtitle {
        font-size: 16px;
        color: #6e6e80;
        margin-bottom: 2.5rem;
        max-width: 600px;
        line-height: 1.5;
    }
    
    .stButton button {
        background-color: white;
        border: 1px solid #d1d5db;
        color: #374151;
        border-radius: 24px;
        padding: 0.5rem 1rem;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton button:hover {
        background-color: #f9fafb;
        border-color: #9ca3af;
    }
    
    .chips-container {
        display: flex;
        justify-content: center;
        gap: 0.75rem;
        flex-wrap: nowrap;
        max-width: 900px;
        margin: 0 auto 3rem auto;
        padding: 0 1rem;
    }
    
    .chat-message {
        background-color: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        max-width: 750px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .chat-message.user {
        background-color: #f9fafb;
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
    
    .stChatInputContainer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(to top, #f7f7f8 60%, transparent);
        padding: 1.5rem 1rem;
        z-index: 100;
    }
    
    .stChatInput {
        max-width: 720px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# System prompt
SYSTEM_PROMPT = """You are the OCR Business Revision Buddy, a friendly AI tutor for OCR GCSE Business (J204).

🎓 BEHAVIOUR RULES:
- Only answer OCR GCSE Business (J204) questions
- Use British English always
- Be friendly, supportive, encouraging, clear and structured
- Use OCR command words: Identify, State, Explain, Analyse, Evaluate, Justify

📚 CONTENT:
- Component 1 - Business 1: business activity, marketing and people (01):
  * Units 1.1-1.6: Business activity
  * Units 2.1-2.4: Marketing
  * Units 3.1-3.7: People
- Component 2 - Business 2: operations, finance and influences on business (02):
  * Units 4.1-4.6: Operations
  * Units 5.1-5.5: Finance
  * Units 6.1-6.3: Influences on business
  * Unit 7: The interdependent nature of business
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

🚫 SAFETY:
If non-Business topics: "I'm designed for OCR GCSE Business (J204). What Business topic would you like to revise?"

Use uploaded documents if available for accuracy."""

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        import PyPDF2
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n\n"
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
    """Show admin panel for document management and student tracking"""
    st.markdown("## 🔧 Teacher Dashboard")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Documents", "📊 Quiz History", "👥 Students", "📈 Analytics"])
    
    with tab1:
        st.markdown("### Document Management")
        
        if 'github' in st.secrets:
            st.success(f"✅ Connected to GitHub: `{st.secrets['github']['repo_name']}`")
            st.info(f"📚 {len(st.session_state.uploaded_documents)} documents loaded")
            
            # Show any errors from GitHub loading
            if 'github_error' in st.session_state and st.session_state['github_error']:
                st.warning("**Loading Log:**")
                for error in st.session_state['github_error']:
                    st.write(error)
            
            if st.button("🔄 Reload from GitHub"):
                with st.spinner("Loading documents from GitHub..."):
                    github_docs = load_documents_from_github()
                    if github_docs:
                        st.session_state.uploaded_documents = github_docs
                        st.success(f"✅ Reloaded {len(github_docs)} documents!")
                    else:
                        st.error("⚠️ No documents loaded. Check the log above for details.")
                st.rerun()
        
        if st.session_state.uploaded_documents:
            st.markdown("**Loaded Documents:**")
            for doc_id, doc in st.session_state.uploaded_documents.items():
                st.write(f"- {doc['name']} ({doc['type']})")
        else:
            st.info("No documents currently loaded. Click 'Reload from GitHub' to load documents.")
    
    with tab2:
        st.markdown("### Quiz History & Marking Records")
        
        if st.session_state.quiz_history:
            st.info(f"📝 {len(st.session_state.quiz_history)} quiz attempts recorded")
            
            # Export button and download
            col1, col2 = st.columns([1, 3])
            with col1:
                export_csv = st.button("📥 Export as CSV")
            
            if export_csv:
                import csv
                from io import StringIO
                
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(["Timestamp", "Student Name", "Class", "Topic", "Marking Details"])
                
                for record in st.session_state.quiz_history:
                    writer.writerow([
                        record.get("timestamp", ""),
                        record.get("student_name", ""),
                        record.get("student_class", ""),
                        record.get("topic", ""),
                        record.get("raw_marking_text", "")[:200] + "..."  # Truncate long text
                    ])
                
                csv_data = output.getvalue()
                
                with col2:
                    st.download_button(
                        label="⬇️ Download CSV File",
                        data=csv_data,
                        file_name=f"quiz_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            st.markdown("---")
            
            # Display quiz records
            for idx, record in enumerate(reversed(st.session_state.quiz_history)):
                with st.expander(f"🎯 {record.get('student_name', 'Unknown')} - {record.get('timestamp', '')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Student:** {record.get('student_name', 'N/A')}")
                        st.write(f"**Class:** {record.get('student_class', 'N/A')}")
                    with col2:
                        st.write(f"**Topic:** {record.get('topic', 'N/A')}")
                        st.write(f"**Time:** {record.get('timestamp', 'N/A')}")
                    
                    st.markdown("**Marking/Feedback:**")
                    st.text_area("", record.get('raw_marking_text', ''), height=150, key=f"quiz_{idx}", disabled=True)
        else:
            st.info("No quiz history yet. Students' quiz attempts will appear here.")
    
    with tab3:
        st.markdown("### Student Sessions")
        
        # Get unique students from quiz history
        students = {}
        for record in st.session_state.quiz_history:
            name = record.get('student_name', 'Unknown')
            class_name = record.get('student_class', 'Unknown')
            key = f"{name} ({class_name})"
            
            if key not in students:
                students[key] = {
                    'name': name,
                    'class': class_name,
                    'attempts': 0,
                    'topics': set()
                }
            
            students[key]['attempts'] += 1
            students[key]['topics'].add(record.get('topic', 'Unknown'))
        
        if students:
            st.info(f"👥 {len(students)} unique students have used the app")
            
            # Display student list
            for student_key, data in sorted(students.items()):
                with st.expander(f"👤 {student_key}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Quiz Attempts:** {data['attempts']}")
                    with col2:
                        st.write(f"**Topics Covered:** {', '.join(data['topics'])}")
        else:
            st.info("No student sessions yet. Student data will appear here once they start using the app.")
    
    with tab4:
        st.markdown("### Class Analytics")
        
        if st.session_state.quiz_history:
            # Topic frequency
            topic_count = {}
            class_count = {}
            
            for record in st.session_state.quiz_history:
                topic = record.get('topic', 'Unknown')
                class_name = record.get('student_class', 'Unknown')
                
                topic_count[topic] = topic_count.get(topic, 0) + 1
                class_count[class_name] = class_count.get(class_name, 0) + 1
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📚 Most Popular Topics:**")
                for topic, count in sorted(topic_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                    st.write(f"- {topic}: {count} attempts")
            
            with col2:
                st.markdown("**🏫 Classes Using the App:**")
                for class_name, count in sorted(class_count.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- {class_name}: {count} attempts")
            
            st.markdown("---")
            st.markdown("**📊 Usage Summary:**")
            st.write(f"- Total quiz attempts: {len(st.session_state.quiz_history)}")
            st.write(f"- Unique students: {len(set(r.get('student_name', '') for r in st.session_state.quiz_history))}")
            st.write(f"- Topics covered: {len(topic_count)}")
        else:
            st.info("Analytics will appear here once students start using the app.")
    
    st.markdown("---")
    if st.button("🔄 Exit Teacher Mode"):
        st.session_state.admin_mode = False
        st.rerun()

def record_quiz_history(assistant_message):
    """Record quiz result if it contains marking/scoring"""
    if any(marker in assistant_message for marker in ["Score:", "score:", "/2", "/3", "/6"]):
        quiz_record = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "student_name": st.session_state.get("student_name", ""),
            "student_class": st.session_state.get("student_class", ""),
            "topic": st.session_state.get("student_topic", ""),
            "raw_marking_text": assistant_message
        }
        st.session_state.quiz_history.append(quiz_record)

def simple_markdown_to_html(text):
    """Convert basic markdown to HTML without external libraries"""
    import re
    
    # Replace **bold** with <strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # Replace *italic* with <em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    # Replace newlines with <br>
    text = text.replace('\n', '<br>')
    
    # Handle numbered lists (1. item)
    text = re.sub(r'^(\d+)\.\s+(.+)$', r'<div style="margin-left: 20px;">\1. \2</div>', text, flags=re.MULTILINE)
    
    # Handle bullet points (- item or * item)
    text = re.sub(r'^[-*]\s+(.+)$', r'<div style="margin-left: 20px;">• \1</div>', text, flags=re.MULTILINE)
    
    return text

def show_message_with_typing(message_content, placeholder):
    """Display a message with typing effect"""
    delay = get_dynamic_delay(message_content)
    
    displayed_text = ""
    for char in message_content:
        displayed_text += char
        html_content = simple_markdown_to_html(displayed_text)
        
        placeholder.markdown(f"""
        <div class="chat-message assistant">
            <div class="message-role">📘 OCR Business Buddy</div>
            <div class="message-content">{html_content}▊</div>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(delay)
    
    # Final display without cursor
    html_content = simple_markdown_to_html(displayed_text)
    
    placeholder.markdown(f"""
    <div class="chat-message assistant">
        <div class="message-role">📘 OCR Business Buddy</div>
        <div class="message-content">{html_content}</div>
    </div>
    """, unsafe_allow_html=True)

def call_ai(user_message, stream_placeholder=None):
    """Call AI with document context"""
    try:
        # Show thinking indicator if placeholder provided
        if stream_placeholder:
            stream_placeholder.markdown("""
            <div class="chat-message assistant">
                <div class="message-role">📘 OCR Business Buddy</div>
                <div class="message-content">🤔 Thinking...</div>
            </div>
            """, unsafe_allow_html=True)
        
        openai_key = st.secrets.get("OPENAI_API_KEY", "")
        anthropic_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        
        # Build document context
        doc_context = ""
        if st.session_state.uploaded_documents:
            for doc_id, doc in st.session_state.uploaded_documents.items():
                content = doc.get('content', '')[:15000]
                doc_context += f"\n[OCR Document: {doc['name']}]\n{content}\n"
        
        # Add student context
        student_context = ""
        if st.session_state.get('student_name'):
            student_context = f"\nStudent: {st.session_state.student_name}"
            if st.session_state.get('student_class'):
                student_context += f" (Class {st.session_state.student_class})"
            if st.session_state.get('student_topic'):
                student_context += f"\nFocusing on: {st.session_state.student_topic}"
        
        messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        messages.append({"role": "user", "content": user_message})
        
        # Try OpenAI
        if openai_key:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            system_msg = SYSTEM_PROMPT
            if doc_context:
                system_msg += f"\n\n{doc_context}"
            if student_context:
                system_msg += f"\n\n{student_context}"
            
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
            
            system_msg = SYSTEM_PROMPT
            if student_context:
                system_msg += f"\n\n{student_context}"
            
            full_msg = user_message
            if doc_context:
                full_msg = f"{doc_context}\n\nStudent: {user_message}"
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=system_msg,
                messages=messages[:-1] + [{"role": "user", "content": full_msg}]
            )
            
            return response.content[0].text
        
        else:
            return "⚠️ No API key configured. Please add OPENAI_API_KEY or ANTHROPIC_API_KEY to secrets."
    
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# Main app logic
if st.session_state.admin_mode:
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1 style="color: #202123;">👨‍🏫 Teacher Dashboard</h1>
        <p style="color: #6e6e80;">OCR Business Revision Buddy - Teacher View</p>
    </div>
    """, unsafe_allow_html=True)
    show_admin_panel()

elif not st.session_state.setup_started:
    # Hero section with chips
    st.markdown("""
    <div class="hero-container">
        <div class="hero-icon">📘</div>
        <h1 class="hero-title">OCR Business Revision Buddy</h1>
        <p class="hero-subtitle">
            Friendly GCSE OCR Business revision helper with interactive questions and feedback
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Suggestion chips
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📚 Aims & objectives (1.4)", key="chip1", use_container_width=True):
            st.session_state.setup_started = True
            st.session_state.pending_prompt = "Explain business aims and objectives (Unit 1.4)"
            st.session_state.pending_source = "chip"
            
            response = "👋 Before we start your revision, I need your first name or initials and your class (e.g. 10ABS) so your teacher knows who completed it.\n\nPlease type:\n**\"Name/Initials, Class\"**\n\nExample: \"A.J., 10B1\"\n\nOnce I have that, I'll ask which topic you want to revise!"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.typing_message_index = len(st.session_state.messages) - 1
            st.session_state.awaiting_student_info = True
            st.rerun()
    
    with col2:
        if st.button("👥 Test me on Unit 1.5", key="chip2", use_container_width=True):
            st.session_state.setup_started = True
            st.session_state.pending_prompt = "Test me on Unit 1.5 - Stakeholders in business"
            st.session_state.pending_source = "chip"
            
            response = "👋 Before we start your revision, I need your first name or initials and your class (e.g. 10ABS) so your teacher knows who completed it.\n\nPlease type:\n**\"Name/Initials, Class\"**\n\nExample: \"A.J., 10B1\"\n\nOnce I have that, I'll ask which topic you want to revise!"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.typing_message_index = len(st.session_state.messages) - 1
            st.session_state.awaiting_student_info = True
            st.rerun()
    
    with col3:
        if st.button("📊 5 MCQs on Unit 2.2", key="chip3", use_container_width=True):
            st.session_state.setup_started = True
            st.session_state.pending_prompt = "Give me 5 MCQs on Unit 2.2 - Market research"
            st.session_state.pending_source = "chip"
            
            response = "👋 Before we start your revision, I need your first name or initials and your class (e.g. 10ABS) so your teacher knows who completed it.\n\nPlease type:\n**\"Name/Initials, Class\"**\n\nExample: \"A.J., 10B1\"\n\nOnce I have that, I'll ask which topic you want to revise!"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.typing_message_index = len(st.session_state.messages) - 1
            st.session_state.awaiting_student_info = True
            st.rerun()
    
    with col4:
        if st.button("📝 Mark my 9-mark answer", key="chip4", use_container_width=True):
            st.session_state.setup_started = True
            st.session_state.pending_prompt = "I have a 9-mark answer to be marked"
            st.session_state.pending_source = "chip"
            
            response = "👋 Before we start your revision, I need your first name or initials and your class (e.g. 10ABS) so your teacher knows who completed it.\n\nPlease type:\n**\"Name/Initials, Class\"**\n\nExample: \"A.J., 10B1\"\n\nOnce I have that, I'll ask which topic you want to revise!"
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.typing_message_index = len(st.session_state.messages) - 1
            st.session_state.awaiting_student_info = True
            st.rerun()

else:
    # Chat mode
    col1, col2, col3 = st.columns([8, 1, 1])
    
    with col3:
        if st.button("↻", key="restart_chat", help="Restart"):
            # Reset all session state
            st.session_state.messages = []
            st.session_state.setup_started = False
            st.session_state.student_name = ""
            st.session_state.student_class = ""
            st.session_state.student_topic = ""
            st.session_state.student_info_submitted = False
            st.session_state.awaiting_student_info = True
            st.session_state.awaiting_topic = False
            st.session_state.pending_prompt = None
            st.session_state.pending_source = None
            st.session_state.typing_message_index = None
            st.rerun()
    
    # Session info
    if st.session_state.student_name:
        st.caption(f"👤 {st.session_state.student_name} – {st.session_state.student_class} – {st.session_state.student_topic}")
    
    # Display chat messages with typing effect for flagged message
    for idx, message in enumerate(st.session_state.messages):
        role = "You" if message["role"] == "user" else "OCR Business Buddy"
        role_class = message["role"]
        icon = "👤" if message["role"] == "user" else "📘"
        
        # Check if this message should show typing effect
        should_type = (idx == st.session_state.typing_message_index and message["role"] == "assistant")
        
        if should_type:
            # Show with typing effect
            placeholder = st.empty()
            show_message_with_typing(message["content"], placeholder)
            # Clear the flag after showing typing
            st.session_state.typing_message_index = None
        else:
            # Show normally - convert markdown to HTML using simple converter
            html_content = simple_markdown_to_html(message["content"])
            
            st.markdown(f"""
            <div class="chat-message {role_class}">
                <div class="message-role">{icon} {role}</div>
                <div class="message-content">{html_content}</div>
            </div>
            """, unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Ask a Business question or request a quiz…"):
    
    # Check for teacher mode password first
    teacher_password = st.secrets.get("TEACHER_PASSWORD", "")
    if teacher_password and (prompt.strip().lower() == teacher_password.lower() or prompt.strip() == teacher_password):
        st.session_state.admin_mode = True
        st.rerun()
    
    # If setup hasn't started and student types something, start setup and store their prompt
    elif not st.session_state.setup_started:
        st.session_state.setup_started = True
        
        # Check if it's just a greeting (don't save as pending prompt)
        greeting_words = ['hi', 'hello', 'hey', 'yo', 'hiya', 'greetings']
        is_greeting = prompt.strip().lower() in greeting_words
        
        if not is_greeting:
            # Save meaningful questions/requests for later
            st.session_state.pending_prompt = prompt
            st.session_state.pending_source = "chat"
        
        response = "👋 Welcome to OCR Business Revision Buddy!\n\Before we start your revision, I need your first name or initials and your class (e.g. 10ABS) so your teacher knows who completed it.\n\nPlease type:\n**\"Name/Initials, Class\"**\n\nExample: \"A.J., 10B1\"\n\nOnce I have that, I'll ask which topic you want to revise!"
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.typing_message_index = len(st.session_state.messages) - 1
        st.session_state.awaiting_student_info = True
        st.rerun()
    
    # Check if awaiting student info
    elif st.session_state.get('awaiting_student_info', False):
        if ',' in prompt:
            parts = [p.strip() for p in prompt.split(',', 1)]
            if len(parts) >= 2:
                name_part, class_part = parts[0], parts[1]
                
                is_valid = (
                    len(name_part) < 30 and 
                    len(class_part) < 30 and
                    not any(word in prompt.lower() for word in ['what', 'how', 'why', 'when', 'where', 'explain', 'tell', 'can you'])
                )
                
                if is_valid:
                    st.session_state.student_name = name_part
                    st.session_state.student_class = class_part
                    st.session_state.awaiting_student_info = False
                    
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    
                    # Check if there's a pending prompt - skip topic question
                    if st.session_state.pending_prompt:
                        st.session_state.student_topic = "OCR GCSE Business"
                        st.session_state.student_info_submitted = True
                        
                        response = f"Great! Thanks **{st.session_state.student_name}** from **{st.session_state.student_class}**! 📚"
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Execute pending prompt
                        followup_prompt = st.session_state.pending_prompt
                        st.session_state.messages.append({"role": "user", "content": followup_prompt})
                        
                        # Show thinking indicator
                        thinking_placeholder = st.empty()
                        ai_response = call_ai(followup_prompt, thinking_placeholder)
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        st.session_state.typing_message_index = len(st.session_state.messages) - 1
                        record_quiz_history(ai_response)
                        
                        st.session_state.pending_prompt = None
                        st.session_state.pending_source = None
                        st.rerun()
                    else:
                        # No pending prompt - just greet and ask for topic directly
                        st.session_state.awaiting_topic = True
                        response = f"Hello **{st.session_state.student_name}** from **{st.session_state.student_class}**! 👋\n\nWhat topic would you like to revise today?\n\n- A specific unit (e.g. \"Unit 1.4 - Business aims\")\n- A topic area (e.g. \"Marketing\" or \"Finance\")\n- \"General revision\" for mixed questions\n\nWhat would you like to focus on?"
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.rerun()
    
    # Check if awaiting topic
    elif st.session_state.get('awaiting_topic', False):
        st.session_state.student_topic = prompt
        st.session_state.awaiting_topic = False
        st.session_state.student_info_submitted = True
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        response = f"Perfect! ✅\n\n**Your revision session is set up:**\n- Student: {st.session_state.student_name}\n- Class: {st.session_state.student_class}\n- Topic: {st.session_state.student_topic}\n\nLet's begin! What would you like to do?\n\n- Ask me to explain a concept\n- Request practice questions\n- Get a quiz to test yourself\n- Or just ask me anything about {st.session_state.student_topic}! 🚀"
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Resume pending prompt if exists
        if st.session_state.pending_prompt:
            followup_prompt = st.session_state.pending_prompt
            st.session_state.messages.append({"role": "user", "content": followup_prompt})
            
            # Show thinking indicator
            thinking_placeholder = st.empty()
            ai_response = call_ai(followup_prompt, thinking_placeholder)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            st.session_state.typing_message_index = len(st.session_state.messages) - 1
            record_quiz_history(ai_response)
            
            st.session_state.pending_prompt = None
            st.session_state.pending_source = None
        
        st.rerun()
    
    else:
        # Normal chat flow - student has completed setup
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Show thinking indicator
        thinking_placeholder = st.empty()
        response = call_ai(prompt, thinking_placeholder)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.typing_message_index = len(st.session_state.messages) - 1
        record_quiz_history(response)
        
        st.rerun()
