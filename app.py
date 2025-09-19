import os
import json
import streamlit as st
from openai import OpenAI
from datetime import datetime
import pypdf
from docx import Document
import glob

# Page config
st.set_page_config(
    page_title="Knowledge Base Chatbot", 
    page_icon="🤖",
    layout="wide"
)

# Title
st.title("🤖 Knowledge Base Chatbot")

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
    
    # Supported file types
    file_patterns = [
        f"{knowledge_base_path}/*.pdf",
        f"{knowledge_base_path}/*.txt",
        f"{knowledge_base_path}/*.docx"
    ]
    
    for pattern in file_patterns:
        for file_path in glob.glob(pattern):
            try:
                filename = os.path.basename(file_path)
                text_content = ""
                
                if file_path.endswith('.pdf'):
                    # PDF processing
                    with open(file_path, 'rb') as file:
                        pdf_reader = pypdf.PdfReader(file)
                        for page in pdf_reader.pages:
                            text_content += page.extract_text() + "\n"
                
                elif file_path.endswith('.txt'):
                    # Plain text
                    with open(file_path, 'r', encoding='utf-8') as file:
                        text_content = file.read()
                
                elif file_path.endswith('.docx'):
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

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load knowledge base
knowledge_base = load_knowledge_base()

# Sidebar for knowledge base info and admin panel
with st.sidebar:
    st.header("📚 Knowledge Base")
    
    if knowledge_base:
        st.success(f"✅ {len(knowledge_base)} documents loaded")
        
        # Show loaded documents
        with st.expander("📄 Available Documents"):
            for doc in knowledge_base:
                st.write(f"• **{doc['name']}**")
                if st.checkbox(f"Preview {doc['name']}", key=f"preview_{doc['name']}"):
                    preview_text = doc['content'][:300] + "..." if len(doc['content']) > 300 else doc['content']
                    st.text_area("Content preview:", preview_text, height=100, disabled=True)
    else:
        st.info("📁 No documents found in knowledge base")
    
    st.divider()
    
    # 🔒 ADMIN PANEL
    with st.expander("🔒 Admin Panel"):
        st.write("**Secure Document Management**")
        
        # Admin password check
        admin_password = st.text_input("Admin Password:", type="password", key="admin_pass")
        correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")  # Set this in Streamlit secrets!
        
        if admin_password == correct_password:
            st.success("✅ Admin access granted")
            
            # Upload new documents
            st.subheader("📤 Upload Documents")
            uploaded_files = st.file_uploader(
                "Upload knowledge base documents:",
                type=['pdf', 'txt', 'docx'],
                accept_multiple_files=True,
                key="admin_upload"
            )
            
            if uploaded_files:
                if st.button("💾 Save Documents", type="primary"):
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
                for doc in knowledge_base:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📄 {doc['name']}")
                    with col2:
                        if st.button("🗑️", key=f"delete_{doc['name']}", help=f"Delete {doc['name']}"):
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
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.rerun()

# Main chat area
col1, col2 = st.columns([3, 1])

with col1:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything - I have access to the knowledge base..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                st.error("❌ OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
            else:
                client = OpenAI(api_key=api_key)
                
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
                    
                    try:
                        # Create streaming response
                        stream = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages_for_api,
                            stream=True,
                            temperature=0.7,
                            max_tokens=2000
                        )
                        
                        # Stream the response
                        for chunk in stream:
                            if chunk.choices[0].delta.content is not None:
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
                        error_msg = f"❌ API Error: {str(e)}"
                        st.error(error_msg)
                        placeholder.markdown(error_msg)
        
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")

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
            help="Download conversation history"
        )

# Information panel
if not knowledge_base:
    st.warning("⚠️ **Knowledge base is empty.** Use the Admin Panel in the sidebar to upload your documents securely.")
else:
    st.info(f"💡 **I have access to {len(knowledge_base)} documents** and can answer questions about them!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    f"Knowledge Base Chatbot • {len(knowledge_base)} documents loaded"
    "</div>", 
    unsafe_allow_html=True
)
