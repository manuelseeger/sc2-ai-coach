# SC2 AI Coach

This context describes the architectural language used to keep the SC2 AI Coach import-safe while still allowing the executable coach runtime to load and validate configuration explicitly.

## Language

**Coach Runtime**:
The executable application flow that is allowed to load configuration, initialize integrations, and wire services together.
_Avoid_: app, main logic, global startup

**Composition Root**:
The startup boundary where the Coach Runtime loads configuration and constructs configured modules and services.
_Avoid_: random module import, singleton init

**Import-Safe Module**:
A module that can be imported without loading configuration, prompting the user, opening connections, or initializing integrations.
_Avoid_: startup module, hot module

**ModuleConfig**:
A bundled settings object delivered from the Composition Root to a module when that module needs multiple related configuration values.
_Avoid_: exploded args, config singleton, implicit globals

**Configured Module**:
An import-safe module instance that receives its dependencies explicitly through construction or call-time arguments.
_Avoid_: module-global setter, hidden startup state

**Shared Config Type**:
An import-safe enum or typed settings fragment that can be reused across modules without depending on the runtime settings loader.
_Avoid_: runtime-only type, config singleton type

**Runtime Settings Loader**:
The component that parses and validates runtime settings and either returns them or raises typed errors.
_Avoid_: startup prompt, exit path, side-effectful init

**Runtime Settings**:
The single validated settings object created once per process start by the Composition Root and used to derive module-specific configuration.
_Avoid_: implicit singleton, per-module reload

**Full Refactor**:
An architectural migration that updates affected paths to explicit wiring without adding backward-compatibility accessors to preserve the old ambient-config pattern.
_Avoid_: migration shim, temporary singleton, fallback accessor

**Owned ModuleConfig**:
A module-scoped configuration type owned by the module that consumes it rather than a shared bag of unrelated settings.
_Avoid_: full runtime settings, god config object, central dumping ground

**Shared Config Fragment**:
An import-safe typed settings fragment extracted only when multiple modules truly share the same concept.
_Avoid_: premature centralization, umbrella config package

**Implementation Selection**:
The choice of which concrete service or adapter to use for a capability such as transcription, wake-word detection, or game event sourcing.
_Avoid_: import-time selection, package magic, hidden factory

**Pure Model Behavior**:
A model method that remains import-safe because it depends only on explicit inputs and model state, not ambient runtime policy.
_Avoid_: hidden config lookup, runtime service reach-through

**Config Bundling Rule**:
A pragmatic rule for introducing a ModuleConfig only when a module needs a meaningful cluster of related settings, while one or two simple values may remain explicit parameters.
_Avoid_: premature sub-object extraction, ceremonial wrappers, one-field config classes

**Prepared Runtime Environment**:
The expected precondition that directories, downloaded assets, and external setup already exist before the Coach Runtime starts.
_Avoid_: lazy init, self-healing startup, embedded bootstrap

**Import-Safe Entrypoint**:
An entrypoint or module that can be imported without loading runtime settings or performing side effects.
_Avoid_: ambient settings load, import-time wiring, hidden startup work

**Explicit Test Settings Load**:
An opt-in test action that intentionally loads current yaml and env-backed settings when a test wants to exercise behavior against real configured values.
_Avoid_: ambient test config import, fixture-only mandate, hidden settings load

**Settings Loader API**:
An explicit callable used by entrypoints and tests to load current yaml and env-backed runtime settings on demand.
_Avoid_: import-time construction, implicit singleton access, duplicated loading rules

**Fresh Settings Load**:
Each call to the Settings Loader API returns a newly constructed Runtime Settings object, leaving any process-level reuse to the caller.
_Avoid_: loader cache, hidden memoization, ambient reuse

**Settings Loader Error**:
A project-specific typed exception raised by the Settings Loader API when reading or validating runtime settings fails.
_Avoid_: sys.exit in loader, raw framework leakage as the public contract, silent fallback

**Shared Composition Module**:
A shared wiring layer that derives module-owned configuration and assembles configured services for the different entrypoints.
_Avoid_: per-entrypoint drift, duplicated wiring, hidden mini-composition roots

**Explicit Infrastructure Wiring**:
The rule that infrastructure dependencies such as databases and stores are constructed by the composition layer and passed in explicitly.
_Avoid_: process-global singleton, ambient fallback, hidden infrastructure state

**Composition-Owned Logging**:
The rule that log handlers, file paths, and logging policy are configured by the composition layer rather than by module import side effects.
_Avoid_: import-time handler setup, config-coupled log module, hidden logger initialization

**Explicit Dependency Access**:
The rule that services, stores, and infrastructure are obtained through constructor or call-time dependencies rather than module-level convenience accessors.
_Avoid_: get_database, get_store, ambient service lookup

**Execution-Path Composition**:
The rule that configured objects are created only inside explicit runtime execution paths rather than as top-level module state.
_Avoid_: top-level composed objects, import-time assembly, hidden startup graph

**Player Identity Enrichment**:
The application step that derives and merges opponent identity signals from replay context and external portrait sources before persisting player state.
_Avoid_: save player info, store helper, plain persistence

**Player Resolver**:
The query-side service that identifies an opponent and retrieves past replay context without owning player-state persistence.
_Avoid_: player saver, enrichment service, write-side resolver

**Player Identity Enricher**:
The write-side service that performs Player Identity Enrichment and owns the merge-and-save workflow for player state.
_Avoid_: replay store method, save helper, generic player service

**Player Portrait Source**:
The shared collaborator that acquires or derives portrait inputs for player identity flows without owning query resolution or player-state persistence.
_Avoid_: resolver helper bag, loose utility functions, saver helper

**Player Replay History**:
The ordered set of stored replays associated with a resolved opponent identity.
_Avoid_: resolver side effect, ad hoc replay lookup, mixed query result

**Recent Player Replay History**:
The bounded recent slice of Player Replay History returned by default for an identified opponent.
_Avoid_: implicit full history, unbounded default, resolver bundle

## Relationships

- The **Coach Runtime** owns the **Composition Root**
- The **Composition Root** loads runtime configuration exactly once per process start
- The **Composition Root** creates one **Runtime Settings** object per process start
- The **Composition Root** passes **ModuleConfig** objects into configured modules
- Only the **Composition Root** handles full **Runtime Settings**
- The **Composition Root** performs **Implementation Selection** explicitly
- The **Composition Root** is implemented through a **Shared Composition Module** reused by entrypoints
- The **Composition Root** owns **Explicit Infrastructure Wiring** for databases and stores
- The **Composition Root** owns **Composition-Owned Logging**
- The **Composition Root** provides **Explicit Dependency Access** for services, stores, and infrastructure
- The **Composition Root** runs through **Execution-Path Composition**, not top-level module assembly
- An **Import-Safe Module** may define or accept a **ModuleConfig**, but it does not load runtime configuration by itself
- A **Configured Module** receives configuration explicitly and does not rely on a module-global setter
- A **Shared Config Type** lives outside the runtime settings loader so import-safe modules can depend on it safely
- The **Runtime Settings Loader** returns validated settings or raises typed errors and does not prompt or terminate the process
- **ModuleConfig** objects are derived from **Runtime Settings** rather than reloading settings per subsystem
- A **Full Refactor** removes ambient-config access from touched code instead of preserving it behind a new compatibility layer
- An **Owned ModuleConfig** exposes only the settings a module owns
- A **Shared Config Fragment** exists only when multiple modules truly share the same settings concept
- Package imports expose symbols but do not perform **Implementation Selection**
- **Pure Model Behavior** may stay on models when explicit inputs are enough to keep the method import-safe
- Broader policy or runtime-dependent behavior moves from models into services or factories
- The **Config Bundling Rule** favors explicit individual values for trivial cases and a **ModuleConfig** only for meaningful related setting clusters
- The **Coach Runtime** assumes a **Prepared Runtime Environment** and does not bootstrap it from config loading
- [coach.py](coach.py), [repcli.py](repcli.py), the future API entrypoint, and test imports must behave as **Import-Safe Entrypoints**
- Tests may use an **Explicit Test Settings Load** when they intentionally want behavior against current yaml and env-backed settings
- Entry points and tests use a **Settings Loader API** rather than importing pre-built settings
- The **Settings Loader API** should follow the same explicit bootstrap style already used in [tests/support/pytest_services.py](tests/support/pytest_services.py#L31)
- The **Settings Loader API** performs a **Fresh Settings Load** on each call
- Process-wide reuse of **Runtime Settings** is owned explicitly by the caller, not by the loader
- The public failure contract of the **Settings Loader API** is a **Settings Loader Error**
- Entry points reuse a **Shared Composition Module** for config-to-dependency assembly rather than wiring independently
- Databases and stores follow **Explicit Infrastructure Wiring** rather than process-global singleton access
- Logging setup follows **Composition-Owned Logging**, while modules acquire loggers in an import-safe way
- Modules use **Explicit Dependency Access** instead of module-level convenience accessors
- Configured objects are created through **Execution-Path Composition** inside `main()`-style flows or command handlers
- A **Player Identity Enrichment** step may end with persistence, but it is not itself a plain store operation
- A **Player Resolver** handles query-side identity lookup, while a **Player Identity Enricher** handles write-side enrichment and persistence
- A **Player Identity Enricher** is constructed through **Execution-Path Composition** with explicit collaborators rather than ambient fallbacks
- A **Player Portrait Source** may be shared by the **Player Resolver** and **Player Identity Enricher** when both need portrait acquisition behavior
- **Player Replay History** is queried through the replay store rather than returned as part of identity resolution
- **Recent Player Replay History** defaults to a bounded slice rather than an implicit full-history query

## Example dialogue

> **Dev:** "Can this persistence model import the config singleton to compute pricing?"
> **Domain expert:** "No. Keep it an **Import-Safe Module** and pass a **ModuleConfig** or call-time dependency from the **Composition Root**."

## Flagged ambiguities

- "config" was used to mean both the validated runtime settings object and arbitrary module-level access to settings - resolved: only the **Composition Root** loads runtime configuration, and modules receive explicit dependencies such as **ModuleConfig**.
- "inject config into the module" could mean constructor injection or a startup-time setter - resolved: use explicit construction or call-time arguments, not module-global setters.
- "config type" was used to mean both runtime settings models and reusable enums - resolved: reusable enums and typed fragments are **Shared Config Types** and live outside the runtime settings loader.
- "load config" was used to include prompting, initialization, and process exit - resolved: the **Runtime Settings Loader** only parses and validates; prompting and termination belong to the executable boundary.
- "global config" was used to mean a process-wide singleton reached from anywhere - resolved: there is one **Runtime Settings** object per process start, but it is created explicitly at the **Composition Root** and passed downward.
- "incremental migration" could imply preserving ambient config behind a new accessor - resolved: this change is a **Full Refactor** with no backward-compatibility accessor layer.
- "pass config to the module" could mean handing over the full settings object - resolved: non-composition-root modules receive **Owned ModuleConfig** objects or narrower call-time dependencies, never full **Runtime Settings**.
- "shared config" could mean collecting all module configs in one place - resolved: **Owned ModuleConfig** is the default, and only truly reused concepts become a **Shared Config Fragment**.
- "importing a package" was used to include choosing configured implementations - resolved: **Implementation Selection** belongs only to the **Composition Root**, never package `__init__` code.
- "leave it on the model" was used loosely - resolved: only **Pure Model Behavior** stays on the model; runtime policy and broader config-shaped behavior move to services or factories.
- "make a config sub-object" could mean any group of values - resolved: follow the **Config Bundling Rule** and only bundle meaningful related settings, not arbitrary small groups.
- "startup init" was treated as part of config behavior - resolved: remove init from config entirely; the runtime assumes a **Prepared Runtime Environment**.
- "stronger import safety" was used broadly - resolved: [coach.py](coach.py), [repcli.py](repcli.py), the API entrypoint, and test imports must be import-safe by default, while tests still retain an **Explicit Test Settings Load** path for real yaml/env-backed settings.
- "loader api" could mean direct settings construction spread through the codebase - resolved: use a single **Settings Loader API**, following the explicit bootstrap pattern already used by test services.
- "one settings object per process" could imply loader-side memoization - resolved: the loader always performs a **Fresh Settings Load**; callers hold onto the result when they want one-per-process behavior.
- "loader failure" could mean raw pydantic errors leaking through every caller - resolved: the loader exposes a project-level **Settings Loader Error** contract and may wrap underlying validation or source-reading exceptions.
- "each entrypoint wires itself" could mean repeating config slicing and implementation choices in multiple places - resolved: wiring belongs in a **Shared Composition Module** reused by `coach`, `repcli`, and the future API.
- "database access" could imply a process-global fallback and singleton store state - resolved: databases and stores use **Explicit Infrastructure Wiring** and are created by the composition layer.
- "project logging" could imply a config-aware `log` module setting handlers on import - resolved: logging policy and handlers use **Composition-Owned Logging**, and modules only acquire loggers without import-time setup.
- "convenience accessor" could seem harmless once config is explicit - resolved: stores, databases, and services use **Explicit Dependency Access** and do not expose module-level getter shortcuts.
- "top-level helper state" could seem harmless after explicit loading - resolved: use **Execution-Path Composition** only; configured objects are not created as module globals.
- "save player info" was used as if this were only a persistence concern - resolved: this flow is **Player Identity Enrichment** that concludes with a store write.
- "player resolver" was used for both lookup and persistence - resolved: **Player Resolver** is query-side only, and **Player Identity Enricher** owns write-side enrichment.
- "move helper methods out" was used to imply standalone functions - resolved: shared portrait acquisition behavior belongs in a **Player Portrait Source** collaborator when both sides need it.
- "resolver result" was used to bundle identity lookup with replay history - resolved: **Player Replay History** is a separate store query, not part of the resolver contract.
- "recent history" could imply an unbounded query with caller-side slicing - resolved: **Recent Player Replay History** is a bounded store query with a default depth of 5.