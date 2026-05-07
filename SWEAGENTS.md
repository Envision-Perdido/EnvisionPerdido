# AI Coding Agent Instructions: CEN3031 Software Engineering Principles

This file tells an AI coding agent how to work in this repository while following the Software Engineering 1 principles from CEN3031. Treat these instructions as project rules unless a human maintainer gives a more specific instruction.

The goal is not just to make code that works once. The goal is to make code that can be understood, tested, changed, maintained, secured, and deployed over time.

---

## 1. Core Operating Rule

When asked to make a change, follow this loop:

1. Understand the problem, domain, current program structure, and technology stack.
2. Identify the smallest safe change that satisfies the requirement.
3. Check existing tests and add or update tests when behavior changes.
4. Implement in small, focused steps.
5. Refactor only enough to reduce complexity and improve maintainability.
6. Verify the change with tests, static checks, or manual reasoning when tests are unavailable.
7. Document only what needs to be remembered by future maintainers.
8. Summarize what changed, why it changed, what was tested, and any remaining risk.

Do not make broad rewrites, speculative redesigns, or “big bang” refactors unless the human explicitly asks for them.

---

## 2. Software Engineering Mindset

Software engineering is programming integrated over time. Optimize for long-term maintainability, not just short-term output.

Prefer code that is:

- Easy to read.
- Easy to test.
- Easy to debug.
- Easy to change.
- Safe under failure.
- Secure by design.
- Documented just enough for future work.

Avoid clever, fragile, overly abstract, or unnecessarily impressive solutions. A simple design that satisfies the requirement is better than a complex design that might be useful someday.

Remember the “No Silver Bullet” idea: no single tool, framework, design pattern, or AI-generated solution removes the essential difficulty of understanding the problem, making trade-offs, and maintaining the system over time.

---

## 3. Requirements and User Stories

Before coding, identify the requirement being satisfied.

When creating or updating feature work, prefer this structure:

```md
## User Story
As a [user role], I want [feature/action], so that [benefit/value].

## Acceptance Criteria
- [ ] Given [starting condition], when [action], then [expected result].
- [ ] Edge cases are handled.
- [ ] Security/privacy requirements are met.
- [ ] Tests are added or updated.
```

Use INVEST when evaluating user stories:

- Independent
- Negotiable
- Valuable
- Estimable
- Small
- Testable

Use MoSCoW when prioritizing:

- Must Have
- Should Have
- Could Have
- Won’t Have

If acceptance criteria are unclear, infer reasonable criteria from the request and state the assumption in the final summary.

---

## 4. Agile and Sprint-Friendly Work

Prefer small-batch development.

A good agent change should usually be:

- Focused on one feature, bug, or refactor.
- Small enough to review.
- Easy to explain in a pull request.
- Safe to merge without surprising unrelated changes.

Do not keep adding extra features during implementation. If you discover additional useful work, list it as follow-up work instead of silently expanding scope.

For incomplete work, leave clear notes about what remains and how to continue.

---

## 5. Git and Version-Control Discipline

Assume Git is the source of truth for project history.

When preparing a change:

- Do not rewrite unrelated files.
- Do not reformat large files unless formatting is the requested task.
- Do not delete code unless it is clearly unused, replaced, or requested.
- Keep changes reviewable and logically grouped.
- Avoid generated noise in diffs.

When giving a final summary, include:

```md
## Summary
- What changed
- Why it changed

## Tests / Verification
- Tests run
- Manual checks performed
- Tests not run and why

## Risks / Follow-up
- Remaining risks
- Suggested follow-up work
```

---

## 6. Reliable Programming

Programming errors often come from misunderstanding one of three things:

1. The problem or application domain.
2. The program and how the code works together.
3. The technology stack.

Before editing, inspect enough of the existing code to avoid these misunderstandings.

### Complexity Rule

More complexity means more opportunities for faults. Reduce complexity whenever it helps the current task.

Prefer:

- Small functions.
- Focused classes.
- Clear data flow.
- Explicit names.
- Guard clauses over deep nesting.
- Composition over deep inheritance.
- Simple interfaces.

Avoid:

- Deeply nested conditionals.
- Long functions doing multiple jobs.
- Classes that know too much.
- Hidden side effects.
- Excessive shared mutable state.
- New abstractions that are not needed yet.

---

## 7. Cohesion and Coupling

Design for high cohesion and low coupling.

### High Cohesion

A module, class, or function should contain related things that serve a common purpose.

Good sign:

- The file/class/function has one clear reason to exist.

Bad signs:

- A class handles unrelated concerns.
- A function mixes calculation, database writes, logging, formatting, and user interaction.
- A file is a random collection of unrelated helpers.

### Low Coupling

A module should depend on as few other modules as reasonably possible.

Good sign:

- A change in one part of the system does not force many unrelated changes elsewhere.

Bad signs:

- One object directly controls many unrelated objects.
- Low-level modules depend on high-level UI or application code.
- Tests require constructing the entire application to test one small behavior.

When reducing coupling, prefer dependency injection, interfaces, clear boundaries, and stable public APIs.

---

## 8. Single Responsibility Principle

Follow the Single Responsibility Principle:

> A class or module should have one reason to change.

Group together things that change for the same reason. Separate things that change for different reasons.

Examples:

- Inventory logic and inventory report formatting should be separate.
- Authentication logic and UI rendering should be separate.
- Database access and business rules should usually be separate.
- Validation and persistence should be clearly separated unless the project structure says otherwise.

Before adding a method to a class, ask:

- Does this belong to this class’s core responsibility?
- Would this create a second reason for the class to change?
- Should this be a separate service, helper, component, or module?

---

## 9. Refactoring Rules

Refactoring means improving internal structure without changing external behavior.

Refactor when:

- Code smells block the requested change.
- Duplicate logic causes risk.
- A function or class has multiple responsibilities.
- Existing abstractions no longer fit.
- A small cleanup makes the requested change safer.

Do not refactor just to show off or because a different style is personally preferred.

### Safe Refactoring Procedure

1. Identify the smallest behavior-preserving improvement.
2. Make one small change.
3. Run relevant tests or perform a clear verification step.
4. Repeat only if it directly supports the task.
5. Stop before the refactor becomes a rewrite.

Never do big-bang refactoring unless explicitly requested.

Common acceptable refactors:

- Extract function.
- Extract class.
- Rename unclear variables.
- Replace deep nesting with guard clauses.
- Remove duplicated logic.
- Remove dead code when clearly safe.
- Move changing logic behind a clear interface.

---

## 10. Code Smells to Detect and Fix

Watch for these code smells:

- Large class: likely violates single responsibility.
- Long method/function: likely does more than one thing.
- Duplicated code: violates DRY.
- Meaningless names: hides intent.
- Unused code: creates confusion.
- Spaghetti code: random organization and hard-to-follow control flow.
- Golden hammer: using one familiar tool/pattern for every problem.
- Boat anchor/dead code: keeping unused code because it might be needed later.
- God object/God class: one object has too many responsibilities or dependencies.
- Copy-paste programming: copied code without understanding.

When fixing a smell, keep the fix proportional to the task. Do not redesign the whole project for one smell.

---

## 11. Design Patterns

A design pattern is a repeatable solution to a common recurring design problem.

Use design patterns only when:

- The problem matches the pattern.
- The pattern makes the code easier to understand or maintain.
- The added structure is worth the complexity.

Do not force patterns into simple code.

Useful pattern guidance:

- Observer is useful when one object changes state and multiple dependents must be notified.
- Factory-style creation can be useful when object creation is complex or varies by type.
- Strategy-style design can be useful when interchangeable behaviors should be selected without huge conditionals.

If using a pattern, name it in comments or documentation only when doing so helps future maintainers understand the design.

---

## 12. Reducing Complexity

### Structural Complexity

Reduce by:

- Keeping functions small.
- Avoiding unnecessary side effects.
- Avoiding deep inheritance chains.
- Keeping modules focused.
- Using guard clauses to reduce nesting.

### Data Complexity

Reduce by:

- Using clear data structures.
- Avoiding confusing aliases to mutable data.
- Keeping transformations explicit.
- Validating data at boundaries.
- Avoiding global mutable state when possible.

### Decision Complexity

Reduce by:

- Simplifying conditionals.
- Replacing repeated decision logic with named helper functions.
- Using guard clauses for invalid cases.
- Avoiding giant boolean expressions.
- Keeping business rules readable.

---

## 13. Architecture Principles

Architecture affects non-functional attributes such as:

- Performance.
- Reliability.
- Availability.
- Security.
- Usability.
- Maintainability.
- Resilience.

Architectural decisions involve trade-offs. Do not optimize one quality while ignoring the others.

### Design Guidelines

Follow these guidelines:

- Localize relationships.
- Group related things together.
- Reduce shared dependencies.
- Separate concerns.
- Implement once; do not duplicate functionality.
- Keep interfaces stable.
- Do not break legacy users unless explicitly required.
- Make new interface changes optional when possible.
- In layered designs, lower layers should not depend on higher layers.
- Do not make components rely on the implementation details of other components.

### YAGNI and Simplicity

Use YAGNI: You Aren’t Gonna Need It.

Do not build features, abstractions, services, or configuration systems for imagined future requirements. Wait until there is an actual need.

Use DTSTTCPW: Do The Simplest Thing That Could Possibly Work.

Prefer rough design up front and iterative improvement over either no design or excessive big design up front.

---

## 14. MVC and Layering

When the project uses MVC or a similar pattern, preserve the separation:

- Model: data and business/domain logic.
- View: user-facing presentation.
- Controller: handles user requests and coordinates models/views.

Do not put business logic in views.
Do not put database details in views.
Do not put unrelated UI concerns into models.

For web/client-server systems:

- Keep API contracts clear.
- Treat JSON/data transfer formats as interfaces.
- Validate data entering the server.
- Keep server-side authorization checks even if the client hides UI actions.

---

## 15. Testing Rules

Testing is part of development, not something added only at the end.

Use the testing pyramid:

1. Unit tests for small pieces of logic.
2. Integration tests for multiple units working together.
3. End-to-end tests for full workflows when needed.

As tests move up the pyramid, they usually become slower, more fragile, and more expensive to maintain.

### Arrange, Act, Assert

Structure tests as:

```python
# Arrange
setup_data = ...

# Act
result = function_under_test(setup_data)

# Assert
assert result == expected_result
```

### TDD When Practical

Use Red, Green, Refactor when appropriate:

1. Red: write a failing test.
2. Green: write just enough code to pass.
3. Refactor: improve the code while tests still pass.

### What to Test

Add or update tests for:

- New behavior.
- Bug fixes.
- Edge cases.
- Validation rules.
- Authorization rules.
- Failure handling.
- Regressions discovered during debugging.

If tests are not available or cannot be run, state that clearly and explain what manual verification was performed.

---

## 16. Security and Privacy by Design

Security must be built in, not added after the product is finished.

Follow these principles:

- Never trust the user.
- Never trust input.
- Client-side validation is never enough.
- Validate input on both client and server when both exist.
- Prefer passlists over blocklists when practical.
- Sanitize and parameterize external input.
- Use parameterized queries for database access.
- Apply least privilege.
- Use defense in depth.
- Do not rely on a single security check.
- Encrypt sensitive data in transit and at rest when applicable.
- Never commit secrets, credentials, tokens, private keys, or real production data.
- Do not assume authenticated users are authorized for every action.

### Authentication vs. Authorization

Authentication answers:

> Who are you?

Authorization answers:

> What are you allowed to access or change?

Check authorization at every relevant server/API entry point.

### Logging and Auditing

When security matters, preserve useful audit trails:

- Who accessed what?
- Who changed what?
- When did the action happen?
- Was access denied?
- What account/IP/request context was involved?

Do not log sensitive secrets or private data unnecessarily.

### Privacy

Protect privacy by:

- Collecting only needed data.
- Anonymizing data when possible.
- Encrypting sensitive data.
- Creating retention/deletion rules.
- Avoiding unnecessary personal data in logs.

Security does not automatically solve privacy. Treat them as related but separate concerns.

---

## 17. Input Validation

Any user-controlled input can cause:

- Database pollution.
- Program instability.
- Malicious attacks.

For every new input field, endpoint, parser, file upload, CLI argument, or imported data source, decide:

- What type is valid?
- What range is valid?
- What format is valid?
- What values are forbidden?
- What should happen when input is invalid?

Prefer passlisting known-good input over blocking known-bad input.

Examples:

- Ages cannot be negative.
- Counts that represent people/items usually cannot be fractional.
- Emails, phone numbers, ZIP codes, and IDs should have explicit format rules.
- Uploaded files should be checked for type, size, and safe handling.

---

## 18. Failure Management and Defensive Coding

Assume failures will happen.

Design code to fail safely:

- Persistent data should not be lost or corrupted.
- Users should be able to recover work when possible.
- The app should not hang indefinitely.
- The app should not expose confidential data during failure.
- Failed database operations should roll back when needed.
- Errors should be logged with useful context.
- User-facing error messages should be safe and understandable.

Do not hide exceptions silently.

Bad:

```python
try:
    save_data()
except Exception:
    pass
```

Better:

```python
try:
    save_data()
except DatabaseError as error:
    rollback_transaction()
    log_error(error)
    show_safe_error_message()
```

Only catch exceptions you can handle meaningfully. If you catch a broad exception, explain why and preserve diagnostic information.

---

## 19. Documentation and Clean Code

The purpose of documentation is communication, not paperwork.

Document stable things, not speculative things.

Use documentation for:

- Requirements.
- Design decisions.
- Public APIs.
- Setup and deployment instructions.
- Non-obvious behavior.
- Warnings about consequences.
- Legal or policy requirements.
- Organizational memory.

Avoid documentation that is:

- Redundant.
- Misleading.
- Out of date.
- A journal of changes that belongs in Git.
- A substitute for cleaning up messy code.

### Comments

Good comments explain why, intent, warnings, or constraints.

Bad comments merely repeat what the code says.

Prefer self-documenting code with meaningful names:

Bad:

```java
int d;
```

Better:

```java
int elapsedTimeInDays;
int daysSinceCreation;
int fileAgeInDays;
```

Use TODO comments only for temporary coding notes. Remove them or convert them into tracked issues before finalizing work.

---

## 20. DevOps, Deployment, and Maintenance

DevOps balances change and stability.

Developers want change:

- New features.
- Bug fixes.
- Improvements.

Operations wants stability:

- Uptime.
- Reliability.
- Predictable deployments.

Support both by keeping changes small, tested, automated, and observable.

### DevOps Principles

Follow these:

- Everyone is responsible.
- Automate everything that can reasonably be automated.
- Measure first; change later.
- Use data to guide improvements.
- Prefer small releases over huge risky releases.
- Keep Git at the core of collaboration and automation.

### CI, Delivery, and Deployment

Continuous Integration:

- Merge changes frequently.
- Use pull requests and review.
- Run automated builds and tests.
- Notify the team when builds/tests fail.

Continuous Delivery:

- Automatically prepare tested code for release.
- Keep a deployment-ready artifact available.
- A human may still choose when to release.

Continuous Deployment:

- Automatically deploy passing changes to production.
- Requires strong tests, monitoring, and rollback confidence.

### Continuous Delivery Principles

Prefer:

- Repeatable, reliable processes.
- Automation.
- Version control for everything.
- Built-in quality.
- Doing the hardest parts first.
- Shared responsibility.
- “Done” meaning released or release-ready.
- Continuous improvement.

### Maintenance

Maintain software by:

- Having a longevity plan.
- Not procrastinating known problems.
- Keeping dependencies updated.
- Performing routine health checks.
- Monitoring logs, usage, security, and performance.
- Preventing invisible failures.

---

## 21. Technical Debt

Technical debt is the future cost created by taking shortcuts now.

Some debt can be acceptable when intentional, limited, and repaid quickly. Ignored debt becomes expensive through bugs, slow development, fragile code, and confusing design.

Repay technical debt by:

- Refactoring complex code.
- Adding missing tests.
- Removing dead code.
- Updating dependencies.
- Improving documentation.
- Simplifying architecture.
- Fixing known bugs.
- Replacing temporary hacks with stable solutions.

When adding a shortcut, label it clearly as temporary and propose how it should be repaid.

---

## 22. Ethics

Technology affects real people. Consider ethical impact before implementing features.

Use three ethical lenses:

### Consequence / Utilitarian Lens

Ask:

> What action produces the most good and least harm?

Consider users, maintainers, customers, future developers, and affected third parties.

### Duty Lens

Ask:

> What obligations, rights, promises, laws, or policies must be respected?

Do not violate user trust, privacy promises, accessibility requirements, or security expectations for convenience.

### Virtue Lens

Ask:

> What would a responsible, honest, careful engineer do?

Be transparent about risks, limitations, and uncertainty.

### Ethical Stop Conditions

Pause and clearly flag the issue if a requested change would:

- Mislead users.
- Hide important risk.
- Weaken privacy or security without justification.
- Expose sensitive data.
- Bypass authorization.
- Make harmful behavior easier.
- Violate project policy, law, or user consent.

Suggest a safer alternative when possible.

---

## 23. Agent Definition of Done

A task is not done until these are satisfied or explicitly marked not applicable:

- [ ] Requirement/user story is understood.
- [ ] Acceptance criteria are satisfied.
- [ ] Change is small and focused.
- [ ] Code has high cohesion and low coupling.
- [ ] Single Responsibility Principle is respected.
- [ ] No unnecessary design pattern or overengineering was added.
- [ ] Relevant code smells were avoided or reduced.
- [ ] Inputs are validated at appropriate boundaries.
- [ ] Authentication and authorization rules are preserved or improved.
- [ ] Privacy-sensitive data is protected.
- [ ] Failure cases are handled safely.
- [ ] Tests were added/updated or a reason is given.
- [ ] Existing tests/checks were run when possible.
- [ ] Documentation was updated if future maintainers need it.
- [ ] No secrets, tokens, credentials, or real private data were committed.
- [ ] Final summary includes changes, tests, risks, and follow-up.

---

## 24. Pull Request / Final Response Template

Use this format when summarizing work:

```md
## Summary
- [Concise bullet of what changed]
- [Concise bullet of why it changed]

## SWE Principles Applied
- Cohesion/coupling: [how the change preserved or improved design]
- SRP/refactoring: [what was separated, simplified, or left alone]
- Testing: [what was tested]
- Security/privacy: [what was validated/protected]
- Documentation: [what was documented or why docs were not needed]

## Tests / Verification
- [Command run or manual check]
- [Result]

## Risks / Follow-up
- [Known limitation]
- [Recommended next step]
```

---

## 25. Default Behavior When Unsure

If the best approach is unclear:

1. Prefer the smallest safe change.
2. Preserve existing behavior.
3. Do not invent unrelated requirements.
4. Make assumptions explicit.
5. Leave follow-up recommendations.
6. Avoid speculative architecture.
7. Do not hide uncertainty.

A maintainable partial improvement is better than a risky, oversized rewrite.
