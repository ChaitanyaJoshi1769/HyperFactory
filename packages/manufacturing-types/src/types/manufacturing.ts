import { z } from 'zod';

export const ManufacturingProcessSchema = z.enum([
  'cnc_machining',
  'turning',
  'milling',
  'drilling',
  'grinding',
  'sheet_metal_fabrication',
  'welding',
  'injection_molding',
  'casting',
  'stamping',
  'pcb_fabrication',
  'pcb_assembly',
  'additive_manufacturing_fdm',
  'additive_manufacturing_sla',
  'additive_manufacturing_sls',
  'tig_welding',
  'mig_welding',
  'robotic_assembly',
  'manual_assembly',
  'surface_treatment',
  'anodizing',
  'plating',
  'painting',
  'quality_inspection',
]);

export type ManufacturingProcess = z.infer<typeof ManufacturingProcessSchema>;

export const MachineSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
  process: ManufacturingProcessSchema,
  location: z.string(),
  status: z.enum(['idle', 'running', 'maintenance', 'offline']),
  capacity_per_hour: z.number(),
  power_consumption_kw: z.number(),
  precision_microns: z.number().optional(),
  max_dimensions: z.object({
    x: z.number(),
    y: z.number(),
    z: z.number(),
  }).optional(),
  material_compatibility: z.array(z.string()),
  certifications: z.array(z.string()).optional(),
  last_maintenance: z.date().optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type Machine = z.infer<typeof MachineSchema>;

export const ProductionJobSchema = z.object({
  id: z.string(),
  part_id: z.string(),
  status: z.enum(['queued', 'in_progress', 'completed', 'failed', 'on_hold']),
  quantity: z.number(),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  assigned_machine_id: z.string().optional(),
  processes: z.array(z.object({
    process: ManufacturingProcessSchema,
    sequence: z.number(),
    estimated_duration_minutes: z.number(),
    actual_duration_minutes: z.number().optional(),
    status: z.enum(['pending', 'in_progress', 'completed', 'failed']),
  })),
  start_time: z.date().optional(),
  completion_time: z.date().optional(),
  estimated_cost: z.number(),
  actual_cost: z.number().optional(),
  quality_checks: z.array(z.object({
    check_id: z.string(),
    parameter: z.string(),
    target_value: z.number(),
    tolerance: z.number(),
    actual_value: z.number().optional(),
    passed: z.boolean().optional(),
  })).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type ProductionJob = z.infer<typeof ProductionJobSchema>;

export const FactoryConfigSchema = z.object({
  id: z.string(),
  name: z.string(),
  location: z.string(),
  machines: z.array(MachineSchema),
  capacity_utilization: z.number(),
  power_consumption_kwh: z.number(),
  production_efficiency: z.number(),
  defect_rate: z.number(),
  average_lead_time_days: z.number(),
  throughput_parts_per_day: z.number(),
});

export type FactoryConfig = z.infer<typeof FactoryConfigSchema>;
