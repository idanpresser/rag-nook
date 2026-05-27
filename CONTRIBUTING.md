# Contributing to Insights Explorer

Thank you for your interest in contributing to **Insights Explorer**! We are excited to build a local, privacy-first personal memory RAG platform together.

To keep the codebase elegant, secure, and performant, please follow these guidelines.

---

## 🗺️ How Can I Contribute?

You can contribute in several ways:
- **Bug Reports & Feature Requests**: Submit an issue using our structured templates.
- **Documentation**: Improve this guide, setup guides, or add inline code documentations.
- **Code Contributions**: Fix open bugs, optimize RAG retrievals, or implement new visualization styles in the React dashboard.

---

## 🛠️ Local Environment Setup

### 1. Prerequisite Installations
- **Python**: version `3.11` or higher.
- **Node.js**: version `18.0` or higher (including `npm`).
- **LM Studio / Ollama**: Running a local compatible model (such as `Nous Hermes 3` or `Gemma-4-e2b`).

### 2. Backend Installation & Activation
1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/idaneyal/personal_memory.git
   cd personal_memory
   ```
2. Create and source a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the project requirements:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Copy the environment template and set up your config:
   ```bash
   cp .env.example .env
   ```

### 3. Frontend Installation
1. Navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```

---

## 🎨 Coding Standards & Quality Guidelines

To maintain absolute software craftsmanship, we enforce uniform linting and style formatting:

- **Formatting (Python)**: We use **Black** for layout rules.
- **Import Sorting**: We use **isort** to structure imports cleanly.
- **Linting**: We use **Flake8** to catch syntax errors and unused variables.

Before submitting any code, install and run `pre-commit` locally to ensure checks pass automatically:
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Manually run on all files
pre-commit run --all-files
```

---

## 🧪 Testing

We require all pull requests to pass the full pytest suite. Ensure everything works cleanly before pushing:

```bash
# Run backend pytest suite from the project root
PYTHONPATH=. .venv/bin/pytest
```

Ensure the Vite production bundle compiles without typescript or layout compiler errors:
```bash
cd frontend
npm run build
```

---

## 🚀 Pull Request Checklist

When submitting a pull request, please ensure the following:
- [ ] Your branch is branched from `main`.
- [ ] Code is formatted cleanly with `black` and imports are sorted.
- [ ] All unit tests pass locally.
- [ ] You have added tests covering the new bugfix or feature.
- [ ] For UI changes, screenshots or screen recordings are attached to the PR.
- [ ] You have updated the `README.md` or other documentations if applicable.

---

## 📜 Code of Conduct

We follow the Contributor Covenant. By participating in this project, you agree to abide by its terms. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for more details.
