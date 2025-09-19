import os
import json
import streamlit as st
from datetime import datetime
import requests
import base64

# Page config
st.set_page_config(
    page_title="Knowledge Base Chatbot", 
    page_icon="🤖",
    layout="wide"
)

# Import Azure OpenAI
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False

# Title
st.title("🤖 Knowledge Base Chatbot")

# SharePoint API functions
class SharePointConnector:
    def __init__(self):
        self.tenant_id = os.getenv("MS_TENANT_ID")
        self.client_id = os.getenv("MS_CLIENT_ID") 
        self.client_secret = os.getenv("MS_CLIENT_SECRET")
        self.site_url = os.getenv("SHAREPOINT_SITE_URL")  # e.g., "https://yourcompany.sharepoint.com/sites/documents"
        self.access_token = None
    
    def get_access_token(self):
        """Get access token for Microsoft Graph API"""
        try:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            response = requests.post(token_url, data=data)
            if response.status_code == 200:
                self.access_token = response.json()['access_token']
                return True
            return False
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return False
    
    def get_site_documents(self, folder_path="Documents"):
        """Fetch documents from SharePoint site"""
        if not self.access_token and not self.get_access_token():
            return []
        
        try:
            # Get site ID first
            site_api_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_url}"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Get documents from specified folder
            docs_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_url}/drive/root:/{folder_path}:/children"
            
            response = requests.get(docs_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json().get('value', [])
                documents = []
                
                for file_info in files:
                    if file_info.get('file'):  # Only process files, not folders
                        doc_content = self.get_file_content(file_info['id'])
                        if doc_content:
                            documents.append({
                                'name': file_info['name'],
                                'content': doc_content,
                                'source': 'sharepoint',
                                'modified': file_info.get('lastModifiedDateTime', ''),
                                'size': file_info.get('size', 0)
                            })
                
                return documents
            
            return []
            
        except Exception as e:
            st.error(f"Error fetching SharePoint documents: {str(e)}")
            return []
    
    def get_file_content(self, file_id):
        """Get content of a specific file"""
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            
            # Get file download URL
            download_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
            
            response = requests.get(download_url, headers=headers)
            
            if response.status_code == 200:
                # For now, handle text files only
                # You'd need additional processing for PDF/DOCX
                try:
                    return response.text
                except:
                    return "Binary file - content not readable as text"
            
            return None
            
        except Exception as e:
            return f"Error reading file: {str(e)}"

# Initialize SharePoint connector
@st.cache_resource
def get_sharepoint_connector():
    return SharePointConnector()

# Load documents from SharePoint
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_knowledge_base():
    """Load documents from SharePoint"""
    connector = get_sharepoint_connector()
    
    # Check if credentials are configured
    required_vars = ["MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET", "SHAREPOINT_SITE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.warning(f"SharePoint not configured. Missing: {', '.join(missing_vars)}")
        return []
    
    try:
        documents = connector.get_site_documents()
        return documents
    except Exception as e:
        st.error(f"Failed to load SharePoint documents: {str(e)}")
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

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

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
    
    # SharePoint status
    sharepoint_configured = all(os.getenv(var) for var in ["MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET", "SHAREPOINT_SITE_URL"])
    
    if sharepoint_configured:
        st.success("✅ SharePoint Configured")
    else:
        st.error("❌ SharePoint Not Configured")
    
    st.info("📄 **Live SharePoint Integration**")
    
    st.divider()
    
    st.header("📚 Knowledge Base")
    
    if knowledge_base:
        st.success(f"✅ {len(knowledge_base)} SharePoint documents loaded")
        
        # Show refresh button
        if st.button("🔄 Refresh Documents", key="refresh_docs"):
            st.cache_data.clear()
            st.rerun()
        
        # Show last update time
        st.caption("📅 Auto-refreshes every 10 minutes")
        
    else:
        st.warning("⚠️ No SharePoint documents found")
        if sharepoint_configured:
            st.info("Check SharePoint permissions and document folder")
        else:
            st.info("Configure SharePoint credentials in secrets")
    
    st.divider()
    
    # Admin panel
    with st.expander("🔒 Admin Panel"):
        st.write("**SharePoint Integration Management**")
        
        admin_password = st.text_input("Admin Password:", type="password", key="admin_password_input")
        correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
        
        if admin_password == correct_password:
            st.success("✅ Admin access granted")
            
            if knowledge_base:
                st.subheader("📄 SharePoint Documents")
                for idx, doc in enumerate(knowledge_base):
                    with st.expander(f"📄 {doc['name']}"):
                        st.write(f"**File:** {doc['name']}")
                        st.write(f"**Source:** SharePoint")
                        st.write(f"**Size:** {doc.get('size', 'Unknown')} bytes")
                        st.write(f"**Modified:** {doc.get('modified', 'Unknown')}")
                        preview_text = doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                        st.text_area("Content preview:", preview_text, height=100, disabled=True, key=f"admin_preview_{idx}")
            
            st.divider()
            
            st.subheader("⚙️ SharePoint Configuration Status")
            
            # Show configuration status
            config_items = [
                ("MS_TENANT_ID", "Azure Tenant ID"),
                ("MS_CLIENT_ID", "App Registration Client ID"), 
                ("MS_CLIENT_SECRET", "App Registration Secret"),
                ("SHAREPOINT_SITE_URL", "SharePoint Site URL")
            ]
            
            for env_var, description in config_items:
                value = os.getenv(env_var)
                if value:
                    st.success(f"✅ {description}: Configured")
                else:
                    st.error(f"❌ {description}: Missing")
            
            st.divider()
            
            st.subheader("📋 Quick Reference")
            st.code('''
# Add these to your Streamlit secrets:
MS_TENANT_ID = "your-azure-tenant-id"
MS_CLIENT_ID = "your-app-registration-client-id"  
MS_CLIENT_SECRET = "your-app-registration-secret"
SHAREPOINT_SITE_URL = "yourcompany.sharepoint.com/sites/yoursite"

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
                        "content": f"""You are a helpful AI assistant with access to company documents from SharePoint. 

{f"COMPANY KNOWLEDGE BASE (from SharePoint):\n{knowledge_context}" if knowledge_context else "You don't currently have access to any company documents from SharePoint."}

When answering questions:
1. First check if the answer can be found in the company documents
2. If found, provide the answer and mention which document it came from
3. If not in the company knowledge base, provide a helpful general answer
4. Be accurate and cite your sources when using company information
5. If you're unsure, say so rather than guessing

Please provide helpful, accurate responses based on company SharePoint documents when available."""
                    }
                    
                    messages_for_api = [system_message] + st.session_state.messages
                    
                    # Call Azure OpenAI API
                    stream, error = call_openai_api(messages_for_api)
                    
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
    f"SharePoint Knowledge Base Chatbot • {len(knowledge_base)} documents • Live Integration"
    "</div>", 
    unsafe_allow_html=True
)
