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


def send_prompt(nb1: str, nb2: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    # "Given a Jupyter notebook with exercises and solutions, which of the following two notebooks should get the higher grade? Output ONLY 'Notebook A' or 'Notebook B' and nothing else!"
    systemprompt = """You are provided with two Jupyter notebooks (Notebook A and Notebook B), each containing exercises with their solutions. Evaluate only the correctness and accuracy of the solutions—ignore code style, formatting, documentation, or any other factors. Determine which notebook contains more correct solutions and output ONLY "Notebook A" or "Notebook B"."""

    data = {
        "model": "llama-3.3-70b-instruct", # "deepseek-r1",
        "messages": [
            {"role": "system", "content": systemprompt},
            {"role": "user", "content": f"Notebook A: {nb1}\n\n\nNotebook B: {nb2}"}
        ],
        "max_tokens": 10,
        "temperature": 0.2,
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
