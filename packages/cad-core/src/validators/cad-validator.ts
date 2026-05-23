import { CADFileFormat } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('cad:validator');

export interface ValidationIssue {
  type: 'error' | 'warning' | 'info';
  code: string;
  message: string;
  recommendation?: string;
}

export class CADValidator {
  validateFile(
    buffer: Buffer,
    format: CADFileFormat,
    fileName: string
  ): ValidationIssue[] {
    logger.debug({ fileName, format }, 'Validating CAD file');

    const issues: ValidationIssue[] = [];

    // Check file size
    if (buffer.length === 0) {
      issues.push({
        type: 'error',
        code: 'EMPTY_FILE',
        message: 'CAD file is empty',
      });
    }

    if (buffer.length > 500 * 1024 * 1024) {
      issues.push({
        type: 'warning',
        code: 'LARGE_FILE',
        message: 'CAD file exceeds 500MB - may cause processing delays',
        recommendation: 'Consider simplifying the model or splitting into assemblies',
      });
    }

    // Check file signature/magic bytes
    const signature = buffer.slice(0, 4).toString('hex');
    if (!this.isValidSignature(signature, format)) {
      issues.push({
        type: 'warning',
        code: 'INVALID_SIGNATURE',
        message: `File signature does not match ${format} format`,
        recommendation: 'Verify file format matches declared type',
      });
    }

    // Check file extension
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    if (!this.isValidExtension(ext, format)) {
      issues.push({
        type: 'warning',
        code: 'EXTENSION_MISMATCH',
        message: `File extension .${ext} does not match ${format} format`,
      });
    }

    // Structural validation
    const structureIssues = this.validateStructure(buffer, format);
    issues.push(...structureIssues);

    logger.debug({ issueCount: issues.length }, 'CAD validation complete');

    return issues;
  }

  private isValidSignature(signature: string, format: CADFileFormat): boolean {
    const signatures: Record<CADFileFormat, string[]> = {
      step: ['69736f31', '49534f31'], // ISO 1
      iges: ['', '48534620'], // HSF
      stl: ['4c430f6c'],
      obj: ['2366', '0a23'], // #f or \n#
      fbx: ['4b4d2044', 'fbx20003d'], // KaydaMaya or fbx=
      gltf: ['7b226173', '676c5446'], // json or glTF
      dwg: ['41433130', '41433231'],
      dxf: ['302020202020202020202020202020202020202020202020'],
      parasolid: ['',  ''],
      stp: ['69736f31', '49534f31'],
      sldprt: ['d0cf11e0'],
      iam: ['d0cf11e0'],
      prt: [''],
    };

    const validSignatures = signatures[format] || [];
    return validSignatures.length === 0 || validSignatures.includes(signature);
  }

  private isValidExtension(ext: string, format: CADFileFormat): boolean {
    const extensions: Record<CADFileFormat, string[]> = {
      step: ['stp', 'step'],
      iges: ['igs', 'ige'],
      stl: ['stl'],
      obj: ['obj'],
      fbx: ['fbx'],
      gltf: ['gltf', 'glb'],
      dwg: ['dwg'],
      dxf: ['dxf'],
      parasolid: ['x_t', 'xmt_txt'],
      stp: ['stp', 'step'],
      sldprt: ['sldprt'],
      iam: ['iam'],
      prt: ['prt'],
    };

    const validExts = extensions[format] || [];
    return validExts.includes(ext);
  }

  private validateStructure(buffer: Buffer, format: CADFileFormat): ValidationIssue[] {
    const issues: ValidationIssue[] = [];

    // Check for corrupt headers
    if (buffer.length < 100) {
      issues.push({
        type: 'warning',
        code: 'SHORT_FILE',
        message: 'CAD file is unusually short - may be incomplete',
      });
    }

    // Basic structure checks per format
    switch (format) {
      case 'stl':
        this.validateSTL(buffer, issues);
        break;
      case 'obj':
        this.validateOBJ(buffer, issues);
        break;
      case 'gltf':
        this.validateGLTF(buffer, issues);
        break;
    }

    return issues;
  }

  private validateSTL(buffer: Buffer, issues: ValidationIssue[]): void {
    // STL binary format: 80 byte header + 4 byte triangle count + triangles
    if (buffer.length < 84) {
      issues.push({
        type: 'error',
        code: 'INVALID_STL',
        message: 'Invalid STL file - insufficient header data',
      });
    }
  }

  private validateOBJ(buffer: Buffer, issues: ValidationIssue[]): void {
    const content = buffer.toString('utf-8', 0, Math.min(1000, buffer.length));

    if (!content.includes('v ') && !content.includes('g ')) {
      issues.push({
        type: 'warning',
        code: 'EMPTY_OBJ',
        message: 'OBJ file contains no vertices or geometry',
      });
    }
  }

  private validateGLTF(buffer: Buffer, issues: ValidationIssue[]): void {
    const magic = buffer.slice(0, 4).toString('ascii');
    if (magic !== 'glTF') {
      issues.push({
        type: 'error',
        code: 'INVALID_GLTF',
        message: 'Invalid glTF file - missing magic number',
      });
    }
  }
}
