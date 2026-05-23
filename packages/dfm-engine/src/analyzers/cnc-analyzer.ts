import { HardwarePart, CADAnalysis } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:cnc-analyzer');

export interface CNCAnalysisResult {
  manufacturability_score: number;
  estimated_machining_time_minutes: number;
  recommended_tools: string[];
  potential_issues: Array<{
    type: string;
    severity: 'info' | 'warning' | 'error';
    description: string;
    recommendation: string;
  }>;
  cost_estimate: number;
  lead_time_days: number;
}

export class CNCAnalyzer {
  analyzePart(part: HardwarePart, cadAnalysis?: CADAnalysis): CNCAnalysisResult {
    logger.debug({ partId: part.id }, 'Analyzing CNC manufacturability');

    const issues: CNCAnalysisResult['potential_issues'] = [];
    let score = 100;

    // Check minimum wall thickness
    if (part.properties?.['min_wall_thickness_mm'] !== undefined) {
      const minWall = part.properties['min_wall_thickness_mm'] as number;
      if (minWall < 1.5) {
        issues.push({
          type: 'wall_thickness',
          severity: 'warning',
          description: `Minimum wall thickness ${minWall}mm is below recommended 1.5mm for CNC`,
          recommendation: 'Increase wall thickness to improve structural integrity and reduce tool wear',
        });
        score -= 10;
      }
    }

    // Check for sharp edges
    if (cadAnalysis?.issues.some((i) => i.type === 'sharp_edges')) {
      issues.push({
        type: 'sharp_edges',
        severity: 'warning',
        description: 'Sharp edges detected - may cause tool breakage',
        recommendation: 'Add 0.5-1.0mm chamfers or fillets to all edges',
      });
      score -= 15;
    }

    // Check hole to wall clearance
    const minClearance = 1.5;
    if (
      part.properties?.['min_hole_distance_to_edge_mm'] !== undefined &&
      (part.properties['min_hole_distance_to_edge_mm'] as number) < minClearance
    ) {
      issues.push({
        type: 'hole_clearance',
        severity: 'warning',
        description: `Hole clearance less than ${minClearance}mm`,
        recommendation: 'Move holes further from edges to prevent tool deflection',
      });
      score -= 10;
    }

    // Calculate machining time estimate based on volume and complexity
    const baseTime = (part.volume_cubic_mm || 1000) / 100;
    const toolCount = this.estimateToolCount(part);
    const machiningTime = baseTime * toolCount;

    // Determine cost based on material and complexity
    const materialCostFactor = part.material.cost_per_kg * 1.2;
    const complexityFactor = Math.max(1, toolCount * 0.5);
    const estimatedCost = materialCostFactor * complexityFactor + 50;

    // Lead time estimation
    let leadTime = 5;
    if (machiningTime > 60) leadTime = 7;
    if (machiningTime > 120) leadTime = 10;

    return {
      manufacturability_score: Math.max(0, score),
      estimated_machining_time_minutes: Math.ceil(machiningTime),
      recommended_tools: this.getRecommendedTools(part),
      potential_issues: issues,
      cost_estimate: estimatedCost,
      lead_time_days: leadTime,
    };
  }

  private estimateToolCount(part: HardwarePart): number {
    let count = 1;

    if (part.tolerances.length > 0) {
      const tightTolerances = part.tolerances.filter(
        (t) => (t.upper_tolerance - t.lower_tolerance) / t.nominal_value < 0.01
      );
      count += Math.min(tightTolerances.length, 5);
    }

    if (part.surface_finishes.length > 0) {
      count += part.surface_finishes.length;
    }

    if (part.properties?.['hole_count'] !== undefined) {
      count += Math.ceil((part.properties['hole_count'] as number) / 5);
    }

    return count;
  }

  private getRecommendedTools(part: HardwarePart): string[] {
    const tools: string[] = [];

    const hardness = part.material.yield_strength || 0;
    if (hardness > 400) {
      tools.push('Carbide end mill');
      tools.push('Coated high-speed steel bit');
    } else {
      tools.push('Aluminum end mill');
      tools.push('Standard high-speed steel bit');
    }

    tools.push('Drill bits (assorted)');
    tools.push('Chamfer tool');
    tools.push('Cutting fluid');

    if (part.tolerances.some((t) => (t.upper_tolerance - t.lower_tolerance) / t.nominal_value < 0.005)) {
      tools.push('Precision boring bar');
    }

    return tools;
  }
}
