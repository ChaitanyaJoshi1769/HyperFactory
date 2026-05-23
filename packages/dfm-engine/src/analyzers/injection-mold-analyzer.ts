import { HardwarePart } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:injection-mold-analyzer');

export interface InjectionMoldAnalysisResult {
  manufacturability_score: number;
  mold_cost_estimate: number;
  piece_price_estimate: number;
  minimum_wall_thickness_mm: number;
  draft_angle_required_degrees: number;
  cooling_time_seconds: number;
  cycle_time_seconds: number;
  lead_time_days: number;
  critical_issues: Array<{
    type: string;
    severity: 'critical' | 'warning' | 'info';
    description: string;
    recommendation: string;
  }>;
}

export class InjectionMoldAnalyzer {
  analyzePart(part: HardwarePart): InjectionMoldAnalysisResult {
    logger.debug({ partId: part.id }, 'Analyzing injection mold manufacturability');

    const issues: InjectionMoldAnalysisResult['critical_issues'] = [];
    let score = 100;

    // Check wall thickness uniformity
    const minWallThickness = 1.5;
    const maxWallThickness = 4;

    if (part.properties?.['min_wall_thickness_mm'] !== undefined) {
      const min = part.properties['min_wall_thickness_mm'] as number;
      if (min < minWallThickness) {
        issues.push({
          type: 'wall_thickness',
          severity: 'critical',
          description: `Minimum wall thickness ${min}mm is below recommended ${minWallThickness}mm`,
          recommendation: `Increase all walls to at least ${minWallThickness}mm for uniform cooling`,
        });
        score -= 20;
      }
    }

    if (part.properties?.['max_wall_thickness_mm'] !== undefined) {
      const max = part.properties['max_wall_thickness_mm'] as number;
      if (max > maxWallThickness) {
        issues.push({
          type: 'wall_thickness_max',
          severity: 'warning',
          description: `Maximum wall thickness ${max}mm may cause sink marks`,
          recommendation: 'Consider adding ribs or reducing wall thickness in thick sections',
        });
        score -= 10;
      }
    }

    // Check for undercuts
    if (part.properties?.['has_undercuts'] === true) {
      issues.push({
        type: 'undercuts',
        severity: 'critical',
        description: 'Part contains undercuts requiring slides or collapsible cores',
        recommendation: 'Eliminate undercuts or plan for additional mold complexity',
      });
      score -= 25;
    }

    // Check for sharp edges
    if (part.surface_finishes.some((f) => f.roughness_ra < 0.4)) {
      issues.push({
        type: 'sharp_edges',
        severity: 'warning',
        description: 'Fine surface finish may require polishing',
        recommendation: 'Use standard finishes (Ra 1.6-3.2) to reduce mold cost',
      });
      score -= 10;
    }

    // Calculate mold cost (simplified)
    const baseToolCost = 5000;
    const complexityFactor = this.calculateComplexity(part);
    const moldCost = baseToolCost + complexityFactor * 1000;

    // Piece price estimation
    const materialCost = part.material.cost_per_kg * part.weight_kg * 1.5;
    const laborPerPiece = 0.50;
    const overheadPerPiece = 0.25;
    const piecePrice = materialCost + laborPerPiece + overheadPerPiece;

    // Cooling time estimation (rough approximation)
    const coolingTime = Math.sqrt(part.weight_kg * 100);

    // Cycle time = cooling + injection + ejection
    const cycleTime = coolingTime + 5 + 2;

    // Lead time (mold making takes significant time)
    let leadTime = 20;
    if (complexityFactor > 5) leadTime = 30;
    if (complexityFactor > 10) leadTime = 45;

    return {
      manufacturability_score: Math.max(0, score),
      mold_cost_estimate: moldCost,
      piece_price_estimate: piecePrice,
      minimum_wall_thickness_mm: minWallThickness,
      draft_angle_required_degrees: 1.5,
      cooling_time_seconds: Math.ceil(coolingTime),
      cycle_time_seconds: Math.ceil(cycleTime),
      lead_time_days: leadTime,
      critical_issues: issues,
    };
  }

  private calculateComplexity(part: HardwarePart): number {
    let complexity = 1;

    if (part.tolerances.length > 0) {
      complexity += Math.min(part.tolerances.length, 5) * 0.5;
    }

    if (part.surface_finishes.length > 1) {
      complexity += part.surface_finishes.length;
    }

    if (part.properties?.['boss_count'] !== undefined) {
      complexity += ((part.properties['boss_count'] as number) * 0.5);
    }

    if (part.properties?.['rib_count'] !== undefined) {
      complexity += ((part.properties['rib_count'] as number) * 0.3);
    }

    return complexity;
  }
}
