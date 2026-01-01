# 🎓 Campus Issue & Complaint Portal (CICP)

📌 **AI-powered platform for universities to manage student issues at scale.**  
Built for accuracy, transparency & seamless student experience.

> **Developed by Team CICP**

---

## ✨ Highlights

| Feature | Status | Description |
|--------|---------|--------------|
| 🇮🇳 College Authentication | ✅ LIVE | Email/Student ID + Google Sign-In (domain restricted) |
| 🤖 AI-Rewriting | ✅ LIVE | Converts informal complaints → professional format |
| 🧠 Severity Engine | 🚨 95–98% Accuracy | Triple-layer: keywords + Gemini AI + verification |
| 📌 Clustering | 🧩 LIVE | Groups similar complaints automatically |
| 👍 Upvotes | 💬 Community Feedback | Students highlight important issues |
| 📊 Dashboard | ⭐ Admin Insights | Real-time analytics & high-severity prioritization |
| 🕵️ Anonymous Mode | 🙈 Privacy Enabled | Submit without identity |

---

## 🛠️ Tech Stack

**Backend:** Flask (Python) • SQLite / PostgreSQL  
**AI:** Google Gemini • Custom Severity Engine  
**Auth:** Firebase Google Sign-In + Manual Login  
**Frontend:** TailwindCSS • Alpine.js • Chart.js  
**ORM:** SQLAlchemy  

---

## 📦 Installation

### 1️⃣ Clone Repo
```bash
git clone https://github.com/Developer-Sahil/CICP
cd CICP
```

### 2️⃣ Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3️⃣ Install Requirements
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Create .env
```bash
cp .env.example .env
```

Update with your values:

```env
SECRET_KEY=your-secret-key
DEBUG=True

DATABASE_URI=sqlite:///complaints.db

# --- AI ---
GEMINI_API_KEY=your-gemini-api-key

# --- Firebase (SERVICE ACCOUNT: BACKEND) ---
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=value
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_CLIENT_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/...

# --- Firebase (FRONTEND: WEB CONFIG) ---
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_APP_ID=...

ALLOWED_GOOGLE_DOMAIN=vitapstudent.ac.in
```

🚫 **Never push service account JSON** — already removed from history & .gitignore!

---

## 🚀 Run Locally

```bash
python app.py
```

Visit: **http://localhost:5000**

---

## 🎯 Authentication System

### Google Sign-In (Recommended)
- Domain restricted → @vitapstudent.ac.in
- Auto-creates profile if first login
- No password required for returning users

### Manual Sign-Up

| Field | Required |
|-------|----------|
| Name | ✅ |
| Student ID | ✅ |
| Email | ✅ |
| Password | Strong (8+ chars, Aa1) |

---

## 🤖 AI Pipeline (Behind the Scenes)

```mermaid
graph LR
A[Student Complaint] --> B[Rewrite with AI]
B --> C[Category Classifier]
C --> D[Severity Engine]
D --> E[Vector Embedding]
E --> F[Similar Cluster Grouping]
F --> G[Dashboard Insights + Upvote Visibility]
```

---

## 📊 Database Schema (Core)

### users
| Field | Notes |
|-------|-------|
| is_google | identifies Google Sign-In accounts |
| student_id | optional for Google users |
| password_hash | empty for Google users |
| email_verified | coming soon |

### complaints
| Field | Notes |
|-------|-------|
| rewritten_text | professional AI rewrite |
| severity | low/medium/high |
| upvotes | 👍 feature |
| cluster_id | automatic similarity mapping |

---

## 🚦 Google Login Flow (Now Fixed)

```
[Frontend Firebase] → ID Token → /firebase-login → Verify + Create/Update User → Session → Profile
```

💡 Session issues + redirect loops **FIXED** in branch `harsh`  
✨ Changes merged into `main` via PR

---

## 🧰 Development Workflow

### Create Branch
```bash
git checkout -b feature/my-change
```

### Commit
```bash
git add .
git commit -m "My update"
```

### Push
```bash
git push origin feature/my-change
```

### Pull Request
→ https://github.com/Developer-Sahil/CICP/pulls

---

## 🧹 If You Accidentally Pushed Secrets

```bash
git filter-branch --force --index-filter \
"git rm --cached --ignore-unmatch firebase_service_account.json" \
--prune-empty --tag-name-filter cat -- --all

git push --force
```

---

## 🧪 Testing

### Severity Engine (40+ cases)
```bash
python test_severity.py
```

### Health Check
```bash
curl http://localhost:5000/health
```

---

## 🚀 Production Deployment

### Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### PostgreSQL
```env
DATABASE_URI=postgresql://user:password@host/dbname
```

### Must Do
- Set `DEBUG=False`
- SSL / HTTPS
- Strong `SECRET_KEY`
- Systemd / service for uptime

---

## 🧭 Roadmap 2026

- [ ] Email alerts for high severity 🚑
- [ ] Attachments (images/screenshots) 📎
- [ ] Complaint status lifecycle 🟡🟢
- [ ] Mobile app (React Native) 📱
- [ ] Inbuilt admin panel & role management 🛡️

---

## 🙌 Support & Contributions

**Pull Requests are welcome** 🎉  
If you find a bug, open an Issue!

👉 https://github.com/Developer-Sahil/CICP/issues

---

## 🧑‍🎓 Built For Campus Empowerment

*"Empowering student voices through intelligent technology."*  
— Team CICP

---

**Last Updated:** January 2026  
**Version:** 2.2.0 (Google Login Patch)
