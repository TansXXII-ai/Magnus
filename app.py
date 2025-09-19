import os
import json
import streamlit as st
from datetime import datetime
import glob
import sys

# Page config
st.set_page_config(
    page_title="Knowledge Base Chatbot", 
    page_icon="🤖",
    layout="wide"
)

# Try importing document processing libraries
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

# Try importing OpenAI libraries
openai_status = "❌ Not available"
AZURE_OPENAI_AVAILABLE = False

try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
    openai_status = "✅ Azure OpenAI imported successfully"
except ImportError as e:
    openai_status = f"❌ Azure OpenAI import failed: {e}"

# Title
st.title("🤖 Knowledge Base Chatbot")

# Debug section (keep this in main area since it's collapsible)
with st.expander("🔍 Debug Information"):
    st.write("🐍 Python version:", sys.version)
    st.write("🤖 Azure OpenAI Status:", openai_status)
    st.write("📄 PDF Support:", "✅ Available" if PDF_AVAILABLE else "❌ Not available")
    st.write("📝 DOCX Support:", "✅ Available" if DOCX_AVAILABLE else "❌ Not available")
    
    # Show Azure OpenAI configuration
    if AZURE_OPENAI_AVAILABLE:
        st.write("🔧 **Azure OpenAI Configuration:**")
        st.write(f"  • API Key: {'✅ Set' if os.getenv('AZURE_OPENAI_API_KEY') else '❌ Missing'}")
        st.write(f"  • Endpoint: {'✅ Set' if os.getenv('AZURE_OPENAI_ENDPOINT') else '❌ Missing'}")
        st.write(f"  • Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'magroupAI')}")

# Clean main area - just show essential info
st.markdown("---")

# Ensure knowledge_base directory exists
os.makedirs("knowledge_base", exist_ok=True)

# Load knowledge base documents
@st.cache_data
def load_knowledge_base():
    """Load all documents from the knowledge base folder"""
    documents = []
    knowledge_base_path = "knowledge_base"
    
    if not os.path.exists(knowledge_base_path):
        return []
    
    # Supported file types based on available libraries
    file_patterns = [f"{knowledge_base_path}/*.txt"]
    if PDF_AVAILABLE:
        file_patterns.append(f"{knowledge_base_path}/*.pdf")
    if DOCX_AVAILABLE:
        file_patterns.append(f"{knowledge_base_path}/*.docx")
    
    for pattern in file_patterns:
        for file_path in glob.glob(pattern):
            try:
                filename = os.path.basename(file_path)
                text_content = ""
                
                if file_path.endswith('.txt'):
                    # Plain text
                    with open(file_path, 'r', encoding='utf-8') as file:
                        text_content = file.read()
                
                elif file_path.endswith('.pdf') and PDF_AVAILABLE:
                    # PDF processing
                    with open(file_path, 'rb') as file:
                        if hasattr(pypdf, 'PdfReader'):
                            pdf_reader = pypdf.PdfReader(file)
                        else:
                            pdf_reader = pypdf.PdfFileReader(file)
                        
                        for page in pdf_reader.pages:
                            text_content += page.extract_text() + "\n"
                
                elif file_path.endswith('.docx') and DOCX_AVAILABLE:
                    # DOCX processing
                    doc = Document(file_path)
                    for paragraph in doc.paragraphs:
                        text_content += paragraph.text + "\n"
                
                if text_content.strip():
                    documents.append({
                        'name': filename,
                        'content': text_content.strip(),
                        'path': file_path
                    })
            
            except Exception as e:
                st.error(f"Error loading {filename}: {str(e)}")
    
    return documents

def call_openai_api(messages):
    """Call Azure OpenAI API"""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "magroupAI")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    if not api_key:
        return None, "No Azure OpenAI API key found"
    if not endpoint:
        return None, "No Azure OpenAI endpoint found"
    
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        
        return client.chat.completions.create(
            model=deployment_name,  # This should be your deployment name
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

# Sidebar for knowledge base info and admin panel
with st.sidebar:
    # Status section at top of sidebar
    st.header("📊 Status")
    
    # Show AI status
    if AZURE_OPENAI_AVAILABLE:
        st.success("✅ Azure OpenAI Connected")
    else:
        st.error("❌ Azure OpenAI Unavailable")
    
    # Show document support status
    doc_support = []
    if PDF_AVAILABLE:
        doc_support.append("PDF")
    if DOCX_AVAILABLE:
        doc_support.append("DOCX")
    doc_support.append("TXT")
    
    st.info(f"📄 **Supported:** {', '.join(doc_support)}")
    
    st.divider()
    
    st.header("📚 Knowledge Base")
    
    if knowledge_base:
        st.success(f"✅ {len(knowledge_base)} documents loaded")
        
        # Show loaded documents
        with st.expander("📄 Available Documents"):
            for idx, doc in enumerate(knowledge_base):
                st.write(f"• **{doc['name']}**")
                if st.checkbox(f"Preview {doc['name']}", key=f"preview_doc_{idx}"):
                    preview_text = doc['content'][:300] + "..." if len(doc['content']) > 300 else doc['content']
                    st.text_area("Content preview:", preview_text, height=100, disabled=True, key=f"preview_text_{idx}")
    else:
        st.warning("⚠️ Knowledge base is empty")
        st.info("Use the Admin Panel below to add documents")
    
    st.divider()
    
    # 🔒 ADMIN PANEL
    with st.expander("🔒 Admin Panel"):
        st.write("**Secure Document Management**")
        
        # Admin password check
        admin_password = st.text_input("Admin Password:", type="password", key="admin_password_input")
        correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
        
        if admin_password == correct_password:
            st.success("✅ Admin access granted")
            
            # Upload new documents
            st.subheader("📤 Upload Documents")
            
            # Dynamic file types based on available libraries
            allowed_types = ['txt']
            if PDF_AVAILABLE:
                allowed_types.append('pdf')
            if DOCX_AVAILABLE:
                allowed_types.append('docx')
            
            uploaded_files = st.file_uploader(
                f"Upload documents ({', '.join(t.upper() for t in allowed_types)}):",
                type=allowed_types,
                accept_multiple_files=True,
                key="document_uploader",
                help=f"Supported formats: {', '.join(t.upper() for t in allowed_types)}"
            )
            
            # Manual text input option
            st.subheader("✍️ Add Document Manually")
            manual_doc_name = st.text_input("Document name:", placeholder="e.g., company-policy.txt", key="manual_doc_name")
            manual_doc_content = st.text_area(
                "Document content:", 
                height=200,
                placeholder="Paste your document content here...",
                key="manual_doc_content"
            )
            
            if st.button("💾 Save Manual Document", type="secondary", key="save_manual_doc") and manual_doc_name and manual_doc_content:
                try:
                    # Ensure .txt extension
                    if not manual_doc_name.endswith('.txt'):
                        manual_doc_name += '.txt'
                    
                    # Save manual content to file
                    file_path = os.path.join("knowledge_base", manual_doc_name)
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(manual_doc_content)
                    st.success(f"✅ {manual_doc_name} saved successfully!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving {manual_doc_name}: {str(e)}")
            
            if uploaded_files:
                if st.button("💾 Save Uploaded Documents", type="primary", key="save_uploaded_docs"):
                    for uploaded_file in uploaded_files:
                        try:
                            # Save file to knowledge_base folder
                            file_path = os.path.join("knowledge_base", uploaded_file.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            st.success(f"✅ {uploaded_file.name} saved successfully!")
                        except Exception as e:
                            st.error(f"❌ Error saving {uploaded_file.name}: {str(e)}")
                    
                    # Clear cache to reload documents
                    st.cache_data.clear()
                    st.rerun()
            
            # Manage existing documents
            if knowledge_base:
                st.subheader("🗑️ Manage Documents")
                for idx, doc in enumerate(knowledge_base):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📄 {doc['name']}")
                    with col2:
                        if st.button("🗑️", key=f"delete_doc_{idx}", help=f"Delete {doc['name']}"):
                            try:
                                os.remove(doc['path'])
                                st.success(f"✅ {doc['name']} deleted")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error deleting {doc['name']}: {str(e)}")
        
        elif admin_password:
            st.error("❌ Incorrect password")
        else:
            st.info("🔐 Enter admin password to manage documents")
    
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

# Chat input (MUST be outside columns and have unique key)
user_input = st.chat_input("Ask me anything - I have access to the knowledge base...", key="main_chat_input")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Generate assistant response
    if not AZURE_OPENAI_AVAILABLE:
        with st.chat_message("assistant"):
            st.error("❌ Azure OpenAI library is not available. Cannot generate responses.")
            st.info("💡 Make sure the OpenAI library is installed and Azure OpenAI credentials are configured.")
    else:
        try:
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if not api_key or not endpoint:
                with st.chat_message("assistant"):
                    st.error("❌ Azure OpenAI credentials not found. Please check your configuration.")
                    if not api_key:
                        st.error("  • Missing: AZURE_OPENAI_API_KEY")
                    if not endpoint:
                        st.error("  • Missing: AZURE_OPENAI_ENDPOINT")
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
                        "content": f"""You are a helpful AI assistant with access to a knowledge base. 

{f"KNOWLEDGE BASE:\\n{knowledge_context}" if knowledge_context else "You don't currently have access to any knowledge base documents."}

When answering questions:
1. First check if the answer can be found in the knowledge base documents
2. If found, provide the answer and mention which document it came from
3. If not in the knowledge base, provide a helpful general answer
4. Be accurate and cite your sources when using the knowledge base
5. If you're unsure, say so rather than guessing

Please provide helpful, accurate responses."""
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
                                # Check if chunk has choices and content
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

# Information panel (remove - status now in sidebar)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    f"Knowledge Base Chatbot • {len(knowledge_base)} documents loaded • Azure OpenAI {'✅' if AZURE_OPENAI_AVAILABLE else '❌'}"
    "</div>", 
    unsafe_allow_html=True
)
