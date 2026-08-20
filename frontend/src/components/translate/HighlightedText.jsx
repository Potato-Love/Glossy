import { useRef } from "react";

function splitHighlightedText(text, highlights = []) {
  const segments = [];
  let cursor = 0;

  [...highlights]
    .sort((left, right) => left.start - right.start)
    .forEach((highlight) => {
      if (highlight.start < cursor || highlight.end > text.length) return;
      if (highlight.start > cursor) {
        segments.push({ text: text.slice(cursor, highlight.start), state: null });
      }
      segments.push({
        text: text.slice(highlight.start, highlight.end),
        state: highlight.state,
        title: `${highlight.source} → ${highlight.target}`,
        key: `${highlight.start}-${highlight.end}-${highlight.suggestion_id || highlight.term_id || "term"}`,
      });
      cursor = highlight.end;
    });

  if (cursor < text.length) segments.push({ text: text.slice(cursor), state: null });
  return segments;
}

export function HighlightedText({ text, highlights = [] }) {
  return splitHighlightedText(text, highlights).map((segment, index) => (
    segment.state ? (
      <mark
        key={segment.key || index}
        className={`term-highlight ${segment.state}`}
        title={segment.title}
      >
        {segment.text}
      </mark>
    ) : <span key={`plain-${index}`}>{segment.text}</span>
  ));
}

export function HighlightedTextarea({ value, highlights, onChange, ...textareaProps }) {
  const mirrorRef = useRef(null);

  function handleScroll(event) {
    if (!mirrorRef.current) return;
    mirrorRef.current.scrollTop = event.currentTarget.scrollTop;
    mirrorRef.current.scrollLeft = event.currentTarget.scrollLeft;
  }

  return (
    <div className="highlighted-textarea">
      <div ref={mirrorRef} className="highlighted-textarea-mirror" aria-hidden="true">
        <HighlightedText text={`${value}\n`} highlights={highlights} />
      </div>
      <textarea
        {...textareaProps}
        value={value}
        onChange={onChange}
        onScroll={handleScroll}
      />
    </div>
  );
}
