import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('cad:feature-detector');

export interface ManufacturingFeature {
  type: string;
  complexity_level: 'simple' | 'moderate' | 'complex';
  manufacturing_difficulty: number;
  estimated_time_minutes: number;
  tool_changes_required: number;
  requires_secondary_operations: boolean;
}

export class ManufacturingFeatureDetector {
  detectFeatures(geometry: string): ManufacturingFeature[] {
    logger.debug('Detecting manufacturing features');

    const features: ManufacturingFeature[] = [];

    // Detect threaded holes
    if (/thread|metric|npt|bsp/gi.test(geometry)) {
      features.push({
        type: 'threaded_hole',
        complexity_level: 'moderate',
        manufacturing_difficulty: 7,
        estimated_time_minutes: 5,
        tool_changes_required: 2,
        requires_secondary_operations: true,
      });
    }

    // Detect blind holes
    if (/blind|not\s+through/gi.test(geometry)) {
      features.push({
        type: 'blind_hole',
        complexity_level: 'moderate',
        manufacturing_difficulty: 6,
        estimated_time_minutes: 4,
        tool_changes_required: 1,
        requires_secondary_operations: false,
      });
    }

    // Detect counter-bores
    if (/counter\s*bore|counterbore|cbore/gi.test(geometry)) {
      features.push({
        type: 'counter_bore',
        complexity_level: 'moderate',
        manufacturing_difficulty: 5,
        estimated_time_minutes: 3,
        tool_changes_required: 2,
        requires_secondary_operations: false,
      });
    }

    // Detect counter-sinks
    if (/counter\s*sink|countersink|csink/gi.test(geometry)) {
      features.push({
        type: 'counter_sink',
        complexity_level: 'simple',
        manufacturing_difficulty: 4,
        estimated_time_minutes: 2,
        tool_changes_required: 1,
        requires_secondary_operations: false,
      });
    }

    // Detect slots
    if (/slot|keyway|groove/gi.test(geometry)) {
      features.push({
        type: 'slot',
        complexity_level: 'moderate',
        manufacturing_difficulty: 6,
        estimated_time_minutes: 5,
        tool_changes_required: 1,
        requires_secondary_operations: false,
      });
    }

    // Detect splines
    if (/spline|involute|gear|teeth/gi.test(geometry)) {
      features.push({
        type: 'spline',
        complexity_level: 'complex',
        manufacturing_difficulty: 9,
        estimated_time_minutes: 20,
        tool_changes_required: 3,
        requires_secondary_operations: true,
      });
    }

    logger.debug({ featureCount: features.length }, 'Feature detection complete');

    return features;
  }

  calculateComplexityScore(features: ManufacturingFeature[]): number {
    if (features.length === 0) return 10;

    const totalDifficulty = features.reduce((sum, f) => sum + f.manufacturing_difficulty, 0);
    const totalTime = features.reduce((sum, f) => sum + f.estimated_time_minutes, 0);

    return Math.min(100, (totalDifficulty + totalTime / 5) / 2);
  }

  estimateMachiningTime(features: ManufacturingFeature[]): number {
    return features.reduce((sum, f) => sum + f.estimated_time_minutes, 0);
  }

  requiresSecondaryOperations(features: ManufacturingFeature[]): boolean {
    return features.some((f) => f.requires_secondary_operations);
  }
}
