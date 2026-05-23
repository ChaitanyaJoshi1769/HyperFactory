import { Supplier, SupplierCapability } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('supplier:matcher');

export interface CapabilityMatch {
  supplier_id: string;
  capability_id: string;
  match_score: number;
  match_reason: string;
  compatibility_score: number;
  meets_requirements: boolean;
}

export interface RequirementSpec {
  process_type: string;
  min_quality_score?: number;
  min_reliability?: number;
  required_certifications?: string[];
  max_lead_time_days?: number;
  min_capacity?: number;
  material_requirements?: string[];
  tolerance_capability_microns?: number;
  budget_max?: number;
}

export class CapabilityMatcher {
  matchCapabilities(
    suppliers: Supplier[],
    requirement: RequirementSpec
  ): CapabilityMatch[] {
    logger.debug({ requirementType: requirement.process_type }, 'Matching capabilities');

    const matches: CapabilityMatch[] = [];

    for (const supplier of suppliers) {
      for (const capability of supplier.capabilities) {
        if (this.isCapabilityRelevant(capability, requirement)) {
          const match = this.scoreMatch(supplier, capability, requirement);
          matches.push(match);
        }
      }
    }

    return matches.sort((a, b) => b.match_score - a.match_score);
  }

  private isCapabilityRelevant(capability: SupplierCapability, requirement: RequirementSpec): boolean {
    if (capability.process !== requirement.process_type && capability.type !== requirement.process_type) {
      return false;
    }

    if (
      requirement.required_certifications &&
      requirement.required_certifications.length > 0
    ) {
      const hasCerts = requirement.required_certifications.every((cert) =>
        capability.certifications.includes(cert)
      );
      if (!hasCerts) return false;
    }

    if (
      requirement.max_lead_time_days &&
      capability.lead_time_days.standard > requirement.max_lead_time_days
    ) {
      return false;
    }

    if (requirement.min_capacity && capability.max_annual_capacity < requirement.min_capacity) {
      return false;
    }

    return true;
  }

  private scoreMatch(
    supplier: Supplier,
    capability: SupplierCapability,
    requirement: RequirementSpec
  ): CapabilityMatch {
    let score = 50;
    let compatibilityScore = 50;

    // Quality score matching
    if (requirement.min_quality_score) {
      const qualityDiff = supplier.quality_score - requirement.min_quality_score;
      if (qualityDiff >= 20) score += 20;
      else if (qualityDiff >= 10) score += 10;
      else if (qualityDiff < 0) score -= 20;

      compatibilityScore += Math.min(20, supplier.quality_score / 5);
    }

    // Reliability matching
    if (requirement.min_reliability) {
      const reliabilityDiff = supplier.reliability_score - requirement.min_reliability;
      if (reliabilityDiff >= 20) score += 15;
      else if (reliabilityDiff >= 10) score += 8;
      else if (reliabilityDiff < 0) score -= 15;

      compatibilityScore += Math.min(15, supplier.on_time_delivery_rate / 7);
    }

    // Lead time scoring
    score += Math.max(0, 20 - capability.lead_time_days.standard);

    // Cost scoring
    if (requirement.budget_max && capability.cost_per_unit_base <= requirement.budget_max) {
      score += 10;
      const costPercentage = (capability.cost_per_unit_base / requirement.budget_max) * 100;
      compatibilityScore += Math.max(0, 20 - costPercentage / 5);
    }

    // Tolerance capability
    if (
      requirement.tolerance_capability_microns &&
      capability.precision_capability_microns &&
      capability.precision_capability_microns <= requirement.tolerance_capability_microns
    ) {
      score += 10;
    }

    // Material compatibility
    if (requirement.material_requirements && capability.material_capabilities) {
      const matchingMaterials = requirement.material_requirements.filter((m) =>
        capability.material_capabilities?.includes(m)
      );
      score += Math.min(10, matchingMaterials.length * 2);
    }

    const meetsRequirements =
      supplier.quality_score >= (requirement.min_quality_score || 0) &&
      supplier.reliability_score >= (requirement.min_reliability || 0);

    return {
      supplier_id: supplier.id,
      capability_id: capability.id,
      match_score: Math.min(100, Math.max(0, score)),
      match_reason: this.generateMatchReason(supplier, capability, requirement),
      compatibility_score: Math.min(100, compatibilityScore),
      meets_requirements: meetsRequirements,
    };
  }

  private generateMatchReason(
    supplier: Supplier,
    capability: SupplierCapability,
    _requirement: RequirementSpec
  ): string {
    const reasons: string[] = [];

    reasons.push(`Quality score: ${supplier.quality_score}%`);
    reasons.push(`Lead time: ${capability.lead_time_days.standard} days`);
    reasons.push(`Cost: $${capability.cost_per_unit_base.toFixed(2)}/unit`);

    if (supplier.on_time_delivery_rate > 95) {
      reasons.push('Excellent on-time delivery');
    }

    if (capability.certifications.length > 0) {
      reasons.push(`Certified: ${capability.certifications.join(', ')}`);
    }

    return reasons.join(' | ');
  }
}
