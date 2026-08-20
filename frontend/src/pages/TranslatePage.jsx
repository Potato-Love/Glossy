return (
  <>
    <div className="translate-page">
      <ModeTabs
        mode={mode}
        setMode={setMode}
      />

      {mode === "text" && (
        <>
          <TranslationBox
            text={text}
            setText={setText}
            result={result}
          />

          <button onClick={handleTranslate}>
            번역하기
          </button>
        </>
      )}

      {mode === "document" && (
        <div>문서 번역 화면</div>
      )}
    </div>

    {result && (
      <section className="term-section">
        <h2>AI가 발견한 용어</h2>

        {termSuggestions.map((term) => (
          <TermSuggestion
            key={term.id}
            term={term}
          />
        ))}
      </section>
    )}
  </>
);