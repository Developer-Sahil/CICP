// COPY FROM FIREBASE CONSOLE → WEB APP SETTINGS
const firebaseConfig = {
  apiKey: "{{ config.FIREBASE_API_KEY }}",
  authDomain: "{{ config.FIREBASE_AUTH_DOMAIN }}",
  projectId: "{{ config.FIREBASE_PROJECT_ID }}"
};
firebase.initializeApp(firebaseConfig);
