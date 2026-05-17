"""db/firebase.py — Firebase Admin SDK initialization."""

import os
import sys
import json
import uuid

import firebase_admin
from firebase_admin import credentials, firestore, storage
from werkzeug.utils import secure_filename

import config


def init_firebase():
    if firebase_admin._apps:
        return
    firebase_env = os.environ.get("FIREBASE_CREDENTIALS")
    if firebase_env:
        try:
            cred_dict = json.loads(firebase_env)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                "storageBucket": config.FIREBASE_STORAGE_BUCKET,
            })
            return
        except Exception:
            pass

    # 2. Try local service-account key file (development)
    key_path = os.path.join(os.path.dirname(__file__), "..", "firebase-key.json")
    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {
            "storageBucket": config.FIREBASE_STORAGE_BUCKET,
        })
        return

    # 3. Fallback to default application credentials
    firebase_admin.initialize_app(options={
        "storageBucket": config.FIREBASE_STORAGE_BUCKET,
    })


def get_db():
    """Return the Firestore client, initializing Firebase if needed."""
    init_firebase()
    return firestore.client()


def get_bucket():
    """Return the Firebase Storage bucket."""
    init_firebase()
    return storage.bucket()


def upload_file_to_firebase(file, folder):
    """Upload a file to Firebase Storage with local fallback."""
    if not file or file.filename == "":
        return None
    
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    path = f"{folder}/{unique_name}"

    try:
        bucket = get_bucket()
        blob = bucket.blob(path)
        blob.upload_from_file(file.stream, content_type=file.content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"Firebase Storage failed ({e}), using local fallback...")
        # Fallback to local storage
        local_dir = os.path.join(os.path.dirname(__file__), "..", "static", "uploads", folder)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, unique_name)
        
        # Reset file stream position
        file.stream.seek(0)
        file.save(local_path)
        
        return f"/static/uploads/{folder}/{unique_name}"
