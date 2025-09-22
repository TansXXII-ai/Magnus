import os
import time
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="MAGnus - MA Group Knowledge Bot", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Remove all sidebar CSS - we're switching to a top bar approach
st.markdown("""
<style>
/* Hide the sidebar completely */
section[data-testid="stSidebar"] {
    display: none !important;
}

/* Top bar styling */
.top-bar {
    background: linear-gradient(135deg, #272557 0%, #1e1f4a 100%);
    padding: 1rem 2rem;
    border-radius: 15px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 15px -5px rgba(39, 37, 87, 0.3);
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}

.top-bar-section {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 600;
}

.status-dot {
    width: 8px;
    height: 8px;
    background: #10b981;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    min-width: 120px;
}

.stat-item {
    text-align: center;
    font-size: 0.85rem;
}

.stat-number {
    font-weight: 700;
    font-size: 1.1rem;
    color: #64b5f6;
}

.quick-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.quick-action-btn {
    background: rgba(119, 158, 184, 0.2);
    color: white;
    border: 1px solid rgba(119, 158, 184, 0.4);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
}

.quick-action-btn:hover {
    background: rgba(119, 158, 184, 0.4);
    transform: translateY(-1px);
}

/* Mobile responsive */
@media (max-width: 768px) {
    .top-bar {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .top-bar-section {
        width: 100%;
        justify-content: space-between;
    }
}
</style>
""", unsafe_allow_html=True)

def load_css():
    """Load external CSS file"""
    try:
        with open('styles.css') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("CSS file not found. Please ensure 'styles.css' is in the same directory as your app.")

# Load CSS
load_css()

def display_logo():
    """Display the MAGnus logo with enhanced styling"""
    try:
        if os.path.exists("magnuslogo.png"):
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                st.image("magnuslogo.png", width=250, use_container_width=False)
        else:
            st.markdown("""
            <div class="logo-text-container">
                <h1 class="logo-text">MAGnus AI</h1>
                <p class="logo-subtitle">Intelligent Assistant</p>
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.markdown("""
        <div class="logo-text-container">
            <h1 class="logo-text">MAGnus AI</h1>
            <p class="logo-subtitle">Intelligent Assistant</p>
        </div>
        """, unsafe_allow_html=True)

def create_avatar_chip(role):
    """Create enhanced avatar chip HTML"""
    if role == "user":
        return '<div class="avatar-chip user"><i class="user-icon">👤</i> You</div>'
    else:
        return '<div class="avatar-chip assistant"><i class="bot-icon">🤖</i> MAGnus</div>'

def display_message_with_custom_avatar(role, content):
    """Display chat message with enhanced custom avatar chip"""
    avatar_html = create_avatar_chip(role)
    message_class = "user-message" if role == "user" else "assistant-message"
    timestamp = datetime.now().strftime('%H:%M')
    
    st.markdown(f"""
    <div class="chat-message-container {message_class}">
        <div class="avatar-container">
            {avatar_html}
        </div>
        <div class="message-content">
            {content}
        </div>
        <div class="message-timestamp">
            {timestamp}
        </div>
    </div>
    """, unsafe_allow_html=True)

def typing_effect_with_avatar(text, role):
    """Display text with typing effect and custom avatar"""
    avatar_html = create_avatar_chip(role)
    timestamp = datetime.now().strftime('%H:%M')
    
    container = st.empty()
    
    # Show typing indicator first
    container.markdown(f"""
    <div class="chat-message-container assistant-message">
        <div class="avatar-container">
            {avatar_html}
        </div>
        <div class="message-content">
            <div class="typing-indicator-container">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    time.sleep(1)
    
    # Show the full message
    container.markdown(f"""
    <div class="chat-message-container assistant-message">
        <div class="avatar-container">
            {avatar_html}
        </div>
        <div class="message-content">
            {text}
        </div>
        <div class="message-timestamp">
            {timestamp}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------- Dependencies ----------
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except Exception:
    AZURE_OPENAI_AVAILABLE = False

# ---------- Utils ----------
def get_secret(key, default=None):
    return os.getenv(key) or st.secrets.get(key, default)

@st.cache_resource
def get_azure_client():
    """Initialize Azure OpenAI client"""
    if not AZURE_OPENAI_AVAILABLE:
        return None
    
    api_key = get_secret("AZURE_OPENAI_API_KEY")
    endpoint = get_secret("AZURE_OPENAI_ENDPOINT")
    api_version = get_secret("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
    
    if not api_key or not endpoint:
        return None
    
    return AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )

def get_or_create_assistant(client):
    """Get existing assistant or create new one with file search"""
    assistant_id = get_secret("AZURE_ASSISTANT_ID")
    
    if assistant_id:
        try:
            assistant = client.beta.assistants.retrieve(assistant_id)
            return assistant
        except Exception as e:
            st.error(f"Could not retrieve assistant {assistant_id}: {e}")
            return None
    else:
        st.error("""
        **Assistant not configured!**
        
        Please create an Assistant in Azure AI Foundry with:
        1. Upload your documents to Data files
        2. Create an Assistant with file search enabled
        3. Add the Assistant ID to your secrets as 'AZURE_ASSISTANT_ID'
        
        See: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/file-search
        """)
        return None

def get_time_greeting():
    """Get time-appropriate greeting"""
    now = datetime.now()
    hour = now.hour
    
    if 5 <= hour < 12:
        return "this morning"
    elif 12 <= hour < 17:
        return "this afternoon"
    elif 17 <= hour < 21:
        return "this evening"
    else:
        return "today"

def create_thread_and_run(client, assistant_id, messages):
    """Create a thread and run with the assistant"""
    try:
        thread = client.beta.threads.create(messages=messages)
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        return thread.id, run.id
    except Exception as e:
        st.error(f"Error creating thread and run: {e}")
        return None, None

def wait_for_run_completion(client, thread_id, run_id, max_wait=60):
    """Wait for assistant run to complete"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            
            if run.status == 'completed':
                return True, run
            elif run.status in ['failed', 'cancelled', 'expired']:
                return False, run
            elif run.status in ['queued', 'in_progress']:
                time.sleep(1)
                continue
            else:
                st.warning(f"Unknown run status: {run.status}")
                time.sleep(1)
                
        except Exception as e:
            st.error(f"Error checking run status: {e}")
            return False, None
    
    return False, None

def get_assistant_response(client, thread_id):
    """Get the latest assistant message from thread"""
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        if messages.data:
            latest_message = messages.data[0]
            if latest_message.role == 'assistant':
                content_parts = []
                for content in latest_message.content:
                    if content.type == 'text':
                        content_parts.append(content.text.value)
                return "\n".join(content_parts)
        return None
    except Exception as e:
        st.error(f"Error retrieving assistant response: {e}")
        return None

# ---------- State ----------
for k, v in [
    ("authenticated", False),
    ("assistant_ready", False),
    ("messages", []),
    ("conversation_state", "initial"),
    ("current_category", None),
    ("thread_id", None),
    ("session_stats", {"questions": 0, "responses": 0}),
]:
    if k not in st.session_state:
        st.session_state[k] = v

def logout():
    """Enhanced logout with confirmation"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_resource.clear()
    st.rerun()

def reset_chat():
    """Enhanced chat reset"""
    st.session_state.messages = []
    st.session_state.conversation_state = "initial"
    st.session_state.current_category = None
    st.session_state.thread_id = None
    st.session_state.session_stats = {"questions": 0, "responses": 0}

# ---------- Screens ----------
def show_login():
    """Enhanced login screen"""
    st.markdown("""
    <div class="login-page-container">
        <div class="login-header">
            <h1 class="login-title">🤖 MAGnus Knowledge Bot</h1>
            <p class="login-subtitle">Your intelligent assistant for MA Group knowledge</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    display_logo()
    
    with st.container():
        st.markdown("""
        <div class="login-form-container">
            <div class="login-form-header">
                <h3>Welcome Back</h3>
                <p>Please sign in to access your AI assistant</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=True):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                login_button = st.form_submit_button("🚀 Sign In & Connect", use_container_width=True)
    
    if login_button:
        if username == "MAG" and st.secrets.get("LOGIN_PASSWORD", "defaultpassword") == password:
            st.session_state.authenticated = True
            st.session_state.assistant_ready = False
            st.success("✅ Login successful! Initializing your assistant...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Invalid username or password. Please try again.")

def show_assistant_setup():
    """Enhanced assistant setup screen"""
    st.markdown("""
    <div class="setup-container">
        <h1 class="setup-title">🤖 MAGnus Knowledge Bot</h1>
        <h3 class="setup-subtitle">🔧 Initializing AI Assistant</h3>
    </div>
    """, unsafe_allow_html=True)
    
    progress_container = st.container()
    
    with progress_container:
        prog = st.progress(0, "Starting initialization...")
        status = st.empty()
        
        # Check Azure OpenAI availability
        status.info("🔍 Checking Azure OpenAI connection...")
        prog.progress(25, "Checking Azure OpenAI...")
        time.sleep(0.5)
        
        if not AZURE_OPENAI_AVAILABLE:
            status.error("❌ Azure OpenAI library not available")
            if st.button("🚪 Return to Login"):
                logout()
            return
        
        # Get Azure client
        status.info("🔗 Connecting to Azure OpenAI...")
        prog.progress(50, "Connecting to Azure...")
        time.sleep(0.5)
        
        client = get_azure_client()
        if not client:
            status.error("❌ Could not connect to Azure OpenAI. Check your credentials.")
            if st.button("🚪 Return to Login"):
                logout()
            return
        
        # Get or create assistant
        status.info("⚙️ Setting up AI Assistant...")
        prog.progress(75, "Setting up assistant...")
        time.sleep(0.5)
        
        assistant = get_or_create_assistant(client)
        if not assistant:
            if st.button("🚪 Return to Login"):
                logout()
            return
        
        # Success
        status.success("✅ Assistant ready!")
        prog.progress(100, "Ready!")
        time.sleep(0.5)
        
        st.session_state.assistant_ready = True
        st.rerun()

def show_main_app():
    """Enhanced main application interface using pure Streamlit components"""
    
    # Get session stats
    user_msgs = len([m for m in st.session_state.messages if m["role"] == "user"])
    ai_msgs = len([m for m in st.session_state.messages if m["role"] == "assistant"])
    
    # Create top bar using pure Streamlit with targeted CSS
    st.markdown("""
    <style>
    .top-status-bar {
        background: linear-gradient(135deg, #272557 0%, #1e1f4a 100%) !important;
        padding: 1rem !important;
        border-radius: 15px !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 4px 15px -5px rgba(39, 37, 87, 0.3) !important;
    }
    .top-status-bar .stMarkdown {
        color: white !important;
    }
    .top-status-bar .stMetric {
        background: rgba(255,255,255,0.1) !important;
        padding: 0.5rem !important;
        border-radius: 8px !important;
        text-align: center !important;
    }
    .top-status-bar .stMetric label {
        color: white !important;
        font-size: 0.8rem !important;
    }
    .top-status-bar .stMetric div[data-testid="metric-container"] > div {
        color: #64b5f6 !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create container with CSS class
    st.markdown('<div class="top-status-bar">', unsafe_allow_html=True)
    
    # Use Streamlit columns for layout
    status_col, info_col, stats_col1, stats_col2 = st.columns([2, 4, 1, 1])
    
    with status_col:
        st.markdown("🟢 **MAGnus Online**")
    
    with info_col:
        st.markdown("GPT-4 Turbo • Azure AI Foundry • File Search Enabled")
    
    with stats_col1:
        st.metric("Questions", user_msgs)
    
    with stats_col2:
        st.metric("Responses", ai_msgs)
    
    # Close container
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add action buttons below the main bar
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        if st.button("🚪 Logout", use_container_width=True):
            logout()
    
    with col2:
        if st.button("🔄 Reset Chat", use_container_width=True):
            reset_chat()
            st.rerun()
    
    with col3:
        if st.button("💡 Help", use_container_width=True):
            st.info("💬 Type your work-related questions in the chat below!")
    
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_resource.clear()
            st.rerun()
    
    with col5:
        if st.button("📈 Export", use_container_width=True):
            if st.session_state.messages:
                export_data = {
                    "timestamp": datetime.now().isoformat(),
                    "messages": st.session_state.messages
                }
                st.download_button(
                    "📥 Download Chat History",
                    data=str(export_data),
                    file_name=f"magnus_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.info("No messages to export")
    
    st.divider()
    
    # Header with gradient background
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">🤖 MAGnus AI Assistant</h1>
        <p class="main-subtitle">Your intelligent companion for MA Group knowledge</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat area (removed control panel section)
    chat_container = st.container()
    
    with chat_container:
        # Initial welcome message
        if not st.session_state.messages and st.session_state.conversation_state == "initial":
            time_greeting = get_time_greeting()
            welcome = f"""👋 **Welcome to MAGnus!**

Hey there! How are you doing {time_greeting}? 

I'm MAGnus, your friendly AI assistant here to help with anything work-related. What can I help you with today?"""
            
            st.session_state.messages.append({"role": "assistant", "content": welcome})
            st.session_state.conversation_state = "show_options"

        # Display chat history
        for m in st.session_state.messages:
            display_message_with_custom_avatar(m["role"], m["content"])

        # Show option buttons after welcome
        if st.session_state.conversation_state == "show_options":
            st.markdown("""
            <div class="options-container">
                <h3>What can I help you with today?</h3>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🤔 I have a Question", use_container_width=True, key="question_btn"):
                    st.session_state.conversation_state = "confirm_question"
                    st.rerun()
                if st.button("⚠️ I have an Issue", use_container_width=True, key="issue_btn"):
                    st.session_state.conversation_state = "confirm_issue"
                    st.rerun()
            
            with col2:
                if st.button("📄 I want to suggest a Change", use_container_width=True, key="change_btn"):
                    st.session_state.conversation_state = "confirm_change"
                    st.rerun()
                if st.button("🔧 I have a Problem", use_container_width=True, key="problem_btn"):
                    st.session_state.conversation_state = "confirm_problem"
                    st.rerun()
            return

        # Confirmation flows
        if st.session_state.conversation_state.startswith("confirm_"):
            category = st.session_state.conversation_state.replace("confirm_", "")
            category_text = {
                "question": "Question - you need information or guidance",
                "change": "Change - you want to suggest an improvement",
                "issue": "Issue - something isn't working as expected", 
                "problem": "Problem - you're experiencing a technical difficulty"
            }
            
            display_message_with_custom_avatar("assistant", f"You've chosen **{category_text[category]}**. Is that correct?")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("✅ Yes, that's right", use_container_width=True, key=f"confirm_{category}"):
                    st.session_state.current_category = category
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"You've chosen **{category_text[category]}**. Is that correct?"
                    })
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": "Yes, that's right"
                    })
                    
                    if category == "change":
                        msg = """Perfect! I love hearing improvement ideas.

The best way to submit your suggestion is through our Innovation Request form:

🔗 **[Submit Innovation Request](https://www.jotform.com/form/250841782712054)**

This ensures your idea gets to the right people and gets proper consideration."""
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                        st.session_state.conversation_state = "completed"
                    else:
                        if category == "question":
                            msg = "Great! What would you like to know? Just ask me anything about work processes, systems, or policies."
                        elif category == "issue":
                            msg = "I understand you're having an issue. Can you tell me what's happening? I'll help you figure it out."
                        else:  # problem
                            msg = "I'm here to help with your problem. What's going wrong? Let me see what I can find to help."
                        
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                        st.session_state.conversation_state = "ready_for_questions"
                    st.rerun()
            
            with col2:
                if st.button("❌ No, let me choose again", use_container_width=True, key=f"reject_{category}"):
                    st.session_state.conversation_state = "show_options"
                    st.rerun()
            return

        # Chat input
        placeholder = "Type your question here..." if st.session_state.conversation_state == "ready_for_questions" else "Hello! How can I help you today?"
        user_input = st.chat_input(placeholder)
        
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            display_message_with_custom_avatar("user", user_input)

            # Handle AI responses
            if st.session_state.conversation_state == "ready_for_questions":
                if not AZURE_OPENAI_AVAILABLE:
                    display_message_with_custom_avatar("assistant", "❌ AI service is not available.")
                    return

                client = get_azure_client()
                if not client:
                    display_message_with_custom_avatar("assistant", "❌ Could not connect to Azure OpenAI service.")
                    return

                assistant = get_or_create_assistant(client)
                if not assistant:
                    display_message_with_custom_avatar("assistant", "❌ AI Assistant is not properly configured.")
                    return

                # Convert messages for assistant
                assistant_messages = []
                for msg in st.session_state.messages:
                    if msg["role"] in ["user", "assistant"]:
                        assistant_messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })

                # Show loading message
                loading_container = st.empty()
                loading_container.markdown("""
                <div class="chat-message-container assistant-message">
                    <div class="avatar-container">
                        <div class="avatar-chip assistant"><i class="bot-icon">🤖</i> MAGnus</div>
                    </div>
                    <div class="message-content">
                        <div class="typing-indicator-container">
                            🔍 Searching company documents...
                            <div class="loading-dots">
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.spinner("Processing..."):
                    # Create thread and run
                    thread_id, run_id = create_thread_and_run(client, assistant.id, assistant_messages)
                    
                    if thread_id and run_id:
                        st.session_state.thread_id = thread_id
                        success, run_result = wait_for_run_completion(client, thread_id, run_id)
                        
                        if success:
                            response = get_assistant_response(client, thread_id)
                            if response:
                                loading_container.empty()
                                typing_effect_with_avatar(response, "assistant")
                                st.session_state.messages.append({"role": "assistant", "content": response})
                            else:
                                loading_container.markdown("❌ Could not retrieve assistant response.")
                        else:
                            error_msg = f"Assistant run failed: {run_result.status}" if run_result else "Assistant run timed out."
                            loading_container.markdown(f"❌ {error_msg}")

    # Enhanced footer
    st.markdown("---")
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    with footer_col1:
        st.caption("🤖 MAGnus Knowledge Bot v2.0")
    with footer_col2:
        st.caption("⚡ Powered by Azure AI Foundry")
    with footer_col3:
        st.caption(f"🕐 Session started: {datetime.now().strftime('%H:%M')}")

# ---------- Router ----------
if not st.session_state.authenticated:
    show_login()
elif not st.session_state.assistant_ready:
    show_assistant_setup()
else:
    show_main_app()
