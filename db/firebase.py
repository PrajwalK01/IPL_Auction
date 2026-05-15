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
        # 1. Try environment variable (for Vercel/Production)
        import json
        firebase_env = os.environ.get("FIREBASE_CREDENTIALS")
        
        if firebase_env:
            try:
                cred_dict = json.loads(firebase_env)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': config.FIREBASE_STORAGE_BUCKET
                })
                print("[OK] Firebase Initialized via Environment Variable.")
                return
            except Exception as e:
                print(f"[FAIL] Failed to init Firebase via env: {e}")

        # 2. Try local file (for Local Development)
        key_path = os.path.join(os.path.dirname(__file__), "..", "firebase-key.json")
        
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': config.FIREBASE_STORAGE_BUCKET
            })
            print("[OK] Firebase Initialized with local service account.")
        else:
            print("[FAIL] No Firebase credentials found. Set FIREBASE_CREDENTIALS env or add firebase-key.json")

def get_db():
    init_firebase()
    return firestore.client()

def get_bucket():
    init_firebase()
    return storage.bucket()
