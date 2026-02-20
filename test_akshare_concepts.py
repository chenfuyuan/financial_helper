
#!/usr/bin/env python3
"""测试 AKShare 概念板块相关接口"""
import akshare as ak
import pandas as pd

print(f"AKShare 版本: {ak.__version__}")
print("=" * 80)

# 1. 查看所有以 concept 开头的函数
print("\n1. 查找 concept 相关接口:")
concept_functions = [func for func in dir(ak) if 'concept' in func.lower()]
for func in sorted(concept_functions):
    print(f"  - {func}")

print("=" * 80)

# 2. 查看 board 相关接口
print("\n2. 查找 board 相关接口:")
board_functions = [func for func in dir(ak) if 'board' in func.lower()]
for func in sorted(board_functions):
    print(f"  - {func}")

print("=" * 80)

# 3. 测试一些常用接口
print("\n3. 尝试获取概念板块列表:")

# 尝试 stock_board_concept_name_ths
try:
    print("\n  尝试接口: stock_board_concept_name_ths")
    df = ak.stock_board_concept_name_ths()
    print(f"  成功! 数据形状: {df.shape}")
    print(f"  列名: {df.columns.tolist()}")
    print(f"  前5行:\n{df.head()}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

# 尝试 stock_board_concept_index_ths
try:
    print("\n  尝试接口: stock_board_concept_index_ths")
    df = ak.stock_board_concept_index_ths(symbol="阿里巴巴概念")
    print(f"  成功! 数据形状: {df.shape}")
    print(f"  列名: {df.columns.tolist()}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

# 尝试 stock_board_concept_cons_ths
try:
    print("\n  尝试接口: stock_board_concept_cons_ths")
    df = ak.stock_board_concept_cons_ths(symbol="阿里巴巴概念")
    print(f"  成功! 数据形状: {df.shape}")
    print(f"  列名: {df.columns.tolist()}")
    print(f"  前5行:\n{df.head()}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

# 尝试其他可能的接口
try:
    print("\n  尝试接口: stock_concept_board_em (东方财富)")
    df = ak.stock_concept_board_em()
    print(f"  成功! 数据形状: {df.shape}")
    print(f"  列名: {df.columns.tolist()}")
    print(f"  前5行:\n{df.head()}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

try:
    print("\n  尝试接口: stock_board_industry_name_em (东方财富行业)")
    df = ak.stock_board_industry_name_em()
    print(f"  成功! 数据形状: {df.shape}")
    print(f"  列名: {df.columns.tolist()}")
except Exception as e:
    print(f"  失败: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("测试完成!")
