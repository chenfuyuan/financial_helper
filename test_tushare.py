import os
import tushare as ts
token = os.environ.get("TUSHARE_TOKEN", "") # Need to get token or check docs
print("Token:", token)
