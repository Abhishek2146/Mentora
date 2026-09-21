/**
 * Master Prompt Generator for Pollinations AI Note Image Generation.
 * Strictly enforces that generated images rely ONLY on the supplied highlighted concept/notes.
 */
export function buildMasterPrompt(notesText: string): string {
  const cleanNotes =
    notesText.trim() ||
    "Rectangle Formula: Area (A) = l x b, Perimeter (P) = 2(l + b), Diagonal (d) = sqrt(l^2 + b^2)";

  return `Authentic real close-up photograph of handwritten notes written in dark royal blue ballpoint pen on white textured paper.
Handwritten content to write:
${cleanNotes}

Style requirements:
* Genuine neat human handwriting in dark blue ballpoint pen ink.
* Underlined handwritten title at the top.
* Neatly drawn hand-drawn geometric diagram or formula box in blue pen where appropriate.
* Clear, highly legible handwritten text, formulas, and definitions.
* Macro flat top-down view of the paper filling the entire screen edge to edge.
* Realistic paper grain texture with natural slight pen pressure variations and authentic ink flow.
* Completely flat document, no perspective distortion.
* Absolutely NO pens, NO pencils, NO hands, NO desk, NO stationery objects. Just the flat paper page with handwritten notes.`;
}
