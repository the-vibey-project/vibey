---
id: skill-azure-devops-pipeline-for-python-68aa18180b
purpose: azure devops pipeline for python
source: src/vibey_tools/skills/plugins/quality-engineering/skills/python-quality-testing/SKILL.md
requires: ["skill-azure-cloud-native-testing-2e886e185f"]
links: ["skill-coverage-targets-and-thresholds-55251a4804"]
---

## Azure DevOps Pipeline for Python

### Multi-Stage Pipeline Structure

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include: [main]
  paths:
    exclude: ['*.md', 'docs/*']

stages:
  - stage: Build
    jobs:
      - job: BuildAndLint
        pool:
          vmImage: ubuntu-latest
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.11'
          
          - script: |
              pip install uv
              uv pip install --system -e ".[dev]"
            displayName: 'Install dependencies'
          
          - script: ruff check . && ruff format . --check
            displayName: 'Lint and format check (Ruff)'
          
          - script: mypy src/
            displayName: 'Type check (mypy)'

  - stage: Test
    dependsOn: Build
    jobs:
      - job: UnitTests
        steps:
          - script: |
              pytest tests/unit/ \
                --junitxml=junit/unit-results.xml \
                --cov=src --cov-report=xml \
                --cov-fail-under=80 -v
            displayName: 'Unit tests'
          
          - task: PublishTestResults@2
            condition: always()
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '**/unit-results.xml'
              failTaskOnFailedTests: true
          
          - task: PublishCodeCoverageResults@2
            inputs:
              summaryFileLocation: '**/coverage.xml'
      
      - job: IntegrationTests
        steps:
          - script: npm install -g azurite && azurite --silent &
            displayName: 'Start Azurite'
          
          - script: |
              pytest tests/integration/ \
                --junitxml=junit/integration-results.xml -v
            displayName: 'Integration tests'
  
  - stage: Security
    dependsOn: Build
    jobs:
      - job: SecurityScan
        steps:
          - task: MicrosoftSecurityDevOps@1
            inputs:
              categories: 'code,dependencies'
              break: true  # fail pipeline on high severity
          
          - script: |
              pip install bandit
              bandit -r src/ -f json -o bandit-report.json -ll
            displayName: 'Bandit SAST'

  - stage: Deploy
    dependsOn: [Test, Security]
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployStaging
        environment: staging
        strategy:
          runOnce:
            deploy:
              steps:
                - script: echo "Deploy to staging"
```

### Parallel Test Execution

```yaml
# Split large test suite across 5 agents
strategy:
  parallel: 5
steps:
  - script: |
      pip install pytest-split
      pytest tests/ \
        --splits=$(System.TotalJobsInPhase) \
        --group=$(System.JobPositionInPhase) \
        --junitxml=junit/test-results-$(System.JobPositionInPhase).xml
```

### GitHub Actions Equivalent

```yaml
# .github/workflows/quality.yml
jobs:
  test:
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check . && ruff format . --check
      - run: mypy src/
      - run: pytest --cov=src --cov-report=xml --cov-fail-under=80
      - uses: codecov/codecov-action@v4
```

---
