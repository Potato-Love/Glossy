import "./TranslatePage.css";

function TranslatePage() {
  return (
    <div className="translate-page">
      <div className="translate-container">
        <div className="translate-toolbar">
          <div className="mode-tabs">
            <button className="mode-tab active">텍스트</button>
            <button className="mode-tab">문서</button>
            <button className="mode-tab">사진</button>
          </div>

          <button className="recipient-selector">
            수신자: Lionel Messi
          </button>
        </div>

        <section className="translation-box">
          <div className="language-header">
            <button>한국어⌄</button>

            <button className="swap-button">⇄</button>

            <div className="target-language">
              <button>영어⌄</button>

              <label>
                용어집
                <input type="checkbox" defaultChecked />
              </label>
            </div>
          </div>

          <div className="translation-content">
            <div className="source-panel">
              안녕하세요, 저희는 풍차돌리기 팀입니다.
            </div>

            <div className="result-panel">
              Hello, we are team{" "}
              <span className="glossary-highlight">
                "Poongchadoligi"
              </span>
              .
            </div>
          </div>
        </section>

        <section className="term-suggestion">
          AI 감지 단어 영역
        </section>
      </div>
    </div>
  );
}

export default TranslatePage;