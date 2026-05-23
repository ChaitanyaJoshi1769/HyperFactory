import { createChildLogger } from '@hyperfactory/shared';

const logger = createChildLogger('robotics:motion');

export interface Waypoint {
  x: number;
  y: number;
  z: number;
  speed_mm_per_sec: number;
}

export interface MotionPlan {
  waypoints: Waypoint[];
  total_distance_mm: number;
  estimated_time_seconds: number;
  collision_free: boolean;
}

export class MotionPlanner {
  planMotion(
    startPos: [number, number, number],
    endPos: [number, number, number],
    maxSpeed: number
  ): MotionPlan {
    logger.debug(
      { start: startPos, end: endPos, maxSpeed },
      'Planning robot motion'
    );

    const waypoints: Waypoint[] = [
      { x: startPos[0], y: startPos[1], z: startPos[2], speed_mm_per_sec: 0 },
      { x: endPos[0], y: endPos[1], z: endPos[2], speed_mm_per_sec: maxSpeed },
    ];

    const dx = endPos[0] - startPos[0];
    const dy = endPos[1] - startPos[1];
    const dz = endPos[2] - startPos[2];

    const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
    const time = distance / maxSpeed;

    return {
      waypoints,
      total_distance_mm: distance,
      estimated_time_seconds: time,
      collision_free: true,
    };
  }
}
