# Partial Creator Catalog Recovery Design

## Problem and evidence

The live Studio run history proves that **Load all videos** already sends `maxItems=0`; it does not require a browser scroll loop. The successful three-item Douyin run used a local Netscape cookie file, while every later load-all attempt used `authenticationFile=null` and failed with `creator profile returned no videos`. Studio then retained the truthful three-item catalog but unconditionally rejected every campaign because `complete=false` and `truncated=true`.

## Product result

A creator can retry complete discovery with the same existing local authentication-file reference. If the platform still cannot enumerate the full account, the creator can explicitly commit an exact selection from the currently observed catalog and continue through translation, voice and local delivery. The UI never labels a partial catalog as complete.

## Capability proof

| Proof field | Decision |
| --- | --- |
| Observable result and owner | Video Graph Studio admits an explicitly acknowledged exact selection from an incomplete Creator Manifest. Creator Selection remains owner of selected IDs and lineage. |
| Protected invariants | Partial status remains visible; consent is explicit; every selected ID exists in the immutable source manifest; no undiscovered video is claimed; empty selections remain rejected. |
| Public contract | `allowPartialCatalog: true` on `creator-campaign`; omitted or false preserves the strict complete-catalog gate. |
| Minimum hard closure | verified Creator Discovery run, Creator Catalog projection, exact selected IDs, Creator Selection public launcher. |
| Safe substitute | Existing incomplete manifest is valid evidence only for the items it contains, never evidence of full account coverage. |
| Decision gate | Browser requires a visible confirmation checkbox before adding `allowPartialCatalog`. |
| RED assertion | A partial catalog plus selected IDs and explicit consent is currently rejected by both browser readiness and the versioned create-run endpoint. |
| Adjacent integration | Studio creates the Campaign Graph, then the existing Creator Selection adapter verifies exact source lineage before Creator Batch begins. |

## Interaction design

When a restored or newly discovered catalog is incomplete, the Videos stage shows:

1. the existing warning and **Load all** action;
2. the reason that platform enumeration may require the saved cookie file;
3. a separate unchecked **Process only the currently loaded videos** confirmation.

Selecting the confirmation removes only the complete-catalog blocker. Video selection, languages, translation provider, voice provider, local output and all existing validation remain required. Starting a run resets no catalog metadata.

The Source stage restores an existing authentication-file path only from the same completed discovery run already projected by Studio. It never reads cookie contents into browser state and never logs them.

## Failure matrix

| Failure | Result |
| --- | --- |
| Load-all without usable authentication | discovery fails, previous catalog remains visible, exact partial-selection option remains available |
| Partial catalog without explicit consent | campaign rejected |
| Consent true with complete catalog | accepted; flag is harmless and retained as request policy |
| Selected ID absent from catalog | existing exact-selection validation rejects it |
| Cookie file no longer exists | backend rejects the authentication path; UI retains the previous catalog |
| Child localization failure | existing Creator Batch checkpoints and retry policy apply |

## Evidence and non-goals

Focused model and API tests will prove default rejection and explicit admission. A real browser drill will restore the existing three-item run, show the cookie reference, enable partial selection and reach a voice-ready preflight without starting the expensive dubbing workload.

This slice does not add browser-session scraping, simulated scrolling, CAPTCHA handling, hidden cookie extraction or a claim that a partial catalog represents the whole account.
