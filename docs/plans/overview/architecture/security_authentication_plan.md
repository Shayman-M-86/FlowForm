# Flow Form — Security and Authentication Architecture Plan

## Purpose

This document outlines the planned security and authentication approach for **Flow Form**.

The goal is to use a modern, secure authentication model for a single page application while keeping the backend API protected and the user session experience smooth.

## Chosen Authentication Model

**Identity standard**

- OpenID Connect (OIDC)

**Authorization standard**

- OAuth 2.0 Authorization Code Grant with PKCE

**Identity provider**

- Auth0

**Session continuity**

- Refresh Token Rotation

## High-Level Architecture

### Frontend

- React single page application
- Uses Auth0 Universal Login for sign-in
- Starts login using Authorization Code Flow with PKCE
- Obtains short-lived access tokens for API calls
- Uses refresh token rotation to maintain the user session

### Backend

- Flask API
- Accepts bearer access tokens from the frontend
- Validates JWT access tokens using Auth0 issuer, audience, signing keys, and expiry
- Enforces authorization rules for protected endpoints

### Identity Provider

- Auth0 manages login, logout, user identity, token issuance, and refresh token rotation

## Planned Authentication Flow

1. User clicks **Log in** in the React app.
2. The SPA redirects the user to **Auth0 Universal Login**.
3. Auth0 authenticates the user.
4. Auth0 redirects back to the SPA with an **authorization code**.
5. The SPA completes the **Authorization Code + PKCE** flow.
6. Auth0 issues:
   - an **ID token**
   - an **access token**
   - a **rotating refresh token**
7. The SPA sends the **access token** to the Flask API as a bearer token.
8. The Flask API validates the JWT and returns protected data.
9. When the access token expires, the SPA uses the refresh token to obtain a new token pair through **Refresh Token Rotation**.

## Token Strategy

### ID Token

Used by the frontend to identify the authenticated user.

### Access Token

Used to call the Flask API.

Planned characteristics:

- short-lived
- audience set to the Flow Form API
- validated by the backend on each protected request

### Refresh Token

Used to keep the user signed in without forcing frequent reauthentication.

Planned characteristics:

- rotation enabled
- old refresh tokens become invalid after use
- reuse detection relied on through Auth0 controls

## Security Goals

- Use a modern SPA login flow
- Avoid the legacy implicit flow
- Protect the authorization code exchange with PKCE
- Keep access tokens short-lived
- Use refresh token rotation to reduce long-lived token risk
- Validate JWTs properly in the Flask backend
- Centralize identity and login management in Auth0
- Support future role-based access control and permissions

## Backend Validation Requirements

The Flask API should validate:

- token signature
- issuer
- audience
- expiry
- token type and intended usage
- permissions or roles where required

The API should reject:

- missing tokens
- expired tokens
- malformed tokens
- tokens with invalid issuer or audience
- tokens without required permissions

## Auth0 Configuration Plan

### Application

- Create a **Single Page Application** in Auth0 for the React frontend

### API

- Create an **API** in Auth0 for the Flask backend
- Define an API identifier / audience

### Login Configuration

- Configure allowed callback URLs
- Configure allowed logout URLs
- Configure allowed web origins

### Token Configuration

- Enable **Authorization Code Flow with PKCE**
- Enable **Refresh Token Rotation**
- Use short-lived access tokens

## Initial Recommendation

- Use the Auth0 SPA SDK in the frontend
- Avoid the implicit flow
- Avoid building custom authentication flows from scratch
- Keep frontend token handling minimal
- Keep backend authorization logic separate from Auth0 login concerns

## Future Security Enhancements

Planned later additions may include:

- role-based access control (RBAC)
- permission-based endpoint protection
- audit logging for authentication events
- anomaly detection and rate limiting
- admin-only routes
- stronger session management rules
- optional backend-for-frontend evaluation if browser-side token handling becomes a concern

## Flow Diagram

```mermaid-graph

React SPA
     │
     │ Authorization Code + PKCE
     ▼
Identity Provider (Auth0)
     │
     │ returns tokens
     ▼
Browser
     │
     │ Authorization: Bearer <access_token>
     ▼
API (Flask)
     │
     │ verify JWT using JWKS
     ▼
Protected resources
```

## Summary

Flow Form will use a modern SPA authentication architecture based on:

- **OpenID Connect**
- **OAuth 2.0 Authorization Code Grant with PKCE**
- **Auth0 as the identity provider**
- **Refresh Token Rotation**
- **JWT bearer access tokens for the Flask API**

This gives the project a strong modern starting point that is secure, standard, and well supported.
