import { describe, expect, it } from 'vitest';
import * as dec from '@/api/decimal';
import { formatDate, formatDue, formatFigure } from '../format';

describe('formatFigure', () => {
  it('groups whole dollars and marks the unit', () => {
    expect(formatFigure('6658000', 'usd').text).toBe('$6,658,000');
  });
  it('scales to thousands without a unit mark for table cells', () => {
    expect(formatFigure('29480000', 'usd', { scale: 1000, unitMark: false }).text).toBe('29,480');
  });
  it('rounds half-up when scaling', () => {
    expect(formatFigure('124500', 'usd', { scale: 1000, unitMark: false }).text).toBe('125');
    expect(formatFigure('124499', 'usd', { scale: 1000, unitMark: false }).text).toBe('124');
  });
  it('shows negative money in parentheses, never with a minus', () => {
    expect(formatFigure('-620000', 'usd', { scale: 1000, unitMark: false })).toEqual({ text: '(620)', negative: true });
    expect(formatFigure('-250000', 'usd').text).toBe('($250,000)');
  });
  it('formats ratios to two places with x', () => {
    expect(formatFigure('1.12', 'ratio').text).toBe('1.12x');
    expect(formatFigure('3.1', 'ratio').text).toBe('3.10x');
  });
  it('formats percentages with a true minus sign', () => {
    expect(formatFigure('-6.7', 'pct').text).toBe('−6.7%');
    expect(formatFigure('11.43', 'pct').text).toBe('11.4%');
  });
  it('shows runway in months at one place, never a whole month', () => {
    expect(formatFigure('13', 'months').text).toBe('13.0 months');
    expect(formatFigure('14.000000', 'months').text).toBe('14.0 months');
    expect(formatFigure('7.076923', 'months').text).toBe('7.1 months');
    expect(formatFigure('6.4', 'months').text).toBe('6.4 months');
    expect(formatFigure('18.4', 'months', { unitMark: false }).text).toBe('18.4');
  });
  it('shows an unknown unit as its stored text with the unit, never throws', () => {
    expect(formatFigure('12.5', 'furlongs' as never)).toEqual({ text: '12.5 furlongs', negative: false });
    expect(formatFigure('-3', 'furlongs' as never).negative).toBe(true);
  });
  it('formats days and counts', () => {
    expect(formatFigure('13', 'days').text).toBe('13 days');
    expect(formatFigure('1200', 'count').text).toBe('1,200');
  });
  it('does not turn a rounded-away negative into negative zero', () => {
    expect(formatFigure('-0.004', 'ratio').text).toBe('0.00x');
  });
});

describe('decimal helpers', () => {
  it('adds and subtracts exactly', () => {
    expect(dec.round(dec.add('0.1', '0.2'), 1)).toBe('0.3');
    expect(dec.round(dec.sub('3017000', '760000', '281000', '200000'), 0)).toBe('1776000');
  });
  it('divides with half-up rounding at the end', () => {
    expect(dec.div('1776000', '1584000', 2)).toBe('1.12');
    expect(dec.div('1', '8', 2)).toBe('0.13');
    expect(dec.div('-1', '8', 2)).toBe('-0.13');
  });
  it('refuses a denominator of zero or less', () => {
    expect(() => dec.div('1', '0', 2)).toThrow();
    expect(() => dec.div('1', '-2', 2)).toThrow();
  });
  it('rejects text that is not a decimal', () => {
    expect(() => dec.add('1,200', '1')).toThrow();
  });
  it('takes the lower of two values', () => {
    expect(dec.min('620000', '250000')).toBe('250000');
  });
});

describe('dates', () => {
  it('formats ISO dates without time-zone arithmetic', () => {
    expect(formatDate('2026-11-12')).toBe('12 Nov 2026');
    expect(formatDate('2026-11-09', { year: false })).toBe('9 Nov');
  });
  it('describes a due date against the simulated date', () => {
    expect(formatDue('2026-11-12', '2026-11-12')).toMatchObject({ text: 'Today', sentence: 'Due today', today: true });
    expect(formatDue('2026-11-13', '2026-11-12').text).toBe('Tomorrow');
    expect(formatDue('2026-11-09', '2026-11-12')).toMatchObject({ text: '3 days late', sentence: 'Overdue by 3 days', overdue: true });
    expect(formatDue('2026-11-20', '2026-11-12').sentence).toBe('Due 20 Nov');
  });
});
