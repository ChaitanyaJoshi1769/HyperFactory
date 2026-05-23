import { ProductionJob, FactoryTelemetry, FactorySchedule, MaintenanceTask } from '@hyperfactory/manufacturing-types';
import { createChildLogger, generateId } from '@hyperfactory/shared';

const logger = createChildLogger('factory:orchestrator');

export interface OrchestrationCommand {
  command_id: string;
  timestamp: Date;
  target_machine_id: string;
  job_id: string;
  action: 'start' | 'pause' | 'resume' | 'stop' | 'abort';
  priority: number;
}

export interface OrchestrationStatus {
  factory_id: string;
  active_jobs: number;
  queued_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  current_utilization: number;
  estimated_throughput: number;
  next_maintenance_due?: Date;
}

export class FactoryOrchestrator {
  private activeJobs: Map<string, ProductionJob> = new Map();
  private jobQueue: ProductionJob[] = [];
  private commandHistory: OrchestrationCommand[] = [];

  queueJob(job: ProductionJob): void {
    logger.debug({ jobId: job.id }, 'Queuing production job');
    this.jobQueue.push(job);
  }

  startJob(jobId: string, machineId: string): OrchestrationCommand {
    logger.info({ jobId, machineId }, 'Starting job on machine');

    const command: OrchestrationCommand = {
      command_id: generateId('cmd'),
      timestamp: new Date(),
      target_machine_id: machineId,
      job_id: jobId,
      action: 'start',
      priority: 1,
    };

    this.commandHistory.push(command);
    this.activeJobs.set(jobId, this.jobQueue.find((j) => j.id === jobId)!);

    return command;
  }

  pauseJob(jobId: string): OrchestrationCommand {
    logger.info({ jobId }, 'Pausing job');

    const job = this.activeJobs.get(jobId);
    if (!job) throw new Error(`Job ${jobId} not found`);

    const command: OrchestrationCommand = {
      command_id: generateId('cmd'),
      timestamp: new Date(),
      target_machine_id: job.assigned_machine_id || '',
      job_id: jobId,
      action: 'pause',
      priority: 2,
    };

    this.commandHistory.push(command);

    return command;
  }

  resumeJob(jobId: string): OrchestrationCommand {
    logger.info({ jobId }, 'Resuming job');

    const job = this.activeJobs.get(jobId);
    if (!job) throw new Error(`Job ${jobId} not found`);

    const command: OrchestrationCommand = {
      command_id: generateId('cmd'),
      timestamp: new Date(),
      target_machine_id: job.assigned_machine_id || '',
      job_id: jobId,
      action: 'resume',
      priority: 2,
    };

    this.commandHistory.push(command);

    return command;
  }

  abortJob(jobId: string, reason: string): OrchestrationCommand {
    logger.warn({ jobId, reason }, 'Aborting job');

    const job = this.activeJobs.get(jobId);
    if (!job) throw new Error(`Job ${jobId} not found`);

    const command: OrchestrationCommand = {
      command_id: generateId('cmd'),
      timestamp: new Date(),
      target_machine_id: job.assigned_machine_id || '',
      job_id: jobId,
      action: 'abort',
      priority: 3,
    };

    this.commandHistory.push(command);
    this.activeJobs.delete(jobId);

    return command;
  }

  getStatus(factoryId: string): OrchestrationStatus {
    const completedJobs = this.commandHistory.filter((c) => c.action === 'stop').length;
    const failedJobs = this.commandHistory.filter((c) => c.action === 'abort').length;

    return {
      factory_id: factoryId,
      active_jobs: this.activeJobs.size,
      queued_jobs: this.jobQueue.length,
      completed_jobs: completedJobs,
      failed_jobs: failedJobs,
      current_utilization: (this.activeJobs.size / (this.activeJobs.size + this.jobQueue.length)) * 100 || 0,
      estimated_throughput: this.estimateThroughput(),
    };
  }

  private estimateThroughput(): number {
    if (this.commandHistory.length === 0) return 0;

    const completedInLastHour = this.commandHistory.filter((c) => {
      const oneHourAgo = new Date(Date.now() - 3600000);
      return c.timestamp > oneHourAgo && c.action === 'stop';
    }).length;

    return completedInLastHour;
  }

  getCommandHistory(limit: number = 100): OrchestrationCommand[] {
    return this.commandHistory.slice(-limit);
  }
}
