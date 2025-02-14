#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv
import time

from functools import lru_cache

# Lade die Umgebungsvariablen aus der .env Datei
load_dotenv()

# Lese API_KEY und API_ENDPOINT aus der .env Datei
API_KEY = os.getenv("API_KEY")
API_ENDPOINT = os.getenv("API_ENDPOINT")

# Überprüfe, ob beide Variablen gesetzt sind
if not API_KEY or not API_ENDPOINT:
    raise Exception("API_KEY oder API_ENDPOINT sind nicht gesetzt. Überprüfen Sie die .env.")


def send_prompt(nb1: str, nb2: str, systemprompt: str = None, max_retries: int = 10):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    # "Given a Jupyter notebook with exercises and solutions, which of the following two notebooks should get the higher grade? Output ONLY 'Notebook A' or 'Notebook B' and nothing else!"
    if not systemprompt:
        systemprompt = """You are provided with two Jupyter notebooks (Notebook A and Notebook B), each containing exercises with their solutions. Evaluate only the correctness and accuracy of the solutions—ignore code style, formatting, documentation, or any other factors. Determine which notebook contains more correct solutions and output ONLY "Notebook A" or "Notebook B"."""

    data = {
        "model": "DeepSeek-R1",  ##"Llama-3.3-70B-Instruct", # "deepseek-r1:14b", #"deepseek-r1-distill-llama-70b", # "llama-3.3-70b-instruct", # "qwen2.5-coder-32b-instruct", # "llama3.1:8b", # "gemma2:latest", # "phi3:latest", # "llama-3.3-70b-instruct", # "deepseek-r1",
        "messages": [
            {"role": "system", "content": systemprompt},
            {"role": "user", "content": f"Notebook A: {nb1}\n\n\nNotebook B: {nb2}"}
        ],
        "max_tokens": 4096,
        "temperature": 0.1,
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(API_ENDPOINT, headers=headers, json=data, timeout=120)
        except requests.exceptions.Timeout:
            print(f"Request timed out. Retrying in {2 ** attempt} seconds... (Attempt {attempt}/{max_retries})")
            time.sleep(2 ** attempt)
            continue
        except requests.exceptions.RequestException as e:
            # Catch any other requests-related errors
            print(f"Request failed: {e}. Retrying in {2 ** attempt} seconds... (Attempt {attempt}/{max_retries})")
            time.sleep(2 ** attempt)
            continue

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # Rate limit encountered
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                wait_time = int(retry_after)
            else:
                # Exponential backoff: 2, 4, 8, ... seconds
                wait_time = 2 ** attempt
            print(f"Rate limit hit. Retrying in {wait_time} seconds... (Attempt {attempt}/{max_retries})")
            time.sleep(wait_time)
        else:
            print("Error in request:", response.status_code, response.text)
            return None

    print("Max retries exceeded due to rate limiting.")
    return None

#@lru_cache(maxsize=None)
def sort_function(d1, d2, dataset: dict, systemprompt: str, retry=10) -> bool:
    if retry == 0:
        print("Maximale Anzahl an Versuchen erreicht.")
        return False
    response = send_prompt(str(dataset[d1]), str(dataset[d2]), systemprompt)
    if response:
        if "choices" in response and len(response["choices"]) > 0:
            msg = response["choices"][0]["message"]["content"].strip()
            print(msg)
            if msg.endswith("Notebook A"):
                print(f"{d1} > {d2}")
                return False
            elif msg.endswith("Notebook B"):
                print(f"{d1} < {d2}")
                return True
            else:
                # Implement a retry mechanism here
                if retry > 1:
                    print(f"Antwort nicht eindeutig: {msg}. Retrying... {retry-1}")
                    return sort_function(d1, d2, dataset, systemprompt, retry=retry-1)
                else:
                    print(f"{d1} == {d2}")
                    return False
        else:
            print("Unerwartetes Antwortformat:", response)

    wait_time = 2 ** (10-retry)
    print(f"Retrying... {wait_time}")
    time.sleep(wait_time)
    return sort_function(d1, d2, dataset, systemprompt, retry=retry-1)


if __name__ == "__main__":
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
