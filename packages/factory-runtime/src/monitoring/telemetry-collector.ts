import { FactoryTelemetry, ProductionLine } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('factory:telemetry');

export interface TelemetryEvent {
  factory_id: string;
  timestamp: Date;
  metric_name: string;
  metric_value: number;
  tags: Record<string, string>;
}

export class TelemetryCollector {
  private events: TelemetryEvent[] = [];
  private metricsBuffer: Map<string, number> = new Map();

  recordEvent(event: TelemetryEvent): void {
    logger.debug(
      {
        factory: event.factory_id,
        metric: event.metric_name,
        value: event.metric_value,
      },
      'Recording telemetry event'
    );

    this.events.push(event);
    this.metricsBuffer.set(`${event.factory_id}:${event.metric_name}`, event.metric_value);

    // Keep only recent events (last 1000)
    if (this.events.length > 1000) {
      this.events = this.events.slice(-1000);
    }
  }

  recordMetric(factoryId: string, metricName: string, value: number, tags?: Record<string, string>): void {
    const event: TelemetryEvent = {
      factory_id: factoryId,
      timestamp: new Date(),
      metric_name: metricName,
      metric_value: value,
      tags: tags || {},
    };

    this.recordEvent(event);
  }

  getMetricValue(factoryId: string, metricName: string): number | undefined {
    return this.metricsBuffer.get(`${factoryId}:${metricName}`);
  }

  getFactoryTelemetry(factoryId: string): Partial<FactoryTelemetry> {
    const machinesOperational = this.getMetricValue(factoryId, 'machines_operational') || 0;
    const machinesInMaintenance = this.getMetricValue(factoryId, 'machines_in_maintenance') || 0;
    const machinesOffline = this.getMetricValue(factoryId, 'machines_offline') || 0;
    const powerConsumption = this.getMetricValue(factoryId, 'power_consumption_kw') || 0;
    const defectRate = this.getMetricValue(factoryId, 'defect_rate') || 0;

    return {
      factory_id: factoryId,
      timestamp: new Date(),
      machines_operational: Math.round(machinesOperational),
      machines_in_maintenance: Math.round(machinesInMaintenance),
      machines_offline: Math.round(machinesOffline),
      current_power_consumption_kw: powerConsumption,
      defect_rate: defectRate,
    };
  }

  getAverageMetric(factoryId: string, metricName: string, timeWindowMinutes: number = 60): number {
    const cutoff = new Date(Date.now() - timeWindowMinutes * 60000);

    const relevantEvents = this.events.filter(
      (e) => e.factory_id === factoryId && e.metric_name === metricName && e.timestamp > cutoff
    );

    if (relevantEvents.length === 0) return 0;

    const sum = relevantEvents.reduce((total, e) => total + e.metric_value, 0);
    return sum / relevantEvents.length;
  }

  getEventHistory(factoryId: string, limit: number = 100): TelemetryEvent[] {
    return this.events
      .filter((e) => e.factory_id === factoryId)
      .slice(-limit);
  }

  getEventsSince(factoryId: string, timestamp: Date): TelemetryEvent[] {
    return this.events.filter((e) => e.factory_id === factoryId && e.timestamp > timestamp);
  }

  clearOldEvents(olderThanMinutes: number): void {
    const cutoff = new Date(Date.now() - olderThanMinutes * 60000);
    const initialCount = this.events.length;

    this.events = this.events.filter((e) => e.timestamp > cutoff);

    logger.info(
      { removed: initialCount - this.events.length, kept: this.events.length },
      'Cleaned up old telemetry events'
    );
  }
}
