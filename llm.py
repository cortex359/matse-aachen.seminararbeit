#!/usr/bin/env python3
import logging
import os
import requests
from dotenv import load_dotenv
import time
from configparser import ConfigParser
import logs
from logs import setup_logger
import os
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage
from dotenv import load_dotenv

class PRPmodel:
    """Pairwise Ranking Prompting model configuration."""
    def __init__(self, config: ConfigParser, data: dict):
        self.API_KEY = os.getenv("API_KEY")
        self.API_ENDPOINT = os.getenv("API_ENDPOINT")

        self.system_prompt = config['Prompting']['system_prompt']
        self.user_prompt_template = config['Prompting']['user_prompt_template']

        self.model = config['Model']['model']
        self.provider = config['Model']['provider']
        self.max_output_tokens = config['Model'].getint('max_output_tokens', 4096)
        self.initial_temperature = config['Model'].getfloat('initial_temperature', 0.1)
        self.temperature_increase_on_error = config['Model'].getfloat('temperature_increase_on_error', 0.1)
        self.max_retries = config['Model'].getint('max_retries', 10)

        self.dataset = data

        assert self.provider in ["Azure", "KISSKI", "LFI"]
        if self.provider == "Azure":
            assert self.model in [ "DeepSeek-R1", "Llama-3.3-70B-Instruct" ]
        elif self.provider == "KISSKI":
            assert self.model in [ "DeepSeek-R1", "deepseek-r1-distill-llama-70b", "llama-3.3-70b-instruct", "qwen2.5-coder-32b-instruct"]
        else:
            assert self.model in [ "deepseek-r1:14b", "llama3.1:8b", "gemma2:latest", "phi3:latest", "llama-3.3-70b-instruct" ]

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

        logger.debug(f"Sending prompt: {data}")

        for attempt in range(1, self.max_retries + 1):
            wait_time: int = 2 ** attempt
            try:
                response = requests.post(self.API_ENDPOINT, headers=headers, json=data, timeout=120)
                logger.info(f"Response: {response.json()}")
                if response.status_code == 200 and response.json()['choices'][0]['finish_reason'] == 'stop':
                    return response.json()
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                    logging.warning(f"Rate limit hit.")
                else:
                    logging.error(f"Error in response: {response.status_code}, {response.text}.")
            except requests.exceptions.Timeout:
                logging.warning(f"Request timed out.")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error in request: {e}.")

            logging.info(f"Retrying in {wait_time} seconds... (Attempt {attempt}/{self.max_retries})")
            time.sleep(wait_time)

        logging.critical(f"Max retries exceeded. No valid response after {self.max_retries} attempts.")
        return {}


    def _send_prompt_azure(self, nb1: str, nb2: str, err_count: int = 0) -> dict:
        user_msg: str = self.user_prompt_template.format(nb1=nb1, nb2=nb2)

        data = {
            "model": self.model,
            "messages": [
                SystemMessage(content=self.system_prompt),
                UserMessage(content=user_msg),
            ],
            "max_tokens": self.max_output_tokens,
            "temperature": (self.initial_temperature + self.temperature_increase_on_error * err_count),
        }

        logger.debug(f"Sending prompt: {data}")

        client = ChatCompletionsClient(
            endpoint=os.environ["AZURE_INFERENCE_SDK_ENDPOINT"],
            credential=AzureKeyCredential(os.environ["AZUREAI_ENDPOINT_KEY"]),
            model = self.model
        )

        for attempt in range(1, self.max_retries + 1):
            wait_time: int = 2 ** attempt
            try:
                response = client.complete(
                    messages=data["messages"],
                    model = data["model"],
                    max_tokens=data["max_tokens"],
                    temperature=data["temperature"]
                )
                logger.info(f"Response: {response}")
                if response and response['choices'][0]['finish_reason'] == 'stop':
                    return response
                else:
                    logging.error(f"Error in response: {response}.")
            except Exception as e:
                logging.error(f"Error in request: {e}.")

            logging.info(f"Retrying in {wait_time} seconds... (Attempt {attempt}/{self.max_retries})")
            time.sleep(wait_time)

        logging.critical(f"Max retries exceeded. No valid response after {self.max_retries} attempts.")
        return {}


    def send_prompt(self, nb1: str, nb2: str, err_count: int = 0) -> dict:
        load_dotenv()
        match self.provider:
            case "Azure":
                return self._send_prompt_azure(nb1, nb2, err_count)
            case "KISSKI":
                self.API_KEY = os.getenv("KISSKI_API_KEY")
                self.API_ENDPOINT = os.getenv("KISSKI_API_ENDPOINT")
            case "LFI":
                self.API_KEY = os.getenv("LFI_API_KEY")
                self.API_ENDPOINT = os.getenv("LFI_API_ENDPOINT")
            case _:
                logging.warning(f"Provider '{self.provider}' not supported. Fallback to API_ENDPOINT.")

        if not self.API_KEY or not self.API_ENDPOINT:
            raise Exception(f"API_KEY or API_ENDPOINT are not set for {self.provider=}. Check .env.")
        return self._send_prompt_openai(nb1, nb2, err_count)


    def sort_function(self, d1, d2, err_count: int = 0) -> bool:
        if err_count == self.max_retries:
            logger.error(f"Compairing {d1} and {d2} failed after max number of retries.")
            return False
        response = self.send_prompt(str(self.dataset[d1]), str(self.dataset[d2]))
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
    logger = setup_logger('llm', 'llm.log', logging.DEBUG)

    config: ConfigParser = ConfigParser()
    config.read("./experiments/001_llama3.3_azure.ini")
    model = PRPmodel(config)

    result = model.send_prompt("Aufgabe: Sage Hallo!\nApfelkuchen ist lecker!", "Aufgabe: Sage Hallo!\nHallo!")

    if result:
        if "choices" in result and len(result["choices"]) > 0:
            antwort = result["choices"][0]["message"]["content"].strip()
            print("Antwort der API:")
            print(antwort)
        else:
            print("Unerwartetes Antwortformat:", result)
