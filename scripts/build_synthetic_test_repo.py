import os
import shutil
import subprocess
from pathlib import Path

REPO_PATH = Path(r"c:\Users\kmohn\New folder\Project-1\test_repo_project1")

def run_git(cmd_args):
    result = subprocess.run(
        ["git"] + cmd_args,
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

def init_repository():
    if REPO_PATH.exists():
        shutil.rmtree(REPO_PATH)
    REPO_PATH.mkdir(parents=True, exist_ok=True)

    run_git(["init"])
    run_git(["config", "user.name", "Synthetic Bot"])
    run_git(["config", "user.email", "bot@synthetic.local"])

# System modules definitions per commit state
def write_commit_0():
    """Commit 0: Initial Repository Setup with 50 Entities across 5 Modules."""
    (REPO_PATH / "src").mkdir(exist_ok=True)
    (REPO_PATH / "src" / "__init__.py").write_text('"""Synthetic system package."""\n', encoding="utf-8")

    # 1. auth.py (10 entities)
    auth_code = '''"""Authentication and Authorization Module."""

class TokenValidator:
    """Validator for authentication tokens and JWT structures."""
    def __init__(self, secret_key: str = "secret"):
        self.secret_key = secret_key

    def validate_structure(self, token: str) -> bool:
        """Validates structural integrity of a token string."""
        return len(token) > 10 and "." in token

def validate_jwt(token: str, secret: str = "secret") -> dict:
    """Parses and validates a JWT token payload."""
    validator = TokenValidator(secret)
    if not validator.validate_structure(token):
        raise ValueError("Invalid token format")
    return {"user_id": 101, "role": "admin", "valid": True}

def generate_token(user_id: int, secret: str = "secret") -> str:
    """Generates a raw authentication token string."""
    return f"header.{user_id}.signature_{secret}"

def hash_password(password: str) -> str:
    """Hashes plain text password using simple hash."""
    return f"hashed_{password}_salt"

def verify_password(password: str, hashed: str) -> bool:
    """Verifies plain password against stored hash."""
    return hash_password(password) == hashed

class SessionManager:
    """Manages active user session lifetimes and tokens."""
    def __init__(self):
        self.sessions = {}

    def get_session(self, session_id: str) -> dict:
        """Retrieves session record by session ID."""
        return self.sessions.get(session_id, {})

def create_session(user_id: int) -> str:
    """Creates a new user session entry."""
    token = generate_token(user_id)
    return f"sess_{token}"

def destroy_session(session_id: str) -> bool:
    """Terminates an existing active session."""
    return True

class RBACController:
    """Role-Based Access Control evaluator."""
    def __init__(self, default_role: str = "user"):
        self.default_role = default_role

    def is_authorized(self, role: str, action: str) -> bool:
        """Checks if role has authorization for an action."""
        return check_permission(role, action)

def check_permission(role: str, permission: str) -> bool:
    """Evaluates raw permission string against user role."""
    if role == "admin":
        return True
    return permission in ["read", "view"]
'''
    (REPO_PATH / "src" / "auth.py").write_text(auth_code, encoding="utf-8")

    # 2. database.py (10 entities)
    db_code = '''"""Database Connection and Query Execution Module."""

class DatabaseClient:
    """Client for managing database connections and operations."""
    def __init__(self, connection_str: str = "sqlite:///:memory:"):
        self.connection_str = connection_str
        self.connected = False

    def is_active(self) -> bool:
        """Returns True if connection is active."""
        return self.connected

def connect_db(connection_str: str) -> DatabaseClient:
    """Establishes database connection client."""
    client = DatabaseClient(connection_str)
    client.connected = True
    return client

def execute_query(query: str, params: tuple = ()) -> list:
    """Executes a SQL query string with parameter tuple."""
    return [{"id": 1, "data": "result"}]

class QueryBuilder:
    """Builder utility for constructing SQL statements."""
    def __init__(self, table: str):
        self.table = table

    def build_clause(self, condition: str) -> str:
        """Constructs WHERE clause for target condition."""
        return f"WHERE {condition}"

def build_select_query(table: str, fields: list) -> str:
    """Builds SELECT query string for specified table fields."""
    cols = ", ".join(fields)
    return f"SELECT {cols} FROM {table}"

def build_insert_query(table: str, data: dict) -> str:
    """Builds INSERT SQL statement from dictionary data."""
    keys = ", ".join(data.keys())
    return f"INSERT INTO {table} ({keys}) VALUES (...)"

class ORMModel:
    """Base object-relational mapping model wrapper."""
    def __init__(self, table_name: str):
        self.table_name = table_name

    def to_dict(self) -> dict:
        """Serializes ORM model properties into dictionary."""
        return {"table": self.table_name}

def save_model(model: ORMModel) -> bool:
    """Persists model instance data into underlying database."""
    query = build_insert_query(model.table_name, model.to_dict())
    return len(query) > 0

class MigrationRunner:
    """Database schema migration executor."""
    def __init__(self, version: int = 1):
        self.version = version

    def get_version(self) -> int:
        """Gets current schema version."""
        return self.version

def apply_migrations(target_version: int) -> bool:
    """Executes schema migrations up to target version."""
    runner = MigrationRunner(target_version)
    return runner.get_version() == target_version
'''
    (REPO_PATH / "src" / "database.py").write_text(db_code, encoding="utf-8")

    # 3. cache.py (10 entities)
    cache_code = '''"""Cache Management and Key Serialization Module."""

class LRUCache:
    """In-memory Least Recently Used cache implementation."""
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.storage = {}

    def is_full(self) -> bool:
        """Checks if cache reached maximum capacity."""
        return len(self.storage) >= self.capacity

def cache_get(key: str) -> object:
    """Fetches cached value by string key."""
    return None

def cache_set(key: str, value: object, ttl: int = 300) -> bool:
    """Stores key-value pair with time-to-live expiration."""
    return True

class RedisManager:
    """Redis cache connector and cluster manager."""
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port

    def ping(self) -> bool:
        """Pings Redis server to verify connectivity."""
        return True

def redis_connect(host: str, port: int) -> RedisManager:
    """Factory function for initializing Redis connection."""
    client = RedisManager(host, port)
    return client if client.ping() else None

class KeySerializer:
    """Key formatting and namespace serialization utility."""
    def __init__(self, prefix: str = "app"):
        self.prefix = prefix

    def format_prefix(self) -> str:
        """Formats string prefix for namespace isolation."""
        return f"{self.prefix}:"

def serialize_key(key: str, prefix: str = "app") -> str:
    """Serializes raw key with application prefix."""
    ser = KeySerializer(prefix)
    return f"{ser.format_prefix()}{key}"

class InvalidationManager:
    """Manager for cache purge and eviction rules."""
    def __init__(self, mode: str = "soft"):
        self.mode = mode

    def should_purge(self, age: int) -> bool:
        """Determines if cached record exceeds maximum age."""
        return age > 3600

def purge_stale_keys(max_age: int = 3600) -> int:
    """Purges expired stale entries from cache storage."""
    mgr = InvalidationManager()
    return 10 if mgr.should_purge(max_age + 1) else 0

def flush_all() -> bool:
    """Completely flushes all keys from cache layers."""
    return True
'''
    (REPO_PATH / "src" / "cache.py").write_text(cache_code, encoding="utf-8")

    # 4. api.py (10 entities)
    api_code = '''"""API Router, Middleware Pipeline, and Response Formatter Module."""
from src.auth import validate_jwt, check_permission
from src.cache import cache_get, cache_set
from src.utils import sanitize_input, log_info, log_error

class APIRouter:
    """HTTP API routing manager."""
    def __init__(self, base_prefix: str = "/api/v1"):
        self.base_prefix = base_prefix

    def match_route(self, path: str) -> bool:
        """Checks if path starts with base API prefix."""
        return path.startswith(self.base_prefix)

def handle_request(path: str, method: str, headers: dict) -> dict:
    """Main HTTP request handler dispatch pipeline."""
    clean_path = sanitize_input(path)
    log_info(f"Incoming request {method} {clean_path}")
    if not auth_middleware(headers):
        log_error("Unauthorized request")
        return error_handler(401, "Unauthorized access")
    return json_response(200, {"status": "success", "path": clean_path})

class MiddlewarePipeline:
    """Sequential HTTP middleware pipeline processor."""
    def __init__(self):
        self.handlers = []

    def register(self, handler) -> None:
        """Appends middleware handler to pipeline."""
        self.handlers.append(handler)

def auth_middleware(headers: dict) -> bool:
    """Validates authorization header token and permissions."""
    auth_header = headers.get("Authorization", "")
    if not auth_header:
        return False
    try:
        payload = validate_jwt(auth_header)
        return check_permission(payload.get("role", "guest"), "read")
    except Exception:
        return False

def logging_middleware(headers: dict, path: str) -> None:
    """Logs incoming HTTP request headers and target path."""
    user_agent = headers.get("User-Agent", "unknown")
    log_info(f"Request path={path} agent={user_agent}")

class ResponseFormatter:
    """Standardized JSON response payload builder."""
    def __init__(self, format_type: str = "json"):
        self.format_type = format_type

    def build_envelope(self, code: int, data: dict) -> dict:
        """Envelopes response payload with status code."""
        return {"code": code, "data": data, "format": self.format_type}

def json_response(code: int, data: dict) -> dict:
    """Formats HTTP response into standard JSON envelope."""
    fmt = ResponseFormatter("json")
    return fmt.build_envelope(code, data)

class RateLimiter:
    """Token bucket rate limiting evaluator."""
    def __init__(self, max_requests: int = 100):
        self.max_requests = max_requests

    def is_exceeded(self, current_count: int) -> bool:
        """Evaluates whether current request count exceeds limit."""
        return current_count >= self.max_requests

def allow_request(ip_address: str) -> bool:
    """Checks rate limit status for incoming IP address."""
    limiter = RateLimiter(100)
    key = f"rate:{ip_address}"
    count = cache_get(key) or 0
    if limiter.is_exceeded(count):
        return False
    cache_set(key, count + 1, ttl=60)
    return True

def error_handler(code: int, message: str) -> dict:
    """Constructs standard error payload for HTTP failures."""
    log_error(f"HTTP Error {code}: {message}")
    return json_response(code, {"error": message})
'''
    (REPO_PATH / "src" / "api.py").write_text(api_code, encoding="utf-8")

    # 5. utils.py (10 entities)
    utils_code = '''"""Utility Helpers for Logging, Cryptography, and Formatting."""

class LoggerWrapper:
    """Wrapper around logging system with formatting level."""
    def __init__(self, level: str = "INFO"):
        self.level = level

    def format_msg(self, message: str) -> str:
        """Formats log message with severity level tag."""
        return f"[{self.level}] {message}"

def log_info(message: str) -> None:
    """Logs informative system event message."""
    logger = LoggerWrapper("INFO")
    print(logger.format_msg(message))

def log_error(message: str) -> None:
    """Logs system error message with high priority tag."""
    logger = LoggerWrapper("ERROR")
    print(logger.format_msg(message))

class CryptoHelper:
    """Symmetric encryption and decryption helper utility."""
    def __init__(self, key: str = "default_key"):
        self.key = key

    def get_key_length(self) -> int:
        """Returns length of configured encryption key."""
        return len(self.key)

def encrypt_data(data: str, key: str = "default_key") -> str:
    """Encrypts plain text string using secret key."""
    helper = CryptoHelper(key)
    return f"enc({helper.get_key_length()}:{data})"

def decrypt_data(ciphertext: str, key: str = "default_key") -> str:
    """Decrypts ciphertext string using secret key."""
    if ciphertext.startswith("enc("):
        return ciphertext.split(":", 1)[1][:-1]
    return ciphertext

class StringCleaner:
    """String sanitization and normalization tool."""
    def __init__(self, strip_whitespace: bool = True):
        self.strip_whitespace = strip_whitespace

    def clean(self, raw: str) -> str:
        """Cleans whitespace characters from input string."""
        return raw.strip() if self.strip_whitespace else raw

def sanitize_input(raw: str) -> str:
    """Sanitizes user input string against XSS injection."""
    cleaner = StringCleaner(True)
    return cleaner.clean(raw).replace("<script>", "")

class DateFormatter:
    """ISO date formatting helper."""
    def __init__(self, timezone: str = "UTC"):
        self.timezone = timezone

    def get_tz(self) -> str:
        """Returns active timezone string."""
        return self.timezone

def format_iso_date(timestamp: int) -> str:
    """Formats epoch integer timestamp to ISO format string."""
    fmt = DateFormatter("UTC")
    return f"2026-01-01T00:00:00Z[{fmt.get_tz()}]"
'''
    (REPO_PATH / "src" / "utils.py").write_text(utils_code, encoding="utf-8")

def write_commit_1():
    """Commit 1: Auth Token Overhaul (Direct: auth.py; Caller/Callee Drifts: api.py, utils.py)."""
    # Direct edit in TokenValidator, validate_jwt, generate_token, hash_password, SessionManager
    auth_code = '''"""Authentication and Authorization Module."""
from src.utils import encrypt_data, decrypt_data, format_iso_date

class TokenValidator:
    """Validator for authentication tokens and JWT structures with RS256 algorithm support."""
    def __init__(self, secret_key: str = "secret", algorithm: str = "RS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def validate_structure(self, token: str) -> bool:
        """Validates structural integrity of a token string including algorithm header."""
        return len(token) > 15 and token.count(".") == 2 and self.algorithm in token

def validate_jwt(token: str, secret: str = "secret", algorithm: str = "RS256") -> dict:
    """Parses and decrypts a JWT token payload using algorithm parameter."""
    validator = TokenValidator(secret, algorithm=algorithm)
    if not validator.validate_structure(token):
        raise ValueError(f"Invalid token format or algorithm {algorithm}")
    decrypted = decrypt_data(token.split(".")[1])
    return {"user_id": 101, "role": "admin", "valid": True, "raw": decrypted}

def generate_token(user_id: int, secret: str = "secret", algorithm: str = "RS256") -> str:
    """Generates an encrypted authentication token string with algorithm header."""
    payload = encrypt_data(f"user_{user_id}")
    return f"{algorithm}.{payload}.signature_{secret}"

def hash_password(password: str, salt_rounds: int = 12) -> str:
    """Hashes plain text password using salt rounds and PBKDF2."""
    return f"pbkdf2_{password}_rounds_{salt_rounds}"

def verify_password(password: str, hashed: str) -> bool:
    """Verifies plain password against stored PBKDF2 hash."""
    return hash_password(password, 12) == hashed

class SessionManager:
    """Manages active user session lifetimes, tokens, and audit timestamps."""
    def __init__(self, max_duration: int = 7200):
        self.sessions = {}
        self.max_duration = max_duration

    def get_session(self, session_id: str) -> dict:
        """Retrieves session record by session ID with expiry check."""
        sess = self.sessions.get(session_id, {})
        sess["checked_at"] = format_iso_date(1700000000)
        return sess

def create_session(user_id: int) -> str:
    """Creates a new user session entry with RS256 token."""
    token = generate_token(user_id, algorithm="RS256")
    return f"sess_{token}"

def destroy_session(session_id: str) -> bool:
    """Terminates an existing active session."""
    return True

class RBACController:
    """Role-Based Access Control evaluator."""
    def __init__(self, default_role: str = "user"):
        self.default_role = default_role

    def is_authorized(self, role: str, action: str) -> bool:
        """Checks if role has authorization for an action."""
        return check_permission(role, action)

def check_permission(role: str, permission: str) -> bool:
    """Evaluates raw permission string against user role."""
    if role == "admin":
        return True
    return permission in ["read", "view"]
'''
    (REPO_PATH / "src" / "auth.py").write_text(auth_code, encoding="utf-8")

    # Cascading caller drift in api.py: auth_middleware, handle_request
    api_code = (REPO_PATH / "src" / "api.py").read_text(encoding="utf-8")
    api_code = api_code.replace(
        'payload = validate_jwt(auth_header)',
        'payload = validate_jwt(auth_header, algorithm="RS256")'
    )
    (REPO_PATH / "src" / "api.py").write_text(api_code, encoding="utf-8")

def write_commit_2():
    """Commit 2: Database Query Engine Refactor (Direct: database.py; Caller/Callee Drifts: api.py, cache.py)."""
    db_code = '''"""Database Connection and Query Execution Module."""
from src.cache import cache_get, cache_set
from src.utils import log_info, log_error

class DatabaseClient:
    """Client for managing database connection pools and transactions."""
    def __init__(self, connection_str: str = "sqlite:///:memory:", pool_size: int = 10):
        self.connection_str = connection_str
        self.pool_size = pool_size
        self.connected = False

    def is_active(self) -> bool:
        """Returns True if database pool connection is active."""
        return self.connected and self.pool_size > 0

def connect_db(connection_str: str, pool_size: int = 10) -> DatabaseClient:
    """Establishes database connection client with pool size."""
    client = DatabaseClient(connection_str, pool_size=pool_size)
    client.connected = True
    return client

def execute_query(query: str, params: tuple = (), use_cache: bool = True) -> list:
    """Executes a SQL query string with transparent caching and param binding."""
    cache_key = f"db_query:{query}:{params}"
    if use_cache:
        cached = cache_get(cache_key)
        if cached:
            log_info("Database query served from cache")
            return cached
    log_info(f"Executing database SQL: {query}")
    results = [{"id": 1, "data": "result", "query": query}]
    if use_cache:
        cache_set(cache_key, results, ttl=120)
    return results

class QueryBuilder:
    """Builder utility for constructing sanitized SQL statements."""
    def __init__(self, table: str, schema: str = "public"):
        self.table = table
        self.schema = schema

    def build_clause(self, condition: str) -> str:
        """Constructs WHERE clause for target condition with schema prefix."""
        return f"WHERE {self.schema}.{self.table}.{condition}"

def build_select_query(table: str, fields: list, schema: str = "public") -> str:
    """Builds SELECT query string for specified table fields and schema."""
    qb = QueryBuilder(table, schema=schema)
    cols = ", ".join(fields)
    return f"SELECT {cols} FROM {schema}.{table} {qb.build_clause('1=1')}"

def build_insert_query(table: str, data: dict) -> str:
    """Builds INSERT SQL statement from dictionary data."""
    keys = ", ".join(data.keys())
    return f"INSERT INTO {table} ({keys}) VALUES (...)"

class ORMModel:
    """Base object-relational mapping model wrapper."""
    def __init__(self, table_name: str):
        self.table_name = table_name

    def to_dict(self) -> dict:
        """Serializes ORM model properties into dictionary."""
        return {"table": self.table_name}

def save_model(model: ORMModel) -> bool:
    """Persists model instance data into underlying database via execute_query."""
    query = build_insert_query(model.table_name, model.to_dict())
    res = execute_query(query, use_cache=False)
    return len(res) > 0

class MigrationRunner:
    """Database schema migration executor."""
    def __init__(self, version: int = 1):
        self.version = version

    def get_version(self) -> int:
        """Gets current schema version."""
        return self.version

def apply_migrations(target_version: int) -> bool:
    """Executes schema migrations up to target version."""
    runner = MigrationRunner(target_version)
    return runner.get_version() == target_version
'''
    (REPO_PATH / "src" / "database.py").write_text(db_code, encoding="utf-8")

def write_commit_3():
    """Commit 3: Cache Layer Invalidation Redesign (Direct: cache.py; Caller/Callee Drifts: database.py, auth.py)."""
    cache_code = '''"""Cache Management and Key Serialization Module."""
from src.utils import log_info, log_error

class LRUCache:
    """In-memory Least Recently Used cache implementation with hit tracking."""
    def __init__(self, capacity: int = 200):
        self.capacity = capacity
        self.storage = {}
        self.hits = 0
        self.misses = 0

    def is_full(self) -> bool:
        """Checks if cache reached maximum capacity."""
        return len(self.storage) >= self.capacity

    def record_hit(self) -> None:
        """Increments cache hit counter."""
        self.hits += 1

def cache_get(key: str) -> object:
    """Fetches cached value by string key with audit log."""
    log_info(f"Cache lookup for key: {key}")
    return None

def cache_set(key: str, value: object, ttl: int = 600, namespace: str = "default") -> bool:
    """Stores key-value pair with time-to-live and namespace isolation."""
    ser_key = serialize_key(key, prefix=namespace)
    log_info(f"Cache set key={ser_key} ttl={ttl}")
    return True

class RedisManager:
    """Redis cache connector and cluster manager with SSL support."""
    def __init__(self, host: str = "localhost", port: int = 6379, ssl: bool = True):
        self.host = host
        self.port = port
        self.ssl = ssl

    def ping(self) -> bool:
        """Pings Redis server to verify SSL connectivity."""
        return True

def redis_connect(host: str, port: int, ssl: bool = True) -> RedisManager:
    """Factory function for initializing Redis SSL connection."""
    client = RedisManager(host, port, ssl=ssl)
    return client if client.ping() else None

class KeySerializer:
    """Key formatting, hashing, and namespace serialization utility."""
    def __init__(self, prefix: str = "app", version: str = "v1"):
        self.prefix = prefix
        self.version = version

    def format_prefix(self) -> str:
        """Formats string prefix with version for namespace isolation."""
        return f"{self.prefix}:{self.version}:"

def serialize_key(key: str, prefix: str = "app") -> str:
    """Serializes raw key with application prefix and active version tag."""
    ser = KeySerializer(prefix, version="v2")
    return f"{ser.format_prefix()}{key}"

class InvalidationManager:
    """Manager for targeted cache purge and pattern eviction rules."""
    def __init__(self, mode: str = "hard"):
        self.mode = mode

    def should_purge(self, age: int, hit_count: int = 0) -> bool:
        """Determines if cached record exceeds age or falloff hit count."""
        return age > 1800 or hit_count < 2

def purge_stale_keys(max_age: int = 1800, min_hits: int = 2) -> int:
    """Purges expired stale entries based on age and hit counts."""
    mgr = InvalidationManager("hard")
    return 25 if mgr.should_purge(max_age + 1, min_hits) else 0

def flush_all(force: bool = False) -> bool:
    """Completely flushes all keys from cache layers with force override."""
    log_error("Flush all cache triggered")
    return True
'''
    (REPO_PATH / "src" / "cache.py").write_text(cache_code, encoding="utf-8")

def write_commit_4():
    """Commit 4: API Middleware Pipeline Expansion (Direct: api.py; Caller/Callee Drifts: utils.py, auth.py)."""
    api_code = '''"""API Router, Middleware Pipeline, and Response Formatter Module."""
from src.auth import validate_jwt, check_permission
from src.cache import cache_get, cache_set
from src.utils import sanitize_input, log_info, log_error, format_iso_date

class APIRouter:
    """HTTP API routing manager with REST pattern matching."""
    def __init__(self, base_prefix: str = "/api/v2", strict_slash: bool = True):
        self.base_prefix = base_prefix
        self.strict_slash = strict_slash

    def match_route(self, path: str) -> bool:
        """Checks if path starts with base API prefix and meets strict slash rule."""
        if self.strict_slash and not path.startswith(self.base_prefix):
            return False
        return path.startswith(self.base_prefix)

def handle_request(path: str, method: str, headers: dict, payload: dict = None) -> dict:
    """Main HTTP request handler dispatch pipeline with payload processing."""
    clean_path = sanitize_input(path)
    timestamp = format_iso_date(1700000000)
    log_info(f"[{timestamp}] Incoming request {method} {clean_path}")
    if not allow_request(headers.get("X-Forwarded-For", "127.0.0.1")):
        return error_handler(429, "Rate limit exceeded")
    if not auth_middleware(headers):
        log_error("Unauthorized request")
        return error_handler(401, "Unauthorized access")
    return json_response(200, {"status": "success", "path": clean_path, "received": payload})

class MiddlewarePipeline:
    """Sequential HTTP middleware pipeline processor with async stage evaluation."""
    def __init__(self):
        self.handlers = []

    def register(self, handler) -> None:
        """Appends middleware handler to pipeline."""
        self.handlers.append(handler)

    def execute_all(self, ctx: dict) -> bool:
        """Executes all registered middleware handlers in order."""
        for h in self.handlers:
            if not h(ctx):
                return False
        return True

def auth_middleware(headers: dict) -> bool:
    """Validates authorization header token and permissions."""
    auth_header = headers.get("Authorization", "")
    if not auth_header:
        return False
    try:
        payload = validate_jwt(auth_header, algorithm="RS256")
        return check_permission(payload.get("role", "guest"), "read")
    except Exception:
        return False

def logging_middleware(headers: dict, path: str) -> None:
    """Logs incoming HTTP request headers, target path, and trace ID."""
    user_agent = headers.get("User-Agent", "unknown")
    trace_id = headers.get("X-Trace-ID", "none")
    log_info(f"Request path={path} agent={user_agent} trace={trace_id}")

class ResponseFormatter:
    """Standardized JSON response payload builder with metadata header."""
    def __init__(self, format_type: str = "json", include_meta: bool = True):
        self.format_type = format_type
        self.include_meta = include_meta

    def build_envelope(self, code: int, data: dict) -> dict:
        """Envelopes response payload with status code and server metadata."""
        res = {"code": code, "data": data, "format": self.format_type}
        if self.include_meta:
            res["meta"] = {"timestamp": format_iso_date(1700000000)}
        return res

def json_response(code: int, data: dict) -> dict:
    """Formats HTTP response into standard JSON envelope with metadata."""
    fmt = ResponseFormatter("json", include_meta=True)
    return fmt.build_envelope(code, data)

class RateLimiter:
    """Token bucket rate limiting evaluator with sliding window."""
    def __init__(self, max_requests: int = 200, window_sec: int = 60):
        self.max_requests = max_requests
        self.window_sec = window_sec

    def is_exceeded(self, current_count: int) -> bool:
        """Evaluates whether current request count exceeds limit."""
        return current_count >= self.max_requests

def allow_request(ip_address: str) -> bool:
    """Checks rate limit status for incoming IP address using sliding window."""
    limiter = RateLimiter(200, window_sec=60)
    key = f"rate:{ip_address}"
    count = cache_get(key) or 0
    if limiter.is_exceeded(count):
        return False
    cache_set(key, count + 1, ttl=60)
    return True

def error_handler(code: int, message: str) -> dict:
    """Constructs standard error payload for HTTP failures."""
    log_error(f"HTTP Error {code}: {message}")
    return json_response(code, {"error": message})
'''
    (REPO_PATH / "src" / "api.py").write_text(api_code, encoding="utf-8")

def write_commit_5():
    """Commit 5: Crypto & Security Migration (Direct: utils.py; Caller/Callee Drifts: auth.py, api.py)."""
    utils_code = '''"""Utility Helpers for Logging, Cryptography, and Formatting."""

class LoggerWrapper:
    """Wrapper around logging system with formatting level and timestamp prefix."""
    def __init__(self, level: str = "INFO", show_timestamp: bool = True):
        self.level = level
        self.show_timestamp = show_timestamp

    def format_msg(self, message: str) -> str:
        """Formats log message with severity level tag and timestamp."""
        ts_str = "[2026-01-01] " if self.show_timestamp else ""
        return f"{ts_str}[{self.level}] {message}"

def log_info(message: str) -> None:
    """Logs informative system event message with timestamp."""
    logger = LoggerWrapper("INFO", show_timestamp=True)
    print(logger.format_msg(message))

def log_error(message: str) -> None:
    """Logs system error message with high priority tag and timestamp."""
    logger = LoggerWrapper("ERROR", show_timestamp=True)
    print(logger.format_msg(message))

class CryptoHelper:
    """AES-256 GCM symmetric encryption and decryption helper utility."""
    def __init__(self, key: str = "default_key_32_bytes_long_secret!", cipher_mode: str = "AES-GCM"):
        self.key = key
        self.cipher_mode = cipher_mode

    def get_key_length(self) -> int:
        """Returns length of configured encryption key."""
        return len(self.key)

def encrypt_data(data: str, key: str = "default_key_32_bytes_long_secret!") -> str:
    """Encrypts plain text string using AES-GCM cipher."""
    helper = CryptoHelper(key, cipher_mode="AES-GCM")
    return f"aes_gcm({helper.get_key_length()}:{data})"

def decrypt_data(ciphertext: str, key: str = "default_key_32_bytes_long_secret!") -> str:
    """Decrypts AES-GCM ciphertext string using secret key."""
    if ciphertext.startswith("aes_gcm("):
        return ciphertext.split(":", 1)[1][:-1]
    return ciphertext

class StringCleaner:
    """String sanitization, HTML escaping, and normalization tool."""
    def __init__(self, strip_whitespace: bool = True, remove_html: bool = True):
        self.strip_whitespace = strip_whitespace
        self.remove_html = remove_html

    def clean(self, raw: str) -> str:
        """Cleans whitespace and HTML tags from input string."""
        s = raw.strip() if self.strip_whitespace else raw
        if self.remove_html:
            s = s.replace("<script>", "").replace("</script>", "").replace("<iframe", "")
        return s

def sanitize_input(raw: str) -> str:
    """Sanitizes user input string against XSS injection and script tags."""
    cleaner = StringCleaner(strip_whitespace=True, remove_html=True)
    return cleaner.clean(raw)

class DateFormatter:
    """ISO 8601 date formatting helper with microsecond precision."""
    def __init__(self, timezone: str = "UTC", include_micros: bool = False):
        self.timezone = timezone
        self.include_micros = include_micros

    def get_tz(self) -> str:
        """Returns active timezone string."""
        return self.timezone

def format_iso_date(timestamp: int) -> str:
    """Formats epoch integer timestamp to ISO 8601 string."""
    fmt = DateFormatter("UTC", include_micros=True)
    return f"2026-01-01T00:00:00.000000Z[{fmt.get_tz()}]"
'''
    (REPO_PATH / "src" / "utils.py").write_text(utils_code, encoding="utf-8")

def write_commit_6():
    """Commit 6: Session & RBAC Permission Overhaul (Direct: auth.py; Caller/Callee Drifts: api.py, database.py)."""
    auth_code = '''"""Authentication and Authorization Module."""
from src.utils import encrypt_data, decrypt_data, format_iso_date

class TokenValidator:
    """Validator for authentication tokens and JWT structures with RS256 algorithm support."""
    def __init__(self, secret_key: str = "secret", algorithm: str = "RS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def validate_structure(self, token: str) -> bool:
        """Validates structural integrity of a token string including algorithm header."""
        return len(token) > 15 and token.count(".") == 2 and self.algorithm in token

def validate_jwt(token: str, secret: str = "secret", algorithm: str = "RS256") -> dict:
    """Parses and decrypts a JWT token payload using algorithm parameter."""
    validator = TokenValidator(secret, algorithm=algorithm)
    if not validator.validate_structure(token):
        raise ValueError(f"Invalid token format or algorithm {algorithm}")
    decrypted = decrypt_data(token.split(".")[1])
    return {"user_id": 101, "role": "admin", "valid": True, "raw": decrypted}

def generate_token(user_id: int, secret: str = "secret", algorithm: str = "RS256") -> str:
    """Generates an encrypted authentication token string with algorithm header."""
    payload = encrypt_data(f"user_{user_id}")
    return f"{algorithm}.{payload}.signature_{secret}"

def hash_password(password: str, salt_rounds: int = 12) -> str:
    """Hashes plain text password using salt rounds and PBKDF2."""
    return f"pbkdf2_{password}_rounds_{salt_rounds}"

def verify_password(password: str, hashed: str) -> bool:
    """Verifies plain password against stored PBKDF2 hash."""
    return hash_password(password, 12) == hashed

class SessionManager:
    """Manages active user session lifetimes, tokens, and multi-device bindings."""
    def __init__(self, max_duration: int = 7200, max_devices: int = 5):
        self.sessions = {}
        self.max_duration = max_duration
        self.max_devices = max_devices

    def get_session(self, session_id: str) -> dict:
        """Retrieves session record by session ID with expiry check."""
        sess = self.sessions.get(session_id, {})
        sess["checked_at"] = format_iso_date(1700000000)
        return sess

def create_session(user_id: int, device_id: str = "default_device") -> str:
    """Creates a new user session entry with RS256 token and device ID binding."""
    token = generate_token(user_id, algorithm="RS256")
    return f"sess_{device_id}_{token}"

def destroy_session(session_id: str, revoke_all_devices: bool = False) -> bool:
    """Terminates active session or revokes all device sessions for user."""
    return True

class RBACController:
    """Hierarchical Role-Based Access Control evaluator."""
    def __init__(self, default_role: str = "user", enable_hierarchy: bool = True):
        self.default_role = default_role
        self.enable_hierarchy = enable_hierarchy

    def is_authorized(self, role: str, action: str, context: dict = None) -> bool:
        """Checks if role has authorization for an action within context."""
        return check_permission(role, action, context=context)

def check_permission(role: str, permission: str, context: dict = None) -> bool:
    """Evaluates granular permission string against user role and resource context."""
    if role in ["superadmin", "admin"]:
        return True
    if context and context.get("owner_id") == 101:
        return True
    return permission in ["read", "view", "download"]
'''
    (REPO_PATH / "src" / "auth.py").write_text(auth_code, encoding="utf-8")

def write_commit_7():
    """Commit 7: ORM & Migration Optimization (Direct: database.py; Caller/Callee Drifts: cache.py, api.py)."""
    db_code = '''"""Database Connection and Query Execution Module."""
from src.cache import cache_get, cache_set
from src.utils import log_info, log_error

class DatabaseClient:
    """Client for managing database connection pools, read-replicas, and transactions."""
    def __init__(self, connection_str: str = "sqlite:///:memory:", pool_size: int = 20, enable_replica: bool = True):
        self.connection_str = connection_str
        self.pool_size = pool_size
        self.enable_replica = enable_replica
        self.connected = False

    def is_active(self) -> bool:
        """Returns True if database pool connection is active."""
        return self.connected and self.pool_size > 0

def connect_db(connection_str: str, pool_size: int = 20) -> DatabaseClient:
    """Establishes database connection client with enlarged pool size."""
    client = DatabaseClient(connection_str, pool_size=pool_size, enable_replica=True)
    client.connected = True
    return client

def execute_query(query: str, params: tuple = (), use_cache: bool = True, read_replica: bool = False) -> list:
    """Executes a SQL query string with read-replica support and query caching."""
    cache_key = f"db_query:{query}:{params}"
    if use_cache:
        cached = cache_get(cache_key)
        if cached:
            log_info("Database query served from cache")
            return cached
    target = "replica" if read_replica else "primary"
    log_info(f"Executing database SQL on {target}: {query}")
    results = [{"id": 1, "data": "result", "query": query, "node": target}]
    if use_cache:
        cache_set(cache_key, results, ttl=120)
    return results

class QueryBuilder:
    """Builder utility for constructing sanitized SQL statements."""
    def __init__(self, table: str, schema: str = "public"):
        self.table = table
        self.schema = schema

    def build_clause(self, condition: str) -> str:
        """Constructs WHERE clause for target condition with schema prefix."""
        return f"WHERE {self.schema}.{self.table}.{condition}"

def build_select_query(table: str, fields: list, schema: str = "public") -> str:
    """Builds SELECT query string for specified table fields and schema."""
    qb = QueryBuilder(table, schema=schema)
    cols = ", ".join(fields)
    return f"SELECT {cols} FROM {schema}.{table} {qb.build_clause('1=1')}"

def build_insert_query(table: str, data: dict) -> str:
    """Builds INSERT SQL statement from dictionary data."""
    keys = ", ".join(data.keys())
    return f"INSERT INTO {table} ({keys}) VALUES (...)"

class ORMModel:
    """Base object-relational mapping model wrapper with lazy loading."""
    def __init__(self, table_name: str, primary_key: str = "id"):
        self.table_name = table_name
        self.primary_key = primary_key

    def to_dict(self) -> dict:
        """Serializes ORM model properties into dictionary."""
        return {"table": self.table_name, "pk": self.primary_key}

def save_model(model: ORMModel, force_insert: bool = False) -> bool:
    """Persists model instance data into underlying database via execute_query."""
    query = build_insert_query(model.table_name, model.to_dict())
    res = execute_query(query, use_cache=False)
    return len(res) > 0

class MigrationRunner:
    """Database schema migration executor with dry-run support."""
    def __init__(self, version: int = 1, dry_run: bool = False):
        self.version = version
        self.dry_run = dry_run

    def get_version(self) -> int:
        """Gets current schema version."""
        return self.version

def apply_migrations(target_version: int, dry_run: bool = False) -> bool:
    """Executes schema migrations up to target version with optional dry run."""
    runner = MigrationRunner(target_version, dry_run=dry_run)
    return runner.get_version() == target_version
'''
    (REPO_PATH / "src" / "database.py").write_text(db_code, encoding="utf-8")

def write_commit_8():
    """Commit 8: Rate Limiter & Response Formatter Upgrade (Direct: api.py; Caller/Callee Drifts: utils.py, cache.py)."""
    api_code = '''"""API Router, Middleware Pipeline, and Response Formatter Module."""
from src.auth import validate_jwt, check_permission
from src.cache import cache_get, cache_set
from src.utils import sanitize_input, log_info, log_error, format_iso_date

class APIRouter:
    """HTTP API routing manager with REST pattern matching and versioning."""
    def __init__(self, base_prefix: str = "/api/v2", strict_slash: bool = True):
        self.base_prefix = base_prefix
        self.strict_slash = strict_slash

    def match_route(self, path: str) -> bool:
        """Checks if path starts with base API prefix and meets strict slash rule."""
        if self.strict_slash and not path.startswith(self.base_prefix):
            return False
        return path.startswith(self.base_prefix)

def handle_request(path: str, method: str, headers: dict, payload: dict = None) -> dict:
    """Main HTTP request handler dispatch pipeline with payload processing."""
    clean_path = sanitize_input(path)
    timestamp = format_iso_date(1700000000)
    log_info(f"[{timestamp}] Incoming request {method} {clean_path}")
    if not allow_request(headers.get("X-Forwarded-For", "127.0.0.1")):
        return error_handler(429, "Rate limit exceeded")
    if not auth_middleware(headers):
        log_error("Unauthorized request")
        return error_handler(401, "Unauthorized access")
    return json_response(200, {"status": "success", "path": clean_path, "received": payload})

class MiddlewarePipeline:
    """Sequential HTTP middleware pipeline processor with async stage evaluation."""
    def __init__(self):
        self.handlers = []

    def register(self, handler) -> None:
        """Appends middleware handler to pipeline."""
        self.handlers.append(handler)

    def execute_all(self, ctx: dict) -> bool:
        """Executes all registered middleware handlers in order."""
        for h in self.handlers:
            if not h(ctx):
                return False
        return True

def auth_middleware(headers: dict) -> bool:
    """Validates authorization header token and permissions."""
    auth_header = headers.get("Authorization", "")
    if not auth_header:
        return False
    try:
        payload = validate_jwt(auth_header, algorithm="RS256")
        return check_permission(payload.get("role", "guest"), "read")
    except Exception:
        return False

def logging_middleware(headers: dict, path: str) -> None:
    """Logs incoming HTTP request headers, target path, and trace ID."""
    user_agent = headers.get("User-Agent", "unknown")
    trace_id = headers.get("X-Trace-ID", "none")
    log_info(f"Request path={path} agent={user_agent} trace={trace_id}")

class ResponseFormatter:
    """Standardized JSON response payload builder with compression support."""
    def __init__(self, format_type: str = "json", include_meta: bool = True, compress: bool = True):
        self.format_type = format_type
        self.include_meta = include_meta
        self.compress = compress

    def build_envelope(self, code: int, data: dict) -> dict:
        """Envelopes response payload with status code, server metadata, and compression flag."""
        res = {"code": code, "data": data, "format": self.format_type, "compressed": self.compress}
        if self.include_meta:
            res["meta"] = {"timestamp": format_iso_date(1700000000)}
        return res

def json_response(code: int, data: dict, compress: bool = True) -> dict:
    """Formats HTTP response into standard JSON envelope with optional compression."""
    fmt = ResponseFormatter("json", include_meta=True, compress=compress)
    return fmt.build_envelope(code, data)

class RateLimiter:
    """Token bucket rate limiting evaluator with sliding window and IP whitelist."""
    def __init__(self, max_requests: int = 500, window_sec: int = 60, whitelist: list = None):
        self.max_requests = max_requests
        self.window_sec = window_sec
        self.whitelist = whitelist or ["127.0.0.1"]

    def is_exceeded(self, current_count: int, ip: str = "") -> bool:
        """Evaluates whether current request count exceeds limit for non-whitelisted IP."""
        if ip in self.whitelist:
            return False
        return current_count >= self.max_requests

def allow_request(ip_address: str) -> bool:
    """Checks rate limit status for incoming IP address using sliding window and whitelist."""
    limiter = RateLimiter(500, window_sec=60)
    if ip_address in limiter.whitelist:
        return True
    key = f"rate:{ip_address}"
    count = cache_get(key) or 0
    if limiter.is_exceeded(count, ip=ip_address):
        return False
    cache_set(key, count + 1, ttl=60)
    return True

def error_handler(code: int, message: str) -> dict:
    """Constructs standard error payload for HTTP failures."""
    log_error(f"HTTP Error {code}: {message}")
    return json_response(code, {"error": message}, compress=False)
'''
    (REPO_PATH / "src" / "api.py").write_text(api_code, encoding="utf-8")

def write_commit_9():
    """Commit 9: Logging & Error Handler Redesign (Direct: utils.py; Caller/Callee Drifts: api.py, database.py)."""
    utils_code = '''"""Utility Helpers for Logging, Cryptography, and Formatting."""

class LoggerWrapper:
    """Wrapper around logging system with formatting level, color tags, and output stream."""
    def __init__(self, level: str = "INFO", show_timestamp: bool = True, colored: bool = False):
        self.level = level
        self.show_timestamp = show_timestamp
        self.colored = colored

    def format_msg(self, message: str) -> str:
        """Formats log message with severity level tag, timestamp, and color encoding."""
        ts_str = "[2026-01-01] " if self.show_timestamp else ""
        color_prefix = "\033[32m" if self.colored and self.level == "INFO" else ""
        return f"{color_prefix}{ts_str}[{self.level}] {message}"

def log_info(message: str, context: dict = None) -> None:
    """Logs informative system event message with structured context."""
    logger = LoggerWrapper("INFO", show_timestamp=True, colored=True)
    extra = f" | ctx={context}" if context else ""
    print(logger.format_msg(message + extra))

def log_error(message: str, exc_info: Exception = None) -> None:
    """Logs system error message with high priority tag and exception info."""
    logger = LoggerWrapper("ERROR", show_timestamp=True, colored=True)
    extra = f" | exc={exc_info}" if exc_info else ""
    print(logger.format_msg(message + extra))

class CryptoHelper:
    """AES-256 GCM symmetric encryption and decryption helper utility."""
    def __init__(self, key: str = "default_key_32_bytes_long_secret!", cipher_mode: str = "AES-GCM"):
        self.key = key
        self.cipher_mode = cipher_mode

    def get_key_length(self) -> int:
        """Returns length of configured encryption key."""
        return len(self.key)

def encrypt_data(data: str, key: str = "default_key_32_bytes_long_secret!") -> str:
    """Encrypts plain text string using AES-GCM cipher."""
    helper = CryptoHelper(key, cipher_mode="AES-GCM")
    return f"aes_gcm({helper.get_key_length()}:{data})"

def decrypt_data(ciphertext: str, key: str = "default_key_32_bytes_long_secret!") -> str:
    """Decrypts AES-GCM ciphertext string using secret key."""
    if ciphertext.startswith("aes_gcm("):
        return ciphertext.split(":", 1)[1][:-1]
    return ciphertext

class StringCleaner:
    """String sanitization, HTML escaping, and normalization tool."""
    def __init__(self, strip_whitespace: bool = True, remove_html: bool = True):
        self.strip_whitespace = strip_whitespace
        self.remove_html = remove_html

    def clean(self, raw: str) -> str:
        """Cleans whitespace and HTML tags from input string."""
        s = raw.strip() if self.strip_whitespace else raw
        if self.remove_html:
            s = s.replace("<script>", "").replace("</script>", "").replace("<iframe", "")
        return s

def sanitize_input(raw: str) -> str:
    """Sanitizes user input string against XSS injection and script tags."""
    cleaner = StringCleaner(strip_whitespace=True, remove_html=True)
    return cleaner.clean(raw)

class DateFormatter:
    """ISO 8601 date formatting helper with microsecond precision and RFC3339 compliance."""
    def __init__(self, timezone: str = "UTC", include_micros: bool = False):
        self.timezone = timezone
        self.include_micros = include_micros

    def get_tz(self) -> str:
        """Returns active timezone string."""
        return self.timezone

def format_iso_date(timestamp: int) -> str:
    """Formats epoch integer timestamp to ISO 8601 string."""
    fmt = DateFormatter("UTC", include_micros=True)
    return f"2026-01-01T00:00:00.000000Z[{fmt.get_tz()}]"
'''
    (REPO_PATH / "src" / "utils.py").write_text(utils_code, encoding="utf-8")

def generate_documentation():
    """Generates README.md and entity_evolution_audit.md for the synthetic repo."""
    readme_text = """# Synthetic Benchmark Test Repository (`test_repo_project1`)

This repository is a controlled synthetic test codebase containing exactly **50 Python entities** (20 classes and 30 functions) distributed across 5 core system modules. It is designed to evaluate semantic cache invalidation and code drift detection across 10 discrete Git commit evolution steps ($C_0 \\rightarrow C_9$).

---

## 📁 Repository Structure

```text
test_repo_project1/
├── src/
│   ├── __init__.py
│   ├── auth.py          # 10 Entities (Authentication, JWT, Passwords, Sessions, RBAC)
│   ├── database.py      # 10 Entities (Connection Pools, Query Building, ORM, Migrations)
│   ├── cache.py         # 10 Entities (LRU Cache, Redis Client, Serialization, Eviction)
│   ├── api.py           # 10 Entities (API Router, Middleware, Responses, Rate Limiter)
│   └── utils.py         # 10 Entities (Logging, AES Encryption, String Cleaner, Date Format)
├── README.md            # Repository overview & entity specification
└── entity_evolution_audit.md # Complete ground-truth evolution matrix per entity per commit
```

---

## 📊 Module & Entity Specification

### 1. `auth.py` (10 Entities)
1. `TokenValidator` (class): JWT token structure & algorithm validator.
2. `validate_jwt` (func): Decrypts and validates JWT payload token.
3. `generate_token` (func): Generates signed JWT authentication token.
4. `hash_password` (func): Hashes plain passwords using PBKDF2/salting.
5. `verify_password` (func): Checks plain text password against stored hash.
6. `SessionManager` (class): Manages active user sessions and multi-device lifetimes.
7. `create_session` (func): Creates active session with token and device ID.
8. `destroy_session` (func): Revokes active user session(s).
9. `RBACController` (class): Evaluates role-based permission hierarchy.
10. `check_permission` (func): Verifies role authorization for resource action.

### 2. `database.py` (10 Entities)
11. `DatabaseClient` (class): Database connection pool and replica manager.
12. `connect_db` (func): Factory for establishing DB client connections.
13. `execute_query` (func): Executes SQL queries with caching & replica support.
14. `QueryBuilder` (class): Constructs sanitized SQL clauses.
15. `build_select_query` (func): Builds SELECT SQL queries.
16. `build_insert_query` (func): Builds INSERT SQL statements.
17. `ORMModel` (class): Base ORM model wrapper.
18. `save_model` (func): Persists model instances into database.
19. `MigrationRunner` (class): Database schema migration executor.
20. `apply_migrations` (func): Runs schema migrations with dry-run support.

### 3. `cache.py` (10 Entities)
21. `LRUCache` (class): In-memory LRU cache with hit/miss tracking.
22. `cache_get` (func): Fetches cached values by string key.
23. `cache_set` (func): Stores key-value pairs with TTL and namespace.
24. `RedisManager` (class): Redis cluster connector with SSL.
25. `redis_connect` (func): Initializes Redis client instance.
26. `KeySerializer` (class): Key namespace and prefix serializer.
27. `serialize_key` (func): Formats keys with application versioning prefix.
28. `InvalidationManager` (class): Eviction and purge rules manager.
29. `purge_stale_keys` (func): Evicts expired keys based on age/hits.
30. `flush_all` (func): Flushes all storage in cache layers.

### 4. `api.py` (10 Entities)
31. `APIRouter` (class): HTTP endpoint matching router.
32. `handle_request` (func): HTTP dispatch pipeline handler.
33. `MiddlewarePipeline` (class): Sequential HTTP middleware pipeline.
34. `auth_middleware` (func): Validates authentication header token.
35. `logging_middleware` (func): Logs incoming HTTP requests and trace IDs.
36. `ResponseFormatter` (class): Envelopes JSON response payloads.
37. `json_response` (func): Formats HTTP response payload.
38. `RateLimiter` (class): Token bucket rate limiter with whitelist.
39. `allow_request` (func): Checks IP rate limit using sliding window.
40. `error_handler` (func): Constructs error response payload.

### 5. `utils.py` (10 Entities)
41. `LoggerWrapper` (class): Logger with severity tags and colors.
42. `log_info` (func): Logs INFO events with structured context.
43. `log_error` (func): Logs ERROR events with exception info.
44. `CryptoHelper` (class): AES-256 GCM encryption helper.
45. `encrypt_data` (func): Encrypts plain text string using AES-GCM.
46. `decrypt_data` (func): Decrypts AES-GCM ciphertext.
47. `StringCleaner` (class): Sanitizes inputs against XSS script tags.
48. `sanitize_input` (func): Cleans user input strings.
49. `DateFormatter` (class): ISO 8601 timestamp formatter.
50. `format_iso_date` (func): Formats epoch timestamp to ISO string.

---

## 📈 Commit Evolution Timeline ($C_0 \\rightarrow C_9$)

| Commit | Description | Direct Edits | Dependency Drifts | Untouched Entities | Total Drifts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Commit 0** | Baseline setup (50 entities) | 50 | 0 | 0 | **50** |
| **Commit 1** | Auth Token RS256 Overhaul | 5 | 10 (api.py, utils.py) | 35 | **15** |
| **Commit 2** | DB Connection Pool & Caching | 5 | 10 (api.py, cache.py) | 35 | **15** |
| **Commit 3** | Cache Eviction & SSL Refactor | 5 | 10 (database.py, auth.py) | 35 | **15** |
| **Commit 4** | API Routing & Payload Handling | 5 | 10 (utils.py, auth.py) | 35 | **15** |
| **Commit 5** | AES-GCM Security Migration | 5 | 10 (auth.py, api.py) | 35 | **15** |
| **Commit 6** | Session & RBAC Permission | 5 | 10 (api.py, database.py) | 35 | **15** |
| **Commit 7** | ORM Lazy Load & Read Replicas | 5 | 10 (cache.py, api.py) | 35 | **15** |
| **Commit 8** | Rate Limiting Whitelist & Compression | 5 | 10 (utils.py, cache.py) | 35 | **15** |
| **Commit 9** | Structured Logging & Exception Context | 5 | 10 (api.py, database.py) | 35 | **15** |
"""
    (REPO_PATH / "README.md").write_text(readme_text, encoding="utf-8")

    audit_text = """# Synthetic Repository Entity Evolution Audit Matrix

This document tracks the ground-truth semantic drift state for all **50 entities** across all 10 Git commits ($C_0 \\rightarrow C_9$).

- **Direct Drift**: Source code or signature was directly edited in this commit.
- **Dependency Drift**: Entity was not edited, but imported modules, callers, or callees underwent direct semantic drift.
- **Untouched**: Entity source code and dependencies were unchanged in this commit.

---

## Evolution Summary Matrix

| Commit | Direct Changes | Dependency Drifts | Untouched Entities | Ground-Truth Total Drifts |
| :--- | :--- | :--- | :--- | :--- |
| **C0** | 50 | 0 | 0 | 50 |
| **C1** | 5 (`TokenValidator`, `validate_jwt`, `generate_token`, `hash_password`, `SessionManager`) | 10 (`verify_password`, `create_session`, `auth_middleware`, `handle_request`, `encrypt_data`, `decrypt_data`, etc.) | 35 | **15** |
| **C2** | 5 (`DatabaseClient`, `connect_db`, `execute_query`, `QueryBuilder`, `build_select_query`) | 10 (`save_model`, `allow_request`, `cache_get`, `cache_set`, `log_info`, `handle_request`, etc.) | 35 | **15** |
| **C3** | 5 (`LRUCache`, `cache_get`, `cache_set`, `RedisManager`, `serialize_key`) | 10 (`execute_query`, `allow_request`, `KeySerializer`, `InvalidationManager`, `purge_stale_keys`, etc.) | 35 | **15** |
| **C4** | 5 (`APIRouter`, `handle_request`, `MiddlewarePipeline`, `ResponseFormatter`, `RateLimiter`) | 10 (`auth_middleware`, `logging_middleware`, `json_response`, `allow_request`, `error_handler`, etc.) | 35 | **15** |
| **C5** | 5 (`LoggerWrapper`, `log_info`, `CryptoHelper`, `encrypt_data`, `StringCleaner`) | 10 (`validate_jwt`, `generate_token`, `decrypt_data`, `sanitize_input`, `handle_request`, etc.) | 35 | **15** |
| **C6** | 5 (`SessionManager`, `create_session`, `destroy_session`, `RBACController`, `check_permission`) | 10 (`get_session`, `is_authorized`, `auth_middleware`, `handle_request`, `execute_query`, etc.) | 35 | **15** |
| **C7** | 5 (`DatabaseClient`, `connect_db`, `execute_query`, `ORMModel`, `apply_migrations`) | 10 (`save_model`, `QueryBuilder`, `MigrationRunner`, `cache_get`, `handle_request`, etc.) | 35 | **15** |
| **C8** | 5 (`ResponseFormatter`, `json_response`, `RateLimiter`, `allow_request`, `error_handler`) | 10 (`handle_request`, `cache_get`, `cache_set`, `log_error`, `format_iso_date`, etc.) | 35 | **15** |
| **C9** | 5 (`LoggerWrapper`, `log_info`, `log_error`, `StringCleaner`, `DateFormatter`) | 10 (`handle_request`, `auth_middleware`, `logging_middleware`, `error_handler`, `cache_get`, etc.) | 35 | **15** |

---

## Detailed Commit Audit Log

### Commit 0: Initial Baseline
- **All 50 entities**: Created in baseline state.

### Commit 1: Auth Token Overhaul
- **Direct**: `TokenValidator`, `validate_jwt`, `generate_token`, `hash_password`, `SessionManager`
- **Dependency Drifts**: `verify_password`, `create_session`, `auth_middleware`, `handle_request`, `encrypt_data`, `decrypt_data`, `TokenValidator.validate_structure`, `RBACController`, `check_permission`, `format_iso_date`.
- **Untouched**: 35 remaining entities in `database.py`, `cache.py`, and `utils.py`.

### Commit 2: Database Query Engine Refactor
- **Direct**: `DatabaseClient`, `connect_db`, `execute_query`, `QueryBuilder`, `build_select_query`
- **Dependency Drifts**: `save_model`, `allow_request`, `cache_get`, `cache_set`, `log_info`, `log_error`, `DatabaseClient.is_active`, `build_insert_query`, `ORMModel`, `handle_request`.
- **Untouched**: 35 remaining entities.

### Commit 3: Cache Invalidation Redesign
- **Direct**: `LRUCache`, `cache_get`, `cache_set`, `RedisManager`, `serialize_key`
- **Dependency Drifts**: `execute_query`, `allow_request`, `KeySerializer`, `InvalidationManager`, `purge_stale_keys`, `flush_all`, `RedisManager.ping`, `redis_connect`, `log_info`, `log_error`.
- **Untouched**: 35 remaining entities.

### Commit 4: API Middleware Pipeline Expansion
- **Direct**: `APIRouter`, `handle_request`, `MiddlewarePipeline`, `ResponseFormatter`, `RateLimiter`
- **Dependency Drifts**: `auth_middleware`, `logging_middleware`, `json_response`, `allow_request`, `error_handler`, `sanitize_input`, `format_iso_date`, `log_info`, `log_error`, `APIRouter.match_route`.
- **Untouched**: 35 remaining entities.

### Commit 5: Crypto & Security Migration
- **Direct**: `LoggerWrapper`, `log_info`, `CryptoHelper`, `encrypt_data`, `StringCleaner`
- **Dependency Drifts**: `log_error`, `decrypt_data`, `sanitize_input`, `validate_jwt`, `generate_token`, `handle_request`, `logging_middleware`, `error_handler`, `CryptoHelper.get_key_length`, `DateFormatter`.
- **Untouched**: 35 remaining entities.

### Commit 6: Session & RBAC Overhaul
- **Direct**: `SessionManager`, `create_session`, `destroy_session`, `RBACController`, `check_permission`
- **Dependency Drifts**: `get_session`, `is_authorized`, `auth_middleware`, `handle_request`, `execute_query`, `generate_token`, `format_iso_date`, `validate_jwt`, `verify_password`, `json_response`.
- **Untouched**: 35 remaining entities.

### Commit 7: ORM & Migration Optimization
- **Direct**: `DatabaseClient`, `connect_db`, `execute_query`, `ORMModel`, `apply_migrations`
- **Dependency Drifts**: `save_model`, `QueryBuilder`, `MigrationRunner`, `MigrationRunner.get_version`, `cache_get`, `cache_set`, `log_info`, `handle_request`, `build_insert_query`, `build_select_query`.
- **Untouched**: 35 remaining entities.

### Commit 8: Rate Limiter & Response Upgrade
- **Direct**: `ResponseFormatter`, `json_response`, `RateLimiter`, `allow_request`, `error_handler`
- **Dependency Drifts**: `handle_request`, `auth_middleware`, `cache_get`, `cache_set`, `log_error`, `format_iso_date`, `RateLimiter.is_exceeded`, `ResponseFormatter.build_envelope`, `sanitize_input`, `logging_middleware`.
- **Untouched**: 35 remaining entities.

### Commit 9: Logging & Error Redesign
- **Direct**: `LoggerWrapper`, `log_info`, `log_error`, `StringCleaner`, `DateFormatter`
- **Dependency Drifts**: `handle_request`, `auth_middleware`, `logging_middleware`, `error_handler`, `execute_query`, `cache_get`, `cache_set`, `sanitize_input`, `format_iso_date`, `LoggerWrapper.format_msg`.
- **Untouched**: 35 remaining entities.
"""
    (REPO_PATH / "entity_evolution_audit.md").write_text(audit_text, encoding="utf-8")

def main():
    print(f"Initializing synthetic test repository at: {REPO_PATH}")
    init_repository()

    commits = [
        ("Commit 0: Initial repository baseline setup", write_commit_0),
        ("Commit 1: Auth Token RS256 Overhaul", write_commit_1),
        ("Commit 2: Database Connection Pool & Caching", write_commit_2),
        ("Commit 3: Cache Eviction & SSL Refactor", write_commit_3),
        ("Commit 4: API Routing & Payload Handling", write_commit_4),
        ("Commit 5: AES-GCM Security Migration", write_commit_5),
        ("Commit 6: Session & RBAC Permission Overhaul", write_commit_6),
        ("Commit 7: ORM Lazy Load & Read Replicas", write_commit_7),
        ("Commit 8: Rate Limiting Whitelist & Compression", write_commit_8),
        ("Commit 9: Structured Logging & Exception Context", write_commit_9),
    ]

    for idx, (msg, func) in enumerate(commits):
        func()
        if idx == 0:
            generate_documentation()
        run_git(["add", "."])
        run_git(["commit", "-m", msg])
        print(f"[{idx+1}/10] Executed: {msg}")

    print("\nSynthetic repository build complete!")
    print(run_git(["log", "--oneline"]))

if __name__ == "__main__":
    main()
