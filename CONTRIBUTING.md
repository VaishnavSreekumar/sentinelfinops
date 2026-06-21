# Contributing to SentinelFinOps

First off, thank you for considering contributing to SentinelFinOps! It is contributors like you who make this platform a powerful, production-ready tool.

Please review these guidelines to make the contribution process smooth and successful.

## Code of Conduct

By participating in this project, you agree to abide by our standards of respectful, collaborative, and professional engagement.

## How to Contribute

### 1. Branch Naming Convention
When working on features, bugfixes, or enhancements, please use the following naming convention for your branches:
- Feature branch: `feature/short-description`
- Bugfix branch: `bugfix/short-description`
- Documentation: `docs/short-description`
- Release tracking: `release/vX.Y.Z`

### 2. Local Setup
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/VaishnavSreekumar/sentinelfinops.git
   cd sentinelfinops
   ```
2. **Setup Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
   ```
3. **Install Pinned Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Copy Configuration Template:**
   ```bash
   cp config/settings.example.yaml config/settings.yaml
   # Populate config/settings.yaml with your development target settings (it is gitignored)
   ```

### 3. Coding Style & Linting
We adhere to PEP8 guidelines for Python code. Before opening a Pull Request, run `flake8` to inspect syntax:
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

### 4. Running Security Scans
Security is paramount in FinOps operations. Verify that your updates do not introduce vulnerabilities:
- **Python scan:** `bandit -r . -x ./venv,./lambda_package`
- **Terraform scan:** `tfsec terraform/`

### 5. Running Tests
You must write unit tests for any new behavior. To execute the test suite:
```bash
python -m unittest discover -s tests
```
Ensure code coverage for your components is at or above **80%**.

### 6. Pull Request Process
1. Push your branch to your origin fork.
2. Open a Pull Request against the `main` branch.
3. Describe the change, the reason it is needed, and your verification steps.
4. Ensure the GitHub Actions CI workflow successfully passes (linting, bandit, tfsec, and tests).
5. Address any reviewer feedback.
