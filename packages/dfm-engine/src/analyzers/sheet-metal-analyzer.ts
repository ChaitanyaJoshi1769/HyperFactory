import { HardwarePart } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:sheet-metal-analyzer');

export interface SheetMetalAnalysisResult {
  manufacturability_score: number;
  minimum_bend_radius_mm: number;
  bend_deduction_total_mm: number;
  scrap_estimate_percent: number;
  press_tonnage_required: number;
  estimated_cost: number;
  lead_time_days: number;
  potential_issues: Array<{
    type: string;
    severity: 'info' | 'warning' | 'error';
    description: string;
    recommendation: string;
  }>;
}

export class SheetMetalAnalyzer {
  analyzePart(part: HardwarePart): SheetMetalAnalysisResult {
    logger.debug({ partId: part.id }, 'Analyzing sheet metal manufacturability');

    const issues: SheetMetalAnalysisResult['potential_issues'] = [];
    let score = 100;

    // Estimate material thickness from properties
    const thickness = (part.properties?.['thickness_mm'] as number) || 1;

    // Check minimum bend radius
    const minBendRadius = Math.max(thickness, 1);
    if ((part.properties?.['bend_radii_mm'] as number[])?.some((r) => r < minBendRadius)) {
      issues.push({
        type: 'bend_radius',
        severity: 'warning',
        description: `Some bend radii are below minimum ${minBendRadius}mm`,
        recommendation: `Increase bend radii to at least ${minBendRadius}mm or change material`,
      });
      score -= 15;
    }

    // Check for sharp corners
    const cornerCount = (part.properties?.['corner_count'] as number) || 0;
    if (cornerCount > 4) {
      issues.push({
        type: 'complexity',
        severity: 'info',
        description: `Part has ${cornerCount} corners - may increase die cost`,
        recommendation: 'Consider simplifying corner geometry if cost is critical',
      });
      score -= 5;
    }

    // Calculate bend deduction
    const bendCount = (part.properties?.['bend_count'] as number) || 0;
    const bendDeduction = bendCount * (Math.PI * minBendRadius - thickness);

    // Calculate press tonnage based on surface area and thickness
    const surfaceArea = part.surface_area_mm2 || 10000;
    const pressTonnage = (surfaceArea * thickness * 1.2) / 1000;

    // Scrap estimation (typically 15-25% for sheet metal)
    const scrapPercent = Math.min(25, 15 + bendCount * 2);

    // Cost estimation
    const materialVolume = part.weight_kg / (part.material.density || 2.7);
    const baseCost = part.material.cost_per_kg * part.weight_kg;
    const laborCost = 20 + bendCount * 5;
    const estimatedCost = baseCost + laborCost;

    // Lead time (typically 5-7 days for simple parts)
    let leadTime = 5;
    if (bendCount > 3) leadTime = 7;
    if (pressTonnage > 100) leadTime = 10;

    return {
      manufacturability_score: Math.max(0, score),
      minimum_bend_radius_mm: minBendRadius,
      bend_deduction_total_mm: bendDeduction,
      scrap_estimate_percent: scrapPercent,
      press_tonnage_required: pressTonnage,
      estimated_cost: estimatedCost,
      lead_time_days: leadTime,
      potential_issues: issues,
    };
  }
}
