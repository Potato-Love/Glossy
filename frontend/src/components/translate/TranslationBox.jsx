function TranslationBox({text, setText, result,}){
    return(
        <section className="translation-box">
      <div className="language-header">
        <button>한국어⌄</button>

        <button className="swap-button">
          ⇄
        </button>

        <div className="target-language">
          <button>영어⌄</button>

          <label>
            용어집
            <input
              type="checkbox"
              defaultChecked
            />
          </label>
        </div>
      </div>

      <div className="translation-content">
        <div className="source-panel">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="번역할 내용을 입력하세요."
          />
        </div>

        <div className="result-panel">
          {result ? (
            <p>{result}</p>
          ) : (
            <p className="result-placeholder">
              번역 결과가 여기에 표시됩니다.
            </p>
          )}
        </div>
      </div>
    </section>
    );
}

export default TranslationBox;