import { Supplier } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('supplier:optimizer');

export interface OptimizationStrategy {
  supplier_id: string;
  current_usage_percent: number;
  recommended_usage_percent: number;
  lead_time_variance_reduction_percent: number;
  cost_savings_potential: number;
  risk_reduction_score: number;
  reasoning: string[];
}

export class SupplierOptimizer {
  optimizeSupplierPortfolio(
    suppliers: Supplier[],
    currentOrders: Array<{ supplierId: string; volume: number }>
  ): OptimizationStrategy[] {
    logger.debug({ supplierCount: suppliers.length }, 'Optimizing supplier portfolio');

    const strategies: OptimizationStrategy[] = [];

    const totalVolume = currentOrders.reduce((sum, order) => sum + order.volume, 0);

    for (const supplier of suppliers) {
      const currentOrder = currentOrders.find((o) => o.supplierId === supplier.id);
      const currentUsagePercent = currentOrder ? (currentOrder.volume / totalVolume) * 100 : 0;

      const recommendedUsage = this.calculateOptimalUsage(supplier, currentUsagePercent);
      const leadTimeVariance = this.estimateLeadTimeVarianceReduction(supplier);
      const costSavings = this.estimateCostSavings(supplier, currentUsagePercent, recommendedUsage);
      const riskReduction = this.calculateRiskReduction(supplier);

      const reasoning = this.generateOptimizationReasoning(
        supplier,
        currentUsagePercent,
        recommendedUsage
      );

      strategies.push({
        supplier_id: supplier.id,
        current_usage_percent: Math.round(currentUsagePercent * 100) / 100,
        recommended_usage_percent: Math.round(recommendedUsage * 100) / 100,
        lead_time_variance_reduction_percent: leadTimeVariance,
        cost_savings_potential: costSavings,
        risk_reduction_score: riskReduction,
        reasoning,
      });
    }

    return strategies.sort((a, b) => b.cost_savings_potential - a.cost_savings_potential);
  }

  private calculateOptimalUsage(supplier: Supplier, current: number): number {
    // Optimal usage depends on supplier performance and risk

    let optimal = current;

    // If supplier is highly reliable, increase usage
    if (supplier.on_time_delivery_rate > 98) {
      optimal = Math.min(50, optimal + 10);
    }

    // If supplier has low quality, decrease usage
    if (supplier.quality_score < 85) {
      optimal = Math.max(0, optimal - 15);
    }

    // Cost-competitive suppliers should get more volume
    if (supplier.cost_competitiveness_score > 80) {
      optimal = Math.min(60, optimal + 8);
    }

    // Diversify to reduce risk - cap at 40% for single supplier
    optimal = Math.min(40, optimal);

    return optimal;
  }

  private estimateLeadTimeVarianceReduction(supplier: Supplier): number {
    // Suppliers with low variance can be relied upon more
    const variance = supplier.lead_time_variability;

    if (variance < 2) return 90;
    if (variance < 5) return 70;
    if (variance < 10) return 50;
    return 20;
  }

  private estimateCostSavings(
    supplier: Supplier,
    _current: number,
    recommended: number
  ): number {
    // Cost savings from volume increases
    if (recommended > _current) {
      const volumeIncrease = recommended - _current;

      if (supplier.cost_competitiveness_score > 80) {
        return volumeIncrease * 5;
      }
      if (supplier.cost_competitiveness_score > 60) {
        return volumeIncrease * 2;
      }
    }

    return 0;
  }

  private calculateRiskReduction(supplier: Supplier): number {
    let score = 50;

    if (supplier.on_time_delivery_rate > 95) score += 20;
    if (supplier.quality_score > 90) score += 15;
    if (supplier.reliability_score > 85) score += 10;

    return Math.min(100, score);
  }

  private generateOptimizationReasoning(
    supplier: Supplier,
    _current: number,
    recommended: number
  ): string[] {
    const reasons: string[] = [];

    if (supplier.on_time_delivery_rate > 98) {
      reasons.push(`Excellent on-time delivery (${supplier.on_time_delivery_rate}%)`);
    }

    if (supplier.quality_score > 90) {
      reasons.push(`High quality score (${supplier.quality_score}/100)`);
    }

    if (supplier.cost_competitiveness_score > 80) {
      reasons.push('Highly cost-competitive');
    }

    if (recommended > _current) {
      reasons.push(`Increase volume to ${recommended.toFixed(1)}% for better economics`);
    }

    return reasons.length > 0 ? reasons : ['Stable supplier with consistent performance'];
  }
}
