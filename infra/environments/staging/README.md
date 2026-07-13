# Staging environment

Staging owns configuration and topology that differ from production while
exercising the AWS platform. The current AWS adapter reads its deployment values
from `infra/platforms/aws/cdk/.env.staging`; platform orchestration remains in
`infra/platforms/aws/cdk`.
