import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import { setWords, type WordTables } from '@/api/words';
// The words the server serves (`GET /words/labels`), as a snapshot the backend test
// `backend/tests/squad/test_served_words.py` keeps equal to what the server serves.
import served from './words.json';

setWords(served as unknown as WordTables);

afterEach(() => cleanup());

// jsdom lacks these; Radix primitives call them.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;
Element.prototype.scrollIntoView ??= () => {};
Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.releasePointerCapture ??= () => {};
