// Voice Persona Engine - Platform Agnostic
// Handles smart voice selection and context-aware switching
// Zero dependencies on GhostCRM or any specific platform

import type {
  VoicePersona,
  VoicePersonaRule,
  PersonaSelectionContext,
  CallEvent
} from './types';

export class VoicePersonaEngine {
  private personas: VoicePersona[] = [];
  private rules: VoicePersonaRule[] = [];
  private tenantId: string;

  constructor(tenantId: string, personas: VoicePersona[] = [], rules: VoicePersonaRule[] = []) {
    this.tenantId = tenantId;
    this.personas = personas;
    this.rules = rules;
  }

  /**
   * Add a persona to the engine
   */
  addPersona(persona: VoicePersona): void {
    this.personas.push(persona);
  }

  /**
   * Add a selection rule
   */
  addRule(rule: VoicePersonaRule): void {
    this.rules.push(rule);
  }

  /**
   * Update personas and rules from external source
   */
  updateFromConfig(personas: VoicePersona[], rules: VoicePersonaRule[]): void {
    this.personas = personas;
    this.rules = rules;
  }

  /**
   * Select the best persona for a given call context
   */
  selectPersona(context: PersonaSelectionContext): VoicePersona | null {
    // Apply rules in priority order
    const applicableRules = this.rules
      .filter((rule) => this.ruleMatches(rule, context))
      .sort((a, b) => b.priority - a.priority);

    if (applicableRules.length > 0) {
      const selectedRule = applicableRules[0];
      const persona = this.personas.find((p) => p.id === selectedRule.action.usePersona);
      if (persona) {
        console.log(`✅ [PERSONA ENGINE] Selected "${persona.name}" via rule: ${selectedRule.id}`);
        return persona;
      }
    }

    // Fallback to best matching persona
    const bestPersona = this.findBestMatchingPersona(context);
    if (bestPersona) {
      console.log(`✅ [PERSONA ENGINE] Selected "${bestPersona.name}" via scoring`);
    }
    return bestPersona;
  }

  /**
   * Context-aware voice switching during call
   */
  shouldSwitchVoice(currentPersona: VoicePersona, callEvent: CallEvent): VoicePersona | null {
    // Switch to authoritative voice for key moments
    if (callEvent.type === 'key_moment' || callEvent.type === 'complaint_escalation') {
      const ownerPersona = this.personas.find(
        (p) => p.tonePreset === 'authoritative' && p.useCases.includes('vip_calls')
      );
      if (ownerPersona && ownerPersona.id !== currentPersona.id) {
        console.log(`🔄 [PERSONA ENGINE] Switching from "${currentPersona.name}" to "${ownerPersona.name}" for key moment`);
        return ownerPersona;
      }
    }

    // Switch to empathetic voice for objection handling
    if (callEvent.type === 'objection_handling') {
      const empathyPersona = this.personas.find(
        (p) => p.tonePreset === 'empathetic' && p.useCases.includes('inbound_support')
      );
      if (empathyPersona && empathyPersona.id !== currentPersona.id) {
        console.log(`🔄 [PERSONA ENGINE] Switching from "${currentPersona.name}" to "${empathyPersona.name}" for objection handling`);
        return empathyPersona;
      }
    }

    // Switch to urgent voice for closing
    if (callEvent.type === 'closing_attempt') {
      const urgentPersona = this.personas.find(
        (p) => p.tonePreset === 'urgent' && p.useCases.includes('collections')
      );
      if (urgentPersona && urgentPersona.id !== currentPersona.id) {
        console.log(`🔄 [PERSONA ENGINE] Switching from "${currentPersona.name}" to "${urgentPersona.name}" for closing`);
        return urgentPersona;
      }
    }

    return null;
  }

  /**
   * Get all active personas for a tenant
   */
  getActivePersonas(): VoicePersona[] {
    return this.personas.filter((p) => p.isActive && p.brandSafety.approved);
  }

  /**
   * Get persona by ID
   */
  getPersonaById(id: string): VoicePersona | null {
    return this.personas.find((p) => p.id === id) || null;
  }

  /**
   * Get personas by use case
   */
  getPersonasByUseCase(useCase: VoicePersona['useCases'][number]): VoicePersona[] {
    return this.personas.filter((p) => p.useCases.includes(useCase));
  }

  /**
   * Score-based persona matching
   */
  private findBestMatchingPersona(context: PersonaSelectionContext): VoicePersona | null {
    let bestPersona: VoicePersona | null = null;
    let bestScore = 0;

    for (const persona of this.getActivePersonas()) {
      const score = this.scorePersonaMatch(persona, context);
      if (score > bestScore) {
        bestScore = score;
        bestPersona = persona;
      }
    }

    return bestPersona;
  }

  /**
   * Calculate relevance score for persona given context
   */
  private scorePersonaMatch(persona: VoicePersona, context: PersonaSelectionContext): number {
    let score = 0;

    // Base score from health (30%)
    score += persona.healthScore.overall * 0.3;

    // Performance score (30%)
    score += persona.analytics.completionRate * 0.3;

    // Context relevance (40%)
    if (persona.contextRules.callType?.includes(context.callType as any)) {
      score += 25;
    }
    if (persona.contextRules.customerSegment?.includes(context.customerSegment as any)) {
      score += 20;
    }
    if (persona.contextRules.department?.includes(context.department as any)) {
      score += 15;
    }
    if (persona.contextRules.language?.includes(context.language as any)) {
      score += 10;
    }

    // VIP boost
    if (context.isVIP && persona.useCases.includes('vip_calls')) {
      score += 30;
    }

    return score;
  }

  /**
   * Check if a rule matches the current context
   */
  private ruleMatches(rule: VoicePersonaRule, context: PersonaSelectionContext): boolean {
    const conditions = rule.conditions;

    // Check callType match
    if (conditions.callType && !conditions.callType.includes(context.callType)) {
      return false;
    }

    // Check customerTags match
    if (conditions.customerTags && context.customerHistory?.tags) {
      const hasTag = conditions.customerTags.some((tag) => context.customerHistory.tags.includes(tag));
      if (!hasTag) return false;
    }

    // Check callAttempt match
    if (conditions.callAttempt && conditions.callAttempt !== context.callAttempt) {
      return false;
    }

    return true;
  }
}

/**
 * Voice Health Analyzer - Platform Agnostic
 */
export class VoiceHealthAnalyzer {
  /**
   * Analyze voice sample quality
   * In production, this would use real audio analysis
   */
  static analyzeVoiceHealth(audioMetadata: {
    duration: number;
    sampleRate?: number;
    channels?: number;
  }): VoicePersona['healthScore'] {
    // Mock analysis - would integrate with real audio processing library
    const mockAnalysis: VoicePersona['healthScore'] = {
      clarity: Math.floor(Math.random() * 20) + 80,
      consistency: Math.floor(Math.random() * 15) + 85,
      emotionalRange: Math.floor(Math.random() * 30) + 70,
      noiseLevel: Math.floor(Math.random() * 10) + 90,
      overall: 0,
      lastAnalyzed: new Date().toISOString(),
      recommendations: []
    };

    // Calculate overall score (weighted)
    mockAnalysis.overall = Math.round(
      mockAnalysis.clarity * 0.3 +
      mockAnalysis.consistency * 0.3 +
      mockAnalysis.emotionalRange * 0.2 +
      mockAnalysis.noiseLevel * 0.2
    );

    // Generate recommendations
    if (mockAnalysis.clarity < 85) {
      mockAnalysis.recommendations.push('Record in a quieter environment for better clarity');
    }
    if (mockAnalysis.emotionalRange < 80) {
      mockAnalysis.recommendations.push('Try varying your tone more to increase emotional range');
    }
    if (mockAnalysis.noiseLevel < 90) {
      mockAnalysis.recommendations.push('Background noise detected. Use noise cancellation or quieter space');
    }
    if (mockAnalysis.overall >= 95) {
      mockAnalysis.recommendations.push('Excellent voice quality! This is production-ready.');
    }

    return mockAnalysis;
  }

  /**
   * Generate insights from persona performance data
   */
  static generateVoiceInsights(personas: VoicePersona[]): string[] {
    const insights: string[] = [];

    // Find best performing persona
    const bestPerformer = personas
      .filter((p) => p.analytics.totalCalls > 10)
      .sort((a, b) => b.analytics.conversionRate - a.analytics.conversionRate)[0];

    if (bestPerformer) {
      insights.push(
        `Your "${bestPerformer.name}" persona performs ${bestPerformer.analytics.conversionRate}% better on conversions than your average voice`
      );
    }

    // Analyze completion rates
    const avgCompletionRate = personas.reduce((sum, p) => sum + p.analytics.completionRate, 0) / personas.length;
    const topCompleter = personas.sort((a, b) => b.analytics.completionRate - a.analytics.completionRate)[0];

    if (topCompleter && topCompleter.analytics.completionRate > avgCompletionRate + 10) {
      insights.push(
        `Your "${topCompleter.name}" voice has ${Math.round(topCompleter.analytics.completionRate - avgCompletionRate)}% fewer hangups than your other voices`
      );
    }

    // Health score insights
    const needsImprovement = personas.filter((p) => p.healthScore.overall < 80);
    if (needsImprovement.length > 0) {
      insights.push(
        `${needsImprovement.length} voice${needsImprovement.length > 1 ? 's' : ''} could benefit from re-recording for better quality`
      );
    }

    return insights;
  }
}

export default VoicePersonaEngine;
