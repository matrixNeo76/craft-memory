# Catalogo Ragionato delle Skill Craft Agent (580 Skill)

> **Ultima revisione:** 2026-05-01
> **Scopo:** Navigare 580 skill organizzate per dominio, comprendere quando usarle e perché.
> **Strategia di lettura:** Usa la **Mappa dei Domini** per orientarti, poi vai alla sezione pertinente.

---

## Mappa dei Domini (Navigazione Rapida)

```
┌────────────────────────────────────────────────────────────────────┐
│  🎯 COSA DEVI FARE?                    →  VAI ALLA SEZIONE       │
├────────────────────────────────────────────────────────────────────┤
│  Sviluppare software (qualsiasi stack)  →  §1 DEV ENGINEERING     │
│  Cloud, DevOps, Infrastruttura          →  §2 INFRASTRUCTURE      │
│  AI / LLM / Agent Systems               →  §3 AI & AGENTS        │
│  Marketing, Vendite, GTM                →  §4 GO-TO-MARKET       │
│  UI/UX Design & Frontend                →  §5 DESIGN & UI        │
│  Database, Dati & Analytics             →  §6 DATA & ANALYTICS   │
│  Security, Compliance                   →  §7 SECURITY            │
│  Microsoft Ecosystem (.NET, Azure, M365) →  §8 MICROSOFT          │
│  Gestione Progetto & Documentazione      →  §9 PROJECT & DOCS    │
│  Sistemi, Reti, OS                      →  §10 SYSTEMS & OPS     │
│  Business, Finance, Legal               →  §11 BUSINESS & FINANCE│
│  Craft Agent stesso (meta-skill)        →  §12 CRAFT AGENT META  │
│  Testing & Quality                      →  §13 TESTING & QA      │
│  Specialized / Niche                    →  §14 SPECIALIZED       │
│  Content & Media                        →  §15 CONTENT & MEDIA   │
│  Giochi, Reverse, Forensics            →  §16 GAMING & SEC      │
│  Vari / Utility                         →  §17 UTILITY           │
└────────────────────────────────────────────────────────────────────┘
```

---

## §1 — DEV ENGINEERING (Sviluppo Software Generale)

### 1.1 Linguaggi & Pattern

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `modern-javascript-patterns` | ES6+, async/await, destructuring, generators, FP | Refactoring JS legacy, ottimizzazione codice |
| `typescript-advanced-types` | Generics, conditional/mapped types, type-safety | Progetti TypeScript complessi, librerie |
| `go-concurrency-patterns` | Goroutines, channels, sync, context | App concorrenti Go, worker pool |
| `rust-async-patterns` | Tokio, async traits, error handling | Sistemi asincroni Rust |
| `csharp-async` | Best practice async C# | .NET async code |
| `error-handling-patterns` | Result types, exception patterns, graceful degradation | APIs, sistemi resilienti |
| `auth-implementation-patterns` | JWT, OAuth2, session management, RBAC | Sistemi di autenticazione |
| `python-code-style` | Linting, naming, docstring, formattazione | Standardizzazione Python |
| `python-design-patterns` | KISS, SOLID, composizione vs ereditarietà | Architettura Python |
| `python-type-safety` | Type hints, generics, protocols, mypy/pyright | Type safety Python |
| `python-anti-patterns` | Checklist anti-pattern Python | Code review Python |
| `python-performance-optimization` | cProfile, memory profilers, ottimizzazione | Slow Python code |
| `memory-safety-patterns` | RAII, ownership, smart pointers (Rust/C++/C) | Sistemi safe |
| `cloud-design-patterns` | 42 pattern distribuiti (reliability, messaging, etc.) | Architettura cloud |

### 1.2 Backend Framework

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `nodejs-backend-patterns` | Express/Fastify, middleware, API design | Nuovi backend Node.js |
| `fastapi-templates` | FastAPI async, DI, error handling | Nuove API Python FastAPI |
| `dotnet-backend-patterns` | .NET backend, DI, EF Core, Dapper, caching | Backend C# |
| `java-springboot` | Spring Boot best practices | Backend Java Spring Boot |
| `kotlin-springboot` | Spring Boot + Kotlin | Backend Kotlin |
| `aspnet-minimal-api-openapi` | Minimal API + documentazione OpenAPI | API .NET minimali |
| `microservices-patterns` | Service boundaries, event-driven, resilience | Architettura microservizi |
| `cqrs-implementation` | CQRS, read/write model separation | Sistemi event-driven |
| `saga-orchestration` | Distributed transactions, compensating actions | Transazioni multi-servizio |
| `event-store-design` | Event store per sistemi event-sourced | Infrastruttura event sourcing |
| `projection-patterns` | Read models da event streams | CQRS read side |
| `api-design-principles` | REST + GraphQL design principles | Design API |
| `openapi-spec-generation` | OpenAPI 3.1 spec da codice | Documentazione API |
| `openapi-to-application-code` | Genera app da spec OpenAPI | Prototipazione rapida |

### 1.3 Frontend Framework

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `nextjs-app-router-patterns` | Next.js 14+, Server Components, streaming, RSC | Siti Next.js moderni |
| `next-best-practices` | RSC boundaries, metadata, error handling | Ottimizzazione Next.js |
| `next-cache-components` | PPR, use cache, cacheLife, cacheTag | Caching Next.js 16 |
| `next-upgrade` | Upgrade Next.js con codemod | Migrazione Next.js |
| `next-intl-add-language` | Aggiunge lingua a next-intl | Internazionalizzazione |
| `react-modernization` | Upgrade React, hooks, concurrent features | Modernizzazione React |
| `react-state-management` | Redux Toolkit, Zustand, Jotai, React Query | Gestione stato React |
| `react-native-architecture` | Expo, navigation, native modules, offline | Sviluppo mobile React Native |
| `react-native-design` | Styling, Reanimated, navigation | UI React Native |
| `vue-best-practices` | Composition API, `<script setup>`, TypeScript | Standard Vue 3 |
| `vue-options-api-best-practices` | Options API (data, methods, this) | Progetti Vue legacy |
| `vue-router-best-practices` | Router 4, navigation guards | Routing Vue |
| `vue-pinia-best-practices` | Pinia stores, state management | Stato Vue |
| `vue-jsx-best-practices` | JSX in Vue (class, className) | Vue + JSX |
| `vue-debug-guides` | Debugging Vue 3, SSR/hydration errors | Bug fixing Vue |
| `shadcn` | Gestione componenti shadcn/ui | UI con shadcn |
| `web-coder` | HTML/CSS/JS, web APIs, HTTP, web standards | Sviluppo web generico |
| `web-component-design` | React/Vue/Svelte component patterns | Componenti riutilizzabili |
| `premium-frontend-ui` | Motion design, typography, craftsmanship | UI premium |
| `e2e-testing-patterns` | Playwright, Cypress, test suite | Test E2E |

### 1.4 Expo / React Native

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `expo-module` | Native modules Swift/Kotlin/TS | Moduli nativi Expo |
| `expo-api-routes` | API routes in Expo Router + EAS Hosting | Backend Expo |
| `expo-deployment` | Deploy iOS/Android/web/hosting | Pubblicazione Expo |
| `expo-dev-client` | Build e distribuzione dev client | Sviluppo Expo |
| `expo-tailwind-setup` | Tailwind v4 + react-native-css + NativeWind | Styling Expo |
| `expo-cicd-workflows` | EAS workflow YAML | CI/CD Expo |
| `use-dom` | Expo DOM components per webview native | Web code su mobile |
| `upgrading-expo` | Upgrade SDK + fix dipendenze | Migrazione Expo |
| `building-native-ui` | Expo Router styling, components, tabs | UI nativa Expo |
| `native-data-fetching` | fetch, React Query, SWR, caching | Data fetching nativo |
| `vercel-react-native-skills` | React Native + Expo best practices | Performance mobile |

### 1.5 Monorepo & Build

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `monorepo-management` | Turborepo, Nx, pnpm workspaces | Gestione monorepo |
| `turborepo` | turbo.json, pipelines, caching, filter | Configurazione Turborepo |
| `turborepo-caching` | Local/remote caching | Ottimizzazione build |
| `nx-workspace-patterns` | Nx setup, project boundaries, build cache | Workspace Nx |
| `bazel-build-optimization` | Remote execution, build optimization | Build enterprise |
| `multi-stage-dockerfile` | Dockerfile ottimizzati multi-stage | Containerizzazione |

### 1.6 MCP Server Generators

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `python-mcp-server-generator` | MCP server Python (FastMCP) | Nuovo MCP in Python |
| `typescript-mcp-server-generator` | MCP server TypeScript | Nuovo MCP in TypeScript |
| `csharp-mcp-server-generator` | MCP server C# | Nuovo MCP in C# |
| `go-mcp-server-generator` | MCP server Go | Nuovo MCP in Go |
| `java-mcp-server-generator` | MCP server Java (Spring Boot opz.) | Nuovo MCP in Java |
| `kotlin-mcp-server-generator` | MCP server Kotlin | Nuovo MCP in Kotlin |
| `php-mcp-server-generator` | MCP server PHP | Nuovo MCP in PHP |
| `ruby-mcp-server-generator` | MCP server Ruby | Nuovo MCP in Ruby |
| `rust-mcp-server-generator` | MCP server Rust (rmcp SDK) | Nuovo MCP in Rust |
| `swift-mcp-server-generator` | MCP server Swift | Nuovo MCP in Swift |
| `mcp-builder` | Guida generale creazione MCP server | Qualsiasi MCP server |
| `mcp-cli` | Interfaccia CLI per MCP | Usare MCP da terminale |
| `mcp-copilot-studio-server-generator` | MCP server per Copilot Studio | MCP per M365 Copilot |
| `mcp-security-audit` | Audit sicurezza MCP config | Review sicurezza MCP |

### 1.7 API Integration Patterns

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `stripe-integration` | Checkout, subscriptions, webhooks | Pagamenti Stripe |
| `paypal-integration` | Express checkout, subscriptions, refunds | Pagamenti PayPal |
| `integrate-context-matic` | Scopre e integra API terze via context-matic MCP | Integrazione API rapida |

### 1.8 Migrazioni & Upgrade

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `dependency-upgrade` | Major version upgrade con staging | Upgrade dipendenze |
| `database-migration` | Zero-downtime schema migration, rollback | Migrazioni DB |
| `angular-migration` | AngularJS → Angular hybrid mode | Migrazione Angular |
| `dotnet-upgrade` | Framework upgrade .NET | Upgrade .NET |
| `react-modernization` | React upgrade, hooks migration | Modernizzazione React |
| `react18-enzyme-to-rtl` | Enzyme → React Testing Library | Migrazione test React |
| `react18-lifecycle-patterns` | UNSAFE_ lifecycle migration | Fix lifecycle React 18 |
| `react18-string-refs` | String refs → createRef | Fix ref React 18 |
| `react18-legacy-context` | Legacy context → createContext | Fix context React 18 |
| `react18-batching-patterns` | Automatic batching regression fix | Fix batching React 18 |
| `react19-concurrent-patterns` | useTransition, use, useOptimistic, Actions | Pattern React 19 |
| `react19-source-patterns` | API changes, ref handling, context updates | Migrazione React 19 |
| `react19-test-patterns` | act imports, Simulate removal, StrictMode | Test React 19 |
| `react18-dep-compatibility` | Dependency compatibility matrix | Compatibilità React 18/19 |

---

## §2 — INFRASTRUCTURE (Cloud, DevOps, K8s)

### 2.1 Kubernetes & Container Orchestration

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `k8s-manifest-generator` | Deployments, Services, ConfigMaps, Secrets | Manifest K8s production |
| `k8s-security-policies` | NetworkPolicy, PodSecurityPolicy, RBAC | Sicurezza K8s |
| `helm-chart-scaffolding` | Helm charts per packaging K8s | Templating K8s |
| `istio-traffic-management` | Routing, circuit breakers, canary | Service mesh Istio |
| `linkerd-patterns` | Linkerd service mesh lightweight | Service mesh Linkerd |
| `service-mesh-observability` | Distributed tracing, metrics, SLOs | Observability mesh |
| `gitops-workflow` | ArgoCD, Flux, declarative K8s | GitOps deploy |
| `mtls-configuration` | Mutual TLS per service-to-service | Zero-trust networking |
| `helm-chart-scaffolding` | Helm charts per packaging | Templating K8s |

### 2.2 CI/CD & Pipeline

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `github-actions-templates` | Workflow CI/CD production-ready | Automazione GitHub |
| `github-actions-docs` | Workflow syntax, triggers, matrices | Documentazione GHA |
| `deployment-pipeline-design` | Canary rollout, approval gates, rollback | Pipeline multi-stage |
| `gitlab-ci-patterns` | Multi-stage, caching, distributed runners | CI/CD GitLab |
| `secrets-management` | Vault, AWS Secrets Manager, rotation | Gestione segreti CI/CD |
| `devops-rollout-plan` | Preflight, step-by-step, rollback plan | Piani di rollout |
| `codeql` | CodeQL scanning via GitHub Actions | Analisi sicurezza codice |
| `dependabot` | Config dependabot.yml, grouped updates | Dipendenze automatiche |
| `secret-scanning` | Secret scanning, push protection, custom patterns | Scansione segreti |
| `sast-configuration` | SAST tools per vulnerability detection | Sicurezza automatica |

### 2.3 Terraform & IaC

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `terraform-module-library` | Moduli Terraform riutilizzabili | IaC multi-cloud |
| `import-infrastructure-as-code` | Import risorse Azure in Terraform (AVM) | Reverse-engineer infra |
| `terraform-azurerm-set-diff-analyzer` | Analisi diff falsi positivi AzureRM | Debug plan Terraform |
| `update-avm-modules-in-bicep` | Update AVM modules in Bicep | Manutenzione Bicep |

### 2.4 Cloud Platforms

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `multi-cloud-architecture` | Decision framework AWS/Azure/GCP/OCI | Architettura multi-cloud |
| `cost-optimization` | Rightsizing, tagging, reserved instances | Ottimizzazione costi cloud |
| `hybrid-cloud-networking` | VPN, dedicated connections on-prem↔cloud | Rete ibrida |
| `aws-cdk-python-setup` | CDK Python setup + deploy | Infrastruttura AWS CDK |

### 2.5 Azure (Vedi anche §8 Microsoft)

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `azure-architecture-autopilot` | Design Azure infra da linguaggio naturale | Progettazione Azure |
| `azure-deployment-preflight` | Validazione Bicep, what-if, permessi | Pre-deploy Azure |
| `azure-pricing` | Prezzi real-time Azure + Copilot Studio | Stime costi Azure |
| `azure-resource-health-diagnose` | Diagnostica health + remediation plan | Troubleshooting Azure |
| `azure-resource-visualizer` | Diagrammi Mermaid da resource groups | Visualizzazione Azure |
| `azure-role-selector` | Role assignment least privilege | RBAC Azure |
| `azure-static-web-apps` | SWA CLI, local development, deploy | Static Web Apps |
| `az-cost-optimize` | Analisi costi Azure + GitHub issues | Ottimizzazione costi Azure |
| `azure-devops-cli` | Azure DevOps via CLI | Automazione DevOps |

### 2.6 Monitoring & Observability

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `prometheus-configuration` | Metric collection, storage, alerting | Infrastruttura monitoring |
| `grafana-dashboards` | Dashboard production per metriche | Visualizzazione metriche |
| `distributed-tracing` | Jaeger, Tempo per tracciamento richieste | Debug microservizi |
| `slo-implementation` | SLI/SLO con error budgets | Reliability engineering |
| `incident-runbook-templates` | Runbook incident response | Procedure incidente |
| `on-call-handoff-patterns` | Shift handoff, escalation, context transfer | Passaggio di consegne |
| `postmortem-writing` | Blameless postmortem + RCA | Analisi incidenti |

---

## §3 — AI & AGENTS

### 3.1 LLM Application Development

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `langchain-architecture` | LangChain + LangGraph per agents, tools | App LLM con LangChain |
| `rag-implementation` | RAG con vector DB + semantic search | Knowledge-grounded AI |
| `hybrid-search-implementation` | Vector + keyword search combinati | Retrieval avanzato |
| `embedding-strategies` | Selezione embedding, chunking strategies | Ottimizzazione RAG |
| `similarity-search-patterns` | Vector DB nearest neighbor | Search semantico |
| `vector-index-tuning` | HNSW tuning, quantization, recall | Ottimizzazione vettori |
| `prompt-engineering-patterns` | Advanced prompting techniques | Ottimizzazione prompt |
| `llm-evaluation` | Automated metrics, human feedback, benchmark | Valutazione LLM |
| `eval-driven-dev` | Eval-based QA per Python LLM apps | Quality assurance AI |
| `agentic-eval` | Self-critique, evaluator-optimizer | Miglioramento agenti |

### 3.2 Agent Frameworks

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `semantic-kernel` | Semantic Kernel .NET/Python | AI orchestration Microsoft |
| `microsoft-agent-framework` | Microsoft Agent Framework .NET/Python | Agenti Microsoft |
| `copilot-sdk` | GitHub Copilot SDK per app agentiche | Agenti embedded |
| `declarative-agents` | M365 Copilot declarative agents | Agenti M365 dichiarativi |
| `copilot-spaces` | Copilot Spaces per contesto condiviso | Knowledge base Copilot |
| `workflow-orchestration-patterns` | Temporal per workflow distribuiti | Long-running processes |
| `temporal-python-testing` | Test Temporal workflows con pytest | Testing Temporal |

### 3.3 Arize AI Observability

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `arize-instrumentation` | Tracing LLM con Arize AX | Instrumentazione AI |
| `arize-trace` | Download/esportazione trace | Debugging trace |
| `arize-evaluator` | LLM-as-judge evaluator su spans | Valutazione output |
| `arize-experiment` | Esperimenti e run evaluation | Testing comparativo |
| `arize-dataset` | CRUD dataset, export, file-based | Gestione dataset |
| `arize-annotation` | Annotation configs + human feedback | Feedback umano |
| `arize-prompt-optimization` | Ottimizzazione prompt da trace data | Debugging prompt |
| `arize-link` | Deep link UI Arize | Condivisione trace |
| `arize-ai-provider-integration` | Provider LLM integration | Setup provider |

### 3.4 Phoenix AI Observability

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `phoenix-cli` | Fetch traces, analyze errors, experiments | Debugging LLM |
| `phoenix-tracing` | OpenInference conventions, custom spans | Tracing LLM |
| `phoenix-evals` | Build e run evaluators | Valutazione LLM |

### 3.5 Tavily (Web Search per AI)

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `tavily-search` | Web search ottimizzato per LLM | Ricerca web generica |
| `tavily-extract` | Estrazione contenuto da URL | Contenuto pagine web |
| `tavily-crawl` | Crawl siti multi-pagina | Documentazione bulk |
| `tavily-map` | Scoperta URL su dominio | Mappatura siti |
| `tavily-research` | Deep research con citazioni | Report dettagliati |
| `tavily-cli` | Tutte le funzionalità Tavily in CLI | Accesso unificato |
| `tavily-best-practices` | Best practice integrazione Tavily | Pattern production |

### 3.6 AI Safety & Governance

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `agent-governance` | Policy-based access, trust scoring, audit | Governance agenti |
| `agent-owasp-compliance` | OWASP ASI Top 10 compliance check | Security audit agenti |
| `agent-supply-chain` | SHA-256 integrity manifests, supply chain | Supply chain agenti |
| `ai-prompt-engineering-safety-review` | Safety review prompt engineering | Review sicurezza prompt |

---

## §4 — GO-TO-MARKET (Marketing, Sales, Growth)

### 4.1 Content & Copywriting

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `copywriting` | Marketing copy per pagine web | Homepage, landing, pricing |
| `copy-editing` | Edit, review, refresh contenuti esistenti | Migliorare copy già scritto |
| `content-strategy` | Content planning, topic clusters, editorial calendar | Pianificazione contenuti |
| `social-content` | Post LinkedIn, Twitter, Instagram | Contenuti social |
| `cold-email` | B2B cold outreach + follow-up sequences | Email di prospezione |
| `email-sequence` | Drip campaign, onboarding, re-engagement | Automazione email |
| `ad-creative` | Ad copy headlines, descriptions, variations | Scrittura annunci |
| `programmatic-seo` | SEO pages at scale da template | Pagine SEO massive |

### 4.2 SEO & Search

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `seo-audit` | Technical SEO audit, on-page, Core Web Vitals | Diagnostica SEO |
| `ai-seo` | Ottimizzazione per AI search (AEO, GEO, LLMO) | Visibilità su AI |
| `schema-markup` | JSON-LD, schema.org, rich snippets | Dati strutturati |
| `site-architecture` | Page hierarchy, navigation, internal linking | Architettura sito |
| `competitor-alternatives` | Comparison/vs pages per SEO | Landing comparative |

### 4.3 Conversion Optimization (CRO)

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `page-cro` | Ottimizzazione conversioni pagine marketing | Landing che non convertono |
| `signup-flow-cro` | Ottimizzazione flusso registrazione | Signup dropoff |
| `onboarding-cro` | Post-signup activation, time-to-value | Utenti che non attivano |
| `form-cro` | Ottimizzazione form (non signup) | Form, demo, contatti |
| `popup-cro` | Popup, modal, exit intent, overlay | Lead capture popup |
| `paywall-upgrade-cro` | In-app paywall, upgrade screen, upsell | Conversione free→paid |
| `ab-test-setup` | A/B test planning, hypothesis, experiment design | Test A/B |

### 4.4 Paid Advertising

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `paid-ads` | Google Ads, Meta, LinkedIn campaign strategy | Campagne a pagamento |
| `ad-creative` | Ad copy variations per piattaforme | Creatività annunci |
| `analytics-tracking` | GA4, GTM, conversion tracking, events | Setup tracking |

### 4.5 Product Marketing & Launch

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `product-marketing-context` | Crea `.agents/product-marketing-context.md` | Setup contesto marketing |
| `launch-strategy` | Product Hunt, beta launch, GTM plan | Pianificazione lancio |
| `pricing-strategy` | Pricing tiers, freemium, value metric | Decisioni prezzo |
| `marketing-ideas` | Brainstorming marketing ideas | Ispirazione marketing |
| `marketing-psychology` | Cognitive bias, persuasion, behavioral science | Psicologia nel marketing |
| `referral-program` | Referral, affiliate, ambassador programs | Programmi referral |
| `lead-magnets` | Ebook, checklist, template per lead gen | Content offer |
| `free-tool-strategy` | Engineering-as-marketing con free tool | Tool gratuiti per lead |
| `competitive-landscape` | Porter, Blue Ocean, positioning maps | Analisi competitor |

### 4.6 Sales Enablement

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `sales-enablement` | Pitch deck, one-pager, objection handling | Materiale vendite |
| `competitor-alternatives` | Battle cards, comparison pages | Comparazione competitor |
| `customer-research` | Interview analysis, persona building, JTBD | Ricerca clienti |

### 4.7 GTM (Go-to-Market Strategy)

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `gtm-0-to-1-launch` | Launch da idea a primi clienti | Primo lancio prodotto |
| `gtm-positioning-strategy` | Posizionamento difendibile | Trovare posizione mercato |
| `gtm-product-led-growth` | Self-serve acquisition, activation | Growth PLG |
| `gtm-ai-gtm` | GTM per AI product, pricing, positioning | AI product GTM |
| `gtm-enterprise-account-planning` | MEDDICC, MAP, complex sales cycle | Enterprise sales |
| `gtm-enterprise-onboarding` | 4-phase enterprise onboarding | Onboarding enterprise |
| `gtm-board-and-investor-communication` | Board deck, investor update, QBR | Comunicazione C-level |
| `gtm-technical-product-pricing` | Usage-based vs seat-based, freemium | Pricing tecnico |
| `gtm-partnership-architecture` | Partner ecosystem, tiering | Partnership strategiche |
| `gtm-developer-ecosystem` | Developer adoption, platform programs | Ecosistema developer |
| `gtm-operating-cadence` | Meeting rhythms, metric reporting, QBR | Ritmo operativo |

### 4.8 Revenue Operations

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `revops` | Lead lifecycle, MQL/SQL, CRM automation | Revenue operations |
| `churn-prevention` | Cancel flow, save offers, dunning | Riduzione churn |
| `billing-automation` | Recurring payments, invoicing, dunning | Fatturazione automatica |
| `analytics-tracking` | GA4, events, conversion tracking | Misurazione performance |

---

## §5 — DESIGN & UI

### 5.1 Design System & Foundations

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `visual-design-foundations` | Typography, color theory, spacing systems | Fondamenti design |
| `design-system-patterns` | Design tokens, theming, component architecture | Sistemi design scalabili |
| `tailwind-design-system` | Tailwind v4 design tokens, component library | Design system Tailwind |
| `brand-guidelines` | Anthropic brand colors + typography | Applicare brand |
| `responsive-design` | Container queries, fluid typography, CSS Grid | Layout responsive |

### 5.2 UI Development

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `frontend-design` | UI production-grade, creative, polished | Interfacce web |
| `ui-ux-pro-max` | 50+ styles, 161 palettes, 57 font pairings | UI/UX design intelligence |
| `ckm-ui-styling` | shadcn/ui + Tailwind styling | Styling avanzato UI |
| `ckm-design` | Brand identity, design tokens, logo generation | Suite design completa |
| `ckm-brand` | Brand voice, visual identity, asset management | Gestione brand |
| `ckm-design-system` | Token architecture, component specs, slides | Architettura design system |
| `ckm-banner-design` | Banner per social/ads/web/print | Banner design |
| `ckm-slides` | HTML presentations con Chart.js | Presentazioni tecniche |
| `interaction-design` | Microinteractions, motion design, transitions | UX animata |
| `theme-factory` | 10 preset temi per artefatti HTML | Temi rapidi |

### 5.3 Mobile Design

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `mobile-ios-design` | HIG + SwiftUI patterns | Design iOS nativo |
| `mobile-android-design` | Material Design 3 + Jetpack Compose | Design Android |

### 5.4 Accessibility

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `accessibility-compliance` | WCAG 2.2, ARIA patterns, screen readers | Accessibilità |
| `wcag-audit-patterns` | Audit WCAG con testing automatico + manuale | Audit accessibilità |
| `screen-reader-testing` | VoiceOver, NVDA, JAWS testing | Test screen reader |

### 5.5 Design Tools

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `penpot-uiux-design` | UI/UX design in Penpot via MCP | Design in Penpot |
| `excalidraw-diagram-generator` | Diagrammi Excalidraw da descrizioni | Diagrammi veloci |
| `canvas-design` | Visual art in .png/.pdf | Poster, arte visiva |
| `algorithmic-art` | p5.js generative art, flow fields | Arte generativa |
| `web-design-guidelines` | Review UI compliance | Review design |
| `web-design-reviewer` | Visual inspection + fix design issues | Ispezione design |

---

## §6 — DATA & ANALYTICS

### 6.1 Database

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `postgresql-table-design` | Schema design PostgreSQL | Progettazione tabelle PG |
| `postgresql-optimization` | JSONB, array, full-text search, window functions | Ottimizzazione PG |
| `postgresql-code-review` | Code review PostgreSQL-specific | Review SQL PG |
| `sql-optimization-patterns` | Indexing, EXPLAIN, query tuning | Ottimizzazione SQL generico |
| `sql-optimization` | Query tuning + execution plan analysis | Performance SQL |
| `sql-code-review` | SQL injection prevention, access control | Review sicurezza SQL |
| `supabase` | Supabase Database, Auth, Edge Functions, Realtime | Full-stack Supabase |
| `supabase-postgres-best-practices` | PG optimization from Supabase | Performance PG Supabase |
| `cosmosdb-datamodeling` | NoSQL data modeling Cosmos DB | Design Cosmos DB |
| `ef-core` | Entity Framework Core best practices | ORM .NET |
| `database-migration` | Zero-downtime migration strategies | Migrazioni DB |

### 6.2 Data Pipeline & Engineering

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `dbt-transformation-patterns` | dbt model organization, testing, incremental | Analytics engineering |
| `airflow-dag-patterns` | Production Apache Airflow DAGs | Pipeline dati |
| `spark-optimization` | Partitioning, caching, shuffle, memory tuning | Performance Spark |
| `bigquery-pipeline-audit` | Audit cost safety, idempotency BQ | Review BigQuery |
| `ml-pipeline-workflow` | MLOps da data prep a deployment | Pipeline ML |

### 6.3 Business Intelligence

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `powerbi-modeling` | Power BI semantic modeling + measures | Modellazione Power BI |
| `power-bi-dax-optimization` | Performance DAX formulas | Ottimizzazione DAX |
| `power-bi-model-design-review` | Model architecture review | Review modello Power BI |
| `power-bi-performance-troubleshooting` | Diagnostica performance Power BI | Troubleshooting PBI |
| `power-bi-report-design-consultation` | Chart selection, layout, accessibility | Design report PBI |
| `kpi-dashboard-design` | Metrics selection, visualization, real-time | Dashboard KPI |
| `data-storytelling` | Narrative with data + visualization | Raccontare coi dati |
| `fabric-lakehouse` | Fabric Lakehouse features + best practices | Lakehouse Microsoft |

### 6.4 Data Analysis & Science

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `data-quality-frameworks` | Great Expectations, dbt tests, data contracts | Qualità dati |
| `datanalysis-credit-risk` | Credit risk data cleaning + variable screening | Analisi rischio credito |
| `market-sizing-analysis` | TAM/SAM/SOM calculation | Sizing mercato |
| `startup-financial-modeling` | 3-5 year financial models | Modelli finanziari |
| `startup-metrics-framework` | CAC, LTV, burn multiple, unit economics | Metriche startup |

### 6.5 Dataverse (Microsoft)

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `dataverse-python-quickstart` | Python SDK setup + CRUD + bulk | Quickstart Dataverse |
| `dataverse-python-production-code` | Error handling, optimization Dataverse | Codice production Dataverse |
| `dataverse-python-advanced-patterns` | Advanced patterns, optimization | Pattern avanzati Dataverse |
| `dataverse-python-usecase-builder` | Soluzioni complete per use case | Case d'uso Dataverse |

---

## §7 — SECURITY

### 7.1 Application Security

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `security-review` | AI-powered codebase security scanner | Audit sicurezza codice |
| `sast-configuration` | SAST tools setup, DevSecOps | Scanning automatico |
| `codeql` | CodeQL scanning via GitHub Actions | Analisi codice GitHub |
| `secret-scanning` | Secret scanning, push protection | Scansione segreti |
| `gdpr-compliant` | GDPR engineering practices | Compliance GDPR sviluppo |
| `gdpr-data-handling` | Consent management, data subject rights | Gestione dati GDPR |
| `pci-compliance` | PCI DSS per payment card data | Compliance pagamenti |
| `secure-linux-web-hosting` | Server hardening, Nginx, HTTPS, firewall | Hardening server |
| `openclaw-secure-linux-cloud` | Self-hosting OpenClaw sicuro | Deploy sicuro OpenClaw |

### 7.2 Threat Modeling

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `threat-model-analyst` | Full STRIDE-A threat model analysis | Analisi threat model |
| `stride-analysis-patterns` | STRIDE methodology application | Threat modeling session |
| `attack-tree-construction` | Attack trees per visualizzazione threat | Mappatura attacchi |
| `security-requirement-extraction` | Security requirements da threat models | Requisiti sicurezza |
| `threat-mitigation-mapping` | Security controls mapping | Piano remediation |

### 7.3 Blockchain & Web3 Security

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `solidity-security` | Smart contract security best practices | Audit contratti Solidity |
| `nft-standards` | ERC-721, ERC-1155, metadata, minting | Standard NFT |
| `defi-protocol-templates` | Staking, AMMs, governance, lending | Template DeFi |
| `web3-testing` | Hardhat + Foundry testing contracts | Test contratti |

### 7.4 Binary & Reverse Engineering

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `binary-analysis-patterns` | Disassembly, decompilation, control flow | Analisi binari |
| `anti-reversing-techniques` | Obfuscation, anti-debugging, packing | Reverse engineering |
| `protocol-reverse-engineering` | Packet analysis, protocol dissection | Reverse protocolli |
| `memory-forensics` | Volatility, memory acquisition, process analysis | Analisi memoria |

---

## §8 — MICROSOFT ECOSYSTEM

### 8.1 .NET / C# / F#

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `dotnet-backend-patterns` | .NET backend, DI, EF Core, Dapper | Sviluppo .NET |
| `dotnet-best-practices` | Code review .NET/C# best practices | Review codice .NET |
| `dotnet-design-pattern-review` | Design pattern review per .NET | Review pattern .NET |
| `dotnet-timezone` | TimeZoneInfo, NodaTime, DST handling | Fusi orari .NET |
| `dotnet-upgrade` | Framework upgrade analysis .NET | Migrazione .NET |
| `csharp-async` | C# async best practices | Async C# |
| `csharp-docs` | XML comments documentation C# | Documentazione C# |
| `ef-core` | Entity Framework Core patterns | ORM .NET |
| `nuget-manager` | Gestione pacchetti NuGet | Package .NET |
| `fluentui-blazor` | Fluent UI Blazor component library | UI Blazor |
| `aspire` | Aspire CLI, AppHost, orchestration, MCP | Distributed app .NET |
| `aspnet-minimal-api-openapi` | Minimal API + OpenAPI | API .NET minimali |

### 8.2 Azure

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `azure-architecture-autopilot` | Design Azure da linguaggio naturale | Progettazione cloud |
| `azure-deployment-preflight` | Preflight Bicep validation | Deploy sicuro |
| `azure-pricing` | Real-time pricing API | Stima costi |
| `azure-resource-health-diagnose` | Diagnosi health risorse | Troubleshooting |
| `azure-resource-visualizer` | Diagrammi da resource group | Visualizzazione |
| `azure-role-selector` | Role assignment least privilege | RBAC |
| `azure-static-web-apps` | SWA + Azure Functions | Static Web Apps |
| `az-cost-optimize` | Cost optimization + GitHub issues | Ottimizzazione costi |
| `azure-devops-cli` | Azure DevOps via CLI | Automazione DevOps |
| `appinsights-instrumentation` | Azure App Insights telemetry | Monitoring app |
| `import-infrastructure-as-code` | Terraform da risorse Azure esistenti | IaC reverse-engineer |

### 8.3 Microsoft 365 / Power Platform

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `declarative-agents` | M365 Copilot declarative agents | Agenti M365 |
| `typespec-create-agent` | TypeSpec declarative agent per Copilot | Agent TypeSpec |
| `typespec-create-api-plugin` | TypeSpec API plugin + Adaptive Cards | Plugin M365 |
| `typespec-api-operations` | GET/POST/PATCH/DELETE in TypeSpec | Operazioni API TypeSpec |
| `mcp-create-declarative-agent` | Declarative agent creation | Agenti dichiarativi |
| `mcp-create-adaptive-cards` | Adaptive Cards creation | Card M365 |
| `mcp-deploy-manage-agents` | Deploy e gestione agenti | Deploy agenti M365 |
| `mcp-copilot-studio-server-generator` | MCP server per Copilot Studio | MCP + Copilot Studio |

### 8.4 Power Platform

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `flowstudio-power-automate-mcp` | Interrogazione Power Automate via MCP | Power Automate API |
| `flowstudio-power-automate-build` | Build flow definitions | Creazione flow |
| `flowstudio-power-automate-debug` | Debug action-level failures | Debug flow |
| `flowstudio-power-automate-monitoring` | Flow health, failure rates | Monitoraggio flow |
| `flowstudio-power-automate-governance` | Classify, audit, compliance flow | Governance flow |
| `power-apps-code-app-scaffold` | Power Apps Code App scaffold | Setup Power Apps |
| `power-platform-mcp-connector-suite` | Custom connector + MCP integration | Connector Copilot Studio |

### 8.5 Copilot Development

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `mcp-copilot-studio-server-generator` | MCP server for Copilot Studio | Server per Copilot Studio |
| `gihub-copilot-starter` | Configurazione Copilot per progetto | Setup Copilot |
| `copilot-usage-metrics` | GitHub Copilot usage metrics | Metriche Copilot |
| `cli-mastery` | Training interattivo GitHub Copilot CLI | Imparare Copilot CLI |
| `noob-mode` | Plain English per Copilot CLI | Utenti non tecnici |
| `copilot-cli-quickstart` | Tutorial Copilot CLI da zero | Onboarding Copilot |

### 8.6 Windows Development

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `winapp-cli` | MSIX packaging, signing, Store publish | Pubblicazione Windows |
| `winmd-api-search` | Windows API discovery | API Windows |
| `winui3-migration-guide` | UWP → WinUI 3 migration | Migrazione WinUI |
| `msstore-cli` | Microsoft Store publishing CLI | Store publish |
| `electron` | Automazione app Electron (VS Code, Slack, etc.) | Desktop automation |

---

## §9 — PROJECT & DOCUMENTATION

### 9.1 Documentation

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `documentation-writer` | Diátaxis documentation framework | Documentazione software |
| `doc-coauthoring` | Structured workflow per co-authoring docs | Scrittura collaborativa |
| `create-readme` | README.md creation | README progetti |
| `create-llms` | llms.txt generation | Context per LLM |
| `update-llms` | Update llms.txt | Manutenzione llms.txt |
| `architecture-decision-records` | ADR writing best practices | Decisioni architetturali |
| `create-architectural-decision-record` | ADR document creation | ADR tools |
| `hads` | Human-AI Documentation Standard | Documentazione AI-friendly |
| `oo-component-documentation` | Object-oriented component docs | Documentazione componenti |
| `csharp-docs` | XML comments C# | .NET documentation |
| `java-docs` | Javadoc documentation | Java documentation |
| `add-educational-comments` | Educational code comments | Commenti formativi |
| `readme-i18n` | README translation multi-lingua | README multilingua |
| `mkdocs-translations` | Documentazione mkdocs multi-lingua | MkDocs i18n |

### 9.2 Specifications & Planning

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `create-specification` | Specification file per AI consumption | Specifiche AI |
| `update-specification` | Update spec con nuovi requisiti | Aggiornamento specifiche |
| `prd` | Product Requirements Documents | PRD per feature |
| `breakdown-epic-pm` | Epic PRD creation | PRD epiche |
| `breakdown-epic-arch` | Technical architecture per epic | Architettura epiche |
| `breakdown-feature-prd` | Feature PRD da epic | PRD feature |
| `breakdown-feature-implementation` | Feature implementation plan | Piani implementazione |
| `breakdown-plan` | Issue planning + automation | Pianificazione progetto |
| `breakdown-test` | Test planning + quality validation | Piani di test |
| `create-implementation-plan` | Implementation plan da nuovo | Piani implementazione |
| `update-implementation-plan` | Update implementation plan | Aggiornamento piani |
| `create-technical-spike` | Time-boxed technical spike | Ricerca tecnica |
| `writing-plans` | Plan da spec/requirements | Scrittura piani |

### 9.3 Project Execution

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `context-driven-development` | Project context artifacts (conductor/) | Setup contesto progetto |
| `context-map` | Mappa file rilevanti per task | Orientamento codice |
| `track-management` | Conductor tracks management | Work tracking |
| `workflow-patterns` | TDD workflow + phase checkpoints | Flusso di lavoro |
| `using-git-worktrees` | Git worktrees isolation | Lavoro isolato |
| `executing-plans` | Executing plans con review checkpoints | Esecuzione piani |
| `test-driven-development` | TDD: test prima del codice | Sviluppo TDD |
| `refactor-plan` | Multi-file refactor sequencing | Refactoring pianificato |
| `brainstorming` | Esplorazione requisiti prima di implementare | Ideazione feature |
| `first-ask` | Task refinement con input tools | Refinement task |
| `boost-prompt` | Prompt refinement workflow | Refinement prompt |

### 9.4 GitHub & Git

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `gh-cli` | GitHub CLI comprehensive reference | Comandi gh |
| `github-issues` | Create/update/manage issues via MCP | Issue management |
| `my-issues` | List my issues in repo | Issue personali |
| `my-pull-requests` | List my PRs in repo | PR personali |
| `gen-specs-as-issues` | Da code a issues strutturate | Generazione issue |
| `create-github-issue-feature-from-specification` | Feature issue da spec | Issue da specifiche |
| `create-github-issues-feature-from-implementation-plan` | Issues da piani | Issue da piani |
| `create-github-issues-for-unmet-specification-requirements` | Issues per requisiti non implementati | Gap analysis |
| `create-github-pull-request-from-specification` | PR da specification | PR da specifiche |
| `issue-fields-migration` | Labels → Issue fields migration | Migrazione metadata |
| `git-commit` | Conventional commit con analisi diff | Commit automatici |
| `conventional-commit` | Conventional commit format | Formato commit |
| `git-advanced-workflows` | Rebase, cherry-pick, bisect, worktrees | Git avanzato |
| `git-flow-branch-creator` | Git Flow branch creation | Branch Git Flow |
| `finishing-a-development-branch` | Decisione merge/PR/cleanup | Completamento branch |
| `make-repo-contribution` | Issue→branch→commits→PR workflow | Contribuzione repo |
| `changelog-automation` | Changelog da commit/PR/releases | Release notes |

### 9.5 Diagrams & Visuals

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `draw-io-diagram-generator` | .drawio file creation (mxGraph XML) | Diagrammi draw.io |
| `excalidraw-diagram-generator` | Excalidraw JSON diagrams | Diagrammi Excalidraw |
| `plantuml-ascii` | ASCII art diagrams (PlantUML text mode) | Diagrammi ASCII |
| `architecture-blueprint-generator` | Architecture documentation + diagrams | Blueprint architettura |
| `technology-stack-blueprint-generator` | Stack detection + visual diagrams | Blueprint stack |
| `folder-structure-blueprint-generator` | Folder structure analysis + diagram | Struttura cartelle |
| `project-workflow-analysis-blueprint-generator` | Workflow analysis + diagrams | Flussi applicativi |
| `code-exemplars-blueprint-generator` | Code exemplars scan + standards | Esempi codice |

---

## §10 — SYSTEMS & OPS

### 10.1 Linux Distro Triage

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `arch-linux-triage` | Pacman, systemd, rolling-release | Arch Linux issues |
| `debian-linux-triage` | Apt, systemd, AppArmor | Debian issues |
| `fedora-linux-triage` | Dnf, systemd, SELinux | Fedora issues |
| `centos-linux-triage` | RHEL-compatible, firewalld, SELinux | CentOS issues |

### 10.2 Scripting & Automazione

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `bash-defensive-patterns` | Bash production-grade scripting | Script shell robusti |
| `shellcheck-configuration` | ShellCheck static analysis | Quality shell script |
| `bats-testing-patterns` | Bash Automated Testing System | Test shell script |
| `uv-package-manager` | Python uv: fast package management | Python dependencies uv |
| `transform_data` | Trasformazione dati via script sandbox | Elaborazione dati |
| `script_sandbox` | Quick inline diagnostics sandboxed | Diagnostica rapida |

### 10.3 Networking

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `hybrid-cloud-networking` | VPN, dedicated connections | Rete ibrida |
| `geofeed-tuner` | IP geolocation feeds RFC 8805 | Geolocalizzazione IP |
| `secure-linux-web-hosting` | DNS, SSH, Nginx, HTTPS, Let's Encrypt | Hosting web sicuro |

### 10.4 Self-hosting & Deploy

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `deploy-to-vercel` | Deploy app/siti su Vercel | Deploy Vercel |
| `vercel-cli-with-tokens` | Vercel CLI con token auth | CLI Vercel |
| `publish-to-pages` | GitHub Pages publish da PPTX/PDF/HTML | Pubblicazione Pages |
| `containerize-aspnetcore` | Dockerfile per ASP.NET Core | Container .NET |
| `containerize-aspnet-framework` | Dockerfile per ASP.NET .NET Framework | Container .NET Framework |

---

## §11 — BUSINESS & FINANCE

### 11.1 Startup & Fundraising

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `startup-financial-modeling` | 3-5 year projections, burn rate | Modelli finanziari |
| `startup-metrics-framework` | CAC, LTV, burn multiple, ARR | Metriche startup |
| `market-sizing-analysis` | TAM/SAM/SOM calculation | Sizing mercato |
| `competitive-landscape` | Porter, Blue Ocean, positioning | Analisi competitor |
| `team-composition-analysis` | Hiring plan, compensation, equity equity | Team building |

### 11.2 Legal & HR

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `employment-contract-templates` | Employment contracts, offer letters | Contratti lavoro |
| `internal-comms` | Internal communications templates | Comunicazioni interne |

### 11.3 Revenue

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `pricing-strategy` | Pricing tiers, freemium, packaging | Strategia prezzo |
| `billing-automation` | Recurring payments, invoicing, dunning | Fatturazione |
| `churn-prevention` | Cancel flow, save offers, recovery | Riduzione churn |

---

## §12 — CRAFT AGENT META (Funzionamento di Craft Agent stesso)

### 12.1 Skill Management

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `find-skills` | Cerca skill disponibili per task | "C'è una skill per X?" |
| `skill-creator` | Create/edit/optimize skills | Nuove skill |
| `writing-skills` | Create/edit/verify skills | Scrittura skill |
| `make-skill-template` | Scaffold SKILL.md + directory | Template skill |
| `skills-cli` | Install, list, check, update skills | CLI skills |
| `microsoft-skill-creator` | Create skill per tecnologie Microsoft | Skill Microsoft |
| `evaluation-methodology` | PluginEval quality methodology | Valutazione qualità skill |
| `suggest-awesome-github-copilot-agents` | Suggerisci agent files da awesome-copilot | Scoperta agent |
| `suggest-awesome-github-copilot-instructions` | Suggerisci instruction files | Scoperta istruzioni |
| `suggest-awesome-github-copilot-skills` | Suggerisci skill files | Scoperta skill |

### 12.2 Prompt Engineering for Craft

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `prompt-builder` | Guida alla creazione prompt Copilot | Scrittura prompt |
| `finalize-agent-prompt` | Polishing prompt per end user | Finalizzare prompt |
| `create-agentsmd` | Generazione AGENTS.md | File AGENTS.md |
| `create-llms` | llms.txt creation | Context per LLM |
| `hads` | Human-AI Documentation Standard | Documentazione AI |
| `copilot-instructions-blueprint-generator` | Genera copilot-instructions.md da pattern | Istruzioni Copilot |

### 12.3 Memory & Handoff

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `remember` | Memory instructions da lezioni apprese | Salvataggio conoscenza |
| `memory-merger` | Merge domain memory → instruction file | Consolidamento memoria |
| `from-the-other-side-vega` | AI partnership patterns | Relazione AI umana |

### 12.4 Multi-Agent Orchestration

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `subagent-driven-development` | Execute plans with sub-agents | Implementazione multi-agente |
| `dispatching-parallel-agents` | 2+ tasks indipendenti in parallelo | Task paralleli |
| `parallel-feature-development` | File ownership, conflict avoidance | Sviluppo feature parallelo |
| `task-coordination-strategies` | Dependency graphs, workload balancing | Coordinamento task |
| `team-composition-patterns` | Agent team design + presets | Composizione team |
| `team-communication-protocols` | Messaging protocols for agent teams | Comunicazione team |
| `structured-autonomy-plan` | Structured Autonomy Planning | Pianificazione autonoma |
| `structured-autonomy-implement` | Structured Autonomy Implementation | Implementazione autonoma |
| `structured-autonomy-generate` | Structured Autonomy Generation | Generazione autonoma |

### 12.5 Verification & Quality

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `verification-before-completion` | Run verification before claiming done | Verifica completamento |
| `systematic-debugging` | Debug process prima di fix | Debug sistematico |
| `parallel-debugging` | Competing hypotheses parallel investigation | Debug complesso |
| `doublecheck` | 3-layer verification pipeline | Fact-checking AI |
| `receiving-code-review` | Ricevere feedback code review | Rispondere a review |
| `requesting-code-review` | Richiedere code review prima del merge | Richiesta review |
| `code-review-excellence` | Effective code review practices | Revisione codice |
| `multi-reviewer-patterns` | Parallel code reviews multi-dimensione | Review multiple |
| `review-and-refactor` | Review + refactor su codice esistente | Manutenzione codice |

---

## §13 — TESTING & QA

### 13.1 Testing Frameworks

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `javascript-testing-patterns` | Jest, Vitest, Testing Library | Test JS/TS |
| `javascript-typescript-jest` | Jest best practices + mocking | Jest specifico |
| `python-testing-patterns` | pytest, fixtures, mocking, TDD | Test Python |
| `pytest-coverage` | Run pytest + coverage al 100% | Coverage Python |
| `csharp-mstest` | MSTest 3.x/4.x unit testing | Test .NET MSTest |
| `csharp-xunit` | xUnit best practices | Test .NET xUnit |
| `csharp-nunit` | NUnit data-driven tests | Test .NET NUnit |
| `csharp-tunit` | TUnit testing patterns | Test .NET TUnit |
| `java-junit` | JUnit 5 data-driven tests | Test Java |
| `spring-boot-testing` | Spring Boot 4 testing + JUnit 6 | Test Spring Boot |
| `unit-test-vue-pinia` | Vue 3 + Vitest + Pinia testing | Test Vue |
| `vue-testing-best-practices` | Vitest, VUT, Playwright per Vue | Test Vue completo |

### 13.2 E2E & Browser Testing

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `e2e-testing-patterns` | Playwright + Cypress | Test E2E |
| `playwright-explore-website` | Website exploration via Playwright | Esplorazione sito |
| `playwright-generate-test` | Genera test Playwright da scenario | Creazione test |
| `playwright-automation-fill-in-form` | Form filling automation | Compilazione form |
| `webapp-testing` | Playwright per app locali | Test app locali |
| `scoutqa-test` | Automated QA testing | Testing automatico |

### 13.3 Polyglot & Specialized Testing

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `polyglot-test-agent` | Unit tests multi-linguaggio | Test qualsiasi linguaggio |
| `e2e-testing-patterns` | Cross-browser E2E testing | Test cross-browser |
| `temporal-python-testing` | Test Temporal workflows | Workflow Temporal |
| `web3-testing` | Hardhat + Foundry smart contract test | Test blockchain |

### 13.4 Quality Playbook

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `quality-playbook` | 6 quality artifacts from codebase | Sistema qualità completo |
| `ruff-recursive-fix` | Ruff checks + autofix iterativo | Linting Python |
| `shellcheck-configuration` | ShellCheck per script bash | Linting shell |

---

## §14 — SPECIALIZED

### 14.1 Oracle → PostgreSQL Migration

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `creating-oracle-to-postgres-master-migration-plan` | Migration plan orchestrale | Pianificazione migrazione |
| `creating-oracle-to-postgres-migration-bug-report` | Bug report migrazione | Bug migration |
| `creating-oracle-to-postgres-migration-integration-tests` | xUnit tests per migrazione | Test migrazione |
| `reviewing-oracle-to-postgres-migration` | Risk identification migration | Review migrazione |
| `migrating-oracle-to-postgres-stored-procedures` | PL/SQL → PL/pgSQL translation | Stored proc migration |
| `planning-oracle-to-postgres-migration-integration-testing` | Test plan per migrazione | Piano test migrazione |
| `scaffolding-oracle-to-postgres-migration-test-project` | Scaffold test project | Setup test migrazione |

### 14.2 Salesforce

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `salesforce-apex-quality` | Apex bulk-safety, CRUD/FLS, SOQL security | Qualità Apex |
| `salesforce-component-standards` | LWC, Aura, Visualforce quality + SLDS 2 | Componenti Salesforce |
| `salesforce-flow-design` | Flow type selection, bulk safety, fault handling | Flow Salesforce |

### 14.3 Convex

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `convex-quickstart` | Nuovo progetto Convex da 0 | Setup Convex |
| `convex-setup-auth` | Autenticazione Convex (Clerk, Auth0, etc.) | Auth Convex |
| `convex-create-component` | Componenti Convex con tabelle isolate | Componenti Convex |
| `convex-migration-helper` | Schema migration Convex widen-migrate-narrow | Migrazione Convex |
| `convex-performance-audit` | Audit performance Convex | Ottimizzazione Convex |

### 14.4 Better Auth

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `better-auth-best-practices` | Better Auth setup, DB adapters, OAuth | Auth con Better Auth |
| `create-auth-skill` | Scaffold authentication con Better Auth | Setup autenticazione |
| `email-and-password-best-practices` | Email verification, password reset | Email/password auth |
| `two-factor-authentication-best-practices` | TOTP, backup codes, 2FA flow | 2FA Better Auth |
| `organization-best-practices` | Multi-tenant org, teams, RBAC | Organizzazioni Better Auth |

### 14.5 Power BI

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `powerbi-modeling` | Semantic modeling + measures | Modellazione PBI |
| `power-bi-dax-optimization` | DAX performance optimization | Ottimizzazione DAX |
| `power-bi-model-design-review` | Model architecture review | Review model PBI |
| `power-bi-performance-troubleshooting` | Diagnostica performance PBI | Troubleshooting PBI |
| `power-bi-report-design-consultation` | Visualization + layout | Design report PBI |

### 14.6 Snowflake

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `snowflake-semanticview` | Semantic views via Snowflake CLI | Semantic layer Snowflake |

### 14.7 Postgres

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `postgresql-table-design` | Schema design PostgreSQL | Design tabelle PG |
| `postgresql-optimization` | JSONB, array, full-text search | Ottimizzazione PG |
| `postgresql-code-review` | Code review PostgreSQL | Review PG |

### 14.8 Vercel

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `vercel-composition-patterns` | React composition patterns | Pattern componenti React |
| `vercel-react-best-practices` | React/Next.js performance optimization | Performance Vercel |
| `vercel-react-native-skills` | React Native best practices | Mobile Vercel |
| `vercel-react-view-transitions` | View Transition API per React | Transizioni React |
| `vercel-sandbox` | Browser automation in Vercel Sandbox | Sandbox Vercel |

### 14.9 Game Development

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `game-engine` | HTML5 Canvas/WebGL game engine | Browser games |
| `godot-gdscript-patterns` | Godot 4 GDScript patterns | Game dev Godot |
| `unity-ecs-patterns` | Unity ECS + DOTS + Burst | Game dev Unity |

### 14.10 WordPress (via browser)

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| * Usa `agent-browser` per automatizzare WordPress | Automazione WP | Interazione col browser |

---

## §15 — CONTENT & MEDIA

### 15.1 Document & File Formats

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `docx` | Creare/leggere/modificare Word .docx | Documenti Word |
| `pptx` | Presentazioni PowerPoint .pptx | Slide deck |
| `xlsx` | Spreadsheet .xlsx/.csv da/a dati | Fogli di calcolo |
| `pdf` | Leggere/combinare/creare PDF | Documenti PDF |
| `pdftk-server` | Manipolazione PDF via CLI (merge, split, encrypt) | Operazioni PDF batch |
| `markdown-to-html` | Conversione Markdown → HTML | Documentazione web |
| `shuffle-json-data` | Shuffle dati JSON in modo sicuro | Randomizzazione dati |
| `convert-plaintext-to-md` | Testo → Markdown | Conversione format |

### 15.2 Email

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `email-drafter` | Draft email nello stile dell'utente | Scrittura email personale |
| `email-sequence` | Drip campaign, onboarding, lifecycle | Sequenze email marketing |
| `cold-email` | B2B cold outreach + follow-up | Email di prospezione |
| `email-and-password-best-practices` | Email verification flows | Verifica email auth |

### 15.3 Media Processing

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `transloadit-media-processing` | Video/audio/image/document processing | Elaborazione media |
| `image-manipulation-image-magick` | ImageMagick processing (resize, convert) | Manipolazione immagini |
| `slack-gif-creator` | GIF animate ottimizzate per Slack | GIF per Slack |
| `nano-banana-pro-openrouter` | Gemini 3 Pro Image generation via OpenRouter | Generazione immagini AI |

### 15.4 Blog & Content

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `content-strategy` | Content planning, topics, cluster | Strategia contenuti |
| `copywriting` | Marketing/web copy writing | Scrittura copy |
| `social-content` | Post per LinkedIn, Twitter, Instagram | Contenuti social |
| `programmatic-seo` | SEO pages at scale | SEO scalabile |
| `lead-magnets` | Ebook, checklist, template | Content offer |

---

## §16 — GAMING & REVERSE ENGINEERING

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `game-engine` | HTML5 Canvas/WebGL games | Giochi browser |
| `godot-gdscript-patterns` | Godot 4 patterns | Sviluppo Godot |
| `unity-ecs-patterns` | Unity ECS + DOTS | Sviluppo Unity |
| `binary-analysis-patterns` | Disassembly, decompilation | Analisi binari |
| `anti-reversing-techniques` | Obfuscation, anti-debugging | Reverse engineering |
| `memory-forensics` | Volatility, memory acquisition | Forensics memoria |
| `protocol-reverse-engineering` | Packet analysis, protocol dissection | Reverse protocolli |
| `legacy-circuit-mockups` | Breadboard circuit mockups (6502) | Circuiti retro |
| `algorithmic-art` | Generative art p5.js | Arte generativa |

---

## §17 — UTILITY

### 17.1 Productivity & Automation

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `automate-this` | Analizza screen recording → script automazione | Automazione processi |
| `autoresearch` | Iterative experimentation loop | Miglioramento autonomo |
| `daily-prep` | Preparazione giornaliera da calendario + task | Prep giornaliero |
| `roundup` | Status briefing personalizzati | Status report |
| `roundup-setup` | Setup roundup con stile comunicazione | Configurazione roundup |
| `meeting-minutes` | Generazione verbali riunione | Verbali meeting |
| `dogfood` | Esplorazione sistematica per bug | QA esplorativo |
| `napkin` | Whiteboard collaborativa via browser | Schizzi e lavagne |

### 17.2 Browser Automation

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `agent-browser` | Browser automation CLI | Automazione web generica |
| `agentcore` | AWS Bedrock AgentCore cloud browser | Cloud browser AWS |
| `chrome-devtools` | Chrome DevTools MCP debugging | Debug browser |
| `electron` | Automazione app Electron | Desktop apps |
| `use-my-browser` | Usa sessione browser utente live | Pagine logged-in |
| `slack` | Interazione Slack via browser automazione | Automazione Slack |
| `develop-userscripts` | Tampermonkey/ScriptCat userscripts | Script browser |

### 17.3 Onboarding & Setup

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `noob-mode` | Plain English per comandi tecnici | Utenti non tecnici |
| `coilot-cli-quickstart` | Tutorial da zero Copilot CLI | Apprendimento CLI |
| `what-context-needed` | Chiede quali file servono | Context discovery |
| `onboard-context-matic` | Interactive tour context-matic MCP | Onboarding MCP |

### 17.4 Environment & Config

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `sandbox-npm-install` | npm install in Docker sandbox | Installazione pacchetti |
| `tzst` | .tzst/.tar.zst archive management | Archivi compressi |
| `xdrop` | File sharing via Xdrop | Condivisione file |
| `xget` | URL rewriting, registry acceleration | Accelerazione download |
| `block-no-verify-hook` | PreToolUse hook per git --no-verify | Protezione commit |

### 17.5 Language & Localization

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `finnish-humanizer` | Remove AI markers da testo finlandese | Umanizzazione testo FI |
| `mkdocs-translations` | Language translation per mkdocs | Traduzione docs |
| `readme-i18n` | README multilingual | README tradotto |
| `next-intl-add-language` | Aggiunge lingua a next-intl | i18n Next.js |

### 17.6 Writing & Editing

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `copy-editing` | Edit/review/refresh copy esistente | Editing copy |
| `refactor` | Surgical code refactoring | Refactoring codice |
| `refactor-plan` | Multi-file refactor sequencing | Refactoring pianificato |
| `review-and-refactor` | Review + refactor | Manutenzione codice |
| `quasi-coder` | Interpreta pseudo-codice e shorthand | Implementazione da descrizioni |

### 17.7 AI Models & Usage

| Skill | Cosa fa | Quando usarla |
|-------|---------|---------------|
| `model-recommendation` | Raccomanda modello AI per task | Selezione modello |
| `running-claude-code-via-litellm-copilot` | Claude Code via LiteLLM proxy | Routing modelli |
| `copilot-usage-metrics` | Metriche d'uso GitHub Copilot | Reporting utilizzo |
| `sponsor-finder` | Trova dependency Sponsorable su GitHub | Funding OSS |
| `opensource-guide-coach` | Guida progetto open source | Open source |

---

## Strategia d'Uso: Come Scegliere la Skill Giusta

### 1. Usa la Tassonomia a 3 Livelli

```
DOMINIO → CATEGORIA → SKILL

Esempio:
§4 GO-TO-MARKET → 4.1 Content & Copywriting → copywriting
§1 DEV ENGINEERING → 1.2 Backend Framework → fastapi-templates
```

### 2. Pattern di Ricerca Rapida

Quando non sai quale skill usare:

```
"Cosa devo fare?"                  → Usa find-skills (cerca per keyword)
"Voglio ottimizzare X"             → Cerca X nella mappa sopra
"C'è una skill per Y?"             → find-skills + grep
"Devo creare un nuovo server..."   → Cerca MCP server generator §1.6
"Devo deployare..."                → §2.2 CI/CD + §2.4 Cloud
```

### 3. Skills Generali Sempre Utili (Prima di Partire)

| Ordine | Skill | Perché |
|--------|-------|--------|
| 1 | `brainstorming` | Esplora requisiti PRIMA di scrivere codice |
| 2 | `context-map` | Mappa tutti i file rilevanti |
| 3 | `writing-plans` | Crea piano da specifiche |
| 4 | `context-driven-development` | Setup contesto progetto |
| 5 | `verification-before-completion` | Verifica prima di dichiarare fatto |

### 4. Skills per Fasi del Progetto

```
IDEAZIONE:    brainstorming → first-ask → product-marketing-context
PLAN:         writing-plans → prd → breakdown-plan → architecture-decision-records
IMPLEMENTAZIONE: executiing-plans → test-driven-development → refactor-plan
TEST:         polyglot-test-agent → e2e-testing-patterns → verification-before-completion
REVIEW:       requesting-code-review → code-review-excellence → security-review
DOCS:         documentation-writer → create-readme → create-llms → architecture-blueprint-generator
RELEASE:      changelog-automation → deploy-to-vercel → launch-strategy
```

### 5. Skills per Stack Tecnologico

| Stack | Skills Consigliate |
|-------|-------------------|
| **Python** | python-code-style, python-design-patterns, python-testing-patterns, python-type-safety, fastapi-templates, uv-package-manager, ruff-recursive-fix |
| **TypeScript/React** | modern-javascript-patterns, typescript-advanced-types, react-state-management, nextjs-app-router-patterns, vercel-react-best-practices, shadcn |
| **Vue 3** | vue-best-practices, vue-router-best-practices, vue-pinia-best-practices, vue-testing-best-practices, vue-debug-guides |
| **.NET/C#** | dotnet-backend-patterns, dotnet-best-practices, csharp-async, ef-core, nuget-manager, aspire, fluentui-blazor |
| **Java** | java-springboot, java-junit, java-docs, java-mcp-server-generator, spring-boot-testing |
| **Go** | go-concurrency-patterns, go-mcp-server-generator |
| **Rust** | rust-async-patterns, memory-safety-patterns, rust-mcp-server-generator |
| **Mobile** | expo-module, react-native-architecture, building-native-ui, mobile-ios-design, mobile-android-design |
| **Azure** | azure-architecture-autopilot, azure-deployment-preflight, azure-pricing, azure-resource-visualizer |
| **AI/LLM** | prompt-engineering-patterns, rag-implementation, arize-instrumentation, eval-driven-dev, tavily-research |
| **Salesforce** | salesforce-apex-quality, salesforce-component-standards, salesforce-flow-design |
| **Power Platform** | flowstudio-power-automate-mcp, power-platform-mcp-connector-suite, declarative-agents |

### 6. Comandi Rapidi per Trovare una Skill

```bash
# Cerca per keyword in tutte le skill
ls ~/.agents/skills/ | grep -i "docker\|k8s\|deploy"

# Vedi la descrizione di una skill (prime righe del SKILL.md)
head -20 ~/.agents/skills/<skill>/SKILL.md

# Cerca contenuto nelle skill
grep -r "webhook\|stripe\|payment" ~/.agents/skills/*/SKILL.md
```

---

## Indice Alfabetico (Completo, 580 Skill)

```
A
├── ab-test-setup                               §4.3
├── accessibility-compliance                    §5.4
├── ad-creative                                 §4.1
├── add-educational-comments                    §9.1
├── agent-browser                               §17.2
├── agent-governance                            §3.6
├── agent-owasp-compliance                      §3.6
├── agent-supply-chain                          §3.6
├── agentcore                                   §17.2
├── agentic-eval                                §3.1
├── ai-prompt-engineering-safety-review          §3.6
├── ai-seo                                      §4.2
├── airflow-dag-patterns                        §6.2
├── algorithmic-art                             §16
├── analytics-tracking                          §4.4
├── angular-migration                           §1.8
├── anti-reversing-techniques                   §16
├── api-design-principles                       §1.2
├── appinsights-instrumentation                 §8.2
├── apple-appstore-reviewer                     (Apple)
├── arch-linux-triage                           §10.1
├── architecture-blueprint-generator            §9.5
├── architecture-decision-records               §9.1
├── architecture-patterns                       §1.1
├── arize-ai-provider-integration               §3.3
├── arize-annotation                            §3.3
├── arize-dataset                               §3.3
├── arize-evaluator                             §3.3
├── arize-experiment                            §3.3
├── arize-instrumentation                       §3.3
├── arize-link                                  §3.3
├── arize-prompt-optimization                   §3.3
├── arize-trace                                 §3.3
├── aspire                                      §8.1
├── aspnet-minimal-api-openapi                  §1.2
├── async-python-patterns                       §1.1
├── attack-tree-construction                    §7.2
├── auth-implementation-patterns                §1.1
├── automate-this                               §17.1
├── autoresearch                                §17.1
├── aws-cdk-python-setup                        §2.4
├── az-cost-optimize                            §2.5/§8.2
├── azure-architecture-autopilot                §2.5/§8.2
├── azure-deployment-preflight                  §2.5/§8.2
├── azure-devops-cli                            §2.5/§8.2
├── azure-pricing                               §2.5/§8.2
├── azure-resource-health-diagnose              §2.5/§8.2
├── azure-resource-visualizer                   §2.5/§8.2
├── azure-role-selector                         §2.5/§8.2
├── azure-static-web-apps                       §2.5/§8.2

B
├── backtesting-frameworks                      §6.4
├── bash-defensive-patterns                     §10.2
├── bats-testing-patterns                       §10.2
├── bazel-build-optimization                    §1.5
├── better-auth-best-practices                  §14.4
├── better-auth-security-best-practices         §14.4
├── bigquery-pipeline-audit                     §6.2
├── billing-automation                          §4.8/§11.3
├── binary-analysis-patterns                    §16
├── block-no-verify-hook                        §17.4
├── boost-prompt                                §9.3
├── brainstorming                               §9.3
├── brand-guidelines                            §5.1
├── breakdown-epic-arch                         §9.2
├── breakdown-epic-pm                           §9.2
├── breakdown-feature-implementation            §9.2
├── breakdown-feature-prd                       §9.2
├── breakdown-plan                              §9.2
├── breakdown-test                              §9.2
├── building-native-ui                          §1.4

C
├── canvas-design                               §5.5
├── centos-linux-triage                         §10.1
├── changelog-automation                        §9.4
├── chrome-devtools                             §17.2
├── churn-prevention                            §4.8/§11.3
├── ckm-banner-design                           §5.2
├── ckm-brand                                   §5.2
├── ckm-design                                  §5.2
├── ckm-design-system                           §5.2
├── ckm-slides                                  §5.2
├── ckm-ui-styling                              §5.2
├── cli-mastery                                 §8.5
├── cloud-design-patterns                       §1.1
├── code-exemplars-blueprint-generator          §9.5
├── code-review-excellence                      §12.5
├── codeql                                      §2.2/§7.1
├── cold-email                                  §4.1/§15.2
├── comment-code-generate-a-tutorial            §9.1
├── competitive-landscape                       §4.5/§11.1
├── competitor-alternatives                     §4.2/§4.6
├── containerize-aspnet-framework               §10.4
├── containerize-aspnetcore                     §10.4
├── content-strategy                            §4.1/§15.4
├── context-driven-development                  §9.3
├── context-map                                 §9.3
├── conventional-commit                         §9.4
├── convert-plaintext-to-md                     §15.1
├── convex-create-component                     §14.3
├── convex-migration-helper                     §14.3
├── convex-performance-audit                    §14.3
├── convex-quickstart                           §14.3
├── convex-setup-auth                           §14.3
├── copilot-cli-quickstart                      §8.5/§17.3
├── copilot-instructions-blueprint-generator    §12.2
├── copilot-sdk                                 §3.2
├── copilot-spaces                              §3.2
├── copilot-usage-metrics                       §8.5/§17.7
├── copy-editing                                §4.1/§17.6
├── copywriting                                 §4.1
├── cosmosdb-datamodeling                       §6.1
├── cost-optimization                           §2.4
├── cqrs-implementation                         §1.2
├── create-adaptable-composable                 §1.3
├── create-agentsmd                             §12.2
├── create-architectural-decision-record        §9.1
├── create-auth-skill                           §14.4
├── create-github-action-workflow-specification §9.2
├── create-github-issue-feature-from-specification  §9.4
├── create-github-issues-feature-from-implementation-plan  §9.4
├── create-github-issues-for-unmet-specification-requirements  §9.4
├── create-github-pull-request-from-specification  §9.4
├── create-implementation-plan                  §9.2
├── create-llms                                 §9.1/§12.2
├── create-readme                               §9.1
├── create-specification                        §9.2
├── create-spring-boot-java-project             §1.2
├── create-spring-boot-kotlin-project           §1.2
├── create-technical-spike                      §9.2
├── create-tldr-page                            §9.1
├── creating-oracle-to-postgres-master-migration-plan  §14.1
├── creating-oracle-to-postgres-migration-bug-report   §14.1
├── creating-oracle-to-postgres-migration-integration-tests  §14.1
├── csharp-async                                §1.1/§8.1
├── csharp-docs                                 §9.1/§8.1
├── csharp-mcp-server-generator                 §1.6/§8.1
├── csharp-mstest                               §13.1
├── csharp-nunit                                §13.1
├── csharp-tunit                                §13.1
├── csharp-xunit                                §13.1
├── customer-research                           §4.6

D
├── daily-prep                                  §17.1
├── data-quality-frameworks                     §6.4
├── data-storytelling                           §6.3
├── database-migration                          §1.8
├── datanalysis-credit-risk                     §6.4
├── dataverse-python-advanced-patterns          §6.5
├── dataverse-python-production-code            §6.5
├── dataverse-python-quickstart                 §6.5
├── dataverse-python-usecase-builder            §6.5
├── dbt-transformation-patterns                 §6.2
├── debian-linux-triage                         §10.1
├── debugging-strategies                        §1.1
├── declarative-agents                          §3.2/§8.3
├── defi-protocol-templates                     §7.3
├── dependabot                                  §2.2
├── dependency-upgrade                          §1.8
├── deploy-to-vercel                            §10.4
├── deployment-pipeline-design                  §2.2
├── design-system-patterns                      §5.1
├── develop-userscripts                         §17.2
├── devops-rollout-plan                         §2.2
├── dispatching-parallel-agents                 §12.4
├── distributed-tracing                         §2.6
├── doc-coauthoring                             §9.1
├── documentation-writer                        §9.1
├── docx                                        §15.1
├── dogfood                                     §17.1
├── dotnet-backend-patterns                     §1.2/§8.1
├── dotnet-best-practices                       §8.1
├── dotnet-design-pattern-review                §8.1
├── dotnet-timezone                             §8.1
├── dotnet-upgrade                              §1.8/§8.1
├── doublecheck                                 §12.5
├── draw-io-diagram-generator                   §9.5

E
├── e2e-testing-patterns                        §1.3/§13.2
├── editorconfig                                §17.4
├── ef-core                                     §6.1/§8.1
├── electron                                    §8.6/§17.2
├── email-and-password-best-practices           §14.4/§15.2
├── email-drafter                               §15.2
├── email-sequence                              §4.1/§15.2
├── embedding-strategies                        §3.1
├── employment-contract-templates               §11.2
├── entra-agent-user                            §8.3
├── error-handling-patterns                     §1.1
├── eval-driven-dev                             §3.1
├── evaluation-methodology                      §12.1
├── event-store-design                          §1.2
├── excalidraw-diagram-generator                §5.5/§9.5
├── executing-plans                             §9.3
├── expo-api-routes                             §1.4
├── expo-cicd-workflows                         §1.4
├── expo-deployment                             §1.4
├── expo-dev-client                             §1.4
├── expo-module                                 §1.4
├── expo-tailwind-setup                         §1.4

F
├── fabric-lakehouse                            §6.3
├── fastapi-templates                           §1.2
├── fedora-linux-triage                         §10.1
├── finalize-agent-prompt                       §12.2
├── find-skills                                 §12.1
├── finishing-a-development-branch              §9.4
├── finnish-humanizer                           §17.5
├── first-ask                                   §9.3
├── flowstudio-power-automate-build             §8.4
├── flowstudio-power-automate-debug             §8.4
├── flowstudio-power-automate-governance        §8.4
├── flowstudio-power-automate-mcp               §8.4
├── flowstudio-power-automate-monitoring        §8.4
├── fluentui-blazor                             §8.1
├── folder-structure-blueprint-generator        §9.5
├── form-cro                                    §4.3
├── free-tool-strategy                          §4.5
├── from-the-other-side-vega                    §12.3
├── frontend-design                             §5.2

G
├── game-engine                                 §16
├── gdpr-compliant                              §7.1
├── gdpr-data-handling                          §7.1
├── gen-specs-as-issues                         §9.4
├── generate-custom-instructions-from-codebase  §12.2
├── geofeed-tuner                               §10.3
├── gh-cli                                      §9.4
├── git-advanced-workflows                      §9.4
├── git-commit                                  §9.4
├── git-flow-branch-creator                     §9.4
├── github-actions-docs                         §2.2
├── github-actions-templates                    §2.2
├── github-copilot-starter                      §8.5
├── github-issues                               §9.4
├── gitlab-ci-patterns                          §2.2
├── gitops-workflow                             §2.1
├── go-concurrency-patterns                     §1.1
├── go-mcp-server-generator                     §1.6
├── godot-gdscript-patterns                     §16
├── grafana-dashboards                          §2.6
├── gtm-0-to-1-launch                           §4.7
├── gtm-ai-gtm                                  §4.7
├── gtm-board-and-investor-communication        §4.7
├── gtm-developer-ecosystem                     §4.7
├── gtm-enterprise-account-planning             §4.7
├── gtm-enterprise-onboarding                   §4.7
├── gtm-operating-cadence                       §4.7
├── gtm-partnership-architecture                §4.7
├── gtm-positioning-strategy                    §4.7
├── gtm-product-led-growth                      §4.7
├── gtm-technical-product-pricing               §4.7

H
├── hads                                        §9.1/§12.2
├── helm-chart-scaffolding                      §2.1
├── hybrid-cloud-networking                     §2.4/§10.3
├── hybrid-search-implementation                §3.1

I
├── image-manipulation-image-magick             §15.3
├── import-infrastructure-as-code               §2.3/§8.2
├── incident-runbook-templates                  §2.6
├── integrate-context-matic                     §1.7
├── interaction-design                          §5.2
├── internal-comms                              §11.2
├── issue-fields-migration                      §9.4
├── istio-traffic-management                    §2.1

J
├── java-add-graalvm-native-image-support       §1.2
├── java-docs                                   §9.1
├── java-junit                                  §13.1
├── java-mcp-server-generator                   §1.6
├── java-refactoring-extract-method             §1.1
├── java-refactoring-remove-parameter           §1.1
├── java-springboot                             §1.2
├── javascript-testing-patterns                 §13.1
├── javascript-typescript-jest                  §13.1

K
├── k8s-manifest-generator                      §2.1
├── k8s-security-policies                       §2.1
├── kotlin-mcp-server-generator                 §1.6
├── kotlin-springboot                           §1.2
├── kpi-dashboard-design                        §6.3

L
├── langchain-architecture                      §3.1
├── launch-strategy                             §4.5
├── lead-magnets                                §4.5
├── legacy-circuit-mockups                      §16
├── linkerd-patterns                            §2.1
├── llm-evaluation                              §3.1

M
├── make-repo-contribution                      §9.4
├── make-skill-template                         §12.1
├── markdown-to-html                            §15.1
├── market-sizing-analysis                      §6.4/§11.1
├── marketing-ideas                             §4.5
├── marketing-psychology                        §4.5
├── mcp-builder                                 §1.6
├── mcp-cli                                     §1.6
├── mcp-copilot-studio-server-generator         §1.6/§8.3
├── mcp-create-adaptive-cards                   §8.3
├── mcp-create-declarative-agent                §8.3
├── mcp-deploy-manage-agents                    §8.3
├── mcp-security-audit                          §1.6
├── meeting-minutes                             §17.1
├── memory-forensics                            §16
├── memory-merger                               §12.3
├── memory-safety-patterns                      §1.1
├── mentoring-juniors                           §17.3
├── microservices-patterns                      §1.2
├── microsoft-agent-framework                   §3.2
├── microsoft-code-reference                    §8
├── microsoft-docs                              §8
├── microsoft-skill-creator                     §12.1
├── migrating-oracle-to-postgres-stored-procedures  §14.1
├── mkdocs-translations                         §9.1/§17.5
├── ml-pipeline-workflow                        §6.2
├── mobile-android-design                       §5.3
├── mobile-ios-design                           §5.3
├── model-recommendation                        §17.7
├── modern-javascript-patterns                  §1.1
├── monorepo-management                         §1.5
├── msstore-cli                                 §8.6
├── mtls-configuration                          §2.1
├── multi-cloud-architecture                    §2.4
├── multi-reviewer-patterns                     §12.5
├── multi-stage-dockerfile                     §1.5
├── my-issues                                   §9.4
├── my-pull-requests                            §9.4

N
├── nano-banana-pro-openrouter                  §15.3
├── napkin                                      §17.1
├── native-data-fetching                        §1.4
├── next-best-practices                         §1.3
├── next-cache-components                       §1.3
├── next-intl-add-language                      §1.3/§17.5
├── next-upgrade                                §1.3
├── nextjs-app-router-patterns                  §1.3
├── nft-standards                               §7.3
├── nodejs-backend-patterns                     §1.2
├── noob-mode                                   §8.5/§17.3
├── nuget-manager                               §8.1
├── nx-workspace-patterns                       §1.5

O
├── on-call-handoff-patterns                    §2.6
├── onboard-context-matic                       §17.3
├── onboarding-cro                              §4.3
├── oo-component-documentation                  §9.1
├── openapi-spec-generation                     §1.2
├── openapi-to-application-code                 §1.2
├── openclaw-secure-linux-cloud                 §7.1
├── opensource-guide-coach                      §17.7
├── organization-best-practices                 §14.4

P
├── page-cro                                    §4.3
├── paid-ads                                    §4.4
├── parallel-debugging                          §12.5
├── parallel-feature-development                §12.4
├── paypal-integration                          §1.7
├── paywall-upgrade-cro                         §4.3
├── pci-compliance                              §7.1
├── pdf                                         §15.1
├── pdftk-server                                §15.1
├── penpot-uiux-design                          §5.5
├── phoenix-cli                                 §3.4
├── phoenix-evals                               §3.4
├── phoenix-tracing                             §3.4
├── php-mcp-server-generator                    §1.6
├── planning-oracle-to-postgres-migration-integration-testing  §14.1
├── plantuml-ascii                              §9.5
├── playwright-automation-fill-in-form          §13.2
├── playwright-explore-website                  §13.2
├── playwright-generate-test                    §13.2
├── polyglot-test-agent                         §13.3
├── popup-cro                                   §4.3
├── postgresql-code-review                      §6.1/§14.7
├── postgresql-optimization                     §6.1/§14.7
├── postgresql-table-design                     §6.1/§14.7
├── postmortem-writing                          §2.6
├── power-apps-code-app-scaffold                §8.4
├── power-bi-dax-optimization                   §14.5
├── power-bi-model-design-review                §14.5
├── power-bi-performance-troubleshooting         §14.5
├── power-bi-report-design-consultation         §14.5
├── power-platform-mcp-connector-suite          §8.4
├── powerbi-modeling                            §6.3/§14.5
├── pptx                                        §15.1
├── prd                                         §9.2
├── premium-frontend-ui                         §5.2
├── pricing-strategy                            §4.5/§11.3
├── product-marketing-context                   §4.5
├── programmatic-seo                            §4.1
├── project-workflow-analysis-blueprint-generator  §9.5
├── projection-patterns                         §1.2
├── prometheus-configuration                    §2.6
├── prompt-builder                              §12.2
├── prompt-engineering-patterns                 §3.1
├── protocol-reverse-engineering                §16
├── publish-to-pages                            §10.4
├── pytest-coverage                             §13.1
├── python-anti-patterns                        §1.1
├── python-background-jobs                      §1.2
├── python-code-style                           §1.1
├── python-configuration                        §1.1
├── python-design-patterns                      §1.1
├── python-error-handling                       §1.1
├── python-mcp-server-generator                 §1.6
├── python-observability                        §1.1
├── python-packaging                            §1.1
├── python-performance-optimization             §1.1
├── python-project-structure                    §1.1
├── python-pypi-package-builder                 §1.1
├── python-resilience                           §1.1
├── python-resource-management                  §1.1
├── python-testing-patterns                     §13.1
├── python-type-safety                          §1.1

Q
├── quality-playbook                            §13.4
├── quasi-coder                                 §17.6

R
├── rag-implementation                          §3.1
├── react-audit-grep-patterns                   §1.8
├── react-modernization                         §1.3/§1.8
├── react-native-architecture                   §1.3
├── react-native-design                         §1.3
├── react-state-management                      §1.3
├── react18-batching-patterns                   §1.8
├── react18-dep-compatibility                   §1.8
├── react18-enzyme-to-rtl                       §1.8
├── react18-legacy-context                      §1.8
├── react18-lifecycle-patterns                  §1.8
├── react18-string-refs                         §1.8
├── react19-concurrent-patterns                 §1.8
├── react19-source-patterns                     §1.8
├── react19-test-patterns                       §1.8
├── readme-blueprint-generator                  §9.1
├── readme-i18n                                 §9.1/§17.5
├── receiving-code-review                       §12.5
├── refactor                                    §17.6
├── refactor-method-complexity-reduce           §17.6
├── refactor-plan                               §9.3/§17.6
├── referral-program                            §4.5
├── remember                                    §12.3
├── remember-interactive-programming            §12.3
├── repo-story-time                             §9.4
├── requesting-code-review                      §12.5
├── responsive-design                           §5.1
├── review-and-refactor                         §12.5/§17.6
├── reviewing-oracle-to-postgres-migration      §14.1
├── revops                                      §4.8
├── risk-metrics-calculation                    §6.4
├── roundup                                     §17.1
├── roundup-setup                               §17.1
├── ruby-mcp-server-generator                   §1.6
├── ruff-recursive-fix                          §13.4
├── running-claude-code-via-litellm-copilot     §17.7
├── rust-async-patterns                         §1.1
├── rust-mcp-server-generator                   §1.6

S
├── saga-orchestration                          §1.2
├── sales-enablement                            §4.6
├── salesforce-apex-quality                     §14.2
├── salesforce-component-standards              §14.2
├── salesforce-flow-design                      §14.2
├── sandbox-npm-install                         §17.4
├── sast-configuration                          §2.2/§7.1
├── scaffolding-oracle-to-postgres-migration-test-project  §14.1
├── schema-markup                               §4.2
├── scoutqa-test                                §13.2
├── screen-reader-testing                       §5.4
├── secret-scanning                             §2.2/§7.1
├── secrets-management                          §2.2
├── secure-linux-web-hosting                    §7.1/§10.3
├── security-requirement-extraction             §7.2
├── security-review                             §7.1
├── semantic-kernel                             §3.2
├── seo-audit                                   §4.2
├── service-mesh-observability                  §2.1
├── shadcn                                      §1.3
├── shellcheck-configuration                    §10.2/§13.4
├── shuffle-json-data                           §15.1
├── signup-flow-cro                             §4.3
├── similarity-search-patterns                  §3.1
├── site-architecture                           §4.2
├── skill-creator                               §12.1
├── skills-cli                                  §12.1
├── slack                                       §17.2
├── slack-gif-creator                           §15.3
├── slo-implementation                          §2.6
├── snowflake-semanticview                      §14.6
├── social-content                              §4.1/§15.4
├── solidity-security                           §7.3
├── spark-optimization                          §6.2
├── sponsor-finder                              §17.7
├── spring-boot-testing                         §13.1
├── sql-code-review                             §6.1
├── sql-optimization                            §6.1
├── sql-optimization-patterns                   §6.1
├── startup-financial-modeling                  §6.4/§11.1
├── startup-metrics-framework                   §6.4/§11.1
├── stride-analysis-patterns                    §7.2
├── stripe-integration                          §1.7
├── structured-autonomy-generate                §12.4
├── structured-autonomy-implement               §12.4
├── structured-autonomy-plan                    §12.4
├── subagent-driven-development                 §12.4
├── suggest-awesome-github-copilot-agents       §12.1
├── suggest-awesome-github-copilot-instructions §12.1
├── suggest-awesome-github-copilot-skills       §12.1
├── supabase                                    §6.1
├── supabase-postgres-best-practices            §6.1
├── swift-mcp-server-generator                  §1.6
├── systematic-debugging                        §12.5

T
├── tailwind-design-system                      §5.1
├── task-coordination-strategies                §12.4
├── tavily-best-practices                       §3.5
├── tavily-cli                                  §3.5
├── tavily-crawl                                §3.5
├── tavily-extract                              §3.5
├── tavily-map                                  §3.5
├── tavily-research                             §3.5
├── tavily-search                               §3.5
├── team-communication-protocols                §12.4
├── team-composition-analysis                   §11.1
├── team-composition-patterns                   §12.4
├── technology-stack-blueprint-generator        §9.5
├── template-skill                              (template vuoto)
├── temporal-python-testing                     §3.2/§13.3
├── terraform-azurerm-set-diff-analyzer         §2.3
├── terraform-module-library                    §2.3
├── test-driven-development                     §9.3
├── theme-factory                               §5.2
├── threat-mitigation-mapping                   §7.2
├── threat-model-analyst                        §7.2
├── tldr-prompt                                 §9.1
├── track-management                            §9.3
├── transloadit-media-processing                §15.3
├── turborepo                                   §1.5
├── turborepo-caching                           §1.5
├── two-factor-authentication-best-practices    §14.4
├── typescript-advanced-types                   §1.1
├── typescript-mcp-server-generator              §1.6
├── typespec-api-operations                     §8.3
├── typespec-create-agent                       §8.3
├── typespec-create-api-plugin                   §8.3
├── tzst                                        §17.4

U
├── ui-ux-pro-max                               §5.2
├── unit-test-vue-pinia                         §13.1
├── unity-ecs-patterns                          §16
├── update-avm-modules-in-bicep                 §2.3
├── update-implementation-plan                  §9.2
├── update-llms                                 §9.1
├── update-markdown-file-index                  §9.1
├── update-specification                        §9.2
├── upgrading-expo                              §1.4
├── use-dom                                     §1.4
├── use-my-browser                              §17.2
├── using-git-worktrees                         §9.3
├── using-superpowers                           §12.1
├── uv-package-manager                          §10.2

V
├── vector-index-tuning                         §3.1
├── vercel-cli-with-tokens                      §10.4
├── vercel-composition-patterns                 §14.8
├── vercel-react-best-practices                 §14.8
├── vercel-react-native-skills                  §14.8
├── vercel-react-view-transitions               §14.8
├── vercel-sandbox                              §14.8
├── verification-before-completion              §12.5
├── visual-design-foundations                   §5.1
├── vscode-ext-commands                         §8
├── vscode-ext-localization                     §8
├── vue-best-practices                          §1.3
├── vue-debug-guides                            §1.3
├── vue-jsx-best-practices                      §1.3
├── vue-options-api-best-practices              §1.3
├── vue-pinia-best-practices                    §1.3
├── vue-router-best-practices                   §1.3
├── vue-testing-best-practices                  §13.1

W
├── wcag-audit-patterns                         §5.4
├── web-artifacts-builder                       §5.2
├── web-coder                                   §1.3
├── web-component-design                        §1.3
├── web-design-guidelines                       §5.5
├── web-design-reviewer                         §5.5
├── web3-testing                                §7.3/§13.3
├── webapp-testing                              §13.2
├── what-context-needed                         §17.3
├── winapp-cli                                  §8.6
├── winmd-api-search                            §8.6
├── winui3-migration-guide                      §8.6
├── workflow-orchestration-patterns             §3.2
├── workflow-patterns                           §9.3
├── workiq-copilot                              §8.5
├── write-coding-standards-from-file            §9.1
├── writing-plans                               §9.2
├── writing-skills                              §12.1

X
├── xdrop                                       §17.4
├── xget                                        §17.4
├── xlsx                                        §15.1
```

---

## Appendice: Skills per Ruolo

| Ruolo | Skills Essenziali | Skills Aggiuntive |
|-------|-------------------|-------------------|
| **Frontend Developer** | nextjs-app-router-patterns, shadcn, vue-best-practices, frontend-design, responsive-design, ui-ux-pro-max | react-state-management, tailwind-design-system, accessibility-compliance |
| **Backend Developer** | nodejs-backend-patterns, fastapi-templates, dotnet-backend-patterns, api-design-principles, error-handling-patterns | database-migration, openapi-spec-generation, stripe-integration |
| **Full-stack Developer** | Tutte le skills frontend + backend + monorepo-management, nextjs-app-router-patterns, supabase | vercel-react-best-practices, context-driven-development |
| **DevOps/SRE** | k8s-manifest-generator, github-actions-templates, prometheus-configuration, terraform-module-library, deployment-pipeline-design | istio-traffic-management, gitops-workflow, slo-implementation |
| **Data Engineer** | airflow-dag-patterns, dbt-transformation-patterns, spark-optimization, bigquery-pipeline-audit, data-quality-frameworks | postgresql-optimization, sql-optimization-patterns |
| **Data Scientist** | ml-pipeline-workflow, rag-implementation, embedding-strategies, python-testing-patterns, eval-driven-dev | arize-instrumentation, phoenix-tracing |
| **Security Engineer** | security-review, sast-configuration, codeql, stride-analysis-patterns, threat-model-analyst, secret-scanning | solidity-security, memory-forensics, gdpr-compliant |
| **Product Manager** | prd, breakdown-plan, product-marketing-context, content-strategy, competitive-landscape, gtm-positioning-strategy | brainstorming, customer-research, market-sizing-analysis |
| **Marketing/Growth** | copywriting, seo-audit, page-cro, email-sequence, paid-ads, social-content, ai-seo | gtm-product-led-growth, referral-program, marketing-psychology |
| **Sales/RevOps** | sales-enablement, cold-email, revops, gtm-enterprise-account-planning, pricing-strategy | competitor-alternatives, churn-prevention, gtm-enterprise-onboarding |
| **Architect** | cloud-design-patterns, microservices-patterns, architecture-decision-records, architecture-blueprint-generator, cqrs-implementation | multi-cloud-architecture, event-store-design, saga-orchestration |
| **Tech Lead** | code-review-excellence, mentoring-juniors, context-driven-development, writing-plans, verification-before-completion, multi-reviewer-patterns | team-composition-patterns, task-coordination-strategies |
| **AI/ML Engineer** | prompt-engineering-patterns, rag-implementation, langchain-architecture, llm-evaluation, arize-instrumentation, tavily-research | agentic-eval, eval-driven-dev, hybrid-search-implementation |

---

> **Nota:** Questo catalogo è stato generato analizzando tutte le 580 skill presenti in `~/.agents/skills/`. La numerazione dei paragrafi (§) serve per navigazione e reference incrociata.
