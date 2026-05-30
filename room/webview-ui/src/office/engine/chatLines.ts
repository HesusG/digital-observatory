// Ambient chat phrases for the boss characters + a pure phrase picker.
// pickPhrase is DOM-free and accepts an injectable rand for deterministic tests.

export const HESUS_LINES: string[] = [
  'Si bro!',
  'tengo miedo',
  '¿crees que me vaya a morir?',
  '¿y si truena el servidor?',
  'no me dejes solo bro',
  'esto se va a caer, lo sé',
  '¿viste eso? qué miedo',
  '¿seguro que esto es seguro?',
];

export const MORENO_LINES: string[] = [
  'uff!',
  'medio día',
  'el mercado nunca duerme',
  'yo ya lo había predicho',
  'eso es ruido, no señal',
  'mis valuaciones nunca fallan',
  'esto es alfa puro',
  'los amateurs venden, yo acumulo',
];

export const PACO_LINES: string[] = [
  'ya fue',
  'el unabomber tenía razón',
  'todo está conectado, ¿no lo ves?',
  'mi peor decisión financiera fue existir',
  'nos están observando',
  'ya nada tiene sentido',
  'debí vender en el pico',
  'el sistema está diseñado para que pierdas',
];

// Pick a random phrase, avoiding an immediate repeat of prevIndex when possible.
export function pickPhrase(
  lines: string[],
  prevIndex: number,
  rand: () => number = Math.random,
): { index: number; text: string } {
  if (lines.length <= 1) return { index: 0, text: lines[0] ?? '' };
  let index = Math.floor(rand() * lines.length);
  if (index >= lines.length) index = lines.length - 1;
  if (index === prevIndex) index = (index + 1) % lines.length;
  return { index, text: lines[index] };
}
