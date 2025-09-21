import streamlit as st
import json
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload

class GoogleDriveAPI:
    def __init__(self):
        self.service = None
        self.folder_name = st.secrets.get("drive", {}).get("folder_name", "MAGnus Knowledge Base")
        self.setup_service()
    
    def setup_service(self):
        """Initialize Google Drive service with service account credentials"""
        try:
            # Get credentials from Streamlit secrets
            if "google_service_account" in st.secrets:
                # Method 1: Full JSON in secrets
                credentials_info = json.loads(st.secrets["google_service_account"])
            else:
                # Method 2: Individual fields in secrets
                credentials_info = {
                    "type": st.secrets["google"]["type"],
                    "project_id": st.secrets["google"]["project_id"],
                    "private_key_id": st.secrets["google"]["private_key_id"],
                    "private_key": st.secrets["google"]["private_key"],
                    "client_email": st.secrets["google"]["client_email"],
                    "client_id": st.secrets["google"]["client_id"],
                    "auth_uri": st.secrets["google"]["auth_uri"],
                    "token_uri": st.secrets["google"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["google"]["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": st.secrets["google"]["client_x509_cert_url"]
                }
            
            # Create credentials object
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            # Build the service
            self.service = build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            st.error(f"Error setting up Google Drive service: {str(e)}")
            self.service = None
    
    def test_connection(self):
        """Test if Google Drive connection is working"""
        if not self.service:
            return False, "Google Drive service not initialized"
        
        try:
            # Try to list files - this will fail if credentials are wrong
            about = self.service.about().get(fields="user").execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            return True, f"Connected as: {user_email}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def find_folder_by_name(self, folder_name):
        """Find folder ID by name"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                return folders[0]['id']
            else:
                return None
        except Exception as e:
            st.error(f"Error finding folder: {str(e)}")
            return None
    
    def list_all_files_recursively(self, folder_id):
        """Recursively list all files in a folder and its subfolders"""
        all_files = []
        
        try:
            # Get files and folders in current directory
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink, parents)",
                pageSize=1000
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # It's a folder - recursively get files from it
                    subfolder_files = self.list_all_files_recursively(item['id'])
                    # Add folder path to file names for clarity
                    for file_item in subfolder_files:
                        file_item['folder_path'] = f"{item['name']}/{file_item.get('folder_path', '')}"
                    all_files.extend(subfolder_files)
                else:
                    # It's a file - add it to our list
                    item['folder_path'] = ""  # Root level file
                    all_files.append(item)
            
            return all_files
            
        except Exception as e:
            st.error(f"Error listing files recursively: {str(e)}")
            return []
    
    def list_files_in_folder(self, folder_id):
        """List all files in a specific folder (now includes subfolders)"""
        return self.list_all_files_recursively(folder_id)
    
    def is_supported_file(self, file_name, mime_type):
        """Check if a file is supported based on name and MIME type"""
        # Define supported MIME types
        supported_mime_types = [
            'text/plain',
            'text/csv', 
            'text/markdown',
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.spreadsheet',
            'application/json',
            'application/x-jsonlines',  # Sometimes used for JSONL
            'text/x-json'  # Alternative JSON MIME type
        ]
        
        # Define supported file extensions
        supported_extensions = [
            '.txt', '.md', '.csv', '.pdf', '.docx', '.json', '.jsonl'
        ]
        
        # Check MIME type
        if mime_type in supported_mime_types:
            return True
            
        # Check file extension for files that might have generic MIME types
        file_lower = file_name.lower()
        for ext in supported_extensions:
            if file_lower.endswith(ext):
                return True
                
        return False
    
    def download_file_content(self, file_id, mime_type):
        """Download file content as bytes"""
        try:
            # Handle Google Docs, Sheets, Slides by exporting
            if mime_type == 'application/vnd.google-apps.document':
                # Export Google Doc as plain text
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                # Export Google Sheet as CSV
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/csv'
                )
            elif mime_type == 'application/vnd.google-apps.presentation':
                # Export Google Slides as plain text
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                # Download regular files
                request = self.service.files().get_media(fileId=file_id)
            
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return file_io.getvalue()
            
        except Exception as e:
            st.error(f"Error downloading file: {str(e)}")
            return None
    
    def process_file_content(self, content, file_name, mime_type):
        """Process file content based on file type"""
        if not content:
            return None
        
        try:
            # Check for JSONL files first (by extension)
            if file_name.lower().endswith('.jsonl'):
                return self.process_jsonl_content(content, file_name)
            
            # Then check by MIME type and other extensions
            if mime_type in ['application/json', 'application/x-jsonlines', 'text/x-json'] or file_name.lower().endswith('.json'):
                return self.process_jsonl_content(content, file_name)
            
            # Handle different file types
            if mime_type in ['text/plain', 'text/csv', 'text/markdown']:
                return content.decode('utf-8')
            
            elif mime_type == 'application/vnd.google-apps.document':
                # Google Doc exported as plain text
                return content.decode('utf-8')
            
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                # Google Sheet exported as CSV
                return content.decode('utf-8')
            
            elif mime_type == 'application/pdf':
                # Handle PDF files
                try:
                    import pypdf
                    pdf_file = io.BytesIO(content)
                    if hasattr(pypdf, 'PdfReader'):
                        pdf_reader = pypdf.PdfReader(pdf_file)
                    else:
                        pdf_reader = pypdf.PdfFileReader(pdf_file)
                    
                    text_content = ""
                    for page in pdf_reader.pages:
                        text_content += page.extract_text() + "\n"
                    
                    return text_content.strip()
                except ImportError:
                    return "Cannot process PDF files. Missing pypdf library."
                except Exception as e:
                    return f"Error processing PDF: {str(e)}"

            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                # Handle DOCX files
                try:
                    from docx import Document
                    docx_file = io.BytesIO(content)
                    doc = Document(docx_file)
                    
                    text_content = ""
                    for paragraph in doc.paragraphs:
                        text_content += paragraph.text + "\n"
                    
                    return text_content.strip()
                except ImportError:
                    return "Cannot process DOCX files. Missing python-docx library."
                except Exception as e:
                    return f"Error processing DOCX: {str(e)}"
            
            else:
                return f"Unsupported file type: {mime_type}"
                
        except Exception as e:
            return f"Error processing file {file_name}: {str(e)}"

    def process_jsonl_content(self, content, file_name):
        """Process JSONL content specifically"""
        try:
            text_accum = []
            content_str = content.decode('utf-8', errors='ignore')
            
            # Debug: Log the first few lines
            lines = content_str.splitlines()
            st.write(f"🔍 Processing JSONL file: {file_name}")
            st.write(f"📊 Total lines: {len(lines)}")
            
            processed_objects = 0
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    processed_objects += 1
                    
                    # Prefer KB fields; fall back to generic content
                    snippet = (obj.get('body_md') or 
                              obj.get('content') or 
                              obj.get('text') or 
                              obj.get('body') or
                              obj.get('description') or
                              '')
                    
                    if snippet:
                        text_accum.append(snippet)
                        
                except json.JSONDecodeError as e:
                    st.warning(f"⚠️ Line {line_num} in {file_name} is not valid JSON: {str(e)}")
                    # Try to use the line as plain text if it's not empty
                    if line.strip():
                        text_accum.append(line)
                except Exception as e:
                    st.warning(f"⚠️ Error processing line {line_num} in {file_name}: {str(e)}")
                    continue
            
            result = "\n\n".join(text_accum).strip() if text_accum else ""
            st.success(f"✅ Successfully processed {processed_objects} JSON objects from {file_name}")
            st.write(f"📝 Extracted {len(result)} characters of content")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing JSONL file {file_name}: {str(e)}"
            st.error(error_msg)
            return error_msg

class GoogleDriveConnector:
    def __init__(self):
        self.api = GoogleDriveAPI()
        self.folder_name = self.api.folder_name
    
    def test_connection(self):
        """Test Google Drive connection"""
        return self.api.test_connection()
    
    def get_documents(self):
        """Get documents from Google Drive folder - now includes subfolders"""
        if not self.api.service:
            return []
        
        try:
            # Find the knowledge base folder
            folder_id = self.api.find_folder_by_name(self.folder_name)
            if not folder_id:
                raise Exception(f"Folder '{self.folder_name}' not found or not shared with service account")
            
            # Get files in the folder (now includes subfolders)
            files = self.api.list_files_in_folder(folder_id)
            
            documents = []
            
            st.write(f"🔍 Found {len(files)} total files in Google Drive")
            
            for file_data in files:
                file_name = file_data['name']
                mime_type = file_data['mimeType']
                folder_path = file_data.get('folder_path', '')
                
                st.write(f"📄 Checking file: {file_name} (MIME: {mime_type})")
                
                # Use the new is_supported_file method
                if self.api.is_supported_file(file_name, mime_type):
                    st.write(f"✅ Processing supported file: {file_name}")
                    
                    # Download and process file content
                    content_bytes = self.api.download_file_content(file_data['id'], mime_type)
                    content_text = self.api.process_file_content(content_bytes, file_name, mime_type)
                    
                    if content_text and not content_text.startswith("Cannot process") and not content_text.startswith("Error"):
                        # Extract file extension for compatibility
                        if mime_type == 'application/vnd.google-apps.document':
                            file_extension = 'gdoc'
                        elif mime_type == 'application/vnd.google-apps.spreadsheet':
                            file_extension = 'gsheet'
                        elif file_name.lower().endswith('.jsonl'):
                            file_extension = 'jsonl'
                        else:
                            file_extension = file_name.split('.')[-1] if '.' in file_name else 'unknown'
                        
                        # Create display name with folder path if in subfolder
                        display_name = file_name
                        if folder_path:
                            display_name = f"{folder_path.rstrip('/')}/{file_name}"
                        
                        documents.append({
                            'name': display_name,  # Include folder path in name
                            'content': content_text,
                            'source': 'google_drive',
                            'modified': file_data.get('modifiedTime', ''),
                            'size': file_data.get('size', 0),
                            'path': file_data.get('webViewLink', ''),
                            'type': file_extension,
                            'mime_type': mime_type,
                            'folder_path': folder_path
                        })
                        
                        st.success(f"✅ Added document: {display_name}")
                    else:
                        st.warning(f"⚠️ Could not extract content from: {file_name}")
                else:
                    st.info(f"ℹ️ Skipping unsupported file: {file_name} (MIME: {mime_type})")
            
            st.success(f"🎉 Successfully loaded {len(documents)} documents")
            return documents
            
        except Exception as e:
            raise Exception(f"Error fetching Google Drive documents: {str(e)}")
