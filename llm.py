#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

# Lade die Umgebungsvariablen aus der .env Datei
load_dotenv()

# Lese API_KEY und API_ENDPOINT aus der .env Datei
API_KEY = os.getenv("API_KEY")
API_ENDPOINT = os.getenv("API_ENDPOINT")

# Überprüfe, ob beide Variablen gesetzt sind
if not API_KEY or not API_ENDPOINT:
    raise Exception("API_KEY oder API_ENDPOINT sind nicht gesetzt. Überprüfen Sie die .env.")


def send_prompt(prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    data = {
        "model": "deepseek-r1", # "llama-3.3-70b-instruct"
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 100,
        "temperature": 0.7,
    }

    response = requests.post(API_ENDPOINT, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        print("Fehler bei der Anfrage:", response.status_code, response.text)
        return None


if __name__ == "__main__":
    #prompt = input("Gib deinen Prompt ein: ")
    prompt = "Who is the orange mad man in the USA?"
    result = send_prompt(prompt)

    if result:
        if "choices" in result and len(result["choices"]) > 0:
            antwort = result["choices"][0]["message"]["content"].strip()
            print("Antwort der API:")
            print(antwort)
            print(result["choices"])
        else:
            print("Unerwartetes Antwortformat:", result)
