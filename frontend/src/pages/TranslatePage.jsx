import { useState } from "react";
import "./TranslatePage.css";

function TranslatePage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState("");

  function handleTranslate() {
    if (!text.trim()) return;

    setResult('Hello, we are team "Poongchadoligi".');
  }

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
              <textarea
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="번역할 내용을 입력하세요."
              />
            </div>

            <div className="result-panel">
              {result ? (
                <p>
                  Hello, we are team{" "}
                  <span className="glossary-highlight">
                    "Poongchadoligi"
                  </span>
                  .
                </p>
              ) : (
                <p className="result-placeholder">
                  번역 결과가 여기에 표시됩니다.
                </p>
              )}
            </div>
          </div>
        </section>

        <div className="translate-action">
          <button
            className="translate-button"
            onClick={handleTranslate}
          >
            번역하기
          </button>
        </div>

        {result && (
          <section className="term-suggestion">
            AI 감지 단어 영역
          </section>
        )}
      </div>
    </div>
  );
}

export default TranslatePage;