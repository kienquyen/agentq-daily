'\nSchema mappings for UI module standardized output.\n'
from.import company,derivatives,equity,events,fund,fundamental,industry,insights,macro,market,search
from.core import register_schemas,standardize_columns
register_schemas(company.SCHEMA_MAP,company.STANDARD_COLUMNS,getattr(company,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(equity.SCHEMA_MAP,equity.STANDARD_COLUMNS,getattr(equity,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(industry.SCHEMA_MAP,industry.STANDARD_COLUMNS,getattr(industry,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(derivatives.SCHEMA_MAP,derivatives.STANDARD_COLUMNS,getattr(derivatives,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(market.SCHEMA_MAP,market.STANDARD_COLUMNS,getattr(market,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(insights.SCHEMA_MAP,insights.STANDARD_COLUMNS,getattr(insights,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(fundamental.SCHEMA_MAP,fundamental.STANDARD_COLUMNS,getattr(fundamental,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(macro.SCHEMA_MAP,macro.STANDARD_COLUMNS,getattr(macro,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(fund.SCHEMA_MAP,fund.STANDARD_COLUMNS,getattr(fund,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(events.SCHEMA_MAP,events.STANDARD_COLUMNS,getattr(events,bytes([69,78,85,77,95,77,65,80]).decode(),None))
register_schemas(search.SCHEMA_MAP,search.STANDARD_COLUMNS,getattr(search,bytes([69,78,85,77,95,77,65,80]).decode(),None))
__all__=[bytes([115,116,97,110,100,97,114,100,105,122,101,95,99,111,108,117,109,110,115]).decode()]