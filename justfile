# Skills Hub monorepo commands

# Install all packages in development mode
dev:
    uv sync --all-packages

# Run all tests
test: test-builder test-eval

# Run skills-hub-builder tests
test-builder:
    uv run pytest packages/skills-hub-builder/tests/ -v

# Run skill-eval tests
test-eval:
    uv run pytest packages/skill-eval/tests/ -v

# Run tests with coverage
test-cov:
    uv run pytest packages/skills-hub-builder/tests/ packages/skill-eval/tests/ -v --cov

# Build the example project
build-example:
    uv run skills-hub-builder build --project example

# Inspect the example project tree
inspect-example:
    uv run skills-hub-builder inspect --project example

# Discover rubrics in the example project
discover-example:
    cd example && uv run skill-eval discover

# Build the self-hosting site (dogfood)
build-self:
    uv run skills-hub-builder build

# Run linting
lint:
    uv run ruff check packages/

# Format code
fmt:
    uv run ruff format packages/

# Clean build artifacts
clean:
    rm -rf example/_site _site
