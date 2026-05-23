import { z } from 'zod';

export const HardwarePartTypeSchema = z.enum([
  'mechanical',
  'pcb',
  'sheet_metal',
  'injection_molded',
  'cnc_machined',
  'additive_manufactured',
  'cast',
  'stamped',
  'assembly',
  'robotics_component',
]);

export type HardwarePartType = z.infer<typeof HardwarePartTypeSchema>;

export const MaterialSchema = z.object({
  id: z.string(),
  name: z.string(),
  density: z.number().optional(),
  cost_per_kg: z.number(),
  tensile_strength: z.number().optional(),
  yield_strength: z.number().optional(),
  thermal_conductivity: z.number().optional(),
  machinability_index: z.number().optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type Material = z.infer<typeof MaterialSchema>;

export const ToleranceSchema = z.object({
  dimension: z.string(),
  nominal_value: z.number(),
  upper_tolerance: z.number(),
  lower_tolerance: z.number(),
  tolerance_type: z.enum(['bilateral', 'unilateral', 'limit']),
  tolerance_grade: z.enum(['IT01', 'IT0', 'IT1', 'IT2', 'IT3', 'IT4', 'IT5', 'IT6', 'IT7', 'IT8', 'IT9', 'IT10', 'IT11', 'IT12', 'IT13', 'IT14', 'IT15', 'IT16']).optional(),
});

export type Tolerance = z.infer<typeof ToleranceSchema>;

export const SurfaceFinishSchema = z.object({
  id: z.string(),
  name: z.string(),
  roughness_ra: z.number(),
  roughness_rz: z.number().optional(),
  process: z.string(),
  cost_multiplier: z.number(),
});

export type SurfaceFinish = z.infer<typeof SurfaceFinishSchema>;

export const HardwarePartSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: HardwarePartTypeSchema,
  revision: z.string(),
  description: z.string().optional(),
  material: MaterialSchema,
  weight_kg: z.number(),
  tolerances: z.array(ToleranceSchema),
  surface_finishes: z.array(SurfaceFinishSchema),
  cad_model_url: z.string(),
  cad_model_hash: z.string(),
  step_file_url: z.string().optional(),
  stl_file_url: z.string().optional(),
  drawing_pdf_url: z.string().optional(),
  estimated_cost: z.number(),
  estimated_lead_time_days: z.number(),
  volume: z.number().optional(),
  surface_area: z.number().optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type HardwarePart = z.infer<typeof HardwarePartSchema>;

export const AssemblySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  parts: z.array(z.object({
    part_id: z.string(),
    quantity: z.number(),
    position: z.object({
      x: z.number(),
      y: z.number(),
      z: z.number(),
    }).optional(),
  })),
  assembly_time_minutes: z.number(),
  estimated_cost: z.number(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type Assembly = z.infer<typeof AssemblySchema>;

export const PCBSchema = z.object({
  id: z.string(),
  name: z.string(),
  revision: z.string(),
  gerber_files_url: z.string(),
  bom_url: z.string(),
  layer_count: z.number(),
  surface_finish: z.string(),
  material: z.enum(['FR4', 'FR2', 'Aluminum', 'Polyimide']),
  thickness_mm: z.number(),
  min_trace_width_mm: z.number(),
  min_via_diameter_mm: z.number(),
  estimated_cost: z.number(),
  estimated_lead_time_days: z.number(),
  properties: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type PCB = z.infer<typeof PCBSchema>;
