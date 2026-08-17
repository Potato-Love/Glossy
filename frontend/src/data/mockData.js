export const demoData = {
  onboardingComplete: false,
  currentUser: {
    id: "user-1",
    name: "김은수",
    nickname: "Eunsoo",
    organization: "Poongcha Team",
    position: "Frontend Developer",
    country: "대한민국",
  },
  team: {
    id: "team-1",
    name: "Poongcha Team",
    inviteCode: "GLOSSY-2026",
    members: [
      {
        id: "user-1",
        nickname: "Eunsoo",
        organization: "Poongcha Team",
        position: "Frontend Developer",
        status: "활동 중",
      },
      {
        id: "user-2",
        nickname: "Jaehoon",
        organization: "Poongcha Team",
        position: "Product Manager",
        status: "활동 중",
      },
      {
        id: "user-3",
        nickname: "Youngbin",
        organization: "Poongcha Team",
        position: "Backend Developer",
        status: "초대됨",
      },
    ],
  },
  terms: [
    {
      id: "term-1",
      scope: "team",
      source: "멋쟁이사자처럼",
      target: "LIKELION",
      strategy: "translate",
      memo: "공식 영문 브랜드명 사용",
      creator: "Jaehoon",
      createdAt: "2026.08.12",
    },
    {
      id: "term-2",
      scope: "team",
      source: "Glossy",
      target: "Glossy",
      strategy: "preserve",
      memo: "서비스명 원문 보존",
      creator: "Eunsoo",
      createdAt: "2026.08.13",
    },
    {
      id: "term-3",
      scope: "personal",
      source: "배포",
      target: "deployment",
      strategy: "translate",
      memo: "개인 문서 기본 표현",
      creator: "Eunsoo",
      createdAt: "2026.08.15",
    },
  ],
  recipients: [
    {
      id: "recipient-1",
      name: "Lionel Messi",
      company: "Inter Miami CF",
      position: "Captain",
      country: "미국",
      tone: "정중하고 간결하게",
      traits: "축구 관련 표현은 자연스럽게 사용",
    },
    {
      id: "recipient-2",
      name: "Emma Müller",
      company: "Berlin Studio",
      position: "Creative Director",
      country: "독일",
      tone: "친근하고 전문적으로",
      traits: "디자인 전문 용어를 선호",
    },
  ],
  history: [
    {
      id: "history-1",
      sourceText: "안녕하세요, 저희는 풍차돌리기 팀입니다.",
      translatedText: "Hello, we are team “Poongchadoligi”.",
      executorId: "user-1",
      executor: "Eunsoo",
      recipient: "Lionel Messi",
      createdAt: "2026.08.18 14:32",
      appliedTerms: ["풍차돌리기 → Poongchadoligi"],
    },
    {
      id: "history-2",
      sourceText: "Glossy의 새 버전을 배포했습니다.",
      translatedText: "We deployed a new version of Glossy.",
      executorId: "user-2",
      executor: "Jaehoon",
      recipient: "Emma Müller",
      createdAt: "2026.08.17 10:05",
      appliedTerms: ["Glossy → Glossy"],
    },
  ],
};

export const countries = ["대한민국", "미국", "영국", "독일", "프랑스", "일본", "중국"];

export const languages = [
  { code: "ko", label: "한국어" },
  { code: "en", label: "영어" },
  { code: "de", label: "독일어" },
  { code: "fr", label: "프랑스어" },
  { code: "ja", label: "일본어" },
  { code: "zh", label: "중국어" },
];

export const countryLanguageMap = {
  대한민국: "ko",
  미국: "en",
  영국: "en",
  독일: "de",
  프랑스: "fr",
  일본: "ja",
  중국: "zh",
};
