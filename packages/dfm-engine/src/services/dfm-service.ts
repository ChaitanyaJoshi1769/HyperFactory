import { HardwarePart, CADAnalysis, PCB } from '@hyperfactory/manufacturing-types';
import { CNCAnalyzer } from '../analyzers/cnc-analyzer';
import { SheetMetalAnalyzer } from '../analyzers/sheet-metal-analyzer';
import { PCBAnalyzer } from '../analyzers/pcb-analyzer';
import { InjectionMoldAnalyzer } from '../analyzers/injection-mold-analyzer';
import { CostOptimizer } from '../optimization/cost-optimizer';
import { ToleranceOptimizer } from '../optimization/tolerance-optimizer';
import { MaterialOptimizer } from '../optimization/material-optimizer';
import { DFMReportGenerator, DFMReport } from '../analysis/dfm-report';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('dfm:service');

export class DFMService {
  private cncAnalyzer = new CNCAnalyzer();
  private sheetMetalAnalyzer = new SheetMetalAnalyzer();
  private pcbAnalyzer = new PCBAnalyzer();
  private injectionMoldAnalyzer = new InjectionMoldAnalyzer();
  private costOptimizer = new CostOptimizer();
  private toleranceOptimizer = new ToleranceOptimizer();
  private materialOptimizer = new MaterialOptimizer();
  private reportGenerator = new DFMReportGenerator();

  analyzeHardwarePart(
    part: HardwarePart,
    cadAnalysis?: CADAnalysis
  ): DFMReport {
    logger.info({ partId: part.id }, 'Starting DFM analysis');

    const processAnalyses = {};

    if (part.type === 'cnc_machined' || part.type === 'mechanical') {
      (processAnalyses as any).cnc = this.cncAnalyzer.analyzePart(part, cadAnalysis);
    }

    if (part.type === 'sheet_metal') {
      (processAnalyses as any).sheet_metal = this.sheetMetalAnalyzer.analyzePart(part);
    }

    if (part.type === 'injection_molded') {
      (processAnalyses as any).injection_mold = this.injectionMoldAnalyzer.analyzePart(part);
    }

    return this.reportGenerator.generateReport(part, cadAnalysis, processAnalyses as any);
  }

  analyzePCB(pcb: PCB): any {
    logger.info({ pcbId: pcb.id }, 'Starting PCB analysis');
    const analysis = this.pcbAnalyzer.analyzePCB(pcb);

    return {
      pcb_id: pcb.id,
      analysis,
      timestamp: new Date(),
    };
  }

  optimizeCosts(part: HardwarePart, availableMaterials?: any[]) {
    logger.info({ partId: part.id }, 'Optimizing costs');
    return this.costOptimizer.optimizeCost(part, availableMaterials);
  }

  optimizeTolerances(part: HardwarePart) {
    logger.info({ partId: part.id }, 'Optimizing tolerances');
    return this.toleranceOptimizer.optimizeTolerances(part);
  }

  optimizeMaterial(part: HardwarePart, availableMaterials: any[]) {
    logger.info({ partId: part.id }, 'Optimizing material');
    return this.materialOptimizer.optimizeMaterial(part, availableMaterials);
  }
}
