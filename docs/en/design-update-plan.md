# XControlP design update plan

**Approved by the project owner on November 19, 2026.** The initial recommendation is **Projects First**. Compare it with the **Working Day** layout from the design review before deciding which screen opens by default. The project owner approves the final layout after seeing both prototypes.

The goal is to make it easy to see where a project has stalled, what the assistant (HQ) proposes, which action was added to the day plan, and how it turned out. Analytics, reports, and the other sections will use the same visual system, with their own priorities.

## Stage 1. Establish the baseline

1. **Prepare a reference copy.** Start from `main` at commit `5122e80` (version `1.0.01`). Use a separate copy of the code and prepare synthetic data for a fresh installation, a typical working day, and a larger dashboard with 30–50 projects. Include long names, active and dismissed alerts, a filled day plan, pending requests, and HQ replies.
2. **Walk through the current workflows in Edge.** Find a stalled project and its next stage, open the reason for an alert, act on an HQ proposal, add and complete a task, and review trends over a period. Record what is visible on entry, the number of transitions and scrolls, and any actions that are easy to miss.
3. **Map the screens and their states.** Give each section a primary purpose and action. Describe what it shows when it has no records, when it still needs setup, and when loading fails. Review the labels for the user's day-end note, the HQ day summary, and the day-results archive in English, Russian, and Hebrew.

**Deliverable** — baseline screenshots, a set of scenarios, and criteria for comparing the prototypes with the current application. [Current screen guide](using.md)

## Stage 2. Fix issues shared by both layouts

1. **Stabilize navigation.** Keep the selected row the same size as the other rows at the current text scale. Keep the comic icons compact. Use background and font weight to show selection, and clearly mark alerts and new replies.
2. **Put active alerts first.** When the Alerts screen opens, show each alert's reason, related project, and available actions first. Make the in-progress and dismissed states explicit. Place event history and statistics below.
3. **Make the bottom status bar consistent.** Check short and long screens, a narrow window, and enlarged text. Give the bar a predictable position and keep bottom controls reachable.

**Acceptance** — switching sections keeps menu items in place, an active alert is readable on entry at 1280 × 800, and the status bar leaves actions accessible. This work can be accepted independently of the new layout. [Navigation styles](../../css/pult.css#L148) · [Current render order](../../js/10-settings.js#L244)

## Stage 3. Compare two prototypes for the opening screen

1. **Projects First.** Put a short **Needs attention** row above the project list and filters. In each project row, show the current stage, the next stage, the last movement, and the alert reason when present. Expanding the row gives access to the full stage sequence and history. A linked HQ proposal can be opened alongside the project context.
2. **Working Day.** Show today's tasks, the next action, and incoming HQ items first. Give projects a compact view with quick access to the full project list and Alerts. Label the project in focus and today's task separately.
3. **Test both prototypes on equal terms.** Use the same data, labels, and visual treatment. Find a stalled project, identify its next stage, add an HQ proposal to the day plan, and mark the task complete. Compare time, transitions, wrong turns, and what attracts attention first. Open both variants with an empty day and with a large project list.
4. **Test the menu structure with the prototypes.** Try project groups as filters within the project list. Observe which sections need direct access and which are easier to find together. Let the walkthrough determine the number of top-level items.

**Owner decision** — choose the default opening screen and the sections that need direct access. Present both prototypes, the comparison, and a recommendation.

## Stage 4. Approve the visual system

1. **Create three reference screens.** Apply the selected structure to Overview, Alerts, and Day Plan. Define the appearance of a project row, active alert, HQ proposal, primary action, and expanded detail. Check how they work together across the three screens.
2. **Give visual cues distinct roles.** Use background and weight for the selected section. In the default palette, use a small orange marker for the current stage and focus. Identify urgency with words and an icon as well as color. Check the existing accent choices, themes, and icon sets in those same roles.
3. **Tune density and readability.** Choose typography that supports Latin, Cyrillic, and Hebrew. Check long names, mixed-direction text, the stage order in the right-to-left layout, visible keyboard focus, and contrast in both themes.
4. **Document the rules with examples.** Describe when to use a row, card, or chart, where illustrations help, and how to present empty states. The criterion for a recognizable XControlP design is that the relationship between a stage, a signal, and an action remains clear across screens and themes.

**Owner decision** — approve the visual system on the three reference screens before applying it throughout XControlP.

## Stage 5. Implement the design by section

| Order | Changes |
| --- | --- |
| **1. Overview, groups, and project details** | Use compact rows and group filters. Show the current and next stages and the last movement. Show the full stage sequence and history in the details. Move general activity trends to Statistics. |
| **2. Day Plan, Day Results, and Calendar** | Bring tasks and quick entry forward. Make completion, carryover, and closing the day easy to find. Clarify the personal note and results archive. Task completion is shown in the day plan, while the project stage follows the existing rules for confirmed progress. |
| **3. HQ and Digests** | Organize requests, replies, and proposals. Show which request is awaiting review, which proposal is already in the plan, and which was declined. Check adding a proposal to the plan and restoring a declined proposal. Make the news digest collections **Interesting** and **Useful** easy to find. |
| **4. Statistics, Overall Level, and Reports** | Give measures visual weight according to the purpose of each screen. Preserve period comparisons, the explanation of the index, saving reports, and printing. Use charts where the user reads trends or compares values. |
| **5. Ideas, Services, Research, and Settings** | Apply the common list, heading, and empty-state patterns. Use consistent translations for standard idea statuses and preserve the meaning of user-written labels. Verify language, theme, scale, icon, and update settings. |

Deliver the implementation in small, verifiable changes. Check existing links to sections. For interactive controls, verify the selected screen, expanded sections, form state, and keyboard focus during a data refresh.

## Stage 6. Run acceptance checks in Edge

1. **Verify complete workflows.** Follow an alert to its reason, project, and action. Follow an HQ request through the reply and proposal to a completed task. Open a project's current and next stages and its history. Also verify closing the day, reviewing a period, and saving a report.
2. **Verify a range of states.** Cover a fresh installation, a filled day, many projects, several alerts, a pending response, an empty section, and a section that needs setup. Check that names, statuses, and controls remain readable in both wide and narrow windows.
3. **Verify languages, themes, and controls.** Run the main tasks in English, Russian, and Hebrew, in light and dark themes. Check enlarged text, tab order, focus return from details, and right-to-left reading order.
4. **Run automated checks and compare with the baseline.** Run the existing repository checks. Add focused checks for changed scenarios outside the existing coverage. Present the before-and-after task results, screenshots, and open findings. [Repository checks](../../.github/workflows/checks.yml)

**Ready for release when** an active alert is visible on entry to Alerts, a user can find a project and understand its state from Overview, and a task added from a proposal appears in the day plan and remains there after a refresh. These actions must remain accessible in a narrow window and with enlarged text.

## Stage 7. Prepare the release and transition

1. **Verify a fresh start and an update from `1.0.01`.** Use reference copies to check settings, section links, and the main actions after a restart.
2. **Update the instructions and release notes in all three languages.** Explain where projects, alerts, and analytics now appear and where to find HQ actions.
3. **Present the build for approval.** Include the comparison with the baseline, check results, and a way to return to the previous code version. Agree on installation in the working dashboard and publication once the build is ready.
4. **Review the first working sessions after the transition.** Collect the owner's observations about what became faster and which transitions need adjustment. Use those observations to scope the next small release.

## Approval checkpoints

Approval of this plan starts Stages 1–3, including the separate navigation and alert fixes in a working copy. The remaining owner decisions are the opening layout and direct navigation, the visual system, and the release of the verified build.
