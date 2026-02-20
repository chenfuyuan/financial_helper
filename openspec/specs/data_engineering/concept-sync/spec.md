# concept-sync Specification

## Purpose
TBD - created by archiving change akshare-concept-sync. Update Purpose after archive.
## Requirements
### Requirement: Sync concept boards and constituent stocks from AKShare
The system SHALL synchronize concept board information and their constituent stock relationships from AKShare's East Money data source using a two-level hash-based fine-grained incremental synchronization strategy (concept-level → stock-level).

#### Scenario: Full sync when no local data exists
- **WHEN** the user triggers a concept sync via `POST /api/v1/data-engineering/concepts/sync` and no local concept data exists for source=AKSHARE
- **THEN** the system fetches all concept boards from AKShare
- **AND** for each concept, the system fetches constituent stocks
- **AND** for each constituent stock, the system attempts to match with `StockBasic` (see association scenarios)
- **AND** the system saves all concepts and stock relationships to the database in a single transaction
- **AND** the system returns a `SyncConceptsResponse` with counts of new concepts and stocks

#### Scenario: Incremental sync — concept-level comparison
- **WHEN** the user triggers a concept sync and local data exists for source=AKSHARE
- **THEN** the system compares remote vs local concepts by `third_code` key and `content_hash`
- **AND** new concepts (remote only) are saved, then their stocks are fetched and saved in full
- **AND** modified concepts (hash differs) are updated, then their stocks undergo stock-level comparison (see next scenario)
- **AND** unchanged concepts (hash matches) are skipped, only `last_synced_at` is updated
- **AND** deleted concepts (local only) and all their associated stocks are removed

#### Scenario: Incremental sync — stock-level comparison for modified concepts
- **WHEN** a concept is identified as modified during sync
- **THEN** the system fetches remote constituent stocks for that concept
- **AND** the system compares remote vs local stocks by `stock_third_code` key and `content_hash`
- **AND** new stocks are saved, modified stocks are updated, deleted stocks are removed
- **AND** the stock-level changes are included in the sync result counts

#### Scenario: Associate stocks with StockBasic entity
- **WHEN** a concept stock is being saved
- **THEN** the system infers exchange suffix from stock code prefix (6→.SH, 0/3→.SZ, 4/8→.BJ) to construct a `candidate_symbol`
- **AND** the system first attempts to match `candidate_symbol` against pre-loaded `StockBasic.symbol` map
- **AND** if match fails, the system attempts to match against pre-loaded `StockBasic.third_code` map (source=TUSHARE)
- **AND** if both matches fail, the system saves the relationship with `stock_symbol` as NULL and logs a warning

#### Scenario: Handle AKShare API failures gracefully
- **WHEN** the AKShare API call fails during sync (network error, parsing error, empty response)
- **THEN** the system throws an `ExternalConceptServiceError`
- **AND** the entire sync transaction is rolled back (no partial data persisted)
- **AND** the error is propagated to the caller with appropriate context

#### Scenario: Handle empty AKShare response
- **WHEN** AKShare returns an empty concept list
- **THEN** the system treats this as a valid response (not an error)
- **AND** all local concepts for source=AKSHARE are marked as deleted
- **AND** the sync result reflects the deletion counts

### Requirement: Content hash calculation for change detection
The system SHALL calculate content hashes using SHA-256 (truncated to first 16 hex characters) for both Concept and ConceptStock entities to enable efficient change detection during incremental sync.

#### Scenario: Calculate Concept content hash
- **WHEN** a Concept entity is being prepared for sync
- **THEN** the system calculates `sha256(f"{source}|{third_code}|{name}")[:16]`
- **AND** the hash is stored in the `content_hash` field

#### Scenario: Calculate ConceptStock content hash
- **WHEN** a ConceptStock entity is being prepared for sync
- **THEN** the system calculates `sha256(f"{source}|{stock_third_code}|{stock_symbol or ''}")[:16]`
- **AND** the hash is stored in the `content_hash` field
- **AND** the hash does NOT include `concept_id` (since new entities have no persisted id yet)

### Requirement: Delete concepts that no longer exist
The system SHALL remove concept boards and their relationships when they no longer appear in the AKShare data source.

#### Scenario: Detect and remove deleted concepts
- **WHEN** a sync is performed and some local concepts are not in the AKShare response
- **THEN** the system identifies these concepts as deleted
- **AND** the system deletes all associated ConceptStock relationships (via cascade or explicit delete)
- **AND** the system deletes the Concept entities
- **AND** the deletion count is included in the sync result

