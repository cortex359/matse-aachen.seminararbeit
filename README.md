# Paarweises Ranking für automatische Textbewertung mit LLMs

![titlebild.png](imgs/titlebild.png)

Diese Repository enthält den Code, mit dem die Untersuchungen der Bachelor-Seminararbeit **Paarweises Ranking für automatische Textbewertung mit LLMs** 
im Studiengang Angewandte Mathematik und Informatik (dual) B. Sc. an der Fachhochschule Aachen durchgeführt wurden. 


![Übersicht.drawio.png](imgs/%C3%9Cbersicht.drawio.png)

Die durchgeführten Experimente sind im Ordner `experiments` als .ini Datei konfiguriert und können mit dem Aufruf

```bash
python execute.py [experiment1] [experiment2] …
``` 

der Reihe nach ausgeführt werden. Dabei werden Logdateien im Ordner `experiments/logs` für eine spätere Auswertung erstellt. 


Für die Kommunikation mit den LLM APIs werden, je nach Provider, die folgende Umgebungsvariablen benötigt:

```dotenv
HUGGINGFACE="********************************"

# KISSKI
KISSKI_API_KEY="********************************"
KISSKI_API_ENDPOINT="https://chat-ai.academiccloud.de/v1/chat/completions"

# Ollama
OLLAMA_API_KEY="********************************"
OLLAMA_API_ENDPOINT="http://localhost:8080/ollama/v1/chat/completions"

# LFI Ollama
LFI_API_ENDPOINT="https://********************************/ollama/v1/chat/completions"
LFI_API_KEY="********************************"

# Azure Llama 3.3 70B
AZURE_API_KEY="********************************"
AZURE_API_ENDPOINT="https://********************************.models.ai.azure.com/chat/completions"

# Azure DeepSeek-R1
AZUREAI_ENDPOINT_KEY="********************************"
AZURE_INFERENCE_SDK_ENDPOINT="https://********************************.services.ai.azure.com/models" 
```

---


**Studiengang**

Angewandte Mathematik und Informatik B.Sc. ([AMI](https://www.fh-aachen.de/studium/angewandte-mathematik-und-informatik-bsc)) an der [FH Aachen](https://www.fh-aachen.de/), University of Applied Sciences.

**Ausbildung mit IHK Abschluss**

Mathematisch technische/-r Softwareentwickler/-in ([MaTSE](https://www.matse-ausbildung.de/startseite.html)) am Lehr- und Forschungsgebiet Igenieurhydrologie ([LFI](https://lfi.rwth-aachen.de/)) der [RWTH Aachen](https://www.rwth-aachen.de/) University.
