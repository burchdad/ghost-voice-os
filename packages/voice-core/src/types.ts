// Voice Core Type Definitions
// Platform-agnostic types for white-label Voice OS

export interface VoicePersona {
  id: string;
  name: string;
  description: string;
  voiceId: string;
  tenantId: string;
  
  // Persona Configuration
  label: string;
  tonePreset: 'friendly' | 'authoritative' | 'empathetic' | 'playful' | 'professional' | 'urgent';
  emotionalRange: {
    warmth: number;
    authority: number;
    empathy: number;
    energy: number;
  };
  
  // Use Case Mapping
  useCases: Array<'outbound_reminder' | 'inbound_support' | 'post_sale_checkin' | 
                  'collections' | 'onboarding' | 'vip_calls' | 'emergency'>;
  
  // Context Rules
  contextRules: {
    timeOfDay?: Array<'morning' | 'afternoon' | 'evening'>;
    callType?: Array<'cold_outbound' | 'warm_follow_up' | 'customer_service' | 'sales_close'>;
    customerSegment?: Array<'vip' | 'new_lead' | 'existing_customer' | 'past_due'>;
    department?: Array<'sales' | 'support' | 'collections' | 'onboarding'>;
    language?: Array<'en' | 'es' | 'fr'>;
  };
  
  // Voice Health Scoring
  healthScore: {
    clarity: number;
    consistency: number;
    emotionalRange: number;
    noiseLevel: number;
    overall: number;
    lastAnalyzed: string;
    recommendations: string[];
  };
  
  // Performance Analytics
  analytics: {
    totalCalls: number;
    completionRate: number;
    avgCallDuration: number;
    customerSatisfactionScore: number;
    conversionRate: number;
    hangupRate: number;
  };
  
  // Brand Safety & Compliance
  brandSafety: {
    approved: boolean;
    approvedBy?: string;
    approvedAt?: string;
    contentFilters: Array<'harassment' | 'threats' | 'inappropriate' | 'compliance'>;
    lastReview: string;
  };
  
  // Training & Optimization
  training: {
    phoneticCoverage: number;
    sampleCount: number;
    suggestedImprovements: string[];
    nextTrainingRecommended: string;
  };
  
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface VoicePersonaRule {
  id: string;
  personaId: string;
  priority: number;
  conditions: {
    timeRange?: { start: string; end: string };
    dayOfWeek?: Array<'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday'>;
    callType?: string;
    customerTags?: string[];
    leadSource?: string;
    callAttempt?: number;
    previousCallOutcome?: 'answered' | 'voicemail' | 'no_answer' | 'busy';
  };
  action: {
    usePersona: string;
    escalationTrigger?: 'key_moment' | 'customer_objection' | 'closing_attempt';
    contextMessage?: string;
  };
}

export interface VoiceConfig {
  tenantId: string;
  voiceType: 'primary' | 'sales' | 'support' | 'spanish' | 'custom';
  language?: string;
}

export interface SynthesisResult {
  audioUrl?: string;
  fallbackText?: string;
  error?: string;
  voiceType?: string;
  isCustomVoice?: boolean;
}

export interface VoiceHelperConfig {
  baseUrl: string;
  tenantId: string;
  apiKey?: string;
  endpoint?: string;
}

export interface PersonaSelectionContext {
  callType: string;
  customerSegment: string;
  timeOfDay: string;
  department: string;
  language: string;
  callAttempt: number;
  customerHistory?: any;
  isVIP?: boolean;
}

export interface CallEvent {
  type: 'key_moment' | 'objection_handling' | 'closing_attempt' | 'complaint_escalation';
  customerResponse?: string;
  callDuration?: number;
}
