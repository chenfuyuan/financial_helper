## MODIFIED Requirements

### Requirement: Sync concept boards and constituent stocks from AKShare
The system SHALL synchronize concept board information and their constituent stock relationships from AKShare's East Money data source using a full synchronization approach with batch operations instead of incremental hash-based comparison.

#### Scenario: Full sync preparation
- **WHEN** the user triggers a concept sync via `POST /api/v1/data-engineering/concepts/sync`
- **THEN** the system fetches all concept boards from AKShare in a single operation
- **AND** the system fetches all local concepts for source=AKSHARE
- **AND** the system builds complete in-memory mappings for comparison
- **AND** the system fetches all listed stocks from StockBasic for matching

#### Scenario: Batch concept synchronization
- **WHEN** the system has prepared all concept data
- **THEN** for each remote concept, the system processes it in a separate transaction
- **AND** the system creates upsert operations for the concept
- **AND** the system calculates content hash and sets current timestamp for `last_synced_at`
- **AND** the system performs concept upsert using repository's save method
- **AND** the system commits the transaction after concept is saved
- **AND** the system logs the number of concepts processed

#### Scenario: Batch stock relationship synchronization
- **WHEN** a concept has been upserted successfully
- **THEN** in the same transaction, the system fetches constituent stocks from AKShare
- **AND** the system matches stocks with StockBasic entities using symbol and third_code
- **AND** the system builds ConceptStock entities with proper concept_id references
- **AND** the system performs batch upsert of the concept's stock relationships
- **AND** the system deletes obsolete stock relationships for this concept
- **AND** the system commits the transaction after all operations for this concept are complete
- **AND** the system logs the stock relationships processed for this concept

#### Scenario: Cleanup obsolete data
- **WHEN** all remote concepts have been processed
- **THEN** the system identifies local concepts not present in remote data
- **AND** for each obsolete concept, the system processes it in a separate transaction
- **AND** the system deletes all ConceptStock relationships for the obsolete concept
- **AND** the system deletes the obsolete Concept entity
- **AND** the system commits the transaction for each obsolete concept
- **AND** the system logs the cleanup operations

#### Scenario: Associate stocks with StockBasic entity
- **WHEN** a concept stock is being prepared for batch upsert
- **THEN** the system infers exchange suffix from stock code prefix (6→.SH, 0/3→.SZ, 4/8→.BJ) to construct a `candidate_symbol`
- **AND** the system first attempts to match `candidate_symbol` against pre-loaded `StockBasic.symbol` map
- **AND** if match fails, the system attempts to match against pre-loaded `StockBasic.third_code` map (source=TUSHARE)
- **AND** if both matches fail, the system excludes the stock from batch upsert and logs a warning

#### Scenario: Handle AKShare API failures gracefully
- **WHEN** the AKShare API call fails during sync (network error, parsing error, empty response)
- **THEN** the system throws an `ExternalConceptServiceError`
- **AND** only the current concept's transaction is rolled back
- **AND** the system continues processing other concepts
- **AND** the error is logged with appropriate context for troubleshooting

#### Scenario: Handle empty AKShare response
- **WHEN** AKShare returns an empty concept list
- **THEN** the system treats this as a valid response (not an error)
- **AND** all local concepts for source=AKSHARE are marked as deleted during cleanup phase
- **AND** the sync result reflects the deletion counts

### Requirement: Content hash calculation for batch operations
The system SHALL calculate content hashes using SHA-256 (truncated to first 16 hex characters) for both Concept and ConceptStock entities to support batch upsert operations.

#### Scenario: Calculate Concept content hash for batch
- **WHEN** preparing Concept entities for batch upsert
- **THEN** the system calculates `sha256(f"{source}|{third_code}|{name}")[:16]` for each concept
- **AND** the hash is stored in the `content_hash` field
- **AND** the hash calculation is performed before batch operations

#### Scenario: Calculate ConceptStock content hash for batch
- **WHEN** preparing ConceptStock entities for batch upsert
- **THEN** the system calculates `sha256(f"{source}|{stock_third_code}|{stock_symbol or ''}")[:16]` for each stock relationship
- **AND** the hash is stored in the `content_hash` field
- **AND** the hash does NOT include `concept_id` (handled separately during batch processing)

### Requirement: Batch delete obsolete concepts
The system SHALL remove concept boards and their relationships when they no longer appear in the AKShare data source using per-concept transaction delete operations.

#### Scenario: Detect and delete obsolete concepts
- **WHEN** a full sync is completed and some local concepts are not in the AKShare response
- **THEN** the system identifies these concepts as obsolete
- **AND** for each obsolete concept, the system processes deletion in a separate transaction
- **AND** the system deletes all associated ConceptStock relationships within the same transaction
- **AND** the system deletes the Concept entity within the same transaction
- **AND** the system commits the transaction for each obsolete concept
- **AND** the deletion count is included in the sync result
