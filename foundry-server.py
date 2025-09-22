# Foundry Server: Implements OpenContext agent that interacts with AI Foundry Language Models

import os
import asyncio
import threading
import signal
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from foundry_local import FoundryLocalManager
from langchain.agents import Tool, initialize_agent
from langchain_community.chat_models import ChatOpenAI
from fastmcp import Client

AGENT_PORT = 3002
MCP_SERVER_ENDPOINT = "http://localhost:3000/mcp"

app = Flask(__name__)
CORS(app)

opencontext_client = Client(MCP_SERVER_ENDPOINT)

async def read_graph_async():
    async with opencontext_client:
        result = await opencontext_client.call_tool("read_graph", {})
        return result

def read_graph(tool_input=None):
    try:
        loop = asyncio.get_running_loop()
        return asyncio.run_coroutine_threadsafe(read_graph_async(), loop).result()
    except RuntimeError:
        return asyncio.run(read_graph_async())


class AIBackendService:
    def __init__(self):
        self.foundry_local_manager = None
        self.openai_client = None
        self.model_info = None
        self.is_initialized = False
        self.is_initializing = False
        self.init_error = None
        self.model_alias = "phi-3.5-mini"
        self.llm = None
        self.agent = None

    async def initialize(self):
        if self.is_initialized:
            return
        if self.is_initializing:
            # Wait for existing initialization to complete
            while self.is_initializing:
                await asyncio.sleep(0.1)
            return

        self.is_initializing = True
        print(f"[AIBackend] Initializing with model: {self.model_alias}")
        
        try:
            # Initialize FoundryLocal manager exactly like agent-script.py
            self.foundry_local_manager = FoundryLocalManager(
                alias_or_model_id=self.model_alias,
                bootstrap=False
            )
            
            is_service_running = self.foundry_local_manager.is_service_running()
            print(f"FoundryLocal service running: {is_service_running}")
            
            if not is_service_running:
                print("[AIBackend] Starting FoundryLocal service...")
                self.foundry_local_manager.start_service()
            
            print(f"[AIBackend] Loading {self.model_alias} model...")
            self.foundry_local_manager.load_model(self.model_alias)
            
            # Get model info
            self.model_info = self.foundry_local_manager.get_model_info(self.model_alias)
            print("[AIBackend] Model Info:", self.model_info)

            # Set up environment variables for LangChain
            os.environ["OPENAI_API_BASE"] = self.foundry_local_manager.endpoint
            os.environ["OPENAI_API_KEY"] = self.foundry_local_manager.api_key

            # Initialize LangChain LLM
            self.llm = ChatOpenAI(
                model_name=self.model_info.id,
                temperature=0.0  # Make it more deterministic
            )

            #Configure tools available for the agent
            tools = [
                Tool(
                    name="read_graph",
                    func=read_graph,
                    description="Read the knowledge graph."
                )
            ]

            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # Agent Setup with better error handling
            self.agent = initialize_agent(
                tools=tools,
                llm=self.llm,
                agent="zero-shot-react-description",
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3,  # Reduced from 5 to avoid too many retry loops
                max_execution_time=30,  # Add timeout
                early_stopping_method="generate"  # Stop on first successful generation
            )
            
            print(f"[AIBackend] Agent initialized with tools: {hasattr(self.agent, 'tools')}")
            if hasattr(self.agent, 'tools'):
                print(f"[AIBackend] Agent tools: {[t.name for t in self.agent.tools] if hasattr(self.agent, 'tools') else 'No tools attribute'}")

            # Also initialize direct OpenAI client for fallback
            self.openai_client = openai.OpenAI(
                base_url=self.foundry_local_manager.endpoint,
                api_key=self.foundry_local_manager.api_key,
            )

            self.is_initialized = True
            self.init_error = None
            print("[AIBackend] Successfully initialized")
        except Exception as error:
            print(f"[AIBackend] Failed to initialize: {error}")
            self.init_error = str(error)
            raise error
        finally:
            self.is_initializing = False


    def get_status(self):
        model_info = None
        if self.model_info:
            if isinstance(self.model_info, dict) and 'id' in self.model_info:
                model_info = {
                    "id": self.model_info['id'],
                    "alias": self.model_alias
                }
            else:
                # Handle case where model_info might be an object with id attribute
                model_info = {
                    "id": getattr(self.model_info, 'id', self.model_alias),
                    "alias": self.model_alias
                }
        
        return {
            "isInitialized": self.is_initialized,
            "isInitializing": self.is_initializing,
            "error": self.init_error,
            "modelInfo": model_info,
            "hasAgent": self.agent is not None,
            "hasLLM": self.llm is not None
        }

# Create AI service instance
ai_service = AIBackendService()

# Routes
@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(ai_service.get_status())

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        prompt = f"""Use the read_graph tool and then {message}."""
        print(f"PROMPT: {prompt}")
        
        response = ai_service.agent.run(prompt)
        print("Agent output:")
        print(response)
        return jsonify({'response': str(response)}), 200
            
    except Exception as error:
        print(f'[AIBackend] Chat direct error: {error}')
        return jsonify({'error': str(error)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok', 
        'timestamp': datetime.now().isoformat()
    })

def initialize_ai_background():
    """Initialize AI service in background thread"""
    def run_init():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(ai_service.initialize())
        except Exception as error:
            print(f'[AIBackend] Failed to initialize AI on startup: {error}')
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_init)
    thread.daemon = True
    thread.start()

def signal_handler(sig, frame):
    print('[AIBackend] Received shutdown signal, shutting down gracefully')
    sys.exit(0)

if __name__ == '__main__':
    # shutdown handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"[AIBackend] Server running on http://localhost:{AGENT_PORT}")
    
    # Start agent in background
    initialize_ai_background()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=AGENT_PORT, debug=False)