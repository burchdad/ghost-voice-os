// Custom Voice Helper - Platform Agnostic
// Handles voice synthesis with provider fallback strategy
// Uses dependency injection - no hardcoded URLs or GhostCRM coupling

import type { VoiceConfig, SynthesisResult, VoiceHelperConfig } from './types';

/**
 * Voice Helper Factory
 * Creates a configured helper instance with injected dependencies
 */
export function createVoiceHelper(config: VoiceHelperConfig) {
  return new VoiceHelper(config);
}

/**
 * Voice Helper - Handles synthesis with fallback chain
 * Priority: Custom Voice → ElevenLabs → TTS Fallback
 */
class VoiceHelper {
  private baseUrl: string;
  private tenantId: string;
  private apiKey?: string;
  private endpoint: string;

  constructor(config: VoiceHelperConfig) {
    this.baseUrl = config.baseUrl;
    this.tenantId = config.tenantId;
    this.apiKey = config.apiKey;
    this.endpoint = config.endpoint || '/v1/voice/synthesize';
  }

  /**
   * Generate speech using tenant's custom voice with fallback chain
   */
  async generateCustomVoiceAudio(
    text: string,
    voiceConfig: VoiceConfig
  ): Promise<SynthesisResult> {
    console.log(
      `🎯 [VOICE HELPER] Generating: "${text.substring(0, 50)}..." with voice type: ${voiceConfig.voiceType}`
    );

    try {
      // Step 1: Try custom voice synthesis
      const customResult = await this.tryCustomVoice(text, voiceConfig);
      if (customResult.audioUrl) {
        console.log(`✅ [VOICE HELPER] Success with custom voice`);
        return customResult;
      }

      // Step 2: Fall back to ElevenLabs
      console.warn(`⚠️ [VOICE HELPER] Custom voice failed, trying ElevenLabs`);
      const elevenResult = await this.tryElevenLabs(text, voiceConfig);
      if (elevenResult.audioUrl) {
        console.log(`✅ [VOICE HELPER] Success with ElevenLabs`);
        return elevenResult;
      }

      // Step 3: Fall back to text (TTS fallback)
      console.warn(`⚠️ [VOICE HELPER] ElevenLabs failed, using text fallback`);
      return {
        fallbackText: text,
        voiceType: voiceConfig.voiceType,
        isCustomVoice: false
      };
    } catch (error) {
      console.error('❌ [VOICE HELPER] Generation error:', error);
      return {
        fallbackText: text,
        error: String(error),
        voiceType: voiceConfig.voiceType
      };
    }
  }

  /**
   * Try custom voice synthesis endpoint
   */
  private async tryCustomVoice(text: string, voiceConfig: VoiceConfig): Promise<SynthesisResult> {
    try {
      const response = await fetch(`${this.baseUrl}${this.endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-Id': this.tenantId,
          ...(this.apiKey && { Authorization: `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({
          text,
          tenantId: this.tenantId,
          voiceType: voiceConfig.voiceType,
          language: voiceConfig.language || 'en-US'
        })
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const result = await response.json();
      if (result.audioUrl) {
        return {
          audioUrl: result.audioUrl,
          voiceType: result.voiceType,
          isCustomVoice: true
        };
      }

      throw new Error('No audioUrl in response');
    } catch (error) {
      console.warn(`⚠️ [VOICE HELPER] Custom voice failed: ${error}`);
      throw error;
    }
  }

  /**
   * Try ElevenLabs synthesis endpoint
   */
  private async tryElevenLabs(text: string, voiceConfig: VoiceConfig): Promise<SynthesisResult> {
    try {
      const elevenLabsVoiceId = mapVoiceTypeToElevenLabs(voiceConfig.voiceType);

      const response = await fetch(`${this.baseUrl}/v1/voice/elevenlabs/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-Id': this.tenantId,
          ...(this.apiKey && { Authorization: `Bearer ${this.apiKey}` })
        },
        body: JSON.stringify({
          text,
          voiceId: elevenLabsVoiceId,
          language: voiceConfig.language || 'en-US'
        })
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const result = await response.json();
      if (result.audioUrl) {
        return {
          audioUrl: result.audioUrl,
          voiceType: result.voiceType,
          isCustomVoice: false
        };
      }

      throw new Error('No audioUrl in response');
    } catch (error) {
      console.warn(`⚠️ [VOICE HELPER] ElevenLabs failed: ${error}`);
      throw error;
    }
  }

  /**
   * Create command for voice playback with fallback support
   */
  createVoiceCommand(audio: SynthesisResult, voiceConfig: VoiceConfig, fallbackText: string) {
    if (audio.audioUrl) {
      // Use custom or ElevenLabs audio
      const commandType = audio.isCustomVoice ? 'CUSTOM_VOICE' : 'ELEVENLABS_VOICE';
      console.log(`🔊 [VOICE COMMAND] Using ${commandType}: ${audio.audioUrl}`);

      return {
        command: 'play_audio',
        audio_url: audio.audioUrl,
        loop: 1,
        overlay: false,
        _voiceSource: audio.isCustomVoice ? 'tenant_custom' : 'elevenlabs_fallback',
        _voiceType: audio.voiceType || voiceConfig.voiceType
      };
    } else {
      // Fall back to TTS
      console.log(`🔄 [VOICE COMMAND] Using TTS fallback`);
      return {
        command: 'speak',
        text: audio.fallbackText || fallbackText,
        voice: mapVoiceTypeToTelnyxVoice(voiceConfig.voiceType),
        language: voiceConfig.language || 'en-US',
        _voiceSource: 'tts_fallback',
        _voiceType: voiceConfig.voiceType
      };
    }
  }
}

/**
 * Map voice types to ElevenLabs voice IDs
 */
function mapVoiceTypeToElevenLabs(voiceType: string): string {
  const voiceMap: Record<string, string> = {
    primary: 'sarah',
    sales: 'jessica',
    support: 'sarah',
    spanish: 'maria',
    custom: 'sarah'
  };

  return voiceMap[voiceType] || 'sarah';
}

/**
 * Map voice types to Telnyx TTS voices (final fallback)
 */
function mapVoiceTypeToTelnyxVoice(voiceType: string): string {
  const voiceMap: Record<string, string> = {
    primary: 'female',
    sales: 'female',
    support: 'female',
    spanish: 'female',
    custom: 'female'
  };

  return voiceMap[voiceType] || 'female';
}

// Legacy exports for backward compatibility (deprecated)
export const generateCustomVoiceAudio = async (
  text: string,
  voiceConfig: VoiceConfig,
  baseUrl: string = 'http://localhost:8000'
): Promise<SynthesisResult> => {
  const helper = createVoiceHelper({
    baseUrl,
    tenantId: voiceConfig.tenantId
  });
  return helper.generateCustomVoiceAudio(text, voiceConfig);
};

export const createCustomVoiceCommand = (
  audio: SynthesisResult,
  voiceConfig: VoiceConfig,
  fallbackText: string
) => {
  const helper = createVoiceHelper({
    baseUrl: 'http://localhost:8000',
    tenantId: voiceConfig.tenantId
  });
  return helper.createVoiceCommand(audio, voiceConfig, fallbackText);
};

export { mapVoiceTypeToElevenLabs, mapVoiceTypeToTelnyxVoice };
