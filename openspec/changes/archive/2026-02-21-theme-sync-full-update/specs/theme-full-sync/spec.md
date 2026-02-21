## ADDED Requirements

### Requirement: Full theme synchronization with batch operations
The system SHALL synchronize all theme concepts and their constituent stocks from AKShare using a full synchronization approach with batch upsert operations, avoiding individual delete-then-insert cycles.

#### Scenario: Prepare data for full sync
- **WHEN** the user triggers a concept sync via `POST /api/v1/data-engineering/concepts/sync`
- **THEN** the system fetches all concept boards from AKShare in a single call
- **AND** the system fetches all local concepts for source=AKSHARE
- **AND** the system builds in-memory maps for remote and local data using `third_code` as key
- **AND** the system fetches all listed stocks from StockBasic for symbol matching

#### Scenario: Batch upsert concepts
- **WHEN** the system has prepared remote and local concept maps
- **THEN** the system creates a list of concepts to upsert (all remote concepts)
- **AND** for each remote concept, the system calculates content hash and sets `last_synced_at`
- **AND** the system performs a batch upsert operation using `concept_repo.save_many()`
- **AND** the system logs the total number of concepts processed

#### Scenario: Batch sync concept stocks
- **WHEN** all concepts have been batch upserted
- **THEN** for each concept, the system fetches constituent stocks from AKShare
- **AND** the system matches stocks with StockBasic using symbol and third_code mapping
- **AND** the system builds a list of ConceptStock entities with proper concept_id references
- **AND** the system performs a batch upsert operation using `concept_stock_repo.save_many()`
- **AND** the system logs the total number of stock relationships processed

#### Scenario: Cleanup obsolete data
- **WHEN** all concepts have been processed individually
- **THEN** the system identifies local concepts that are not in the remote data
- **AND** for each obsolete concept, the system deletes its ConceptStock relationships in a separate transaction
- **AND** the system deletes the obsolete Concept entity in the same transaction
- **AND** each obsolete concept is processed in its own transaction

#### Scenario: Transaction management
- **WHEN** performing the full synchronization
- **THEN** the system uses a separate transaction for each concept's processing
- **AND** each transaction includes the concept upsert and its stock relationships
- **AND** each transaction commits after the concept and its stocks are processed
- **AND** if a concept's transaction fails, only that concept is rolled back
- **AND** the system continues processing other concepts independently
- **AND** the system returns detailed sync result counts including failures

#### Scenario: Performance optimization
- **WHEN** processing large amounts of concept data
- **THEN** the system uses batch operations to minimize database round trips
- **AND** the system processes concepts in configurable batch sizes
- **AND** the system logs progress at key milestones
- **AND** the system monitors memory usage during processing
