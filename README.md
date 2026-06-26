# Book App — AWS CDK CRUD API

A serverless CRUD API for managing books, built with AWS CDK (Python).

## Architecture

```
Client → API Gateway (REST /v1) → Lambda (per endpoint) → DynamoDB
                    ↕
             Cognito User Pool (JWT auth)
```

**Services:**
- **API Gateway** — REST API, `/v1` stage, Cognito JWT authorisation
- **AWS Lambda** — Python 3.12, one function per endpoint for minimal IAM
- **DynamoDB** — `isbn` as partition key, PAY_PER_REQUEST billing
- **Cognito User Pools** — `admin` and `reader` groups

## Prerequisites

- Python 3.12
- Node.js 22 (CDK CLI)
- AWS CLI configured (`aws configure`)
- Docker (for Lambda bundling during deploy)

```bash
npm install -g aws-cdk
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

## Deployment

Bootstrap your AWS account once (first time only):

```bash
cdk bootstrap aws://ACCOUNT_ID/REGION
```

Deploy:

```bash
make deploy          # deploys to dev
make deploy ENV=prod # deploys to prod
```

After deploy, stack outputs print the API URL, User Pool ID, and Client ID.

## User Management

The scripts in `scripts/` fetch the Cognito User Pool ID and Client ID automatically
from the CloudFormation stack outputs. If the stack is not reachable, they fall back
to prompting for the values manually.

**Create a user** (interactive — prompts for email, password, and role):

```bash
make create-user          # targets dev
ENV=prod make create-user # targets prod
```

**Get a JWT token** (interactive — prompts for email and password):

```bash
make login          # targets dev
ENV=prod make login # targets prod
```


The `IdToken` printed at the end is used as the `Authorization` header value for API requests.

## Running Tests

```bash
make test   # unit + CDK assertion tests
make lint   # ruff check + format check
```

## API Usage

The full API specification is available in [`docs/openapi.yaml`](docs/openapi.yaml).
Import it into Postman via **Import → File** alongside [`docs/postman_environment.json`](docs/postman_environment.json).

Base URL: `https://{api-id}.execute-api.{region}.amazonaws.com/v1`

All write operations require `Authorization: {IdToken}` (Cognito JWT from `make login`).
Read operations (`GET`) are public.

### Create a book (admin only)

```bash
curl -X POST {BASE_URL}/books \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "978-0-06-112008-4",
    "name": "To Kill a Mockingbird",
    "authors": ["Harper Lee"],
    "languages": ["EN"],
    "countries": ["US"],
    "numberOfPages": 281,
    "releaseDate": "1960-07-11"
  }'
```

### Create multiple books (admin only, max 10 per request)

```bash
curl -X POST {BASE_URL}/books/batch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"books": [{...}, {...}]}'
```

Returns `201` if all created, `207 Multi-Status` if partial failure.

### Query books (public)

```bash
# All books
curl {BASE_URL}/books

# Filter by language (ISO 639-1)
curl "{BASE_URL}/books?languages=EN"

# Filter by multiple languages (OR logic)
curl "{BASE_URL}/books?languages=EN,FR"

# Filter by language AND country
curl "{BASE_URL}/books?languages=EN&countries=US"

# Pagination
curl "{BASE_URL}/books?limit=10&nextToken={token}"
```

Supported filter fields: `isbn`, `name`, `authors`, `languages`, `countries`, `releaseDate`.

### Get a book (public)

```bash
curl {BASE_URL}/books/978-0-06-112008-4
```

### Update a book (admin only)

`isbn` is immutable and ignored if included in the body.

```bash
curl -X PUT {BASE_URL}/books/978-0-06-112008-4 \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"numberOfPages": 300}'
```

### Delete a book (admin only)

```bash
curl -X DELETE {BASE_URL}/books/978-0-06-112008-4 \
  -H "Authorization: $TOKEN"
```

## Design Decisions & Assumptions

### Role-based access
Not all operations are available to all users. Admins manage the catalog (full CRUD); readers can only browse (`GET`). Enforced via Cognito groups (`admin`, `reader`) and a service-layer role check. The `Authorization` header carries the Cognito `IdToken` directly — no `Bearer` prefix, as required by `CognitoUserPoolsAuthorizer`.

### isbn is immutable
ISBN is the globally unique book identifier. Once set it cannot be changed. Update requests strip `isbn` from the payload before validation; a `PUT` to a non-existent ISBN returns `404`.

### Languages and countries use ISO codes
`languages` accepts ISO 639-1 codes (`EN`, `FR`), `countries` accepts ISO 3166-1 alpha-2 codes (`US`, `GB`). Values are normalised to uppercase on ingestion so `en`, `En`, and `EN` are all stored as `EN`, ensuring consistent filtering.

### Filtering uses Scan + FilterExpression
All filter fields use DynamoDB Scan with a `FilterExpression`. This correctly handles multi-value list attributes — `?languages=EN` finds books where `EN` appears anywhere in the `languages` list. A GSI-based approach was evaluated but rejected because DynamoDB list attributes cannot be GSI keys.

Multiple values on the same field use OR logic; values across different fields use AND:
- `?languages=EN,FR` → books with EN **or** FR
- `?languages=EN&countries=US` → books with EN language **and** US country

### API versioning
All endpoints are under `/v1`. A future breaking change deploys as `/v2` without disrupting existing clients.

### DynamoDB billing — PAY_PER_REQUEST vs PROVISIONED

The table uses `PAY_PER_REQUEST` billing. Here is the reasoning:

In `PROVISIONED` mode, 1 WCU = 1 write/second for items ≤ 1KB. The batch endpoint processes books sequentially (1 DynamoDB write at a time per Lambda invocation), so 1 request to the batch endpoint having 10 books will consume at most 10 WCU simultaneously.

However, in a spike scenario — for example, 10 clients simultaneously calling `POST /books/batch` with 10 books each, all completing within the same second — up to 100 WCU could be consumed.

`PAY_PER_REQUEST` eliminates this entirely: DynamoDB scales instantly to absorb any burst with no throttling and no upfront capacity planning. At this stage of the application, where traffic patterns are unknown and spikes are likely, PAY_PER_REQUEST is the correct default.

**When to revisit:** once traffic is predictable and sustained, switching to PROVISIONED with auto-scaling (already modelled in `BookAppDynamodbTable`) reduces cost significantly at high throughput.

## Next Steps

### Custom domain for the API
Currently the API is exposed via the default API Gateway URL (`https://{id}.execute-api.{region}.amazonaws.com/v1`). A production deployment should use a custom domain (e.g. `api.bookapp.com/v1`) via:
- **AWS Certificate Manager** — provision a TLS certificate for the domain
- **API Gateway custom domain** — map the domain to the API Gateway stage
- **Route 53** — create an alias record pointing to the API Gateway domain

This can be added as a CDK construct in `BookAppStack` using `apigw.DomainName` and `route53.ARecord`.

### CI/CD pipeline
We should add a GitHub Actions workflow that will run on every pull request to enforce code quality before merge. This ensures linting, unit tests, integration tests, and CDK synthesis all pass before any code reaches `main`.
