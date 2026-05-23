import { z } from 'zod';

export const CADFileFormatSchema = z.enum([
  'step',
  'iges',
  'stl',
  'obj',
  'fbx',
  'gltf',
  'dwg',
  'dxf',
  'parasolid',
  'stp',
  'sldprt',
  'iam',
  'prt',
]);

export type CADFileFormat = z.infer<typeof CADFileFormatSchema>;

export const BoundingBoxSchema = z.object({
  min_x: z.number(),
  min_y: z.number(),
  min_z: z.number(),
  max_x: z.number(),
  max_y: z.number(),
  max_z: z.number(),
});

export type BoundingBox = z.infer<typeof BoundingBoxSchema>;

export const CADModelSchema = z.object({
  id: z.string(),
  name: z.string(),
  format: CADFileFormatSchema,
  file_url: z.string(),
  file_hash: z.string(),
  file_size_bytes: z.number(),
  bounding_box: BoundingBoxSchema,
  volume_cubic_mm: z.number().optional(),
  surface_area_mm2: z.number().optional(),
  part_count: z.number().optional(),
  assembly_count: z.number().optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type CADModel = z.infer<typeof CADModelSchema>;

export const GeometryFeatureSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.enum(['hole', 'pocket', 'boss', 'fillet', 'chamfer', 'thread', 'groove', 'edge', 'face', 'surface']),
  dimensions: z.record(z.string(), z.number()),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type GeometryFeature = z.infer<typeof GeometryFeatureSchema>;

export const CADAnalysisSchema = z.object({
  id: z.string(),
  cad_model_id: z.string(),
  analysis_type: z.enum(['geometry', 'draft', 'wall_thickness', 'draft_angle', 'undercut', 'sharp_edges', 'surface_continuity']),
  features: z.array(GeometryFeatureSchema),
  issues: z.array(z.object({
    issue_id: z.string(),
    type: z.string(),
    severity: z.enum(['info', 'warning', 'error', 'critical']),
    description: z.string(),
    location: z.object({
      x: z.number(),
      y: z.number(),
      z: z.number(),
    }).optional(),
    recommendation: z.string().optional(),
  })),
  manufacturability_score: z.number().min(0).max(100),
  created_at: z.date(),
  updated_at: z.date(),
});

export type CADAnalysis = z.infer<typeof CADAnalysisSchema>;

export const CADRevisionSchema = z.object({
  id: z.string(),
  cad_model_id: z.string(),
  revision_number: z.number(),
  changes: z.array(z.object({
    field: z.string(),
    old_value: z.unknown(),
    new_value: z.unknown(),
  })),
  change_reason: z.string().optional(),
  created_by: z.string(),
  created_at: z.date(),
});

export type CADRevision = z.infer<typeof CADRevisionSchema>;
