
import os
import json
import time
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="MAGnus - MA Group Knowledge Bot", page_icon="🤖", layout="wide")

try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except Exception:
    AZURE_OPENAI_AVAILABLE = False

try:
    from google_drive_api import GoogleDriveConnector
    GOOGLE_DRIVE_AVAILABLE = True
except Exception:
    GOOGLE_DRIVE_AVAILABLE = False

def get_secret(key: str, default=None):
    return os.getenv(key) or st.secrets.get(key, default)

@st.cache_resource
def get_google_drive_connector():
    if GOOGLE_DRIVE_AVAILABLE:
        try:
            return GoogleDriveConnector()
        except Exception:
            return None
    return None

@st.cache_data(ttl=1800)
def load_knowledge_base_incremental():
    """
    Load documents from Google Drive.
    Supports both:
      - get_documents_incremental(progress_callback=...)
      - get_documents()
    """
    documents = []
    if not GOOGLE_DRIVE_AVAILABLE:
        return documents, "Google Drive module not available."
    try:
        if "google" in st.secrets or "google_service_account" in st.secrets:
            google_connector = get_google_drive_connector()
            if not google_connector:
                return documents, "Failed to initialize Google Drive connector."

            # optional: file summary if implemented
            try:
                if hasattr(google_connector, "get_file_summary"):
                    _ = google_connector.get_file_summary()
            except Exception:
                pass

            # Prefer incremental if available
            if hasattr(google_connector, "get_documents_incremental"):
                current_files = []
                def progress_callback(processed, total, current):
                    current_files.clear()
                    current_files.extend(current or [])
                data = google_connector.get_documents_incremental(progress_callback=progress_callback)
            elif hasattr(google_connector, "get_documents"):
                data = google_connector.get_documents()
            else:
                return documents, "Connector has no get_documents(_incremental) method."

            # Normalize list/generator
            if data is None:
                data = []
            try:
                for d in data:
                    documents.append(d)
            except TypeError:
                # if a single object was returned
                documents.append(data)

            return documents, None
        else:
            return documents, "Google Drive credentials not configured."
    except Exception as e:
        return documents, f"Error fetching Google Drive documents: {str(e)}"

def call_openai_api(messages):
    if not AZURE_OPENAI_AVAILABLE:
        return None, "Azure OpenAI library not available"
    api_key = get_secret("AZURE_OPENAI_API_KEY")
    endpoint = get_secret("AZURE_OPENAI_ENDPOINT")
    deployment_name = get_secret("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")
    api_version = get_secret("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    if not api_key or not endpoint:
        return None, "Missing Azure OpenAI credentials"
    try:
        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        stream = client.chat.completions.create(
            model=deployment_name, messages=messages, stream=True, temperature=0.7, max_tokens=2000
        )
        return stream, None
    except Exception as e:
        return None, f"Azure OpenAI API error: {str(e)}"

# -------- state --------
for k, v in [
    ("authenticated", False),
    ("loading_complete", False),
    ("knowledge_base", []),
    ("messages", []),
    ("conversation_state", "initial"),
    ("current_category", None),
    ("last_loaded_at", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v

def logout():
    st.session_state.authenticated = False
    st.session_state.loading_complete = False
    st.session_state.knowledge_base = []
    st.session_state.messages = []
    st.session_state.conversation_state = "initial"
    st.session_state.current_category = None
    st.cache_data.clear()
    try:
        st.cache_resource.clear()
    except Exception:
        pass
    st.rerun()

def show_login():
    st.title("🔐 MAGnus Knowledge Bot - Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("🚀 Login & Connect", use_container_width=True)
    if login_button:
        if username == "MAG" and st.secrets.get("LOGIN_PASSWORD", "defaultpassword") == password:
            st.session_state.authenticated = True
            st.session_state.loading_complete = False
            st.rerun()
        else:
            st.error("Invalid username or password. Please try again.")

def show_loading():
    st.title("🤖 MAGnus Knowledge Bot")
    st.markdown("### 📚 Loading Knowledge Base")
    prog = st.progress(0)
    status = st.empty()
    status.text("Connecting to Google Drive...")
    prog.progress(20)
    documents, err = load_knowledge_base_incremental()
    if err:
        st.error(f"❌ Error loading documents: {err}")
        colA, colB = st.columns(2)
        with colA:
            if st.button("🔄 Retry"):
                st.rerun()
        with colB:
            if st.button("🚪 Logout"):
                logout()
        return
    st.session_state.knowledge_base = documents
    st.session_state.last_loaded_at = datetime.now().isoformat()
    status.text(f"✅ Loaded {len(documents)} documents")
    prog.progress(100)
    st.session_state.loading_complete = True
    time.sleep(0.6)
    st.rerun()

def show_main_app():
    st.title("🤖 MAGnus - MA Group Knowledge Bot")
    if st.button("🚪 Logout"):
        logout()

    st.sidebar.header("📚 Knowledge Base")
    kb = st.session_state.knowledge_base
    st.sidebar.write(f"Loaded documents: {len(kb)}")

    # Initial welcome message
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
    user_input = st.chat_input("Type here...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        state = st.session_state.conversation_state
        if state == "initial":
            with st.chat_message("assistant"):
                st.markdown(st.session_state.messages[0]["content"])
                st.session_state.conversation_state = "categorizing"

        elif state == "categorizing":
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

        elif state in ["waiting_for_issue", "waiting_for_problem", "categorized"]:
            if not AZURE_OPENAI_AVAILABLE:
                with st.chat_message("assistant"):
                    st.error("AI service is not available.")
            else:
                # Build compact context (RAG-lite)
                kb = st.session_state.knowledge_base
                knowledge_context = ""
                if kb:
                    q = user_input.lower()
                    filtered = [d for d in kb if any(
                        kw in (d.get('content') or '').lower() for kw in q.split() if len(kw) > 3
                    )]
                    cands = filtered if filtered else kb
                    cands = sorted(cands, key=lambda x: x.get('priority', 3))
                    ctx, remaining = [], 20000
                    for doc in cands[:10]:
                        snippet = (doc.get('content') or "")[:2000]
                        if not snippet:
                            continue
                        if remaining - len(snippet) <= 0:
                            break
                        ctx.append(f"Document: {doc.get('name','Unknown')} (Priority: {doc.get('priority','Unknown')})\n{snippet}")
                        remaining -= len(snippet)
                    knowledge_context = "\n\n".join(ctx)

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

                with st.chat_message("assistant"):
                    with st.spinner("🤔 Searching through company documents..."):
                        placeholder = st.empty()
                        full = ""
                        stream, err = call_openai_api(messages_for_api)
                    if err:
                        st.error(f"AI Error: {err}")
                        placeholder.markdown(f"AI Error: {err}")
                    elif stream:
                        try:
                            for chunk in stream:
                                if not hasattr(chunk, "choices") or not chunk.choices:
                                    continue
                                delta_obj = getattr(chunk.choices[0], "delta", None)
                                if not delta_obj:
                                    continue
                                delta = getattr(delta_obj, "content", None)
                                if delta:
                                    full += delta
                                    placeholder.markdown(full + "▌")
                            placeholder.markdown(full)
                            st.session_state.messages.append({"role": "assistant", "content": full})
                        except Exception as e:
                            st.error(f"Streaming Error: {e}")
                            placeholder.markdown(f"Streaming Error: {e}")

    st.markdown("---")
    st.caption(f"MAGnus Knowledge Bot • Docs: {len(kb)} • Last loaded: {st.session_state.last_loaded_at or 'Unknown'}")

if not st.session_state.authenticated:
    show_login()
elif not st.session_state.loading_complete:
    show_loading()
else:
    show_main_app()
