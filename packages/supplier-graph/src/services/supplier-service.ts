import { Supplier } from '@hyperfactory/manufacturing-types';
import { SupplierGraph } from '../graph/supplier-graph';
import { CapabilityMatcher, RequirementSpec } from '../matching/capability-matcher';
import { SupplierScorer } from '../matching/supplier-scorer';
import { SupplierOptimizer } from '../optimization/supplier-optimizer';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('supplier:service');

export class SupplierService {
  private graph = new SupplierGraph();
  private matcher = new CapabilityMatcher();
  private scorer = new SupplierScorer();
  private optimizer = new SupplierOptimizer();

  addSupplier(supplier: Supplier): void {
    logger.info({ supplierId: supplier.id }, 'Adding supplier to graph');
    this.graph.addSupplier(supplier);
  }

  addSuppliers(suppliers: Supplier[]): void {
    logger.info({ count: suppliers.length }, 'Adding multiple suppliers');
    for (const supplier of suppliers) {
      this.addSupplier(supplier);
    }
  }

  findSuppliersForCapability(
    processType: string,
    requirement?: Partial<RequirementSpec>
  ): Supplier[] {
    logger.info({ processType }, 'Finding suppliers for capability');

    const candidates = this.graph.findSuppliersWithCapability(processType);

    if (!requirement) {
      return candidates;
    }

    const fullRequirement: RequirementSpec = {
      process_type: processType,
      ...requirement,
    };

    const matches = this.matcher.matchCapabilities(candidates, fullRequirement);

    return candidates
      .filter((s) => matches.some((m) => m.supplier_id === s.id && m.meets_requirements))
      .sort((a, b) => {
        const scoreA = this.scorer.scoreSupplier(a).overall_score;
        const scoreB = this.scorer.scoreSupplier(b).overall_score;
        return scoreB - scoreA;
      });
  }

  scoreSupplier(supplier: Supplier) {
    return this.scorer.scoreSupplier(supplier);
  }

  rankSuppliers(suppliers: Supplier[]) {
    return this.scorer.rankSuppliers(suppliers);
  }

  optimizePortfolio(
    suppliers: Supplier[],
    currentOrders: Array<{ supplierId: string; volume: number }>
  ) {
    logger.info({ supplierCount: suppliers.length }, 'Optimizing supplier portfolio');
    return this.optimizer.optimizeSupplierPortfolio(suppliers, currentOrders);
  }

  findSuppliersByLocation(country: string, region?: string): Supplier[] {
    logger.debug({ country, region }, 'Finding suppliers by location');
    return this.graph.findSuppliersInLocation(country, region);
  }

  findSuppliersByNearestRegion(country: string, capabilityType: string): Supplier[] {
    logger.debug({ country, capabilityType }, 'Finding nearest suppliers');
    return this.graph.findNearestSuppliers(country, capabilityType);
  }

  findSuppliersByCertification(certification: string): Supplier[] {
    logger.debug({ certification }, 'Finding certified suppliers');
    return this.graph.findSuppliersWithCertification(certification);
  }

  getGraphStats() {
    return this.graph.getSupplierStats();
  }

  getGraphData() {
    return this.graph.getGraph();
  }
}
