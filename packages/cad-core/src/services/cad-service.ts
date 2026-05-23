import { CADFileFormat, CADModel } from '@hyperfactory/manufacturing-types';
import { CADProcessor } from '../processors/cad-processor';
import { GeometryAnalyzer } from '../processors/geometry-analyzer';
import { ManufacturingFeatureDetector } from '../processors/manufacturing-feature-detector';
import { FormatConverter } from '../converters/format-converter';
import { CADValidator } from '../validators/cad-validator';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('cad:service');

export class CADService {
  private processor = new CADProcessor();
  private geometryAnalyzer = new GeometryAnalyzer();
  private featureDetector = new ManufacturingFeatureDetector();
  private converter = new FormatConverter();
  private validator = new CADValidator();

  async processCADFile(
    fileBuffer: Buffer,
    format: CADFileFormat,
    fileName: string
  ): Promise<CADModel> {
    logger.info({ fileName, format }, 'Processing CAD file');

    // Validate file
    const validationIssues = this.validator.validateFile(fileBuffer, format, fileName);
    const errors = validationIssues.filter((i) => i.type === 'error');

    if (errors.length > 0) {
      throw new Error(`CAD file validation failed: ${errors[0].message}`);
    }

    // Process file
    const processingResult = await this.processor.processFile(fileBuffer, format, fileName);

    // Analyze geometry
    const fileContent = fileBuffer.toString('utf-8', 0, Math.min(10000, fileBuffer.length));
    const geometryFeatures = this.geometryAnalyzer.analyzeGeometry(
      processingResult.bounding_box,
      fileContent
    );

    // Detect manufacturing features
    const manufacturingFeatures = this.featureDetector.detectFeatures(fileContent);

    const model: CADModel = {
      id: processingResult.model_id,
      name: fileName.split('.')[0],
      format,
      file_url: `s3://hyperfactory-cad/${processingResult.model_id}.${format}`,
      file_hash: 'placeholder-hash',
      file_size_bytes: fileBuffer.length,
      bounding_box: processingResult.bounding_box,
      volume_cubic_mm: processingResult.volume_cubic_mm,
      surface_area_mm2: processingResult.surface_area_mm2,
      part_count: processingResult.part_count,
      assembly_count: processingResult.assembly_count,
      properties: {
        geometry_features: geometryFeatures.length,
        manufacturing_features: manufacturingFeatures.length,
        complexity_score: this.featureDetector.calculateComplexityScore(manufacturingFeatures),
        estimated_machining_time: this.featureDetector.estimateMachiningTime(
          manufacturingFeatures
        ),
        requires_secondary_operations: this.featureDetector.requiresSecondaryOperations(
          manufacturingFeatures
        ),
      },
      created_at: new Date(),
      updated_at: new Date(),
    };

    logger.info({ modelId: model.id }, 'CAD file processing complete');

    return model;
  }

  async convertCADFormat(
    fileBuffer: Buffer,
    fromFormat: CADFileFormat,
    toFormat: CADFileFormat
  ): Promise<Buffer> {
    logger.info({ from: fromFormat, to: toFormat }, 'Converting CAD format');

    if (!this.converter.isConversionSupported(fromFormat, toFormat)) {
      throw new Error(`Conversion from ${fromFormat} to ${toFormat} is not supported`);
    }

    return this.converter.convertFormat(fileBuffer, fromFormat, toFormat);
  }

  supportsVisualization(format: CADFileFormat): boolean {
    return this.converter.supportsVisualization(format);
  }

  getAvailableConversions(format: CADFileFormat): CADFileFormat[] {
    return this.converter.getCommonConversions(format);
  }
}
