# InCollege – Student Networking & Job Search Platform

A student-focused networking and job search application built as part of the EPICS program. The project consists of two components:  

1. **Backend + CLI (Fall 2023 EPICS)** – Python-based server with SQLite, JWT authentication, and CLI interactions.  
2. **Web App (Agile/Scrum Team, Nov 2023)** – React.js frontend with MongoDB backend, supporting job search and student networking features.  

---

## ⚠️ Warning
This project is not compatible with native Windows environments and has not been tested on macOS. To run locally, please use either a Linux environment or the Windows Subsystem for Linux (WSL).

---

## 🚀 Features
- User authentication with JWT  
- Student networking (connections, requests, profile management)  
- Job search functionality  
- CLI interface for backend testing  
- React.js web frontend with MongoDB backend (Agile/Scrum project)  
- 200+ test cases for reliability and sprint deliverables aligned with client requirements  

---

## 🖥️ Launching the Backend (EPICS CLI Component)

Follow these steps if you want to run a development backend server on your local machine:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   
2. Create a secret key:
     echo "yoursecretkey" > jwt-key.txt
   
3. Create the SQLite database:

    python3 models.py users.db


4. Launch the backend server:

    gunicorn --bind 0.0.0.0:8000 server:app


5. Run the CLI frontend:

    python3 main.py http://localhost:8000
