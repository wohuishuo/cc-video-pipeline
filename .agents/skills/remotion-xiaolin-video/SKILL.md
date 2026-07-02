---
name: remotion-xiaolin-video
description: Build evidence-dense Xiaolin-style Remotion videos with frame checks.
---

# Remotion Xiaolin Video

## When To Use

Use this skill when editing Remotion video code for a Xiaolin-like explainer, especially when the user says the video is too PPT-like, too AI-flavored, visually cheap, frozen during pauses, poorly timed to narration, or not using reference frames.

## Required Workflow

1. Read the local project brief/script/storyboard and the relevant `reference/*/analysis.md`.
2. Open at least three reference frames before changing visuals.
3. Inspect the current Remotion composition or exported preview frames.
4. Make the smallest code changes that increase real shot variety and timing clarity.
5. Render a preview and inspect frames from the changed section before reporting success.

## Hard Rules

- Do not claim that viewers "feel" something. Describe only what is visible, audible, timed, or editable.
- Do not use scene titles as fake subtitles. Bottom captions require real timed transcript data.
- Pauses must not look frozen: at least one of background texture, presenter frame, diagram, crop, scan line, or music tail must continue.
- The opening 30 seconds should have at least 8 visual beats unless the reference analysis says otherwise.
- Avoid one reusable card grid. Use at least four visual families in the opening: concept composite, phone/live page, form/table, contract/desk, chat/recruiting, network graph, evidence wall, or full-frame question.
- Keep one focal point per shot. If text becomes small or scattered, split it into another shot instead of squeezing it.
- Use Remotion frame math (`useCurrentFrame`, `interpolate`, `spring`) for motion. Do not use CSS animations.
- Before commit, render a short preview and inspect representative frames.

## Xiaolin Reference Targets

Use local Xiaolin analysis as concrete reference, not as vague "advanced feeling":

- Average cut density in the analyzed sample is about 2.24 seconds per cut; opening is about 1.6 seconds per cut.
- Opening pattern: familiar examples quickly shown, then one unifying reveal.
- Common visual families: dark concept composite, host or circular PiP, full-screen materials, real-shot/archival-style frame, relationship diagram, large title card, and caption only when synced to speech.
- Audio rhythm uses music bed and intentional silence; visual motion should continue through silence.

## Review Checklist

Before final answer, check:

- Does the first screen start with actual video content, not production notes or draft labels?
- Are there at least 8 distinct opening beats in the first 30 seconds?
- Is any long hold still moving?
- Are right-side text blocks legible and not competing with the main focal point?
- Did you render and inspect frames after editing?
