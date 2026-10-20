// Do not evaluate templates while opening an automation: decode only our constant.
export function decodeAutomationDesign(value) {
  if (value && typeof value === "object" && !Array.isArray(value))
    return structuredClone(value);
  const prefix = "{{ ";
  const suffix = " | from_json }}";
  if (
    typeof value !== "string" ||
    !value.startsWith(prefix) ||
    !value.endsWith(suffix)
  )
    throw new Error("Expected a designer document or encoded designer source");
  const document = JSON.parse(
    JSON.parse(value.slice(prefix.length, -suffix.length)),
  );
  if (
    !document ||
    typeof document !== "object" ||
    !Array.isArray(document.elements)
  )
    throw new Error("The designer source must be a document");
  return document;
}
