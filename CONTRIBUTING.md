# Contributing to SentinelFinOps (v5.0)

Thank you for contributing to SentinelFinOps! This guide covers coding standards, architectural principles, and the steps to extend the system without violating our decoupled layers.

---

## 1. Architectural Principles

All contributions must adhere to the following principles:
- **Decoupled Responsibilities**: Do not mix layers. Scanners discover resources; the AI runtime reasons; the Policy Engine enforces compliance; Slack presents notifications; storage classes manage state.
- **Fail-Safe Integrity**: AI and LLM outputs are auxiliary. The platform must function using legacy heuristics if AI services are unavailable.
- **Dependency Injection**: Classes (like mappers, rules, and validators) must receive their dependencies via constructor parameters. Do not load configuration files or instantiate provider client singletons inside deep logic classes.
- **Immutability**: All contracts (subclasses of `ContractBase`) and evaluation results must be immutable to avoid side effects.

---

## 2. Local Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/VaishnavSreekumar/sentinelfinops.git
   cd sentinelfinops
   ```
2. **Setup Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Setup Local Config**:
   ```bash
   cp config/settings.example.yaml config/settings.yaml
   # Edit settings.yaml to match your sandbox environment
   ```

---

## 3. Extension Guides

### How to Add a New Context Mapper
1. Create a new mapper class (e.g., `RDSMapper`) inheriting from `ContextMapper` in `ai/context/`.
2. Implement `supported_resource_type` to return the target resource type.
3. Implement `map(self, scan_context: ScanContext) -> ResourceContextV1` to transform raw parameters into the normalized contract.
4. Register the new mapper class in the `create_ai_runtime` factory function inside `ai/runtime.py`.

### How to Add a New LLM Provider
1. Create a new provider class (e.g., `AnthropicProvider`) inheriting from `LLMProvider` in `ai/interfaces/provider.py`.
2. Implement the `generate(self, system_prompt: str, user_prompt: str, response_schema: Type) -> Any` method.
3. Handle authentication using keys passed through the provider's `config` dictionary argument.
4. Register the provider instantiation key inside `create_ai_runtime()` inside `ai/runtime.py`.

### How to Add a New Prompt Template
1. Create a directory inside `config/prompts/` matching the prompt name (e.g., `config/prompts/idle_db/`).
2. Create a semantic version directory (e.g., `1.0.0/`).
3. Add `system.txt` (defining role/rules) and `user.txt` (containing contextual variables like `{{ context_json }}`).
4. The `PromptRegistry` will automatically discover and load the latest version.

### How to Add a New Policy Rule
1. Create a subclass in `policy/rules/` (e.g., `policy/rules/critical_tag.py`) inheriting from `PolicyRule` in `policy/rules/base_rule.py`.
2. Implement `evaluate(self, recommendation: RecommendationV1, context: Any = None) -> Union[bool, List[str]]`.
3. If validation fails, return a list of string violations. If it passes, return `True`.
4. Register the rule instance in the `create_ai_runtime` composition root's policy engine ruleset in `ai/runtime.py`.

---

## 4. Coding & Testing Standards

- **Static Type Hinting**: All new methods and functions must specify type annotations.
- **PEP 8 Linting**: Run `flake8` to scan for style violations:
  ```bash
  flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
  ```
- **Security Check**: Run `bandit` and `tfsec` to verify security health:
  ```bash
  bandit -r . -x ./venv,./lambda_package
  tfsec terraform/
  ```
- **Unit Testing**: You must write unit tests for all classes. Execute the test suite using:
  ```bash
  python -m unittest discover -s tests -p "test_*.py"
  ```
- **Coverage**: Keep overall test coverage above **80%**.
