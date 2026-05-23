import { HardwarePart, Tolerance } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:tolerance-optimizer');

export interface ToleranceOptimization {
  current_tolerances: Tolerance[];
  optimized_tolerances: Tolerance[];
  cost_reduction_percent: number;
  manufacturability_improvement: number;
  critical_dimensions: string[];
}

export class ToleranceOptimizer {
  optimizeTolerances(part: HardwarePart): ToleranceOptimization {
    logger.debug({ partId: part.id }, 'Optimizing tolerances');

    const criticalDimensions = this.identifyCriticalDimensions(part);
    const optimized = part.tolerances.map((tolerance) => {
      if (criticalDimensions.includes(tolerance.dimension)) {
        return tolerance;
      }

      const currentRange = tolerance.upper_tolerance - tolerance.lower_tolerance;
      const percentageOfValue = (currentRange / tolerance.nominal_value) * 100;

      if (percentageOfValue < 0.5) {
        const newRange = Math.max(0.05, tolerance.nominal_value * 0.005);
        const newLower = tolerance.nominal_value - newRange / 2;
        const newUpper = tolerance.nominal_value + newRange / 2;

        return {
          ...tolerance,
          upper_tolerance: newUpper,
          lower_tolerance: newLower,
        };
      }

      return tolerance;
    });

    const costReduction = this.calculateCostReduction(part.tolerances, optimized);
    const manufacturabilityImprovement = this.calculateManufacturabilityImprovement(
      part.tolerances,
      optimized
    );

    return {
      current_tolerances: part.tolerances,
      optimized_tolerances: optimized,
      cost_reduction_percent: costReduction,
      manufacturability_improvement: manufacturabilityImprovement,
      critical_dimensions: criticalDimensions,
    };
  }

  private identifyCriticalDimensions(part: HardwarePart): string[] {
    return part.tolerances
      .filter((t) => (t.upper_tolerance - t.lower_tolerance) / t.nominal_value < 0.01)
      .map((t) => t.dimension);
  }

  private calculateCostReduction(
    current: Tolerance[],
    optimized: Tolerance[]
  ): number {
    let reduction = 0;

    for (let i = 0; i < current.length; i++) {
      const curr = current[i];
      const opt = optimized[i];

      const currTightness = (curr.upper_tolerance - curr.lower_tolerance) / curr.nominal_value;
      const optTightness = (opt.upper_tolerance - opt.lower_tolerance) / opt.nominal_value;

      if (optTightness > currTightness) {
        reduction += (optTightness - currTightness) * 10;
      }
    }

    return Math.min(30, reduction);
  }

  private calculateManufacturabilityImprovement(
    current: Tolerance[],
    optimized: Tolerance[]
  ): number {
    const currentScore = current.filter(
      (t) => (t.upper_tolerance - t.lower_tolerance) / t.nominal_value < 0.005
    ).length;
    const optimizedScore = optimized.filter(
      (t) => (t.upper_tolerance - t.lower_tolerance) / t.nominal_value < 0.005
    ).length;

    return optimizedScore - currentScore;
  }
}
