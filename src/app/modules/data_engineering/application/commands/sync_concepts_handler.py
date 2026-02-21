import os
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from time import perf_counter

import psutil  # type: ignore

from app.config import settings
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.entities.stock_basic import StockBasic
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
from app.shared_kernel.infrastructure.logging import get_logger

from .sync_concepts import SyncConcepts, SyncConceptsResult

logger = get_logger(__name__)


class SyncConceptsHandler(CommandHandler[SyncConcepts, SyncConceptsResult]):
    """概念板块全量同步处理器。

    采用全量同步策略，一次性获取所有远程概念数据并与本地数据进行比较。
    每个概念使用独立事务处理，保证数据一致性的同时避免长时间锁定数据库资源。

    主要特性：
    - 全量同步：每次同步都处理所有概念，确保数据最终一致性
    - 独立事务：每个概念使用独立事务，错误隔离，避免影响其他概念
    - 批量处理：支持分批处理大量概念，避免内存溢出
    - 性能监控：记录处理时间、内存使用等性能指标
    - 错误处理：单个概念失败不影响其他概念的处理

    Attributes:
        _gateway: 概念数据网关，用于获取远程数据
        _concept_repo: 概念仓储，用于持久化概念数据
        _concept_stock_repo: 概念-股票关联仓储，用于持久化股票关系
        _stock_basic_repo: 股票基础信息仓储，用于股票匹配
        _uow: 工作单元，管理事务
        _batch_size: 批次大小，用于分批处理大量概念
    """

    def __init__(
        self,
        gateway: ConceptGateway,
        concept_repo: ConceptRepository,
        concept_stock_repo: ConceptStockRepository,
        stock_basic_repo: StockBasicRepository,
        uow: UnitOfWork,
        batch_size: int | None = None,  # 可选，默认使用配置
    ) -> None:
        """初始化同步处理器。

        Args:
            gateway: 概念数据网关
            concept_repo: 概念仓储
            concept_stock_repo: 概念-股票关联仓储
            stock_basic_repo: 股票基础信息仓储
            uow: 工作单元
            batch_size: 批次大小，默认使用配置文件中的值
        """
        self._gateway = gateway
        self._concept_repo = concept_repo
        self._concept_stock_repo = concept_stock_repo
        self._stock_basic_repo = stock_basic_repo
        self._uow = uow
        self._batch_size = batch_size or settings.CONCEPT_SYNC_BATCH_SIZE

    def _get_memory_usage(self) -> dict[str, int]:
        """获取当前进程的内存使用情况。

        Returns:
            包含物理内存和虚拟内存使用量的字典（单位：MB）
        """
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            "rss_mb": memory_info.rss // 1024 // 1024,  # 物理内存
            "vms_mb": memory_info.vms // 1024 // 1024,  # 虚拟内存
        }

    async def handle(self, command: SyncConcepts) -> SyncConceptsResult:
        """执行全量同步概念和股票关系。

        同步流程：
        1. 准备阶段：获取所有远程概念、本地概念和股票基础数据
        2. 分批处理：按批次处理所有远程概念，每个概念使用独立事务
        3. 清理阶段：删除本地存在但远程不存在的过时概念

        Args:
            command: 同步命令（当前无参数）

        Returns:
            包含同步结果统计的 SyncConceptsResult 对象

        Raises:
            ExternalConceptServiceError: 当外部数据源服务出现错误时
        """
        start = perf_counter()
        now = datetime.now(UTC)
        initial_memory = self._get_memory_usage()

        logger.info("开始全量同步概念数据", source=DataSource.AKSHARE.value, **initial_memory)

        # 准备阶段：获取所有必要数据
        remote_concepts = await self._gateway.fetch_concepts()
        local_concepts = await self._concept_repo.find_all(DataSource.AKSHARE)
        stock_basics = await self._stock_basic_repo.find_all_listed(DataSource.TUSHARE)

        logger.info(
            "数据准备完成",
            remote_concepts_count=len(remote_concepts),
            local_concepts_count=len(local_concepts),
            stock_basics_count=len(stock_basics),
            **self._get_memory_usage(),
        )

        # 构建映射表用于快速查找
        symbol_map = {s.symbol: s for s in stock_basics}
        third_code_map = {s.third_code: s for s in stock_basics}
        remote_map = {c.third_code: c for c in remote_concepts}
        local_map = {c.third_code: c for c in local_concepts}

        # 统计计数器
        new_concepts = 0
        modified_concepts = 0
        deleted_concepts = 0
        new_stocks = 0
        modified_stocks = 0
        deleted_stocks = 0
        failed_concepts = 0

        # 第一阶段：分批处理所有远程概念（每个概念独立事务）
        remote_items = list(remote_map.items())
        total_batches = (len(remote_items) + self._batch_size - 1) // self._batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * self._batch_size
            end_idx = start_idx + self._batch_size
            batch_items = remote_items[start_idx:end_idx]

            logger.info(
                "开始处理批次",
                batch_number=batch_idx + 1,
                total_batches=total_batches,
                batch_size=len(batch_items),
                **self._get_memory_usage(),
            )

            for i, (third_code, remote) in enumerate(batch_items, 1):
                try:
                    global_progress = f"{batch_idx * self._batch_size + i}/{len(remote_items)}"
                    logger.info(
                        "开始处理概念", third_code=third_code, concept_name=remote.name, progress=global_progress
                    )

                    # 在独立事务中处理单个概念
                    n, m, d = await self._process_single_concept(
                        remote, local_map.get(third_code), now, symbol_map, third_code_map
                    )

                    if local_map.get(third_code) is None:
                        new_concepts += 1
                    else:
                        modified_concepts += 1

                    new_stocks += n
                    modified_stocks += m
                    deleted_stocks += d

                    logger.info(
                        "概念处理完成", third_code=third_code, new_stocks=n, modified_stocks=m, deleted_stocks=d
                    )

                except Exception as e:
                    failed_concepts += 1
                    logger.error("概念处理失败", third_code=third_code, error=str(e), exc_info=True)
                    # 继续处理下一个概念
                    continue

            # 批次完成后记录内存使用情况
            logger.info("批次处理完成", batch_number=batch_idx + 1, **self._get_memory_usage())

        # 第二阶段：清理过时概念（每个概念独立事务）
        obsolete_third_codes = set(local_map.keys()) - set(remote_map.keys())
        logger.info("开始清理过时概念", obsolete_count=len(obsolete_third_codes))

        for third_code in obsolete_third_codes:
            try:
                local = local_map[third_code]
                if local.id is None:
                    continue

                await self._delete_obsolete_concept(local.id)
                deleted_concepts += 1

                # 获取该概念的股票数量用于统计
                old_stocks = await self._concept_stock_repo.find_by_concept_id(local.id)
                deleted_stocks += len(old_stocks)

                logger.info("过时概念清理完成", third_code=third_code)

            except Exception as e:
                logger.error("过时概念清理失败", third_code=third_code, error=str(e), exc_info=True)
                continue

        total_stocks = new_stocks + modified_stocks + deleted_stocks
        duration_ms = int((perf_counter() - start) * 1000)
        final_memory = self._get_memory_usage()

        logger.info(
            "全量同步完成",
            total_concepts=len(remote_concepts),
            new_concepts=new_concepts,
            modified_concepts=modified_concepts,
            deleted_concepts=deleted_concepts,
            total_stocks=total_stocks,
            new_stocks=new_stocks,
            modified_stocks=modified_stocks,
            deleted_stocks=deleted_stocks,
            failed_concepts=failed_concepts,
            duration_ms=duration_ms,
            **final_memory,
        )

        return SyncConceptsResult(
            total_concepts=len(remote_concepts),
            new_concepts=new_concepts,
            modified_concepts=modified_concepts,
            deleted_concepts=deleted_concepts,
            total_stocks=total_stocks,
            new_stocks=new_stocks,
            modified_stocks=modified_stocks,
            deleted_stocks=deleted_stocks,
            duration_ms=duration_ms,
        )

    async def _process_single_concept(
        self,
        remote_concept: Concept,
        local_concept: Concept | None,
        now: datetime,
        symbol_map: dict[str, StockBasic],
        third_code_map: dict[str, StockBasic],
    ) -> tuple[int, int, int]:
        """在独立事务中处理单个概念及其股票关系。

        Returns:
            (new_stocks, modified_stocks, deleted_stocks)
        """
        try:
            # 保存或更新概念
            if local_concept is None:
                # 新概念
                saved_concept = await self._concept_repo.save(replace(remote_concept, last_synced_at=now))
                concept_id = saved_concept.id or 0
                local_stock_map = {}
            else:
                # 更新现有概念
                saved_concept = await self._concept_repo.save(
                    replace(remote_concept, id=local_concept.id, last_synced_at=now)
                )
                concept_id = saved_concept.id or 0
                local_stocks = await self._concept_stock_repo.find_by_concept_id(concept_id)
                local_stock_map = {s.stock_third_code: s for s in local_stocks}

            # 同步股票关系
            new_stocks, modified_stocks, deleted_stocks = await self._sync_concept_stocks(
                concept_id,
                remote_concept.name,
                remote_concept.third_code,
                local_stock_map,
                symbol_map,
                third_code_map,
            )

            # 提交事务
            await self._uow.commit()

            return new_stocks, modified_stocks, deleted_stocks

        except Exception as e:
            # 回滚事务
            await self._uow.rollback()
            raise e

    async def _delete_obsolete_concept(self, concept_id: int) -> None:
        """在独立事务中删除过时概念及其股票关系。"""
        try:
            # 删除所有股票关系
            await self._concept_stock_repo.delete_by_concept_id(concept_id)
            # 删除概念
            await self._concept_repo.delete(concept_id)
            # 提交事务
            await self._uow.commit()

        except Exception as e:
            # 回滚事务
            await self._uow.rollback()
            raise e

    async def _sync_concept_stocks(
        self,
        concept_id: int,
        concept_name: str,
        concept_third_code: str,
        local_map: dict[str, ConceptStock],
        symbol_map: Mapping[str, StockBasic],
        third_code_map: Mapping[str, StockBasic],
    ) -> tuple[int, int, int]:
        remote_tuples = await self._gateway.fetch_concept_stocks(concept_third_code, concept_name)
        # 构建实际使用的third_code集合，用于删除逻辑
        remote_actual_third_codes = set()
        for stock_third_code, _stock_name in remote_tuples:
            stock_symbol = stock_third_code
            if stock_symbol in symbol_map:
                stock = symbol_map[stock_symbol]
                if stock is not None:
                    remote_actual_third_codes.add(stock.third_code)

        to_upsert: list[ConceptStock] = []
        to_delete_ids: list[int] = []
        now = datetime.now(UTC)
        new_count = 0
        modified_count = 0
        deleted_count = 0

        for stock_third_code, _stock_name in remote_tuples:
            # AKShare返回的代码可能需要格式转换才能匹配symbol
            stock_symbol = stock_third_code
            matched_stock: StockBasic | None = None

            # 首先尝试直接匹配symbol
            if stock_symbol in symbol_map:
                matched_stock = symbol_map[stock_symbol]
            else:
                # 尝试添加市场后缀匹配（如000001 -> 000001.SZ）
                for suffix in [".SZ", ".SH", ".BJ"]:
                    candidate = stock_symbol + suffix
                    if candidate in symbol_map:
                        matched_stock = symbol_map[candidate]
                        break

            # 如果仍然匹配不上，跳过这个股票
            if not matched_stock:
                continue

            actual_third_code = matched_stock.third_code

            content_hash = ConceptStock.compute_hash(
                DataSource.AKSHARE,
                actual_third_code,
                stock_symbol,
            )
            local = local_map.get(actual_third_code)
            if local is None:
                to_upsert.append(
                    ConceptStock(
                        id=None,
                        concept_id=concept_id,
                        source=DataSource.AKSHARE,
                        stock_third_code=actual_third_code,
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
                        stock_third_code=actual_third_code,
                        stock_symbol=stock_symbol,
                        content_hash=content_hash,
                        added_at=local.added_at,
                    )
                )
                modified_count += 1

        for code, local in local_map.items():
            if code in remote_actual_third_codes:
                continue
            if local.id is not None:
                to_delete_ids.append(local.id)
            deleted_count += 1

        await self._concept_stock_repo.save_many(to_upsert)
        await self._concept_stock_repo.delete_many(to_delete_ids)
        return new_count, modified_count, deleted_count
