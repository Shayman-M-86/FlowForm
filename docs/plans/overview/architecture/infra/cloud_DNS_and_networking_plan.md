# Flow Form — Cloud DNS and Networking Plan


## DNS and Networking

### Domain Structure
FlowForm will use a primary domain with separate subdomains for the frontend and backend services.

Planned structure:

- **flowform.com** → frontend application
- **api.flowform.com** → backend API
- *(optional later)* **auth.flowform.com** → Auth0 custom authentication domain

### DNS Management
DNS will be managed using **Amazon Route 53**.

Route 53 records will route traffic to the appropriate AWS services using alias records.

### Frontend Routing

Frontend requests will follow this path:

Browser → Route 53 → CloudFront → S3

- The React SPA will be stored as static build files in **Amazon S3**.
- **CloudFront** will act as the global CDN and HTTPS entry point.
- CloudFront will cache static assets and deliver them through edge locations for faster performance.

### Backend Routing

API requests will follow this path:

Browser → Route 53 → Application Load Balancer → ECS Fargate

- The backend Flask API will run inside containers on **ECS Fargate**.
- An **Application Load Balancer (ALB)** will expose the API publicly.
- The ALB will route traffic to the ECS service tasks running the API.

### HTTPS and Certificates

HTTPS will be used for both frontend and backend endpoints.

- **AWS Certificate Manager (ACM)** will provide TLS certificates.
- CloudFront will terminate HTTPS for the frontend.
- The Application Load Balancer will terminate HTTPS for the backend API.

### Authentication Routing

Authentication will be handled externally by **Auth0**.

The application will redirect users to Auth0 for login and token issuance. After authentication, users are redirected back to the frontend application.

If a custom domain is used for Auth0 in the future, it may be configured as:

- **auth.flowform.com** → Auth0 tenant

