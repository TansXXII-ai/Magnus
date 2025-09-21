import os
import json
import streamlit as st
from datetime import datetime

# Page config
st.set_page_config(
    page_title="MAGnus - MA Groups Knowledge Bot", 
    page_icon="🤖",
    layout="wide"
)

# Import Azure OpenAI
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False

# Import Google Drive
try:
    from google_drive_api import GoogleDriveConnector
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

# Import document processing libraries
PDF_AVAILABLE = False
DOCX_AVAILABLE = False

try:
    import pypdf
    PDF_AVAILABLE = True
except ImportError:
    try:
        import PyPDF2 as pypdf
        PDF_AVAILABLE = True
    except ImportError:
        pass

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    pass

# Initialize Google Drive connector
@st.cache_resource
def get_google_drive_connector():
    if GOOGLE_DRIVE_AVAILABLE:
        return GoogleDriveConnector()
    return None

# Load documents from Google Drive with smart caching
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def load_knowledge_base():
    """Load documents from Google Drive with smart caching"""
    documents = []
    
    # Load from Google Drive
    if GOOGLE_DRIVE_AVAILABLE:
        try:
            # Check if Google Drive credentials are configured
            if "google" in st.secrets or "google_service_account" in st.secrets:
                google_connector = get_google_drive_connector()
                if google_connector:
                    google_docs = google_connector.get_documents()
                    documents.extend(google_docs)
        except Exception as e:
            raise Exception(f"Error fetching Google Drive documents: {str(e)}")
    
    return documents

def load_knowledge_base_incremental(progress_placeholder, status_placeholder):
    """Load documents with real-time progress updates"""
    documents = []
    
    if GOOGLE_DRIVE_AVAILABLE:
        try:
            if "google" in st.secrets or "google_service_account" in st.secrets:
                google_connector = get_google_drive_connector()
                if google_connector:
                    
                    # Get file summary first
                    summary = google_connector.get_file_summary()
                    total_files = summary.get('total', 0)
                    
                    if total_files == 0:
                        status_placeholder.text("No supported documents found")
                        progress_placeholder.progress(1.0)
                        return []
                    
                    # Show summary
                    status_placeholder.text(f"Found {total_files} documents. Starting smart loading...")
                    
                    def progress_callback(processed, total, current_files):
                        progress = processed / total if total > 0 else 0
                        progress_placeholder.progress(progress)
                        
                        if current_files:
                            file_names = [f.split('/')[-1] for f in current_files]  # Get just filenames
                            status_placeholder.text(f"Processing: {', '.join(file_names)}")
                        else:
                            status_placeholder.text(f"✅ Loaded {processed}/{total} documents")
                    
                    # Load documents with progress
                    google_docs = google_connector.get_documents_incremental(
                        progress_callback=progress_callback
                    )
                    documents.extend(google_docs)
                    
        except Exception as e:
            status_placeholder.text(f"❌ Error: {str(e)}")
            raise Exception(f"Error fetching Google Drive documents: {str(e)}")
    
    return documents

def call_openai_api(messages):
    """Call Azure OpenAI API"""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    if not api_key or not endpoint:
        return None, "Missing Azure OpenAI credentials"
    
    try:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        
        return client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=2000
        ), None
        
    except Exception as e:
        return None, f"Azure OpenAI API error: {str(e)}"

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "loading_complete" not in st.session_state:
    st.session_state.loading_complete = False

if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_state" not in st.session_state:
    st.session_state.conversation_state = "initial"

if "current_category" not in st.session_state:
    st.session_state.current_category = None

# Login function with Google Drive integration
def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("MAGNUS AI Logo Design.png", width=150)
        except:
            pass
    
    st.title("🔐 MAGnus Knowledge Bot - Login")
    
    st.markdown("""
    **Welcome to MAGnus Knowledge Bot**
    
    Please log in to access the company knowledge base. Your Google Drive will be connected automatically.
    """)
    
    # Check Google Drive connection
    storage_status = []
    
    if GOOGLE_DRIVE_AVAILABLE:
        try:
            if "google" in st.secrets or "google_service_account" in st.secrets:
                google_connector = get_google_drive_connector()
                if google_connector:
                    connected, message = google_connector.test_connection()
                    if connected:
                        storage_status.append(f"✅ Google Drive: {message}")
                    else:
                        storage_status.append(f"❌ Google Drive: {message}")
                else:
                    storage_status.append("❌ Google Drive: Failed to initialize")
            else:
                storage_status.append("⚠️ Google Drive not configured")
        except Exception as e:
            storage_status.append(f"❌ Google Drive error: {str(e)}")
    else:
        storage_status.append("❌ Google Drive not available")
    
    # Display storage status
    if storage_status:
        st.markdown("### 📁 Document Storage Status")
        for status in storage_status:
            st.markdown(status)
        st.markdown("---")
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("🚀 Login & Connect", use_container_width=True)
        
        if login_button:
            correct_username = "MAG"
            correct_password = st.secrets.get("LOGIN_PASSWORD", "defaultpassword")
            
            if username == correct_username and password == correct_password:
                st.session_state.authenticated = True
                st.session_state.loading_complete = False
                
                with st.spinner("🔗 Connecting to Google Drive..."):
                    st.success("✅ Login successful! Connecting to document sources...")
                    st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

# Enhanced loading function with incremental progress
def show_loading():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("MAGNUS AI Logo Design.png", width=150)
        except:
            pass
    
    st.title("🤖 MAGnus Knowledge Bot")
    
    st.markdown("### 📚 Loading Knowledge Base")
    
    # Create progress elements
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Initializing Google Drive connection...")
    progress_bar.progress(0.1)
    
    # Check Google Drive
    if GOOGLE_DRIVE_AVAILABLE:
        try:
            if "google" in st.secrets or "google_service_account" in st.secrets:
                google_connector = get_google_drive_connector()
                if google_connector:
                    status_text.text("Testing Google Drive connection...")
                    progress_bar.progress(0.2)
                    
                    connected, message = google_connector.test_connection()
                    if connected:
                        st.info(f"📱 Google Drive: {message}")
                        
                        # Use incremental loading with progress
                        try:
                            documents = load_knowledge_base_incremental(progress_bar, status_text)
                            
                            st.session_state.knowledge_base = documents
                            
                            # Show final summary
                            fast_files = len([d for d in documents if d.get('processing_speed') == 'fast'])
                            medium_files = len([d for d in documents if d.get('processing_speed') == 'medium'])
                            slow_files = len([d for d in documents if d.get('processing_speed') == 'slow'])
                            
                            summary_text = f"✅ Loaded {len(documents)} documents successfully!"
                            if fast_files:
                                summary_text += f" ({fast_files} fast, {medium_files} medium, {slow_files} complex files)"
                            
                            status_text.text(summary_text)
                            progress_bar.progress(1.0)
                            
                            st.session_state.loading_complete = True
                            
                            import time
                            time.sleep(2)  # Show success message briefly
                            
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error loading documents: {str(e)}")
                            st.info("Please check your Google Drive configuration and try again.")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("🔄 Retry"):
                                    st.rerun()
                            with col2:
                                if st.button("🚪 Logout"):
                                    logout()
                            return
                    else:
                        st.error(f"❌ Google Drive connection failed: {message}")
                        if st.button("🔙 Back to Login"):
                            logout()
                        return
                else:
                    st.error("❌ Failed to initialize Google Drive connector")
                    if st.button("🔙 Back to Login"):
                        logout()
                    return
            else:
                st.error("❌ Google Drive credentials not configured")
                if st.button("🔙 Back to Login"):
                    logout()
                return
        except Exception as e:
            st.error(f"❌ Google Drive error: {str(e)}")
            if st.button("🔙 Back to Login"):
                logout()
            return
    else:
        st.error("❌ Google Drive integration not available")
        st.info("Please check that google_drive_api.py is present and requirements are installed")
        if st.button("🔙 Back to Login"):
            logout()
        return

# Logout function
def logout():
    st.session_state.authenticated = False
    st.session_state.loading_complete = False
    st.session_state.knowledge_base = []
    st.session_state.messages = []
    st.rerun()

# Main app
def show_main_app():
    # Header
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        try:
            st.image("MAGNUS AI Logo Design.png", width=80)
        except:
            st.markdown("**MAG**")
    with col2:
        st.title("🤖 MAGnus - MA Groups Knowledge Bot")
    with col3:
        if st.button("🚪 Logout", help="Logout from MAGnus"):
            logout()
    
    # Information section
    st.markdown("""
    **Welcome to the MAGnus Knowledge Base Chatbot!** This AI assistant has access to company documents and can help you find information quickly.

    **What you can ask:**
    - **How to**: "Create a new claim in Pulse" or "How do I log into the phone system"

    **Tips for better results:**
    - Be specific with your questions
    - Ask follow-up questions if you need more details
    - The chatbot will tell you which document contains the information

    ---
    """)

    knowledge_base = st.session_state.knowledge_base

    # Sidebar
    with st.sidebar:
        st.header("📊 Status")
        
        if AZURE_OPENAI_AVAILABLE:
            st.success("✅ Azure OpenAI Connected")
        else:
            st.error("❌ Azure OpenAI Unavailable")
        
        # Google Drive status
        st.subheader("📁 Document Source")
        
        if GOOGLE_DRIVE_AVAILABLE:
            try:
                if "google" in st.secrets or "google_service_account" in st.secrets:
                    connector = get_google_drive_connector()
                    if connector:
                        connected, message = connector.test_connection()
                        if connected:
                            st.success("✅ Google Drive Connected")
                            st.caption(f"📁 {message}")
                        else:
                            st.error("❌ Google Drive Connection Failed")
                            st.caption(f"Error: {message}")
                    else:
                        st.error("❌ Google Drive Failed to Initialize")
                else:
                    st.warning("⚠️ Google Drive not configured")
            except Exception as e:
                st.error(f"❌ Google Drive Error: {str(e)}")
        else:
            st.error("❌ Google Drive not available")
        
        st.divider()
        
        # Enhanced Knowledge Base section with performance stats
        st.header("📚 Knowledge Base")
        
        if knowledge_base:
            total_docs = len(knowledge_base)
            
            # Show document statistics
            fast_files = len([d for d in knowledge_base if d.get('processing_speed') == 'fast'])
            medium_files = len([d for d in knowledge_base if d.get('processing_speed') == 'medium'])
            slow_files = len([d for d in knowledge_base if d.get('processing_speed') == 'slow'])
            
            # Priority breakdown
            priority_1 = len([d for d in knowledge_base if d.get('priority') == 1])
            priority_2 = len([d for d in knowledge_base if d.get('priority') == 2])
            priority_3 = len([d for d in knowledge_base if d.get('priority') == 3])
            priority_4 = len([d for d in knowledge_base if d.get('priority') == 4])
            
            st.success(f"✅ {total_docs} documents loaded from Google Drive")
            
            # Show performance stats
            with st.expander("📊 Loading Performance"):
                st.write("**By Processing Speed:**")
                if fast_files > 0:
                    st.write(f"🟢 Fast: {fast_files} files (text, Google Docs)")
                if medium_files > 0:
                    st.write(f"🟡 Medium: {medium_files} files (small PDFs)")
                if slow_files > 0:
                    st.write(f"🔴 Complex: {slow_files} files (large PDFs, DOCX)")
                
                st.write("**By Priority:**")
                if priority_1 > 0:
                    st.write(f"🔥 High Priority: {priority_1} files")
                if priority_2 > 0:
                    st.write(f"📋 Medium Priority: {priority_2} files")
                if priority_3 > 0:
                    st.write(f"📂 Standard: {priority_3} files")
                if priority_4 > 0:
                    st.write(f"📦 Archive: {priority_4} files")
            
            if st.button("🔄 Smart Refresh", key="refresh_docs"):
                st.cache_data.clear()
                st.session_state.knowledge_base = []
                st.session_state.loading_complete = False
                st.rerun()
            
            st.caption("🔄 Smart caching enabled • Only changed files re-downloaded")
            
        else:
            st.warning("⚠️ No documents found")
            st.info("Check Google Drive folder and permissions")
        
        st.divider()
        
        # Admin panel with enhanced Google Drive management
        with st.expander("🔒 Admin Panel"):
            st.write("**Google Drive Document Management**")
            
            admin_password = st.text_input("Admin Password:", type="password", key="admin_password_input")
            correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
            
            if admin_password == correct_password:
                st.success("✅ Admin access granted")
                
                if knowledge_base:
                    st.subheader("🌐 Google Drive Documents")
                    
                    # Add filter options
                    filter_col1, filter_col2 = st.columns(2)
                    with filter_col1:
                        speed_filter = st.selectbox("Filter by Speed:", ["All", "Fast", "Medium", "Slow"])
                    with filter_col2:
                        priority_filter = st.selectbox("Filter by Priority:", ["All", "High (1)", "Medium (2)", "Standard (3)", "Archive (4)"])
                    
                    # Filter documents
                    filtered_docs = knowledge_base
                    if speed_filter != "All":
                        speed_map = {"Fast": "fast", "Medium": "medium", "Slow": "slow"}
                        filtered_docs = [d for d in filtered_docs if d.get('processing_speed') == speed_map[speed_filter]]
                    
                    if priority_filter != "All":
                        priority_map = {"High (1)": 1, "Medium (2)": 2, "Standard (3)": 3, "Archive (4)": 4}
                        filtered_docs = [d for d in filtered_docs if d.get('priority') == priority_map[priority_filter]]
                    
                    st.write(f"Showing {len(filtered_docs)} of {len(knowledge_base)} documents")
                    
                    for idx, doc in enumerate(filtered_docs):
                        # Create a more informative title
                        speed_emoji = {"fast": "🟢", "medium": "🟡", "slow": "🔴"}.get(doc.get('processing_speed'), "⚪")
                        priority_emoji = {1: "🔥", 2: "📋", 3: "📂", 4: "📦"}.get(doc.get('priority'), "📄")
                        
                        title = f"{speed_emoji}{priority_emoji} {doc['name']}"
                        
                        with st.expander(title):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**File:** {doc['name']}")
                                st.write(f"**Source:** Google Drive")
                                st.write(f"**Size:** {doc.get('size', 'Unknown')} bytes")
                                st.write(f"**Type:** {doc.get('mime_type', doc.get('type', 'Unknown'))}")
                            
                            with col2:
                                st.write(f"**Modified:** {doc.get('modified', 'Unknown')}")
                                st.write(f"**Processing Speed:** {doc.get('processing_speed', 'Unknown')}")
                                st.write(f"**Priority:** {doc.get('priority', 'Unknown')}")
                                if doc.get('folder_path'):
                                    st.write(f"**Folder:** {doc.get('folder_path')}")
                            
                            if doc.get('path'):
                                st.markdown(f"**[View in Drive]({doc['path']})**")
                            
                            preview_text = doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                            st.text_area("Content preview:", preview_text, height=100, disabled=True, key=f"admin_google_preview_{idx}")
                
                st.divider()
                
                st.subheader("⚙️ Configuration Status")
                
                config_items = [
                    ("Google Service Account", "Google Drive Credentials"),
                    ("AZURE_OPENAI_API_KEY", "Azure OpenAI API Key"),
                    ("AZURE_OPENAI_ENDPOINT", "Azure OpenAI Endpoint"),
                    ("LOGIN_PASSWORD", "Login Password"),
                    ("ADMIN_PASSWORD", "Admin Password")
                ]
                
                for env_var, description in config_items:
                    if env_var == "Google Service Account":
                        if "google" in st.secrets or "google_service_account" in st.secrets:
                            st.success(f"✅ {description}: Configured")
                        else:
                            st.error(f"❌ {description}: Missing")
                    else:
                        value = os.getenv(env_var) or st.secrets.get(env_var)
                        if value:
                            st.success(f"✅ {description}: Configured")
                        else:
                            st.error(f"❌ {description}: Missing")
                
                st.divider()
                
                st.subheader("📋 Configuration Reference")
                st.code('''
# Add these to your Streamlit secrets:

# Google Drive Configuration
[google]
type = "service_account"
project_id = "magnus-knowledge-base"
private_key_id = "your-private-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
your-private-key-content
-----END PRIVATE KEY-----"""
client_email = "magnus-drive-service@magnus-knowledge-base.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"

[drive]
folder_name = "MAGnus Knowledge Base"

# Login credentials
LOGIN_PASSWORD = "your-secure-login-password"
ADMIN_PASSWORD = "your-admin-password"

# Azure OpenAI
AZURE_OPENAI_API_KEY = "your-key"
AZURE_OPENAI_ENDPOINT = "your-endpoint"
AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4.1-mini"
                ''', language="toml")
                
            elif admin_password:
                st.error("❌ Incorrect password")
            else:
                st.info("🔑 Enter admin password for configuration status")
        
        st.divider()
        
        # Chat controls
        if st.session_state.messages:
            if st.button("🗑️ Clear Chat", type="secondary", key="clear_chat_button"):
                st.session_state.messages = []
                st.session_state.conversation_state = "initial"
                st.session_state.current_category = None
                st.rerun()

        if st.session_state.conversation_state != "initial":
            if st.button("🔄 Start New Conversation", key="restart_conversation"):
                st.session_state.messages = []
                st.session_state.conversation_state = "initial"
                st.session_state.current_category = None
                st.rerun()

    # Main chat area
    col1, col2 = st.columns([3, 1])

    with col1:
        # Show initial welcome message automatically when chat loads
        if not st.session_state.messages and st.session_state.conversation_state == "initial":
            # Add the welcome message to session state immediately
            welcome_response = """👋 Welcome to MAGnus Knowledge Bot!

I'm here to help! To provide you with the best assistance, please let me know what type of request this is:

🤔 **Question** - I need information or guidance
📄 **Change** - I want to suggest an improvement or new feature  
⚠️ **Issue** - Something isn't working as expected
🔧 **Problem** - I'm experiencing a technical difficulty

Please type one of these options: **Question**, **Change**, **Issue**, or **Problem**"""
            
            st.session_state.messages.append({"role": "assistant", "content": welcome_response})
            st.session_state.conversation_state = "categorizing"
        
        # Display chat history (including the welcome message)
        for idx, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    with col2:
        # Export functionality
        if st.session_state.messages:
            st.subheader("💾 Export")
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "knowledge_base_docs": [doc["name"] for doc in knowledge_base],
                "knowledge_base_source": "google_drive",
                "performance_stats": {
                    "total_documents": len(knowledge_base),
                    "fast_files": len([d for d in knowledge_base if d.get('processing_speed') == 'fast']),
                    "medium_files": len([d for d in knowledge_base if d.get('processing_speed') == 'medium']),
                    "slow_files": len([d for d in knowledge_base if d.get('processing_speed') == 'slow'])
                },
                "messages": st.session_state.messages
            }
            
            st.download_button(
                label="📤 Export Chat",
                data=json.dumps(export_data, indent=2),
                file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                help="Download conversation history",
                key="export_chat_button"
            )

    # Chat input with dynamic placeholder
    if st.session_state.conversation_state == "initial":
        placeholder_text = "Hello! How can I help you today?"
    elif st.session_state.conversation_state == "waiting_for_issue":
        placeholder_text = "Please describe your issue in detail..."
    elif st.session_state.conversation_state == "waiting_for_problem":
        placeholder_text = "Please describe your problem in detail..."
    else:
        placeholder_text = "Type your question here..."
        
    user_input = st.chat_input(placeholder_text, key="main_chat_input")

    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Handle different conversation states
        if st.session_state.conversation_state == "initial":
            with st.chat_message("assistant"):
                response = """I'm here to help! To provide you with the best assistance, please let me know what type of request this is:

🤔 **Question** - I need information or guidance
📄 **Change** - I want to suggest an improvement or new feature  
⚠️ **Issue** - Something isn't working as expected
🔧 **Problem** - I'm experiencing a technical difficulty

Please type one of these options: **Question**, **Change**, **Issue**, or **Problem**"""
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.conversation_state = "categorizing"
        
        elif st.session_state.conversation_state == "categorizing":
            user_choice = user_input.lower().strip()
            
            with st.chat_message("assistant"):
                if "question" in user_choice:
                    st.session_state.current_category = "question"
                    response = "Perfect! What would you like to know? Please ask your question and I'll search through our company documents to find the answer."
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.conversation_state in ["waiting_for_issue", "waiting_for_problem", "categorized"]:
            # Check for positive/completion responses
            positive_indicators = ['thank you', 'thanks', 'sorted', 'solved', 'fixed', 'resolved', 'perfect', 'great', 'awesome', 'excellent', 'done', 'good', 'helpful', 'appreciate']
            user_lower = user_input.lower()
            
            if any(indicator in user_lower for indicator in positive_indicators):
                with st.chat_message("assistant"):
                    response = "You're welcome! I'm glad I could help. 😊\n\nStarting a fresh conversation for you..."
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # Clear the chat and reset state after a brief pause
                    import time
                    time.sleep(1)
                    st.session_state.messages = []
                    st.session_state.conversation_state = "initial"
                    st.session_state.current_category = None
                    st.rerun()
            
            elif not AZURE_OPENAI_AVAILABLE:
                with st.chat_message("assistant"):
                    st.error("AI service is not available.")
            else:
                try:
                    api_key = os.getenv("AZURE_OPENAI_API_KEY")
                    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                    if not api_key or not endpoint:
                        with st.chat_message("assistant"):
                            st.error("AI service is not configured.")
                    else:
                        with st.chat_message("assistant"):
                            with st.spinner("🤔 Searching through company documents..."):
                                placeholder = st.empty()
                                full_response = ""
                                
                                # Prepare knowledge base context with priority information
                                knowledge_context = ""
                                if knowledge_base:
                                    # Sort documents by priority for context (high priority first)
                                    sorted_docs = sorted(knowledge_base, key=lambda x: x.get('priority', 3))
                                    knowledge_context = "\n\n".join([
                                        f"Document: {doc['name']} (Source: Google Drive, Priority: {doc.get('priority', 'Unknown')})\n{doc['content']}" 
                                        for doc in sorted_docs
                                    ])
                                
                                # System message with knowledge base
                                system_message = {
                                    "role": "system", 
                                    "content": f"""You are a company knowledge base assistant. You ONLY provide information that can be found in the company documents provided to you.

{f"COMPANY KNOWLEDGE BASE:\n{knowledge_context}" if knowledge_context else "You don't currently have access to any company documents."}

IMPORTANT RESTRICTIONS:
1. ONLY answer questions using information directly found in the company documents above
2. If the answer is not in the company documents, respond with: "I cannot find that information in our company documents. Please contact your manager or HR for assistance with this question."
3. Do NOT provide general advice, external information, or assumptions
4. Do NOT make up information or provide answers based on general knowledge
5. Always cite which specific document contains the information you're referencing
6. If a question is partially covered in the documents, only answer the parts that are documented
7. The documents are organized by priority - higher priority documents contain more essential information

Your role is to be a reliable source of company-specific information only."""
                                }
                                
                                messages_for_api = [system_message] + st.session_state.messages
                                
                                # Call Azure OpenAI API
                                stream, error = call_openai_api(messages_for_api)
                            
                            if error:
                                error_msg = f"AI Error: {error}"
                                st.error(error_msg)
                                placeholder.markdown(error_msg)
                            elif stream:
                                try:
                                    for chunk in stream:
                                        if (hasattr(chunk, 'choices') and 
                                            len(chunk.choices) > 0 and 
                                            hasattr(chunk.choices[0], 'delta') and
                                            hasattr(chunk.choices[0].delta, 'content') and
                                            chunk.choices[0].delta.content is not None):
                                            
                                            delta = chunk.choices[0].delta.content
                                            full_response += delta
                                            placeholder.markdown(full_response + "▌")
                                    
                                    placeholder.markdown(full_response)
                                    
                                    st.session_state.messages.append({
                                        "role": "assistant", 
                                        "content": full_response
                                    })
                                    
                                    # Follow-up for issues/problems
                                    if st.session_state.conversation_state in ["waiting_for_issue", "waiting_for_problem"]:
                                        if "cannot find that information" not in full_response.lower():
                                            follow_up = f"\n\n---\n\nDid this information help resolve your {st.session_state.current_category}? If not, you can submit an **[Innovation Request](https://www.jotform.com/form/250841782712054)** to get additional support."
                                            placeholder.markdown(full_response + follow_up)
                                            st.session_state.messages[-1]["content"] += follow_up
                                        else:
                                            follow_up = f"\n\n---\n\nSince I couldn't find specific information about your {st.session_state.current_category}, I recommend submitting an **[Innovation Request](https://www.jotform.com/form/250841782712054)** to get proper support from our team."
                                            placeholder.markdown(full_response + follow_up)
                                            st.session_state.messages[-1]["content"] += follow_up
                                        
                                        st.session_state.conversation_state = "completed"
                                    
                                except Exception as e:
                                    error_msg = f"Streaming Error: {str(e)}"
                                    st.error(error_msg)
                                    placeholder.markdown(error_msg)
                
                except Exception as e:
                    with st.chat_message("assistant"):
                        st.error(f"Unexpected error: {str(e)}")

    # Footer with enhanced performance info
    st.markdown("---")
    
    # Dynamic footer based on loaded documents and performance
    footer_parts = []
    footer_parts.append("MAGnus Knowledge Bot")
    
    if knowledge_base:
        total_docs = len(knowledge_base)
        fast_files = len([d for d in knowledge_base if d.get('processing_speed') == 'fast'])
        cached_files = len([d for d in knowledge_base if 'cached' in str(d.get('source', ''))])
        
        footer_parts.append(f"{total_docs} documents")
        
        if fast_files > 0:
            footer_parts.append(f"{fast_files} optimized files")
        
        footer_parts.append("Smart Loading & Caching")
    else:
        footer_parts.append("Powered by Google Drive")
    
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
        f"{' • '.join(footer_parts)}"
        "</div>", 
        unsafe_allow_html=True
    )

# Main app logic
if not st.session_state.authenticated:
    show_login()
elif not st.session_state.loading_complete:
    show_loading()
else:
    show_main_app()": "assistant", "content": response})
                    st.session_state.conversation_state = "categorized"
                
                elif "change" in user_choice:
                    st.session_state.current_category = "change"
                    response = """That's fantastic! We love hearing improvement ideas from our team.

To submit your change request or suggestion, please use our **Innovation Request Form**:

🔗 **[Submit Innovation Request](https://www.jotform.com/form/250841782712054)**

This form ensures your idea gets to the right people and receives proper consideration. Thank you for helping us improve!"""
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.conversation_state = "completed"
                
                elif "issue" in user_choice:
                    st.session_state.current_category = "issue"
                    response = "I understand you're experiencing an issue. Please describe what's happening in detail, and I'll search our documentation to help resolve it."
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.conversation_state = "waiting_for_issue"
                
                elif "problem" in user_choice:
                    st.session_state.current_category = "problem"
                    response = "I'm here to help with your problem. Please explain what's going wrong, and I'll look through our resources to find a solution."
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    st.session_state.conversation_state = "waiting_for_problem"
                
                else:
                    response = """I didn't quite catch that. Please choose one of these options:

• Type **Question** if you need information
• Type **Change** if you want to suggest an improvement  
• Type **Issue** if something isn't working
• Type **Problem** if you're experiencing difficulties"""
                    st.markdown(response)
                    st.session_state.messages.append({"role
