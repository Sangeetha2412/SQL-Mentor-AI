# SQL Mentor AI 🤖

> AI-Powered SQL Learning, Query Generation, File Analysis & Visualization Platform

## Features

- 🤖 **RAG Chatbot** — Ask anything about SQL using Groq LLaMA 3.3 70B
- 📁 **Multi-Format File Analysis** — CSV, Excel, JSON, PDF, TXT, SQL, SQLite
- 🗄️ **Database Explorer** — Browse SQLite schemas, run safe SELECT queries
- 📊 **Chart Builder** — Bar, Line, Pie, Doughnut, Scatter, Area charts
- 🔍 **Data Explorer** — Paginated, searchable, sortable table viewer
- 🔐 **Auth** — Email/password + Google OAuth
- 🛡️ **Admin Panel** — Users, files, chats, API key management, analytics

---

## Windows PowerShell Setup

### 1. Create and open project folder
```powershell
mkdir sql-mentor-ai
cd sql-mentor-ai
code .
```

### 2. Create virtual environment
```powershell
python -m venv venv
```

### 3. Activate virtual environment
```powershell
.\venv\Scripts\Activate.ps1
# If you get a policy error, run first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install requirements
```powershell
pip install -r requirements.txt
```

### 5. Create .env file
```powershell
Copy-Item .env.example .env
```

### 6. Generate SETTINGS_ENCRYPTION_KEY
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output and paste into .env as SETTINGS_ENCRYPTION_KEY=<output>
```

### 7. Generate SECRET_KEY
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
# Copy and paste into .env as SECRET_KEY=<output>
```

### 8. Edit your .env file
Open `.env` and fill in:
```
SECRET_KEY=<generated above>
GROQ_API_KEY=your-groq-api-key
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=YourSecurePassword123!
SETTINGS_ENCRYPTION_KEY=<generated above>
```

### 9. Run document ingestion (one-time)
```powershell
python ingest_docs.py
```

### 10. Run the application
```powershell
python app.py
```

### 11. Open in browser
```
http://localhost:5000
```

---

## Getting Your Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up / log in
3. Click **API Keys** in the left sidebar
4. Click **Create API Key**
5. Copy the key (starts with `gsk_`)
6. Paste into `.env` as `GROQ_API_KEY=gsk_...`

---

## Google OAuth Setup (Optional)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project or select existing
3. Go to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client IDs**
5. Application type: **Web application**
6. Add Authorized redirect URI: `http://localhost:5000/auth/google/callback`
7. Copy **Client ID** and **Client Secret**
8. Add to `.env`:
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
```

---

## Admin Panel Setup

The admin user is created automatically on first startup using `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `.env`.

Access admin panel at: `http://localhost:5000/admin/dashboard`

### Update Groq API Key from Admin UI
1. Log in as admin
2. Go to Admin → API Settings
3. Enter new Groq API key
4. Click **Test Key** to verify
5. Click **Save API Key**

---

## Adding SQL Knowledge Documents

Place `.md`, `.txt`, or `.sql` files in `data/sql_docs/`:
```powershell
# Example
Copy-Item my_sql_notes.md data/sql_docs/
python ingest_docs.py  # Re-run to ingest new docs
```

---

## Using the Application

### Upload & Analyze Files
1. Go to **Upload Files**
2. Drag & drop or click to upload
3. Supported: CSV, Excel, JSON, PDF, TXT, Markdown, SQL, SQLite (.db)
4. Click **Explore** to browse data in table format
5. Click **Chart** to create visualizations

### AI Chat
1. Go to **AI Chat**
2. Click the paperclip icon to attach uploaded files
3. Ask questions like:
   - "Explain INNER JOIN with examples"
   - "Analyze the uploaded CSV and show missing values"
   - "Write a query to find top 10 customers by revenue"
   - "What tables exist in this database?"

### Data Explorer
- Browse uploaded tabular data (CSV, Excel, JSON)
- Search, sort, filter columns
- For SQLite files: view schema, run safe SELECT queries
- Download filtered data as CSV

### Visualizations
- Select X and Y axis columns
- Choose chart type (Bar, Line, Pie, etc.)
- Select aggregation (Count, Sum, Average)
- Click Generate Chart
- Save or download as PNG

---

## Deployment (Render / Railway)

### Render
1. Push code to GitHub
2. Create new Web Service on Render
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Add all environment variables in Render dashboard
6. Set `SESSION_COOKIE_SECURE=True` for HTTPS

### Environment Variables for Production
```
SECRET_KEY=<strong-random-key>
DATABASE_URL=sqlite:///instance/sql_mentor.db
GROQ_API_KEY=<your-key>
SETTINGS_ENCRYPTION_KEY=<fernet-key>
ADMIN_EMAIL=<your-admin-email>
ADMIN_PASSWORD=<strong-password>
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback
```

---

## Project Structure

```
sql-mentor-ai/
├── app.py                  # Main Flask app & routes
├── config.py               # Configuration & env vars
├── database.py             # SQLAlchemy instance
├── models.py               # Database models
├── auth.py                 # Auth blueprint (login, signup, Google OAuth)
├── admin.py                # Admin blueprint
├── rag_pipeline.py         # RAG + Groq AI response generation
├── file_processor.py       # File parsing & metadata extraction
├── sql_executor.py         # Safe SQL query execution
├── chart_generator.py      # Chart.js config generation
├── data_analyzer.py        # Pagination & data analysis
├── encryption_utils.py     # Fernet API key encryption
├── ingest_docs.py          # Run once: ingest SQL docs into ChromaDB
├── requirements.txt
├── .env.example
├── data/sql_docs/          # SQL knowledge base documents
├── uploads/                # User uploaded files (auto-created)
├── chroma_db/              # ChromaDB vector store (auto-created)
├── static/css/             # Stylesheets
├── static/js/              # JavaScript files
└── templates/              # Jinja2 HTML templates
```

---

## Security Notes

- All passwords hashed with Werkzeug PBKDF2
- API keys encrypted with Fernet before database storage
- Per-user ChromaDB collections (data isolation)
- Only SELECT/WITH queries allowed on uploaded SQLite files
- CSRF protection via Flask-WTF
- File extension allowlist
- Secure filenames with Werkzeug
