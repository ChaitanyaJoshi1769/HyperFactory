import { HardwarePart, Material } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:cost-optimizer');

export interface CostOptimization {
  current_cost: number;
  optimized_cost: number;
  savings_amount: number;
  savings_percent: number;
  recommendations: Array<{
    category: string;
    current_value: unknown;
    recommended_value: unknown;
    savings: number;
    risk_level: 'low' | 'medium' | 'high';
  }>;
}

export class CostOptimizer {
  optimizeCost(part: HardwarePart, alternatives?: Material[]): CostOptimization {
    logger.debug({ partId: part.id }, 'Optimizing manufacturing cost');

    const recommendations: CostOptimization['recommendations'] = [];
    let currentCost = part.estimated_cost;
    let optimizedCost = currentCost;

    // Check material optimization
    if (alternatives && alternatives.length > 0) {
      const cheapestMaterial = alternatives.reduce((prev, current) =>
        current.cost_per_kg < prev.cost_per_kg ? current : prev
      );

      if (cheapestMaterial.cost_per_kg < part.material.cost_per_kg) {
        const materialSavings =
          (part.material.cost_per_kg - cheapestMaterial.cost_per_kg) * part.weight_kg;

        recommendations.push({
          category: 'material_substitution',
          current_value: part.material.name,
          recommended_value: cheapestMaterial.name,
          savings: materialSavings,
          risk_level: 'medium',
        });

        optimizedCost -= materialSavings;
      }
    }

    // Check tolerance optimization
    const tightTolerances = part.tolerances.filter(
      (t) => (t.upper_tolerance - t.lower_tolerance) / t.nominal_value < 0.01
    );

    if (tightTolerances.length > 3) {
      const toleranceSavings = tightTolerances.length * 15;
      recommendations.push({
        category: 'tolerance_relaxation',
        current_value: `${tightTolerances.length} tight tolerances`,
        recommended_value: `Relax to ±0.1% tolerance`,
        savings: toleranceSavings,
        risk_level: 'low',
      });

      optimizedCost -= toleranceSavings;
    }

    // Check surface finish optimization
    const expensiveFinishes = part.surface_finishes.filter((f) => f.cost_multiplier > 2);
    if (expensiveFinishes.length > 0) {
      const finishSavings = expensiveFinishes.length * 10 * part.surface_area_mm2 / 1000;
      recommendations.push({
        category: 'surface_finish',
        current_value: `${expensiveFinishes.length} expensive finishes`,
        recommended_value: 'Standard finish (Ra 1.6)',
        savings: finishSavings,
        risk_level: 'medium',
      });

      optimizedCost -= finishSavings;
    }

    // Check weight optimization
    const weightSavings = (part.weight_kg * 0.05) * part.material.cost_per_kg;
    if (weightSavings > 5) {
      recommendations.push({
        category: 'weight_reduction',
        current_value: `${part.weight_kg.toFixed(2)}kg`,
        recommended_value: `${(part.weight_kg * 0.95).toFixed(2)}kg`,
        savings: weightSavings,
        risk_level: 'medium',
      });

      optimizedCost -= weightSavings;
    }

    return {
      current_cost: currentCost,
      optimized_cost: Math.max(0, optimizedCost),
      savings_amount: currentCost - optimizedCost,
      savings_percent: ((currentCost - optimizedCost) / currentCost) * 100,
      recommendations,
    };
  }
}
