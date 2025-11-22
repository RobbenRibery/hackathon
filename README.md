# Negotiation Agent

A web-based negotiation system where autonomous buyer and seller agents negotiate using LLMs.

## Quick Start

1. **Install dependencies**:
   ```bash
   uv pip install -e .
   ```

2. **Set up OpenAI API Key**:
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   Get your API key from: https://platform.openai.com/api-keys

3. **Start the web server**:
   ```bash
   python web_server.py
   ```

4. **Open in browser**:
   ```
   http://localhost:8000
   ```

## Features

- **Configuration Editor**: Edit BUYER and SELLER agent settings via web UI
- **System Prompt Customization**: Define agent personalities and negotiation styles
- **Real-time Negotiations**: Run negotiation rounds with live chat interface
- **WhatsApp-style Chat UI**: Buyer messages on right (green), seller on left (white)

## Configuration

Both BUYER and SELLER configurations support:
- `aggression` (0-5): Negotiation style intensity
- `maxRounds` (1-10): Maximum negotiation rounds
- `priceMarginPct` (0-30): Price margin percentage
- `responseDelayMs` (0-5000): Artificial response delay
- `useLLM` (bool): Enable LLM or use rule-based logic
- `allowedPaymentMethods` (array): Accepted payment methods
- `logChat` (bool): Enable chat logging
- `content` (string): System prompt content

Configurations are stored in `config/buyer.json` and `config/seller.json`.

## Architecture

- **Backend**: FastAPI server (`web_server.py`)
- **Frontend**: Single-page HTML application (`webui/index.html`)
- **Core**: Synapse protocol agents (`synapse/`)
- **Model**: OpenAI GPT-4o-mini (configurable in `web_server.py` and `synapse/agent.py`)

## Project Structure

```
hackathon/
├── web_server.py          # FastAPI web server
├── webui/
│   └── index.html         # Web UI
├── synapse/               # Core negotiation protocol
│   ├── agent.py           # NegotiationAgent class
│   ├── protocol.py         # Message and protocol definitions
│   ├── router.py           # Message routing
│   ├── schemas.py          # BUYER/SELLER schemas
│   └── config_loader.py   # Configuration loading
└── config/                # Agent configurations
    ├── buyer.json
    └── seller.json
```
