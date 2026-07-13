# Product Spec — insight-engine

## Problem

Product teams receive feedback across reviews, surveys, and support tickets, but synthesis is manual, slow, and biased toward whoever shouted loudest most recently. Decisions get made on anecdote instead of the corpus.

## Users

- **Primary:** Product managers who need a weekly signal on what customers are saying and what to do about it
- **Secondary:** Founders/leadership consuming the brief; support leads routing urgent themes

## Jobs to be done

1. "When feedback piles up, help me see the themes without reading 500 tickets."
2. "When I claim 'customers want X' in a roadmap discussion, give me cited evidence."
3. "When something starts breaking, surface it before it becomes churn."

## Core loop

Ingest → cluster into themes → score sentiment/urgency → suggested action per theme → weekly cited brief → PM decision.

## Success metrics

- **Activation:** first brief generated within 10 minutes of setup
- **Quality:** ≥80% of theme assignments judged correct on the eval set (see EVALS.md)
- **Trust:** 100% of brief quotes traceable to a real record ID (hard guarantee)
- **Outcome proxy:** # of themes marked "fix" that reach a roadmap item

## Non-goals (v0)

- Real-time streaming ingestion
- Multi-tenant auth
- Closing-the-loop ticket replies

## Riskiest assumptions

1. Cluster themes match how PMs mentally categorize feedback (test: eval set)
2. A weekly cadence is right (test: usage of on-demand `/brief` vs scheduled)
