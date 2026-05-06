# Play Perdido Remote Event Engine Bundle
## Shareable Handoff for Event Ingest and Event-Copy Generation

---

# Purpose

This folder is the self-contained handoff bundle for any remote project that will:

- generate event payloads for Play Perdido
- generate titles, summaries, and event marketing copy
- push those events into the Play Perdido ingestion pipeline

The remote project should not need the rest of the Play Perdido repo to understand the contract.

---

# Required Read Order

Read these first, in order:

1. [01_play_perdido_event_submission_contract.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/remote-handoffs/event-engine-bundle/01_play_perdido_event_submission_contract.md)
2. [02_play_perdido_event_submission_contract.schema.json](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/remote-handoffs/event-engine-bundle/02_play_perdido_event_submission_contract.schema.json)
3. [03_play_perdido_event_llm_copy_contract.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/remote-handoffs/event-engine-bundle/03_play_perdido_event_llm_copy_contract.md)

Then read these for brand, taxonomy, and rubric context:

4. [04_play_perdido_llm_content_rubric_usage.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/remote-handoffs/event-engine-bundle/04_play_perdido_llm_content_rubric_usage.md)
5. [05_play_perdido_llm_content_guidelines_rubric.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/remote-handoffs/event-engine-bundle/05_play_perdido_llm_content_guidelines_rubric.md)
6. [06_play_perdido_data_model_taxonomy_strategy.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/remote-handoffs/event-engine-bundle/06_play_perdido_data_model_taxonomy_strategy.md)
7. [07_play_perdido_uiux_strategy.md](/home/steve/Desktop/Documents/Envision Perdido/build/playperdido/docs/remote-handoffs/event-engine-bundle/07_play_perdido_uiux_strategy.md)

---

# What Each File Does

## 01 Event Submission Contract

Defines:

- canonical payload structure
- allowed event categories
- location requirements
- geography and review rules
- WordPress and EventON mapping expectations

This is the authoritative ingest contract.

## 02 JSON Schema

Defines:

- machine-validatable payload structure
- enums
- required fields

Use this for pre-flight validation before sending payloads.

## 03 Event LLM Copy Contract

Defines:

- allowed and forbidden LLM behavior
- title, summary, detail-copy, and CTA standards
- anti-redundancy rules
- scoring thresholds
- draft -> score -> rewrite -> re-score workflow
- reusable prompt templates

This is the authoritative content-generation contract.

## 04 Rubric Usage

Explains how the broader Play Perdido rubric is meant to be applied operationally.

## 05 Full Content Rubric

Defines the deeper brand and scoring rules behind Play Perdido content quality.

## 06 Data Model and Taxonomy Strategy

Explains why the event engine must obey the Play Perdido category model instead of source-system taxonomy.

## 07 UI/UX Strategy

Explains the product the remote system is feeding.

This matters because the event copy and metadata must support:

- discovery-first UX
- feed-first pages
- curated category browsing
- mobile-first event cards

---

# Non-Negotiable Handoff Notes

The remote project should assume:

1. source taxonomy is advisory only
2. Play Perdido category enums are authoritative
3. linked structured locations are required
4. event copy must pass the LLM rewrite-and-rubric workflow before payload submission
5. highly repetitive recurring-event copy is not acceptable
6. the system should prefer `review` over low-quality `publish`

---

# Minimum Files If You Need To Forward Only The Essentials

If a smaller subset must be shared, use:

- `01_play_perdido_event_submission_contract.md`
- `02_play_perdido_event_submission_contract.schema.json`
- `03_play_perdido_event_llm_copy_contract.md`

That is the minimum viable handoff.
