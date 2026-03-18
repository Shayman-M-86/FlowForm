# Flow Form — CI/CD Pipeline Plan

## Purpose
This document outlines the planned Continuous Integration and Continuous Deployment (CI/CD) pipeline for **FlowForm**.

The goal is to automate testing, building, and deployment of both the frontend and backend services while keeping the system understandable and maintainable.

The pipeline will support reliable deployments to **staging** and **production** environments.

---

# CI/CD Overview

FlowForm will use a CI/CD pipeline that automatically:

- runs tests when code changes
- builds the frontend and backend artifacts
- stores backend container images
- deploys the application to staging
- allows controlled promotion to production

The pipeline will manage deployments for both services:

- React frontend
- Flask backend API

---

# Source Control

Source code will be stored in **GitHub**.

The repository will contain:

- React frontend code
- Flask backend code
- infrastructure configuration
- Docker configuration

## Branch Strategy

The project will use a simple branching strategy.

### Main Branch

`main`

- represents production-ready code
- protected branch
- deployments originate from this branch

### Feature Branches

`feature/*`

- used for development work
- merged through pull requests

### Hotfix Branches (optional)

`hotfix/*`

- used for urgent fixes to production

---

# CI/CD Platform

The pipeline will use **GitHub Actions**.

GitHub Actions will:

- run automated tests
- build Docker images
- push images to AWS
- deploy the application

---

# Continuous Integration (CI)

Continuous Integration runs automatically when code is pushed or when pull requests are opened.

CI will perform the following steps:

### 1. Install Dependencies

- install frontend dependencies
- install backend dependencies

### 2. Static Checks

Examples may include:

- linting
- formatting checks

### 3. Run Tests

- frontend tests
- backend unit tests

### 4. Build Backend Container

The backend Flask API will be packaged into a Docker container.

### 5. Verify Container Build

Ensure the container builds successfully before merging.

---

# Continuous Deployment (CD)

Deployment will occur after code is merged into the `main` branch.

The deployment pipeline will build application artifacts once and promote them through environments.

---

# Backend Deployment Pipeline

### Step 1 — Build Docker Image

The backend container image is built from the repository.

### Step 2 — Push Image to Amazon ECR

The Docker image will be pushed to **Amazon Elastic Container Registry (ECR)**.

### Step 3 — Deploy to ECS Staging Service

The ECS service running in the **staging environment** will be updated to use the new container image.

### Step 4 — Run Basic Health Checks

The pipeline will verify that the service starts successfully.

### Step 5 — Production Promotion

After staging verification, the same container image can be promoted to production.

This ensures the exact same build is used in both environments.

---

# Frontend Deployment Pipeline

### Step 1 — Build React Application

The React project will be built using:

```
npm run build
```

This produces the static frontend assets.

### Step 2 — Upload Build to S3

The build output will be uploaded to the **S3 frontend bucket**.

### Step 3 — Invalidate CloudFront Cache

After deployment, the CloudFront distribution cache will be invalidated so users receive the latest frontend files.

---

# Environments

FlowForm will initially use two environments.

## Staging

Used for validating deployments before production.

Characteristics:

- separate ECS service
- separate environment configuration
- same infrastructure structure as production

## Production

The live application used by real users.

Characteristics:

- production ECS service
- production database
- protected deployment process

---

# Secrets and Configuration

Sensitive values will not be stored in source code.

Secrets will be stored using:

- **GitHub Secrets** for CI/CD access
- **AWS Secrets Manager or Parameter Store** for runtime configuration

Examples include:

- database credentials
- Auth0 configuration
- API keys

---

# Image and Build Strategy

The pipeline will follow a **build once, deploy many** strategy.

- container image built once
- pushed to ECR
- same image promoted through environments

This improves reliability and prevents environment-specific build differences.

---

# Future Improvements

Possible enhancements may include:

- automated integration testing against staging
- blue/green deployments for ECS
- preview environments for pull requests
- infrastructure provisioning through Terraform or CloudFormation

---

# Summary

The FlowForm CI/CD pipeline will:

- use **GitHub Actions** for automation
- run tests on every change
- build backend containers
- store images in **Amazon ECR**
- deploy the backend to **ECS Fargate**
- deploy the frontend to **S3 + CloudFront**

This pipeline provides reliable automated deployments while keeping the system relatively simple and maintainable.

