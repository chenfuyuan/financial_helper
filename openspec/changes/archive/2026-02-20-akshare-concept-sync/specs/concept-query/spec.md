
## ADDED Requirements

### Requirement: Query concept board list
The system SHALL provide an API endpoint to retrieve the list of concept boards, wrapped in `ApiResponse[list[ConceptResponse]]`.

#### Scenario: Get all concept boards
- **WHEN** a user requests `GET /api/v1/data-engineering/concepts`
- **THEN** the system returns all concept boards from the database
- **AND** the response is wrapped in `ApiResponse` with `code=200`
- **AND** each concept includes: id, source, third_code, name, last_synced_at

#### Scenario: Filter concepts by data source
- **WHEN** a user requests `GET /api/v1/data-engineering/concepts?source=AKSHARE`
- **THEN** the system returns only concepts from the specified data source
- **AND** concepts from other sources are excluded

#### Scenario: No concepts exist
- **WHEN** a user requests concept boards and no data has been synced yet
- **THEN** the system returns an empty list with `code=200`
- **AND** the response is `ApiResponse(code=200, data=[])`

#### Scenario: Invalid source parameter
- **WHEN** a user requests `GET /api/v1/data-engineering/concepts?source=INVALID`
- **THEN** the system returns a 422 Unprocessable Entity error (FastAPI validation)

### Requirement: Query constituent stocks of a concept
The system SHALL provide an API endpoint to retrieve the constituent stocks of a specific concept board, wrapped in `ApiResponse[list[ConceptStockResponse]]`.

#### Scenario: Get constituent stocks of a concept
- **WHEN** a user requests `GET /api/v1/data-engineering/concepts/{concept_id}/stocks`
- **THEN** the system returns all ConceptStock relationships for the specified concept
- **AND** each stock includes: id, concept_id, source, stock_third_code, stock_symbol, added_at

#### Scenario: Concept not found
- **WHEN** a user requests constituent stocks for a non-existent concept_id
- **THEN** the system raises `ConceptNotFoundError`
- **AND** the global exception handler returns a 404 Not Found with `ApiResponse(code=404, message=...)`

#### Scenario: Concept exists but has no constituent stocks
- **WHEN** a user requests stocks for a concept that exists but has no associated stocks
- **THEN** the system returns an empty list with `code=200`
- **AND** the response is `ApiResponse(code=200, data=[])`

