import { Supplier, SupplierCapability } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('supplier:graph');

export interface GraphNode {
  id: string;
  type: 'supplier' | 'capability' | 'location' | 'certification';
  data: unknown;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  properties: Record<string, unknown>;
}

export class SupplierGraph {
  private nodes: Map<string, GraphNode> = new Map();
  private edges: Map<string, GraphEdge[]> = new Map();

  addSupplier(supplier: Supplier): void {
    logger.debug({ supplierId: supplier.id }, 'Adding supplier to graph');

    const supplierNode: GraphNode = {
      id: supplier.id,
      type: 'supplier',
      data: supplier,
    };

    this.nodes.set(supplier.id, supplierNode);

    // Add capability nodes
    for (const capability of supplier.capabilities) {
      const capId = `cap-${supplier.id}-${capability.id}`;
      const capNode: GraphNode = {
        id: capId,
        type: 'capability',
        data: capability,
      };

      this.nodes.set(capId, capNode);

      // Edge: supplier -> capability
      this.addEdge(
        supplier.id,
        capId,
        {
          source: supplier.id,
          target: capId,
          weight: 1.0,
          properties: {
            relationship: 'has_capability',
          },
        }
      );
    }

    // Add location node
    const locationId = `loc-${supplier.location.country}-${supplier.location.region}`;
    if (!this.nodes.has(locationId)) {
      const locNode: GraphNode = {
        id: locationId,
        type: 'location',
        data: supplier.location,
      };
      this.nodes.set(locationId, locNode);
    }

    this.addEdge(
      supplier.id,
      locationId,
      {
        source: supplier.id,
        target: locationId,
        weight: 1.0,
        properties: {
          relationship: 'located_in',
        },
      }
    );

    // Add certification nodes
    for (const cert of supplier.certifications) {
      const certId = `cert-${cert}`;
      if (!this.nodes.has(certId)) {
        const certNode: GraphNode = {
          id: certId,
          type: 'certification',
          data: { name: cert },
        };
        this.nodes.set(certId, certNode);
      }

      this.addEdge(
        supplier.id,
        certId,
        {
          source: supplier.id,
          target: certId,
          weight: 1.0,
          properties: {
            relationship: 'certified_by',
          },
        }
      );
    }
  }

  private addEdge(source: string, target: string, edge: GraphEdge): void {
    if (!this.edges.has(source)) {
      this.edges.set(source, []);
    }
    this.edges.get(source)!.push(edge);
  }

  findSuppliersWithCapability(capabilityType: string): Supplier[] {
    const suppliers: Supplier[] = [];

    for (const node of this.nodes.values()) {
      if (node.type === 'supplier') {
        const supplier = node.data as Supplier;
        if (supplier.capabilities.some((c) => c.process === capabilityType || c.type === capabilityType)) {
          suppliers.push(supplier);
        }
      }
    }

    return suppliers;
  }

  findSuppliersInLocation(country: string, region?: string): Supplier[] {
    const suppliers: Supplier[] = [];

    for (const node of this.nodes.values()) {
      if (node.type === 'supplier') {
        const supplier = node.data as Supplier;
        if (supplier.location.country === country && (!region || supplier.location.region === region)) {
          suppliers.push(supplier);
        }
      }
    }

    return suppliers;
  }

  findSuppliersWithCertification(certification: string): Supplier[] {
    const suppliers: Supplier[] = [];

    for (const node of this.nodes.values()) {
      if (node.type === 'supplier') {
        const supplier = node.data as Supplier;
        if (supplier.certifications.includes(certification)) {
          suppliers.push(supplier);
        }
      }
    }

    return suppliers;
  }

  calculateConnectivity(supplierId: string): number {
    const edges = this.edges.get(supplierId) || [];
    return edges.length;
  }

  findNearestSuppliers(
    country: string,
    capabilityType: string,
    maxDistance?: number
  ): Supplier[] {
    const candidates = this.findSuppliersInLocation(country);
    return candidates.filter((s) =>
      s.capabilities.some((c) => c.process === capabilityType || c.type === capabilityType)
    );
  }

  getGraph() {
    return {
      nodes: Array.from(this.nodes.values()),
      edges: Array.from(this.edges.values()).flat(),
    };
  }

  getSupplierStats() {
    let supplierCount = 0;
    let capabilityCount = 0;
    let locationCount = 0;
    let certificationCount = 0;

    for (const node of this.nodes.values()) {
      if (node.type === 'supplier') supplierCount++;
      else if (node.type === 'capability') capabilityCount++;
      else if (node.type === 'location') locationCount++;
      else if (node.type === 'certification') certificationCount++;
    }

    return {
      suppliers: supplierCount,
      capabilities: capabilityCount,
      locations: locationCount,
      certifications: certificationCount,
      total_nodes: this.nodes.size,
      total_edges: Array.from(this.edges.values()).flat().length,
    };
  }
}
