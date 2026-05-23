import { ValidationError } from './errors';

export const validateEmail = (email: string): boolean => {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
};

export const validateURL = (url: string): boolean => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

export const validateRequired = (value: unknown): boolean => {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string' && value.trim() === '') return false;
  if (Array.isArray(value) && value.length === 0) return false;
  return true;
};

export const validateRange = (
  value: number,
  min: number,
  max: number
): boolean => {
  return value >= min && value <= max;
};

export const validateMinLength = (value: string, minLength: number): boolean => {
  return value.length >= minLength;
};

export const validateMaxLength = (value: string, maxLength: number): boolean => {
  return value.length <= maxLength;
};

export const validatePattern = (value: string, pattern: RegExp): boolean => {
  return pattern.test(value);
};

export const assertRequired = (value: unknown, fieldName: string): void => {
  if (!validateRequired(value)) {
    throw new ValidationError(`${fieldName} is required`);
  }
};

export const assertEmail = (value: string, fieldName = 'Email'): void => {
  if (!validateEmail(value)) {
    throw new ValidationError(`${fieldName} is invalid`);
  }
};

export const assertRange = (
  value: number,
  min: number,
  max: number,
  fieldName = 'Value'
): void => {
  if (!validateRange(value, min, max)) {
    throw new ValidationError(`${fieldName} must be between ${min} and ${max}`);
  }
};

export const assertMinLength = (
  value: string,
  minLength: number,
  fieldName = 'Value'
): void => {
  if (!validateMinLength(value, minLength)) {
    throw new ValidationError(
      `${fieldName} must be at least ${minLength} characters long`
    );
  }
};

export const assertMaxLength = (
  value: string,
  maxLength: number,
  fieldName = 'Value'
): void => {
  if (!validateMaxLength(value, maxLength)) {
    throw new ValidationError(
      `${fieldName} must not exceed ${maxLength} characters`
    );
  }
};

export const assertPattern = (
  value: string,
  pattern: RegExp,
  fieldName = 'Value'
): void => {
  if (!validatePattern(value, pattern)) {
    throw new ValidationError(`${fieldName} format is invalid`);
  }
};
