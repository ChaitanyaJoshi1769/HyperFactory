import { z } from 'zod';

export const ShipmentStatusSchema = z.enum([
  'pending',
  'picked',
  'packed',
  'shipped',
  'in_transit',
  'delivered',
  'returned',
  'cancelled',
]);

export type ShipmentStatus = z.infer<typeof ShipmentStatusSchema>;

export const CarrierSchema = z.enum([
  'fedex',
  'ups',
  'usps',
  'dhl',
  'amazon',
  'local_courier',
  'air_freight',
  'sea_freight',
  'rail',
  'trucking',
]);

export type Carrier = z.infer<typeof CarrierSchema>;

export const ShipmentSchema = z.object({
  id: z.string(),
  order_id: z.string(),
  status: ShipmentStatusSchema,
  origin: z.object({
    facility_id: z.string(),
    address: z.string(),
    country: z.string(),
  }),
  destination: z.object({
    facility_id: z.string(),
    address: z.string(),
    country: z.string(),
  }),
  carrier: CarrierSchema,
  tracking_number: z.string(),
  items: z.array(z.object({
    part_id: z.string(),
    quantity: z.number(),
    weight_kg: z.number().optional(),
  })),
  total_weight_kg: z.number(),
  total_volume_m3: z.number().optional(),
  cost: z.number(),
  estimated_delivery_date: z.date(),
  actual_delivery_date: z.date().optional(),
  events: z.array(z.object({
    event_type: z.string(),
    timestamp: z.date(),
    location: z.string(),
    details: z.string().optional(),
  })).optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type Shipment = z.infer<typeof ShipmentSchema>;

export const WarehouseSchema = z.object({
  id: z.string(),
  name: z.string(),
  location: z.object({
    country: z.string(),
    region: z.string(),
    city: z.string(),
    address: z.string(),
    latitude: z.number().optional(),
    longitude: z.number().optional(),
  }),
  capacity_cubic_meters: z.number(),
  current_utilization_cubic_meters: z.number(),
  inventory_items: z.array(z.string()),
  manager_id: z.string(),
  operating_hours: z.string().optional(),
  climate_controlled: z.boolean(),
  security_rating: z.number(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type Warehouse = z.infer<typeof WarehouseSchema>;

export const LogisticsNetworkSchema = z.object({
  id: z.string(),
  name: z.string(),
  warehouses: z.array(z.string()),
  factories: z.array(z.string()),
  distribution_centers: z.array(z.string()),
  carriers: z.array(CarrierSchema),
  shipments: z.array(z.string()),
  total_inventory_value: z.number(),
  average_delivery_time_days: z.number(),
  on_time_delivery_rate: z.number(),
});

export type LogisticsNetwork = z.infer<typeof LogisticsNetworkSchema>;

export const RouteOptimizationSchema = z.object({
  id: z.string(),
  shipment_id: z.string(),
  origin: z.string(),
  destination: z.string(),
  primary_route: z.array(z.object({
    waypoint: z.string(),
    distance_km: z.number(),
    estimated_time_hours: z.number(),
  })),
  alternative_routes: z.array(z.array(z.object({
    waypoint: z.string(),
    distance_km: z.number(),
    estimated_time_hours: z.number(),
  }))).optional(),
  total_distance_km: z.number(),
  total_estimated_time_hours: z.number(),
  estimated_cost: z.number(),
  emissions_kg_co2: z.number().optional(),
  optimization_score: z.number(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type RouteOptimization = z.infer<typeof RouteOptimizationSchema>;
