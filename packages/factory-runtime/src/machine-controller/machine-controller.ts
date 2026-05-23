import { Machine, ProductionJob } from '@hyperfactory/manufacturing-types';
import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('factory:machine-controller');

export interface MachineCommand {
  machine_id: string;
  command: 'start_job' | 'stop_job' | 'emergency_stop' | 'home' | 'tool_change' | 'spindle_on' | 'spindle_off';
  parameters?: Record<string, unknown>;
  timeout_seconds?: number;
}

export interface MachineResponse {
  machine_id: string;
  command_id: string;
  status: 'success' | 'failure' | 'timeout';
  result?: Record<string, unknown>;
  error?: string;
  timestamp: Date;
}

export class MachineController {
  private machineStates: Map<string, Machine> = new Map();

  registerMachine(machine: Machine): void {
    logger.info({ machineId: machine.id }, 'Registering machine with controller');
    this.machineStates.set(machine.id, machine);
  }

  sendCommand(machineId: string, command: MachineCommand): MachineResponse {
    logger.debug({ machineId, command: command.command }, 'Sending command to machine');

    const machine = this.machineStates.get(machineId);
    if (!machine) {
      throw new Error(`Machine ${machineId} not registered`);
    }

    // Simulate command execution
    const response: MachineResponse = {
      machine_id: machineId,
      command_id: `cmd-${Date.now()}`,
      status: this.executeCommand(machine, command),
      timestamp: new Date(),
    };

    return response;
  }

  private executeCommand(machine: Machine, command: MachineCommand): 'success' | 'failure' | 'timeout' {
    // Simplified command execution
    // In production, would communicate with actual machine controllers via:
    // - OPC UA
    // - MQTT
    // - HTTP REST
    // - Proprietary protocols

    switch (command.command) {
      case 'start_job':
        machine.status = 'running';
        return 'success';

      case 'stop_job':
        machine.status = 'idle';
        return 'success';

      case 'emergency_stop':
        machine.status = 'offline';
        logger.warn({ machineId: machine.id }, 'Emergency stop activated');
        return 'success';

      case 'home':
        return 'success';

      case 'tool_change':
        return 'success';

      case 'spindle_on':
        return 'success';

      case 'spindle_off':
        return 'success';

      default:
        return 'failure';
    }
  }

  getMachineStatus(machineId: string): Machine | undefined {
    return this.machineStates.get(machineId);
  }

  getAllMachineStatus(): Machine[] {
    return Array.from(this.machineStates.values());
  }

  updateMachineStatus(machineId: string, status: Machine['status']): void {
    const machine = this.machineStates.get(machineId);
    if (machine) {
      machine.status = status;
      logger.debug({ machineId, status }, 'Machine status updated');
    }
  }
}
