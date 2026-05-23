export class HyperFactoryError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500,
    public context?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'HyperFactoryError';
  }
}

export class ValidationError extends HyperFactoryError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'VALIDATION_ERROR', 400, context);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends HyperFactoryError {
  constructor(resource: string, id: string) {
    super(`${resource} not found: ${id}`, 'NOT_FOUND', 404, { resource, id });
    this.name = 'NotFoundError';
  }
}

export class ConflictError extends HyperFactoryError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'CONFLICT', 409, context);
    this.name = 'ConflictError';
  }
}

export class UnauthorizedError extends HyperFactoryError {
  constructor(message: string = 'Unauthorized') {
    super(message, 'UNAUTHORIZED', 401);
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends HyperFactoryError {
  constructor(message: string = 'Forbidden') {
    super(message, 'FORBIDDEN', 403);
    this.name = 'ForbiddenError';
  }
}

export class TimeoutError extends HyperFactoryError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'TIMEOUT', 408, context);
    this.name = 'TimeoutError';
  }
}

export class ExternalServiceError extends HyperFactoryError {
  constructor(service: string, message: string, statusCode?: number) {
    super(
      `External service error from ${service}: ${message}`,
      'EXTERNAL_SERVICE_ERROR',
      statusCode || 502,
      { service }
    );
    this.name = 'ExternalServiceError';
  }
}
