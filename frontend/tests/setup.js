import '@testing-library/jest-dom';
import { TextDecoder, TextEncoder } from 'node:util';
import { randomUUID } from 'node:crypto';

Object.assign(globalThis, { TextEncoder, TextDecoder });
if (!globalThis.crypto.randomUUID) {
  Object.defineProperty(globalThis.crypto, 'randomUUID', { value: randomUUID, configurable: true });
}
