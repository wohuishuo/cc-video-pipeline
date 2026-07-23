# Information Gap: 38 Independent Remotion Shots Design

## Goal

Replace the repeated 30-minute card skeleton with 38 independently rendered and verified shots. Preserve the dark investigative dossier aesthetic while giving every shot distinct composition, evidence, motion, and sound treatment.

The observable result is a master Remotion composition assembled exclusively from 38 individually accepted shot compositions. Every shot can also render its own still and short preview.

## Creative Direction

The visual language is premium investigative documentary rather than slideshow:

- charcoal, warm-black, ivory paper, restrained blue and warning red;
- physical depth from paper, glass, screens, shadows, camera parallax, and realistic surface texture;
- reconstructed interfaces and documents instead of unsupported real-company accusations;
- official case anchors where claims need public evidence;
- real or licensed generic B-roll for hands, phones, contracts, venues, devices, desks, and workspaces;
- one dominant visual argument per shot;
- no shot may consist only of a title and interchangeable rectangular cards.

Reusable primitives are allowed: typography, captions, paper texture, presenter window, source badge, redaction mark, cursor, camera rig, and transition utilities. Complete layouts are not reused in consecutive shots.

## Acceptance Unit

Each shot owns:

```text
shots/shot-NN/
  shot.json
  ShotNN.tsx
  assets/
  preview.png
  preview.mp4
```

Each `shot.json` declares:

- shot ID, chapter, start/end seconds, narration excerpt, and visual purpose;
- asset IDs and source/provenance records;
- music cue, sound effects, gain, fade, and ducking;
- composition family and unique-layout signature;
- expected text, evidence labels, and safety annotations;
- render status and verification receipt.

The master composition owns sequencing only. It cannot alter shot layouts, evidence, or audio decisions.

## 38-Shot Visual Plan

| Shot | Time | Visual result | Required material | Sound treatment |
| ---: | --- | --- | --- | --- |
| 01 | 0:00–0:08 | Four reconstructed offers scatter across a physical evidence desk; camera pushes toward the question | R01–R04 interface thumbnails, desk texture, presenter PIP | cold investigative pulse; four paper hits |
| 02 | 0:08–0:22 | Rapid four-screen phone carousel showing the four entry offers as distinct interfaces | R01–R04 full screens, phone frame, hand/scroll B-roll | pulse continues; four UI swipes |
| 03 | 0:22–0:45 | Materials wall: livestream, teacher, contract, and payment evidence connected but visibly incomplete | reconstructed screenshots, string/line graph, missing-evidence stamps | muted ticks; low uncertainty drone |
| 04 | 0:45–1:20 | Camera travels through a cashflow question built from receipts and arrows | receipt stack, payment nodes, animated question typography | music drops; bass impact on question |
| 05 | 1:20–1:30 | Chapter-title reset: money exits buyer and remains with seller despite failure | original ledger animation | chapter sting and short silence |
| 06 | 1:30–2:05 | Four-level legal/ethical boundary rendered as a museum evidence stair | C01, official terminology source badge | measured documentary cue begins |
| 07 | 2:05–2:50 | Split reconstruction: visible fulfilled actions versus undisclosed downstream conditions | R01/R03 fragments, contract/receipt closeups | paper turns; subtle tension bed |
| 08 | 2:50–3:35 | Entry-price tunnel leading from free/cheap offers into progressively larger commitments | R01–R04 price portals | forward riser; price clicks |
| 09 | 3:35–4:10 | Behavior funnel shown inside a phone analytics interface | C02, reconstructed analytics UI | soft electronic rhythm; step ticks |
| 10 | 4:10–5:10 | Screenshot wall collapses to reveal missing denominator questions | reconstructed success screenshots, C03 | camera shutters, then music cutoff |
| 11 | 5:10–5:35 | Monthly-income screenshot is physically dismantled into revenue and missing costs | C03/C05 number layers, calculator | number punches; calculator taps |
| 12 | 5:35–6:50 | Egg campaign travels through six real-world stations on a tabletop map | R02, B03 imagery, QR reconstruction, product package | warmer investigative cue; waypoint hits |
| 13 | 6:50–7:35 | One transaction becomes a long contact timeline across phone, group, lecture, test, and sales | chat UI, calendar, phone notifications | notification sequence under narration |
| 14 | 7:35–8:10 | First key question appears inside a paused chat/payment screen | reconstructed chat, payment sheet, contact trail | near-silence; single sub hit |
| 15 | 8:10–8:55 | Promise-label carousel: AI dividend, city partner, health management, high-pay remote work | R01/R03/R04, label tags | restrained momentum cue |
| 16 | 8:55–9:45 | Advertising promise is peeled back to reveal required conditions underneath | reconstructed sales page, layered terms, magnifier | adhesive peel and clause zoom |
| 17 | 9:45–10:35 | Franchise entrance price expands into a physical waterfall of total costs | R03, C04, receipts, equipment B-roll | percussive ledger cue; cost drops |
| 18 | 10:35–12:30 | Second key question navigates a maze of time, tools, customers, and platform constraints | original condition maze, icons, dead ends | tense minimal pulse; wrong-path stingers |
| 19 | 12:30–13:35 | Best-case stories occupy a glowing foreground while the missing population remains dark | reconstructed testimonials, population silhouettes | music thins; distant crowd texture |
| 20 | 13:35–14:50 | Eight missing-number evidence cards appear as distinct source documents, not repeated generic cards | C03 plus refund/ad/platform documents | eight light document hits |
| 21 | 14:50–15:45 | “30,000 per month” is decomposed in a financial workstation | spreadsheet reconstruction, invoices, calculator | number impact followed by mechanical rhythm |
| 22 | 15:45–17:00 | Revenue-to-profit waterfall passes through rent, labour, ingredients, platform and ads | C04/C05, R03, restaurant B-roll | subtraction ticks and low beat |
| 23 | 17:00–18:10 | Full fee chain becomes a long horizontal conveyor with different collectors below each node | C04, collector identities, invoices | industrial conveyor rhythm |
| 24 | 18:10–19:10 | Three simultaneous cashflow tracks compare course, franchise, and supply-chain businesses | R01/R03/R06, animated payment paths | three-layer rhythmic motif |
| 25 | 19:10–20:00 | Recruitment interface morphs into training contract and instalment bill | R04, O01 official case anchor | glitch morph, contract stamp |
| 26 | 20:00–22:00 | Interactive full-cost ledger lets each hidden charge enter a verified row | C04, invoices, source badges | quiet calculation cue; row-entry clicks |
| 27 | 22:00–22:50 | Seller-dependency question shown as two futures on a balance scale | original balance scene, buyer/seller paths | cue transition; heavy balance creak |
| 28 | 22:50–23:45 | Failure outcome and already-collected fees coexist on an asymmetric split screen | C05, failed storefront/generic work B-roll | low cello/drone; receipt hits |
| 29 | 23:45–24:35 | Control map shows ownership of supply, customers, platform, account and withdrawal rules | R06, network diagram | restrained tech pulse; node locks |
| 30 | 24:35–25:25 | Livestream display, product page, actual delivery and service explanation align in four material columns | R05, reconstructed product imagery | tactile package sounds; red-line hits |
| 31 | 25:25–26:30 | Seller-takes/buyer-keeps ledger fills both sides with physical tokens | C05, receipt and debt tokens | ledger cue resolves downward |
| 32 | 26:30–27:00 | Five-question chapter reset arranged as five sealed evidence folders | C06, folder textures | five stamp rhythm; hopeful transition |
| 33 | 27:00–27:25 | Median question: best case slides away and distribution chart comes forward | original distribution chart | single data reveal tone |
| 34 | 27:25–27:50 | Failure-rate question: exit paths branch into a Sankey-style failure map | original failure map | branching ticks and subdued pulse |
| 35 | 27:50–28:15 | Future-cost question: current price receipt unrolls into a longer hidden-cost receipt | R01/R03/R04, C04 | receipt printer sound |
| 36 | 28:15–28:45 | Delivery checklist compares livestream, page, package, and after-sales explanations item by item | R05, checklist overlays | checkbox sounds; mismatch warning |
| 37 | 28:45–29:25 | Final failure question overlays the four opening offers with completed seller cashflows | R01–R04 and resolved flow paths | opening motif returns, heavier bass |
| 38 | 29:25–30:00 | Sales-page language transforms into a clean personal ledger and downloadable five-question card | C06, final ledger, export card | restrained resolution cue; final paper close |

## Asset Strategy

### Reconstructed assets

R01–R06 are original fictional interfaces built for the video. They must use invented names, faces, numbers, phone numbers, and QR patterns and carry `示意重构` where confusion is possible.

### Official evidence

O01–O03 use only agency name, publication title, date, source URL, and short paraphrased findings. Full article bodies, copyrighted photographs, and unrelated identities are excluded.

### Licensed B-roll

Every downloaded asset receives an entry in `assets/asset-license.json` containing source page, direct file, creator, license, download date, attribution text, and permitted platforms. Assets without durable provenance remain blocked.

### Generated or original visuals

Original UI, charts, diagrams, reconstructed documents, and generic illustrative imagery may be produced locally. Generated imagery cannot depict a real identifiable accused business or person.

## Audio Design

Thirty-eight independent shots do not mean 38 unrelated songs. The soundtrack uses eight chapter cues:

| Cue | Shots | Mood |
| --- | --- | --- |
| M01 | 01–05 | cold investigative hook |
| M02 | 06–09 | measured explanatory tension |
| M03 | 10–14 | uncertainty and evidence inspection |
| M04 | 15–18 | promise-versus-condition pressure |
| M05 | 19–22 | analytical financial breakdown |
| M06 | 23–26 | industrial cashflow momentum |
| M07 | 27–31 | consequence and risk transfer |
| M08 | 32–38 | practical resolution and recall |

Each shot defines cue in/out, fades, narration ducking, and 0–3 transition effects. Music changes occur at chapter boundaries or intentional narrative pivots. Shot boundaries use sound design rather than arbitrary song replacement.

Source priority:

1. YouTube Audio Library tracks marked attribution-not-required where possible.
2. Mixkit music and effects under the applicable free license.
3. Pixabay audio after license and item-page review.
4. Freesound CC0 or CC-BY effects only; CC-BY receives attribution and non-commercial licenses are excluded.

`audio/audio-license.json` stores track title, artist, page URL, license URL, downloaded filename, SHA-256, attribution, download date, and assigned cues.

## State Owners and Invariants

| Mutable state | Unique owner | Invariant |
| --- | --- | --- |
| shot intent, timing, asset/audio references | `ShotSpec` | one version describes one renderable shot |
| asset file and licensing evidence | `AssetRegistry` | no unlicensed or unidentified asset can become approved |
| audio file, licence and cue assignment | `AudioRegistry` | every audible external file has provenance and permitted use |
| shot preview and approval receipt | `ShotBuild` | a shot is accepted only from its own verified render |
| master ordering and crossfades | `MasterTimeline` | master consumes accepted shot facts and cannot edit shot state |

## Capability DAG

```text
Shot specification
  ├──Query──> AssetRegistry ──Fact: licensed assets──┐
  ├──Query──> AudioRegistry ──Fact: licensed audio──┤
  └──Command────────────────────────────────────────> ShotBuild
                                                       |
                                                       ├──Fact: still verified
                                                       └──Fact: preview verified
                                                                |
Accepted ShotBuild facts (01..38) ──Query──────────────> MasterTimeline
```

Hard dependencies are the shot specification and accepted asset/audio facts. During early layout tests, generated placeholders may substitute for B-roll only if visibly labelled and if the shot cannot be marked asset-complete. An unapproved shot blocks master completion.

The lowest unproven node is Shot 01 with its real/reconstructed evidence, licensed audio cue, still, short preview, and verification receipt.

## Verification

Each shot must pass:

- Remotion composition discovery;
- TypeScript compilation/bundle;
- still render at an evidence-bearing frame;
- short video preview render;
- asset existence and licence-manifest validation;
- no secret, real phone number, active QR, or unsupported real-company identifier;
- text overflow and safe-area checks;
- at least two meaningful visual objects plus background texture and caption;
- unique-layout check against the previous shot;
- audio file, licence, cue, fade, and ducking validation.

Visual review occurs from the individual still/preview, never from assumptions based on code. After shots 01–38 pass, the master receives a composition listing check, chapter-boundary audio check, and sampled renders around every transition.

## Migration

- Keep the current `information-gap` compositions as legacy references during development.
- Build the new system under a separate `information-gap-shots` entry.
- Do not import the legacy 38-scene renderer into new shots.
- Selectively reuse only low-level primitives after a shot-specific test demonstrates value.
- Replace the master registration only after all 38 new shot facts are accepted.

## Non-goals

- No literal copying of Xiaolin's branding, presenter identity, footage, or proprietary graphics.
- No unsupported accusation against identifiable companies or people.
- No automatic acceptance based only on successful rendering.
- No 38-song soundtrack or music change at every cut.
- No vertical version until the horizontal 38-shot master is verified.
- No claim of production completion until licensed assets, narration timing, full audio mix, and full master render are verified.

## Delivery Ledger

- Current level: `DESIGNED`.
- Present evidence: 38-shot map, asset classes, audio policy, owners, invariants, DAG, verification gates, migration boundary.
- Missing evidence: implemented shot system, licensed files, stills, previews, accepted shots, narration timing, master render.
- Substitutes allowed: generated or reconstructed visuals during shot development, explicitly marked incomplete.
- Decision gates: final individual track selection and licensed B-roll choice depend on item availability at acquisition time.
- Forbidden claims: 38 shots implemented, audio licensed, master complete, Xiaolin style replicated exactly, platform or production verified.

