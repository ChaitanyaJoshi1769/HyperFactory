import { z } from 'zod';

export const RFQStatusSchema = z.enum([
  'draft',
  'sent',
  'received',
  'evaluating',
  'accepted',
  'rejected',
  'expired',
]);

export type RFQStatus = z.infer<typeof RFQStatusSchema>;

export const RFQSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  part_id: z.string(),
  quantity: z.number(),
  required_delivery_date: z.date(),
  status: RFQStatusSchema,
  suppliers_invited: z.array(z.string()),
  quotes_received: z.array(z.string()),
  target_price: z.number().optional(),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  requirements: z.record(z.string(), z.unknown()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type RFQ = z.infer<typeof RFQSchema>;

export const BOMSchema = z.object({
  id: z.string(),
  assembly_id: z.string(),
  revision: z.string(),
  items: z.array(z.object({
    line_number: z.number(),
    part_id: z.string(),
    quantity: z.number(),
    unit_of_measure: z.string(),
    supplier_id: z.string().optional(),
    unit_cost: z.number().optional(),
    total_cost: z.number().optional(),
    lead_time_days: z.number().optional(),
    notes: z.string().optional(),
  })),
  total_cost: z.number(),
  total_lead_time_days: z.number(),
  optimized: z.boolean(),
  optimization_savings: z.number().optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type BOM = z.infer<typeof BOMSchema>;

export const InventoryItemSchema = z.object({
  id: z.string(),
  part_id: z.string(),
  warehouse_id: z.string(),
  quantity_on_hand: z.number(),
  quantity_allocated: z.number(),
  quantity_available: z.number(),
  reorder_point: z.number(),
  reorder_quantity: z.number(),
  unit_cost: z.number(),
  total_value: z.number(),
  last_received_date: z.date().optional(),
  expiration_date: z.date().optional(),
  storage_location: z.string().optional(),
  batch_numbers: z.array(z.string()).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type InventoryItem = z.infer<typeof InventoryItemSchema>;

export const PurchaseRequisitionSchema = z.object({
  id: z.string(),
  requester_id: z.string(),
  status: z.enum(['draft', 'submitted', 'approved', 'ordered', 'received', 'cancelled']),
  items: z.array(z.object({
    part_id: z.string(),
    quantity: z.number(),
    unit_cost: z.number().optional(),
  })),
  required_date: z.date(),
  business_justification: z.string().optional(),
  cost_center: z.string().optional(),
  approval_chain: z.array(z.object({
    approver_id: z.string(),
    status: z.enum(['pending', 'approved', 'rejected']),
    timestamp: z.date().optional(),
  })).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type PurchaseRequisition = z.infer<typeof PurchaseRequisitionSchema>;
