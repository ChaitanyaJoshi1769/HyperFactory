import { HardwarePart, CADAnalysis } from '@hyperfactory/manufacturing-types';
import { CNCAnalysisResult } from '../analyzers/cnc-analyzer';
import { SheetMetalAnalysisResult } from '../analyzers/sheet-metal-analyzer';
import { PCBAnalysisResult } from '../analyzers/pcb-analyzer';
import { InjectionMoldAnalysisResult } from '../analyzers/injection-mold-analyzer';

export interface DFMReport {
  part_id: string;
  part_name: string;
  analysis_timestamp: Date;
  overall_manufacturability_score: number;
  estimated_lead_time_days: number;
  estimated_total_cost: number;
  process_specific_analysis: {
    cnc?: CNCAnalysisResult;
    sheet_metal?: SheetMetalAnalysisResult;
    pcb?: PCBAnalysisResult;
    injection_mold?: InjectionMoldAnalysisResult;
  };
  cad_issues: Array<{
    type: string;
    severity: string;
    description: string;
    recommendation: string;
  }>;
  recommendations: {
    immediate_actions: string[];
    design_improvements: string[];
    cost_reductions: string[];
    lead_time_optimizations: string[];
  };
  risk_assessment: {
    technical_risk: 'low' | 'medium' | 'high';
    schedule_risk: 'low' | 'medium' | 'high';
    cost_risk: 'low' | 'medium' | 'high';
    risk_mitigation_actions: string[];
  };
}

export class DFMReportGenerator {
  generateReport(
    part: HardwarePart,
    cadAnalysis?: CADAnalysis,
    processAnalyses?: {
      cnc?: CNCAnalysisResult;
      sheet_metal?: SheetMetalAnalysisResult;
      pcb?: PCBAnalysisResult;
      injection_mold?: InjectionMoldAnalysisResult;
    }
  ): DFMReport {
    const scores: number[] = [];
    const leadTimes: number[] = [];
    const costs: number[] = [];

    if (processAnalyses?.cnc) {
      scores.push(processAnalyses.cnc.manufacturability_score);
      leadTimes.push(processAnalyses.cnc.lead_time_days);
      costs.push(processAnalyses.cnc.cost_estimate);
    }

    if (processAnalyses?.sheet_metal) {
      scores.push(processAnalyses.sheet_metal.manufacturability_score);
      leadTimes.push(processAnalyses.sheet_metal.lead_time_days);
      costs.push(processAnalyses.sheet_metal.estimated_cost);
    }

    if (processAnalyses?.pcb) {
      scores.push(processAnalyses.pcb.manufacturability_score);
      leadTimes.push(processAnalyses.pcb.lead_time_days);
      costs.push(processAnalyses.pcb.pcb_cost_estimate);
    }

    if (processAnalyses?.injection_mold) {
      scores.push(processAnalyses.injection_mold.manufacturability_score);
      leadTimes.push(processAnalyses.injection_mold.lead_time_days);
      costs.push(processAnalyses.injection_mold.piece_price_estimate);
    }

    const overallScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 75;
    const maxLeadTime = leadTimes.length > 0 ? Math.max(...leadTimes) : 7;
    const totalCost = costs.length > 0 ? costs.reduce((a, b) => a + b, 0) : part.estimated_cost;

    const cadIssues = cadAnalysis?.issues.map((issue) => ({
      type: issue.type,
      severity: issue.severity,
      description: issue.description,
      recommendation: issue.recommendation || 'Review and address this issue',
    })) || [];

    const recommendations = this.generateRecommendations(
      part,
      processAnalyses,
      cadAnalysis
    );

    const riskAssessment = this.assessRisks(overallScore, maxLeadTime, totalCost);

    return {
      part_id: part.id,
      part_name: part.name,
      analysis_timestamp: new Date(),
      overall_manufacturability_score: Math.round(overallScore),
      estimated_lead_time_days: maxLeadTime,
      estimated_total_cost: totalCost,
      process_specific_analysis: processAnalyses || {},
      cad_issues: cadIssues,
      recommendations,
      risk_assessment: riskAssessment,
    };
  }

  private generateRecommendations(
    part: HardwarePart,
    processAnalyses?: {
      cnc?: CNCAnalysisResult;
      sheet_metal?: SheetMetalAnalysisResult;
      pcb?: PCBAnalysisResult;
      injection_mold?: InjectionMoldAnalysisResult;
    },
    cadAnalysis?: CADAnalysis
  ) {
    const immediate: string[] = [];
    const designImprovements: string[] = [];
    const costReductions: string[] = [];
    const leadTimeOpts: string[] = [];

    if (processAnalyses?.cnc?.potential_issues.some((i) => i.severity === 'error')) {
      immediate.push('Address CNC manufacturability errors before proceeding');
    }

    if (part.tolerances.length > 8) {
      designImprovements.push('Reduce number of tight tolerances');
      costReductions.push('Relax non-critical tolerances to reduce machining time');
    }

    if (part.surface_finishes.length > 3) {
      costReductions.push('Consolidate surface finish requirements');
    }

    if ((processAnalyses?.cnc?.estimated_machining_time_minutes || 0) > 120) {
      leadTimeOpts.push('Consider breaking part into sub-components for parallel machining');
    }

    return {
      immediate_actions: immediate,
      design_improvements: designImprovements,
      cost_reductions: costReductions,
      lead_time_optimizations: leadTimeOpts,
    };
  }

  private assessRisks(
    score: number,
    leadTime: number,
    cost: number
  ): DFMReport['risk_assessment'] {
    return {
      technical_risk: score < 70 ? 'high' : score < 85 ? 'medium' : 'low',
      schedule_risk: leadTime > 14 ? 'high' : leadTime > 7 ? 'medium' : 'low',
      cost_risk: cost > 500 ? 'high' : cost > 200 ? 'medium' : 'low',
      risk_mitigation_actions: [
        'Conduct design review with manufacturing partners',
        'Create prototype for validation',
        'Establish contingency timeline buffer',
      ],
    };
  }
}
