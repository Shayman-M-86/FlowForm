# Production environment

Production owns configuration and topology that differ from staging. The current
AWS adapter reads its deployment values from `infra/platforms/aws/cdk/.env.prod`;
platform orchestration remains in `infra/platforms/aws/cdk`.
