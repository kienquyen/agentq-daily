import logging
from datetime import datetime
try:from vnstock.core.utils.logger import get_logger
except ImportError:
	def get_logger(name):return logging.getLogger(name)
from vnstock_data.core.types import CacheStrategy,DataCategory,DataQuality,DataSource,ExchangeType,MarketType,ProviderType,SubscriptionTier,UpdateFrequency
logger=get_logger(__name__)
def validate_date(date_str):
	'\n    Validate date string format in the format YYYY-mm-dd.\n    \n    Args:\n        date_str: Date string to validate\n    \n    Returns:\n        bool: True if valid, False otherwise\n    ';A=date_str
	try:datetime.strptime(A,bytes([37,89,45,37,109,45,37,100]).decode());return True
	except ValueError:logger.error(f"Invalid date format: {A}. Please use the format YYYY-mm-dd.");return False
def validate_data_category(category):
	'\n    Validate and normalize data category.\n    \n    Args:\n        category: Category string to validate\n    \n    Returns:\n        Optional[DataCategory]: Validated category or None if invalid\n    ';A=category
	try:return DataCategory(A.lower())
	except ValueError:B=[A.value for A in DataCategory];logger.error(f"Invalid data category: {A}. Valid options: {B}");return
def validate_provider_type(provider_type):
	'\n    Validate and normalize provider type.\n    \n    Args:\n        provider_type: Provider type string to validate\n    \n    Returns:\n        Optional[ProviderType]: Validated type or None if invalid\n    ';A=provider_type
	try:return ProviderType(A.lower())
	except ValueError:B=[A.value for A in ProviderType];logger.error(f"Invalid provider type: {A}. Valid options: {B}");return
def validate_market_type(market_type):
	'\n    Validate and normalize market type.\n    \n    Args:\n        market_type: Market type string to validate\n    \n    Returns:\n        Optional[MarketType]: Validated type or None if invalid\n    ';A=market_type
	try:return MarketType(A.lower())
	except ValueError:B=[A.value for A in MarketType];logger.error(f"Invalid market type: {A}. Valid options: {B}");return
def validate_exchange_type(exchange_type):
	'\n    Validate and normalize exchange type.\n    \n    Args:\n        exchange_type: Exchange type string to validate\n    \n    Returns:\n        Optional[ExchangeType]: Validated type or None if invalid\n    ';A=exchange_type
	try:return ExchangeType(A.lower())
	except ValueError:B=[A.value for A in ExchangeType];logger.error(f"Invalid exchange type: {A}. Valid options: {B}");return
def validate_subscription_tier(tier):
	'\n    Validate and normalize subscription tier.\n    \n    Args:\n        tier: Tier string to validate\n    \n    Returns:\n        Optional[SubscriptionTier]: Validated tier or None if invalid\n    '
	try:return SubscriptionTier(tier.lower())
	except ValueError:A=[A.value for A in SubscriptionTier];logger.error(f"Invalid subscription tier: {tier}. Valid options: {A}");return
def validate_data_source(source):
	'\n    Validate and normalize data source.\n    \n    Args:\n        source: Source string to validate\n    \n    Returns:\n        Optional[DataSource]: Validated source or None if invalid\n    ';A=source
	try:return DataSource(A.lower())
	except ValueError:B=[A.value for A in DataSource];logger.error(f"Invalid data source: {A}. Valid options: {B}");return
def check_subscription_access(tier,source,category):
	"\n    Check if subscription tier can access a specific data source and category.\n    \n    Args:\n        tier: User's subscription tier\n        source: Data source to access\n        category: Data category to access\n    \n    Returns:\n        tuple[bool, str]: (can_access, error_message)\n    ";C=category;B=source;A=tier;from vnstock_data.core.types import SubscriptionConfig as D
	if not D.can_access_source(A,B):return False,f"Subscription tier {A.value} cannot access data source {B.value}. Required: Bronze or higher."
	if not D.can_access_category(A,C):return False,f"Subscription tier {A.value} cannot access data category {C.value}. Required: Bronze or higher."
	return True,bytes([65,99,99,101,115,115,32,103,114,97,110,116,101,100]).decode()
def validate_data_quality(quality):
	'\n    Validate and normalize data quality level.\n    \n    Args:\n        quality: Quality string to validate\n    \n    Returns:\n        Optional[DataQuality]: Validated quality or None if invalid\n    ';A=quality
	try:return DataQuality(A.lower())
	except ValueError:B=[A.value for A in DataQuality];logger.error(f"Invalid data quality: {A}. Valid options: {B}");return
def validate_update_frequency(frequency):
	'\n    Validate and normalize update frequency.\n    \n    Args:\n        frequency: Frequency string to validate\n    \n    Returns:\n        Optional[UpdateFrequency]: Validated frequency or None if invalid\n    ';A=frequency
	try:return UpdateFrequency(A.lower())
	except ValueError:B=[A.value for A in UpdateFrequency];logger.error(f"Invalid update frequency: {A}. Valid options: {B}");return
def validate_cache_strategy(strategy):
	'\n    Validate and normalize cache strategy.\n    \n    Args:\n        strategy: Strategy string to validate\n    \n    Returns:\n        Optional[CacheStrategy]: Validated strategy or None if invalid\n    ';A=strategy
	try:return CacheStrategy(A.lower())
	except ValueError:B=[A.value for A in CacheStrategy];logger.error(f"Invalid cache strategy: {A}. Valid options: {B}");return