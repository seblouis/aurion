import os
import json
import time
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Simulation d'un navigateur réel pour éviter les blocages anti-bot
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def send_mail(notes_list):
    msg = EmailMessage()
    msg["Subject"] = "🎓 Aurion : Nouvelle Note Détectée !"
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = os.getenv("EMAIL")

    body = "Bonjour,\n\nUne ou plusieurs nouvelles notes ont été publiées sur Aurion :\n\n"
    body += "\n".join([f"• {n}" for n in notes_list])
    body += "\n\nCeci est un message automatique de ton cluster Docker."
    
    msg.set_content(body)

    try:
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL"), os.getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
        print("✅ Mail de notification envoyé avec succès.")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi du mail : {e}")

def run_bot():
    driver = get_driver()
    wait = WebDriverWait(driver, 20)
    storage_path = "/app/data/storage.json"
    
    try:
        print(f"[{time.strftime('%H:%M:%S')}] Connexion à Aurion...")
        driver.get(os.getenv("AURION_URL"))

        # --- PHASE DE LOGIN ---
        # Attente que le champ username soit présent
        user_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        user_field.send_keys(os.getenv("AURION_USER"))
        
        driver.find_element(By.NAME, "password").send_keys(os.getenv("AURION_PASS"))
        
        # On cherche le bouton de validation (souvent de type submit)
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        login_button.click()
        
        print("Connexion réussie, accès à la page des notes...")
        
        # --- LECTURE DES NOTES ---
        # Attendre que le tableau des notes soit chargé (on attend les balises <td>)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "td")))
        time.sleep(2) # Sécurité pour le rendu JS

        rows = driver.find_elements(By.TAG_NAME, "tr")
        current_notes = []
        for row in rows:
            text = row.text.strip()
            # On ne garde que les lignes qui contiennent du texte (matière + note)
            if text and len(text) > 3:
                current_notes.append(text)

        # --- COMPARAISON ET NOTIFICATION ---
        old_notes = []
        if os.path.exists(storage_path):
            with open(storage_path, "r", encoding="utf-8") as f:
                old_notes = json.load(f)

        # On identifie les lignes qui n'étaient pas là avant
        new_notes = [n for n in current_notes if n not in old_notes]

        if new_notes:
            print(f"🔥 {len(new_notes)} nouvelle(s) note(s) trouvée(s) !")
            send_mail(new_notes)
            # Mise à jour du stockage
            with open(storage_path, "w", encoding="utf-8") as f:
                json.dump(current_notes, f, ensure_ascii=False, indent=4)
        else:
            print("💤 Aucune nouvelle note détectée.")

    except Exception as e:
        print(f"⚠️ Une erreur est survenue : {e}")
        # Optionnel : faire un screenshot pour debug en cas d'erreur
        # driver.save_screenshot("/app/data/error_debug.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    # Fréquence de vérification : toutes les 4 heures
    CHECK_INTERVAL = 4 * 3600 
    print("🚀 Démarrage du moteur Aurion Notifier (Mode Docker Cluster)")
    while True:
        run_bot()
        print(f"Prochaine vérification dans 4 heures...")
        time.sleep(CHECK_INTERVAL)