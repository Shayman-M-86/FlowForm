export const QUESTION_MAX = 5000;
export const TAG_MAX = 40;
export const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

export const QUESTION_TEXTAREA_MAX_HEIGHT = 600;
export const OPTION_TEXTAREA_MAX_HEIGHT = 200;

export function blurOnEnter(event: React.KeyboardEvent<HTMLElement>) {
  if (event.key === "Enter") {
    event.preventDefault();
    (event.currentTarget as HTMLElement).blur();
  }
}

export function autoResizeTextarea(
  element: HTMLTextAreaElement,
  maxHeight: number = OPTION_TEXTAREA_MAX_HEIGHT,
) {
  const resolvedMax = element.classList.contains("node-pill__question")
    ? QUESTION_TEXTAREA_MAX_HEIGHT
    : maxHeight;
  element.style.height = "0px";
  const nextHeight = Math.min(element.scrollHeight, resolvedMax);
  element.style.height = `${nextHeight}px`;
  element.style.overflowY = element.scrollHeight > resolvedMax ? "auto" : "hidden";
}

export function nextAvailableTag(items: { tag: string }[]): string {
  const used = new Set(items.map((item) => item.tag));
  for (const letter of ALPHABET) {
    if (!used.has(letter)) return letter;
  }
  return "";
}

export function sanitizeQuestionId(value: string): string {
  return value.toLowerCase().replace(/\s+/g, "_");
}

export function incrementQuestionId(value: string): string {
  const match = value.match(/^(.*?)(\d+)(\D*)$/);
  if (match) {
    const [, prefix, digits, suffix] = match;
    return `${prefix}${String(Number(digits) + 1).padStart(digits.length, "0")}${suffix}`;
  }
  const base = value.trim() === "" ? "question_id" : value;
  return `${base}_1`;
}
