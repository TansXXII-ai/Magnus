import os
import json
import streamlit as st
from datetime import datetime
import glob

# Try importing OpenAI with both old and new versions
try:
    from openai import OpenAI  # New version (1.x)
    USE_NEW_OPENAI = True
except ImportError:
    import openai  # Old version (0.x)
    USE_NEW_OPENAI = False

# Page config
st.set_page_config(
    page_title="Knowledge Base Chatbot", 
    page_icon="🤖",
    layout="wide"
)

# Title
st.title("🤖 Knowledge Base Chatbot")

# Debug info - show which OpenAI version we're using
if USE_NEW_OPENAI:
    st.success("✅ Using OpenAI v1.x (new version)")
else:
    st.info("ℹ️ Using OpenAI v0.x (legacy version)")

# Notice about file support
st.info("📝 **Simple & Reliable:** Currently supports plain text files (.txt) and manual content input for maximum compatibility.")

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
    
    # Supported file types (only plain text for now)
    file_patterns = [
        f"{knowledge_base_path}/*.txt"
    ]
    
    for pattern in file_patterns:
        for file_path in glob.glob(pattern):
            try:
                filename = os.path.basename(file_path)
                text_content = ""
                
                if file_path.endswith('.txt'):
                    # Plain text
                    with open(file_path, 'r', encoding='utf-8') as file:
                        text_content = file.read()
                
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
    """Call OpenAI API with compatibility for both old and new versions"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if USE_NEW_OPENAI:
        # New OpenAI v1.x
        client = OpenAI(api_key=api_key)
        return client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=2000
        )
    else:
        # Old OpenAI v0.x
        openai.api_key = api_key
        return openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            temperature=0.7,
            max_tokens=2000
        )

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
        st.markdown("""
        **To add documents:**
        1. Use the Admin Panel below to upload .txt files
        2. OR manually paste content in the admin panel
        3. Documents will appear immediately
        """)
    
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
            st.subheader("📤 Upload Text Documents")
            uploaded_files = st.file_uploader(
                "Upload .txt files:",
                type=['txt'],
                accept_multiple_files=True,
                key="admin_upload",
                help="Upload plain text files only"
            )
            
            # Manual text input option
            st.subheader("✍️ Add Document Manually")
            manual_doc_name = st.text_input("Document name:", placeholder="e.g., company-policy.txt")
            manual_doc_content = st.text_area(
                "Document content:", 
                height=200,
                placeholder="Paste your document content here..."
            )
            
            if st.button("💾 Save Manual Document", type="secondary") and manual_doc_name and manual_doc_content:
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
                        # Call OpenAI API (compatible with both versions)
                        stream = call_openai_api(messages_for_api)
                        
                        # Stream the response (works with both old and new versions)
                        for chunk in stream:
                            if USE_NEW_OPENAI:
                                # New version
                                if chunk.choices[0].delta.content is not None:
                                    delta = chunk.choices[0].delta.content
                                    full_response += delta
                                    placeholder.markdown(full_response + "▌")
                            else:
                                # Old version
                                if chunk.choices[0].get('delta', {}).get('content'):
                                    delta = chunk.choices[0]['delta']['content']
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
    st.warning("⚠️ **Knowledge base is empty.** Use the Admin Panel in the sidebar to add your documents.")
    st.info("💡 **Two ways to add content:** Upload .txt files OR paste content manually in the admin panel.")
else:
    st.info(f"💡 **I have access to {len(knowledge_base)} text documents** and can answer questions about them!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    f"Knowledge Base Chatbot • {len(knowledge_base)} documents loaded • OpenAI {'v1.x' if USE_NEW_OPENAI else 'v0.x'}"
    "</div>", 
    unsafe_allow_html=True
)
