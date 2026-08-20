export function replaceSuggestionHighlights(value, highlights, suggestionId, target) {
  const matches = highlights
    .filter((item) => item.suggestion_id === suggestionId)
    .sort((left, right) => left.start - right.start);
  if (!matches.length) return { value, highlights };

  let nextValue = "";
  let cursor = 0;
  matches.forEach((match) => {
    nextValue += value.slice(cursor, match.start) + target;
    cursor = match.end;
  });
  nextValue += value.slice(cursor);

  const nextHighlights = highlights.map((highlight) => {
    let shift = 0;
    for (const match of matches) {
      const delta = target.length - (match.end - match.start);
      if (highlight.suggestion_id === suggestionId && highlight.start === match.start) {
        return { ...highlight, start: match.start + shift, end: match.start + shift + target.length, target };
      }
      if (match.end <= highlight.start) shift += delta;
    }
    return { ...highlight, start: highlight.start + shift, end: highlight.end + shift };
  });
  return { value: nextValue, highlights: nextHighlights };
}
