export interface DisplayResult {
  /** Parsed value: the resolved object/array/primitive, or the original for unparseable strings */
  parsed: unknown;
  /** Text to display when isJson is false */
  displayText: string;
  /** True when the value should render as structured JSON (object or array) */
  isJson: boolean;
  /** True when the input was a JSON-encoded string that was successfully parsed */
  isParsed: boolean;
}

const MAX_UNWRAP_DEPTH = 5;

/**
 * Prepare a value for display.
 *
 * - Objects/arrays → isJson:true, pass to a JSON viewer.
 * - JSON-encoded strings that decode to an object/array → isJson:true (recursively unwrapped up to MAX_UNWRAP_DEPTH).
 * - JSON-encoded string scalars → isJson:false, displayText holds the decoded string.
 * - Plain strings that are not valid JSON → isJson:false, displayText is the original.
 * - null/undefined → isJson:false, displayText "null" / "".
 */
export function prepareDisplay(value: unknown, _depth = 0): DisplayResult {
  if (value === undefined || value === null) {
    return {
      parsed: value ?? null,
      displayText: value === undefined ? "" : "null",
      isJson: false,
      isParsed: false,
    };
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return { parsed: value, displayText: String(value), isJson: false, isParsed: false };
  }

  if (Array.isArray(value) || (typeof value === "object")) {
    return { parsed: value, displayText: "", isJson: true, isParsed: false };
  }

  // String handling
  if (typeof value === "string") {
    if (!value.trim()) {
      return { parsed: value, displayText: value, isJson: false, isParsed: false };
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(value);
    } catch {
      return { parsed: value, displayText: value, isJson: false, isParsed: false };
    }

    // Parsed as another string → try recursive unwrap for double-encoded JSON
    if (typeof parsed === "string") {
      if (_depth < MAX_UNWRAP_DEPTH) {
        const inner = prepareDisplay(parsed, _depth + 1);
        if (inner.isJson) {
          return { parsed: inner.parsed, displayText: "", isJson: true, isParsed: true };
        }
      }
      return { parsed, displayText: parsed, isJson: false, isParsed: true };
    }

    // Parsed as object/array
    if (Array.isArray(parsed) || (typeof parsed === "object" && parsed !== null)) {
      return { parsed, displayText: "", isJson: true, isParsed: true };
    }

    // Parsed as null/number/boolean
    return { parsed, displayText: parsed === null ? "null" : String(parsed), isJson: false, isParsed: true };
  }

  return { parsed: value, displayText: String(value), isJson: false, isParsed: false };
}
