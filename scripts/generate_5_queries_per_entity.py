import json
from pathlib import Path

# Load entities from synthetic repo test_repo_project1
repo_path = Path(r"c:\Users\kmohn\New folder\Project-1\test_repo_project1")

entities_spec = [
    # 1. auth.py (10 entities)
    ("src/auth.py::TokenValidator", "class", "TokenValidator", [
        "What validator verifies authentication tokens and JWT structures?",
        "Which class inspects token signature header format and secret keys?",
        "How is the token validator initialized with secret keys and RS256 algorithm?",
        "Where is token structural integrity checked prior to payload parsing?",
        "Which component handles authentication token validation rules?"
    ]),
    ("src/auth.py::validate_jwt", "function", "validate_jwt", [
        "How does the system parse and validate JWT bearer tokens and payload claims?",
        "Which function decrypts JWT authorization headers using secret keys?",
        "Where are invalid JWT token formats caught and raised as ValueErrors?",
        "What routine returns user ID and role dictionaries from JWT tokens?",
        "How is RS256 token verification executed during authentication?"
    ]),
    ("src/auth.py::generate_token", "function", "generate_token", [
        "How are raw authentication header tokens generated with algorithm signatures?",
        "Which function constructs encrypted JWT authentication token strings?",
        "Where are signed tokens formatted for user authorization response payloads?",
        "What routine creates RS256 signed bearer tokens for user IDs?",
        "How is the encrypted user ID token payload generated?"
    ]),
    ("src/auth.py::hash_password", "function", "hash_password", [
        "Which function hashes plain text user passwords using PBKDF2 with salt rounds?",
        "How are passwords encrypted prior to storage in the database?",
        "Where are configurable salt rounds applied during password hashing?",
        "What routine converts plain password strings into salted hashes?",
        "How is security salting enforced during user password registration?"
    ]),
    ("src/auth.py::verify_password", "function", "verify_password", [
        "How is a plain text password checked against a stored security hash?",
        "Which function verifies password equality during user login authentication?",
        "Where is PBKDF2 password verification executed for stored hashes?",
        "What routine evaluates plain text password matches against database hashes?",
        "How does the login pipeline validate plain password credentials?"
    ]),
    ("src/auth.py::SessionManager", "class", "SessionManager", [
        "What component manages user active sessions and multi-device lifetimes?",
        "Which class tracks active session records in dictionary storage?",
        "How is maximum session duration enforced across active user sessions?",
        "Where are session audit timestamps updated during session lookups?",
        "Which manager handles session lookup and multi-device revocation?"
    ]),
    ("src/auth.py::create_session", "function", "create_session", [
        "How are new active sessions initialized with device bindings?",
        "Which function creates active session tokens bound to device IDs?",
        "Where are user sessions stored upon successful login authentication?",
        "What routine generates session strings containing device ID and token?",
        "How is a new user session created with RS256 algorithm tokens?"
    ]),
    ("src/auth.py::destroy_session", "function", "destroy_session", [
        "Which function revokes active sessions or terminates user device sessions?",
        "How are user sessions invalidated upon logout or session expiry?",
        "Where is session revocation executed for multi-device user sessions?",
        "What routine purges active session tokens from session storage?",
        "How does the system terminate an active user session by session ID?"
    ]),
    ("src/auth.py::RBACController", "class", "RBACController", [
        "What controller handles hierarchical role-based authorization checks?",
        "Which class evaluates user roles and permission hierarchies?",
        "How is access authorization evaluated for resource actions?",
        "Where is default role initialization configured for access control?",
        "Which component enforces role-based access restrictions?"
    ]),
    ("src/auth.py::check_permission", "function", "check_permission", [
        "How are resource permissions evaluated against user role contexts?",
        "Which function verifies if a role has authorization for an action?",
        "Where are admin and superadmin privileges granted access overrides?",
        "What routine checks permission strings like read, view, or download?",
        "How is granular permission verification performed for resources?"
    ]),

    # 2. database.py (10 entities)
    ("src/database.py::DatabaseClient", "class", "DatabaseClient", [
        "What class manages database connection pools and read replica transactions?",
        "Which client tracks database connectivity status and connection pools?",
        "How is the database connection string and pool size configured?",
        "Where is active database connection pool status checked?",
        "Which component handles primary and replica database connections?"
    ]),
    ("src/database.py::connect_db", "function", "connect_db", [
        "How are database connections established with pool sizes?",
        "Which factory function initializes DatabaseClient connection instances?",
        "Where is the database connection established and marked active?",
        "What routine creates database client instances with pool configurations?",
        "How is the database connection client instantiated for SQL queries?"
    ]),
    ("src/database.py::execute_query", "function", "execute_query", [
        "Which routine executes SQL queries with transparent caching and replica selection?",
        "How are SQL query strings executed with parameter binding and caching?",
        "Where are database queries routed to read-replicas or primary nodes?",
        "What function fetches SQL query results while checking cache keys?",
        "How is transparent database query caching performed for SELECT statements?"
    ]),
    ("src/database.py::QueryBuilder", "class", "QueryBuilder", [
        "How are WHERE clauses constructed with table schema prefixes?",
        "Which class builds sanitized SQL clauses and table condition strings?",
        "Where is schema prefix formatting applied during query building?",
        "What builder utility constructs SQL WHERE clauses for tables?",
        "How are table names and schema parameters initialized for SQL query building?"
    ]),
    ("src/database.py::build_select_query", "function", "build_select_query", [
        "What helper builds SELECT SQL statements for specified table columns?",
        "Which function constructs SELECT query strings with schema prefixes?",
        "Where are column lists formatted into SQL SELECT statement strings?",
        "How is a full SELECT SQL query string constructed for a table?",
        "What routine formats SELECT columns and table names with WHERE clauses?"
    ]),
    ("src/database.py::build_insert_query", "function", "build_insert_query", [
        "How are INSERT SQL statements generated from key-value dictionaries?",
        "Which function formats INSERT INTO query strings from model data?",
        "Where are dictionary keys extracted to build SQL column insert targets?",
        "What helper constructs SQL INSERT statements for ORM persistence?",
        "How is model data serialized into INSERT INTO SQL string statements?"
    ]),
    ("src/database.py::ORMModel", "class", "ORMModel", [
        "What ORM wrapper model serializes table properties into dictionary payloads?",
        "Which base ORM model class manages table names and primary keys?",
        "How are ORM model attributes converted into dictionary representations?",
        "Where is table primary key metadata defined for object-relational mapping?",
        "Which model class wraps database entity tables for persistence?"
    ]),
    ("src/database.py::save_model", "function", "save_model", [
        "How are ORM model instances saved into the database table?",
        "Which function persists model dictionary data via execute_query?",
        "Where is build_insert_query invoked to persist ORM models?",
        "What routine saves ORM model changes without caching?",
        "How does the system commit ORM model data to the database client?"
    ]),
    ("src/database.py::MigrationRunner", "class", "MigrationRunner", [
        "What executor manages database schema migration versions and dry-runs?",
        "Which class tracks schema migration versions and migration execution?",
        "How is dry-run migration mode configured in MigrationRunner?",
        "Where is current database schema version retrieved during migrations?",
        "Which runner handles schema migration version management?"
    ]),
    ("src/database.py::apply_migrations", "function", "apply_migrations", [
        "What executor applies schema migration steps up to a target version?",
        "Which function runs schema migrations up to target version numbers?",
        "Where are dry-run schema migrations evaluated before execution?",
        "What routine verifies schema version compliance against target versions?",
        "How are database schema migrations executed up to a target version?"
    ]),

    # 3. cache.py (10 entities)
    ("src/cache.py::LRUCache", "class", "LRUCache", [
        "What class implements the in-memory LRU cache with hit and miss tracking?",
        "Which in-memory cache tracks storage capacity and cache hits?",
        "How is maximum storage capacity evaluated in LRUCache?",
        "Where are cache hits and miss statistics recorded during lookups?",
        "Which storage component handles in-memory Least Recently Used caching?"
    ]),
    ("src/cache.py::cache_get", "function", "cache_get", [
        "How are cached object entries retrieved by string keys?",
        "Which function performs cache lookups with audit logging?",
        "Where are cached values fetched from memory or Redis storage?",
        "What routine returns cached items given a string cache key?",
        "How is cache key retrieval logged and processed?"
    ]),
    ("src/cache.py::cache_set", "function", "cache_set", [
        "How are key-value items stored into cache with TTL and namespace isolation?",
        "Which function stores cached values with time-to-live expiration?",
        "Where are serialized keys generated prior to setting cache values?",
        "What routine saves items into cache storage under namespace prefixes?",
        "How is key-value caching executed with TTL seconds and namespace isolation?"
    ]),
    ("src/cache.py::RedisManager", "class", "RedisManager", [
        "What manager connects to the Redis cluster and verifies SSL connectivity?",
        "Which client manages Redis connection host, port, and SSL ping?",
        "How is Redis host and port configuration initialized?",
        "Where is Redis server ping executed to verify cluster connection?",
        "Which connector manages Redis cluster communication?"
    ]),
    ("src/cache.py::redis_connect", "function", "redis_connect", [
        "How are Redis connection instances established with SSL ping checks?",
        "Which factory function creates RedisManager instances if ping succeeds?",
        "Where is Redis connection connectivity tested before returning client?",
        "What routine returns an active Redis client or None if ping fails?",
        "How is Redis cluster connectivity initialized via factory connection?"
    ]),
    ("src/cache.py::KeySerializer", "class", "KeySerializer", [
        "How are cache key prefixes formatted with namespace and application versioning?",
        "Which utility formats string prefixes for namespace isolation?",
        "Where is prefix versioning string formatted in KeySerializer?",
        "What serializer handles key namespace formatting and versioning?",
        "Which helper formats key prefixes for application namespace isolation?"
    ]),
    ("src/cache.py::serialize_key", "function", "serialize_key", [
        "How are raw cache keys serialized with application version prefixes?",
        "Which function formats raw keys using KeySerializer prefix rules?",
        "Where are active version tags appended to cache keys?",
        "What routine serializes keys with namespace and version strings?",
        "How is a raw string key transformed into a versioned cache key?"
    ]),
    ("src/cache.py::InvalidationManager", "class", "InvalidationManager", [
        "What manager evaluates targeted cache purge and pattern eviction rules?",
        "Which class determines whether cached records exceed maximum age?",
        "How is purge criteria evaluated against record age and hit counts?",
        "Where are cache eviction mode rules configured in InvalidationManager?",
        "Which utility determines cache entry eviction and purge eligibility?"
    ]),
    ("src/cache.py::purge_stale_keys", "function", "purge_stale_keys", [
        "Which function purges stale or expired entries based on age and hit counts?",
        "How are expired cache entries evicted from storage?",
        "Where is InvalidationManager invoked to calculate purged key counts?",
        "What routine purges stale cache items exceeding maximum age threshold?",
        "How is stale key eviction executed across cache storage?"
    ]),
    ("src/cache.py::flush_all", "function", "flush_all", [
        "Which function completely flushes all keys from cache storage layers?",
        "How are all cached keys cleared during cache reset operations?",
        "Where is force override evaluated during full cache flush?",
        "What routine logs error alerts and flushes all cache keys?",
        "How is complete cache storage purge performed across memory layers?"
    ]),

    # 4. api.py (10 entities)
    ("src/api.py::APIRouter", "class", "APIRouter", [
        "What HTTP API router matches incoming request paths against API prefixes?",
        "Which class manages REST endpoint prefix matching and strict slash rules?",
        "How is base API prefix matching initialized in APIRouter?",
        "Where is strict slash pattern matching evaluated for API paths?",
        "Which component handles HTTP request path route matching?"
    ]),
    ("src/api.py::handle_request", "function", "handle_request", [
        "How does the main HTTP request dispatch pipeline process path headers and payloads?",
        "Which main handler dispatches HTTP requests through rate limits and auth?",
        "Where are request paths sanitized and logged with timestamp tags?",
        "What routine processes incoming HTTP request paths, methods, and headers?",
        "How are HTTP request payloads processed through middleware validation?"
    ]),
    ("src/api.py::MiddlewarePipeline", "class", "MiddlewarePipeline", [
        "What pipeline processor executes sequential HTTP middleware handlers?",
        "Which class registers and executes HTTP middleware pipeline stages?",
        "How are middleware handlers registered and executed in order?",
        "Where are context dictionaries evaluated across registered handlers?",
        "Which component manages sequential HTTP request processing pipelines?"
    ]),
    ("src/api.py::auth_middleware", "function", "auth_middleware", [
        "What middleware function validates authorization headers and token permissions?",
        "How are HTTP Authorization header JWT tokens parsed and verified?",
        "Where are check_permission calls executed for bearer token roles?",
        "What routine intercepts unauthorized HTTP requests without tokens?",
        "How is authentication header token validation enforced in middleware?"
    ]),
    ("src/api.py::logging_middleware", "function", "logging_middleware", [
        "How are incoming HTTP request headers, target paths, and trace IDs logged?",
        "Which middleware logs User-Agent and X-Trace-ID request headers?",
        "Where are request path logs formatted with user agent strings?",
        "What routine logs incoming HTTP request metadata for auditing?",
        "How is HTTP request path and header trace logging performed?"
    ]),
    ("src/api.py::ResponseFormatter", "class", "ResponseFormatter", [
        "How are HTTP response payloads wrapped into standardized JSON metadata envelopes?",
        "Which class formats JSON response envelopes with server timestamps?",
        "Where is response compression status appended to payload envelopes?",
        "What formatter builds JSON response structures with status codes?",
        "Which component wraps data payloads into standard JSON response objects?"
    ]),
    ("src/api.py::json_response", "function", "json_response", [
        "How is HTTP response data formatted into a standard JSON envelope?",
        "Which helper function returns JSON response envelopes with status codes?",
        "Where is ResponseFormatter instantiated to format HTTP output?",
        "What routine builds HTTP 200 OK JSON response payloads?",
        "How are success data payloads converted to JSON response envelopes?"
    ]),
    ("src/api.py::RateLimiter", "class", "RateLimiter", [
        "What rate limiting component evaluates sliding window counts against IP whitelists?",
        "Which class tracks maximum requests per sliding window interval?",
        "How is request count limit checked against token bucket capacity?",
        "Where is IP address whitelist checking performed in RateLimiter?",
        "Which evaluator determines if request rate limit has been exceeded?"
    ]),
    ("src/api.py::allow_request", "function", "allow_request", [
        "How is IP address rate limit status evaluated using sliding window counters?",
        "Which function checks rate limit keys in cache for incoming IPs?",
        "Where are IP whitelists checked before incrementing rate limit counts?",
        "What routine returns False if an IP address exceeds request limits?",
        "How is rate limiting enforced for incoming client IP addresses?"
    ]),
    ("src/api.py::error_handler", "function", "error_handler", [
        "How are standard HTTP error response payloads constructed for failures?",
        "Which function logs error messages and returns 401 or 429 JSON responses?",
        "Where is log_error invoked when HTTP request handling fails?",
        "What routine constructs JSON error envelopes with status codes and messages?",
        "How are error payloads formatted for unauthorized or rate-limited requests?"
    ]),

    # 5. utils.py (10 entities)
    ("src/utils.py::LoggerWrapper", "class", "LoggerWrapper", [
        "What logger wrapper formats severity level tags, timestamps, and colors?",
        "Which class formats system log messages with severity tags?",
        "How are color prefixes and timestamp strings formatted in LoggerWrapper?",
        "Where is log severity level initialized in LoggerWrapper?",
        "Which component formats log output lines for system events?"
    ]),
    ("src/utils.py::log_info", "function", "log_info", [
        "How are informative system event messages logged with structured context?",
        "Which function logs INFO severity messages with timestamp tags?",
        "Where is LoggerWrapper instantiated for informative logging?",
        "What routine prints formatted log messages with optional context?",
        "How is structured INFO logging executed for system operations?"
    ]),
    ("src/utils.py::log_error", "function", "log_error", [
        "How are high priority error messages logged with exception details?",
        "Which function logs ERROR severity messages with exception info?",
        "Where is LoggerWrapper instantiated for high priority error logging?",
        "What routine prints formatted ERROR messages with stack traces?",
        "How is error logging executed for system exceptions and failures?"
    ]),
    ("src/utils.py::CryptoHelper", "class", "CryptoHelper", [
        "What cryptography helper utility manages AES-256 GCM symmetric keys?",
        "Which class provides key length checks and AES cipher mode settings?",
        "How is key length retrieved in CryptoHelper?",
        "Where is secret key length and cipher mode initialized?",
        "Which helper utility handles symmetric encryption key management?"
    ]),
    ("src/utils.py::encrypt_data", "function", "encrypt_data", [
        "How is plain text data encrypted using AES-256 GCM cipher mode?",
        "Which function converts plain text strings into ciphertext outputs?",
        "Where is CryptoHelper instantiated during data encryption?",
        "What routine formats encrypted strings with key length prefixes?",
        "How is symmetric string encryption performed using secret keys?"
    ]),
    ("src/utils.py::decrypt_data", "function", "decrypt_data", [
        "How is AES-256 GCM ciphertext decrypted back to plain text?",
        "Which function parses ciphertext strings and removes cipher headers?",
        "Where is ciphertext prefix checking performed during decryption?",
        "What routine extracts original plain text from encrypted payload strings?",
        "How is symmetric string decryption executed for encrypted payloads?"
    ]),
    ("src/utils.py::StringCleaner", "class", "StringCleaner", [
        "What string sanitization tool strips whitespace and escapes HTML tags?",
        "Which class sanitizes raw user input strings against script injection?",
        "How is whitespace stripping and HTML tag removal configured?",
        "Where is string cleaning executed in StringCleaner?",
        "Which utility sanitizes raw string inputs against XSS script tags?"
    ]),
    ("src/utils.py::sanitize_input", "function", "sanitize_input", [
        "How is user input sanitized against XSS injection and script tags?",
        "Which function cleans raw input strings using StringCleaner?",
        "Where are HTML script and iframe tags stripped from user strings?",
        "What routine normalizes raw user inputs prior to route processing?",
        "How is input sanitization performed for incoming API path strings?"
    ]),
    ("src/utils.py::DateFormatter", "class", "DateFormatter", [
        "What ISO 8601 date formatting helper manages timezones and microsecond precision?",
        "Which class handles timezone formatting for epoch integer timestamps?",
        "How is active timezone string retrieved in DateFormatter?",
        "Where is microsecond precision enabled in DateFormatter?",
        "Which helper utility formats epoch timestamps to ISO date strings?"
    ]),
    ("src/utils.py::format_iso_date", "function", "format_iso_date", [
        "How are epoch integer timestamps formatted into ISO 8601 date strings?",
        "Which function converts epoch timestamps to ISO date strings with UTC timezone?",
        "Where is DateFormatter instantiated during timestamp formatting?",
        "What routine returns ISO 8601 formatted date strings with microsecond precision?",
        "How is date formatting performed for system event timestamps?"
    ])
]

# Build 250 curated queries dataset
query_list = []
query_counter = 1

for target_id, entity_type, entity_name, questions in entities_spec:
    file_path = target_id.split("::")[0]
    for q_text in questions:
        query_list.append({
            "query_id": f"syn_{query_counter:03d}",
            "query_text": q_text,
            "category": "changed_entity",
            "target_entity_id": target_id,
            "target_entity_name": entity_name,
            "expected_behavior": "latest_snapshot",
            "commit_after": "",
            "file_path": file_path,
            "entity_type": entity_type
        })
        query_counter += 1

out_path = Path(r"c:\Users\kmohn\New folder\Project-1\src\benchmarking\data\curated_queries_synthetic_5x.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(query_list, f, indent=2)

print(f"Successfully generated {len(query_list)} curated queries (5 queries per entity for all 50 entities) at:")
print(f"  {out_path}")
