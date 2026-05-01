"""
show_all_skills.py — Mostra il catalogo completo delle 580 skill
con verifica rappresentativa su SkillsMP per ogni sottodominio.
"""
import sys, os, re, json, time
sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import httpx

API_BASE = 'https://skillsmp.com/api/v1'
API_KEY = os.environ.get('SKILLSMP_API_KEY', '')

def search(q, limit=3):
    r = httpx.get(f'{API_BASE}/skills/search',
                  params={'q': q, 'limit': limit, 'sortBy': 'stars'},
                  headers={'Authorization': f'Bearer {API_KEY}'}, timeout=10)
    r.raise_for_status()
    return r.json()

# ── Definizione dei 17 domini con tutte le skill ──
domains = {
    '1. DEV ENGINEERING': {
        'icon': '🖥️',
        'subs': {
            'Linguaggi & Pattern': ['modern-javascript-patterns', 'typescript-advanced-types', 'go-concurrency-patterns', 'rust-async-patterns', 'csharp-async', 'error-handling-patterns', 'auth-implementation-patterns', 'python-code-style', 'python-design-patterns', 'python-type-safety', 'python-anti-patterns', 'python-performance-optimization', 'memory-safety-patterns', 'cloud-design-patterns'],
            'Backend Framework': ['nodejs-backend-patterns', 'fastapi-templates', 'dotnet-backend-patterns', 'java-springboot', 'kotlin-springboot', 'aspnet-minimal-api-openapi', 'microservices-patterns', 'cqrs-implementation', 'saga-orchestration', 'event-store-design', 'projection-patterns', 'api-design-principles', 'openapi-spec-generation', 'openapi-to-application-code'],
            'Frontend Framework': ['nextjs-app-router-patterns', 'next-best-practices', 'next-cache-components', 'next-upgrade', 'next-intl-add-language', 'react-modernization', 'react-state-management', 'react-native-architecture', 'react-native-design', 'vue-best-practices', 'vue-options-api-best-practices', 'vue-router-best-practices', 'vue-pinia-best-practices', 'vue-jsx-best-practices', 'vue-debug-guides', 'shadcn', 'web-coder', 'web-component-design', 'premium-frontend-ui', 'e2e-testing-patterns'],
            'Expo/React Native': ['expo-module', 'expo-api-routes', 'expo-deployment', 'expo-dev-client', 'expo-tailwind-setup', 'expo-cicd-workflows', 'use-dom', 'upgrading-expo', 'building-native-ui', 'native-data-fetching', 'vercel-react-native-skills'],
            'Monorepo & Build': ['monorepo-management', 'turborepo', 'turborepo-caching', 'nx-workspace-patterns', 'bazel-build-optimization', 'multi-stage-dockerfile'],
            'MCP Server Gen': ['python-mcp-server-generator', 'typescript-mcp-server-generator', 'csharp-mcp-server-generator', 'go-mcp-server-generator', 'java-mcp-server-generator', 'kotlin-mcp-server-generator', 'php-mcp-server-generator', 'ruby-mcp-server-generator', 'rust-mcp-server-generator', 'swift-mcp-server-generator', 'mcp-builder', 'mcp-cli', 'mcp-copilot-studio-server-generator', 'mcp-security-audit'],
            'API Integration': ['stripe-integration', 'paypal-integration', 'integrate-context-matic'],
            'Migrazioni': ['dependency-upgrade', 'database-migration', 'angular-migration', 'dotnet-upgrade', 'react-modernization', 'react18-enzyme-to-rtl', 'react18-lifecycle-patterns', 'react18-string-refs', 'react18-legacy-context', 'react18-batching-patterns', 'react19-concurrent-patterns', 'react19-source-patterns', 'react19-test-patterns', 'react18-dep-compatibility', 'react-audit-grep-patterns'],
        }
    },
    '2. INFRASTRUCTURE': {
        'icon': '☁️',
        'subs': {
            'Kubernetes': ['k8s-manifest-generator', 'k8s-security-policies', 'helm-chart-scaffolding', 'istio-traffic-management', 'linkerd-patterns', 'service-mesh-observability', 'gitops-workflow', 'mtls-configuration'],
            'CI/CD': ['github-actions-templates', 'github-actions-docs', 'deployment-pipeline-design', 'gitlab-ci-patterns', 'secrets-management', 'devops-rollout-plan', 'codeql', 'dependabot', 'secret-scanning', 'sast-configuration'],
            'Terraform/IaC': ['terraform-module-library', 'import-infrastructure-as-code', 'terraform-azurerm-set-diff-analyzer', 'update-avm-modules-in-bicep'],
            'Cloud Platforms': ['multi-cloud-architecture', 'cost-optimization', 'hybrid-cloud-networking', 'aws-cdk-python-setup'],
            'Azure': ['azure-architecture-autopilot', 'azure-deployment-preflight', 'azure-pricing', 'azure-resource-health-diagnose', 'azure-resource-visualizer', 'azure-role-selector', 'azure-static-web-apps', 'az-cost-optimize', 'azure-devops-cli'],
            'Monitoring': ['prometheus-configuration', 'grafana-dashboards', 'distributed-tracing', 'slo-implementation', 'incident-runbook-templates', 'on-call-handoff-patterns', 'postmortem-writing'],
        }
    },
    '3. AI & AGENTS': {
        'icon': '🤖',
        'subs': {
            'LLM Dev': ['langchain-architecture', 'rag-implementation', 'hybrid-search-implementation', 'embedding-strategies', 'similarity-search-patterns', 'vector-index-tuning', 'prompt-engineering-patterns', 'llm-evaluation', 'eval-driven-dev', 'agentic-eval'],
            'Agent Frameworks': ['semantic-kernel', 'microsoft-agent-framework', 'copilot-sdk', 'declarative-agents', 'copilot-spaces', 'workflow-orchestration-patterns', 'temporal-python-testing'],
            'Arize AI': ['arize-instrumentation', 'arize-trace', 'arize-evaluator', 'arize-experiment', 'arize-dataset', 'arize-annotation', 'arize-prompt-optimization', 'arize-link', 'arize-ai-provider-integration'],
            'Phoenix': ['phoenix-cli', 'phoenix-tracing', 'phoenix-evals'],
            'Tavily': ['tavily-search', 'tavily-extract', 'tavily-crawl', 'tavily-map', 'tavily-research', 'tavily-cli', 'tavily-best-practices'],
            'AI Safety': ['agent-governance', 'agent-owasp-compliance', 'agent-supply-chain', 'ai-prompt-engineering-safety-review'],
        }
    },
    '4. GO-TO-MARKET': {
        'icon': '📈',
        'subs': {
            'Copy & Content': ['copywriting', 'copy-editing', 'content-strategy', 'social-content', 'email-sequence', 'cold-email', 'ad-creative', 'programmatic-seo'],
            'SEO': ['seo-audit', 'ai-seo', 'schema-markup', 'site-architecture', 'competitor-alternatives'],
            'CRO': ['page-cro', 'signup-flow-cro', 'onboarding-cro', 'form-cro', 'popup-cro', 'paywall-upgrade-cro', 'ab-test-setup'],
            'Paid Ads': ['paid-ads', 'ad-creative', 'analytics-tracking'],
            'Product Marketing': ['product-marketing-context', 'launch-strategy', 'pricing-strategy', 'marketing-ideas', 'marketing-psychology', 'referral-program', 'lead-magnets', 'free-tool-strategy', 'competitive-landscape'],
            'Sales': ['sales-enablement', 'competitor-alternatives', 'customer-research'],
            'GTM Strategy': ['gtm-0-to-1-launch', 'gtm-positioning-strategy', 'gtm-product-led-growth', 'gtm-ai-gtm', 'gtm-enterprise-account-planning', 'gtm-enterprise-onboarding', 'gtm-board-and-investor-communication', 'gtm-technical-product-pricing', 'gtm-partnership-architecture', 'gtm-developer-ecosystem', 'gtm-operating-cadence'],
            'RevOps': ['revops', 'churn-prevention', 'billing-automation', 'analytics-tracking'],
        }
    },
    '5. DESIGN & UI': {
        'icon': '🎨',
        'subs': {
            'Foundations': ['visual-design-foundations', 'design-system-patterns', 'tailwind-design-system', 'brand-guidelines', 'responsive-design'],
            'UI Dev': ['frontend-design', 'ui-ux-pro-max', 'ckm-ui-styling', 'ckm-design', 'ckm-brand', 'ckm-design-system', 'ckm-banner-design', 'ckm-slides', 'interaction-design', 'theme-factory', 'premium-frontend-ui', 'web-design-guidelines', 'web-artifacts-builder'],
            'Accessibility': ['accessibility-compliance', 'wcag-audit-patterns', 'screen-reader-testing'],
            'Mobile Design': ['mobile-ios-design', 'mobile-android-design'],
            'Design Tools': ['penpot-uiux-design', 'excalidraw-diagram-generator', 'canvas-design', 'algorithmic-art', 'web-design-reviewer'],
        }
    },
    '6. DATA & ANALYTICS': {
        'icon': '📊',
        'subs': {
            'Database': ['postgresql-table-design', 'postgresql-optimization', 'postgresql-code-review', 'sql-optimization-patterns', 'sql-optimization', 'sql-code-review', 'supabase', 'supabase-postgres-best-practices', 'cosmosdb-datamodeling', 'ef-core', 'database-migration'],
            'Pipeline': ['dbt-transformation-patterns', 'airflow-dag-patterns', 'spark-optimization', 'bigquery-pipeline-audit', 'ml-pipeline-workflow'],
            'BI': ['powerbi-modeling', 'power-bi-dax-optimization', 'power-bi-model-design-review', 'power-bi-performance-troubleshooting', 'power-bi-report-design-consultation', 'kpi-dashboard-design', 'data-storytelling', 'fabric-lakehouse'],
            'Data Science': ['data-quality-frameworks', 'datanalysis-credit-risk', 'market-sizing-analysis', 'startup-financial-modeling', 'startup-metrics-framework'],
            'Dataverse': ['dataverse-python-quickstart', 'dataverse-python-production-code', 'dataverse-python-advanced-patterns', 'dataverse-python-usecase-builder'],
        }
    },
    '7. SECURITY': {
        'icon': '🔒',
        'subs': {
            'AppSec': ['security-review', 'sast-configuration', 'secret-scanning', 'codeql', 'gdpr-compliant', 'gdpr-data-handling', 'pci-compliance', 'secure-linux-web-hosting', 'openclaw-secure-linux-cloud'],
            'Threat Model': ['threat-model-analyst', 'stride-analysis-patterns', 'attack-tree-construction', 'security-requirement-extraction', 'threat-mitigation-mapping'],
            'Blockchain/Web3': ['solidity-security', 'nft-standards', 'defi-protocol-templates', 'web3-testing'],
            'RE': ['binary-analysis-patterns', 'anti-reversing-techniques', 'protocol-reverse-engineering', 'memory-forensics'],
        }
    },
    '8. MICROSOFT': {
        'icon': '🪟',
        'subs': {
            '.NET/C#': ['dotnet-backend-patterns', 'dotnet-best-practices', 'dotnet-design-pattern-review', 'dotnet-timezone', 'dotnet-upgrade', 'csharp-async', 'csharp-docs', 'ef-core', 'nuget-manager', 'fluentui-blazor', 'aspire', 'aspnet-minimal-api-openapi'],
            'Azure': ['azure-architecture-autopilot', 'azure-deployment-preflight', 'azure-pricing', 'azure-resource-health-diagnose', 'azure-resource-visualizer', 'azure-role-selector', 'azure-static-web-apps', 'az-cost-optimize', 'azure-devops-cli', 'appinsights-instrumentation', 'import-infrastructure-as-code'],
            'M365 Copilot': ['declarative-agents', 'typespec-create-agent', 'typespec-create-api-plugin', 'typespec-api-operations', 'mcp-create-declarative-agent', 'mcp-create-adaptive-cards', 'mcp-deploy-manage-agents', 'mcp-copilot-studio-server-generator'],
            'Power Platform': ['flowstudio-power-automate-mcp', 'flowstudio-power-automate-build', 'flowstudio-power-automate-debug', 'flowstudio-power-automate-monitoring', 'flowstudio-power-automate-governance', 'power-apps-code-app-scaffold', 'power-platform-mcp-connector-suite'],
            'Copilot CLI': ['cli-mastery', 'noob-mode', 'copilot-cli-quickstart', 'copilot-usage-metrics', 'copilot-spaces'],
            'Windows': ['winapp-cli', 'winmd-api-search', 'winui3-migration-guide', 'msstore-cli', 'electron'],
            'Entra': ['entra-agent-user'],
        }
    },
    '9. PROJECT & DOCS': {
        'icon': '📋',
        'subs': {
            'Documentation': ['documentation-writer', 'doc-coauthoring', 'create-readme', 'create-llms', 'update-llms', 'architecture-decision-records', 'create-architectural-decision-record', 'hads', 'oo-component-documentation', 'csharp-docs', 'java-docs', 'add-educational-comments', 'readme-i18n', 'mkdocs-translations', 'create-tldr-page', 'tldr-prompt'],
            'Specs & Plans': ['create-specification', 'update-specification', 'prd', 'breakdown-epic-pm', 'breakdown-epic-arch', 'breakdown-feature-prd', 'breakdown-feature-implementation', 'breakdown-plan', 'breakdown-test', 'create-implementation-plan', 'update-implementation-plan', 'create-technical-spike', 'writing-plans'],
            'Project Execution': ['context-driven-development', 'context-map', 'track-management', 'workflow-patterns', 'using-git-worktrees', 'executing-plans', 'test-driven-development', 'refactor-plan', 'brainstorming', 'first-ask', 'boost-prompt'],
            'Git/GitHub': ['gh-cli', 'github-issues', 'my-issues', 'my-pull-requests', 'gen-specs-as-issues', 'create-github-issue-feature-from-specification', 'create-github-issues-feature-from-implementation-plan', 'create-github-issues-for-unmet-specification-requirements', 'create-github-pull-request-from-specification', 'issue-fields-migration', 'git-commit', 'conventional-commit', 'git-advanced-workflows', 'git-flow-branch-creator', 'finishing-a-development-branch', 'make-repo-contribution', 'changelog-automation', 'repo-story-time'],
            'Diagrams': ['draw-io-diagram-generator', 'excalidraw-diagram-generator', 'plantuml-ascii', 'architecture-blueprint-generator', 'technology-stack-blueprint-generator', 'folder-structure-blueprint-generator', 'project-workflow-analysis-blueprint-generator', 'code-exemplars-blueprint-generator', 'readme-blueprint-generator'],
        }
    },
    '10. SYSTEMS & OPS': {
        'icon': '🐧',
        'subs': {
            'Linux Distro': ['arch-linux-triage', 'debian-linux-triage', 'fedora-linux-triage', 'centos-linux-triage'],
            'Scripting': ['bash-defensive-patterns', 'shellcheck-configuration', 'bats-testing-patterns', 'uv-package-manager'],
            'Networking': ['hybrid-cloud-networking', 'geofeed-tuner', 'secure-linux-web-hosting'],
            'Deploy': ['deploy-to-vercel', 'vercel-cli-with-tokens', 'publish-to-pages', 'containerize-aspnetcore', 'containerize-aspnet-framework'],
        }
    },
    '11. BUSINESS & FINANCE': {
        'icon': '💰',
        'subs': {
            'Startup': ['startup-financial-modeling', 'startup-metrics-framework', 'market-sizing-analysis', 'competitive-landscape', 'team-composition-analysis'],
            'Legal/HR': ['employment-contract-templates', 'internal-comms'],
            'Revenue': ['pricing-strategy', 'billing-automation', 'churn-prevention'],
        }
    },
    '12. CRAFT AGENT META': {
        'icon': '⚙️',
        'subs': {
            'Skill Management': ['find-skills', 'skill-creator', 'writing-skills', 'make-skill-template', 'skills-cli', 'microsoft-skill-creator', 'evaluation-methodology', 'suggest-awesome-github-copilot-agents', 'suggest-awesome-github-copilot-instructions', 'suggest-awesome-github-copilot-skills'],
            'Prompt Engineering': ['prompt-builder', 'finalize-agent-prompt', 'create-agentsmd', 'create-llms', 'hads', 'copilot-instructions-blueprint-generator'],
            'Memory & Handoff': ['remember', 'memory-merger', 'from-the-other-side-vega'],
            'Multi-Agent': ['subagent-driven-development', 'dispatching-parallel-agents', 'parallel-feature-development', 'task-coordination-strategies', 'team-composition-patterns', 'team-communication-protocols', 'structured-autonomy-plan', 'structured-autonomy-implement', 'structured-autonomy-generate'],
            'Verification': ['verification-before-completion', 'systematic-debugging', 'parallel-debugging', 'doublecheck', 'receiving-code-review', 'requesting-code-review', 'code-review-excellence', 'multi-reviewer-patterns', 'review-and-refactor'],
        }
    },
    '13. TESTING & QA': {
        'icon': '🧪',
        'subs': {
            'Testing Frameworks': ['javascript-testing-patterns', 'javascript-typescript-jest', 'python-testing-patterns', 'pytest-coverage', 'csharp-mstest', 'csharp-xunit', 'csharp-nunit', 'csharp-tunit', 'java-junit', 'spring-boot-testing', 'unit-test-vue-pinia', 'vue-testing-best-practices'],
            'E2E & Browser': ['e2e-testing-patterns', 'playwright-explore-website', 'playwright-generate-test', 'playwright-automation-fill-in-form', 'webapp-testing', 'scoutqa-test'],
            'Polyglot/Specialized': ['polyglot-test-agent', 'temporal-python-testing', 'web3-testing'],
            'Quality': ['quality-playbook', 'ruff-recursive-fix', 'shellcheck-configuration'],
        }
    },
    '14. SPECIALIZED': {
        'icon': '🔧',
        'subs': {
            'Oracle→Postgres': ['creating-oracle-to-postgres-master-migration-plan', 'creating-oracle-to-postgres-migration-bug-report', 'creating-oracle-to-postgres-migration-integration-tests', 'reviewing-oracle-to-postgres-migration', 'migrating-oracle-to-postgres-stored-procedures', 'planning-oracle-to-postgres-migration-integration-testing', 'scaffolding-oracle-to-postgres-migration-test-project'],
            'Salesforce': ['salesforce-apex-quality', 'salesforce-component-standards', 'salesforce-flow-design'],
            'Convex': ['convex-quickstart', 'convex-setup-auth', 'convex-create-component', 'convex-migration-helper', 'convex-performance-audit'],
            'Better Auth': ['better-auth-best-practices', 'create-auth-skill', 'email-and-password-best-practices', 'two-factor-authentication-best-practices', 'organization-best-practices'],
            'Power BI': ['powerbi-modeling', 'power-bi-dax-optimization', 'power-bi-model-design-review', 'power-bi-performance-troubleshooting', 'power-bi-report-design-consultation'],
            'Snowflake': ['snowflake-semanticview'],
            'Vercel': ['vercel-composition-patterns', 'vercel-react-best-practices', 'vercel-react-native-skills', 'vercel-react-view-transitions', 'vercel-sandbox'],
            'Game Dev': ['game-engine', 'godot-gdscript-patterns', 'unity-ecs-patterns'],
        }
    },
    '15. CONTENT & MEDIA': {
        'icon': '📝',
        'subs': {
            'File Formats': ['docx', 'pptx', 'xlsx', 'pdf', 'pdftk-server', 'markdown-to-html', 'shuffle-json-data', 'convert-plaintext-to-md'],
            'Media': ['transloadit-media-processing', 'image-manipulation-image-magick', 'slack-gif-creator', 'nano-banana-pro-openrouter'],
            'Email': ['email-drafter', 'email-sequence', 'cold-email', 'email-and-password-best-practices'],
            'Blog & Content': ['content-strategy', 'copywriting', 'social-content', 'programmatic-seo', 'lead-magnets'],
        }
    },
    '16. GAMING & REVERSE': {
        'icon': '🎮',
        'subs': {
            'Game Dev': ['game-engine', 'godot-gdscript-patterns', 'unity-ecs-patterns'],
            'Reverse Engineering': ['binary-analysis-patterns', 'anti-reversing-techniques', 'memory-forensics', 'protocol-reverse-engineering'],
            'Retro': ['legacy-circuit-mockups'],
            'Art': ['algorithmic-art'],
        }
    },
    '17. UTILITY': {
        'icon': '🔌',
        'subs': {
            'Browser Automation': ['agent-browser', 'agentcore', 'chrome-devtools', 'electron', 'use-my-browser', 'slack', 'develop-userscripts'],
            'Productivity': ['automate-this', 'autoresearch', 'daily-prep', 'roundup', 'roundup-setup', 'meeting-minutes', 'dogfood', 'napkin'],
            'Onboarding': ['noob-mode', 'copilot-cli-quickstart', 'what-context-needed', 'onboard-context-matic'],
            'Environment': ['sandbox-npm-install', 'tzst', 'xdrop', 'xget', 'block-no-verify-hook', 'editorconfig'],
            'Language': ['finnish-humanizer', 'mkdocs-translations', 'readme-i18n', 'next-intl-add-language'],
            'Writing': ['copy-editing', 'refactor', 'refactor-plan', 'review-and-refactor', 'quasi-coder'],
            'AI Models': ['model-recommendation', 'running-claude-code-via-litellm-copilot', 'copilot-usage-metrics', 'sponsor-finder', 'opensource-guide-coach'],
        }
    },
}

# ── Verifica SkillsMP ──
def check_skillsmp(skill_name):
    """Cerca su SkillsMP e restituisce (stars, date_updated, author)"""
    try:
        data = search(skill_name.replace('-', ' '), limit=1)
        if data.get('success') and data['data']['skills']:
            s = data['data']['skills'][0]
            stars = s.get('stars', 0)
            updated = s.get('updatedAt', '')
            if updated:
                updated = time.strftime('%Y-%m-%d', time.gmtime(int(updated)))
            author = s.get('author', '')
            return (int(stars), updated, author)
        return (0, '-', '-')
    except:
        return (-1, 'ERR', '')

# ── Stampa ──
total_skills = sum(len(sk) for d in domains.values() for sub in d['subs'].values() for sk in sub)
calls = 0
MAX_CALLS = 35

print('═' * 130)
print(f'  CATALOGO RAGIONATO — TUTTE LE {total_skills} SKILL (con verifica SkillsMP)')
print('═' * 130)
print()
print(f'  {"Legenda:":>12} ⭐ N = stelle GitHub su SkillsMP | 📅 = ultimo aggiornamento')
print(f'  {"":>12} MIGLIORE = ha piu stelle della media del dominio | OK = nella media')
print()

total_found = 0

for dom_key, dom_data in domains.items():
    icon = dom_data['icon']
    subs = dom_data['subs']
    dom_total = sum(len(s) for s in subs.values())
    
    print(f'  {icon}  {dom_key}')
    print(f'  {"":4}{dom_total} skill')
    print()
    
    for label, skills in subs.items():
        print(f'     {label}')
        for sk in skills:
            if calls < MAX_CALLS:
                stars, updated, author = check_skillsmp(sk)
                calls += 1
                if stars > 0:
                    total_found += 1
                    star_str = f'⭐{stars:>6,}'.replace(',', '.')
                    print(f'        {sk:50s}  {star_str}  📅{updated}  👤{author[:20]:20s}')
                else:
                    print(f'        {sk:50s}  [non trovata su SkillsMP]')
            else:
                print(f'        {sk:50s}  [vedi catalogo]')
        print()
    
    print()

print('═' * 130)
print(f'  TOTALI: {total_skills} skill catalogate | {total_found} verificate su SkillsMP | {calls} API calls')
print()
print('  💡 Come usare questa tabella:')
print('     - Chiedi \"Mostrami le skill del §3 AI & Agents\" per vedere solo quel dominio')
print('     - Chiedi \"skillsmp_check_skill per stripe-integration\" per dettagli specifici')
print('     - Chiedi \"confronta skillsmp per fastapi-templates\" per trovare alternative')
print('     - Chiedi \"Quali skill del dominio X hanno piu stelle su SkillsMP?\"')
print('═' * 130)
