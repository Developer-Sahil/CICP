# 🔧 Firebase Troubleshooting Guide

## Error: "The default Firebase app does not exist"

**Full Error:**
```
ValueError: The default Firebase app does not exist. Make sure to initialize 
the SDK by calling initialize_app().
```

**Cause:** Firebase Admin SDK needs to be initialized before using Firestore.

**Solution:** The updated `firebase_models.py` now includes Firebase initialization. Make sure you're using the latest version.

---

## Common Issues & Solutions

### 1. Firebase Credentials Not Found

**Error:**
```
Failed to initialize Firebase: ...
KeyError: 'FIREBASE_PROJECT_ID'
```

**Solution:**
1. Check your `.env` file exists in project root
2. Verify all Firebase variables are present:
   ```env
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_PRIVATE_KEY_ID=...
   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   FIREBASE_CLIENT_EMAIL=...
   FIREBASE_CLIENT_ID=...
   FIREBASE_CLIENT_CERT_URL=...
   ```

3. Restart your app after updating `.env`

### 2. Invalid Private Key Format

**Error:**
```
ValueError: Could not deserialize key data
```

**Solution:**
Make sure `FIREBASE_PRIVATE_KEY` in `.env` has `\n` for line breaks:

```env
# WRONG:
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY----- MIIEvQIBADANBg... -----END PRIVATE KEY-----"

# CORRECT:
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg...\n-----END PRIVATE KEY-----\n"
```

**OR** use the service account JSON file:
1. Download from Firebase Console → Project Settings → Service Accounts
2. Save as `firebase_service_account.json` in project root
3. The code will automatically use it

### 3. Permission Denied in Firestore

**Error:**
```
PermissionDenied: Missing or insufficient permissions
```

**Solution:**
1. Go to Firebase Console → Firestore Database → Rules
2. Update rules to allow authenticated access:
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```
3. Click "Publish"

### 4. Module Not Found Errors

**Error:**
```
ModuleNotFoundError: No module named 'firebase_admin'
```

**Solution:**
```bash
pip install firebase-admin google-cloud-firestore python-dotenv
```

Or install all requirements:
```bash
pip install -r requirements.txt
```

### 5. Double Initialization Error

**Error:**
```
ValueError: The default Firebase app already exists.
```

**Solution:**
This happens if Firebase is initialized twice. The updated code handles this:
- `firebase_models.py` initializes Firebase once
- `firebase_auth.py` reuses the existing initialization

If you still see this, check for any other files calling `firebase_admin.initialize_app()`.

### 6. Firestore Connection Timeout

**Error:**
```
TimeoutError: Deadline exceeded
```

**Solution:**
1. Check your internet connection
2. Verify Firebase project ID is correct
3. Make sure Firestore is enabled in Firebase Console
4. Try increasing timeout (if needed):
   ```python
   db = firestore.client()
   # Add timeout parameter if needed
   ```

### 7. Data Not Appearing in Firestore

**Symptoms:**
- App runs without errors
- Data doesn't show in Firebase Console

**Solution:**
1. Check Firebase Console → Firestore Database
2. Look for collections: `users`, `complaints`, `categories`
3. If empty, check Flask logs for errors
4. Verify write permissions in Firestore rules
5. Test with a simple write:
   ```python
   from database.firebase_models import Category
   Category.create('Test Category')
   ```

### 8. Categories Not Initializing

**Symptoms:**
```
Categories: 0
```

**Solution:**
Manually initialize categories:
```bash
python -c "from database.firebase_models import initialize_categories; initialize_categories()"
```

Or in Python:
```python
from database.firebase_models import initialize_categories
initialize_categories()
```

### 9. User Login Issues

**Error:**
```
User not found after Google login
```

**Solution:**
1. Check `auth/firebase_auth.py` is updated
2. Verify it imports from `firebase_models`:
   ```python
   from database.firebase_models import User
   ```
3. Check Firebase Console → Authentication
4. Verify Google Sign-In is enabled

### 10. Environment Variables Not Loading

**Symptoms:**
- `.env` file exists but values are None
- Credentials not found errors

**Solution:**
1. Install python-dotenv:
   ```bash
   pip install python-dotenv
   ```

2. Make sure `.env` is in project root (same directory as `app.py`)

3. Check file format (no spaces around `=`):
   ```env
   # WRONG:
   FIREBASE_PROJECT_ID = my-project
   
   # CORRECT:
   FIREBASE_PROJECT_ID=my-project
   ```

4. No quotes needed unless value has spaces:
   ```env
   # Simple value:
   FIREBASE_PROJECT_ID=my-project-123
   
   # Value with spaces:
   SECRET_KEY="my secret key with spaces"
   ```

---

## Quick Diagnostics

### Test 1: Check Environment Variables
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Project ID:', os.getenv('FIREBASE_PROJECT_ID'))"
```

Should output your project ID, not `None`.

### Test 2: Test Firebase Connection
```bash
python -c "from database.firebase_models import db; print('✅ Firebase connected!')"
```

Should print success message without errors.

### Test 3: Test Category Creation
```bash
python -c "from database.firebase_models import Category; print('Categories:', Category.count())"
```

Should show number of categories (7 after initialization).

### Test 4: Full Health Check
```bash
curl http://localhost:5000/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "connected",
  "categories": 7
}
```

---

## Debugging Tips

### Enable Debug Logging
Add to your `app.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Firebase Console
1. Go to https://console.firebase.google.com
2. Select your project
3. Check:
   - **Firestore Database** - See your data
   - **Authentication** - See logged-in users
   - **Usage** - Check quotas

### Check Flask Logs
Look for these messages:
```
Firebase initialized from environment variables
Categories initialized successfully
* Running on http://0.0.0.0:5000
```

### Verify File Structure
```
CICP/
├── .env                          ← Environment variables
├── firebase_service_account.json ← Optional
├── app.py                        ← Main app
├── database/
│   └── firebase_models.py        ← Firebase models
├── auth/
│   └── firebase_auth.py          ← Google login
└── utils/
    └── firebase_helpers.py       ← Helper functions
```

---

## Still Having Issues?

### 1. Check Firebase Status
Visit: https://status.firebase.google.com/

### 2. Verify Project Settings
- Firebase Console → Project Settings
- Make sure project is active
- Check billing (if applicable)

### 3. Test with Minimal Code
Create `test_firebase.py`:
```python
from dotenv import load_dotenv
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize
service_account = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
}

cred = credentials.Certificate(service_account)
firebase_admin.initialize_app(cred)

# Test connection
db = firestore.client()
print("✅ Firebase connected!")

# Test write
doc_ref = db.collection('test').document()
doc_ref.set({'message': 'Hello Firebase!'})
print("✅ Write successful!")

# Test read
docs = db.collection('test').limit(1).get()
print(f"✅ Read successful! Found {len(list(docs))} documents")
```

Run:
```bash
python test_firebase.py
```

### 4. Common Solutions Checklist

- [ ] Installed all requirements
- [ ] `.env` file in project root
- [ ] All Firebase variables in `.env`
- [ ] Private key has `\n` for newlines
- [ ] Firestore enabled in console
- [ ] Authentication enabled
- [ ] Rules allow authenticated access
- [ ] Using updated `firebase_models.py`
- [ ] Using updated `firebase_auth.py`
- [ ] No double initialization

---

## Getting Help

If none of the above solutions work:

1. **Check error logs carefully**
   - Read the full error message
   - Note the exact line causing the error

2. **Verify credentials**
   - Double-check project ID matches Firebase Console
   - Regenerate service account key if needed

3. **Test incrementally**
   - Start with minimal code
   - Add features one at a time

4. **Check Firebase documentation**
   - https://firebase.google.com/docs/firestore
   - https://firebase.google.com/docs/admin/setup

---

## Success Indicators ✅

You know everything is working when:

- ✅ App starts without errors
- ✅ `Firebase initialized` in logs
- ✅ `Categories initialized successfully` in logs
- ✅ Can access http://localhost:5000
- ✅ Health check returns "healthy"
- ✅ Can see data in Firebase Console
- ✅ Can register and login
- ✅ Can submit complaints

If you see all of these, you're good to go! 🚀