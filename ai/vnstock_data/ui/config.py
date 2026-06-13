'\nConfiguration module for UI Data Routing Overrides.\n\nProvides the ability to dynamically override the data routing logic. \nThis is useful when:\n1. A default API source breaks and needs to be patched quickly.\n2. A user wants to provide a custom "patchwork" data source (e.g., just one method from ACBS)\n   without building a full provider module.\n'
ROUTE_OVERRIDES={}
def set_route(domain_method,source,provider_type,class_name,method):"\n    Override the default data source routing for a specific UI method.\n    (Make sure to register your custom class via ProviderRegistry.register() first)\n    \n    Args:\n        domain_method: The UI method to override (e.g., 'company.profile')\n        source: The source name (e.g., 'acbs')\n        provider_type: The provider type category in registry (e.g., 'company', 'listing')\n        class_name: The name of the custom class (mostly for logging)\n        method: The method to call on the provider instance\n    ";ROUTE_OVERRIDES[domain_method]=source,provider_type,class_name,method
def get_route(domain,method,default_sources):
	'\n    Get the routing configuration for a specific domain and method, checking overrides first.\n    ';B=domain;A=method;C=f"{B}.{A}"
	if C in ROUTE_OVERRIDES:return ROUTE_OVERRIDES[C]
	D=default_sources.get(B,{})
	if A not in D:raise NotImplementedError(f"Method '{A}' not implemented for domain '{B}'")
	return D[A]
def clear_route_overrides():'Clear all custom route overrides.';ROUTE_OVERRIDES.clear()