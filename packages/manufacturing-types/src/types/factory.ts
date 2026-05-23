import { z } from 'zod';

export const FactoryStateSchema = z.enum([
  'idle',
  'operating',
  'maintenance',
  'emergency_stop',
  'offline',
]);

export type FactoryState = z.infer<typeof FactoryStateSchema>;

export const ProductionLineSchema = z.object({
  id: z.string(),
  name: z.string(),
  machines: z.array(z.string()),
  primary_process: z.string(),
  throughput_per_hour: z.number(),
  status: z.enum(['idle', 'running', 'maintenance', 'offline']),
  current_job_id: z.string().optional(),
  queue_depth: z.number(),
  estimated_completion_time: z.date().optional(),
});

export type ProductionLine = z.infer<typeof ProductionLineSchema>;

export const FactoryTelemetrySchema = z.object({
  factory_id: z.string(),
  timestamp: z.date(),
  machines_operational: z.number(),
  machines_in_maintenance: z.number(),
  machines_offline: z.number(),
  production_lines: z.array(ProductionLineSchema),
  current_power_consumption_kw: z.number(),
  total_daily_production: z.number(),
  average_cycle_time_minutes: z.number(),
  defect_rate: z.number(),
  utilization_rate: z.number(),
  queue_depth: z.number(),
  estimated_throughput: z.number(),
});

export type FactoryTelemetry = z.infer<typeof FactoryTelemetrySchema>;

export const FactoryMetricsSchema = z.object({
  factory_id: z.string(),
  date: z.date(),
  parts_produced: z.number(),
  parts_defective: z.number(),
  defect_rate: z.number(),
  average_cycle_time_minutes: z.number(),
  total_power_consumption_kwh: z.number(),
  total_cost: z.number(),
  average_cost_per_part: z.number(),
  utilization_rate: z.number(),
  on_time_delivery_rate: z.number(),
  overall_equipment_effectiveness: z.number(),
  production_efficiency: z.number(),
  quality_score: z.number(),
  safety_incidents: z.number(),
});

export type FactoryMetrics = z.infer<typeof FactoryMetricsSchema>;

export const FactoryScheduleSchema = z.object({
  id: z.string(),
  factory_id: z.string(),
  production_line_id: z.string(),
  scheduled_jobs: z.array(z.object({
    job_id: z.string(),
    sequence: z.number(),
    scheduled_start: z.date(),
    scheduled_end: z.date(),
    priority: z.enum(['low', 'medium', 'high', 'critical']),
  })),
  shift_start: z.date(),
  shift_end: z.date(),
  shift_type: z.enum(['morning', 'afternoon', 'night']),
  optimization_score: z.number(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type FactorySchedule = z.infer<typeof FactoryScheduleSchema>;

export const MaintenanceTaskSchema = z.object({
  id: z.string(),
  machine_id: z.string(),
  task_type: z.enum(['preventive', 'corrective', 'predictive', 'emergency']),
  status: z.enum(['scheduled', 'in_progress', 'completed', 'cancelled']),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  description: z.string(),
  estimated_duration_minutes: z.number(),
  actual_duration_minutes: z.number().optional(),
  scheduled_start: z.date(),
  scheduled_end: z.date(),
  actual_start: z.date().optional(),
  actual_end: z.date().optional(),
  assigned_technician: z.string().optional(),
  parts_replaced: z.array(z.string()).optional(),
  cost: z.number().optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type MaintenanceTask = z.infer<typeof MaintenanceTaskSchema>;
