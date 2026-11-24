# AI Customer Workflow - Repository Instructions

## 1. Product Context

Build an AI-powered customer workflow platform that manages the complete lead lifecycle:

Lead Capture → Qualification → Email Generation → Approval → Email Communication → Response Classification → Follow-up → CRM Synchronization → Analytics.

The application must be modular, maintainable, secure and scalable.

## 2. Technology Standards

- Python 3.11 or a compatible supported version.
- Streamlit for the user interface.
- PostgreSQL as the shared production database.
- SQLAlchemy ORM and Alembic migrations.
- Pydantic for data validation.
- FastAPI for future API exposure.
- OpenAI API through a provider abstraction.
- Pytest for testing.
- GitHub Actions for CI/CD.
- Streamlit Community Cloud for the initial deployment.

## 3. Architecture Rules

- Follow modular monolith architecture.
- Keep Streamlit presentation separate from business logic.
- Separate AI functionality from workflow orchestration.
- Implement repository and service layers.
- Use dependency injection for external integrations.
- Use abstract interfaces for email and CRM providers.
- Implement Salesforce, HubSpot and Zoho adapters independently.
- Never couple business logic directly to a specific CRM.
- Use configuration-driven business rules.

## 4. AI Rules

- All prompts must be stored in the prompts directory.
- AI outputs must be validated using Pydantic schemas.
- Use structured JSON outputs.
- Never allow AI-generated text to directly execute database changes.
- AI should propose actions; deterministic application services should validate and execute them.
- Log model name, prompt version, execution status and relevant metadata.
- Do not log secrets or unnecessary personal information.
- Handle model timeouts, invalid output and API failures.

## 5. Workflow Rules

- Implement explicit workflow states and valid transitions.
- Persist workflow state in the database.
- Implement idempotency for email and CRM operations.
- Implement retries with exponential backoff.
- Separate transient failures from permanent failures.
- Maintain a complete audit history.
- Prevent duplicate emails and duplicate CRM records.
- Cancel follow-up tasks when a customer responds or unsubscribes.
- Require human approval before external email sending.
- Enforce suppression and consent policies.

## 6. Security Rules

- Never hardcode API keys, passwords or tokens.
- Use Streamlit secrets or environment variables.
- Never commit .env or credentials.
- Enforce user and tenant data isolation.
- Implement role-based permissions.
- Use least-privilege OAuth scopes.
- Validate all user inputs.
- Treat email content and imported lead data as untrusted input.
- Protect against prompt injection.
- Never expose internal prompts, secrets or private customer records to unauthorized users.

## 7. Coding Standards

- Use clear names and type hints.
- Follow PEP 8.
- Write small, reusable functions.
- Avoid unnecessary code duplication.
- Add docstrings to public classes and functions.
- Handle exceptions explicitly.
- Never silently swallow errors.
- Keep dependencies pinned or constrained.
- Avoid unnecessary dependencies.

## 8. Testing Standards

- Add unit tests for every business service.
- Mock external email, CRM and AI integrations.
- Test invalid inputs and error conditions.
- Test workflow transitions.
- Test duplicate lead handling.
- Test email approval and sending restrictions.
- Test CRM synchronization retries.
- Test tenant isolation.
- Run tests before completing a development task.

## 9. Development Instructions

- Follow the approved project architecture.
- Inspect existing code before modifying it.
- Do not overwrite working modules unnecessarily.
- Implement functionality incrementally.
- Do not create placeholder functionality that appears operational.
- Use clearly labelled mock adapters when real credentials are unavailable.
- Update README documentation when functionality changes.
- Report changed files, test results, outstanding issues and setup instructions after each task.

## 10. Deployment

- The application entry point must be app.py.
- Use requirements.txt for dependencies.
- Support Streamlit Community Cloud deployment.
- Keep development, testing and production configurations separate.
- Never require real customer data to run the demo.
- Provide sample data for demonstration.
- Do not claim production readiness without passing security, integration and deployment validation.