# FlowForm — Technical Architecture Overview

## Purpose
This document provides a high-level technical overview of the planned architecture for **FlowForm**.

FlowForm is designed as a dynamic form platform that allows questionnaires, surveys, quizzes, and decision-based forms to adapt in real time based on user input.

## Core Architecture

FlowForm is planned as a modern web application with three main layers:

- **Frontend:** React single page application
- **Backend:** Flask API
- **Database:** PostgreSQL

The system will use a primarily relational data model for forms, questions, answers, submissions, and related entities, with flexible JSON-based storage for custom rule definitions.

## Frontend

### Technology
- React
- Single Page Application (SPA)

### Responsibilities
The frontend will be responsible for:
- rendering forms and interactive question flows
- managing the user interface and client-side experience
- sending user input to the backend API
- handling authentication with Auth0
- maintaining session continuity through the authentication SDK and token refresh flow

### Frontend Role in FlowForm
The React SPA will present forms to users and update the visible questions dynamically as answers are submitted or evaluated.

This layer will focus on:
- smooth user experience
- responsive form rendering
- authenticated API communication
- integration with the form execution flow

## Backend

### Technology
- Python
- Flask
- SQLAlchemy

### Responsibilities
The backend will act as the main application and business logic layer.

It will be responsible for:
- exposing API endpoints for the frontend
- storing and retrieving form definitions
- evaluating form logic and rule conditions
- managing submissions and results
- validating authenticated requests
- enforcing authorization rules

### Backend Role in FlowForm
The Flask API will serve as the central engine for the application.

It will coordinate:
- form creation and management
- question and answer storage
- rule retrieval and execution
- submission processing
- protected operations for authenticated users

## Database

### Technology
- PostgreSQL

### Data Model Approach
FlowForm will use a **primarily relational SQL schema** for the core application data.

This includes structured entities such as:
- users
- forms
- questions
- answer options
- submissions
- response records

This relational model supports:
- strong data integrity
- clear relationships between entities
- reliable querying and reporting
- easier long-term maintenance

## Rule Storage Model

The custom rule system will be stored as **JSON in the database**.

### Why JSON for Rules
The rule layer needs more flexibility than the rest of the relational model because rules may vary in structure depending on the form’s logic.

Examples of rule behaviour include:
- showing or hiding questions
- skipping sections
- branching to another question
- scoring quiz answers
- driving decision-tree style flows

### Planned Approach
- store rules in JSON format in PostgreSQL
- parse and validate rule structures in the backend
- execute rule logic within the Flask application

This allows the platform to keep the core data relational while giving the rule engine flexibility where needed.

## Authentication and Security Architecture

### Authentication Standards
- OAuth 2.0 Authorization Code Grant with PKCE
- OpenID Connect (OIDC)

### Identity Provider
- Auth0

### Session Strategy
- Refresh Token Rotation

### Planned Authentication Flow
FlowForm will use a modern SPA authentication flow:

1. The React SPA redirects the user to Auth0 Universal Login.
2. The user authenticates with Auth0.
3. Auth0 redirects back to the SPA with an authorization code.
4. The SPA completes the Authorization Code + PKCE flow.
5. Auth0 issues tokens for the session.
6. The frontend sends access tokens to the Flask API.
7. The Flask API validates JWT access tokens before allowing access to protected resources.
8. Refresh Token Rotation is used to maintain session continuity securely.

### Security Goals
The authentication design aims to:
- use a modern standard login flow for browser applications
- avoid the implicit flow
- keep access tokens short-lived
- use refresh token rotation for safer long-lived sessions
- centralize identity management in Auth0
- protect backend endpoints with JWT validation

## API Design Direction

The backend will expose API endpoints for both application management and runtime form usage.

Likely areas include:
- authentication-aware user endpoints
- form creation and editing endpoints
- question and answer management endpoints
- rule definition endpoints
- form execution or submission endpoints
- results and analytics endpoints in later versions

## High-Level Request Flow

### Form Management Flow
- authenticated user accesses the React application
- frontend calls the Flask API
- backend stores form structure and related entities in PostgreSQL
- custom rules are stored as JSON in the database

### Form Execution Flow
- end user opens a form
- frontend renders the current question set
- answers are submitted to the backend
- backend evaluates rules and determines the next state of the form
- frontend updates the visible questions accordingly

## Initial Technology List

### Frontend
- React
- SPA architecture

### Backend
- Python
- Flask
- SQLAlchemy

### Database
- PostgreSQL
- JSON rule storage inside the database

### Authentication
- OAuth 2.0 Authorization Code Grant with PKCE
- OpenID Connect (OIDC)
- Auth0
- Refresh Token Rotation

## Long-Term Expansion Areas

Potential future additions may include:
- role-based access control (RBAC)
- advanced permissions
- form analytics
- audit logging
- visual rule builders
- scoring engines for quizzes
- versioning for forms and rules
- background processing for large workflows

## Summary

FlowForm is planned as a React SPA backed by a Flask API, using SQLAlchemy and PostgreSQL for the main data model.

The application will use a relational database structure for core entities, while storing the custom form rule system as JSON for flexibility.

Authentication will use **OAuth 2.0 Authorization Code Grant with PKCE**, **OpenID Connect**, **Auth0**, and **Refresh Token Rotation**.

This architecture gives FlowForm a strong foundation for dynamic form execution, secure user authentication, and future expansion.

