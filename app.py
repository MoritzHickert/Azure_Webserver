import os
from flask import Flask, request, session, redirect, url_for
import pymysql
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

# --- Konfiguration aus Umgebungsvariablen ---
DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')
APP_SECRET_KEY = os.environ.get('APP_SECRET_KEY', 'default-secret-key-change-me') # Fallback-Wert

# Azure-spezifische Variablen
STORAGE_ACCOUNT_NAME = os.environ.get('STORAGE_ACCOUNT_NAME')
CONTAINER_NAME = os.environ.get('S3_BUCKET')  # Wir verwenden den alten Variablennamen weiter
BLOB_ACCOUNT_URL = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"

app = Flask(__name__)
app.secret_key = APP_SECRET_KEY

# --- Authentifizierung ---
azure_credential = DefaultAzureCredential()


# --- Datenbankverbindung ---
def get_db_connection():
    return pymysql.connect(host=DB_HOST,
                           user=DB_USER,
                           password=DB_PASSWORD,
                           database=DB_NAME,
                           cursorclass=pymysql.cursors.DictCursor)


# --- Routen der Anwendung ---
@app.route('/')
def home():
    if 'username' in session:
        try:
            blob_service_client = BlobServiceClient(account_url=BLOB_ACCOUNT_URL, credential=azure_credential)
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob="index.html")
            downloader = blob_client.download_blob()
            content = downloader.readall().decode('utf-8')
            return content
        except Exception as e:
            return f"<h1>Geschützter Inhalt</h1><p>Fehler beim Laden von Azure Storage: {e}</p>"
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s AND password_hash = %s", (username, password))
                user = cursor.fetchone()
            conn.close()

            if user:
                session['username'] = user['username']
                return redirect(url_for('home'))
            else:
                error = 'Ungültige Anmeldedaten. Bitte erneut versuchen.'
        except Exception as e:
            error = f'Ein Datenbankfehler ist aufgetreten: {e}'

    return f'''
        <form method="post">
            <h1>Login</h1>
            {f"<p style='color:red;'>{error}</p>" if error else ""}
            <p>Username: <input type="text" name="username"></p>
            <p>Password: <input type="password" name="password"></p>
            <p><input type="submit" value="Login"></p>
        </form>
    '''


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)