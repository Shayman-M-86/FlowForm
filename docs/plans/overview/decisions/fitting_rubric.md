# Main strategy

The rubric is actually helpful because it tells you what **must exist in v1** and what can wait. Based on your rubric and your current FlowForm vision, the best move is:

Build **FlowForm v1 as a smaller API-first product** that still fits your long-term architecture.

That means:

- keep the **real project name and concept**
- keep the **real planned stack**
- keep the **real deployment direction**
- reduce the **feature surface**
- make the **rule engine intentionally limited**
- focus on what the rubric can clearly assess

That fits your broader FlowForm idea of dynamic, answer-driven forms  and still aligns with your planned React + Flask + Postgres + JSON-rule architecture .

## The biggest constraint from the rubric

The capstone is heavily centered on:

- relational data modeling
- REST API design
- CRUD endpoints
- Auth0 RBAC
- endpoint testing
- deployment
- documentation

So for **version 1**, the capstone really wants a strong **backend API project with auth and tests**, not a huge product platform.

That means your first version should make the **dynamic form logic real**, but only in a controlled way.

## Best v1 product shape

I think the best first version is:

**A form creator can create a form with questions and answer options, attach simple branching rules, and a respondent can submit answers through the API or a minimal frontend.**

That is enough to prove the product.

## What to include in v1

### Core entities

Use a relational model for:

- users or creators
- forms
- questions
- answer options
- submissions
- responses

And keep rules in **JSON / JSONB** exactly as you planned .

### Rule engine scope

Keep the rule engine very small.

For v1, only support things like:

- `show_question`
- `hide_question`
- maybe `end_form`

Use one trigger:

- `on_answer`

Use only a few condition operators:

- `equals`
- `not_equals`
- maybe `contains`

That still matches your rule-engine design, but keeps it buildable .

### Authentication and RBAC

Because the rubric explicitly requires RBAC, you should make this part central in v1.

Use Auth0 with at least two roles, for example:

**Admin**

- create forms
- edit forms
- delete forms
- view submissions

**Participant**

- view published forms
- submit responses

That fits the rubric cleanly and also makes sense for FlowForm.

## What to leave for v2

These should be postponed:

- visual rule builder
- advanced scoring engine
- analytics dashboard
- complex branching combinations
- multi-page form designer
- large admin features
- multi-tenant organizations
- advanced audit tooling
- staging/production sophistication if it slows submission

Those are portfolio expansion features, not capstone essentials.

## Recommended v1 API design

Shape the API around the rubric.

A clean v1 could be:

### GET

- `GET /forms`
- `GET /forms/<id>`
- `GET /submissions/<form_id>` or `GET /forms/<id>/submissions`

### POST

- `POST /forms`
- `POST /forms/<id>/questions`
- `POST /forms/<id>/submit`

### PATCH

- `PATCH /forms/<id>`
- `PATCH /questions/<id>`

### DELETE

- `DELETE /forms/<id>`
- maybe `DELETE /questions/<id>`

That gives you the rubric coverage easily.

## Best v1 data model

A realistic first version could be:

- `Form`
- `Question`
- `AnswerOption`
- `FormRule`
- `Submission`
- `Response`

You could store rules either in a dedicated `form_rules` table with a JSON column, or as a JSON column on `forms`.  
For rubric clarity, I think a dedicated `form_rules` table is better because it still gives structure while preserving JSON flexibility.

## Best way to satisfy the rule concept without overbuilding

Do not make a full generic workflow engine in v1.

Instead:

- on submission of an answer
- evaluate a small set of JSON rules
- return the next visible questions

That is enough to demonstrate the adaptive behavior you described in your overview and technical plan .

## Frontend advice for v1

Because the rubric suggests a frontend but does not require a large one, make it minimal.

You only need enough UI to prove:

- Auth0 login redirect
- form list
- form detail
- simple form builder or at least question creation
- respondent form fill flow

Do not spend weeks making a polished frontend before the API is solid.

For capstone success, the backend is more important.

## Hosting advice for v1

Your long-term hosting plan is strong:

- frontend on S3 + CloudFront
- backend on ECS Fargate
- database on RDS
- Auth0 external

But for the very first submission, be careful not to let infra block the project.

If ECS/RDS deployment slows you down too much, the rubric only really requires the **API to be live on a cloud platform**. So your v1 deployment decision should optimize for **submission certainty first**, then you can keep the AWS plan for the stronger portfolio version.

## Best phased plan

### Phase 1 — Capstone v1

Goal: pass rubric with a real project

Build:

- relational SQLAlchemy models
- JSON-backed simple rules
- CRUD API
- Auth0 RBAC
- tests
- live deployment
- README

### Phase 2 — Portfolio v1.5

Goal: make it feel like a real product

Add:

- stronger React frontend
- polished form execution UX
- richer rule evaluation
- cloud deployment matching your AWS plan
- domain, DNS, CI/CD improvements

### Phase 3 — Portfolio v2

Goal: expand toward full FlowForm vision

Add:

- visual logic builder
- analytics
- scoring
- versioning
- better admin workflows

## My honest recommendation on scope

For the capstone, the **hero feature** should be:

**dynamic conditional questions powered by stored JSON rules**

That is what makes the project special.

Everything else should be simplified around that.

## Strong v1 concept statement

A good way to frame the project is:

**FlowForm is a dynamic questionnaire API and web app where authenticated users can create forms with conditional question logic, and respondents are guided through adaptive question flows based on their answers.**

That sounds real, matches your product idea, and fits the rubric.

## What I think you should do next

The next practical step is to turn the rubric into a **v1 scope document** with three sections:

- must-have for submission
- nice-to-have if time permits
- post-capstone roadmap

I can make that plan next and map each rubric item directly to concrete FlowForm features.
