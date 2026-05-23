import { z } from 'zod';

export const RobotTypeSchema = z.enum([
  'articulated_arm',
  'scara',
  'delta',
  'cartesian',
  'humanoid',
  'mobile_manipulator',
  'mobile_base',
  'gripper',
  'cobot',
  'agv',
  'amr',
]);

export type RobotType = z.infer<typeof RobotTypeSchema>;

export const RobotConfigSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: RobotTypeSchema,
  model: z.string(),
  manufacturer: z.string(),
  payload_kg: z.number(),
  reach_mm: z.number(),
  repeatability_mm: z.number(),
  speed_mm_per_sec: z.number(),
  degrees_of_freedom: z.number(),
  control_system: z.string(),
  communication_protocol: z.array(z.string()),
  installed_tools: z.array(z.string()).optional(),
  status: z.enum(['idle', 'running', 'error', 'maintenance', 'offline']),
  properties: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type RobotConfig = z.infer<typeof RobotConfigSchema>;

export const RobotTaskSchema = z.object({
  id: z.string(),
  robot_id: z.string(),
  task_type: z.enum(['pick_place', 'assembly', 'welding', 'painting', 'quality_inspection', 'packaging', 'deburring', 'custom']),
  status: z.enum(['queued', 'executing', 'completed', 'failed', 'paused']),
  work_piece_id: z.string().optional(),
  trajectory: z.array(z.object({
    position: z.object({
      x: z.number(),
      y: z.number(),
      z: z.number(),
    }),
    rotation: z.object({
      roll: z.number(),
      pitch: z.number(),
      yaw: z.number(),
    }).optional(),
    speed: z.number(),
  })).optional(),
  estimated_duration_seconds: z.number(),
  actual_duration_seconds: z.number().optional(),
  success: z.boolean().optional(),
  error_message: z.string().optional(),
  quality_metrics: z.record(z.string(), z.number()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type RobotTask = z.infer<typeof RobotTaskSchema>;

export const RobotCellSchema = z.object({
  id: z.string(),
  name: z.string(),
  robots: z.array(RobotConfigSchema),
  conveyor_system: z.boolean(),
  vision_system: z.boolean(),
  safety_rating: z.string(),
  production_capacity_per_hour: z.number(),
  current_task: z.string().optional(),
  status: z.enum(['idle', 'running', 'maintenance', 'error', 'offline']),
  properties: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type RobotCell = z.infer<typeof RobotCellSchema>;

export const RobotTelemetrySchema = z.object({
  robot_id: z.string(),
  timestamp: z.date(),
  current_position: z.object({
    x: z.number(),
    y: z.number(),
    z: z.number(),
  }),
  current_rotation: z.object({
    roll: z.number(),
    pitch: z.number(),
    yaw: z.number(),
  }).optional(),
  joint_angles: z.array(z.number()).optional(),
  joint_torques: z.array(z.number()).optional(),
  gripper_force: z.number().optional(),
  current_task_id: z.string().optional(),
  operating_time_hours: z.number(),
  cycle_count: z.number(),
  error_count: z.number(),
  temperature_celsius: z.number().optional(),
  power_consumption_w: z.number().optional(),
  status: z.string(),
});

export type RobotTelemetry = z.infer<typeof RobotTelemetrySchema>;
