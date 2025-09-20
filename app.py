import os
import json
import streamlit as st
import requests
import secrets
import base64
import hashlib
from datetime import datetime
from urllib.parse import urlencode, parse_qs, urlparse

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

# Import Dropbox
try:
    import dropbox
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False

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

# Dropbox OAuth 2 functions
class DropboxOAuthConnector:
    def __init__(self):
        self.client_id = os.getenv("DROPBOX_CLIENT_ID")
        self.client_secret = os.getenv("DROPBOX_CLIENT_SECRET")
        self.redirect_uri = os.getenv("DROPBOX_REDIRECT_URI", "http://localhost:8501")
        self.folder_path = os.getenv("DROPBOX_FOLDER_PATH", "/MAGnus")
        self.access_token = None
        self.dbx = None
    
    def generate_auth_url(self):
        """Generate Dropbox OAuth 2 authorization URL with PKCE"""
        if not self.client_id:
            raise Exception("Dropbox Client ID not configured")
        
        # Generate PKCE code verifier and challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        # Store code verifier in session state
        st.session_state.code_verifier = code_verifier
        
        # Build authorization URL
        auth_params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'scope': 'files.metadata.read files.content.read',
            'state': secrets.token_urlsafe(32)  # CSRF protection
        }
        
        # Store state for verification
        st.session_state.oauth_state = auth_params['state']
        
        auth_url = f"https://www.dropbox.com/oauth2/authorize?{urlencode(auth_params)}"
        return auth_url
    
    def handle_oauth_callback(self, authorization_code, state):
        """Handle OAuth callback and exchange code for access token"""
        # Verify state parameter (CSRF protection)
        if state != st.session_state.get('oauth_state'):
            raise Exception("Invalid state parameter - possible CSRF attack")
        
        if not hasattr(st.session_state, 'code_verifier'):
            raise Exception("Code verifier not found in session")
        
        # Exchange authorization code for access token
        token_data = {
            'code': authorization_code,
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'code_verifier': st.session_state.code_verifier
        }
        
        response = requests.post('https://api.dropboxapi.com/oauth2/token', data=token_data)
        
        if response.status_code == 200:
            token_response = response.json()
            self.access_token = token_response['access_token']
            
            # Store token in session state (in production, use encrypted storage)
            st.session_state.dropbox_access_token = self.access_token
            st.session_state.dropbox_authenticated = True
            
            # Initialize Dropbox client
            self.dbx = dropbox.Dropbox(self.access_token)
            
            return True
        else:
            raise Exception(f"Token exchange failed: {response.text}")
    
    def initialize_client(self, access_token=None):
        """Initialize Dropbox client with access token"""
        token = access_token or st.session_state.get('dropbox_access_token')
        if token and DROPBOX_AVAILABLE:
            self.access_token = token
            self.dbx = dropbox.Dropbox(token)
            return True
        return False
    
    def test_connection(self):
        """Test if the Dropbox connection is working"""
        if not self.dbx:
            return False, "No Dropbox client initialized"
        
        try:
            account_info = self.dbx.users_get_current_account()
            return True, f"Connected as: {account_info.name.display_name}"
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"
    
    def get_documents(self):
        """Fetch documents from Dropbox folder"""
        if not self.dbx:
            raise Exception("Dropbox client not initialized")
        
        try:
            documents = []
            
            # List files in the specified folder
            result = self.dbx.files_list_folder(self.folder_path)
            
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    # Process multiple file types
                    file_extension = entry.name.lower().split('.')[-1]
                    
                    if file_extension in ['txt', 'md', 'csv', 'pdf', 'docx']:
                        content = self.get_file_content(entry.path_lower, file_extension)
                        if content and not content.startswith("Cannot process") and not content.startswith("Error"):
                            documents.append({
                                'name': entry.name,
                                'content': content,
                                'source': 'dropbox_oauth',
                                'modified': entry.server_modified.isoformat() if entry.server_modified else '',
                                'size': entry.size,
                                'path': entry.path_lower,
                                'type': file_extension
                            })
            
            return documents
            
        except dropbox.exceptions.AuthError:
            # Clear stored token if auth fails
            if 'dropbox_access_token' in st.session_state:
                del st.session_state.dropbox_access_token
            if 'dropbox_authenticated' in st.session_state:
                del st.session_state.dropbox_authenticated
            raise Exception("Dropbox authentication expired. Please re-authenticate.")
        except dropbox.exceptions.ApiError as e:
            raise Exception(f"Dropbox API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error fetching Dropbox documents: {str(e)}")
    
    def get_file_content(self, file_path, file_extension):
        """Get content of a specific file based on its type"""
        try:
            _, response = self.dbx.files_download(file_path)
            
            if file_extension in ['txt', 'md', 'csv']:
                # Text files
                content = response.content.decode('utf-8')
                return content
            
            elif file_extension == 'pdf' and PDF_AVAILABLE:
                # PDF files
                import io
                pdf_file = io.BytesIO(response.content)
                
                if hasattr(pypdf, 'PdfReader'):
                    pdf_reader = pypdf.PdfReader(pdf_file)
                else:
                    pdf_reader = pypdf.PdfFileReader(pdf_file)
                
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                return text_content.strip()
            
            elif file_extension == 'docx' and DOCX_AVAILABLE:
                # DOCX files
                import io
                docx_file = io.BytesIO(response.content)
                doc = Document(docx_file)
                
                text_content = ""
                for paragraph in doc.paragraphs:
                    text_content += paragraph.text + "\n"
                
                return text_content.strip()
            
            else:
                # Unsupported file type or missing library
                missing_libs = []
                if file_extension == 'pdf' and not PDF_AVAILABLE:
                    missing_libs.append("pypdf")
                if file_extension == 'docx' and not DOCX_AVAILABLE:
                    missing_libs.append("python-docx")
                
                if missing_libs:
                    return f"Cannot process {file_extension.upper()} files. Missing libraries: {', '.join(missing_libs)}"
                else:
                    return f"Unsupported file type: {file_extension}"
                    
        except UnicodeDecodeError:
            return f"File {file_path} contains binary data - cannot display as text"
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"

# Initialize Dropbox connector
@st.cache_resource
def get_dropbox_connector():
    return DropboxOAuthConnector()

# Load documents from Dropbox
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def load_knowledge_base():
    """Load documents from Dropbox with OAuth authentication"""
    connector = get_dropbox_connector()
    
    # Check if user is authenticated with Dropbox
    if not st.session_state.get('dropbox_authenticated', False):
        return []
    
    # Initialize client with stored token
    if not connector.initialize_client():
        return []
    
    if not DROPBOX_AVAILABLE:
        raise Exception("Dropbox library not available. Check requirements.txt")
    
    try:
        documents = connector.get_documents()
        return documents
    except Exception as e:
        # If authentication fails, clear stored credentials
        if "authentication expired" in str(e).lower():
            if 'dropbox_access_token' in st.session_state:
                del st.session_state.dropbox_access_token
            if 'dropbox_authenticated' in st.session_state:
                del st.session_state.dropbox_authenticated
        raise Exception(f"Error loading documents: {str(e)}")

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

if "dropbox_authenticated" not in st.session_state:
    st.session_state.dropbox_authenticated = False

# Handle OAuth callback
def handle_oauth_callback():
    """Handle OAuth callback from URL parameters"""
    # Get URL parameters
    query_params = st.query_params
    
    if 'code' in query_params and 'state' in query_params:
        connector = get_dropbox_connector()
        try:
            success = connector.handle_oauth_callback(
                query_params['code'], 
                query_params['state']
            )
            if success:
                st.success("✅ Dropbox authentication successful!")
                # Clear URL parameters
                st.query_params.clear()
                # Force reload to refresh the app state
                st.rerun()
            else:
                st.error("❌ Dropbox authentication failed")
        except Exception as e:
            st.error(f"❌ OAuth error: {str(e)}")
            # Clear any partial auth state
            if 'dropbox_access_token' in st.session_state:
                del st.session_state.dropbox_access_token
            if 'dropbox_authenticated' in st.session_state:
                del st.session_state.dropbox_authenticated

# Login function
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
    
    Please log in to access the company knowledge base.
    """)
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login", use_container_width=True)
        
        if login_button:
            correct_username = "MAG"
            correct_password = st.secrets.get("LOGIN_PASSWORD", "defaultpassword")
            
            if username == correct_username and password == correct_password:
                st.session_state.authenticated = True
                st.session_state.loading_complete = False
                st.success("Login successful! Checking Dropbox connection...")
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

# Dropbox authentication function
def show_dropbox_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("MAGNUS AI Logo Design.png", width=150)
        except:
            pass
    
    st.title("🔗 Connect to Dropbox")
    
    st.markdown("""
    **Secure Dropbox Integration**
    
    To access your company knowledge base, we need to connect to Dropbox using secure OAuth 2.0 authentication.
    
    This ensures your data remains secure and we only access the documents you've authorized.
    """)
    
    connector = get_dropbox_connector()
    
    # Check if we have the necessary configuration
    if not connector.client_id:
        st.error("❌ Dropbox OAuth not configured. Please contact your administrator.")
        if st.button("🚪 Logout"):
            logout()
        return
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔗 Connect to Dropbox", type="primary", use_container_width=True):
            try:
                auth_url = connector.generate_auth_url()
                st.markdown(f"**[Click here to authenticate with Dropbox]({auth_url})**")
                st.info("👆 Click the link above to authorize MAGnus to access your Dropbox documents.")
                st.markdown("After authorization, you'll be redirected back here automatically.")
            except Exception as e:
                st.error(f"Error generating authentication URL: {str(e)}")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()

# Loading function
def show_loading():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("MAGNUS AI Logo Design.png", width=150)
        except:
            pass
    
    st.title("🤖 MAGnus Knowledge Bot")
    
    st.markdown("### 📚 Loading Knowledge Base")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("Connecting to Dropbox...")
    progress_bar.progress(20)
    
    connector = get_dropbox_connector()
    
    # Check if authenticated
    if not st.session_state.get('dropbox_authenticated', False):
        st.error("❌ Dropbox not authenticated")
        return
    
    status_text.text("Initializing Dropbox client...")
    progress_bar.progress(40)
    
    # Initialize client
    if not connector.initialize_client():
        st.error("❌ Failed to initialize Dropbox client")
        return
    
    status_text.text("Testing connection...")
    progress_bar.progress(50)
    
    # Test connection
    connected, message = connector.test_connection()
    if not connected:
        st.error(f"❌ Connection failed: {message}")
        return
    
    status_text.text("Fetching documents...")
    progress_bar.progress(70)
    
    try:
        documents = load_knowledge_base()
        st.session_state.knowledge_base = documents
        
        progress_bar.progress(90)
        status_text.text("Finalizing setup...")
        
        progress_bar.progress(100)
        status_text.text(f"✅ Loaded {len(documents)} documents successfully!")
        
        st.session_state.loading_complete = True
        
        import time
        time.sleep(1)
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error loading documents: {str(e)}")
        st.info("Please check your Dropbox configuration and try again.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retry"):
                st.rerun()
        with col2:
            if st.button("🚪 Logout"):
                logout()

# Logout function
def logout():
    st.session_state.authenticated = False
    st.session_state.loading_complete = False
    st.session_state.knowledge_base = []
    st.session_state.messages = []
    st.session_state.dropbox_authenticated = False
    if 'dropbox_access_token' in st.session_state:
        del st.session_state.dropbox_access_token
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
        
        # Dropbox OAuth status
        if st.session_state.get('dropbox_authenticated', False):
            st.success("✅ Dropbox OAuth Connected")
            
            # Show connection test
            connector = get_dropbox_connector()
            if connector.initialize_client():
                connected, message = connector.test_connection()
                if connected:
                    st.info(f"👤 {message}")
                else:
                    st.warning(f"⚠️ {message}")
        else:
            st.error("❌ Dropbox Not Authenticated")
        
        st.info("🔐 **Secure OAuth 2.0 Integration**")
        
        st.divider()
        
        st.header("📚 Knowledge Base")
        
        if knowledge_base:
            st.success(f"✅ {len(knowledge_base)} Dropbox documents loaded")
            
            if st.button("🔄 Refresh Documents", key="refresh_docs"):
                st.session_state.knowledge_base = []
                st.session_state.loading_complete = False
                st.rerun()
            
            st.caption("📅 Auto-refreshes every 30 minutes")
            
        else:
            st.warning("⚠️ No Dropbox documents found")
            st.info("Check Dropbox folder and permissions")
        
        st.divider()
        
        # Admin panel
        with st.expander("🔒 Admin Panel"):
            st.write("**Dropbox OAuth Management**")
            
            admin_password = st.text_input("Admin Password:", type="password", key="admin_password_input")
            correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
            
            if admin_password == correct_password:
                st.success("✅ Admin access granted")
                
                # OAuth status
                st.subheader("🔐 OAuth Status")
                if st.session_state.get('dropbox_authenticated', False):
                    st.success("✅ User authenticated with Dropbox")
                    if st.button("🚪 Revoke Dropbox Access", type="secondary"):
                        if 'dropbox_access_token' in st.session_state:
                            del st.session_state.dropbox_access_token
                        st.session_state.dropbox_authenticated = False
                        st.success("Dropbox access revoked")
                        st.rerun()
                else:
                    st.warning("❌ User not authenticated with Dropbox")
                
                if knowledge_base:
                    st.subheader("📄 Dropbox Documents")
                    for idx, doc in enumerate(knowledge_base):
                        with st.expander(f"📄 {doc['name']}"):
                            st.write(f"**File:** {doc['name']}")
                            st.write(f"**Source:** Dropbox OAuth")
                            st.write(f"**Size:** {doc.get('size', 'Unknown')} bytes")
                            st.write(f"**Modified:** {doc.get('modified', 'Unknown')}")
                            st.write(f"**Path:** {doc.get('path', 'Unknown')}")
                            preview_text = doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                            st.text_area("Content preview:", preview_text, height=100, disabled=True, key=f"admin_preview_{idx}")
                
                st.divider()
                
                st.subheader("⚙️ OAuth Configuration Status")
                
                config_items = [
                    ("DROPBOX_CLIENT_ID", "Dropbox Client ID"),
                    ("DROPBOX_CLIENT_SECRET", "Dropbox Client Secret"),
                    ("DROPBOX_REDIRECT_URI", "Redirect URI"),
                    ("DROPBOX_FOLDER_PATH", "Dropbox Folder Path")
                ]
                
                for env_var, description in config_items:
                    value = os.getenv(env_var)
                    if value:
                        st.success(f"✅ {description}: Configured")
                    else:
                        if env_var in ["DROPBOX_REDIRECT_URI", "DROPBOX_FOLDER_PATH"]:
                            default_val = "http://localhost:8501" if env_var == "DROPBOX_REDIRECT_URI" else "/MAGnus"
                            st.info(f"ℹ️ {description}: Using default ({default_val})")
                        else:
                            st.error(f"❌ {description}: Missing")
                
                st.divider()
                
                st.subheader("📋 Configuration Reference")
                st.code('''
# Add these to your Streamlit secrets:
DROPBOX_CLIENT_ID = "your-dropbox-app-key"
DROPBOX_CLIENT_SECRET = "your-dropbox-app-secret"
DROPBOX_REDIRECT_URI = "http://localhost:8501"  # or your deployed URL
DROPBOX_FOLDER_PATH = "/MAGnus"

# Login credentials
LOGIN_PASSWORD = "your-secure-login-password"

# Azure OpenAI (existing)
AZURE_OPENAI_API_KEY = "your-key"
AZURE_OPENAI_ENDPOINT = "your-endpoint"
AZURE_OPENAI_DEPLOYMENT_NAME = "gpt-4.1-mini"
ADMIN_PASSWORD = "your-admin-password"
                ''', language="toml")
                
            elif admin_password:
                st.error("❌ Incorrect password")
            else:
                st.info("🔐 Enter admin password for configuration status")
        
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
        # Display chat history
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
🔄 **Change** - I want to suggest an improvement or new feature  
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
                    responses = [
                        "Great! I'm here to help answer your question. What would you like to know?",
                        "Perfect! Ask away - I'll search through our company documents to find the answer.",
                        "Excellent! What can I help you learn about today?",
                        "Wonderful! I'm ready to help with your question."
                    ]
                    import random
                    response = random.choice(responses)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
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
                    st.session_state.messages.append({"role": "assistant", "content": response})
        
        elif st.session_state.conversation_state in ["waiting_for_issue", "waiting_for_problem", "categorized"]:
            if not AZURE_OPENAI_AVAILABLE:
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
                                
                                # Prepare knowledge base context
                                knowledge_context = ""
                                if knowledge_base:
                                    knowledge_context = "\n\n".join([
                                        f"Document: {doc['name']}\n{doc['content']}" 
                                        for doc in knowledge_base
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

        # Show initial categorization if no messages yet
        if not st.session_state.messages and st.session_state.conversation_state == "initial":
            with st.chat_message("assistant"):
                response = """👋 Welcome to MAGnus Knowledge Bot!

I'm here to help! To provide you with the best assistance, please let me know what type of request this is:

🤔 **Question** - I need information or guidance
🔄 **Change** - I want to suggest an improvement or new feature  
⚠️ **Issue** - Something isn't working as expected
🔧 **Problem** - I'm experiencing a technical difficulty

Please type one of these options: **Question**, **Change**, **Issue**, or **Problem**"""
                
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.conversation_state = "categorizing"

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
        f"MAGnus Knowledge Bot • {len(knowledge_base)} documents • Secured with OAuth 2.0"
        "</div>", 
        unsafe_allow_html=True
    )

# Main app logic with OAuth callback handling
if __name__ == "__main__":
    # Handle OAuth callback first
    handle_oauth_callback()
    
    # Main app flow
    if not st.session_state.authenticated:
        show_login()
    elif st.session_state.authenticated and not st.session_state.get('dropbox_authenticated', False):
        show_dropbox_auth()
    elif not st.session_state.loading_complete:
        show_loading()
    else:
        show_main_app()
