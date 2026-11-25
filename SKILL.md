---
name: arkui-visual-replica
description: Recreate local HTML pages, screenshots, design images, or mockups as high-fidelity HarmonyOS NEXT ArkUI/ArkTS, covering static visual cloning and interaction-rich native motion. Use for 高保真复刻、还原、迁移 HTML/截图/设计图, animated timelines, gestures, transitions, 3D volume, shared elements, spring physics, scroll-linked effects, particles, and motion QA. Do not use for original visual design without a reference, backend, persistence, or general ArkUI business logic unrelated to visual or motion replication.
---

# ArkUI Visual Replica

Recreate one selected visual surface in ArkUI and ArkTS. Treat the rendered reference as visual
truth and use native layout, text, resources, and motion. Use the user's existing HarmonyOS
project and its conventions unless the user requests a new project. Preserve local fonts and
assets where feasible and disclose substitutions. Keep unrelated product logic out of scope.

## Choose the Smallest Workflow That Meets the Request

| Request | Workflow |
|---|---|
| Static page or screenshot | Capture the selected state and coordinate baseline, implement the native layout, and verify to the requested [visual evidence level](references/visual-qa.md#evidence-levels). Keep controls visual only. |
| Simple autonomous motion | Follow the visual workflow, then use [deterministic visual motion](references/visual-motion.md) to verify a stable reference frame, normal playback, and cleanup on exit. |
| Interaction or precise motion | Use the [motion workflow](#motion-workflow) for gestures, navigation, scroll-linked effects, springs, particles, staged or interruptible timelines, or autonomous motion with specific timing, clipping, loop seams, or lifecycle acceptance. |

Open only the references and sections needed for the chosen workflow. The
[motion example index](references/motion-examples.md) is optional and organized by behavior.

## Establish the Reference

1. Resolve the readable source, exact page/selector/region and state, reference viewport or
   image dimensions, and destination project/module/component. Record the requested verification
   target. Inspect the source and existing project before asking for missing details. Resolve
   material ambiguity about the source surface, viewport, or destination before writing code.
2. Use [local HTML capture](references/local-html-capture.md) after runtime scripts run, or use
   [image analysis](references/image-visual-analysis.md) for screenshots and designs. Establish
   a [coordinate baseline](references/coordinate-baseline.md) with source pixels, ArkUI vp,
   device screenshot pixels, safe area, and crop. If the screens differ in aspect ratio, check
   top, body, and bottom regions independently.
3. Build the static geometry first. Follow
   [ArkUI layout mapping](references/arkui-visual-mapping.md) for components, tokens, and
   responsive scaling. Keep text and layout native, reserve explicit coordinates for custom
   drawing, and align crops before comparing. When the reference uses compound effects, consult
   [compound CSS effect mapping](references/css-effect-mapping.md) for blur, mask, filter, and
   other layered effects. Use a custom layer only where needed and surface material
   approximations before using them. Keep the full page in ArkUI and limit pre-rendered imagery
   to decorative layers.

## Motion Workflow

1. Run the reference at the contract viewport. Observe normal and reduced-speed playback and
   write the [motion contract](references/motion-contract.md) for the applicable triggers,
   states, timing, gesture thresholds, velocity handoff, interruption, lifecycle, performance
   constraints, and reduced-motion behavior. Open only the applicable
   [conditional contract fields](references/motion-contract-fields.md), such as progress, paths,
   masks, loops, particles, interruption, or timing validation. Include only the destination
   route or shared element the contract needs.
2. Choose native animation, gesture, transition, or scroll APIs with
   [motion mapping](references/arkui-motion-mapping.md). For behavior-specific implementation
   shapes, open only the matching section of [motion patterns](references/arkui-motion-patterns.md).
   Use Canvas where the effect requires it. On layered or multi-track motion, first verify one
   representative track's start, intermediate, and end states on the target, then extend the
   binding. Choose checkpoints in the contract before capture.
3. Run [single-scene motion QA](references/motion-qa.md#single-scene-qa) on the changed scene.
   Exercise the contracted primary and interruption paths and all applicable repeat, reverse,
   re-entry, background, and reduced-motion paths. Add only the matching
   [behavior-specific QA](references/motion-qa-patterns.md) section for masks, loops, trails,
   scroll, tabs, navigation, lists, cards, bursts, or 3D. Use quick mode for sampled states,
   timing mode for named anchors, and device measurements for performance claims. Reuse the HTML
   baseline. Consult [timing and performance measurements](references/motion-measurement.md)
   for named timing checks or performance claims.

## Verify and Report

- When modifying this skill's bundled files, run
  `python scripts/validate_skill.py <skill-root>` before reporting completion.
- For builds and device operations, use [preflight](references/preflight.md) and the installed
  `harmonyos-capabilities` workflow when available. Otherwise inspect project settings,
  installed documentation, and CLI help. Use an explicit target and stay within the authorized
  install, launch, and capture scope. Obtain authorization for remote asset downloads or
  bundling where needed.
- Apply the [visual QA criteria and handoff](references/visual-qa.md#handoff). Use the
  [region comparison guide](references/region-comparison.md) for geometry mismatches and
  [failure patterns](references/visual-failure-patterns.md) when adjustments stop helping.
- For the motion workflow, also apply the
  [motion QA criteria and handoff](references/motion-qa.md#handoff). Report the evidence
  actually captured and the remaining differences. Resolve script and asset paths relative to
  this skill directory.

## Review Difficult Replicas

- During implementation, briefly record the symptom, failed approach, and evidence when
  repeated rework, a change of approach, or a late QA finding affects the result.
- At handoff, suggest at most one skill change if it would help on another page and change a
  decision about implementation or QA. Keep page-specific details in the task notes and label
  unresolved causes as hypotheses. Apply skill changes only during authorized maintenance.
- During maintenance, require recurrence on another page or a reliably reproducible finding
  with clear impact. State the trigger, action, verification, and applicable SDK or device scope.
  Fix routing if an existing rule was missed and revise its wording if it was unclear. Merge
  overlapping guidance. Put shared decisions in this file and scenario-specific advice in the
  closest reference. Check the original case and a nearby case before generalizing.
