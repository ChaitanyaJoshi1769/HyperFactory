import { TimeoutError } from './errors';

export interface RetryOptions {
  maxAttempts?: number;
  delayMs?: number;
  backoffMultiplier?: number;
  maxDelayMs?: number;
  shouldRetry?: (error: Error) => boolean;
}

const defaultOptions: Required<RetryOptions> = {
  maxAttempts: 3,
  delayMs: 1000,
  backoffMultiplier: 2,
  maxDelayMs: 30000,
  shouldRetry: () => true,
};

export const retry = async <T>(
  fn: () => Promise<T>,
  options?: RetryOptions
): Promise<T> => {
  const opts = { ...defaultOptions, ...options };
  let lastError: Error | undefined;
  let delayMs = opts.delayMs;

  for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt === opts.maxAttempts || !opts.shouldRetry(lastError)) {
        throw lastError;
      }

      await new Promise((resolve) => setTimeout(resolve, delayMs));
      delayMs = Math.min(delayMs * opts.backoffMultiplier, opts.maxDelayMs);
    }
  }

  throw lastError || new Error('Retry failed');
};

export const retryWithTimeout = async <T>(
  fn: () => Promise<T>,
  timeoutMs: number,
  options?: RetryOptions
): Promise<T> => {
  return retry(
    () =>
      Promise.race([
        fn(),
        new Promise<T>((_, reject) =>
          setTimeout(() => reject(new TimeoutError('Operation timed out')), timeoutMs)
        ),
      ]),
    options
  );
};

export const exponentialBackoff = (attempt: number, baseDelay = 1000): number => {
  return Math.min(baseDelay * Math.pow(2, attempt - 1), 30000);
};
