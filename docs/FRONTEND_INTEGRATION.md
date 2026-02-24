# Frontend Chat Integration Guide

This document explains how to connect a frontend application to the Ithaka chat API using the AG-UI protocol over WebSockets.

## Overview

The chat API follows a two-step flow:

1. **Initialize** a conversation via a REST call to get a JWT token.
2. **Connect** to the WebSocket using that token, then exchange messages as JSON frames following the AG-UI event protocol.

All messages (user and assistant) are persisted server-side. The JWT ensures that each WebSocket connection is scoped to a single conversation.

```
Frontend                          Backend
  │                                  │
  │  POST /api/v1/conversations/init │
  │ ──────────────────────────────►  │
  │  { token, conversationId }       │
  │ ◄──────────────────────────────  │
  │                                  │
  │  WS /api/v1/ws?token=<jwt>       │
  │ ◄══════════════════════════════► │
  │                                  │
  │  {"message": "Hola"}    ──────►  │
  │  ◄────── RUN_STARTED             │
  │  ◄────── TEXT_MESSAGE_START      │
  │  ◄────── TEXT_MESSAGE_CONTENT    │
  │  ◄────── TEXT_MESSAGE_END        │
  │  ◄────── STATE_SNAPSHOT          │
  │  ◄────── RUN_FINISHED            │
```

---

## Step 1 -- Initialize a Conversation

**Endpoint:** `POST /api/v1/conversations/init`

**Request body** (JSON, all fields optional):

```json
{
  "email": "user@example.com"
}
```

Or send an empty body `{}` if you don't have the user's email yet.

**Response** (`200 OK`):

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "conversationId": 42
}
```

| Field            | Type     | Description                                     |
|------------------|----------|-------------------------------------------------|
| `token`          | `string` | JWT valid for 60 minutes (configurable)         |
| `conversationId` | `number` | Integer ID of the conversation in the database  |

Store both values. The `token` is needed to open the WebSocket. The `conversationId` can be displayed or used for other REST calls.

### Example (fetch)

```js
const res = await fetch("http://localhost:8000/api/v1/conversations/init", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@example.com" }),
});
const { token, conversationId } = await res.json();
```

---

## Step 2 -- Connect via WebSocket

**URL:** `ws://localhost:8000/api/v1/ws?token=<JWT>`

The token is passed as a query parameter. The server validates it on connection and extracts the `conversationId`. If the token is expired or invalid the WebSocket handshake is rejected.

### Example (vanilla JS)

```js
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws?token=${token}`);

ws.onopen = () => {
  console.log("Connected to chat");
};

ws.onmessage = (event) => {
  const agEvent = JSON.parse(event.data);
  handleAgUiEvent(agEvent);
};

ws.onclose = () => {
  console.log("Disconnected");
};
```

---

## Step 3 -- Send Messages

Send a JSON text frame with the user's message:

```json
{
  "message": "Hola, quiero saber sobre los programas de ITHAKA"
}
```

### Optional: Wizard State

If the conversation is inside the wizard flow, include the wizard state so the backend can resume from the correct question:

```json
{
  "message": "Juan Perez",
  "wizard_state": {
    "wizard_session_id": "abc-123",
    "current_question": 3,
    "wizard_responses": { "1": "Juan", "2": "juan@mail.com" },
    "wizard_state": "ACTIVE",
    "awaiting_answer": true
  }
}
```

---

## Step 4 -- Handle AG-UI Events

Each response from the server is a JSON object with a `type` field. Events arrive in a deterministic sequence for each user message:

### Event Sequence

```
RUN_STARTED
TEXT_MESSAGE_START
TEXT_MESSAGE_CONTENT   (one or more)
TEXT_MESSAGE_END
STATE_SNAPSHOT         (optional, only when there is state to report)
RUN_FINISHED
```

On error the sequence is:

```
RUN_STARTED
RUN_ERROR
RUN_FINISHED
```

### Event Reference

#### `RUN_STARTED`

A new processing run has begun.

```json
{
  "type": "RUN_STARTED",
  "threadId": "42",
  "runId": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

Use this to show a loading indicator.

#### `TEXT_MESSAGE_START`

The assistant is about to send a message.

```json
{
  "type": "TEXT_MESSAGE_START",
  "messageId": "a1b2c3d4-...",
  "role": "assistant"
}
```

Create a new message bubble in the UI.

#### `TEXT_MESSAGE_CONTENT`

A chunk of the assistant's response. Append `delta` to the current message.

```json
{
  "type": "TEXT_MESSAGE_CONTENT",
  "messageId": "a1b2c3d4-...",
  "delta": "Hola! ITHAKA es el centro de emprendimiento..."
}
```

Currently the full response arrives in a single `delta`. In the future this may be streamed in smaller chunks for real-time typing effects.

#### `TEXT_MESSAGE_END`

The assistant's message is complete.

```json
{
  "type": "TEXT_MESSAGE_END",
  "messageId": "a1b2c3d4-..."
}
```

Hide the loading/typing indicator.

#### `STATE_SNAPSHOT`

Application state update. Contains wizard progress and which agent handled the request.

```json
{
  "type": "STATE_SNAPSHOT",
  "snapshot": {
    "agent_used": "faq",
    "wizard_state": "ACTIVE",
    "current_question": 3,
    "wizard_responses": { "1": "Juan", "2": "juan@mail.com" },
    "awaiting_answer": true,
    "wizard_session_id": "abc-123"
  }
}
```

| Field               | Type      | Description                                         |
|---------------------|-----------|-----------------------------------------------------|
| `agent_used`        | `string`  | Which agent handled the message (`faq`, `wizard`, `validator`, etc.) |
| `wizard_state`      | `string`  | `"ACTIVE"`, `"COMPLETED"`, or absent if not in wizard flow |
| `current_question`  | `number`  | Current wizard question number (1-20)               |
| `wizard_responses`  | `object`  | Map of question number to user answer               |
| `awaiting_answer`   | `boolean` | Whether the wizard is waiting for the user's answer |
| `wizard_session_id` | `string`  | Session ID for the wizard flow                      |

Use this to update progress bars, show/hide wizard UI, or store state locally to send back with the next message.

#### `RUN_ERROR`

An error occurred during processing.

```json
{
  "type": "RUN_ERROR",
  "message": "Error description",
  "code": "INTERNAL_ERROR"
}
```

| Code             | Meaning                          |
|------------------|----------------------------------|
| `BAD_REQUEST`    | Invalid JSON or empty message    |
| `INTERNAL_ERROR` | Server-side processing failure   |

#### `RUN_FINISHED`

The run is complete. Always the last event in a sequence.

```json
{
  "type": "RUN_FINISHED",
  "threadId": "42",
  "runId": "f47ac10b-..."
}
```

---

## Complete React Example

```tsx
import { useState, useRef, useCallback, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const API_BASE = "http://localhost:8000/api/v1";

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const bufferRef = useRef<{ id: string; content: string } | null>(null);

  // Initialize conversation and connect WebSocket
  const connect = useCallback(async () => {
    const res = await fetch(`${API_BASE}/conversations/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const { token } = await res.json();

    const ws = new WebSocket(
      `${API_BASE.replace("http", "ws")}/ws?token=${token}`
    );

    ws.onmessage = (event) => {
      const e = JSON.parse(event.data);

      switch (e.type) {
        case "RUN_STARTED":
          setIsLoading(true);
          break;

        case "TEXT_MESSAGE_START":
          bufferRef.current = { id: e.messageId, content: "" };
          break;

        case "TEXT_MESSAGE_CONTENT":
          if (bufferRef.current) {
            bufferRef.current.content += e.delta;
          }
          break;

        case "TEXT_MESSAGE_END":
          if (bufferRef.current) {
            const msg = bufferRef.current;
            setMessages((prev) => [
              ...prev,
              { id: msg.id, role: "assistant", content: msg.content },
            ]);
            bufferRef.current = null;
          }
          break;

        case "RUN_FINISHED":
          setIsLoading(false);
          break;

        case "RUN_ERROR":
          console.error("Chat error:", e.message);
          setIsLoading(false);
          break;
      }
    };

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  const send = () => {
    if (!input.trim() || !wsRef.current) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
    };
    setMessages((prev) => [...prev, userMsg]);
    wsRef.current.send(JSON.stringify({ message: input }));
    setInput("");
  };

  return (
    <div>
      <div>
        {messages.map((m) => (
          <div key={m.id} style={{ textAlign: m.role === "user" ? "right" : "left" }}>
            <strong>{m.role}:</strong> {m.content}
          </div>
        ))}
        {isLoading && <div>Typing...</div>}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && send()}
        placeholder="Escribe un mensaje..."
      />
      <button onClick={send} disabled={isLoading}>
        Enviar
      </button>
    </div>
  );
}
```

---

## Token Expiration

The JWT is valid for **60 minutes** by default. If the token expires while the WebSocket is open, the connection stays alive. However, if the connection drops and the frontend tries to reconnect with an expired token, the handshake will be rejected.

**Recommended strategy:** call `/conversations/init` again to get a fresh token when reconnecting, or before the token expires. You can decode the JWT client-side to read the `exp` claim and schedule a refresh.

---

## CORS

The backend allows requests from `http://localhost:3000` and `http://localhost:3001` by default. If your frontend runs on a different origin, the backend CORS config in `app/main.py` needs to be updated.
