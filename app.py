import os
import os
import time
import re
import streamlit as st
import time
from datetime import datetime
import streamlit as st
from datetime import datetime
from html import escape
from streamlit.components.v1 import html


st.set_page_config(
st.set_page_config(
    page_title="MAGnus - MA Group Knowledge Bot", 
    page_title="MAGnus - MA Group Knowledge Bot", 
    page_icon="🤖", 
    page_icon="🤖", 
    layout="wide",
    layout="wide",
    initial_sidebar_state="expanded"
    initial_sidebar_state="expanded"
)
)


# Remove all sidebar CSS - we're switching to a top bar approach
# Remove all sidebar CSS - we're switching to a top bar approach
st.markdown("""
st.markdown("""
<style>
<style>
/* Hide the sidebar completely */
/* Hide the sidebar completely */
section[data-testid="stSidebar"] {
section[data-testid="stSidebar"] {
    display: none !important;
    display: none !important;
}
}


/* Top bar styling */
/* Top bar styling */
.top-bar {
.top-bar {
    background: linear-gradient(135deg, #272557 0%, #1e1f4a 100%);
    background: linear-gradient(135deg, #272557 0%, #1e1f4a 100%);
    padding: 1rem 2rem;
    padding: 1rem 2rem;
    border-radius: 15px;
    border-radius: 15px;
    margin-bottom: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 15px -5px rgba(39, 37, 87, 0.3);
    box-shadow: 0 4px 15px -5px rgba(39, 37, 87, 0.3);
    color: white;
    color: white;
    display: flex;
    display: flex;
@@ -133,109 +136,178 @@ def display_logo():
            col1, col2, col3 = st.columns([2, 1, 2])
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
            with col2:
                st.image("magnuslogo.png", width=250, use_container_width=False)
                st.image("magnuslogo.png", width=250, use_container_width=False)
        else:
        else:
            st.markdown("""
            st.markdown("""
            <div class="logo-text-container">
            <div class="logo-text-container">
                <h1 class="logo-text">MAGnus AI</h1>
                <h1 class="logo-text">MAGnus AI</h1>
                <p class="logo-subtitle">Intelligent Assistant</p>
                <p class="logo-subtitle">Intelligent Assistant</p>
            </div>
            </div>
            """, unsafe_allow_html=True)
            """, unsafe_allow_html=True)
    except Exception as e:
    except Exception as e:
        st.markdown("""
        st.markdown("""
        <div class="logo-text-container">
        <div class="logo-text-container">
            <h1 class="logo-text">MAGnus AI</h1>
            <h1 class="logo-text">MAGnus AI</h1>
            <p class="logo-subtitle">Intelligent Assistant</p>
            <p class="logo-subtitle">Intelligent Assistant</p>
        </div>
        </div>
        """, unsafe_allow_html=True)
        """, unsafe_allow_html=True)


def create_avatar_chip(role):
def create_avatar_chip(role):
    """Create enhanced avatar chip HTML"""
    """Create enhanced avatar chip HTML"""
    if role == "user":
    if role == "user":
        return '<div class="avatar-chip user"><i class="user-icon">👤</i> You</div>'
        return '<div class="avatar-chip user"><i class="user-icon">👤</i> You</div>'
    else:
    else:
        return '<div class="avatar-chip assistant"><i class="bot-icon">🤖</i> MAGnus</div>'
        return '<div class="avatar-chip assistant"><i class="bot-icon">🤖</i> MAGnus</div>'


def display_message_with_custom_avatar(role, content):
def format_message_content(text):
    """Display chat message with enhanced custom avatar chip"""
    """Convert lightweight Markdown to HTML for display"""
    avatar_html = create_avatar_chip(role)
    if not text:
    message_class = "user-message" if role == "user" else "assistant-message"
        return ""
    timestamp = datetime.now().strftime('%H:%M')

    
    safe_text = escape(text)
    st.markdown(f"""
    safe_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_text)
    <div class="chat-message-container {message_class}">
    safe_text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", safe_text)
        <div class="avatar-container">
    safe_text = re.sub(r"`(.+?)`", r"<code>\1</code>", safe_text)
            {avatar_html}

        </div>
    lines = safe_text.split("\n")
        <div class="message-content">
    html_parts = []
            {content}
    buffer = []
        </div>
    in_list = False
        <div class="message-timestamp">

            {timestamp}
    def flush_buffer():
        </div>
        nonlocal buffer
    </div>
        if buffer:
    """, unsafe_allow_html=True)
            html_parts.append(f"<p>{'<br>'.join(buffer)}</p>")
            buffer = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("- "):
            flush_buffer()
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{stripped[2:].strip()}</li>")
        elif stripped == "":
            flush_buffer()
            if in_list:
                html_parts.append("</ul>")
                in_list = False
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            buffer.append(stripped)

    flush_buffer()
    if in_list:
        html_parts.append("</ul>")

    return "".join(html_parts) or "<p></p>"


def display_message_with_custom_avatar(role, content):
    """Display chat message with enhanced custom avatar chip"""
    avatar_html = create_avatar_chip(role)
    message_class = "user-message" if role == "user" else "assistant-message"
    timestamp = datetime.now().strftime('%H:%M')
    formatted_content = format_message_content(content)

    st.markdown(f"""
    <div class="chat-message-container {message_class}">
        <div class="avatar-container">
            {avatar_html}
        </div>
        <div class="message-content">
            {formatted_content}
        </div>
        <div class="message-timestamp">
            {timestamp}
        </div>
    </div>
    """, unsafe_allow_html=True)


def typing_effect_with_avatar(text, role):
def typing_effect_with_avatar(text, role):
    """Display text with typing effect and custom avatar"""
    """Display text with typing effect and custom avatar"""
    avatar_html = create_avatar_chip(role)
    avatar_html = create_avatar_chip(role)
    timestamp = datetime.now().strftime('%H:%M')
    timestamp = datetime.now().strftime('%H:%M')
    
    
    container = st.empty()
    container = st.empty()
    
    
    # Show typing indicator first
    # Show typing indicator first
    container.markdown(f"""
    container.markdown(f"""
    <div class="chat-message-container assistant-message">
    <div class="chat-message-container assistant-message">
        <div class="avatar-container">
        <div class="avatar-container">
            {avatar_html}
            {avatar_html}
        </div>
        </div>
        <div class="message-content">
        <div class="message-content">
            <div class="typing-indicator-container">
            <div class="typing-indicator-container">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
            </div>
        </div>
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)
    """, unsafe_allow_html=True)
    
    
    time.sleep(1)
    time.sleep(0.5)
    

    # Show the full message
    displayed_text = ""
    container.markdown(f"""
    typing_delay = max(0.005, min(0.03, 0.6 / max(len(text), 1)))
    <div class="chat-message-container assistant-message">
    for char in text:
        <div class="avatar-container">
        displayed_text += char
            {avatar_html}
        formatted_content = format_message_content(displayed_text)
        </div>
        container.markdown(f"""
        <div class="message-content">
        <div class="chat-message-container assistant-message">
            {text}
            <div class="avatar-container">
        </div>
                {avatar_html}
        <div class="message-timestamp">
            </div>
            {timestamp}
            <div class="message-content">
        </div>
                {formatted_content}
    </div>
            </div>
    """, unsafe_allow_html=True)
            <div class="message-timestamp">
                {timestamp}
            </div>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(typing_delay)

    formatted_content = format_message_content(text)
    container.markdown(f"""
    <div class="chat-message-container assistant-message">
        <div class="avatar-container">
            {avatar_html}
        </div>
        <div class="message-content">
            {formatted_content}
        </div>
        <div class="message-timestamp">
            {timestamp}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------- Dependencies ----------
# ---------- Dependencies ----------
try:
try:
    from openai import AzureOpenAI
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
    AZURE_OPENAI_AVAILABLE = True
except Exception:
except Exception:
    AZURE_OPENAI_AVAILABLE = False
    AZURE_OPENAI_AVAILABLE = False


# ---------- Utils ----------
# ---------- Utils ----------
def get_secret(key, default=None):
def get_secret(key, default=None):
    return os.getenv(key) or st.secrets.get(key, default)
    return os.getenv(key) or st.secrets.get(key, default)


@st.cache_resource
@st.cache_resource
def get_azure_client():
def get_azure_client():
    """Initialize Azure OpenAI client"""
    """Initialize Azure OpenAI client"""
    if not AZURE_OPENAI_AVAILABLE:
    if not AZURE_OPENAI_AVAILABLE:
        return None
        return None
    
    
    api_key = get_secret("AZURE_OPENAI_API_KEY")
    api_key = get_secret("AZURE_OPENAI_API_KEY")
    endpoint = get_secret("AZURE_OPENAI_ENDPOINT")
    endpoint = get_secret("AZURE_OPENAI_ENDPOINT")
    api_version = get_secret("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
    api_version = get_secret("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
    
    
    if not api_key or not endpoint:
    if not api_key or not endpoint:
        return None
        return None
    
    
@@ -317,76 +389,98 @@ def wait_for_run_completion(client, thread_id, run_id, max_wait=60):
                
                
        except Exception as e:
        except Exception as e:
            st.error(f"Error checking run status: {e}")
            st.error(f"Error checking run status: {e}")
            return False, None
            return False, None
    
    
    return False, None
    return False, None


def get_assistant_response(client, thread_id):
def get_assistant_response(client, thread_id):
    """Get the latest assistant message from thread"""
    """Get the latest assistant message from thread"""
    try:
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        if messages.data:
        if messages.data:
            latest_message = messages.data[0]
            latest_message = messages.data[0]
            if latest_message.role == 'assistant':
            if latest_message.role == 'assistant':
                content_parts = []
                content_parts = []
                for content in latest_message.content:
                for content in latest_message.content:
                    if content.type == 'text':
                    if content.type == 'text':
                        content_parts.append(content.text.value)
                        content_parts.append(content.text.value)
                return "\n".join(content_parts)
                return "\n".join(content_parts)
        return None
        return None
    except Exception as e:
    except Exception as e:
        st.error(f"Error retrieving assistant response: {e}")
        st.error(f"Error retrieving assistant response: {e}")
        return None
        return None


# ---------- State ----------
# ---------- State ----------
for k, v in [
for k, v in [
    ("authenticated", False),
    ("authenticated", False),
    ("assistant_ready", False),
    ("assistant_ready", False),
    ("messages", []),
    ("messages", []),
    ("conversation_state", "initial"),
    ("conversation_state", "initial"),
    ("current_category", None),
    ("current_category", None),
    ("thread_id", None),
    ("thread_id", None),
    ("session_stats", {"questions": 0, "responses": 0}),
    ("session_stats", {"questions": 0, "responses": 0}),
]:
    ("show_help_panel", False),
    if k not in st.session_state:
    ("show_export_panel", False),
        st.session_state[k] = v
    ("follow_up_prompt", False),

    ("scroll_to_latest", False),
def logout():
]:
    """Enhanced logout with confirmation"""
    if k not in st.session_state:
    for key in list(st.session_state.keys()):
        st.session_state[k] = v
        del st.session_state[key]

def append_message(role, content):
    """Store a chat message and flag the UI to scroll to the latest entry"""
    st.session_state.messages.append({"role": role, "content": content})
    if "session_stats" in st.session_state:
        if role == "user":
            st.session_state.session_stats["questions"] = (
                st.session_state.session_stats.get("questions", 0) + 1
            )
        elif role == "assistant":
            st.session_state.session_stats["responses"] = (
                st.session_state.session_stats.get("responses", 0) + 1
            )
    st.session_state.scroll_to_latest = True

def logout():
    """Enhanced logout with confirmation"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_resource.clear()
    st.cache_resource.clear()
    st.rerun()
    st.rerun()


def reset_chat():
def reset_chat():
    """Enhanced chat reset"""
    """Enhanced chat reset"""
    st.session_state.messages = []
    st.session_state.messages = []
    st.session_state.conversation_state = "initial"
    st.session_state.conversation_state = "initial"
    st.session_state.current_category = None
    st.session_state.current_category = None
    st.session_state.thread_id = None
    st.session_state.thread_id = None
    st.session_state.session_stats = {"questions": 0, "responses": 0}
    st.session_state.session_stats = {"questions": 0, "responses": 0}
    st.session_state.follow_up_prompt = False
    st.session_state.show_help_panel = False
    st.session_state.show_export_panel = False
    st.session_state.scroll_to_latest = False


# ---------- Screens ----------
# ---------- Screens ----------
def show_login():
def show_login():
    """Enhanced login screen"""
    """Enhanced login screen"""
    st.markdown("""
    st.markdown("""
    <div class="login-page-container">
    <div class="login-page-container">
        <div class="login-header">
        <div class="login-header">
            <h1 class="login-title">🤖 MAGnus Knowledge Bot</h1>
            <h1 class="login-title">🤖 MAGnus Knowledge Bot</h1>
            <p class="login-subtitle">Your intelligent assistant for MA Group knowledge</p>
            <p class="login-subtitle">Your intelligent assistant for MA Group knowledge</p>
        </div>
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)
    """, unsafe_allow_html=True)
    
    
    display_logo()
    display_logo()
    
    
    with st.container():
    with st.container():
        st.markdown("""
        st.markdown("""
        <div class="login-form-container">
        <div class="login-form-container">
            <div class="login-form-header">
            <div class="login-form-header">
                <h3>Welcome Back</h3>
                <h3>Welcome Back</h3>
                <p>Please sign in to access your AI assistant</p>
                <p>Please sign in to access your AI assistant</p>
            </div>
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)
        """, unsafe_allow_html=True)
        
        
@@ -446,53 +540,53 @@ def show_assistant_setup():
                logout()
                logout()
            return
            return
        
        
        # Get or create assistant
        # Get or create assistant
        status.info("⚙️ Setting up AI Assistant...")
        status.info("⚙️ Setting up AI Assistant...")
        prog.progress(75, "Setting up assistant...")
        prog.progress(75, "Setting up assistant...")
        time.sleep(0.5)
        time.sleep(0.5)
        
        
        assistant = get_or_create_assistant(client)
        assistant = get_or_create_assistant(client)
        if not assistant:
        if not assistant:
            if st.button("🚪 Return to Login"):
            if st.button("🚪 Return to Login"):
                logout()
                logout()
            return
            return
        
        
        # Success
        # Success
        status.success("✅ Assistant ready!")
        status.success("✅ Assistant ready!")
        prog.progress(100, "Ready!")
        prog.progress(100, "Ready!")
        time.sleep(0.5)
        time.sleep(0.5)
        
        
        st.session_state.assistant_ready = True
        st.session_state.assistant_ready = True
        st.rerun()
        st.rerun()


def show_main_app():
def show_main_app():
    """Enhanced main application interface using pure Streamlit components"""
    """Enhanced main application interface using pure Streamlit components"""
    
    
    # Get session stats␍␊
    # Get session stats␊
    user_msgs = len([m for m in st.session_state.messages if m["role"] == "user"])
    user_msgs = st.session_state.session_stats.get("questions", 0)
    ai_msgs = len([m for m in st.session_state.messages if m["role"] == "assistant"])
    ai_msgs = st.session_state.session_stats.get("responses", 0)
    
    
    # Create top bar using pure Streamlit with targeted CSS
    # Create top bar using pure Streamlit with targeted CSS
    st.markdown("""
    st.markdown("""
    <style>
    <style>
    .top-status-bar {
    .top-status-bar {
        background: linear-gradient(135deg, #272557 0%, #1e1f4a 100%) !important;
        background: linear-gradient(135deg, #272557 0%, #1e1f4a 100%) !important;
        padding: 1rem !important;
        padding: 1rem !important;
        border-radius: 15px !important;
        border-radius: 15px !important;
        margin-bottom: 1.5rem !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 4px 15px -5px rgba(39, 37, 87, 0.3) !important;
        box-shadow: 0 4px 15px -5px rgba(39, 37, 87, 0.3) !important;
    }
    }
    .top-status-bar .stMarkdown {
    .top-status-bar .stMarkdown {
        color: white !important;
        color: white !important;
    }
    }
    .top-status-bar .stMetric {
    .top-status-bar .stMetric {
        background: rgba(255,255,255,0.1) !important;
        background: rgba(255,255,255,0.1) !important;
        padding: 0.5rem !important;
        padding: 0.5rem !important;
        border-radius: 8px !important;
        border-radius: 8px !important;
        text-align: center !important;
        text-align: center !important;
    }
    }
    .top-status-bar .stMetric label {
    .top-status-bar .stMetric label {
        color: white !important;
        color: white !important;
        font-size: 0.8rem !important;
        font-size: 0.8rem !important;
    }
    }
    .top-status-bar .stMetric div[data-testid="metric-container"] > div {
    .top-status-bar .stMetric div[data-testid="metric-container"] > div {
@@ -513,249 +607,302 @@ def show_main_app():
    
    
    with info_col:
    with info_col:
        st.markdown("GPT-4 Turbo • Azure AI Foundry • File Search Enabled")
        st.markdown("GPT-4 Turbo • Azure AI Foundry • File Search Enabled")
    
    
    with stats_col1:
    with stats_col1:
        st.metric("Questions", user_msgs)
        st.metric("Questions", user_msgs)
    
    
    with stats_col2:
    with stats_col2:
        st.metric("Responses", ai_msgs)
        st.metric("Responses", ai_msgs)
    
    
    # Close container
    # Close container
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    
    # Add action buttons below the main bar
    # Add action buttons below the main bar
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    
    with col1:
    with col1:
        if st.button("🚪 Logout", use_container_width=True):
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            logout()
    
    
    with col2:
    with col2:
        if st.button("🔄 Reset Chat", use_container_width=True):
        if st.button("🔄 Reset Chat", use_container_width=True):
            reset_chat()
            reset_chat()
            st.rerun()
            st.rerun()
    
    
    with col3:
    with col3:
        if st.button("💡 Help", use_container_width=True):
        if st.button("💡 Help", use_container_width=True, key="toggle_help"):
            st.info("💬 Type your work-related questions in the chat below!")
            st.session_state.show_help_panel = not st.session_state.show_help_panel
    
        if st.session_state.show_help_panel:
    with col4:
            st.info("💬 Type your work-related questions in the chat below!")
        if st.button("🔄 Refresh", use_container_width=True):

            st.cache_resource.clear()
    with col4:
            st.rerun()
        if st.button("🔄 Refresh", use_container_width=True):
    
            st.cache_resource.clear()
    with col5:
            st.rerun()
        if st.button("📈 Export", use_container_width=True):

            if st.session_state.messages:
    with col5:
                export_data = {
        if st.button("📈 Export", use_container_width=True, key="toggle_export"):
                    "timestamp": datetime.now().isoformat(),
            st.session_state.show_export_panel = not st.session_state.show_export_panel
                    "messages": st.session_state.messages
        if st.session_state.show_export_panel:
                }
            if st.session_state.messages:
                st.download_button(
                export_data = {
                    "📥 Download Chat History",
                    "timestamp": datetime.now().isoformat(),
                    data=str(export_data),
                    "messages": st.session_state.messages
                    file_name=f"magnus_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                }
                    mime="application/json"
                st.download_button(
                )
                    "📥 Download Chat History",
            else:
                    data=str(export_data),
                st.info("No messages to export")
                    file_name=f"magnus_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key="download_history"
                )
            else:
                st.info("No messages to export")
    
    
    st.divider()
    st.divider()
    
    
    # Header with gradient background
    # Header with gradient background
    st.markdown("""
    st.markdown("""
    <div class="main-header">
    <div class="main-header">
        <h1 class="main-title">🤖 MAGnus AI Assistant</h1>
        <h1 class="main-title">🤖 MAGnus AI Assistant</h1>
        <p class="main-subtitle">Your intelligent companion for MA Group knowledge</p>
        <p class="main-subtitle">Your intelligent companion for MA Group knowledge</p>
    </div>
    </div>
    """, unsafe_allow_html=True)
    """, unsafe_allow_html=True)
    
    
    # Chat area (removed control panel section)
    # Chat area (removed control panel section)
    chat_container = st.container()
    chat_container = st.container()
    
    
    with chat_container:
    with chat_container:
        # Initial welcome message
        # Initial welcome message
        if not st.session_state.messages and st.session_state.conversation_state == "initial":
        if not st.session_state.messages and st.session_state.conversation_state == "initial":
            time_greeting = get_time_greeting()
            time_greeting = get_time_greeting()
            welcome = f"""👋 **Welcome to MAGnus!**
            welcome = f"""👋 **Welcome to MAGnus!**


Hey there! How are you doing {time_greeting}? 
Hey there! How are you doing {time_greeting}? 


I'm MAGnus, your friendly AI assistant here to help with anything work-related. What can I help you with today?"""
I'm MAGnus, your friendly AI assistant here to help with anything work-related. What can I help you with today?"""
            
            
            st.session_state.messages.append({"role": "assistant", "content": welcome})
            append_message("assistant", welcome)
            st.session_state.conversation_state = "show_options"
            st.session_state.conversation_state = "show_options"


        # Display chat history␍␊
        # Display chat history␊
        for m in st.session_state.messages:␍␊
        for m in st.session_state.messages:␊
            display_message_with_custom_avatar(m["role"], m["content"])␍␊
            display_message_with_custom_avatar(m["role"], m["content"])␊
␍␊
␊
        # Show option buttons after welcome␍␊
        # Show option buttons after welcome␊
        if st.session_state.conversation_state == "show_options":␍␊
        if st.session_state.conversation_state == "show_options":␊
            st.markdown("""␍␊
            st.markdown("""␊
            <div class="options-container">␍␊
            <div class="options-container">␊
                <h3>What can I help you with today?</h3>␍␊
                <h3>What can I help you with today?</h3>␊
            </div>
            </div>
            """, unsafe_allow_html=True)
            """, unsafe_allow_html=True)
            
            
            col1, col2 = st.columns(2)
            col1, col2 = st.columns(2)
            with col1:
            with col1:
                if st.button("🤔 I have a Question", use_container_width=True, key="question_btn"):
                if st.button("🤔 I have a Question", use_container_width=True, key="question_btn"):
                    st.session_state.conversation_state = "confirm_question"
                    st.session_state.conversation_state = "confirm_question"
                    st.rerun()
                    st.session_state.scroll_to_latest = True
                if st.button("⚠️ I have an Issue", use_container_width=True, key="issue_btn"):
                    st.rerun()
                    st.session_state.conversation_state = "confirm_issue"
                if st.button("⚠️ I have an Issue", use_container_width=True, key="issue_btn"):
                    st.rerun()
                    st.session_state.conversation_state = "confirm_issue"
            
                    st.session_state.scroll_to_latest = True
            with col2:
                    st.rerun()
                if st.button("📄 I want to suggest a Change", use_container_width=True, key="change_btn"):

                    st.session_state.conversation_state = "confirm_change"
            with col2:
                    st.rerun()
                if st.button("📄 I want to suggest a Change", use_container_width=True, key="change_btn"):
                if st.button("🔧 I have a Problem", use_container_width=True, key="problem_btn"):
                    st.session_state.conversation_state = "confirm_change"
                    st.session_state.conversation_state = "confirm_problem"
                    st.session_state.scroll_to_latest = True
                    st.rerun()
                    st.rerun()
                if st.button("🔧 I have a Problem", use_container_width=True, key="problem_btn"):
                    st.session_state.conversation_state = "confirm_problem"
                    st.session_state.scroll_to_latest = True
                    st.rerun()
            return
            return


        # Confirmation flows
        # Confirmation flows
        if st.session_state.conversation_state.startswith("confirm_"):
        if st.session_state.conversation_state.startswith("confirm_"):
            category = st.session_state.conversation_state.replace("confirm_", "")
            category = st.session_state.conversation_state.replace("confirm_", "")
            category_text = {
            category_text = {
                "question": "Question - you need information or guidance",
                "question": "Question - you need information or guidance",
                "change": "Change - you want to suggest an improvement",
                "change": "Change - you want to suggest an improvement",
                "issue": "Issue - something isn't working as expected", 
                "issue": "Issue - something isn't working as expected", 
                "problem": "Problem - you're experiencing a technical difficulty"
                "problem": "Problem - you're experiencing a technical difficulty"
            }
            }
            
            
            display_message_with_custom_avatar("assistant", f"You've chosen **{category_text[category]}**. Is that correct?")
            display_message_with_custom_avatar("assistant", f"You've chosen {category_text[category]}. Is that correct?")
            
            
            col1, col2 = st.columns([1, 1])
            col1, col2 = st.columns([1, 1])
            with col1:
            with col1:
                if st.button("✅ Yes, that's right", use_container_width=True, key=f"confirm_{category}"):
                if st.button("✅ Yes, that's right", use_container_width=True, key=f"confirm_{category}"):
                    st.session_state.current_category = category
                    st.session_state.current_category = category
                    st.session_state.messages.append({
                    append_message("assistant", f"You've chosen {category_text[category]}. Is that correct?")
                        "role": "assistant", 
                    append_message("user", "Yes, that's right")
                        "content": f"You've chosen **{category_text[category]}**. Is that correct?"

                    })
                    if category == "change":
                    st.session_state.messages.append({
                        msg = """Perfect! I love hearing improvement ideas.
                        "role": "user", 

                        "content": "Yes, that's right"
The best way to submit your suggestion is through our Innovation Request form:
                    })

                    
🔗 **[Submit Innovation Request](https://www.jotform.com/form/250841782712054)**
                    if category == "change":

                        msg = """Perfect! I love hearing improvement ideas.
This ensures your idea gets to the right people and gets proper consideration."""

                        append_message("assistant", msg)
The best way to submit your suggestion is through our Innovation Request form:
                        st.session_state.conversation_state = "completed"

                    else:
🔗 **[Submit Innovation Request](https://www.jotform.com/form/250841782712054)**
                        if category == "question":

                            msg = "Great! What would you like to know? Just ask me anything about work processes, systems, or policies."
This ensures your idea gets to the right people and gets proper consideration."""
                        elif category == "issue":
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                            msg = "I understand you're having an issue. Can you tell me what's happening? I'll help you figure it out."
                        st.session_state.conversation_state = "completed"
                        else:  # problem
                    else:
                            msg = "I'm here to help with your problem. What's going wrong? Let me see what I can find to help."
                        if category == "question":

                            msg = "Great! What would you like to know? Just ask me anything about work processes, systems, or policies."
                        append_message("assistant", msg)
                        elif category == "issue":
                        st.session_state.conversation_state = "ready_for_questions"
                            msg = "I understand you're having an issue. Can you tell me what's happening? I'll help you figure it out."
                    st.rerun()
                        else:  # problem
                            msg = "I'm here to help with your problem. What's going wrong? Let me see what I can find to help."
                        
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                        st.session_state.conversation_state = "ready_for_questions"
                    st.rerun()
            
            
            with col2:
            with col2:
                if st.button("❌ No, let me choose again", use_container_width=True, key=f"reject_{category}"):
                if st.button("❌ No, let me choose again", use_container_width=True, key=f"reject_{category}"):
                    st.session_state.conversation_state = "show_options"
                    st.session_state.conversation_state = "show_options"
                    st.rerun()
                    st.rerun()
            return
            return


        # Chat input
        # Chat input
        placeholder = "Type your question here..." if st.session_state.conversation_state == "ready_for_questions" else "Hello! How can I help you today?"
        placeholder = "Type your question here..." if st.session_state.conversation_state == "ready_for_questions" else "Hello! How can I help you today?"
        user_input = st.chat_input(placeholder)
        user_input = st.chat_input(placeholder)
        

        if user_input:
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.follow_up_prompt = False
            display_message_with_custom_avatar("user", user_input)
            append_message("user", user_input)
            display_message_with_custom_avatar("user", user_input)


            # Handle AI responses
            # Handle AI responses
            if st.session_state.conversation_state == "ready_for_questions":
            if st.session_state.conversation_state == "ready_for_questions":
                if not AZURE_OPENAI_AVAILABLE:
                if not AZURE_OPENAI_AVAILABLE:
                    display_message_with_custom_avatar("assistant", "❌ AI service is not available.")
                    display_message_with_custom_avatar("assistant", "❌ AI service is not available.")
                    return
                    return


                client = get_azure_client()
                client = get_azure_client()
                if not client:
                if not client:
                    display_message_with_custom_avatar("assistant", "❌ Could not connect to Azure OpenAI service.")
                    display_message_with_custom_avatar("assistant", "❌ Could not connect to Azure OpenAI service.")
                    return
                    return


                assistant = get_or_create_assistant(client)
                assistant = get_or_create_assistant(client)
                if not assistant:
                if not assistant:
                    display_message_with_custom_avatar("assistant", "❌ AI Assistant is not properly configured.")
                    display_message_with_custom_avatar("assistant", "❌ AI Assistant is not properly configured.")
                    return
                    return


                # Convert messages for assistant
                # Convert messages for assistant
                assistant_messages = []
                assistant_messages = []
                for msg in st.session_state.messages:
                for msg in st.session_state.messages:
                    if msg["role"] in ["user", "assistant"]:
                    if msg["role"] in ["user", "assistant"]:
                        assistant_messages.append({
                        assistant_messages.append({
                            "role": msg["role"],
                            "role": msg["role"],
                            "content": msg["content"]
                            "content": msg["content"]
                        })
                        })


                # Show loading message
                # Show loading message
                loading_container = st.empty()
                loading_container = st.empty()
                loading_container.markdown("""
                loading_container.markdown("""
                <div class="chat-message-container assistant-message">
                <div class="chat-message-container assistant-message">
                    <div class="avatar-container">
                    <div class="avatar-container">
                        <div class="avatar-chip assistant"><i class="bot-icon">🤖</i> MAGnus</div>
                        <div class="avatar-chip assistant"><i class="bot-icon">🤖</i> MAGnus</div>
                    </div>
                    </div>
                    <div class="message-content">
                    <div class="message-content">
                        <div class="typing-indicator-container">
                        <div class="typing-indicator-container">
                            🔍 Searching company documents...
                            🔍 Searching company documents...
                            <div class="loading-dots">
                            <div class="loading-dots">
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                                <span class="typing-dot"></span>
                            </div>
                            </div>
                        </div>
                        </div>
                    </div>
                    </div>
                </div>
                </div>
                """, unsafe_allow_html=True)
                """, unsafe_allow_html=True)
                
                
                with st.spinner("Processing..."):␍␊
                with st.spinner("Processing..."):␊
                    # Create thread and run␍␊
                    # Create thread and run␊
                    thread_id, run_id = create_thread_and_run(client, assistant.id, assistant_messages)␍␊
                    thread_id, run_id = create_thread_and_run(client, assistant.id, assistant_messages)␊
                    

                    if thread_id and run_id:␍␊
                    if thread_id and run_id:␊
                        st.session_state.thread_id = thread_id␍␊
                        st.session_state.thread_id = thread_id␊
                        success, run_result = wait_for_run_completion(client, thread_id, run_id)
                        success, run_result = wait_for_run_completion(client, thread_id, run_id)
                        
                        
                        if success:
                        if success:
                            response = get_assistant_response(client, thread_id)
                            response = get_assistant_response(client, thread_id)
                            if response:
                            if response:
                                loading_container.empty()
                                loading_container.empty()
                                typing_effect_with_avatar(response, "assistant")
                                follow_up_line = (
                                st.session_state.messages.append({"role": "assistant", "content": response})
                                    "Has this answered your question? You can ask a follow-up below "
                            else:
                                    "or reset the chat if you need to start again."
                                loading_container.markdown("❌ Could not retrieve assistant response.")
                                )
                        else:
                                enhanced_response = f"{response.strip()}\n\n{follow_up_line}"
                            error_msg = f"Assistant run failed: {run_result.status}" if run_result else "Assistant run timed out."
                                typing_effect_with_avatar(enhanced_response, "assistant")
                            loading_container.markdown(f"❌ {error_msg}")
                                append_message("assistant", enhanced_response)

                                st.session_state.follow_up_prompt = True
    # Enhanced footer
                            else:
    st.markdown("---")
                                loading_container.markdown("❌ Could not retrieve assistant response.")
                        else:
                            error_msg = f"Assistant run failed: {run_result.status}" if run_result else "Assistant run timed out."
                            loading_container.markdown(f"❌ {error_msg}")

        if (
            st.session_state.follow_up_prompt
            and st.session_state.conversation_state == "ready_for_questions"
        ):
            st.markdown("""
            <div class="follow-up-card">
                <strong>Has this answered your question?</strong><br>
                You can ask a follow-up below or reset the chat to start again.
            </div>
            """, unsafe_allow_html=True)

            follow_col1, follow_col2 = st.columns([3, 1])
            with follow_col1:
                st.caption("Type another question in the chat box to keep the conversation going.")
            with follow_col2:
                if st.button("🔄 Reset chat", use_container_width=True, key="followup_reset"):
                    reset_chat()
                    st.rerun()

        st.markdown('<div id="chat-bottom-anchor"></div>', unsafe_allow_html=True)

    if st.session_state.scroll_to_latest:
        html(
            """
            <script>
            const parentWindow = window.parent;
            if (parentWindow && parentWindow.document) {
                const anchor = parentWindow.document.getElementById('chat-bottom-anchor');
                if (anchor && anchor.scrollIntoView) {
                    anchor.scrollIntoView({ behavior: 'smooth', block: 'end' });
                } else if (parentWindow.document.body) {
                    parentWindow.scrollTo({
                        top: parentWindow.document.body.scrollHeight,
                        behavior: 'smooth'
                    });
                }
            }
            </script>
            """,
            height=0,
        )
        st.session_state.scroll_to_latest = False

    # Enhanced footer
    st.markdown("---")
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    with footer_col1:
    with footer_col1:
        st.caption("🤖 MAGnus Knowledge Bot v2.0")
        st.caption("🤖 MAGnus Knowledge Bot v2.0")
    with footer_col2:
    with footer_col2:
        st.caption("⚡ Powered by Azure AI Foundry")
        st.caption("⚡ Powered by Azure AI Foundry")
    with footer_col3:
    with footer_col3:
        st.caption(f"🕐 Session started: {datetime.now().strftime('%H:%M')}")
        st.caption(f"🕐 Session started: {datetime.now().strftime('%H:%M')}")


# ---------- Router ----------
# ---------- Router ----------
if not st.session_state.authenticated:
if not st.session_state.authenticated:
    show_login()
    show_login()
elif not st.session_state.assistant_ready:
elif not st.session_state.assistant_ready:
    show_assistant_setup()
    show_assistant_setup()
else:
else:
    show_main_app()
    show_main_app()
styles.css
+11
-0

@@ -481,50 +481,61 @@ button[title*="sidebar"] svg,
    box-shadow: var(--shadow-xl);
}

/* FIXED: User messages with solid background for better readability */
.chat-message-container.user-message {
    background: #f8fafc;
    margin-left: 3rem;
    border-left: 4px solid var(--secondary-color);
}

.chat-message-container.user-message::before {
    background: linear-gradient(180deg, var(--secondary-color), var(--secondary-dark));
}

/* FIXED: Assistant messages with solid background for better readability */
.chat-message-container.assistant-message {
    background: var(--background-white);
    margin-right: 3rem;
    border-left: 4px solid var(--secondary-color);
}

.chat-message-container.assistant-message::before {
    background: linear-gradient(180deg, var(--secondary-color), var(--secondary-dark));
}

.follow-up-card {
    background: rgba(103, 126, 217, 0.08);
    border: 1px solid rgba(103, 126, 217, 0.2);
    border-radius: 14px;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
    box-shadow: 0 12px 30px -15px rgba(39, 37, 87, 0.35);
    color: var(--secondary-dark);
    font-weight: 500;
}

.avatar-container {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 0.75rem;
}

/* FIXED: Message content with much better contrast */
.message-content {
    font-family: 'Inter', sans-serif;
    line-height: 1.7;
    color: var(--text-dark);
    font-size: 1rem;
    margin-bottom: 0.5rem;
    font-weight: 500;
    text-shadow: 0 1px 1px rgba(255,255,255,0.8);
}

/* FIXED: Message timestamp with better visibility */
.message-timestamp {
    font-size: 0.75rem;
    color: var(--text-medium);
    text-align: right;
    font-weight: 600;
    opacity: 0.8;
    background: rgba(255,255,255,0.7);
