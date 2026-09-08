# How Your Data Moves in AEGIS: A Simple Guide

Welcome! If you're wondering what happens to your documents, questions, and data when you use the AEGIS system, this guide is for you. We've broken down the "data flow" (how information travels) into simple steps without the technical jargon.

## The Big Picture (Flowchart)

Here is a visual map of how your information travels through the system. 

```mermaid
flowchart TD
    %% Styling for a friendly look
    classDef user fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px;
    classDef app fill:#e8f5e9,stroke:#4caf50,stroke-width:2px;
    classDef brain fill:#fff3e0,stroke:#ff9800,stroke-width:2px;
    classDef vault fill:#ffebee,stroke:#f44336,stroke-width:2px;
    classDef monitor fill:#ede7f6,stroke:#673ab7,stroke-width:2px;

    User([👤 You (The User)]):::user
    WebScreen[💻 The Screen You See (Web App)]:::app
    TrafficCop[🚦 The Traffic Cop (API Coordinator)]:::app
    Worker[👷 The Hard Worker (Background Tasks)]:::app
    
    Brain[🧠 The AI Brain (Ollama Models)]:::brain
    Vault[(🔒 The Secure Vault (Database & Storage))]:::vault
    Security[🛡️ The Security Guard (Sentinel)]:::monitor

    %% How they connect
    User -- "Clicks, types, uploads" --> WebScreen
    WebScreen -- "Sends your requests" --> TrafficCop
    
    TrafficCop -- "Sends heavy tasks" --> Worker
    TrafficCop -- "Saves & retrieves info" --> Vault
    TrafficCop -- "Asks questions" --> Brain
    
    Worker -- "Reads & understands documents" --> Brain
    Worker -- "Saves processed files safely" --> Vault
    
    TrafficCop -. "Being watched by" .-> Security
    Security -. "Makes sure nothing leaks to the internet" .-> TrafficCop

```

---

## Step-by-Step: What Happens When...

### 1. When You Upload a Document (PDF, Excel, Word, etc.)
* **You hand it over:** You drag and drop a file onto the screen.
* **The Traffic Cop takes it:** The system's coordinator receives your file and immediately hands it to the **Hard Worker** because reading a long document takes time.
* **The Hard Worker reads it:** The worker reads your document, translates it into a format the AI can understand (like highlighting important parts), and then locks it away safely in the **Secure Vault**.
* **Result:** Your file is now securely stored, completely scrambled (encrypted) so no unauthorized person can read it. 

### 2. When You Ask a Question in the Chat
* **You type a question:** You ask something like, "Summarize the report I just uploaded."
* **The Traffic Cop searches:** It goes to the **Secure Vault** to find the exact paragraphs from your document that answer your question.
* **The AI Brain thinks:** The Traffic Cop gives your question *and* the relevant paragraphs to the **AI Brain**. The Brain reads them and formulates a helpful, easy-to-read answer.
* **You get the answer:** The Traffic Cop sends the AI's answer back to your screen, along with exactly where it found the information in your document.

### 3. When You Upload an Excel/CSV file (Tabular Data)
* **The system gets to work immediately:** Instead of just saving it for chatting, the **Hard Worker** automatically starts analyzing the numbers.
* **It finds insights:** It figures out the trends, creates beautiful charts, and writes an easy-to-read summary of what the data means.
* **Result:** You automatically get a dashboard full of charts and a complete report, without having to ask!

---

## The Most Important Thing: Your Privacy (The Security Guard)

The biggest feature of this system is that **it is completely isolated from the internet.** 

Imagine AEGIS as a high-security room without any doors or windows to the outside world. 
* **No Cloud:** Your documents are never sent to Google, Microsoft, or ChatGPT. 
* **The Security Guard (Sentinel):** There is a dedicated monitor whose *only job* is to constantly check that the system is completely disconnected from the outside internet. If it ever detects a "leak", it raises an alarm.
* **The Vault:** Even if someone somehow stole the physical hard drive from the computer, your documents are locked inside a **Secure Vault** (encrypted). Without the digital "key," it looks like random gibberish.

**In summary:** You are working with a highly intelligent assistant that lives entirely inside your computer. Whatever you tell it, stays strictly between you and the computer.
