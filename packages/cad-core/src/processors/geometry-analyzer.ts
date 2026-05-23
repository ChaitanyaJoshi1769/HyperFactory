import { BoundingBox, GeometryFeature } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('cad:geometry-analyzer');

export class GeometryAnalyzer {
  analyzeGeometry(bbox: BoundingBox, fileContent: string): GeometryFeature[] {
    logger.debug('Analyzing geometry features');

    const features: GeometryFeature[] = [];

    // Detect holes
    const holePattern = /hole|bore|drilled|diameter\s+\d+/gi;
    if (holePattern.test(fileContent)) {
      features.push({
        id: 'feature-hole-1',
        name: 'Primary Hole',
        type: 'hole',
        dimensions: {
          diameter: 10,
          depth: 20,
        },
      });
    }

    // Detect pockets
    if (/pocket|depression|recess/gi.test(fileContent)) {
      features.push({
        id: 'feature-pocket-1',
        name: 'Pocket',
        type: 'pocket',
        dimensions: {
          width: 50,
          length: 50,
          depth: 10,
        },
      });
    }

    // Detect fillets
    if (/fillet|radius|round/gi.test(fileContent)) {
      features.push({
        id: 'feature-fillet-1',
        name: 'Fillet',
        type: 'fillet',
        dimensions: {
          radius: 2,
        },
      });
    }

    // Detect chamfers
    if (/chamfer|beveled?|edge/gi.test(fileContent)) {
      features.push({
        id: 'feature-chamfer-1',
        name: 'Chamfer',
        type: 'chamfer',
        dimensions: {
          angle: 45,
          size: 1,
        },
      });
    }

    logger.debug({ featureCount: features.length }, 'Geometry analysis complete');

    return features;
  }

  calculateVolume(vertices: Array<[number, number, number]>): number {
    if (vertices.length < 4) return 0;

    // Simplified volume calculation using convex hull approximation
    const xs = vertices.map((v) => v[0]);
    const ys = vertices.map((v) => v[1]);
    const zs = vertices.map((v) => v[2]);

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const minZ = Math.min(...zs);
    const maxZ = Math.max(...zs);

    return (maxX - minX) * (maxY - minY) * (maxZ - minZ) * 0.6;
  }

  detectWallThickness(geometry: string): { min: number; max: number } {
    // Simplified wall thickness detection
    const wallThicknessPattern = /thickness\s+(\d+(?:\.\d+)?)/gi;
    const matches = [...geometry.matchAll(wallThicknessPattern)];

    if (matches.length > 0) {
      const values = matches.map((m) => parseFloat(m[1]));
      return {
        min: Math.min(...values),
        max: Math.max(...values),
      };
    }

    return { min: 1.5, max: 5 };
  }

  detectDraftAngles(geometry: string): number[] {
    const draftPattern = /draft\s+(\d+(?:\.\d+)?)\s*(?:degree|deg|°)/gi;
    const matches = [...geometry.matchAll(draftPattern)];

    return matches.map((m) => parseFloat(m[1]));
  }

  detectUndercuts(geometry: string): boolean {
    return /undercut|undercut|reverse|overhang/gi.test(geometry);
  }
}
