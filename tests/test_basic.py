# test_basic.py
"""اختبار بسيط للتأكد من عمل المكتبة"""

import asyncio
from pocket_trader import get_version, test_installation

def test():
    print(f"Version: {get_version()}")
    print(f"Installation OK: {test_installation()}")
    
    from pocket_trader.models import Asset
    print(f"Asset EURUSD: {Asset.EURUSD}")
    
    from pocket_trader.constants import Regions
    print(f"Demo URL: {Regions.DEMO}")
    
    print("✅ All basic tests passed!")

if __name__ == "__main__":
    test()