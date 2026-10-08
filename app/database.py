import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TABLE_URL = "/rest/v1/found_items"


class StorageNotConfigured(RuntimeError):
	pass


def is_configured() -> bool:
	return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))


def _request(method: str, query: str = "", payload: dict | None = None) -> object:
	base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
	service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
	if not base_url or not service_key:
		raise StorageNotConfigured("Supabase storage is not configured.")

	body = json.dumps(payload).encode("utf-8") if payload is not None else None
	request = Request(
		f"{base_url}{TABLE_URL}{query}",
		data=body,
		method=method,
		headers={
			"apikey": service_key,
			"Authorization": f"Bearer {service_key}",
			"Content-Type": "application/json",
			"Prefer": "resolution=merge-duplicates,return=minimal",
		},
	)

	try:
		with urlopen(request, timeout=10) as response:
			result = response.read()
			return json.loads(result) if result else None
	except (HTTPError, URLError, TimeoutError) as error:
		raise RuntimeError("Could not access shared item storage.") from error


def load_items() -> dict[str, dict[str, str]]:
	rows = _request("GET", "?select=item_name,location,ciphertext,iv,timestamp&order=timestamp.desc")
	return {
		row["item_name"]: {
			"location": row["location"],
			"ciphertext": row["ciphertext"],
			"iv": row["iv"],
			"timestamp": row["timestamp"],
		}
		for row in rows
	}


def save_item(item_name: str, record: dict[str, str]) -> None:
	_request(
		"POST",
		"?on_conflict=item_name",
		{"item_name": item_name, **record},
	)