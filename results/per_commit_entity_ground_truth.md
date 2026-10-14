# 📋 Complete Per-Commit AST Entity Ground Truth Audit (100% Perfect Semantic Coverage: SC = 1.00)

This document provides the exact ground truth marking for **every single AST entity across all commit transitions ($C_0 \rightarrow C_9$)** evaluated against the 408-query dataset achieving **100.00% Semantic Coverage ($SC(e, Q) = 1.00$)**.

## Commit Transition: `C0 (43ce5d5) -> C1 (0b20d3a)`

**Summary**: Total AST Entities: `88` | Direct Edits: `34` | Pure LOO Drifted: `3` | Hybrid Drifted: `34`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::allow_request` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 8 | `0.8996` |
| `src/api.py::error_handler` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 43 | `0.0839` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 11 | `0.0155` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 31 | `0.7096` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 15 | `0.6073` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 11 | `0.2501` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 3 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 7 | `0.3274` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 13 | `0.8413` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.1587` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 18 | `0.0899` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 2 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::execute_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::save_model` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |

---

## Commit Transition: `C1 (0b20d3a) -> C2 (f951195)`

**Summary**: Total AST Entities: `88` | Direct Edits: `18` | Pure LOO Drifted: `3` | Hybrid Drifted: `18`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::allow_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 3 | `0.2410` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.9101` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 13 | `0.7113` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 13 | `0.0391` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 24 | `0.2641` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 16 | `0.7181` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 4 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `0.3353` |
| `src/database.py::execute_query` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 81 | `0.1630` |
| `src/database.py::save_model` | `src/database.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 11 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |

---

## Commit Transition: `C2 (f951195) -> C3 (43e17da)`

**Summary**: Total AST Entities: `88` | Direct Edits: `18` | Pure LOO Drifted: `1` | Hybrid Drifted: `18`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::allow_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 9 | `0.9101` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 3 | `0.2461` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 18 | `0.0786` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 28 | `0.5000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 11 | `0.1924` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 10 | `0.1587` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 11 | `0.3274` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 10 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 2 | `0.1301` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 9 | `0.0899` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `0.3422` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 21 | `0.1786` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 36 | `0.6629` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 5 | `0.8413` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 3 | `0.7544` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.9214` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 9 | `0.0544` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::execute_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::save_model` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |

---

## Commit Transition: `C3 (43e17da) -> C4 (3937bbf)`

**Summary**: Total AST Entities: `89` | Direct Edits: `18` | Pure LOO Drifted: `3` | Hybrid Drifted: `18`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 6 | `0.0899` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 7 | `0.1459` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 2 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 13 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `0.1587` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 7 | `0.5429` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 18 | `0.7866` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 11 | `0.0899` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 30 | `0.1700` |
| `src/api.py::allow_request` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.5730` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 18 | `0.8596` |
| `src/api.py::json_response` | `src/api.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 3 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 5 | `0.8413` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::record_hit` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::execute_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::save_model` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |

---

## Commit Transition: `C4 (3937bbf) -> C5 (1ee704e)`

**Summary**: Total AST Entities: `90` | Direct Edits: `18` | Pure LOO Drifted: `4` | Hybrid Drifted: `18`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::execute_all` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::allow_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::record_hit` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::execute_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::save_model` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.5546` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 18 | `0.0198` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 3 | `0.2819` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 4 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 13 | `0.1587` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 13 | `0.3363` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 14 | `0.0786` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `0.3401` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 2 | `0.5000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `0.6436` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.1284` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.2071` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 2 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 3 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 9 | `0.1587` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 4 | `0.7035` |

---

## Commit Transition: `C5 (1ee704e) -> C6 (b528f96)`

**Summary**: Total AST Entities: `90` | Direct Edits: `16` | Pure LOO Drifted: `2` | Hybrid Drifted: `16`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::execute_all` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::allow_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 7 | `0.3527` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 8 | `0.6571` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 6 | `0.1587` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 4 | `0.2893` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 3 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 3 | `0.0294` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 11 | `0.0899` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 4 | `0.3927` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::record_hit` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::execute_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::save_model` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |

---

## Commit Transition: `C6 (b528f96) -> C7 (ecdf44a)`

**Summary**: Total AST Entities: `90` | Direct Edits: `18` | Pure LOO Drifted: `2` | Hybrid Drifted: `18`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::execute_all` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::allow_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::record_hit` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 4 | `0.7181` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 5 | `0.0544` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 2 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 8 | `0.1924` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 11 | `0.8618` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 8 | `0.1303` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 1 | `0.1587` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `0.0899` |
| `src/database.py::execute_query` | `src/database.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 10 | `0.0544` |
| `src/database.py::save_model` | `src/database.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 4 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |

---

## Commit Transition: `C7 (ecdf44a) -> C8 (c4f2d56)`

**Summary**: Total AST Entities: `90` | Direct Edits: `19` | Pure LOO Drifted: `2` | Hybrid Drifted: `19`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 17 | `0.9214` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::execute_all` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 8 | `0.0899` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 20 | `0.8413` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 5 | `0.1587` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 2 | `0.7060` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 2 | `0.7674` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 2 | `0.3927` |
| `src/api.py::allow_request` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `0.3274` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 5 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 1 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::record_hit` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::execute_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::save_model` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |

---

## Commit Transition: `C8 (c4f2d56) -> C9 (9834080)`

**Summary**: Total AST Entities: `90` | Direct Edits: `18` | Pure LOO Drifted: `3` | Hybrid Drifted: `18`

| Entity AST Name | File Path | Entity Type | Direct Edit? | Pure LOO Drifted (Without Direct) | Hybrid Drifted (With Direct) | Displaced Queries | p-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `src/api.py::APIRouter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::APIRouter::match_route` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::execute_all` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::MiddlewarePipeline::register` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::RateLimiter::is_exceeded` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter` | `src/api.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::__init__` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::ResponseFormatter::build_envelope` | `src/api.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::allow_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::auth_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::error_handler` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::handle_request` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::json_response` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/api.py::logging_middleware` | `src/api.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::RBACController::is_authorized` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::SessionManager::get_session` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator` | `src/auth.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::__init__` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::TokenValidator::validate_structure` | `src/auth.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::check_permission` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::create_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::destroy_session` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::generate_token` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::hash_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::validate_jwt` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/auth.py::verify_password` | `src/auth.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::InvalidationManager::should_purge` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::KeySerializer::format_prefix` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::is_full` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::LRUCache::record_hit` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager` | `src/cache.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::__init__` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::RedisManager::ping` | `src/cache.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_get` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::cache_set` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::flush_all` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::purge_stale_keys` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::redis_connect` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/cache.py::serialize_key` | `src/cache.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::DatabaseClient::is_active` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::MigrationRunner::get_version` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::ORMModel::to_dict` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder` | `src/database.py` | `class` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::__init__` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::QueryBuilder::build_clause` | `src/database.py` | `method` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::apply_migrations` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_insert_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::build_select_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::connect_db` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::execute_query` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/database.py::save_model` | `src/database.py` | `function` | NO | 🟢 NOT DRIFTED | 🟢 NOT DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper` | `src/utils.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::__init__` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::CryptoHelper::get_key_length` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter` | `src/utils.py` | `class` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 8 | `1.0000` |
| `src/utils.py::DateFormatter::__init__` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::DateFormatter::get_tz` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::LoggerWrapper` | `src/utils.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 4 | `0.6726` |
| `src/utils.py::LoggerWrapper::__init__` | `src/utils.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 3 | `1.0000` |
| `src/utils.py::LoggerWrapper::format_msg` | `src/utils.py` | `method` | YES | 🔴 DRIFTED | 🔴 DRIFTED | 13 | `1.0000` |
| `src/utils.py::StringCleaner` | `src/utils.py` | `class` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::__init__` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::StringCleaner::clean` | `src/utils.py` | `method` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::decrypt_data` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::encrypt_data` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::format_iso_date` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |
| `src/utils.py::log_error` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 2 | `0.1587` |
| `src/utils.py::log_info` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 4 | `0.5000` |
| `src/utils.py::sanitize_input` | `src/utils.py` | `function` | YES | 🟢 NOT DRIFTED | 🔴 DRIFTED | 0 | `1.0000` |

---
