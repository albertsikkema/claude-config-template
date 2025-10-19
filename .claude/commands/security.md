### Unified Code Review and Security Analysis Prompt for Parallel Execution

Your task is to perform a **comprehensive review of the current codebase** using a structured approach. The review consists of **code quality checks**, **test validations**, **documentation updates**, and an **enterprise-grade security analysis** across 18 critical areas.

Execute the following tasks **in parallel** using specialized subagents and ensure consolidated feedback for each category.

---

### **1. Code Review**

#### Steps:

- **Code Quality**:
  - **Detect project type** by examining files:
    - JavaScript/TypeScript: `package.json`, check for linting/formatting scripts
    - Python: `pyproject.toml`, `setup.py`, check for `black`, `ruff`, `flake8`, `mypy`
    - Go: `go.mod`, check for `golangci-lint`, `gofmt`
    - Rust: `Cargo.toml`, check for `rustfmt`, `clippy`
    - Java: `pom.xml`, `build.gradle`, check for `checkstyle`, `spotless`
    - Other: Look for common linting/formatting tools in CI configuration
  - **Run appropriate quality checks**:
    - Execute detected formatters and linters (e.g., `npm run lint`, `black .`, `gofmt`, `cargo fmt`)
    - Use the `code-reviewer` agent to analyze code quality and adherence to best practices
- **Tests**:
  - **Detect test framework** and run appropriate commands:
    - JavaScript/TypeScript: `npm test`, `jest`, `vitest`, `mocha`
    - Python: `pytest`, `unittest`, `tox`
    - Go: `go test ./...`
    - Rust: `cargo test`
    - Java: `mvn test`, `gradle test`
  - **Validate test coverage**:
    - Check for tests covering recent changes
    - Verify test organization (unit, integration, e2e)
    - Run coverage reports if available
- **Documentation**:
  - Check if `README.md` reflects changes (including configuration, environment variables, setup instructions)
  - Ensure `CLAUDE.md` includes relevant information for updates
  - Verify inline code documentation (docstrings, JSDoc, etc.)
- **API Documentation**:
  - Check for API documentation in common formats:
    - OpenAPI/Swagger specifications
    - API client collections (Bruno, Postman, Insomnia)
    - Generated API docs (Sphinx, JSDoc, GoDoc, etc.)
  - Verify new endpoints/functions are documented
  - Confirm examples and test cases exist

---

### **2. Security Analysis**

#### Methodology:

Conduct a thorough security assessment using a **4-phase approach** informed by framework discovery.

##### **Phase 0: Framework Discovery and Research**

- **Detect technology stack** by examining project files:
  - JavaScript/TypeScript: `package.json` dependencies (frameworks, auth libraries, ORMs)
  - Python: `requirements.txt`, `pyproject.toml`, `Pipfile` (Django, Flask, FastAPI, SQLAlchemy, etc.)
  - Go: `go.mod` (Gin, Echo, GORM, etc.)
  - Rust: `Cargo.toml` (Actix, Rocket, Diesel, etc.)
  - Java: `pom.xml`, `build.gradle` (Spring, Hibernate, etc.)
- Examine project structure to understand architectural patterns (MVC, microservices, monolith, etc.)
- Research security best practices for identified frameworks and languages
- Create a framework-specific and language-specific security checklist

##### **Phase 1: Critical Security Areas (6 areas)**

Analyze foundational security controls:

1. **Data Isolation & Access Control**:
   - Multi-tenant data isolation (if applicable)
   - Database-level access controls
   - Row-level security patterns
2. **Input Validation & Injection Prevention**:
   - SQL injection protection (parameterized queries, ORM usage)
   - Command injection prevention
   - Path traversal protection
   - Language-specific injection risks (LDAP, XML, etc.)
3. **Authentication & Session Security**:
   - Password hashing (bcrypt, Argon2, PBKDF2)
   - Session management and token security
   - JWT/OAuth implementation security
   - MFA/2FA implementation
4. **Cross-Site Scripting (XSS) Prevention**:
   - Output encoding and sanitization
   - Content Security Policy (CSP)
   - Framework-specific XSS protections
5. **File Upload & Storage Security**:
   - File type validation and content scanning
   - Secure file storage patterns
   - Path traversal protection
   - Image/media processing security
6. **Environment & Secrets Management**:
   - Environment variable handling
   - API key and credential storage
   - Secrets management integration (Vault, AWS Secrets Manager, etc.)
   - Configuration file security

##### **Phase 2: Security Configuration (6 areas)**

Review middleware, access controls, and infrastructure patterns:

1. **Rate Limiting & DoS Protection**:
   - Request rate limiting implementation
   - Brute force protection
   - Resource exhaustion prevention
   - Framework-specific middleware (e.g., express-rate-limit, slowapi, etc.)
2. **CSRF Protection**:
   - CSRF token implementation
   - SameSite cookie attributes
   - Framework default protections
   - API CSRF considerations
3. **Authorization & RBAC**:
   - Role-based access control patterns
   - Permission checking mechanisms
   - Attribute-based access control (ABAC) if used
   - Policy enforcement points
4. **Database Security**:
   - Connection security (SSL/TLS)
   - Credential management
   - Query logging and monitoring
   - Backup encryption
   - Database user permissions
5. **Logging & Privacy Protection**:
   - Sensitive data in logs (PII, credentials, tokens)
   - Log injection prevention
   - Audit logging for security events
   - Log retention and access controls
6. **Third-Party Integration Security**:
   - Dependency vulnerability scanning
   - API key security for external services
   - Webhook signature verification
   - OAuth/SAML integration security

##### **Phase 3: Implementation Security Patterns (6 areas)**

Examine architectural and coding security:

1. **Secure Coding Patterns**:
   - Memory safety (buffer overflows, null pointer dereferences)
   - Integer overflow/underflow prevention
   - Race conditions and concurrency issues
   - Type confusion vulnerabilities
   - Language-specific secure coding practices
2. **Error Handling & Information Disclosure**:
   - Stack traces in production
   - Error message information leakage
   - Proper exception handling
   - Graceful degradation
   - Debug mode detection
3. **API Security Patterns**:
   - Input validation on all endpoints
   - Output encoding
   - HTTP security headers (HSTS, X-Frame-Options, X-Content-Type-Options, etc.)
   - API versioning and deprecation
   - GraphQL/REST-specific security
4. **Frontend Security Controls** (if applicable):
   - Client-side input validation (complementing server-side)
   - Secure storage (localStorage, sessionStorage, cookies)
   - Third-party script integrity (SRI)
   - DOM-based XSS prevention
5. **Dependency Security**:
   - Outdated dependencies and known vulnerabilities
   - Dependency scanning tools (Dependabot, Snyk, npm audit, cargo audit, etc.)
   - License compliance
   - Supply chain security
6. **Performance & Resource Security**:
   - Algorithmic complexity attacks
   - Memory leaks
   - Resource cleanup
   - Timeout configurations
   - Connection pooling security

#### For Each Security Area:

- Assess current implementation and framework-specific features
- Identify vulnerabilities and risk levels (CRITICAL | HIGH | MEDIUM | LOW)
- Include evidence with code examples and file locations (file:line format)
- Provide actionable recommendations aligned with framework and language best practices
- Reference relevant security standards (OWASP Top 10, CWE, language-specific guidelines)

---

### Deliverables

#### **Comprehensive Review Report**:

Save consolidated findings to `thoughts/shared/reviews/security-analysis-YYYY-MM-DD.md` with the following structure:

1. **Executive Summary**:
   - Technology stack overview (languages, frameworks, key dependencies)
   - Code quality overview
   - Security rating (EXCELLENT | GOOD | NEEDS IMPROVEMENT | POOR)
   - Key findings and actionable recommendations
   - Production readiness determination
2. **Code Review Results**:
   - Formatting/linting results (language-specific tools)
   - Automated test results and coverage metrics
   - Documentation completeness assessment
   - API documentation feedback
3. **Security Analysis Findings**:
   - **Framework Discovery Summary**:
     - Stack identification (languages, frameworks, libraries)
     - Built-in security features detected
     - Security tools and configurations in use
   - **Detailed Phase 1-3 Findings**:
     - For each of 18 security areas, include:
       - Current state assessment
       - Vulnerabilities identified with evidence (file:line references)
       - Risk level (CRITICAL | HIGH | MEDIUM | LOW)
       - Code examples demonstrating issues
   - **Risk Assessment Matrix**:
     - Summary of findings by risk level
     - Attack surface analysis
   - **Compliance Readiness**:
     - OWASP Top 10 coverage
     - GDPR/privacy considerations (if applicable)
     - Industry-specific compliance (SOC 2, HIPAA, PCI-DSS, etc.)
4. **Recommendations**:
   - **Immediate Actions** (CRITICAL/HIGH priority)
   - **Short-term Improvements** (MEDIUM priority)
   - **Long-term Hardening** (LOW priority, best practices)
   - Implementation steps tailored to detected framework/language
   - Security improvement roadmap with estimated effort
   - Tool recommendations (SAST, DAST, dependency scanners, etc.)

---

### Execution

#### Subagent Usage:

Launch parallel subagents for comprehensive analysis:

1. **Code Quality Subagent**:
   - Detect project type and available tooling
   - Execute appropriate formatting and linting commands
   - Run test suites with coverage analysis
   - Validate test organization and completeness

2. **Documentation Subagent**:
   - Review README.md for setup instructions and configuration
   - Check CLAUDE.md for project-specific patterns
   - Verify inline documentation (docstrings, comments, type hints)
   - Assess API documentation completeness

3. **Security Analysis Subagents** (run in parallel after Phase 0):
   - **Phase 0 Subagent** (Foundation):
     - Detect technology stack (language, framework, dependencies)
     - Identify architectural patterns
     - Research framework/language-specific security best practices
     - Create customized security checklist
     - Identify existing security tools and configurations

   - **Phase 1 Subagent** (Critical Areas):
     - Analyze 6 critical security areas using Phase 0 research
     - Focus on authentication, data protection, injection prevention
     - Identify high-risk vulnerabilities

   - **Phase 2 Subagent** (Configuration):
     - Evaluate 6 security configuration areas
     - Review middleware, rate limiting, CSRF, authorization
     - Assess database and logging security

   - **Phase 3 Subagent** (Implementation):
     - Examine 6 implementation security patterns
     - Review coding practices, error handling, API security
     - Analyze dependency and resource security

**Execution Flow**:
1. Launch Code Quality and Documentation subagents immediately
2. Launch Phase 0 subagent for framework discovery
3. Once Phase 0 completes, launch Phase 1-3 subagents in parallel
4. Consolidate all findings into comprehensive report

**Consolidation**:
Merge outputs from all subagents into the final report structure, including:
- Technology stack summary
- Code quality metrics
- All 18 security areas analyzed with evidence
- Risk assessment matrix
- Prioritized recommendations
- Production readiness evaluation

---

### Success Criteria

The task is complete when:

- **Code Quality**: Formatting/linting executed, tests run with coverage analysis
- **Documentation**: README.md, CLAUDE.md, and API docs reviewed for completeness
- **Security Analysis**: All 18 security areas analyzed with evidence and risk levels
- **Technology Alignment**: Recommendations specific to detected framework and language
- **Deliverable**: Comprehensive report saved to `thoughts/shared/reviews/security-analysis-YYYY-MM-DD.md`
- **Actionability**: Prioritized recommendations with implementation guidance
- **Production Readiness**: Clear determination with supporting evidence

---

### Getting Started

1. **Immediate Actions**:
   - Launch Code Quality and Documentation subagents in parallel
   - Launch Phase 0 (Framework Discovery) subagent

2. **After Phase 0 Completes**:
   - Launch Phase 1-3 security analysis subagents in parallel
   - Each subagent should use findings from Phase 0 for context

3. **Consolidation**:
   - Merge all subagent outputs into structured report
   - Ensure `thoughts/shared/reviews/` directory exists (create if needed)
   - Save report with current date: `security-analysis-YYYY-MM-DD.md`

4. **Review & Feedback**:
   - Present executive summary to user
   - Highlight CRITICAL and HIGH priority findings
   - Provide clear next steps for remediation
