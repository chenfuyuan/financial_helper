## 1. Database Migration

- [ ] 1.1 Create Alembic migration for `stock_daily` and `stock_daily_sync_failure` tables

## 2. Domain Layer

- [ ] 2.1 Implement `StockDaily` and `StockDailySyncFailure` entities
- [ ] 2.2 Implement `StockDailyGateway`, `StockDailyRepository`, and `StockDailySyncFailureRepository` interfaces

## 3. Infrastructure Layer (Models & Mappers)

- [ ] 3.1 Implement SQLAlchemy models (`StockDailyModel` and `StockDailySyncFailureModel`)
- [ ] 3.2 Implement persistence mappers for entity-to-dict conversion

## 4. Infrastructure Layer (Gateway)

- [ ] 4.1 Implement `AsyncTokenBucket` rate limiter in `shared_kernel`
- [ ] 4.2 Implement `TuShareStockDailyMapper` for TuShare data parsing
- [ ] 4.3 Implement `TuShareStockDailyGateway` with rate limiting and API orchestration

## 5. Infrastructure Layer (Repositories)

- [ ] 5.1 Implement `SqlAlchemyStockDailyRepository` (with upsert and `get_latest_trade_date`)
- [ ] 5.2 Implement `SqlAlchemyStockDailySyncFailureRepository`

## 6. Application Layer

- [ ] 6.1 Implement `SyncStockDailyIncrement` Command & Handler
- [ ] 6.2 Implement `SyncStockDailyHistory` Command & Handler (with breakpoint resume)
- [ ] 6.3 Implement `RetryStockDailySyncFailures` Command & Handler

## 7. Interface Layer

- [ ] 7.1 Implement HTTP routes and dependency injection in `stock_daily_router.py`
