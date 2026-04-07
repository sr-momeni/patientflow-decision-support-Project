# ER Triage Chatbot

This component provides an AI-powered triage assistant for the Emergency Department (ER). It uses GPT-4o (Standard and Realtime) to conduct initial patient assessments and calculate urgency scores using the Canadian Triage and Acuity Scale (CTAS).

The chatbot is configured to acknowledge that the patient is physically present in the ER, sitting at the triage desk.

## Prerequisites

1.  **OpenAI API Key**: Ensure you have a valid OpenAI API key in a file named `openAI_key.txt` in the project root directory.
2.  **Dependencies**: Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

1.  **Start the Backend Server**:
    From the project root directory, run:
    ```bash
    uvicorn backend.server:app --reload --port 8000
    ```
    OR (if using the direct server script):
    ```bash
    python backend/server.py
    ```

2.  **Access the Chatbot UI**:
    Open your web browser and navigate to:
    [http://localhost:8000/chatbot/ui](http://localhost:8000/chatbot/ui)

## Features

-   **Standard Chat**: A text-based triage conversation.
-   **Realtime Voice**: A high-speed voice interface using OpenAI's Realtime API (requires WebRTC support in the browser).
-   **Urgency Scoring**: Automatically calculates CTAS level (1-5) based on the conversation summary.
-   **ER Context**: The AI is instructed that the patient is physically in the hospital.

## Project Structure

-   `backend/chatbot/chatbot_agent.py`: Core logic for the standard GPT-4o chatbot.
-   `backend/chatbot/chatbot_routes.py`: FastAPI routes, including Realtime API session management.
-   `backend/chatbot/static/index.html`: The web-based user interface.
-   `backend/agents/urgency_scoring_agent.py`: Logic for mapping clinical data to CTAS levels.
