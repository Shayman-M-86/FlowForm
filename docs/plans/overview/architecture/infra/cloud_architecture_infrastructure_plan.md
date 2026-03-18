# Flow Form — Cloud Architecture and Infrastructure Plan

## Purpose
This document gives a short overview of the planned cloud hosting and infrastructure approach for **FlowForm**.

The goal is to keep the architecture modern, container-based, and reasonably cost-effective while still using production-style AWS services.

---

## Cloud Provider
- **AWS**

FlowForm will be hosted in AWS, with the frontend and backend deployed as separate services.

---

## Frontend Hosting
- **React Single Page Application**
- **Static hosting with Amazon S3**
- **Content delivery through Amazon CloudFront**

### Planned Role
The frontend will be built into static files and hosted in an S3 bucket.

CloudFront will sit in front of S3 to provide:
- fast global delivery
- HTTPS support
- caching of static assets
- a clean public entry point for the frontend

---

## Backend Hosting
- **Flask API**
- **Containerized with Docker**
- **Hosted on Amazon ECS with Fargate**

### Planned Role
The backend will run as a containerized service and expose the application API used by the frontend.

Amazon ECS Fargate is the preferred deployment target because it provides a good middle ground between simplicity and real-world AWS container infrastructure.

It allows the application to remain container-based without the cost and complexity of Kubernetes.

---

## Database

- **Amazon RDS for PostgreSQL**

### Planned Role

PostgreSQL will be hosted as a managed database service in AWS.

This will store the main relational data for FlowForm, including forms, questions, responses, and related structured application data.

Using RDS keeps the database managed while avoiding the overhead of self-hosting PostgreSQL in containers.

---

## Authentication

- **Auth0**

- managed outside AWS

### Planned Role

Authentication will not be hosted directly inside AWS.

FlowForm will use Auth0 as the external identity provider for:

- login
- logout
- token issuance
- OpenID Connect identity handling
- refresh token rotation

AWS infrastructure will trust and validate Auth0-issued tokens in the backend API.

---

## DNS and Networking
- **Amazon Route 53** for DNS management
- **CloudFront** for frontend routing and HTTPS
- **Application Load Balancer** for backend API routing and HTTPS
- optional later: custom domain for Auth0 authentication
- AWS Certificate Manager for TLS certificates

### Planned Role
Route 53 will manage the DNS records for the FlowForm domain and route traffic to the appropriate AWS services.

For more detailed DNS and networking plans, see the separate document: [Flow Form — Cloud DNS and Networking Plan](./flow_form_cloud_DNS_and_networking_plan.md)

## Summary High-Level Architecture

FlowForm will follow this basic structure:

- **Frontend:** React SPA hosted on S3 and delivered through CloudFront
- **Backend:** Flask API running in ECS Fargate containers
- **Database:** PostgreSQL hosted in Amazon RDS
- **Authentication:** Auth0 as an external identity provider

This gives FlowForm a clean, modern, and moderately complex cloud foundation that is suitable for learning, scaling, and future expansion.
