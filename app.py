import os
import time
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="MAGnus - MA Group Knowledge Bot", page_icon="🤖", layout="wide")

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
    st.title("🔐 MAGnus Knowledge Bot - Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("🚀 Login & Connect", use_container_width=True)
    
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
    st.title("🤖 MAGnus - MA Group Knowledge Bot")
    
    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🚪 Logout"):
            logout()
    with col2:
        if st.button("🔍 Toggle Debug"):
            st.session_state.debug_mode = not st.session_state.debug_mode
            st.rerun()
    with col3:
        if st.button("🔄 Reset Chat"):
            st.session_state.messages = []
            st.session_state.conversation_state = "initial"
            st.session_state.thread_id = None
            st.rerun()

    # Sidebar with system info
    st.sidebar.header("🤖 AI Assistant")
    st.sidebar.write("Status: ✅ Ready")
    st.sidebar.write("Source: Azure AI Foundry")
    st.sidebar.write("Search: File Search Enabled")
    
    if st.session_state.debug_mode:
        st.sidebar.header("🔍 Debug Info")
        st.sidebar.write(f"Thread ID: {st.session_state.thread_id}")
        st.sidebar.write(f"Messages: {len(st.session_state.messages)}")
        st.sidebar.write(f"State: {st.session_state.conversation_state}")

    # Initial welcome
    if not st.session_state.messages and st.session_state.conversation_state == "initial":
        welcome = """👋 Welcome to MAGnus Knowledge Bot!

I'm here to help! To provide you with the best assistance, please let me know what type of request this is:

🤔 **Question** - I need information or guidance
📄 **Change** - I want to suggest an improvement or new feature  
⚠️ **Issue** - Something isn't working as expected
🔧 **Problem** - I'm experiencing a technical difficulty

Please type one of these options: **Question**, **Change**, **Issue**, or **Problem**"""
        st.session_state.messages.append({"role": "assistant", "content": welcome})
        st.session_state.conversation_state = "categorizing"

    # Chat history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Input
    placeholder = "Type your question here..." if st.session_state.conversation_state != "initial" else "Hello! How can I help you today?"
    user_input = st.chat_input(placeholder)
    if not user_input:
        return

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    state = st.session_state.conversation_state
    
    if state == "initial":
        with st.chat_message("assistant"):
            st.markdown(st.session_state.messages[0]["content"])
            st.session_state.conversation_state = "categorizing"
        return

    if state == "categorizing":
        choice = user_input.lower().strip()
        with st.chat_message("assistant"):
            if "question" in choice:
                st.session_state.current_category = "question"
                msg = "Perfect! What would you like to know? Please ask your question and I'll search through our company documents to find the answer."
                st.markdown(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
                st.session_state.conversation_state = "categorized"
            elif "change" in choice:
                st.session_state.current_category = "change"
                msg = ("That's fantastic! We love hearing improvement ideas from our team.\n\n"
                       "Submit via **Innovation Request**:\n\n"
                       "🔗 **[Submit Innovation Request](https://www.jotform.com/form/250841782712054)**")
                st.markdown(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
                st.session_state.conversation_state = "completed"
            elif "issue" in choice:
                st.session_state.current_category = "issue"
                msg = "I understand you're experiencing an issue. Please describe what's happening in detail, and I'll search our documentation to help resolve it."
                st.markdown(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
                st.session_state.conversation_state = "waiting_for_issue"
            elif "problem" in choice:
                st.session_state.current_category = "problem"
                msg = "I'm here to help with your problem. Please explain what's going wrong, and I'll look through our resources to find a solution."
                st.markdown(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
                st.session_state.conversation_state = "waiting_for_problem"
            else:
                msg = ("I didn't quite catch that. Please choose one of these options:\n\n"
                       "• Type **Question** if you need information\n"
                       "• Type **Change** if you want to suggest an improvement  \n"
                       "• Type **Issue** if something isn't working\n"
                       "• Type **Problem** if you're experiencing difficulties")
                st.markdown(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
        return

    # Question / Issue / Problem handling with Azure Assistant
    if state in ["waiting_for_issue", "waiting_for_problem", "categorized"]:
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
            with st.spinner("🤔 Searching through company documents..."):
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
                    st.markdown(response)
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
