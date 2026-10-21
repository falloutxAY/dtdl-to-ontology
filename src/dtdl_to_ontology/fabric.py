"""Opt-in Fabric REST deployment and definition retrieval."""

import base64
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .report import canonical_json

API_ROOT = "https://api.fabric.microsoft.com/v1"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_OPERATION_TIMEOUT_SECONDS = 900
DEFAULT_RETRY_SECONDS = 5


class FabricApiError(RuntimeError):
    """An explicit Fabric API or service-response failure."""


@dataclass(frozen=True)
class ApiResponse:
    status: int
    headers: object
    body: object


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def decode_definition(definition: object, label: str) -> tuple[dict, dict[str, str]]:
    if not isinstance(definition, dict) or not isinstance(definition.get("parts"), list):
        raise ValueError(f"{label} must contain a parts array.")
    decoded: dict[str, str] = {}
    for index, part in enumerate(definition["parts"]):
        if not isinstance(part, dict):
            raise ValueError(f"{label} part {index} must be an object.")
        path = part.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"{label} part {index} has no valid path.")
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in path or ":" in path:
            raise ValueError(f"{label} part has an unsafe path: {path!r}.")
        if path in decoded:
            raise ValueError(f"{label} contains duplicate part path: {path}.")
        if part.get("payloadType") != "InlineBase64":
            raise ValueError(f"{label} part {path!r} is not InlineBase64.")
        payload = part.get("payload")
        if not isinstance(payload, str):
            raise ValueError(f"{label} part {path!r} has no Base64 payload.")
        try:
            decoded[path] = base64.b64decode(payload, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError(f"{label} part {path!r} is not valid UTF-8 Base64.") from error
    return definition, decoded


def read_definition(path: Path, expected_name: str | None = None) -> tuple[dict, dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Definition file is not valid JSON: {path}.") from error
    definition, parts = decode_definition(payload, "Definition")
    platform = parts.get(".platform")
    if platform is None:
        raise ValueError("Definition is missing the required .platform part.")
    try:
        metadata = json.loads(platform)["metadata"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("Definition .platform metadata is invalid.") from error
    if not isinstance(metadata, dict):
        raise ValueError("Definition .platform metadata is invalid.")
    display_name = metadata.get("displayName")
    if metadata.get("type") != "Ontology" or not isinstance(display_name, str) or not display_name:
        raise ValueError("Definition .platform must identify a named Ontology.")
    if expected_name is not None and expected_name != display_name:
        raise ValueError(
            f"Deployment name {expected_name!r} does not match .platform displayName "
            f"{display_name!r}."
        )
    return definition, parts


class FabricClient:
    def __init__(
        self,
        access_token: str,
        *,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        operation_timeout: int = DEFAULT_OPERATION_TIMEOUT_SECONDS,
        sleep=time.sleep,
        monotonic=time.monotonic,
        opener=None,
    ):
        token = access_token.strip()
        if not token or any(ord(char) < 32 for char in token):
            raise ValueError("Fabric access token must be a non-empty, single-line value.")
        self._access_token = token
        self._timeout = timeout
        self._operation_timeout = operation_timeout
        self._sleep = sleep
        self._monotonic = monotonic
        self._opener = opener or build_opener(_RejectRedirects())

    def _request(
        self,
        method: str,
        url: str,
        body: dict | None = None,
        *,
        operation_url: bool = False,
    ) -> ApiResponse:
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or (
            parsed_url.netloc != "api.fabric.microsoft.com"
            and not (operation_url and self._is_trusted_operation_host(parsed_url.hostname))
        ):
            raise FabricApiError("Refusing to send Fabric authorization to an untrusted host.")
        headers = {"Accept": "application/json"}
        data = None
        headers["Authorization"] = "Bearer " + self._access_token
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = canonical_json(body).encode("utf-8")
        request = Request(url, data=data, headers=headers, method=method)
        for attempt in range(4):
            try:
                with self._opener.open(request, timeout=self._timeout) as response:
                    payload = response.read()
                    status = response.status
                    response_headers = response.headers
                break
            except HTTPError as error:
                if error.code == 429 and attempt < 3:
                    delay = self._retry_after(error.headers)
                    error.close()
                    self._sleep(delay)
                    continue
                error_body = error.read()
                detail = self._error_detail(error_body)
                suffix = f": {detail}" if detail else ""
                request_id = error.headers.get("RequestId") if error.headers else None
                request_suffix = f" (request ID {request_id})" if request_id else ""
                raise FabricApiError(
                    f"Fabric API returned HTTP {error.code}{request_suffix}{suffix}."
                ) from None
        if not payload:
            return ApiResponse(status, response_headers, {})
        if "json" not in response_headers.get("Content-Type", "").lower():
            return ApiResponse(status, response_headers, payload)
        try:
            decoded = payload.decode("utf-8")
            response_body = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FabricApiError(
                "Fabric API returned a non-JSON or invalid UTF-8 response."
            ) from error
        return ApiResponse(status, response_headers, response_body)

    def _error_detail(self, payload: bytes) -> str:
        try:
            body = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ""
        if not isinstance(body, dict):
            return ""
        error = body.get("error")
        if not isinstance(error, dict):
            error = body
        code = error.get("errorCode") or error.get("code")
        message = error.get("message")
        detail = " - ".join(
            value[:500] for value in (code, message) if isinstance(value, str) and value
        )
        return detail.replace(self._access_token, "[redacted]")

    def _complete_operation(self, response: ApiResponse) -> tuple[ApiResponse, str | None]:
        if response.status != 202:
            if not 200 <= response.status < 300:
                raise FabricApiError(f"Fabric API returned unexpected HTTP {response.status}.")
            return response, None
        location = response.headers.get("Location")
        if not isinstance(location, str) or not location:
            raise FabricApiError("Fabric accepted the request without an operation Location.")
        location = self._validate_operation_url(location)
        deadline = self._monotonic() + self._operation_timeout
        retry_after = self._retry_after(response.headers)
        while True:
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                raise FabricApiError("Fabric long-running operation timed out.")
            self._sleep(min(retry_after, remaining))
            operation = self._request("GET", location, operation_url=True)
            if operation.status != 200:
                raise FabricApiError(f"Fabric operation polling returned HTTP {operation.status}.")
            if not isinstance(operation.body, dict):
                raise FabricApiError("Fabric operation status was not a JSON object.")
            state = operation.body.get("status")
            if state == "Succeeded":
                result_location = operation.headers.get("Location") or location
                parsed_location = urlparse(urljoin(location, result_location))
                if not parsed_location.path.rstrip("/").endswith("/result"):
                    parsed_location = parsed_location._replace(
                        path=parsed_location.path.rstrip("/") + "/result"
                    )
                result_url = self._validate_operation_url(parsed_location.geturl(), result=True)
                result = self._request("GET", result_url, operation_url=True)
                if not 200 <= result.status < 300:
                    raise FabricApiError(f"Fabric operation result returned HTTP {result.status}.")
                return result, state
            if state in {"Failed", "Cancelled", "Canceled"}:
                detail = self._error_detail(canonical_json(operation.body).encode("utf-8"))
                suffix = f": {detail}" if detail else ""
                raise FabricApiError(f"Fabric long-running operation {state.lower()}{suffix}.")
            if state not in {"NotStarted", "Running"}:
                raise FabricApiError(f"Fabric returned an unknown operation state: {state!r}.")
            retry_after = self._retry_after(operation.headers)

    @staticmethod
    def _validate_operation_url(url: str, *, result: bool = False) -> str:
        parsed = urlparse(url)
        if not parsed.scheme and not parsed.netloc:
            parsed = urlparse(urljoin("https://api.fabric.microsoft.com/", url))
        segments = parsed.path.rstrip("/").split("/")
        expected_length = 5 if result else 4
        try:
            port = parsed.port
        except ValueError:
            port = -1
        if (
            parsed.scheme != "https"
            or not FabricClient._is_trusted_operation_host(parsed.hostname)
            or port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or len(segments) != expected_length
            or segments[:3] != ["", "v1", "operations"]
            or not segments[3]
            or (result and segments[4] != "result")
        ):
            raise FabricApiError(
                "Fabric returned an invalid operation URL "
                f"(scheme={parsed.scheme!r}, host={parsed.hostname!r}, "
                f"path={parsed.path!r})."
            )
        return parsed.geturl()

    @staticmethod
    def _is_trusted_operation_host(hostname: str | None) -> bool:
        if hostname is None:
            return False
        host = hostname.lower()
        return (
            host == "api.fabric.microsoft.com"
            or host == "redirect.analysis.windows.net"
            or host.endswith("-redirect.analysis.windows.net")
        )

    @staticmethod
    def _retry_after(headers: object) -> float:
        if headers is None:
            return DEFAULT_RETRY_SECONDS
        value = headers.get("Retry-After")
        if value is None:
            return DEFAULT_RETRY_SECONDS
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return DEFAULT_RETRY_SECONDS

    def create_ontology(
        self,
        workspace_id: str,
        display_name: str,
        definition: dict,
        folder_id: str | None = None,
    ) -> tuple[dict, int, str | None]:
        workspace = str(uuid.UUID(workspace_id))
        body = {"displayName": display_name, "type": "Ontology", "definition": definition}
        folder = str(uuid.UUID(folder_id)) if folder_id is not None else None
        if folder is not None:
            body["folderId"] = folder
        response = self._request("POST", f"{API_ROOT}/workspaces/{workspace}/items", body)
        initial_status = response.status
        completed, operation_status = self._complete_operation(response)
        item = completed.body if isinstance(completed.body, dict) else {}
        item_id = item.get("id")
        if not item_id:
            item = self._find_created_item(workspace, display_name, folder)
            item_id = item.get("id")
        try:
            item["id"] = str(uuid.UUID(item_id))
        except (ValueError, TypeError, AttributeError) as error:
            raise FabricApiError(
                "Fabric create response did not contain a valid item ID."
            ) from error
        if item.get("type") not in (None, "Ontology"):
            raise FabricApiError("Fabric create response was not an Ontology item.")
        if item.get("workspaceId") not in (None, workspace):
            raise FabricApiError("Fabric created the Ontology in an unexpected workspace.")
        if item.get("displayName") not in (None, display_name):
            raise FabricApiError("Fabric create response did not match the requested item name.")
        if item.get("folderId") not in (None, folder):
            raise FabricApiError("Fabric created the Ontology in an unexpected folder.")
        return item, initial_status, operation_status

    def _find_created_item(
        self, workspace_id: str, display_name: str, folder_id: str | None
    ) -> dict:
        query = {"type": "Ontology", "recursive": "false"}
        if folder_id is not None:
            query["rootFolderId"] = folder_id
        matches = []
        continuation_token = None
        while True:
            page_query = dict(query)
            if continuation_token:
                page_query["continuationToken"] = continuation_token
            url = f"{API_ROOT}/workspaces/{workspace_id}/items?{urlencode(page_query)}"
            response = self._request("GET", url)
            if response.status != 200 or not isinstance(response.body, dict):
                raise FabricApiError("Fabric completed item creation but exact item lookup failed.")
            items = response.body.get("value")
            if not isinstance(items, list):
                raise FabricApiError(
                    "Fabric completed item creation but returned an invalid item list."
                )
            matches.extend(
                item
                for item in items
                if isinstance(item, dict)
                and item.get("displayName") == display_name
                and item.get("type") == "Ontology"
                and item.get("workspaceId") in (None, workspace_id)
                and item.get("folderId") == folder_id
            )
            continuation_token = response.body.get("continuationToken")
            if not continuation_token:
                break
        if len(matches) != 1:
            raise FabricApiError(
                "Fabric completed item creation but exact item lookup found "
                f"{len(matches)} matching Ontology items."
            )
        return matches[0]

    def get_definition(self, workspace_id: str, item_id: str) -> tuple[object, int, str | None]:
        workspace = str(uuid.UUID(workspace_id))
        item = str(uuid.UUID(item_id))
        response = self._request(
            "POST", f"{API_ROOT}/workspaces/{workspace}/items/{item}/getDefinition"
        )
        initial_status = response.status
        completed, operation_status = self._complete_operation(response)
        return completed.body, initial_status, operation_status


def deploy_definition(
    path: Path,
    workspace_id: str,
    access_token: str,
    *,
    expected_name: str | None = None,
    folder_id: str | None = None,
    client: FabricClient | None = None,
) -> dict:
    workspace = str(uuid.UUID(workspace_id))
    definition, local_parts = read_definition(path, expected_name)
    platform = json.loads(local_parts[".platform"])
    display_name = platform["metadata"]["displayName"]
    fabric = client or FabricClient(access_token)
    item, create_status, create_operation = fabric.create_ontology(
        workspace, display_name, definition, folder_id
    )
    item_id = item["id"]
    try:
        response, get_status, get_operation = fabric.get_definition(workspace, item_id)
        if not isinstance(response, dict):
            raise FabricApiError("Fabric getDefinition response was not a JSON object.")
        service_definition = response.get("definition")
        _, service_parts = decode_definition(service_definition, "Fabric getDefinition")
    except (FabricApiError, ValueError) as error:
        raise FabricApiError(
            f"Ontology was created as item {item_id}, but getDefinition verification failed: "
            f"{error}"
        ) from error
    expected_paths = sorted(local_parts)
    returned_paths = sorted(service_parts)
    return {
        "service_acceptance": "create_and_get_definition_succeeded",
        "semantic_equivalence": "not_asserted",
        "workspace_id": workspace,
        "item_id": item_id,
        "display_name": display_name,
        "create_http_status": create_status,
        "create_operation_status": create_operation,
        "get_definition_http_status": get_status,
        "get_definition_operation_status": get_operation,
        "expected_part_count": len(expected_paths),
        "returned_part_count": len(returned_paths),
        "missing_part_paths": sorted(set(expected_paths) - set(returned_paths)),
        "additional_part_paths": sorted(set(returned_paths) - set(expected_paths)),
    }
