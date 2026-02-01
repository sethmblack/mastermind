import type { WSEvent, WSEventType } from '@/types';

type EventCallback = (event: WSEvent) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: number | null = null;
  private listeners: Map<WSEventType | '*', Set<EventCallback>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: number | null = null;

  connect(sessionId: number): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN && this.sessionId === sessionId) {
        resolve();
        return;
      }

      this.disconnect();
      this.sessionId = sessionId;

      // Use Vite proxy for WebSocket (proxied to backend port 8000)
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/chat/${sessionId}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log(`WebSocket connected to session ${sessionId}`);
        this.reconnectAttempts = 0;
        this.startHeartbeat();
        resolve();
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.stopHeartbeat();
        this.emit({ type: 'disconnected', data: { code: event.code, reason: event.reason }, timestamp: new Date().toISOString() });

        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onmessage = (event) => {
        try {
          const wsEvent: WSEvent = JSON.parse(event.data);
          this.emit(wsEvent);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
    });
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
    this.reconnectAttempts = 0;
  }

  private scheduleReconnect(): void {
    if (this.sessionId === null) return;

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

    setTimeout(() => {
      if (this.sessionId !== null) {
        this.connect(this.sessionId).catch(console.error);
      }
    }, delay);
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'heartbeat', data: {} });
      }
    }, 30000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  send(message: { type: string; data: Record<string, unknown> }): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  // Event methods
  sendUserMessage(content: string): void {
    this.send({ type: 'user_message', data: { content } });
  }

  startDiscussion(): void {
    this.send({ type: 'start_discussion', data: {} });
  }

  pauseDiscussion(): void {
    this.send({ type: 'pause_discussion', data: {} });
  }

  resumeDiscussion(): void {
    this.send({ type: 'resume_discussion', data: {} });
  }

  stopDiscussion(): void {
    this.send({ type: 'stop_discussion', data: {} });
  }

  changePhase(phase: string): void {
    this.send({ type: 'change_phase', data: { phase } });
  }

  requestVote(proposal: string): void {
    this.send({ type: 'vote_request', data: { proposal } });
  }

  // Listener management
  on(eventType: WSEventType | '*', callback: EventCallback): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  off(eventType: WSEventType | '*', callback: EventCallback): void {
    this.listeners.get(eventType)?.delete(callback);
  }

  private emit(event: WSEvent): void {
    // Emit to specific listeners
    this.listeners.get(event.type)?.forEach((callback) => callback(event));
    // Emit to wildcard listeners
    this.listeners.get('*')?.forEach((callback) => callback(event));
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get currentSessionId(): number | null {
    return this.sessionId;
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();
