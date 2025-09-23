1. Foundry Setup

Install Foundry: `winget install Microsoft.FoundryLocal`

Install a Foundry model: `foundry model download phi-3.5-mini`

2. Server Setup

Create virtual environment: `python -m venv venv`

Activate virtual environment: `.\venv\Scripts\activate`

Install dependencies: pip install -r `requirements.txt`

3. Starting the Server

`python foundry-server.py`

4. Exit the virtual environment
- Stop the server with ctrl+c
- Run `deactivate`
