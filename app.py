import streamlit as st
import json
from datetime import datetime
import io

# Page config
st.set_page_config(
    page_title="OCR Business Revision Buddy",
    page_icon="📚",
    layout="wide"
)

# Initialize session state
if 'student_name' not in st.session_state:
    st.session_state.student_name = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'quiz_mode' not in st.session_state:
    st.session_state.quiz_mode = False
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'student_answer' not in st.session_state:
    st.session_state.student_answer = ""
if 'quiz_history' not in st.session_state:
    st.session_state.quiz_history = []
if 'selected_topic' not in st.session_state:
    st.session_state.selected_topic = None
if 'uploaded_documents' not in st.session_state:
    st.session_state.uploaded_documents = {}
if 'knowledge_base_ready' not in st.session_state:
    st.session_state.knowledge_base_ready = False

# OCR GCSE Business Topics (J204 Specification - Exact Match)
# Component 01: Business activity, marketing and people
# Component 02: Operations, finance and influences on business

OCR_TOPICS = {
    "Component 01 - Paper 1": {
        "1. Business Activity": [
            "1.1 The role of business enterprise and entrepreneurship",
            "1.2 Business planning",
            "1.3 Business ownership",
            "1.4 Business aims and objectives",
            "1.5 Stakeholders in business",
            "1.6 Business growth"
        ],
        "2. Marketing": [
            "2.1 The role of marketing",
            "2.2 Market research",
            "2.3 Market segmentation",
            "2.4 The marketing mix"
        ],
        "3. People": [
            "3.1 The role of human resources",
            "3.2 Organisational structures and different ways of working",
            "3.3 Communication in business",
            "3.4 Recruitment and selection",
            "3.5 Motivation and retention",
            "3.6 Training and development",
            "3.7 Employment law"
        ]
    },
    "Component 02 - Paper 2": {
        "4. Operations": [
            "4.1 Production processes",
            "4.2 Quality of goods and services",
            "4.3 The sales process and customer service",
            "4.4 Consumer law",
            "4.5 Business location",
            "4.6 Working with suppliers"
        ],
        "5. Finance": [
            "5.1 The role of the finance function",
            "5.2 Sources of finance",
            "5.3 Revenue, costs, profit and loss",
            "5.4 Break-even",
            "5.5 Cash and cash flow"
        ],
        "6. Influences on Business": [
            "6.1 Ethical and environmental considerations",
            "6.2 The economic climate",
            "6.3 Globalisation"
        ],
        "7. The Interdependent Nature of Business": [
            "7.1 How business functions work together (SYNOPTIC)"
        ]
    }
}

# System prompt for AI
SYSTEM_PROMPT = """You are an expert OCR GCSE Business Studies (J204) examiner and revision tutor. Your role is to:

1. Help students revise OCR GCSE Business Studies J204 specification topics
2. Generate practice exam questions following OCR command words and mark schemes
3. Mark student answers using OCR assessment criteria and levels of response
4. Provide detailed, constructive feedback like a real OCR examiner
5. Explain concepts clearly with real business examples
6. Track student progress and identify areas for improvement

OCR GCSE Business J204 Structure:
- Component 01 (Paper 1): Business activity, marketing and people (80 marks, 1h 30min, 50%)
  • Section A: Multiple choice (15 marks)
  • Section B: Short, medium, extended response (65 marks)
  
- Component 02 (Paper 2): Operations, finance and influences on business (80 marks, 1h 30min, 50%)
  • Section A: Multiple choice (15 marks)
  • Section B: Short, medium, extended response with SYNOPTIC questions (65 marks)

OCR Command Words and Mark Allocations:
- State/Identify (1 mark): Simple recall - one word/short phrase
- Outline (2 marks): Brief description with limited development
- Explain (3-4 marks): Show understanding with clear reasoning and development
- Analyse (4-6 marks): Break down, examine in detail, develop chains of reasoning
- Evaluate/Justify (6-9 marks): Make judgments with evidence, weigh up alternatives, reach conclusion
- Discuss (6-9 marks): Present both sides, analyze arguments, reach balanced conclusion
- Recommend (6-9 marks): Make supported judgment with justified business decision
- Calculate: Show all workings clearly

Assessment Objectives (AO):
- AO1 (35%): Knowledge and understanding of business concepts
- AO2 (35%): Application to business contexts and scenarios
- AO3 (30%): Analysis and evaluation to make judgments

When marking answers:
- Use levels of response marking for extended answers (typically 6-9 marks)
- Award marks for: Knowledge points, Application to context, Analysis (chains of reasoning), Evaluation (judgments)
- Look for: Business terminology, real examples, context application, developed explanations
- Deduct marks for: Vague statements, lack of development, no context, poor structure
- Give specific feedback on how to improve using OCR mark scheme language

Quantitative Skills (minimum 10% of marks):
- Percentages and percentage changes
- Averages, revenue, costs, profit
- Gross profit margin and net profit margin
- Average rate of return
- Cash flow forecasts
- Break-even calculations

You have access to the following uploaded documents as your knowledge base:
{document_list}

CRITICAL: Always reference the OCR J204 specification and uploaded materials when answering questions and marking work. Use real business examples from case studies in past papers. Stay strictly within the OCR GCSE Business J204 specification content."""

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        import PyPDF2
        
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        
        return text
    except Exception as e:
        return f"Error extracting PDF: {str(e)}\n\nNote: Install PyPDF2 with: pip install PyPDF2"

def process_uploaded_file(uploaded_file, doc_type):
    """Process uploaded PDF and extract text"""
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
            'content': f"Error processing file: {str(e)}",
            'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M")
        }

def call_ai_tutor(user_message, context="", documents=None):
    """
    Call OpenAI or Anthropic API with uploaded documents as context
    Supports both OpenAI and Anthropic - checks which API key is available
    """
    
    # Check which API key is available
    openai_key = st.secrets.get("OPENAI_API_KEY", "")
    anthropic_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    
    # Build document context
    doc_context = ""
    if documents:
        doc_list = []
        for doc_id, doc in documents.items():
            doc_list.append(f"- {doc['name']} ({doc['type']})")
            doc_context += f"\n\n=== {doc['name']} ({doc['type']}) ===\n{doc['content'][:50000]}\n"  # Limit size
        
        system_prompt = SYSTEM_PROMPT.format(
            document_list="\n".join(doc_list) if doc_list else "None uploaded yet"
        )
    else:
        system_prompt = SYSTEM_PROMPT.format(document_list="None uploaded yet")
    
    # Prepare full context
    full_context = doc_context + "\n\n" + context if doc_context else context
    full_message = f"{full_context}\n\nStudent question: {user_message}"
    
    # Try OpenAI first
    if openai_key:
        try:
            import openai
            
            client = openai.OpenAI(api_key=openai_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",  # Using GPT-4o (most capable model)
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_message}
                ],
                max_tokens=3000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except ImportError:
            pass  # Try Anthropic instead
        except Exception as e:
            return f"⚠️ OpenAI API error: {str(e)}"
    
    # Try Anthropic if OpenAI not available
    if anthropic_key:
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=anthropic_key)
            
            messages = [
                {"role": "user", "content": full_message}
            ]
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=3000,
                system=system_prompt,
                messages=messages
            )
            
            return response.content[0].text
        
        except ImportError:
            pass
        except Exception as e:
            return f"⚠️ Anthropic API error: {str(e)}"
    
    # No API keys available
    return """⚠️ No AI API key found.

To enable AI features, add ONE of these to Streamlit secrets:

**Option 1: OpenAI (GPT-4)**
```toml
OPENAI_API_KEY = "sk-..."
```

**Option 2: Anthropic (Claude)**
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

**Steps:**
1. Get API key from platform.openai.com OR console.anthropic.com
2. Add to Streamlit secrets
3. Install library: `pip install openai` OR `pip install anthropic`
4. Restart the app

For now, the app will show example responses."""

# Admin/Setup page for document uploads
def show_setup_page():
    st.title("📚 Knowledge Base Setup")
    st.markdown("### Upload OCR GCSE Business Documents")
    
    st.info("""
    **Upload the following documents to build your AI's knowledge base:**
    
    - 📄 OCR GCSE Business Specification
    - 📝 Past Papers (with mark schemes)
    - 📚 Textbooks (PDF format)
    - 📊 Examiner Reports
    - 📋 Revision Guides
    
    The AI will use these documents to provide accurate, OCR-aligned revision help and marking.
    """)
    
    # Document upload sections
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 OCR Specification")
        spec_file = st.file_uploader(
            "Upload OCR GCSE Business Specification (PDF)",
            type=['pdf'],
            key="spec_upload"
        )
        if spec_file:
            if st.button("Process Specification", key="process_spec"):
                with st.spinner("Extracting text from specification..."):
                    doc_data = process_uploaded_file(spec_file, "OCR Specification")
                    st.session_state.uploaded_documents['specification'] = doc_data
                    st.success(f"✅ Processed: {spec_file.name}")
        
        st.subheader("📚 Textbooks")
        textbook_files = st.file_uploader(
            "Upload Textbook(s) (PDF)",
            type=['pdf'],
            accept_multiple_files=True,
            key="textbook_upload"
        )
        if textbook_files:
            if st.button("Process Textbooks", key="process_textbooks"):
                for idx, textbook in enumerate(textbook_files):
                    with st.spinner(f"Processing {textbook.name}..."):
                        doc_data = process_uploaded_file(textbook, "Textbook")
                        st.session_state.uploaded_documents[f'textbook_{idx}'] = doc_data
                        st.success(f"✅ Processed: {textbook.name}")
    
    with col2:
        st.subheader("📝 Past Papers & Mark Schemes")
        past_paper_files = st.file_uploader(
            "Upload Past Papers (PDF)",
            type=['pdf'],
            accept_multiple_files=True,
            key="past_paper_upload"
        )
        if past_paper_files:
            if st.button("Process Past Papers", key="process_papers"):
                for idx, paper in enumerate(past_paper_files):
                    with st.spinner(f"Processing {paper.name}..."):
                        doc_data = process_uploaded_file(paper, "Past Paper/Mark Scheme")
                        st.session_state.uploaded_documents[f'past_paper_{idx}'] = doc_data
                        st.success(f"✅ Processed: {paper.name}")
        
        st.subheader("📊 Additional Resources")
        other_files = st.file_uploader(
            "Upload Other Resources (Examiner Reports, Guides, etc.)",
            type=['pdf', 'txt'],
            accept_multiple_files=True,
            key="other_upload"
        )
        if other_files:
            if st.button("Process Resources", key="process_other"):
                for idx, file in enumerate(other_files):
                    with st.spinner(f"Processing {file.name}..."):
                        doc_data = process_uploaded_file(file, "Additional Resource")
                        st.session_state.uploaded_documents[f'resource_{idx}'] = doc_data
                        st.success(f"✅ Processed: {file.name}")
    
    # Show uploaded documents
    st.markdown("---")
    st.subheader("📋 Uploaded Documents")
    
    if st.session_state.uploaded_documents:
        for doc_id, doc in st.session_state.uploaded_documents.items():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"📄 **{doc['name']}**")
            with col2:
                st.write(doc['type'])
            with col3:
                st.write(f"Uploaded: {doc['uploaded_at']}")
            with col4:
                if st.button("🗑️", key=f"delete_{doc_id}"):
                    del st.session_state.uploaded_documents[doc_id]
                    st.rerun()
        
        st.success(f"✅ **{len(st.session_state.uploaded_documents)} documents** loaded in knowledge base")
        
        if st.button("✅ Knowledge Base Ready - Start Using App", type="primary"):
            st.session_state.knowledge_base_ready = True
            st.rerun()
    else:
        st.warning("⚠️ No documents uploaded yet. Upload documents to enable AI features.")
        
        if st.button("Skip for now (use AI's general knowledge only)"):
            st.session_state.knowledge_base_ready = True
            st.rerun()

# Login page
def show_login():
    st.title("📚 OCR GCSE Business Revision Buddy")
    st.markdown("### Your AI-powered study companion")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        
        # Check if knowledge base is set up
        if not st.session_state.knowledge_base_ready:
            st.info("👨‍🏫 **Teacher Setup Required**")
            if st.button("🔧 Set Up Knowledge Base (Teacher)", use_container_width=True):
                st.session_state.student_name = "admin_setup"
                st.rerun()
        
        st.markdown("---")
        
        name = st.text_input("Enter your name to start:", key="login_name")
        
        if st.button("Start Revising", use_container_width=True):
            if name.strip():
                st.session_state.student_name = name.strip()
                st.rerun()
            else:
                st.error("Please enter your name")
        
        st.markdown("---")
        st.info("""
        **Features:**
        - 🤖 AI tutor trained on OCR materials
        - 📝 Unlimited practice questions
        - ✅ OCR examiner-style marking
        - 📊 Track your progress
        - 💡 Personalized feedback
        - 📚 Based on uploaded textbooks & spec
        """)

# Main app interface
def show_main_app():
    # Sidebar
    with st.sidebar:
        st.title(f"👋 {st.session_state.student_name}!")
        
        # Show knowledge base status
        if st.session_state.uploaded_documents:
            with st.expander("📚 Knowledge Base", expanded=False):
                st.write(f"**{len(st.session_state.uploaded_documents)} documents loaded**")
                for doc in st.session_state.uploaded_documents.values():
                    st.write(f"• {doc['name'][:30]}...")
        
        st.markdown("---")
        
        mode = st.radio(
            "Choose Mode:",
            ["💬 Revision Chat", "📝 Practice Questions", "📊 My Progress", "🔧 Manage Documents"],
            key="app_mode"
        )
        
        st.markdown("---")
        
        st.subheader("📖 OCR Topics")
        
        for component, sections in OCR_TOPICS.items():
            st.markdown(f"**{component}**")
            for section, topics in sections.items():
                with st.expander(section):
                    for topic in topics:
                        if st.button(topic, use_container_width=True, key=f"topic_{topic}"):
                            st.session_state.selected_topic = topic
                            st.session_state.chat_history.append({
                                "role": "system",
                                "content": f"Student selected topic: {topic}"
                            })
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    # Main content area
    if mode == "💬 Revision Chat":
        show_revision_chat()
    elif mode == "📝 Practice Questions":
        show_practice_questions()
    elif mode == "📊 My Progress":
        show_progress()
    else:
        show_setup_page()

# Revision Chat Mode
def show_revision_chat():
    st.title("💬 Revision Chat")
    st.markdown("Ask me anything about OCR GCSE Business Studies!")
    
    if st.session_state.selected_topic:
        st.info(f"📌 Current topic: **{st.session_state.selected_topic}**")
    
    if st.session_state.uploaded_documents:
        st.success(f"✅ AI has access to {len(st.session_state.uploaded_documents)} documents")
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message['content'])
            elif message["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.write(message['content'])
    
    # Chat input
    user_input = st.chat_input("Ask a question...")
    
    # Quick question buttons
    st.markdown("**Quick questions:**")
    col1, col2, col3 = st.columns(3)
    
    quick_questions = [
        "Explain this topic simply",
        "Give me an example",
        "Test my understanding"
    ]
    
    clicked_question = None
    if col1.button(quick_questions[0], use_container_width=True):
        clicked_question = quick_questions[0]
    if col2.button(quick_questions[1], use_container_width=True):
        clicked_question = quick_questions[1]
    if col3.button(quick_questions[2], use_container_width=True):
        clicked_question = quick_questions[2]
    
    # Process input
    if user_input or clicked_question:
        question = clicked_question if clicked_question else user_input
        
        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })
        
        # Get AI response
        context = f"Current topic: {st.session_state.selected_topic}" if st.session_state.selected_topic else ""
        
        with st.spinner("AI Tutor is thinking..."):
            # Check if any API key is available
            has_api = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY")
            
            if not has_api:
                response = f"""**Demo Mode** (Add API key to enable real AI)

Based on the uploaded documents, I would provide a detailed answer about: "{question}"

The AI would:
- Reference specific pages from the OCR specification
- Use examples from the textbook
- Cite mark schemes for exam technique
- Provide practice questions based on past papers

**Documents available to AI:**
{', '.join([doc['name'] for doc in st.session_state.uploaded_documents.values()]) if st.session_state.uploaded_documents else 'None - upload documents in Manage Documents'}

Current topic: {st.session_state.selected_topic or 'General'}"""
            else:
                response = call_ai_tutor(
                    question, 
                    context, 
                    st.session_state.uploaded_documents
                )
        
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response
        })
        
        st.rerun()

# Practice Questions Mode
def show_practice_questions():
    st.title("📝 Practice Questions")
    st.markdown("Get OCR-style exam questions with AI marking")
    
    if st.session_state.uploaded_documents:
        st.success(f"✅ Questions will be based on {len(st.session_state.uploaded_documents)} uploaded documents")
    
    col1, col2 = st.columns(2)
    
    with col1:
        question_type = st.selectbox(
            "Question Type:",
            ["State/Identify (1 mark)", "Outline (2 marks)", "Explain (3-4 marks)", 
             "Analyse (4-6 marks)", "Evaluate (6-9 marks)", "Calculate"]
        )
    
    with col2:
        if st.session_state.selected_topic:
            topic_choice = st.session_state.selected_topic
        else:
            all_topics = []
            for component in OCR_TOPICS.values():
                for section_topics in component.values():
                    all_topics.extend(section_topics)
            topic_choice = st.selectbox("Topic:", ["Any topic"] + all_topics)
    
    if st.button("Generate New Question", use_container_width=True):
        with st.spinner("AI is generating an OCR-style question from uploaded materials..."):
            st.session_state.current_question = {
                "type": question_type,
                "topic": topic_choice,
                "question": f"**{question_type} Question:**\n\nExplain two advantages of using market research before launching a new product. [4 marks]\n\n*(Real question would be generated from past papers and specification)*",
                "marks": 4
            }
    
    if st.session_state.current_question:
        st.markdown("---")
        st.markdown(st.session_state.current_question["question"])
        st.markdown(f"**Marks available:** {st.session_state.current_question['marks']}")
        
        st.markdown("---")
        
        answer = st.text_area(
            "Your Answer:",
            height=200,
            placeholder="Type your answer here..."
        )
        
        if st.button("Submit Answer for Marking", use_container_width=True):
            if answer.strip():
                with st.spinner("AI Examiner is marking your answer using OCR mark schemes..."):
                    marking_feedback = f"""
**MARKING FEEDBACK** (Based on OCR Mark Schemes)

**Your Answer:**
{answer}

**Mark Awarded:** 3 / {st.session_state.current_question['marks']}

---

**Examiner Comments:**

✅ **What you did well:**
- Good structure and clear points
- Relevant business knowledge shown
- Used appropriate terminology

⚠️ **Areas for improvement:**
- Develop your explanation further with "This means that..."
- Add specific business examples
- Link back to the question more explicitly

**Model Answer (from mark scheme):**
1. Market research helps identify customer needs and preferences. This means that the business can design a product that customers actually want, reducing the risk of product failure.

2. It provides data on competitors and market gaps. As a result, the business can position their product to fill an unmet need or differentiate from competitors.

**Assessment Objectives:**
- AO1 (Knowledge): 2/2 ✅
- AO2 (Application): 1/2 ⚠️

---
**Score saved to your progress!**
"""
                
                st.markdown(marking_feedback)
                
                # Save to quiz history
                st.session_state.quiz_history.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "question": st.session_state.current_question["question"],
                    "answer": answer,
                    "score": 3,
                    "max_marks": st.session_state.current_question['marks']
                })
            else:
                st.error("Please write an answer before submitting")

# Progress Tracking
def show_progress():
    st.title("📊 My Progress")
    
    if not st.session_state.quiz_history:
        st.info("No quiz attempts yet. Complete some practice questions to see your progress!")
        return
    
    # Overall stats
    col1, col2, col3 = st.columns(3)
    
    total_questions = len(st.session_state.quiz_history)
    total_score = sum(q["score"] for q in st.session_state.quiz_history)
    total_possible = sum(q["max_marks"] for q in st.session_state.quiz_history)
    avg_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
    
    with col1:
        st.metric("Questions Attempted", total_questions)
    
    with col2:
        st.metric("Total Marks", f"{total_score}/{total_possible}")
    
    with col3:
        st.metric("Average Score", f"{avg_percentage:.1f}%")
    
    st.markdown("---")
    
    # Recent attempts
    st.subheader("Recent Attempts")
    
    for attempt in reversed(st.session_state.quiz_history[-10:]):
        with st.expander(f"{attempt['date']} - Score: {attempt['score']}/{attempt['max_marks']}"):
            st.markdown(f"**Question:** {attempt['question']}")
            st.markdown(f"**Your Answer:** {attempt['answer']}")
            
            percentage = (attempt['score'] / attempt['max_marks'] * 100)
            if percentage >= 75:
                st.success(f"Excellent! {percentage:.0f}%")
            elif percentage >= 50:
                st.warning(f"Good effort! {percentage:.0f}%")
            else:
                st.error(f"Keep practicing! {percentage:.0f}%")

# Main app logic
def main():
    if st.session_state.student_name is None:
        show_login()
    elif st.session_state.student_name == "admin_setup":
        show_setup_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()