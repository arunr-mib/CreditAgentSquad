import { describe, expect, it } from 'vitest';
import { othersPhrase } from './CommandCentre';

describe('the command centre subtitle', () => {
  it('names the one role the rest need', () => {
    expect(othersPhrase([['Credit officer', 5]])).toEqual({ text: '5 need Credit officer sign-off', list: null });
    expect(othersPhrase([['Credit officer', 1]])?.text).toBe('1 needs Credit officer sign-off');
  });

  it('groups several roles and keeps the list behind the phrase', () => {
    const others: Array<[string, number]> = [
      ['Credit officer', 5],
      ['Portfolio manager or Credit officer', 1],
    ];
    expect(othersPhrase(others)).toEqual({ text: '6 need other roles', list: others });
  });

  it('says nothing when everything is within the reader’s authority', () => {
    expect(othersPhrase([])).toBeNull();
  });
});
