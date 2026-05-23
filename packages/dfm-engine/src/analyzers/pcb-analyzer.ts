import { PCB } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:pcb-analyzer');

export interface PCBAnalysisResult {
  manufacturability_score: number;
  pcb_cost_estimate: number;
  assembly_complexity_score: number;
  lead_time_days: number;
  critical_issues: Array<{
    type: string;
    severity: 'critical' | 'warning' | 'info';
    description: string;
    recommendation: string;
  }>;
  design_for_testability_score: number;
  thermal_analysis_needed: boolean;
}

export class PCBAnalyzer {
  analyzePCB(pcb: PCB): PCBAnalysisResult {
    logger.debug({ pcbId: pcb.id }, 'Analyzing PCB manufacturability');

    const issues: PCBAnalysisResult['critical_issues'] = [];
    let score = 100;

    // Check design rule violations
    if (pcb.min_trace_width_mm < 0.1) {
      issues.push({
        type: 'trace_width',
        severity: 'critical',
        description: 'Trace width below 0.1mm may not be achievable',
        recommendation: 'Increase trace width to 0.15mm minimum for standard PCB fabs',
      });
      score -= 20;
    }

    if (pcb.min_via_diameter_mm < 0.3) {
      issues.push({
        type: 'via_diameter',
        severity: 'critical',
        description: 'Via diameter below 0.3mm is difficult to manufacture',
        recommendation: 'Increase via diameter to 0.3mm or use blind/buried vias',
      });
      score -= 15;
    }

    // Check layer count
    if (pcb.layer_count > 10) {
      issues.push({
        type: 'layer_complexity',
        severity: 'warning',
        description: `${pcb.layer_count} layers increases manufacturing complexity and cost`,
        recommendation: 'Consider consolidating layers if possible',
      });
      score -= 10;
    }

    // Check surface finish
    const validFinishes = ['lead_free_hasl', 'immersion_gold', 'immersion_silver', 'osp'];
    if (!validFinishes.includes(pcb.surface_finish.toLowerCase())) {
      issues.push({
        type: 'surface_finish',
        severity: 'warning',
        description: `Surface finish "${pcb.surface_finish}" may have limited fab support`,
        recommendation: 'Use standard finishes: HASL, Immersion Gold, Silver, or OSP',
      });
      score -= 5;
    }

    // Cost estimation (simplified)
    const baseCost = 50;
    const layerCost = pcb.layer_count * 10;
    const areaCost = (pcb.thickness_mm * 10) * 5;
    const complexityCost =
      (pcb.min_trace_width_mm < 0.15 ? 50 : 0) + (pcb.min_via_diameter_mm < 0.4 ? 30 : 0);
    const estimatedCost = baseCost + layerCost + areaCost + complexityCost;

    // Lead time estimation
    let leadTime = 5;
    if (pcb.layer_count > 6) leadTime = 7;
    if (pcb.min_trace_width_mm < 0.15 || pcb.min_via_diameter_mm < 0.4) leadTime = 10;

    // Determine if thermal analysis is needed
    const thermalAnalysisNeeded =
      (pcb.layer_count > 4 && baseCost > 100) || pcb.thickness_mm < 0.4;

    return {
      manufacturability_score: Math.max(0, score),
      pcb_cost_estimate: estimatedCost,
      assembly_complexity_score: Math.min(100, 50 + pcb.layer_count * 5),
      lead_time_days: leadTime,
      critical_issues: issues,
      design_for_testability_score: this.calculateDFTScore(pcb),
      thermal_analysis_needed: thermalAnalysisNeeded,
    };
  }

  private calculateDFTScore(pcb: PCB): number {
    let score = 100;

    if ((pcb.layer_count > 8)) {
      score -= 10;
    }

    if (pcb.min_via_diameter_mm < 0.5) {
      score -= 5;
    }

    return Math.max(0, score);
  }
}
