/**
 * Voice OS Client SDK
 * Official TypeScript SDK for Ghost Voice OS
 * 
 * Usage:
 * ```ts
 * const voiceClient = new VoiceOSClient({
 *   baseUrl: 'https://voice.ghostcrm.ai',
 *   tenantId: 'ghostcrm'
 * });
 * 
 * const audio = await voiceClient.synthesize({
 *   text: 'Hello world',
 *   voiceId: 'sarah'
 * });
 * ```
 */

export interface VoiceOSClientConfig {
  baseUrl: string;
  tenantId: string;
  apiKey?: string;
  timeout?: number;
}

export interface SynthesizeOptions {
  text: string;
  voiceId?: string;
  voiceType?: 'primary' | 'sales' | 'support' | 'spanish' | 'custom';
  language?: string;
}

export interface TenantInfo {
  tenant_id: string;
  name: string;
  branding: Record<string, any>;
  providers: Record<string, string>;
  features: Record<string, boolean>;
}

export interface ServiceInfo {
  name: string;
  version: string;
  description: string;
  available_tenants: string[];
}

export interface SynthesisResponse {
  audioUrl?: string;
  fallbackText?: string;
  error?: string;
  voiceType?: string;
  isCustomVoice?: boolean;
}

export interface UploadVoiceOptions {
  file: File;
  voiceName: string;
  voiceType?: 'primary' | 'sales' | 'support' | 'spanish' | 'custom';
}

export class VoiceOSClient {
  private baseUrl: string;
  private tenantId: string;
  private apiKey?: string;
  private timeout: number;

  constructor(config: VoiceOSClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.tenantId = config.tenantId;
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
  }

  /**
   * Synthesize text to speech
   */
  async synthesize(options: SynthesizeOptions): Promise<ArrayBuffer> {
    const url = `${this.baseUrl}/v1/voice/synthesize`;

    const response = await this._fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: options.text,
        voice_id: options.voiceId || 'sarah',
        voice_type: options.voiceType || 'primary',
        language: options.language || 'en-US',
      }),
    });

    if (!response.ok) {
      throw new Error(`Synthesis failed: ${response.statusText}`);
    }

    return await response.arrayBuffer();
  }

  /**
   * Synthesize using custom tenant voice
   */
  async synthesizeCustomVoice(options: SynthesizeOptions): Promise<ArrayBuffer> {
    const url = `${this.baseUrl}/v1/voice/synthesize-custom`;

    const response = await this._fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: options.text,
        voice_id: options.voiceId || 'sarah',
        voice_type: options.voiceType || 'primary',
        language: options.language || 'en-US',
      }),
    });

    if (!response.ok) {
      throw new Error(`Custom voice synthesis failed: ${response.statusText}`);
    }

    return await response.arrayBuffer();
  }

  /**
   * Upload custom voice file
   */
  async uploadVoice(options: UploadVoiceOptions): Promise<{ success: boolean; url: string }> {
    const formData = new FormData();
    formData.append('voice', options.file);
    formData.append('voiceName', options.voiceName);
    formData.append('voiceType', options.voiceType || 'primary');

    const response = await this._fetch(`${this.baseUrl}/v1/voice/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Get service info
   */
  async getServiceInfo(): Promise<ServiceInfo> {
    const response = await this._fetch(`${this.baseUrl}/v1/info`);

    if (!response.ok) {
      throw new Error(`Failed to get service info: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Get tenant information
   */
  async getTenantInfo(tenantId?: string): Promise<TenantInfo> {
    const tid = tenantId || this.tenantId;
    const response = await this._fetch(`${this.baseUrl}/v1/tenants/${tid}`);

    if (!response.ok) {
      throw new Error(`Failed to get tenant info: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * List all available tenants
   */
  async listTenants(): Promise<{ tenants: string[] }> {
    const response = await this._fetch(`${this.baseUrl}/v1/tenants`);

    if (!response.ok) {
      throw new Error(`Failed to list tenants: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    const response = await this._fetch(`${this.baseUrl}/health`);

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Initiate an AI call
   */
  async initiateCall(phoneNumber: string, script: string): Promise<{ callId: string; status: string }> {
    const response = await this._fetch(`${this.baseUrl}/v1/calls/initiate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        to: phoneNumber,
        script: script,
      }),
    });

    if (!response.ok) {
      throw new Error(`Call initiation failed: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Internal fetch wrapper with tenant header and timeout
   */
  private async _fetch(url: string, options: RequestInit = {}): Promise<Response> {
    const headers = new Headers(options.headers || {});

    // Add tenant ID header
    if (!headers.has('X-Tenant-Id')) {
      headers.set('X-Tenant-Id', this.tenantId);
    }

    // Add API key if provided
    if (this.apiKey && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${this.apiKey}`);
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    // Add timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...config,
        signal: controller.signal,
      });

      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Create audio element from synthesized audio
   * Handles blob creation and URL object lifecycle
   */
  async playAudio(options: SynthesizeOptions): Promise<HTMLAudioElement> {
    const audioBuffer = await this.synthesize(options);
    const blob = new Blob([audioBuffer], { type: 'audio/mpeg' });
    const url = URL.createObjectURL(blob);

    const audio = new Audio(url);
    
    // Cleanup on end
    audio.onended = () => {
      URL.revokeObjectURL(url);
    };
    
    return audio;
  }

  /**
   * Synthesize and play audio immediately
   * Waits for playback to complete
   */
  async synthesizeAndPlay(options: SynthesizeOptions): Promise<void> {
    const audio = await this.playAudio(options);
    
    return new Promise((resolve, reject) => {
      audio.onended = () => {
        URL.revokeObjectURL(audio.src);
        resolve();
      };
      audio.onerror = () => {
        URL.revokeObjectURL(audio.src);
        reject(new Error('Audio playback failed'));
      };
      audio.play().catch(reject);
    });
  }

  /**
   * Change tenant ID
   */
  setTenantId(tenantId: string): void {
    this.tenantId = tenantId;
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<VoiceOSClientConfig>): void {
    if (config.baseUrl) {
      this.baseUrl = config.baseUrl.replace(/\/$/, '');
    }
    if (config.tenantId) {
      this.tenantId = config.tenantId;
    }
    if (config.apiKey) {
      this.apiKey = config.apiKey;
    }
    if (config.timeout) {
      this.timeout = config.timeout;
    }
  }
}

export default VoiceOSClient;

