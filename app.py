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

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "messages" not in st.session_state:
    st.session_state.messages = []

# Login function
def show_login():
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
            # Check credentials
            correct_username = "MAG"
            correct_password = st.secrets.get("LOGIN_PASSWORD", "defaultpassword")
            
            if username == correct_username and password == correct_password:
                st.session_state.authenticated = True
                st.success("Login successful! Redirecting...")
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")

# Logout function
def logout():
    st.session_state.authenticated = False
    st.session_state.messages = []  # Clear chat history on logout
    st.rerun()

# Main app (only shown when authenticated)
def show_main_app():
    
    # Header with logout button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🤖 MAGnus - MA Groups Knowledge Bot")
    with col2:
        if st.button("🚪 Logout", help="Logout from MAGnus"):
            logout()
    
    # Information section about the chatbot
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

    # Dropbox API functions
    class DropboxConnector:
        def __init__(self):
            self.access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
            self.folder_path = os.getenv("DROPBOX_FOLDER_PATH", "/MAGnus")
            self.dbx = None
            
            if self.access_token and DROPBOX_AVAILABLE:
                self.dbx = dropbox.Dropbox(self.access_token)
        
        def get_documents(self):
            """Fetch documents from Dropbox folder"""
            if not self.dbx:
                return []
            
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
                                    'source': 'dropbox',
                                    'modified': entry.server_modified.isoformat() if entry.server_modified else '',
                                    'size': entry.size,
                                    'path': entry.path_lower,
                                    'type': file_extension
                                })
                
                return documents
                
            except dropbox.exceptions.AuthError:
                st.error("❌ Dropbox authentication failed. Check your access token.")
                return []
            except dropbox.exceptions.ApiError as e:
                st.error(f"❌ Dropbox API error: {str(e)}")
                return []
            except Exception as e:
                st.error(f"❌ Error fetching Dropbox documents: {str(e)}")
                return []
        
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
        return DropboxConnector()

    # Load documents from Dropbox
    @st.cache_data(ttl=1800)  # Cache for 30 minutes instead of 5
    def load_knowledge_base():
        """Load documents from Dropbox with optimized caching"""
        connector = get_dropbox_connector()
        
        # Check if credentials are configured
        access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
        
        if not access_token:
            return []
        
        if not DROPBOX_AVAILABLE:
            st.error("❌ Dropbox library not available. Check requirements.txt")
            return []
        
        try:
            documents = connector.get_documents()
            return documents
        except Exception as e:
            # Return cached data if available, otherwise show warning
            st.warning(f"Using cached documents due to error: {str(e)}")
            return []

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

    # Load knowledge base
    knowledge_base = load_knowledge_base()

    # Sidebar
    with st.sidebar:
        # Status section
        st.header("📊 Status")
        
        if AZURE_OPENAI_AVAILABLE:
            st.success("✅ Azure OpenAI Connected")
        else:
            st.error("❌ Azure OpenAI Unavailable")
        
        # Dropbox status
        dropbox_token = os.getenv("DROPBOX_ACCESS_TOKEN")
        
        if dropbox_token and DROPBOX_AVAILABLE:
            st.success("✅ Dropbox Connected")
        elif not dropbox_token:
            st.error("❌ Dropbox Token Missing")
        elif not DROPBOX_AVAILABLE:
            st.error("❌ Dropbox Library Missing")
        
        st.info("📄 **Live Dropbox Integration**")
        
        st.divider()
        
        st.header("📚 Knowledge Base")
        
        if knowledge_base:
            st.success(f"✅ {len(knowledge_base)} Dropbox documents loaded")
            
            # Show refresh button
            if st.button("🔄 Refresh Documents", key="refresh_docs"):
                st.cache_data.clear()
                st.rerun()
            
            # Show last update time
            st.caption("📅 Auto-refreshes every 30 minutes")
            
        else:
            st.warning("⚠️ No Dropbox documents found")
            if dropbox_token:
                st.info("Check Dropbox folder and file permissions")
            else:
                st.info("Configure Dropbox access token in secrets")
        
        st.divider()
        
        # Admin panel
        with st.expander("🔒 Admin Panel"):
            st.write("**Dropbox Integration Management**")
            
            admin_password = st.text_input("Admin Password:", type="password", key="admin_password_input")
            correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
            
            if admin_password == correct_password:
                st.success("✅ Admin access granted")
                
                if knowledge_base:
                    st.subheader("📄 Dropbox Documents")
                    for idx, doc in enumerate(knowledge_base):
                        with st.expander(f"📄 {doc['name']}"):
                            st.write(f"**File:** {doc['name']}")
                            st.write(f"**Source:** Dropbox")
                            st.write(f"**Size:** {doc.get('size', 'Unknown')} bytes")
                            st.write(f"**Modified:** {doc.get('modified', 'Unknown')}")
                            st.write(f"**Path:** {doc.get('path', 'Unknown')}")
                            preview_text = doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                            st.text_area("Content preview:", preview_text, height=100, disabled=True, key=f"admin_preview_{idx}")
                
                st.divider()
                
                st.subheader("⚙️ Dropbox Configuration Status")
                
                # Show configuration status
                config_items = [
                    ("DROPBOX_ACCESS_TOKEN", "Dropbox Access Token"),
                    ("DROPBOX_FOLDER_PATH", "Dropbox Folder Path")
                ]
                
                for env_var, description in config_items:
                    value = os.getenv(env_var)
                    if value:
                        st.success(f"✅ {description}: Configured")
                    else:
                        if env_var == "DROPBOX_FOLDER_PATH":
                            st.info(f"ℹ️ {description}: Using default (/MAGnus)")
                        else:
                            st.error(f"❌ {description}: Missing")
                
                st.divider()
                
                st.subheader("📋 Quick Reference")
                st.code('''
# Add these to your Streamlit secrets:
DROPBOX_ACCESS_TOKEN = "your-dropbox-access-token"
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

    # Chat input
    user_input = st.chat_input("Ask me anything about our company documents...", key="main_chat_input")

    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Generate assistant response
        if not AZURE_OPENAI_AVAILABLE:
            with st.chat_message("assistant"):
                st.error("❌ Azure OpenAI library is not available.")
        else:
            try:
                api_key = os.getenv("AZURE_OPENAI_API_KEY")
                endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                if not api_key or not endpoint:
                    with st.chat_message("assistant"):
                        st.error("❌ Azure OpenAI credentials not configured.")
                else:
                    with st.chat_message("assistant"):
                        # Show thinking indicator
                        with st.spinner("🤔 Thinking and analyzing your question..."):
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
                                "content": f"""You are a helpful AI assistant with access to company documents from Dropbox. 

{f"COMPANY KNOWLEDGE BASE (from Dropbox):\n{knowledge_context}" if knowledge_context else "You don't currently have access to any company documents from Dropbox."}

When answering questions:
1. First check if the answer can be found in the company documents
2. If found, provide the answer and mention which document it came from
3. If not in the company knowledge base, provide a helpful general answer
4. Be accurate and cite your sources when using company information
5. If you're unsure, say so rather than guessing

Please provide helpful, accurate responses based on company Dropbox documents when available."""
                            }
                            
                            messages_for_api = [system_message] + st.session_state.messages
                            
                            # Call Azure OpenAI API
                            stream, error = call_openai_api(messages_for_api)
                        
                        # Clear the thinking indicator and show response
                        if error:
                            error_msg = f"❌ API Error: {error}"
                            st.error(error_msg)
                            placeholder.markdown(error_msg)
                        elif stream:
                            try:
                                # Stream the response with better error handling
                                for chunk in stream:
                                    if (hasattr(chunk, 'choices') and 
                                        len(chunk.choices) > 0 and 
                                        hasattr(chunk.choices[0], 'delta') and
                                        hasattr(chunk.choices[0].delta, 'content') and
                                        chunk.choices[0].delta.content is not None):
                                        
                                        delta = chunk.choices[0].delta.content
                                        full_response += delta
                                        placeholder.markdown(full_response + "▌")
                                
                                # Final response without cursor
                                placeholder.markdown(full_response)
                                
                                # Add to message history
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": full_response
                                })
                                
                            except Exception as e:
                                error_msg = f"❌ Streaming Error: {str(e)}"
                                st.error(error_msg)
                                placeholder.markdown(error_msg)
            
            except Exception as e:
                with st.chat_message("assistant"):
                    st.error(f"❌ Unexpected error: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
        f"MAGnus Knowledge Bot • {len(knowledge_base)} documents • Secured with Login"
        "</div>", 
        unsafe_allow_html=True
    )

# Main app logic
if not st.session_state.authenticated:
    show_login()
else:
    show_main_app()
