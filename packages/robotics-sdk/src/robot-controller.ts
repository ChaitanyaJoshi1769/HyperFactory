import { RobotConfig, RobotTask, RobotTelemetry } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('robotics:controller');

export class RobotController {
  private robot: RobotConfig;
  private currentTask?: RobotTask;
  private telemetryHistory: RobotTelemetry[] = [];

  constructor(robot: RobotConfig) {
    this.robot = robot;
    logger.info({ robotId: robot.id, model: robot.model }, 'Robot controller initialized');
  }

  async executeTask(task: RobotTask): Promise<void> {
    logger.info({ taskId: task.id, type: task.task_type }, 'Starting task execution');
    this.currentTask = { ...task, status: 'executing' };

    try {
      await this.simulateTaskExecution(task);
      this.currentTask.status = 'completed';
      this.currentTask.success = true;
    } catch (error) {
      this.currentTask.status = 'failed';
      this.currentTask.success = false;
      this.currentTask.error_message = String(error);
      logger.error({ taskId: task.id, error }, 'Task execution failed');
    }
  }

  private async simulateTaskExecution(task: RobotTask): Promise<void> {
    const duration = task.estimated_duration_seconds || 10;
    await new Promise((resolve) => setTimeout(resolve, Math.min(duration * 100, 1000)));
  }

  getTelemetry(): RobotTelemetry {
    return {
      robot_id: this.robot.id,
      timestamp: new Date(),
      current_position: { x: 0, y: 0, z: 0 },
      operating_time_hours: 100,
      cycle_count: 5000,
      error_count: 2,
      status: this.robot.status,
    };
  }

  recordTelemetry(telemetry: RobotTelemetry): void {
    this.telemetryHistory.push(telemetry);
    if (this.telemetryHistory.length > 1000) {
      this.telemetryHistory = this.telemetryHistory.slice(-1000);
    }
  }

  getCurrentTask(): RobotTask | undefined {
    return this.currentTask;
  }

  getStatus(): RobotConfig['status'] {
    return this.robot.status;
  }
}
