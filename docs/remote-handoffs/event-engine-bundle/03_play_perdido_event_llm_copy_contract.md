# Play Perdido Event LLM Copy Contract
## Prompt, Rubric, Rewrite, and QA Workflow for External Event-Copy Generation

---

# Purpose

This document is the content-generation companion to:

- [10_play_perdido_event_submission_contract.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/10_play_perdido_event_submission_contract.md)

Use it when an external system is responsible for generating:

- event titles
- event summaries
- event detail copy
- CTA labels
- teaser copy used in cards or previews

This contract exists to keep event copy:

- consistent with Play Perdido branding
- useful in a discovery-first UI
- readable on mobile
- distinct across the site
- free of chamber-style filler and generic tourism language

This is not optional polish.

It is part of the ingest quality bar.

---

# Relationship To Other Docs

Use this together with:

- [09_play_perdido_llm_content_rubric_usage.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/09_play_perdido_llm_content_rubric_usage.md)
- [10_play_perdido_event_submission_contract.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/10_play_perdido_event_submission_contract.md)
- [01_play_perdido_uiux_strategy.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/01_play_perdido_uiux_strategy.md)
- [06_play_perdido_data_model_taxonomy_strategy.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/06_play_perdido_data_model_taxonomy_strategy.md)
- [play_perdido_llm_content_guidelines_rubric.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/tools/play_perdido_llm_content_guidelines_rubric.md)

If this document conflicts with the generic rubric, this document wins for event-copy specifics.

---

# What The External LLM Is Allowed To Do

The external content system may:

- normalize raw event titles
- rewrite weak source copy
- generate concise summaries
- produce cleaner detail copy
- propose CTA labels
- remove spam, noise, and source-system artifacts

The external content system may not:

- invent venues
- invent dates or times
- invent prices
- invent artists, sponsors, or hosts
- invent accessibility claims
- invent family-friendliness when not supported
- invent Perdido relevance when geography is weak

The model may clarify.

It may not fabricate.

---

# Inputs The LLM Must Receive

Every event-copy generation run should receive:

1. raw source title
2. raw source body
3. canonical category or categories
4. canonical location name
5. event date/time facts
6. Perdido-fit status
7. source URL if available
8. any known organizer or CTA URL

Recommended extra inputs:

- source-system tags
- image presence or absence
- whether the event is recurring
- nearby discovery branch hints like `Live Music`, `Food & Drink`, or `Beach & Water`

The model should never be asked to infer event facts from brand strategy alone.

---

# Required Output Fields

The LLM layer should produce:

- `normalized_title`
- `summary`
- `detail_copy`
- `cta_label`
- `copy_quality_report`

Recommended:

- `copy_flags`
- `review_required`
- `why_review_required`

---

# Event Copy Standards

## 1. Title Standard

Titles should be:

- specific
- readable
- human
- concise
- useful in lists and cards

Titles should not:

- look machine-generated
- repeat the same venue phrasing across many events
- use spammy separators unless the source event truly needs them
- overstuff location, category, and date into one line
- rely on all caps

### Title Rules

1. Keep the actual event identity intact.
2. Remove noise like duplicated venue phrases, tracking junk, and broken separators.
3. Preserve artist or event names exactly when they are the point of the event.
4. Do not append category labels like `Live Music` if the title already makes that clear.
5. Do not inject `Perdido` into every title.

### Good Title Behavior

- `Friday Night Live Music at Bar45`
- `Buzz Runners`
- `Education in Motion`

### Bad Title Behavior

- `PERDIDO LIVE MUSIC FRIDAY NIGHT AT BAR45!!!`
- `Bar45 Friday Happy Hour Live Music Gulf Shores Alabama Near Perdido`
- `Get Lost in Perdido With Friday Night Live Music`

## 2. Summary Standard

Summary is the most important event-copy field for the site UI.

It will support:

- event cards
- feed previews
- accordion expansions
- branch pages

Summary should:

- explain what it is
- help the user decide
- mention who it fits or why it matters
- stay concrete and short

Target length:

- `35` to `90` words

Summary should not:

- repeat the title
- repeat full date/time strings already shown elsewhere in the UI
- read like brochure filler
- overuse adjectives
- sound like a press release

## 3. Detail Copy Standard

Detail copy can be fuller than summary, but still must be disciplined.

Target length:

- `70` to `220` words in most cases

Detail copy should:

- clean up weak source text
- preserve useful event facts
- improve readability
- keep a local, calm, useful tone

Detail copy should not:

- balloon into article-length prose
- repeat the summary verbatim
- preserve source spam or keyword stuffing
- read like a chamber listing dump

## 4. CTA Standard

Allowed CTA styles:

- `View Details`
- `Learn More`
- `Register`
- `Get Tickets`
- `See Event Info`

CTA labels should stay practical.

Do not generate:

- `Don’t Miss Out`
- `Act Now`
- `Reserve Your Spot Today`

unless the source context truly requires a stronger transactional label and the link destination supports it.

---

# Anti-Redundancy Rules

This system must actively avoid repetitive event copy.

## Across A Single Event

Do not make:

- `normalized_title`
- `summary`
- `detail_copy`

all say the same thing in slightly different words.

Required distinction:

- title identifies
- summary helps decide
- detail copy provides fuller context

## Across Similar Events

If a venue or source posts recurring events, the LLM must avoid turning them into clones.

Examples:

- recurring happy hours
- recurring live music nights
- recurring golf scrambles
- recurring market listings

The engine should vary summary framing based on the actual event type:

- social night
- music-forward
- family-friendly
- skill-based
- outdoor activity

## Forbidden Repetition Patterns

Reject or rewrite copy when:

1. the first sentence begins the same way across multiple events
2. the same adjective stack appears repeatedly
3. every summary says `perfect for locals and visitors`
4. every event says `soak in the vibes`
5. every event says `don’t miss`
6. every event says `something for everyone`

---

# Required Generation Workflow

The external system must use this loop for every event.

## Step 1: Fact Extraction

Extract only supported facts:

- event identity
- venue
- activity type
- audience clues
- cost clues
- action clues

If facts are unclear, mark them uncertain.

## Step 2: Draft

Generate:

- title
- summary
- detail copy
- CTA label

## Step 3: Rubric Score

Score the draft using the event-copy rubric below.

## Step 4: Analytical Rewrite Pass

The model must explicitly identify:

- what feels generic
- what feels repetitive
- what is too long
- what lacks local usefulness
- what sounds too promotional
- what could cause poor card UX or mobile scan speed

## Step 5: Rewrite

Rewrite based on the analytical findings.

## Step 6: Re-score

Re-score the rewritten version.

## Step 7: Stop Or Escalate

If the content still fails threshold after `3` rewrite passes:

- mark `review_required = true`
- explain why

---

# Event-Copy Rubric

Score each event output on a `100` point scale.

## Categories

1. Brand Alignment — `20`
2. Usefulness / Decision Support — `20`
3. Clarity and Brevity — `15`
4. Local and Contextual Fit — `10`
5. Distinctiveness / Anti-Redundancy — `15`
6. Mobile Readability — `10`
7. Accuracy Discipline — `10`

Total:

- `100`

## 1. Brand Alignment — 20

High score:

- feels like a thoughtful local guide
- supports discovery
- avoids hype
- sounds like Play Perdido

Low score:

- sounds corporate
- sounds like a chamber blast
- sounds like generic tourism copy

## 2. Usefulness / Decision Support — 20

High score:

- helps the user quickly decide whether to click or go
- clarifies what kind of event it is
- frames relevance well

Low score:

- decorative but vague
- gives no decision value

## 3. Clarity and Brevity — 15

High score:

- concise
- quick to scan
- strong first sentence
- no filler

Low score:

- bloated
- repetitive
- hard to parse on mobile

## 4. Local and Contextual Fit — 10

High score:

- appropriately rooted in the local experience
- respects geography and category context

Low score:

- could describe any event in any beach town
- ignores the event’s actual branch context

## 5. Distinctiveness / Anti-Redundancy — 15

High score:

- does not echo other event summaries
- avoids template sameness
- varies rhythm and framing naturally

Low score:

- sounds cloned
- repeats common filler structures

## 6. Mobile Readability — 10

High score:

- works in cards and short preview surfaces
- front-loads useful information

Low score:

- buries meaning
- wastes the first sentence

## 7. Accuracy Discipline — 10

High score:

- stays inside source facts
- avoids invented claims
- reflects uncertainty honestly

Low score:

- embellishes unsupported facts
- fabricates specifics

---

# Required Thresholds

Use these minimum thresholds:

- title: `98/100`
- summary: `96/100`
- detail copy: `96/100`
- CTA label: `94/100`
- full event bundle average: `96/100`

Hard fail conditions:

- any fabricated fact
- any non-canonical category language in public-facing copy
- obvious chamber or press-release tone
- obvious repetitive template copy

---

# Prompt Templates

These are the prompts the external system should use or adapt.

## Prompt 1: Event Title Normalizer

```text
You are writing for Play Perdido, a discovery-first local events site.

Your job is to normalize a raw source event title into a clean public title.

Rules:
- Preserve the real event identity.
- Remove junk separators, source noise, duplicated venue text, and spammy casing.
- Keep the title specific and readable.
- Do not invent facts.
- Do not add hype.
- Do not add "Perdido" unless it is truly part of the event identity.
- Optimize for event cards, lists, and mobile scanning.

Return:
1. normalized_title
2. short rationale

Raw title:
{{raw_title}}

Known facts:
{{facts}}
```

## Prompt 2: Event Summary Writer

```text
You are writing a short event summary for Play Perdido.

Context:
- Play Perdido is not a chamber calendar or tourism brochure.
- The tone should be local, clear, useful, calm, and inviting.
- The summary must help a user decide whether this event is worth a tap.

Rules:
- 35 to 90 words.
- Do not repeat the title.
- Do not repeat full date and time if the UI already shows them.
- Explain what kind of event this is and why it may be relevant.
- Keep it specific.
- Avoid generic hype, filler adjectives, and boilerplate.
- Do not invent facts.
- Do not use sales language.

Category context:
{{categories}}

Venue:
{{location_name}}

Raw source title:
{{raw_title}}

Raw source body:
{{raw_body}}

Return only:
summary
```

## Prompt 3: Event Detail Copy Rewriter

```text
You are rewriting event detail copy for Play Perdido.

Goal:
- Preserve useful facts.
- Remove junk, duplication, spam, and source-system awkwardness.
- Keep the result readable, mobile-friendly, and consistent with a discovery-first local guide.

Rules:
- 70 to 220 words unless the source requires less.
- Keep the tone calm, practical, and local.
- Do not sound like a press release.
- Do not invent facts.
- Preserve important venue, activity, and audience details when supported.
- Avoid repeating the summary sentence-for-sentence.

Known facts:
{{facts}}

Raw source body:
{{raw_body}}

Return only:
detail_copy
```

## Prompt 4: Analytical Rewrite Pass

```text
You are reviewing event copy for Play Perdido before publication.

Evaluate the title, summary, detail copy, and CTA label.

Identify:
- generic language
- repetitive patterns
- weak mobile readability
- vague decision support
- branding drift
- unsupported claims

Then rewrite the copy to improve it while staying faithful to the source facts.

Return:
1. issues_found
2. revised_title
3. revised_summary
4. revised_detail_copy
5. revised_cta_label
```

## Prompt 5: Event Copy Scoring Pass

```text
You are scoring event copy for Play Perdido.

Use this rubric:
- Brand Alignment — 20
- Usefulness / Decision Support — 20
- Clarity and Brevity — 15
- Local and Contextual Fit — 10
- Distinctiveness / Anti-Redundancy — 15
- Mobile Readability — 10
- Accuracy Discipline — 10

Score:
- title
- summary
- detail copy
- CTA label
- overall bundle

Then decide:
- pass
- rewrite
- human review

Return structured scoring and brief justification.
```

---

# Recommended Structured Output

The external system should capture the full QA trail.

Recommended output:

```json
{
  "normalized_title": "",
  "summary": "",
  "detail_copy": "",
  "cta_label": "",
  "copy_quality_report": {
    "title_score": 0,
    "summary_score": 0,
    "detail_copy_score": 0,
    "cta_score": 0,
    "overall_score": 0,
    "status": "pass",
    "issues_found": [],
    "rewrite_passes": 0,
    "review_required": false,
    "why_review_required": ""
  }
}
```

---

# Review Triggers

Require human review when:

1. the source event is outside the normal geography
2. the source body is extremely weak
3. the event facts are contradictory
4. the model keeps producing repetitive copy
5. the title cannot be cleaned without risking factual drift
6. the copy score stays below threshold after three passes

---

# Final Rule

The point of this workflow is not to make event copy sound more “AI.”

The point is to make it:

- cleaner
- more useful
- more local
- more consistent
- more distinct

If the external system cannot produce content that strengthens the Play Perdido product experience, it should send the record to review instead of pretending the copy is ready.
