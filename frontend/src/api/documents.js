const API_URL = import.meta.env.VITE_API_URL ?? "";
const USE_MOCK = import.meta.env.VITE_USE_MOCK_DOCUMENTS !== "false";

function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function postFormData(path, formData) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("문서를 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.");
  }

  return response.json();
}

function appendOptions(formData, options) {
  formData.append("sourceLanguage", options.sourceLanguage);
  formData.append("targetLanguage", options.targetLanguage);
  formData.append("recipientId", options.recipientId ?? "");
  formData.append("glossaryEnabled", String(options.glossaryEnabled));
}

const documentTranslationMock = {
  document: {
    pageCount: 12,
    wordCount: 3482,
  },
  appliedTermCount: 17,
  translatedParagraphs: [
    {
      id: "paragraph-1",
      source: "Zebra 프로젝트는 여러 팀의 검색 데이터를 하나의 RAG Pipeline으로 통합합니다.",
      target: "Project Zebra consolidates search data from multiple teams into a single RAG Pipeline.",
    },
    {
      id: "paragraph-2",
      source: "Finch는 검색 결과를 검증하고 품질 지표를 실시간으로 제공합니다.",
      target: "Finch validates search results and provides quality metrics in real time.",
    },
    {
      id: "paragraph-3",
      source: "Glossy 용어집을 적용하면 프로젝트명과 기술 용어가 문서 전체에서 동일하게 유지됩니다.",
      target: "With the Glossy glossary applied, project names and technical terms remain consistent throughout the document.",
    },
  ],
  suggestions: [
    {
      id: "document-term-zebra",
      source: "Zebra",
      target: "Zebra",
      kind: "프로젝트명으로 추정",
      recommendedStrategy: "preserve",
    },
    {
      id: "document-term-rag",
      source: "RAG Pipeline",
      target: "RAG Pipeline",
      kind: "기술 용어로 추정",
      recommendedStrategy: "translate",
    },
    {
      id: "document-term-finch",
      source: "Finch",
      target: "Finch",
      kind: "제품명으로 추정",
      recommendedStrategy: "preserve",
    },
    {
      id: "document-term-retrieval",
      source: "Retrieval Quality",
      target: "검색 품질",
      kind: "반복 전문 용어로 추정",
      recommendedStrategy: "translate",
    },
  ],
};

const comparisonMock = {
  inconsistencies: [
    {
      id: "compare-zebra",
      source: "Zebra",
      kind: "프로젝트명",
      recommendedTarget: "Zebra",
      recommendedStrategy: "preserve",
      variants: [
        { documentName: "translation_v1.docx", target: "얼룩말 프로젝트", count: 8 },
        { documentName: "translation_v2.pdf", target: "Zebra", count: 11 },
      ],
    },
    {
      id: "compare-rag",
      source: "RAG Pipeline",
      kind: "기술 용어",
      recommendedTarget: "RAG Pipeline",
      recommendedStrategy: "translate",
      variants: [
        { documentName: "translation_v1.docx", target: "검색 증강 생성 파이프라인", count: 5 },
        { documentName: "translation_v2.pdf", target: "RAG Pipeline", count: 7 },
        { documentName: "translation_final.txt", target: "RAG 파이프라인", count: 4 },
      ],
    },
    {
      id: "compare-finch",
      source: "Finch",
      kind: "제품명",
      recommendedTarget: "Finch",
      recommendedStrategy: "preserve",
      variants: [
        { documentName: "translation_v1.docx", target: "핀치", count: 6 },
        { documentName: "translation_v2.pdf", target: "Finch", count: 6 },
      ],
    },
  ],
};

const imageTranslationMock = {
  extractedText: "Zebra 프로젝트의 RAG Pipeline 검토 결과를 Finch 팀에 공유해 주세요.",
  translatedText: "Please share the review results of Project Zebra's RAG Pipeline with the Finch team.",
  suggestions: [
    {
      id: "image-term-zebra",
      source: "Zebra",
      target: "Zebra",
      kind: "프로젝트명으로 추정",
      recommendedStrategy: "preserve",
    },
    {
      id: "image-term-rag",
      source: "RAG Pipeline",
      target: "RAG Pipeline",
      kind: "기술 용어로 추정",
      recommendedStrategy: "translate",
    },
  ],
};

export async function translateDocument({ file, ...options }) {
  if (USE_MOCK) {
    await wait(1900);
    return {
      ...documentTranslationMock,
      document: { ...documentTranslationMock.document, name: file.name },
    };
  }

  const formData = new FormData();
  formData.append("file", file);
  appendOptions(formData, options);
  return postFormData("/documents/translate", formData);
}

export async function compareTranslations({ sourceFile, translationFiles, ...options }) {
  if (USE_MOCK) {
    await wait(1600);
    return {
      inconsistencies: comparisonMock.inconsistencies.map((item) => ({
        ...item,
        variants: item.variants.map((variant, index) => ({
          ...variant,
          documentName: translationFiles[index % translationFiles.length].name,
        })),
      })),
      sourceDocument: sourceFile.name,
      translationDocuments: translationFiles.map((file) => file.name),
    };
  }

  const formData = new FormData();
  formData.append("sourceFile", sourceFile);
  translationFiles.forEach((file) => formData.append("translationFiles", file));
  appendOptions(formData, options);
  return postFormData("/documents/compare", formData);
}

export async function translateImage({ file, ...options }) {
  if (USE_MOCK) {
    await wait(1300);
    return { ...imageTranslationMock, imageName: file.name };
  }

  const formData = new FormData();
  formData.append("file", file);
  appendOptions(formData, options);
  return postFormData("/images/translate", formData);
}
