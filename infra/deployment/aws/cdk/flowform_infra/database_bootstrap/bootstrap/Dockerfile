FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir --requirement ${LAMBDA_TASK_ROOT}/requirements.txt

COPY . ${LAMBDA_TASK_ROOT}/bootstrap
COPY --from=database_init aws/core_database_v1.sql ${LAMBDA_TASK_ROOT}/bootstrap/sql/
COPY --from=database_init aws/response_database_v1.sql ${LAMBDA_TASK_ROOT}/bootstrap/sql/
COPY --from=database_init aws/roles_v1.sql ${LAMBDA_TASK_ROOT}/bootstrap/sql/
COPY --from=database_init aws/verification_v1.sql ${LAMBDA_TASK_ROOT}/bootstrap/sql/
COPY --from=database_init schema/flowform_core_db_schema_v4.sql ${LAMBDA_TASK_ROOT}/bootstrap/schema/
COPY --from=database_init schema/flowform_response_db_schema_v4.sql ${LAMBDA_TASK_ROOT}/bootstrap/schema/

CMD ["bootstrap.handler.handler"]
