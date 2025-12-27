from typing import Dict, List, Optional, Tuple
from datetime import datetime

STATE = {
    # ===== Core trading flow =====
    "signals": [],         
    "trades": [],           
    "decisions": [],        

    # ===== Portfolio & history =====
    "portfolio": None,
    "trade_history": [],    

    # ===== Execution context =====
    "symbols": [],          
    "as_of": None,          
    "run_mode": None,       

    # ===== External data (cached & rate-limited) =====
    "external_data": {
        "news": {},         
        "trends": {},       
    },
}
