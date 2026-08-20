function TermSuggestions({term}){
    return(
    <div className="term-suggestion">
      <div>
        <strong>{term.original}</strong>
        <p>{term.translation}</p>
      </div>

      <div className="term-actions">
        <button>용어집에 추가</button>
        <button>수정</button>
        <button>거절</button>
      </div>
    </div>
  );
}