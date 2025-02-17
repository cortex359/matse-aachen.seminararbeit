#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv
import time
from configparser import ConfigParser
import logs


class PRPmodel:
    """Pairwise Ranking Prompting model configuration."""
    def __init__(self, config: ConfigParser):
        self.system_prompt = config['Model']['system_prompt']
        self.user_prompt_template = config['Model']['user_prompt_template']

        self.model = config['Model']['model']
        self.provider = config['Model']['provider']
        self.max_output_tokens = config['Model'].getint('max_output_tokens', 4096)
        self.initial_temperature = config['Model'].getfloat('initial_temperature', 0.1)
        self.temperature_increase_on_error = config['Model'].getfloat('temperature_increase_on_error', 0.1)
        self.max_retries = config['Model'].getint('max_retries', 10)


        assert self.model in [ "DeepSeek-R1", "deepseek-r1:14b", "Llama-3.3-70B-Instruct", "deepseek-r1-distill-llama-70b", "llama-3.3-70b-instruct", "qwen2.5-coder-32b-instruct", "llama3.1:8b", "gemma2:latest", "phi3:latest", "llama-3.3-70b-instruct", "deepseek-r1" ]

    def _send_prompt_openai(self, nb1: str, nb2: str, err_count: int = 0) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.API_KEY}"
        }

        user_msg: str = self.user_prompt_template.format(nb1=nb1, nb2=nb2)

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": self.max_output_tokens,
            "temperature": (self.initial_temperature + self.temperature_increase_on_error * err_count),
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.post(self.API_ENDPOINT, headers=headers, json=data, timeout=120)
            except requests.exceptions.Timeout:
                logging.warning(f"Request timed out. Retrying in {2 ** attempt} seconds... (Attempt {attempt}/{max_retries})")
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




    def _send_prompt_azure(self, nb1: str, nb2: str) -> dict:
        if not systemprompt:
            systemprompt = """You are provided with two Jupyter notebooks (Notebook A and Notebook B), each containing exercises with their solutions. Evaluate only the correctness and accuracy of the solutions—ignore code style, formatting, documentation, or any other factors. Determine which notebook contains more correct solutions and output ONLY "Notebook A" or "Notebook B"."""

        data = {
            "model": "DeepSeek-R1",  # "Llama-3.3-70B-Instruct"
            "messages": [
                SystemMessage(content=systemprompt),
                UserMessage(content=f"Notebook A: {nb1}\n\n\nNotebook B: {nb2}")
            ],
            "max_tokens": 4096,
            "temperature": 0.1,
        }

        model = ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(os.environ["AZUREAI_ENDPOINT_KEY"]),
            model = "DeepSeek-R1"
        )

        for attempt in range(1, max_retries + 1):
            try:
                response = model.complete(
                    messages=data["messages"],
                    model = data["model"],
                    max_tokens=data["max_tokens"],
                    temperature=data["temperature"]
                )
            except HttpResponseError as e:
                print(f"Request failed: {e}. Retrying in {2 ** attempt} seconds... (Attempt {attempt}/{max_retries})")
                time.sleep(2 ** attempt)
                continue

            print(f"{response['usage']['prompt_tokens']} + {response['usage']['completion_tokens']}")
            if response and response['choices'][0]['finish_reason'] == 'stop':
                return response

        print("Max retries exceeded due to rate limiting.")
        return None



    def send_prompt(self, nb1: str, nb2: str):
        load_dotenv()
        match self.provider:
            case "Azure":
                return _send_prompt_azure(nb1, nb2)
            case "KISSKI":
                self.API_KEY = os.getenv("KISSKI_API_KEY")
                self.API_ENDPOINT = os.getenv("KISSKI_API_ENDPOINT")
            case "LFI":
                self.API_KEY = os.getenv("LFI_API_KEY")
                self.API_ENDPOINT = os.getenv("LFI_API_ENDPOINT")
            case _:
                self.API_KEY = os.getenv("API_KEY")
                self.API_ENDPOINT = os.getenv("API_ENDPOINT")

        if not self.API_KEY or not self.API_ENDPOINT:
            raise Exception(f"API_KEY oder API_ENDPOINT sind nicht für {provider=} gesetzt. Überprüfen Sie die .env.")
        return _send_prompt_openai(nb1, nb2)



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
