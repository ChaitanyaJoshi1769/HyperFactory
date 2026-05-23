import { HardwarePart, Material } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:material-optimizer');

export interface MaterialOptimization {
  current_material: Material;
  recommended_alternatives: Array<{
    material: Material;
    cost_savings_percent: number;
    performance_impact: number;
    manufacturability_improvement: number;
    recommendation_strength: 'high' | 'medium' | 'low';
  }>;
  total_material_cost: number;
  optimized_material_cost: number;
}

export class MaterialOptimizer {
  optimizeMaterial(
    part: HardwarePart,
    availableMaterials: Material[]
  ): MaterialOptimization {
    logger.debug({ partId: part.id }, 'Optimizing material selection');

    const alternatives = availableMaterials
      .filter((m) => this.isMaterialCompatible(m, part))
      .map((material) => ({
        material,
        cost_savings_percent: this.calculateCostSavings(part.material, material, part.weight_kg),
        performance_impact: this.evaluatePerformanceImpact(part.material, material),
        manufacturability_improvement: this.evaluateManufacturability(material),
        recommendation_strength: this.determineRecommendationStrength(part.material, material),
      }))
      .sort((a, b) => b.cost_savings_percent - a.cost_savings_percent);

    const currentCost = part.material.cost_per_kg * part.weight_kg;
    const bestAlternative = alternatives[0];
    const optimizedCost = bestAlternative
      ? bestAlternative.material.cost_per_kg * part.weight_kg
      : currentCost;

    return {
      current_material: part.material,
      recommended_alternatives: alternatives.slice(0, 5),
      total_material_cost: currentCost,
      optimized_material_cost: optimizedCost,
    };
  }

  private isMaterialCompatible(candidate: Material, part: HardwarePart): boolean {
    if (!candidate.tensile_strength || !part.material.tensile_strength) {
      return true;
    }

    return candidate.tensile_strength >= part.material.tensile_strength * 0.9;
  }

  private calculateCostSavings(
    current: Material,
    alternative: Material,
    weight: number
  ): number {
    const currentTotal = current.cost_per_kg * weight;
    const alternativeTotal = alternative.cost_per_kg * weight;

    return ((currentTotal - alternativeTotal) / currentTotal) * 100;
  }

  private evaluatePerformanceImpact(current: Material, alternative: Material): number {
    let impact = 0;

    if (alternative.tensile_strength && current.tensile_strength) {
      impact += ((alternative.tensile_strength / current.tensile_strength) - 1) * 20;
    }

    if (alternative.thermal_conductivity && current.thermal_conductivity) {
      impact += ((alternative.thermal_conductivity / current.thermal_conductivity) - 1) * 10;
    }

    return Math.max(-50, Math.min(50, impact));
  }

  private evaluateManufacturability(material: Material): number {
    let score = 0;

    if (material.machinability_index) {
      score += (material.machinability_index / 100) * 50;
    }

    if (material.cost_per_kg < 10) {
      score += 20;
    }

    return Math.min(100, score);
  }

  private determineRecommendationStrength(
    current: Material,
    alternative: Material
  ): 'high' | 'medium' | 'low' {
    const costDiff = ((current.cost_per_kg - alternative.cost_per_kg) / current.cost_per_kg) * 100;

    if (costDiff > 20) return 'high';
    if (costDiff > 10) return 'medium';
    return 'low';
  }
}
