import os
import streamlit as st
from sqlalchemy import create_engine, Column, String, Integer, text
from sqlalchemy.orm import sessionmaker, declarative_base
import pdfplumber
from docx import Document
from cryptography.fernet import Fernet

# Create the uploads directory if it doesn't exist
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Database setup
DATABASE_URL = "sqlite:///documents.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# Encryption setup
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Models
class DocumentModel(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    content = Column(String)

class UserHistory(Base):
    __tablename__ = "user_history"
    id = Column(Integer, primary_key=True)
    user = Column(String)
    query = Column(String)
    response = Column(String)

Base.metadata.create_all(engine)

# Functions to read different document formats
def read_pdf(file_path):
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Error reading PDF file: {e}")
        return ""

def read_docx(file_path):
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text
        return text
    except Exception as e:
        st.error(f"Error reading DOCX file: {e}")
        return ""

def read_txt(file_path):
    try:
        with open(file_path, "r") as file:
            return file.read()
    except Exception as e:
        st.error(f"Error reading TXT file: {e}")
        return ""

# Function to encrypt content
def encrypt_content(content):
    try:
        return cipher_suite.encrypt(content.encode()).decode()
    except Exception as e:
        st.error(f"Error encrypting content: {e}")
        return ""

# Function to decrypt content
def decrypt_content(encrypted_content):
    try:
        return cipher_suite.decrypt(encrypted_content.encode()).decode()
    except Exception:
        return ""  # Return an empty string in case of an error

# Function to save uploaded files
def save_uploadedfile(uploadedfile):
    try:
        file_path = os.path.join("uploads", uploadedfile.name)
        with open(file_path, "wb") as f:
            f.write(uploadedfile.getbuffer())
        st.success(f"Saved file: {uploadedfile.name} in uploads folder")
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return ""

# Function to save user history
def save_user_history(user, query, response):
    try:
        history = UserHistory(user=user, query=query, response=response)
        session.add(history)
        session.commit()
    except Exception as e:
        st.error(f"Error saving user history: {e}")

# Function to get user history
def get_user_history(user):
    try:
        return session.query(UserHistory).filter_by(user=user).all()
    except Exception as e:
        st.error(f"Error retrieving user history: {e}")
        return []

# Function to save history to file
def save_history_to_file(user):
    try:
        history = get_user_history(user)
        file_path = f"{user}_history.txt"
        with open(file_path, "w", encoding="utf-8") as file:
            for record in history:
                file.write(f"Query: {record.query}\nResponse: {record.response}\n\n")
        return file_path
    except Exception as e:
        st.error(f"Error saving history to file: {e}")
        return ""

# Function to search documents
def search_documents(query):
    try:
        search_results = []
        with engine.connect() as conn:
            result = conn.execute(text("SELECT filename, content FROM documents")).fetchall()
            for row in result:
                file_path = os.path.join("uploads", row[0])
                decrypted_content = decrypt_content(row[1])
                if decrypted_content and query.lower() in decrypted_content.lower():
                    search_results.append((row[0], decrypted_content))
        return search_results
    except Exception as e:
        st.error(f"Error executing search query: {e}")
        return []

# Streamlit UI
st.set_page_config(page_title="Document Query Application", layout="wide")

st.markdown(
    """
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton button {
        background-color: #4caf50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stTextInput > div > input {
        border-radius: 4px;
        padding: 10px;
        font-size: 16px;
        border: 1px solid #d1d5db;
    }
    .stFileUploader > div > div {
        border-radius: 4px;
        padding: 10px;
        font-size: 16px;
        border: 1px solid #d1d5db;
        background-color: white;
    }
    .stDownloadButton > div > div > div > div > button {
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stMarkdown h1 {
        color: #333;
    }
    .stExpander {
        border-radius: 4px;
        border: 1px solid #d1d5db;
        padding: 10px;
        background-color: #f8f9fa;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📄 Document Query Application")
st.write("Upload your documents and perform secure, encrypted searches.")

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    file_path = save_uploadedfile(uploaded_file)
    if file_path:
        content = ""
        if uploaded_file.name.endswith(".pdf"):
            content = read_pdf(file_path)
        elif uploaded_file.name.endswith(".docx"):
            content = read_docx(file_path)
        else:
            content = read_txt(file_path)
        
        if content:
            encrypted_content = encrypt_content(content)
            document = DocumentModel(filename=uploaded_file.name, content=encrypted_content)
            try:
                session.add(document)
                session.commit()
                st.success(f"Document {uploaded_file.name} successfully saved to the database.")
            except Exception as e:
                st.error(f"Error saving document to database: {e}")

query = st.text_input("Enter your query:")
search_results = []

if st.button("Search"):
    search_results = search_documents(query)
    
    if search_results:
        st.write("### Found in the following documents:")
        for filename, text in search_results:
            with st.expander(f"Document: {filename}"):
                st.write(text[:500])  # Display first 500 characters
            save_user_history("test_user", query, text[:500])
    else:
        st.write("No results found.")

if st.button("Download chat history"):
    file_path = save_history_to_file("test_user")
    if file_path:
        with open(file_path, "rb") as file:
            st.download_button(
                label="Download chat history",
                data=file,
                file_name="test_user_history.txt",
                mime="text/plain"
            )
