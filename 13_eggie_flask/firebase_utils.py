import firebase_admin
from firebase_admin import credentials, firestore

# 초기화된 앱을 재사용하도록 설정
firebase_app = None
db = None

def init_firestore():
    global firebase_app, db
    if not firebase_admin._apps:  # 이미 초기화되어 있지 않으면
        cred = credentials.Certificate("serviceAccountKey_test.json")
        firebase_app = firebase_admin.initialize_app(cred)
        db = firestore.client()
    return db