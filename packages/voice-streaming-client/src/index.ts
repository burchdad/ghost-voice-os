/**
 * Streaming Voice Client
 * Real-time bidirectional audio communication with Ghost Voice OS
 */

export interface StreamingConfig {
  /** WebSocket endpoint URL (e.g., ws://localhost:8000/v1/stream/ws/call/:sessionId) */
  wsUrl: string;
  
  /** Audio sample rate (default: 16000) */
  sampleRate?: number;
  
  /** Audio encoding (default: PCM) */
  encoding?: "PCM" | "OPUS";
  
  /** Chunk size for audio streaming (default: 20480) */
  chunkSize?: number;
  
  /** Enable automatic reconnection */
  autoReconnect?: boolean;
  
  /** Max reconnection attempts */
  maxReconnectAttempts?: number;
}

export interface StreamMessage {
  type: "audio" | "transcript" | "metadata" | "error" | "control";
  [key: string]: any;
}

export interface AudioChunk {
  type: "audio";
  data: string; // base64 encoded audio
  duration_ms: number;
}

export interface TranscriptMessage {
  type: "transcript";
  text: string;
  is_final: boolean;
  confidence: number;
}

export interface ErrorMessage {
  type: "error";
  error: string;
  phase?: string;
}

/**
 * Streaming Voice Client
 * Handles WebSocket connection, audio I/O, and message routing
 */
export class StreamingVoiceClient {
  private ws: WebSocket | null = null;
  private config: Required<StreamingConfig>;
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private isConnected = false;
  private reconnectAttempts = 0;
  private audioQueue: Uint8Array[] = [];
  private processingAudio = false;

  private listeners: Map<string, Set<Function>> = new Map();

  constructor(config: StreamingConfig) {
    this.config = {
      sampleRate: 16000,
      encoding: "PCM",
      chunkSize: 20480,
      autoReconnect: true,
      maxReconnectAttempts: 5,
      ...config,
    };
  }

  /**
   * Connect to the streaming server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.wsUrl);

        this.ws.onopen = () => {
          console.log("✅ Connected to streaming server");
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.emit("connected");
          resolve();
        };

        this.ws.onmessage = (event: MessageEvent) => {
          this.handleMessage(event.data);
        };

        this.ws.onerror = (error) => {
          console.error("❌ WebSocket error:", error);
          this.emit("error", error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log("🔌 Disconnected from server");
          this.isConnected = false;
          this.emit("disconnected");

          if (this.config.autoReconnect && this.reconnectAttempts < this.config.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect().catch(console.error), delay);
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Start recording audio from microphone
   */
  async startRecording(): Promise<void> {
    try {
      // Get user's microphone
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: this.config.sampleRate,
        },
      });

      // Create audio context
      this.audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)();

      // Create media recorder
      const mimeType = "audio/webm";
      const options = {
        mimeType,
        audioBitsPerSecond: 128000,
      };

      this.mediaRecorder = new MediaRecorder(this.mediaStream, options);

      // Send audio chunks as they arrive
      this.mediaRecorder.ondataavailable = async (event: BlobEvent) => {
        if (event.data.size > 0) {
          await this.sendAudioChunk(event.data);
        }
      };

      // Start recording with 100ms chunks
      this.mediaRecorder.start(100);

      console.log("🎤 Recording started");
      this.emit("recording_started");
    } catch (error) {
      console.error("❌ Failed to start recording:", error);
      this.emit("error", error);
      throw error;
    }
  }

  /**
   * Stop recording audio
   */
  stopRecording(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
      console.log("⏹️  Recording stopped");
      this.emit("recording_stopped");
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  /**
   * Send audio chunk to server
   */
  private async sendAudioChunk(blob: Blob): Promise<void> {
    if (!this.isConnected || !this.ws) {
      console.warn("⚠️  Not connected, dropping audio chunk");
      return;
    }

    try {
      const arrayBuffer = await blob.arrayBuffer();
      const base64Data = this.arrayBufferToBase64(arrayBuffer);

      this.ws.send(
        JSON.stringify({
          type: "audio",
          data: base64Data,
        })
      );

      console.debug(`📤 Sent ${blob.size} bytes of audio`);
    } catch (error) {
      console.error("Error sending audio chunk:", error);
    }
  }

  /**
   * Handle incoming message from server
   */
  private handleMessage(data: string): void {
    try {
      const message: StreamMessage = JSON.parse(data);

      switch (message.type) {
        case "audio": {
          this.handleAudioChunk(message as AudioChunk);
          break;
        }
        case "transcript": {
          this.emit("transcript", message as TranscriptMessage);
          break;
        }
        case "error": {
          console.error("🔴 Server error:", (message as ErrorMessage).error);
          this.emit("error", message);
          break;
        }
        case "metadata": {
          this.emit("metadata", message);
          break;
        }
        default: {
          console.warn("Unknown message type:", message.type);
        }
      }
    } catch (error) {
      console.error("Error handling message:", error);
    }
  }

  /**
   * Handle incoming audio chunk
   */
  private async handleAudioChunk(message: AudioChunk): Promise<void> {
    try {
      const binaryString = atob(message.data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Queue for playback
      this.audioQueue.push(bytes);

      // Start playback if not already processing
      if (!this.processingAudio) {
        await this.playAudioQueue();
      }

      console.debug(`📥 Received audio: ${message.duration_ms}ms`);
    } catch (error) {
      console.error("Error handling audio chunk:", error);
    }
  }

  /**
   * Play queued audio chunks
   */
  private async playAudioQueue(): Promise<void> {
    if (!this.audioContext || this.audioQueue.length === 0) {
      return;
    }

    this.processingAudio = true;

    try {
      while (this.audioQueue.length > 0) {
        const chunk = this.audioQueue.shift();
        if (chunk) {
          await this.playAudioBuffer(chunk);
        }
      }
    } finally {
      this.processingAudio = false;
    }
  }

  /**
   * Play a single audio buffer
   */
  private playAudioBuffer(audioData: Uint8Array): Promise<void> {
    return new Promise((resolve) => {
      if (!this.audioContext) {
        resolve();
        return;
      }

      try {
        // Decode audio data (assuming PCM 16-bit)
        const pcmData = this.decodePCM16(audioData);
        const audioBuffer = this.audioContext.createBuffer(
          1,
          pcmData.length,
          this.config.sampleRate
        );

        audioBuffer.getChannelData(0).set(pcmData);

        // Create and play source
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;

        source.connect(this.audioContext.destination);
        source.onended = () => resolve();

        source.start(0);
      } catch (error) {
        console.error("Error playing audio buffer:", error);
        resolve();
      }
    });
  }

  /**
   * Decode PCM 16-bit audio
   */
  private decodePCM16(data: Uint8Array): Float32Array {
    const pcmData = new Float32Array(data.length / 2);
    let index = 0;

    for (let i = 0; i < data.length; i += 2) {
      const s = ((data[i + 1] << 8) | data[i]) << 16) >> 16;
      pcmData[index++] = s < 0 ? s / 0x8000 : s / 0x7fff;
    }

    return pcmData;
  }

  /**
   * Send control command to server
   */
  sendControl(command: string): void {
    if (!this.isConnected || !this.ws) {
      console.warn("Not connected");
      return;
    }

    this.ws.send(
      JSON.stringify({
        type: "control",
        command,
      })
    );
  }

  /**
   * Stop the call and disconnect
   */
  async stop(): Promise<void> {
    this.stopRecording();
    this.sendControl("stop");

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
  }

  /**
   * Subscribe to events
   */
  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  /**
   * Unsubscribe from events
   */
  off(event: string, callback: Function): void {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.delete(callback);
    }
  }

  /**
   * Emit event
   */
  private emit(event: string, data?: any): void {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.forEach((callback) => callback(data));
    }
  }

  /**
   * Convert ArrayBuffer to Base64
   */
  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * Check if connected
   */
  get connected(): boolean {
    return this.isConnected;
  }
}

// Export for use
export default StreamingVoiceClient;
