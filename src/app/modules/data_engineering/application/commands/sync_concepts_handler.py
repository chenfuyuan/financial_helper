"""SyncConcepts 命令处理器。"""

from dataclasses import replace
from datetime import UTC, datetime
from time import perf_counter

from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.gateways.concept_gateway import ConceptGateway
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.repositories.concept_stock_repository import (
    ConceptStockRepository,
)
from app.modules.data_engineering.domain.repositories.stock_basic_repository import (
    StockBasicRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork

from .sync_concepts import SyncConcepts, SyncConceptsResult


def _build_candidate_symbol(raw_code: str) -> str | None:
    if not raw_code:
        return None
    if raw_code.startswith("6"):
        return f"{raw_code}.SH"
    if raw_code.startswith("0") or raw_code.startswith("3"):
        return f"{raw_code}.SZ"
    if raw_code.startswith("4") or raw_code.startswith("8"):
        return f"{raw_code}.BJ"
    return None


class SyncConceptsHandler(CommandHandler[SyncConcepts, SyncConceptsResult]):
    def __init__(
        self,
        gateway: ConceptGateway,
        concept_repo: ConceptRepository,
        concept_stock_repo: ConceptStockRepository,
        stock_basic_repo: StockBasicRepository,
        uow: UnitOfWork,
    ) -> None:
        self._gateway = gateway
        self._concept_repo = concept_repo
        self._concept_stock_repo = concept_stock_repo
        self._stock_basic_repo = stock_basic_repo
        self._uow = uow

    async def handle(self, command: SyncConcepts) -> SyncConceptsResult:
        start = perf_counter()
        now = datetime.now(UTC)

        remote_concepts = await self._gateway.fetch_concepts()
        local_concepts = await self._concept_repo.find_all(DataSource.AKSHARE)
        stock_basics = await self._stock_basic_repo.find_all_listed(DataSource.TUSHARE)

        symbol_map = {s.symbol: s for s in stock_basics}
        third_code_map = {s.third_code: s for s in stock_basics}

        remote_map = {c.third_code: c for c in remote_concepts}
        local_map = {c.third_code: c for c in local_concepts}

        new_concepts = 0
        modified_concepts = 0
        deleted_concepts = 0
        new_stocks = 0
        modified_stocks = 0
        deleted_stocks = 0

        for third_code, remote in remote_map.items():
            local = local_map.get(third_code)
            if local is None:
                saved = await self._concept_repo.save(replace(remote, last_synced_at=now))
                n, m, d = await self._sync_concept_stocks(saved.id or 0, remote.name, remote.third_code, {}, symbol_map, third_code_map)
                # 每个新题材同步完立即提交
                await self._uow.commit()
                new_concepts += 1
                new_stocks += n
                modified_stocks += m
                deleted_stocks += d
                continue

            if local.content_hash != remote.content_hash:
                to_save = replace(remote, id=local.id, last_synced_at=now)
                saved = await self._concept_repo.save(to_save)
                local_stocks = await self._concept_stock_repo.find_by_concept_id(saved.id or 0)
                local_stock_map = {s.stock_third_code: s for s in local_stocks}
                n, m, d = await self._sync_concept_stocks(
                    saved.id or 0,
                    remote.name,
                    remote.third_code,
                    local_stock_map,
                    symbol_map,
                    third_code_map,
                )
                # 每个修改题材同步完立即提交
                await self._uow.commit()
                modified_concepts += 1
                new_stocks += n
                modified_stocks += m
                deleted_stocks += d
                continue

            await self._concept_repo.save(replace(local, last_synced_at=now))
            # 未变更题材也立即提交更新时间
            await self._uow.commit()

        for third_code, local in local_map.items():
            if third_code in remote_map or local.id is None:
                continue
            old_stocks = await self._concept_stock_repo.find_by_concept_id(local.id)
            deleted_stocks += len(old_stocks)
            await self._concept_stock_repo.delete_by_concept_id(local.id)
            await self._concept_repo.delete(local.id)
            # 每个删除题材立即提交
            await self._uow.commit()
            deleted_concepts += 1
        total_stocks = new_stocks + modified_stocks + deleted_stocks
        return SyncConceptsResult(
            total_concepts=len(remote_concepts),
            new_concepts=new_concepts,
            modified_concepts=modified_concepts,
            deleted_concepts=deleted_concepts,
            total_stocks=total_stocks,
            new_stocks=new_stocks,
            modified_stocks=modified_stocks,
            deleted_stocks=deleted_stocks,
            duration_ms=int((perf_counter() - start) * 1000),
        )

    async def _sync_concept_stocks(
        self,
        concept_id: int,
        concept_name: str,
        concept_third_code: str,
        local_map: dict[str, ConceptStock],
        symbol_map: dict[str, object],
        third_code_map: dict[str, object],
    ) -> tuple[int, int, int]:
        remote_tuples = await self._gateway.fetch_concept_stocks(concept_third_code, concept_name)
        remote_codes = {code for code, _ in remote_tuples}

        to_upsert: list[ConceptStock] = []
        to_delete_ids: list[int] = []
        now = datetime.now(UTC)
        new_count = 0
        modified_count = 0
        deleted_count = 0

        for stock_third_code, _stock_name in remote_tuples:
            candidate = _build_candidate_symbol(stock_third_code)
            stock_symbol = None
            # 优先按symbol匹配
            if candidate and candidate in symbol_map:
                stock_symbol = candidate
            # 回退按third_code匹配
            elif stock_third_code in third_code_map:
                stock_symbol = candidate
            content_hash = ConceptStock.compute_hash(
                DataSource.AKSHARE,
                stock_third_code,
                stock_symbol,
            )
            local = local_map.get(stock_third_code)
            if local is None:
                to_upsert.append(
                    ConceptStock(
                        id=None,
                        concept_id=concept_id,
                        source=DataSource.AKSHARE,
                        stock_third_code=stock_third_code,
                        stock_symbol=stock_symbol,
                        content_hash=content_hash,
                        added_at=now,
                    )
                )
                new_count += 1
                continue
            if local.content_hash != content_hash:
                to_upsert.append(
                    ConceptStock(
                        id=local.id,
                        concept_id=concept_id,
                        source=DataSource.AKSHARE,
                        stock_third_code=stock_third_code,
                        stock_symbol=stock_symbol,
                        content_hash=content_hash,
                        added_at=local.added_at,
                    )
                )
                modified_count += 1

        for code, local in local_map.items():
            if code in remote_codes:
                continue
            if local.id is not None:
                to_delete_ids.append(local.id)
            deleted_count += 1

        await self._concept_stock_repo.save_many(to_upsert)
        await self._concept_stock_repo.delete_many(to_delete_ids)
        return new_count, modified_count, deleted_count
