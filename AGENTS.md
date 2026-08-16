# AGENTS.md

## Project Overview

**Glossy** is an AI translation service for teams that need consistent terminology across collaboration.

Core product flow:

1. User enters text or uploads a document.
2. Glossy translates using the selected glossary and recipient profile.
3. AI detects potential new terminology.
4. The user approves, edits, or rejects suggested terms.
5. Approved terms are saved and reused in later translations.

The product should feel like a lightweight SaaS tool, not a generic AI chat interface.

## Frontend Stack

- React
- Vite
- JavaScript
- Plain CSS
- React Router
- `fetch` for API communication unless another dependency is clearly justified

### Do not use

- TypeScript
- Tailwind CSS
- Redux
- Large UI frameworks unless explicitly requested
- Unnecessary abstractions or dependencies

This project is being developed while learning React, so code should stay readable and explainable.

## Main Screens

### Onboarding
- Sign up / log in
- Profile setup
  - Name
  - Nickname
  - Organization
  - Position
  - Country
- Team creation / team joining
- Join via invite code or invite link

### Translate
- Text / document mode
- Source and target language selection
- Recipient profile selection
- Team / personal glossary activation
- Translation input and result
- Applied glossary term highlighting
- AI terminology suggestions
  - Approve
  - Edit
  - Reject
- Standard translation vs Glossy translation comparison

### Glossary
- Team glossary
- Personal glossary
- Add / edit / delete terms
- Support at least:
  - Preserve original
  - Translate to specified term

### Recipient Profiles
- Name
- Organization
- Position
- Nationality / country
- Tone
- Additional communication preferences

### History
- Personal translation history
- Team translation history
- Show translator, timestamp, and recipient when available

### Team Settings
- Team member list
- Invite code generation
- Invite link generation

### My Profile
- View and edit personal information

## Suggested Directory Structure

```text
src/
├── assets/
│   ├── icons/
│   └── images/
├── components/
│   ├── common/
│   ├── layout/
│   ├── translate/
│   ├── glossary/
│   ├── recipient/
│   ├── history/
│   └── team/
├── pages/
│   ├── TranslatePage.jsx
│   ├── GlossaryPage.jsx
│   ├── RecipientProfilePage.jsx
│   ├── HistoryPage.jsx
│   ├── TeamPage.jsx
│   └── MyPage.jsx
├── api/
├── data/
├── styles/
│   ├── global.css
│   └── variables.css
├── App.jsx
└── main.jsx
```

Do not create empty folders or files just to match this structure. Add them when the feature is actually implemented.

## React Guidelines

### Components

Split components based on responsibility, not arbitrary size.

Good examples:

- `Sidebar`
- `ModeTabs`
- `RecipientSelector`
- `TranslationBox`
- `TranslationResult`
- `TermSuggestionCard`
- `GlossaryTable`

Avoid turning every small HTML element into its own component.

### State

Prefer local state first.

Use:
- `useState`
- `useEffect` only when actually needed
- props for parent-child communication

Do not add global state management unless the application genuinely requires it.

Keep state as close as possible to the components that use it.

### Lists

Use `.map()` for glossary terms, recipient profiles, history items, and AI suggestions.

Always use a stable unique `key`.

### Event Handlers

Use named handlers when logic is more than trivial.

```jsx
function handleTranslate() {
  // ...
}
```

Prefer:

```jsx
<button onClick={handleTranslate}>
```

over putting complex logic directly inside JSX.

## CSS Guidelines

Use plain CSS.

Prefer CSS files near the component they style.

```text
Sidebar.jsx
Sidebar.css
```

Shared global values should live in `src/styles/variables.css`.

Example:

```css
:root {
  --color-primary: #2797f5;
  --color-primary-light: #eaf5ff;
  --color-text: #191919;
  --color-text-secondary: #777777;
  --color-border: #dddddd;
  --color-sidebar: #f7f7f9;
  --color-success: #67efa9;
  --color-danger: #ff6b6b;
  --radius-sm: 8px;
  --radius-md: 12px;
}
```

### Layout

Prefer:
- Flexbox
- CSS Grid
- `gap`
- `max-width`
- responsive padding

Avoid using absolute positioning to reproduce Figma coordinates.

The implementation should remain usable when the browser size changes.

## Figma Implementation Rules

The current Figma design is the visual source of truth.

When implementing a screen:

1. Match the overall layout first.
2. Match spacing and sizing.
3. Match typography.
4. Match borders, radius, and colors.
5. Add interactions.
6. Fine-tune pixel-level differences last.

Do not sacrifice responsive behavior just to reproduce exact X/Y coordinates from Figma.

Reuse visual patterns consistently across screens.

## Glossy UX Rules

### Translation

The translation screen is the product's primary screen.

The user should always be able to understand:
- what language is being translated
- which recipient profile is applied
- which glossary is active
- which terms Glossy changed or preserved
- what action to take next

### Glossary Terms

Distinguish between:
- already-applied glossary terms
- newly detected AI term suggestions

Do not visually represent both states identically.

### AI Term Suggestions

Avoid ambiguous icon-only actions for important decisions.

Prefer clear actions such as:
- `용어집에 추가`
- `수정`
- `거절`

If icons are used, provide tooltips or accompanying labels.

### Recipient Profile

Make it clear that the selected person is the **translation recipient**, not the logged-in user.

### Comparison Mode

The standard translation and Glossy translation should use the same source text and underlying translation model where possible.

Highlight only meaningful differences introduced by Glossy context.

## API Integration

Do not call the LLM provider directly from React.

Expected flow:

```text
React
  ↓
Backend API
  ↓
Glossary / recipient context
  ↓
LLM API
  ↓
Backend response
  ↓
React
```

Keep API calls outside presentation components when practical.

Example:

```text
src/api/translate.js
src/api/glossary.js
src/api/recipient.js
src/api/team.js
```

Use environment variables for backend URLs:

```text
VITE_API_URL
```

Never hard-code API keys in the frontend.

## Mock Data First

The frontend should be developable before the backend is finished.

Use mock data for features that do not have a working endpoint yet.

```js
export const mockTranslation = {
  translatedText: 'Hello, we are team "Poongchadoligi".',
  detectedTerms: [
    {
      id: 1,
      source: "풍차돌리기",
      target: "Poongchadoligi",
      category: "고유명사(팀명)",
      strategy: "발음대로 번역",
    },
  ],
};
```

Keep mock response shapes close to the planned backend API shape so they can be replaced easily.

## Code Quality Rules

- Prefer simple code over clever code.
- Keep naming explicit and readable.
- Remove unused imports and dead code.
- Avoid premature abstraction.
- Avoid deeply nested JSX when a meaningful component split improves readability.
- Do not rewrite unrelated files.
- Do not change project-wide architecture without a clear reason.
- Keep dependencies minimal.
- Preserve existing UI behavior when modifying isolated features.

## Agent Behavior

When generating or editing code for this repository:

1. Read the surrounding code before modifying a file.
2. Make the smallest reasonable change.
3. Follow the existing naming and directory conventions.
4. Do not introduce TypeScript or Tailwind.
5. Do not replace plain CSS with another styling system.
6. Do not install packages unless they provide clear value.
7. Explain unfamiliar React concepts briefly when presenting code changes.
8. Prefer code that a React learner can understand and maintain.
9. If several implementation options exist, prefer the simpler one.
10. When backend details are missing, use mocks or clearly marked placeholders instead of inventing an API contract.
11. Do not expose secrets or API keys in frontend code.
12. Keep the Glossy core flow—translate → detect terminology → approve/edit/reject → reuse—easy to demonstrate.

## Current Priority

The first implementation target is the main translation page based on the existing Figma design.

Recommended order:

1. Global styles and CSS variables
2. Sidebar
3. Translate page layout
4. Text / document mode selector
5. Recipient selector
6. Translation input / result UI
7. Glossary highlighting
8. AI term suggestion card
9. Mock interactions
10. Backend integration
11. Remaining pages

The goal is to get the core user experience working before expanding the feature set.
