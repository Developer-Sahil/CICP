import firebase_admin
from firebase_admin import credentials, firestore
import os

def init_firestore():
    """
    Initialize Firebase Admin SDK exactly once.
    Uses Application Default Credentials (ADC).
    """

    if not firebase_admin._apps:
        # ADC will be used automatically
        firebase_admin.initialize_app()

    return firestore.client()
