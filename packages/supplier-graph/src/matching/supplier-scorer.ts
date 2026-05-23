import { Supplier } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('supplier:scorer');

export interface SupplierScoring {
  supplier_id: string;
  overall_score: number;
  quality_component: number;
  reliability_component: number;
  cost_component: number;
  innovation_component: number;
  sustainability_component: number;
  recommendation: 'preferred' | 'qualified' | 'conditional' | 'not_recommended';
}

export class SupplierScorer {
  scoreSupplier(supplier: Supplier): SupplierScoring {
    logger.debug({ supplierId: supplier.id }, 'Scoring supplier');

    const qualityScore = supplier.quality_score;
    const reliabilityScore = supplier.on_time_delivery_rate;
    const costScore = this.calculateCostScore(supplier);
    const innovationScore = this.calculateInnovationScore(supplier);
    const sustainabilityScore = this.calculateSustainabilityScore(supplier);

    // Weighted average
    const overallScore =
      qualityScore * 0.3 +
      reliabilityScore * 0.25 +
      costScore * 0.2 +
      innovationScore * 0.15 +
      sustainabilityScore * 0.1;

    const recommendation = this.getRecommendation(overallScore, qualityScore, reliabilityScore);

    return {
      supplier_id: supplier.id,
      overall_score: Math.round(overallScore),
      quality_component: qualityScore,
      reliability_component: reliabilityScore,
      cost_component: costScore,
      innovation_component: innovationScore,
      sustainability_component: sustainabilityScore,
      recommendation,
    };
  }

  private calculateCostScore(supplier: Supplier): number {
    // Scoring based on cost competitiveness
    // Higher score means more cost-competitive

    const baseScore = supplier.cost_competitiveness_score;

    // Volume discounts improve score
    if (supplier.minimum_order_value && supplier.minimum_order_value < 1000) {
      return baseScore + 10;
    }

    return baseScore;
  }

  private calculateInnovationScore(supplier: Supplier): number {
    // Scoring based on innovation capacity
    // Check for advanced capabilities and certifications

    let score = 50;

    const advancedCerts = supplier.certifications.filter(
      (c) =>
        c.includes('ISO') ||
        c.includes('AS9100') ||
        c.includes('NADCAP') ||
        c.includes('TS16949') ||
        c.includes('IATF')
    );

    score += advancedCerts.length * 10;

    // Higher number of capabilities suggests innovation
    score += Math.min(20, supplier.capabilities.length * 2);

    return Math.min(100, score);
  }

  private calculateSustainabilityScore(supplier: Supplier): number {
    // Scoring based on sustainability practices

    let score = 50;

    const sustainabilityCerts = supplier.certifications.filter(
      (c) =>
        c.includes('ISO 14001') ||
        c.includes('EMAS') ||
        c.includes('carbon') ||
        c.includes('RoHS') ||
        c.includes('REACH')
    );

    score += sustainabilityCerts.length * 15;

    return Math.min(100, score);
  }

  private getRecommendation(
    overall: number,
    quality: number,
    reliability: number
  ): 'preferred' | 'qualified' | 'conditional' | 'not_recommended' {
    if (overall >= 85 && quality >= 85 && reliability >= 90) {
      return 'preferred';
    }

    if (overall >= 75 && quality >= 75 && reliability >= 80) {
      return 'qualified';
    }

    if (overall >= 60 && quality >= 60) {
      return 'conditional';
    }

    return 'not_recommended';
  }

  rankSuppliers(suppliers: Supplier[]): SupplierScoring[] {
    return suppliers
      .map((s) => this.scoreSupplier(s))
      .sort((a, b) => b.overall_score - a.overall_score);
  }
}
