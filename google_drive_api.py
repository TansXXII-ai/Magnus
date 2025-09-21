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
    
    def list_files_in_folder(self, folder_id):
        """List all files in a specific folder"""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
                pageSize=100
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            st.error(f"Error listing files: {str(e)}")
            return []
    
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

class GoogleDriveConnector:
    def __init__(self):
        self.api = GoogleDriveAPI()
        self.folder_name = self.api.folder_name
    
    def test_connection(self):
        """Test Google Drive connection"""
        return self.api.test_connection()
    
    def get_documents(self):
        """Get documents from Google Drive folder - compatible with existing Dropbox format"""
        if not self.api.service:
            return []
        
        try:
            # Find the knowledge base folder
            folder_id = self.api.find_folder_by_name(self.folder_name)
            if not folder_id:
                raise Exception(f"Folder '{self.folder_name}' not found or not shared with service account")
            
            # Get files in the folder
            files = self.api.list_files_in_folder(folder_id)
            
            documents = []
            supported_types = [
                'text/plain',
                'text/csv', 
                'text/markdown',
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.google-apps.document',
                'application/vnd.google-apps.spreadsheet'
            ]
            
            for file_data in files:
                file_name = file_data['name']
                mime_type = file_data['mimeType']
                
                # Only process supported file types
                if mime_type in supported_types:
                    # Download and process file content
                    content_bytes = self.api.download_file_content(file_data['id'], mime_type)
                    content_text = self.api.process_file_content(content_bytes, file_name, mime_type)
                    
                    if content_text and not content_text.startswith("Cannot process") and not content_text.startswith("Error"):
                        # Extract file extension for compatibility
                        if mime_type == 'application/vnd.google-apps.document':
                            file_extension = 'gdoc'
                        elif mime_type == 'application/vnd.google-apps.spreadsheet':
                            file_extension = 'gsheet'
                        else:
                            file_extension = file_name.split('.')[-1] if '.' in file_name else 'unknown'
                        
                        documents.append({
                            'name': file_name,
                            'content': content_text,
                            'source': 'google_drive',
                            'modified': file_data.get('modifiedTime', ''),
                            'size': file_data.get('size', 0),
                            'path': file_data.get('webViewLink', ''),
                            'type': file_extension,
                            'mime_type': mime_type
                        })
            
            return documents
            
        except Exception as e:
            raise Exception(f"Error fetching Google Drive documents: {str(e)}")
