#!/usr/bin/env python3
import re
import traceback
import requests
import time
from configparser import ConfigParser
from nbformat import NotebookNode

import os
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.pipeline.transport import RequestsTransport
from dotenv import load_dotenv

from logs import global_logger as logging


class PRPmodel:
    """Pairwise Ranking Prompting model configuration."""
    def __init__(self, config: ConfigParser, data: dict[str, NotebookNode]):
        self.API_KEY = os.getenv("API_KEY")
        self.API_ENDPOINT = os.getenv("API_ENDPOINT")

        self.system_prompt = config['Prompting']['system_prompt']
        self.user_prompt_template = config['Prompting']['user_prompt_template']
        self.majority_vote = config['Prompting'].getboolean('majority_vote', False)
        self.votes = config['Prompting'].getint('votes', 1)

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
            assert self.model in [ "DeepSeek-R1", "deepseek-r1-distill-llama-70b", "llama-3.3-70b-instruct", "qwen2.5-coder-32b-instruct", "mistral-large-instruct"]
        elif self.provider == "LFI":
            assert self.model in [ "deepseek-r1:8b", "llama3.1:8b", "gemma2:latest", "phi3:latest" ]
        else:
            raise AssertionError(f"Provider '{self.provider}' not supported.")

        if self.majority_vote:
            assert self.initial_temperature >= 0.1, "Majority voting requires at least a 0.1 temperature"
            assert self.votes % 2 == 1, "Majority voting requires an odd number of votes"

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

        logging.debug(f"Sending prompt: {data}")

        for attempt in range(1, self.max_retries + 1):
            wait_time: int = 2 ** attempt
            try:
                response = requests.post(self.API_ENDPOINT, headers=headers, json=data, timeout=120)
                logging.debug(f'Response with status_code {response.status_code} "{response.text}"')
                if response.status_code == 200:
                    if response.json()['choices'][0]['finish_reason'] == 'stop':
                        logging.info(f'Received valid response: {response.json()}')
                        return response.json()
                    else:
                        logging.warning(f'Response did not finish correctly. (Maybe limit of {self.max_output_tokens} output tokens was hit?): {response.json()}')
                        wait_time = 1
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
                logging.error(f"Error in request: {e} {traceback.format_exc()}.")

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

        logging.debug(f"Sending prompt: {data}")

        # transport needed to specify a timeout
        transport = RequestsTransport(connection_timeout=600, read_timeout=600)

        client = ChatCompletionsClient(
            endpoint=os.environ["AZURE_INFERENCE_SDK_ENDPOINT"],
            credential=AzureKeyCredential(os.environ["AZUREAI_ENDPOINT_KEY"]),
            model = self.model,
            transport=transport
        )

        for attempt in range(1, self.max_retries + 1):
            wait_time: int = 2 ** attempt
            try:
                response = client.complete(
                    messages=data["messages"],
                    model = data["model"],
                    max_tokens=data["max_tokens"],
                    temperature=data["temperature"],
                )
                if (response and "choices" in response and len(response["choices"]) > 0
                        and response['choices'][0]['finish_reason'] == 'stop'):
                    logging.info(f'Received valid response: {response}')
                    return dict(response)
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
                if self.model == "Llama-3.3-70B-Instruct":
                    self.API_KEY = os.getenv("AZURE_API_KEY")
                    self.API_ENDPOINT = os.getenv("AZURE_API_ENDPOINT")
                else:
                    self.API_KEY = os.getenv("AZUREAI_ENDPOINT_KEY")
                    self.API_ENDPOINT = os.getenv("AZURE_INFERENCE_SDK_ENDPOINT")
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


    def parse_response(self, msg: str) -> bool:
        """Interprets the most common output forms that might deviate from instruction, i.e. ending like
        - Notebook A
        - "Notebook B"
        - 'Notebook A'.
        - Notebook B.
        - **Notebook A**
        - \boxed{Notebook A}
        """
        pattern = r'["\'\*{]?Notebook (A|B)[}"\'\*]?[\.\s\*]*$'
        match = re.search(pattern, msg, re.IGNORECASE)
        if match:
            notebook_letter = match.group(1).upper()
            return notebook_letter == 'B'
        else:
            raise ValueError("Output does not end with a valid Notebook identifier")


    def sort_function(self, d1, d2, err_count: int = 0) -> bool:
        if err_count == self.max_retries:
            logging.error(f"Compairing {d1} and {d2} failed after max number of retries.")
            return False
        response = self.send_prompt(str(self.dataset[d1]), str(self.dataset[d2]), err_count)
        if response and "choices" in response and len(response["choices"]) > 0:
            msg = response["choices"][0]["message"]["content"].strip()
            try:
                comparison: bool = self.parse_response(msg)
                logging.info(f"{d1} < {d2}") if comparison else logging.info(f"{d1} > {d2}")
                return comparison
            except ValueError:
                if err_count < self.max_retries:
                    logging.warning(f"Response was not decisively. {msg=}. Retrying... {err_count}/{self.max_retries}")
                    return self.sort_function(d1, d2, err_count=err_count+1)
                else:
                    logging.error(f"Compairing {d1} and {d2} failed after max number of retries. Assuming {d1} > {d2}.")
                    return False
        else:
            logging.error(f"Compairing {d1} and {d2} failed. Unexpected response: {response}")

        wait_time = 2 ** (err_count + 1)
        logging.warning(f"Retrying in {wait_time} seconds... (Attempt {err_count}/{self.max_retries})")
        time.sleep(wait_time)
        return self.sort_function(d1, d2, err_count=err_count+1)

    def sort_function_majority_vote(self, d1, d2):
        votes = 0
        majority = self.votes // 2 + 1
        for i in range(1, self.votes + 1):
            if self.sort_function(d1, d2):
                votes += 1
            else:
                votes -= 1

            # Early stopping if absolut majority is reached
            logging.debug(f"Majority voting for {d1} vs. {d2} now at {votes}.")
            if votes >= majority:
                logging.info(f'{d1} < {d2} with {(i+votes)/2}/{self.votes} votes.')
                return True
            elif votes <= -majority:
                logging.info(f'{d1} > {d2} with {(i-votes)/2}/{self.votes} votes.')
                return False

        if votes > 0:
            logging.info(f'{d1} < {d2} with {(self.votes + votes) / 2}/{self.votes} votes.')
            return True
        else:
            logging.info(f'{d1} > {d2} with {(self.votes - votes) / 2}/{self.votes} votes.')
            return False


if __name__ == "__main__":
    config: ConfigParser = ConfigParser()
    config.read("experiments/vorlage_llama3.3_azure.ini")
    model = PRPmodel(config, {})

    result = model.send_prompt("Aufgabe: Sage Hallo!\nApfelkuchen ist lecker!", "Aufgabe: Sage Hallo!\nHallo!")

    antwort = result["choices"][0]["message"]["content"].strip()
    print("Antwort der API:")
    print(antwort)
