# How to Run the Multi Agent Project

Follow these steps to set up and run the HR Support Chatbot.

## Prerequisites
- Python 3.9+
- OpenAI API Key

## 1. Setup Environment
Create a virtual environment and install the required dependencies:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Configuration
Create a `.env` file in the root directory and add your OpenAI API key:

```text
OPENAI_API_KEY=your_api_key_here
```
