import { ProductionJob, Machine } from '@hyperfactory/manufacturing-types';
import { createChildLogger, generateId } from '@hyperfactory/shared';

const logger = createChildLogger('factory:scheduler');

export interface ScheduleResult {
  schedule_id: string;
  total_duration_minutes: number;
  machine_utilization_percent: number;
  job_order: string[];
  estimated_completion_time: Date;
  optimization_score: number;
}

export class JobScheduler {
  scheduleJobs(jobs: ProductionJob[], machines: Machine[]): ScheduleResult {
    logger.debug({ jobCount: jobs.length, machineCount: machines.length }, 'Scheduling jobs');

    const scheduleId = generateId('schedule');

    // Sort jobs by priority and quantity
    const sortedJobs = [...jobs].sort((a, b) => {
      const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
      const aPriority = priorityOrder[a.priority];
      const bPriority = priorityOrder[b.priority];

      if (aPriority !== bPriority) return aPriority - bPriority;
      return b.quantity - a.quantity;
    });

    // Assign jobs to machines
    const machineQueues = this.assignJobsToMachines(sortedJobs, machines);

    // Calculate metrics
    const totalDuration = this.calculateTotalDuration(machineQueues);
    const utilization = this.calculateMachineUtilization(machines, totalDuration);
    const optimizationScore = this.calculateOptimizationScore(machineQueues, machines);

    const completionTime = new Date();
    completionTime.setMinutes(completionTime.getMinutes() + totalDuration);

    return {
      schedule_id: scheduleId,
      total_duration_minutes: Math.ceil(totalDuration),
      machine_utilization_percent: Math.round(utilization * 100) / 100,
      job_order: sortedJobs.map((j) => j.id),
      estimated_completion_time: completionTime,
      optimization_score: Math.round(optimizationScore),
    };
  }

  private assignJobsToMachines(
    jobs: ProductionJob[],
    machines: Machine[]
  ): Map<string, ProductionJob[]> {
    const queues = new Map<string, ProductionJob[]>();

    // Initialize machine queues
    for (const machine of machines) {
      queues.set(machine.id, []);
    }

    // Greedy assignment - assign to least loaded machine
    for (const job of jobs) {
      let minLoadMachine = '';
      let minLoad = Infinity;

      for (const [machineId, queue] of queues.entries()) {
        const load = queue.reduce((sum, j) => sum + j.quantity, 0);
        if (load < minLoad) {
          minLoad = load;
          minLoadMachine = machineId;
        }
      }

      if (minLoadMachine) {
        queues.get(minLoadMachine)!.push(job);
      }
    }

    return queues;
  }

  private calculateTotalDuration(machineQueues: Map<string, ProductionJob[]>): number {
    let maxDuration = 0;

    for (const jobs of machineQueues.values()) {
      let duration = 0;
      for (const job of jobs) {
        const totalProcessTime = job.processes.reduce((sum, p) => sum + p.estimated_duration_minutes, 0);
        duration += totalProcessTime;
      }
      maxDuration = Math.max(maxDuration, duration);
    }

    return maxDuration;
  }

  private calculateMachineUtilization(machines: Machine[], totalDuration: number): number {
    if (totalDuration === 0) return 0;

    const totalCapacity = machines.length * totalDuration * 60;
    const utilized = machines.reduce((sum, m) => sum + m.capacity_per_hour * totalDuration, 0);

    return (utilized / totalCapacity) * 100;
  }

  private calculateOptimizationScore(
    machineQueues: Map<string, ProductionJob[]>,
    machines: Machine[]
  ): number {
    // Score based on load balancing and utilization
    const loads: number[] = [];

    for (const jobs of machineQueues.values()) {
      const load = jobs.reduce((sum, j) => sum + j.quantity, 0);
      loads.push(load);
    }

    if (loads.length === 0) return 0;

    const avgLoad = loads.reduce((a, b) => a + b, 0) / loads.length;
    const variance = loads.reduce((sum, load) => sum + Math.pow(load - avgLoad, 2), 0) / loads.length;
    const stdDev = Math.sqrt(variance);

    // Lower std dev = better balance = higher score
    return Math.max(0, 100 - stdDev * 10);
  }
}
