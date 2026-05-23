import { z } from 'zod';

export const SupplierTypeSchema = z.enum([
  'cnc_shop',
  'pcb_fab',
  'sheet_metal_vendor',
  'injection_molding',
  'assembly_house',
  'logistics_provider',
  'material_supplier',
  'finishing_shop',
  'testing_lab',
  'additive_manufacturing',
  'robotics_integrator',
  'electronics_supplier',
]);

export type SupplierType = z.infer<typeof SupplierTypeSchema>;

export const SupplierCapabilitySchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
  process: z.string().optional(),
  min_order_quantity: z.number(),
  max_annual_capacity: z.number(),
  lead_time_days: z.object({
    standard: z.number(),
    expedited: z.number().optional(),
  }),
  cost_per_unit_base: z.number(),
  volume_discounts: z.array(z.object({
    min_quantity: z.number(),
    discount_percent: z.number(),
  })).optional(),
  precision_capability_microns: z.number().optional(),
  material_capabilities: z.array(z.string()).optional(),
  certifications: z.array(z.string()),
  properties: z.record(z.string(), z.unknown()).optional(),
});

export type SupplierCapability = z.infer<typeof SupplierCapabilitySchema>;

export const SupplierSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: SupplierTypeSchema,
  location: z.object({
    country: z.string(),
    region: z.string(),
    city: z.string(),
  }),
  contact_email: z.string().email(),
  contact_phone: z.string().optional(),
  capabilities: z.array(SupplierCapabilitySchema),
  quality_score: z.number().min(0).max(100),
  reliability_score: z.number().min(0).max(100),
  cost_competitiveness_score: z.number().min(0).max(100),
  on_time_delivery_rate: z.number().min(0).max(100),
  defect_rate: z.number().min(0).max(100),
  minimum_order_value: z.number().optional(),
  payment_terms: z.string(),
  lead_time_variability: z.number(),
  certifications: z.array(z.string()),
  quality_audits: z.array(z.object({
    date: z.date(),
    score: z.number(),
    auditor: z.string(),
  })).optional(),
  properties: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type Supplier = z.infer<typeof SupplierSchema>;

export const SupplierQuoteSchema = z.object({
  id: z.string(),
  supplier_id: z.string(),
  part_id: z.string(),
  capability_id: z.string(),
  quantity: z.number(),
  unit_price: z.number(),
  total_price: z.number(),
  lead_time_days: z.number(),
  minimum_order_quantity: z.number(),
  volume_available: z.number(),
  expiration_date: z.date(),
  terms: z.string().optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type SupplierQuote = z.infer<typeof SupplierQuoteSchema>;

export const ProcurementOrderSchema = z.object({
  id: z.string(),
  supplier_id: z.string(),
  supplier_quote_id: z.string(),
  status: z.enum(['draft', 'sent', 'confirmed', 'in_production', 'shipped', 'delivered', 'cancelled']),
  items: z.array(z.object({
    part_id: z.string(),
    quantity: z.number(),
    unit_price: z.number(),
  })),
  total_value: z.number(),
  expected_delivery_date: z.date(),
  actual_delivery_date: z.date().optional(),
  payment_status: z.enum(['pending', 'partial', 'paid', 'overdue']),
  created_at: z.date(),
  updated_at: z.date(),
});

export type ProcurementOrder = z.infer<typeof ProcurementOrderSchema>;
