import "../../pages/TranslatePage.css";

function ModeTabs({mode, setMode}){
    return(
        <div className="modeTabs">
            <button className={mode === "text" ? "mode-tab active" : "mode-tab"}
            onClick={() => setMode("text")}
            >
                텍스트
            </button>

            <button className={mode === "document" ? "mode-tab active" : "mode-tab"}
            onClick={() => setMode("document")}
            >
                문서
            </button>

            <button className={mode === "image" ? "mode-tab active" : "mode-tab"}
            onClick={() => setMode("image")}
            >
                사진
            </button>
        </div>
    )
}

export default ModeTabs;
