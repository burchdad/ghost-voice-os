// Voice Core - Main Export
// All exports for the voice-core package
// Platform-agnostic, zero GhostCRM dependencies

export * from './types';
export * from './VoicePersonaEngine';
export * from './customVoiceHelper';

// Re-export main classes for convenience
export { VoicePersonaEngine, VoiceHealthAnalyzer } from './VoicePersonaEngine';
export { createVoiceHelper } from './customVoiceHelper';
