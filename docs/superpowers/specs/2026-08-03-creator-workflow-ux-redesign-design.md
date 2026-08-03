# Creator Workflow UX Redesign

Date: 2026-08-03
Status: approved by the operator's standing instruction to proceed without repeated confirmation

## Design read

This is a local video-production wizard for a non-technical operator. It should feel like a dependable professional workstation, not a marketing page, an engineering graph, or an abstract dashboard.

- Redesign mode: targeted evolution
- Design variance: 4
- Motion intensity: 3
- Visual density: 6
- Theme: locked dark interface
- Accent: one restrained electric blue
- Shape rule: 12px workspace surfaces, 8px controls, pill only for status

## Problems observed

1. Text below the page title, inside cards, and in the left rail is too small to scan comfortably.
2. Large empty cards consume space without clarifying the next action.
3. Selected, ready, blocked, and running states rely on subtle borders, tiny dots, or disabled styling.
4. Generic **Continue** labels do not tell the operator what will happen next.
5. The review screen repeats data but does not behave like a final, actionable job summary.
6. A disabled start button does not explain whether configuration is missing or another task is running.
7. Numbered English eyebrows add visual noise without helping a Chinese-first workflow.

## Chosen approach

Keep the seven-stage information architecture and all API contracts. Recompose each stage around three questions:

1. What am I choosing now?
2. What has already been selected?
3. What will the next action do?

The alternative dashboard approach would expose too many controls at once. A single long form would remove progress context and make recovery harder. Both are rejected.

## Interaction model

- The left rail remains the persistent map. Each stage shows a readable name, short outcome, and explicit state: current, complete, or not configured.
- The fixed footer uses stage-specific action labels such as **Choose videos**, **Choose languages**, and **Review job** instead of generic **Continue**.
- Selection cards use a clear filled state and check indicator, not border color alone.
- Empty, warning, and error panels use direct instructions and one primary recovery action.
- Motion is limited to 160-220ms opacity/transform transitions, hover feedback, and pressed feedback. Reduced-motion disables transitions.

## Review screen

The review screen becomes an order-style job summary:

- A compact workload strip shows source videos, local outputs, and optional publication routes.
- Configuration groups show Source, Languages, Voice, and Destination with an **Edit** action that returns to the owning stage.
- The launch panel shows one explicit state:
  - Ready: explains the exact local workload and enables **Start processing**.
  - Blocked: lists missing decisions and labels the button **Complete setup first**.
  - Running: explains that a task is already active and offers **View progress** instead of looking mysteriously disabled.
- Local output is visually primary. Publication remains clearly optional.

## Accessibility and responsive behavior

- Body text is at least 14px; operational metadata is at least 11px.
- Every interactive control has visible hover, focus-visible, active, selected, and disabled states.
- Color is never the only state signal.
- Desktop navigation stays one line vertically; under 900px it becomes a horizontally scrollable stage strip.
- Review content collapses to one column under 1100px, with the launch panel before configuration details on narrow screens.
- No horizontal document overflow is permitted at 800x900 or 390x844.

## Boundaries

- No API, workflow graph, manifest, persistence, translation, voice, or publication contract changes.
- No new frontend framework or icon dependency.
- No decorative infinite canvas, glass effects, gradients-as-content, scroll hijacking, or image generation.
- Existing element IDs used by application logic remain stable.

## Verification

- Pure model tests cover stage-specific actions and launch-state presentation.
- Existing Studio API and model suites remain green.
- Real-browser drills cover Source, Videos, Translation, Voice, Output, Review, and Activity at desktop and compact widths.
- The browser console must contain zero errors.
