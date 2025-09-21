import os
import time
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="MAGnus - MA Group Knowledge Bot", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
    """Display the MAGnus logo"""
    try:
        # Try to load logo from various sources
        logo_url = "https://raw.githubusercontent.com/yourusername/yourrepo/main/magnuslogo.png"  # Update with your GitHub path
        st.markdown(f"""
        <div class="logo-container">
            <img src="{logo_url}" alt="MAGnus Logo">
        </div>
        """, unsafe_allow_html=True)
    except:
        # Fallback if logo can't be loaded
        st.markdown("""
        <div class="logo-container">
            <h1 style="color: var(--secondary-color); font-family: 'Inter', sans-serif; font-weight: 700;">MAGnus</h1>
        </div>
        """, unsafe_allow_html=True)

def typing_effect(text, placeholder):
    """Display text with typing effect"""
    displayed_text = ""
    for char in text:
        displayed_text += char
        placeholder.markdown(displayed_text + '<span class="typing-indicator"></span>', unsafe_allow_html=True)
        time.sleep(0.02)  # Adjust speed here - 0.02 is quite fast
    
    # Final display without cursor
    placeholder.markdown(displayed_text)

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
        # Use existing assistant
        try:
            assistant = client.beta.assistants.retrieve(assistant_id)
            return assistant
        except Exception as e:
            st.error(f"Could not retrieve assistant {assistant_id}: {e}")
            return None
    else:
        # Instructions for creating assistant in Azure AI Foundry
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
    import datetime
    now = datetime.datetime.now()
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
        # Create thread with messages
        thread = client.beta.threads.create(messages=messages)
        
        # Create run
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
    
    return False, None  # Timeout

def get_assistant_response(client, thread_id):
    """Get the latest assistant message from thread"""
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        if messages.data:
            latest_message = messages.data[0]
            if latest_message.role == 'assistant':
                # Extract text content
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
    ("debug_mode", False),
]:
    if k not in st.session_state:
        st.session_state[k] = v

def logout():
    st.session_state.authenticated = False
    st.session_state.assistant_ready = False
    st.session_state.messages = []
    st.session_state.conversation_state = "initial"
    st.session_state.current_category = None
    st.session_state.thread_id = None
    st.cache_resource.clear()
    st.rerun()

# ---------- Screens ----------
def show_login():
    st.markdown('<h1 class="main-title">🔐 MAGnus Knowledge Bot</h1>', unsafe_allow_html=True)
    
    display_logo()
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.markdown("### Welcome Back!")
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        login_button = st.form_submit_button("🚀 Login & Connect", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if login_button:
        if username == "MAG" and st.secrets.get("LOGIN_PASSWORD", "defaultpassword") == password:
            st.session_state.authenticated = True
            st.session_state.assistant_ready = False
            st.rerun()
        else:
            st.error("Invalid username or password. Please try again.")

def show_assistant_setup():
    st.title("🤖 MAGnus Knowledge Bot")
    st.markdown("### 🔧 Setting up AI Assistant")
    
    prog = st.progress(0)
    status = st.empty()
    
    # Check Azure OpenAI availability
    status.text("Checking Azure OpenAI connection...")
    prog.progress(25)
    
    if not AZURE_OPENAI_AVAILABLE:
        st.error("❌ Azure OpenAI library not available")
        if st.button("🚪 Logout"):
            logout()
        return
    
    # Get Azure client
    status.text("Connecting to Azure OpenAI...")
    prog.progress(50)
    
    client = get_azure_client()
    if not client:
        st.error("❌ Could not connect to Azure OpenAI. Check your credentials.")
        if st.button("🚪 Logout"):
            logout()
        return
    
    # Get or create assistant
    status.text("Setting up AI Assistant...")
    prog.progress(75)
    
    assistant = get_or_create_assistant(client)
    if not assistant:
        if st.button("🚪 Logout"):
            logout()
        return
    
    # Success
    status.text("✅ Assistant ready!")
    prog.progress(100)
    
    st.session_state.assistant_ready = True
    time.sleep(0.5)
    st.rerun()

def show_main_app():
    st.markdown('<h1 class="main-title">🤖 MAGnus - MA Group Knowledge Bot</h1>', unsafe_allow_html=True)
    
    display_logo()
    
    # Control buttons (removed debug toggle)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🚪 Logout"):
            logout()
    with col2:
        if st.button("🔄 Reset Chat"):
            st.session_state.messages = []
            st.session_state.conversation_state = "initial"
            st.session_state.thread_id = None
            st.rerun()

    # Sidebar with system info
    with st.sidebar:
        st.markdown("### 🤖 AI Assistant")
        st.write("**Status:** ✅ Ready")
        st.write("**Source:** Azure AI Foundry")
        st.write("**Search:** File Search Enabled")
        
        st.markdown("---")
        st.markdown("### 📱 Contact")
        st.write("For technical support or questions about MAGnus, contact your IT team.")

    # Initial welcome with time-based greeting
    if not st.session_state.messages and st.session_state.conversation_state == "initial":
        time_greeting = get_time_greeting()
        welcome = f"""Hey there! How are you doing {time_greeting}? 

I'm MAGnus, your friendly AI assistant here to help with anything work-related. What can I help you with?"""
        st.session_state.messages.append({"role": "assistant", "content": welcome})
        st.session_state.conversation_state = "show_options"

    # Chat history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Show option buttons after welcome
    if st.session_state.conversation_state == "show_options":
        st.markdown("### What can I help you with?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤔 I have a Question", use_container_width=True):
                st.session_state.conversation_state = "confirm_question"
                st.rerun()
            if st.button("⚠️ I have an Issue", use_container_width=True):
                st.session_state.conversation_state = "confirm_issue"
                st.rerun()
        
        with col2:
            if st.button("📄 I want to suggest a Change", use_container_width=True):
                st.session_state.conversation_state = "confirm_change"
                st.rerun()
            if st.button("🔧 I have a Problem", use_container_width=True):
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
        
        with st.chat_message("assistant"):
            st.markdown(f"You've chosen **{category_text[category]}**. Is that correct?")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✅ Yes, that's right", use_container_width=True):
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
                    msg = ("Perfect! I love hearing improvement ideas.\n\nThe best way to submit your suggestion is through our Innovation Request form:\n\n🔗 **[Submit Innovation Request](https://www.jotform.com/form/250841782712054)**\n\nThis ensures your idea gets to the right people and gets proper consideration.")
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
            if st.button("❌ No, let me choose again", use_container_width=True):
                st.session_state.conversation_state = "show_options"
                st.rerun()
        return

    # Input for questions
    if st.session_state.conversation_state == "ready_for_questions":
        placeholder = "Type your question here..."
    else:
        placeholder = "Hello! How can I help you today?"
    user_input = st.chat_input(placeholder)
    if not user_input:
        return

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Handle questions with the Azure Assistant
    if st.session_state.conversation_state == "ready_for_questions":
        if not AZURE_OPENAI_AVAILABLE:
            with st.chat_message("assistant"):
                st.error("AI service is not available.")
            return

        client = get_azure_client()
        if not client:
            with st.chat_message("assistant"):
                st.error("Could not connect to Azure OpenAI service.")
            return

        assistant = get_or_create_assistant(client)
        if not assistant:
            with st.chat_message("assistant"):
                st.error("AI Assistant is not properly configured.")
            return

        # Convert messages to OpenAI format for the assistant
        assistant_messages = []
        for msg in st.session_state.messages:
            if msg["role"] in ["user", "assistant"]:
                assistant_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        with st.chat_message("assistant"):
            with st.spinner("Let me check our company documents for you..."):
                # Create thread and run
                thread_id, run_id = create_thread_and_run(
                    client, 
                    assistant.id, 
                    assistant_messages
                )
                
                if not thread_id or not run_id:
                    st.error("Failed to start AI Assistant.")
                    return
                
                # Store thread ID for potential follow-ups
                st.session_state.thread_id = thread_id
                
                if st.session_state.debug_mode:
                    st.write(f"🔍 Thread ID: {thread_id}")
                    st.write(f"🔍 Run ID: {run_id}")
                
                # Wait for completion
                success, run_result = wait_for_run_completion(client, thread_id, run_id)
                
                if not success:
                    if run_result:
                        st.error(f"Assistant run failed: {run_result.status}")
                        if st.session_state.debug_mode and hasattr(run_result, 'last_error'):
                            st.write(f"Error details: {run_result.last_error}")
                    else:
                        st.error("Assistant run timed out or failed.")
                    return
                
                # Get the response
                response = get_assistant_response(client, thread_id)
                
                if response:
                    # Use typing effect for the response
                    response_placeholder = st.empty()
                    typing_effect(response, response_placeholder)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("Could not retrieve assistant response.")

    # Footer
    st.markdown("---")
    st.caption(f"MAGnus Knowledge Bot • Powered by Azure AI Foundry • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ---------- Router ----------
if not st.session_state.authenticated:
    show_login()
elif not st.session_state.assistant_ready:
    show_assistant_setup()
else:
    show_main_app()
