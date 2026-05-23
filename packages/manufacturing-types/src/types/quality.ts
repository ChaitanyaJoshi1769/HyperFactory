import { z } from 'zod';

export const QualityCheckTypeSchema = z.enum([
  'dimensional',
  'surface_finish',
  'material_verification',
  'visual_inspection',
  'functional_test',
  'stress_test',
  'thermal_test',
  'electrical_test',
  'assembly_validation',
  'documentation_check',
]);

export type QualityCheckType = z.infer<typeof QualityCheckTypeSchema>;

export const QualityCheckSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  check_type: QualityCheckTypeSchema,
  parameter: z.string(),
  nominal_value: z.number(),
  tolerance: z.number(),
  actual_value: z.number(),
  passed: z.boolean(),
  severity: z.enum(['critical', 'major', 'minor']).optional(),
  notes: z.string().optional(),
  inspector_id: z.string(),
  checked_at: z.date(),
});

export type QualityCheck = z.infer<typeof QualityCheckSchema>;

export const DefectSchema = z.object({
  id: z.string(),
  part_id: z.string(),
  job_id: z.string(),
  defect_type: z.string(),
  severity: z.enum(['critical', 'major', 'minor']),
  description: z.string(),
  root_cause: z.string().optional(),
  corrective_action: z.string().optional(),
  detected_at: z.date(),
  resolved_at: z.date().optional(),
  prevention_measure: z.string().optional(),
});

export type Defect = z.infer<typeof DefectSchema>;

export const QualityMetricsSchema = z.object({
  factory_id: z.string(),
  date: z.date(),
  total_inspections: z.number(),
  passed_inspections: z.number(),
  failed_inspections: z.number(),
  defect_rate: z.number(),
  critical_defects: z.number(),
  major_defects: z.number(),
  minor_defects: z.number(),
  first_pass_yield: z.number(),
  rework_rate: z.number(),
  cost_of_quality: z.number(),
  trending: z.enum(['improving', 'stable', 'declining']),
});

export type QualityMetrics = z.infer<typeof QualityMetricsSchema>;

export const AuditSchema = z.object({
  id: z.string(),
  factory_id: z.string().optional(),
  supplier_id: z.string().optional(),
  audit_type: z.enum(['internal', 'supplier', 'third_party', 'compliance']),
  audit_date: z.date(),
  auditor_id: z.string(),
  findings: z.array(z.object({
    category: z.string(),
    finding: z.string(),
    severity: z.enum(['critical', 'major', 'minor']),
    evidence: z.string().optional(),
  })),
  score: z.number(),
  status: z.enum(['completed', 'in_progress', 'pending']),
  corrective_actions: z.array(z.object({
    finding_id: z.string(),
    action: z.string(),
    due_date: z.date(),
    status: z.enum(['open', 'closed']),
  })).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type Audit = z.infer<typeof AuditSchema>;
