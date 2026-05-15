"""
db/firebase.py — Firebase Admin SDK initialization
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

# Initialize Firebase
def init_firebase():
    if not firebase_admin._apps:
        # Look for key in root directory
        key_path = os.path.join(os.path.dirname(__file__), "..", "firebase-key.json")
        
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': config.FIREBASE_STORAGE_BUCKET
            })
            print("[OK] Firebase Initialized with service account.")
        else:
            # Fallback for local testing if key is missing (this will fail on actual Firestore calls)
            print("[WARN] firebase-key.json not found in root. Firebase will fail.")
            # Initialize with default credentials if available
            try:
                firebase_admin.initialize_app()
                print("[OK] Firebase Initialized with default credentials.")
            except:
                print("[FAIL] Firebase initialization failed. Please add firebase-key.json")

def get_db():
    init_firebase()
    return firestore.client()

def get_bucket():
    init_firebase()
    return storage.bucket()
