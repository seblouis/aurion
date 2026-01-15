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
    # On imite un vrai navigateur pour éviter d'être bloqué
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def send_mail(content):
    msg = EmailMessage()
    msg["Subject"] = "🎓 Aurion : Nouvelle Note !"
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = os.getenv("EMAIL")
    msg.set_content(f"Une nouvelle note a été détectée :\n\n" + "\n".join(content))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(os.getenv("EMAIL"), os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)

def run_bot():
    driver = get_driver()
    wait = WebDriverWait(driver, 15)
    
    try:
        print("Connexion à Aurion...")
        driver.get(os.getenv("AURION_URL"))

        # --- LOGIQUE DE LOGIN ---
        # Remplace 'username' et 'password' par les vrais IDs des champs (Inspecter l'élément)
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(os.getenv("AURION_USER"))
        driver.find_element(By.NAME, "password").send_keys(os.getenv("AURION_PASS"))
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        print("Lecture des notes...")
        time.sleep(5) # Temps de chargement du tableau
        
        # Extraction brute (on récupère les lignes du tableau)
        elements = driver.find_elements(By.CSS_SELECTOR, "tr") 
        current_notes = [el.text.strip() for el in elements if len(el.text) > 5]

        # --- COMPARAISON ---
        storage_path = "/app/data/storage.json"
        old_notes = []
        if os.path.exists(storage_path):
            with open(storage_path, "r") as f:
                old_notes = json.load(f)

        new_notes = [n for n in current_notes if n not in old_notes]

        if new_notes:
            print(f"Trouvé {len(new_notes)} nouvelles notes !")
            send_mail(new_notes)
            with open(storage_path, "w") as f:
                json.dump(current_notes, f)
        else:
            print("Rien de neuf.")

    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    # Boucle pour vérifier toutes les 6 heures (ou configurer via Cron externe)
    while True:
        run_bot()
        print("Sommeil pour 6 heures...")
        time.sleep(21600)