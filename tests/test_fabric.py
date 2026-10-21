import io
import json
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest

from dtdl_to_ontology.definition import envelope, platform_details
from dtdl_to_ontology.fabric import (
    FabricApiError,
    FabricClient,
    decode_definition,
    deploy_definition,
)
from dtdl_to_ontology.report import canonical_json

WORKSPACE_ID = "ec53121a-7764-4e63-aebb-7af2c46f9a66"
ITEM_ID = "ab3037c5-1011-4326-bf75-743f7d6a7e9b"
TOKEN = "test-access-token"


def definition(name="Example"):
    return envelope(
        {
            ".platform": canonical_json(platform_details(name)),
            "database.tmdl": "database\n\tcompatibilityLevel: 1000000\n",
            "entities/default.Example.tmdl": (
                'entity "default.Example"\n\tlineageTag: example\n'
                '\n\tproperty "name"\n\t\tlineageTag: property\n\t\tdataType: string\n'
            ),
        }
    )


def write_definition(tmp_path: Path, name="Example"):
    path = tmp_path / "definition.json"
    path.write_text(canonical_json(definition(name)), encoding="utf-8")
    return path


class FakeResponse:
    def __init__(self, status, body=None, headers=None):
        self.status = status
        self.headers = headers if headers is not None else Message()
        if self.headers.get("Content-Type") is None:
            self.headers["Content-Type"] = "application/json"
        self._body = b"" if body is None else canonical_json(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def test_deploy_creates_and_retrieves_definition_without_exposing_token(
    tmp_path,
):
    local_definition = definition()
    opener = FakeOpener(
        [
            FakeResponse(
                201,
                {"id": ITEM_ID, "type": "Ontology", "workspaceId": WORKSPACE_ID},
            ),
            FakeResponse(200, {"definition": local_definition}),
        ]
    )
    result = deploy_definition(
        write_definition(tmp_path),
        WORKSPACE_ID,
        TOKEN,
        client=FabricClient(TOKEN, opener=opener),
    )

    assert result["service_acceptance"] == "create_and_get_definition_succeeded"
    assert result["semantic_equivalence"] == "not_asserted"
    assert result["item_id"] == ITEM_ID
    assert result["expected_part_count"] == result["returned_part_count"] == 3
    assert result["definition_part_paths_match"]
    assert result["definition_parts_textually_identical"]
    assert result["semantic_comparison"]["status"] == "completed"
    assert result["semantic_comparison"]["supported_fields_match"]
    assert not result["missing_part_paths"]
    assert not result["additional_part_paths"]
    assert not result["changed_part_paths"]
    create_request, get_request = [call[0] for call in opener.requests]
    assert (
        create_request.full_url
        == f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items"
    )
    assert create_request.get_method() == "POST"
    assert create_request.get_header("Authorization") == f"Bearer {TOKEN}"
    create_body = json.loads(create_request.data)
    assert create_body == {
        "displayName": "Example",
        "type": "Ontology",
        "definition": local_definition,
    }
    assert get_request.full_url == (
        f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items/{ITEM_ID}/getDefinition"
    )
    assert get_request.get_method() == "POST"


def test_deploy_waits_for_lro_and_retrieves_result(tmp_path):
    local_definition = definition()
    location = "https://df-msit-scus-redirect.analysis.windows.net/v1/operations/operation-id"
    create_operation_response = FakeResponse(200, {"status": "Succeeded"})
    create_operation_response.headers["Location"] = location + "/result?api-version=v1"
    get_operation_response = FakeResponse(200, {"status": "Succeeded"})
    get_operation_response.headers["Location"] = location + "/result?api-version=v1"
    responses = iter(
        [
            FakeResponse(202, headers=Message()),
            create_operation_response,
            FakeResponse(
                200,
                {"id": ITEM_ID, "type": "Ontology", "workspaceId": WORKSPACE_ID},
            ),
            FakeResponse(202, headers=Message()),
            get_operation_response,
            FakeResponse(200, {"definition": local_definition}),
        ]
    )
    responses_list = list(responses)
    responses_list[0].headers["Location"] = location
    responses_list[0].headers["Retry-After"] = "0"
    responses_list[3].headers["Location"] = location
    responses_list[3].headers["Retry-After"] = "0"
    opener = FakeOpener(responses_list)
    client = FabricClient(TOKEN, operation_timeout=5, sleep=lambda _: None, opener=opener)
    result = deploy_definition(
        write_definition(tmp_path),
        WORKSPACE_ID,
        TOKEN,
        client=client,
    )

    assert result["create_http_status"] == 202
    assert result["create_operation_status"] == "Succeeded"
    assert result["get_definition_http_status"] == 202
    assert result["get_definition_operation_status"] == "Succeeded"
    requests = [call[0] for call in opener.requests]
    assert [request.get_method() for request in requests] == [
        "POST",
        "GET",
        "GET",
        "POST",
        "GET",
        "GET",
    ]
    assert requests[1].full_url == location
    assert requests[1].get_header("Authorization") == f"Bearer {TOKEN}"
    assert (
        requests[2].full_url
        == "https://df-msit-scus-redirect.analysis.windows.net/v1/operations/operation-id/result"
        "?api-version=v1"
    )


def test_deploy_finds_created_item_when_lro_result_is_not_an_item(tmp_path):
    location = "https://api.fabric.microsoft.com/v1/operations/operation-id"
    create_response = FakeResponse(202)
    create_response.headers["Location"] = location
    create_response.headers["Retry-After"] = "0"
    definition_response = FakeResponse(202)
    definition_response.headers["Location"] = location
    definition_response.headers["Retry-After"] = "0"
    opener = FakeOpener(
        [
            create_response,
            FakeResponse(200, {"status": "Succeeded"}),
            FakeResponse(200, ["unexpected result shape"]),
            FakeResponse(
                200,
                {
                    "value": [
                        {
                            "id": ITEM_ID,
                            "displayName": "Example",
                            "type": "Ontology",
                            "workspaceId": WORKSPACE_ID,
                        }
                    ]
                },
            ),
            definition_response,
            FakeResponse(200, {"status": "Succeeded"}),
            FakeResponse(200, {"definition": definition()}),
        ]
    )
    client = FabricClient(TOKEN, operation_timeout=5, sleep=lambda _: None, opener=opener)

    result = deploy_definition(
        write_definition(tmp_path),
        WORKSPACE_ID,
        TOKEN,
        client=client,
    )

    assert result["item_id"] == ITEM_ID
    assert result["service_acceptance"] == "create_and_get_definition_succeeded"
    assert [call[0].get_method() for call in opener.requests] == [
        "POST",
        "GET",
        "GET",
        "GET",
        "POST",
        "GET",
        "GET",
    ]
    assert opener.requests[3][0].full_url.endswith("/items?type=Ontology&recursive=false")


def test_deploy_retries_throttled_api_response(tmp_path):
    retry_headers = Message()
    retry_headers["Retry-After"] = "0"
    throttled = HTTPError(
        f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/items",
        429,
        "Too Many Requests",
        retry_headers,
        io.BytesIO(b'{"errorCode":"TooManyRequests"}'),
    )
    opener = FakeOpener(
        [
            throttled,
            FakeResponse(
                201,
                {"id": ITEM_ID, "type": "Ontology", "workspaceId": WORKSPACE_ID},
            ),
            FakeResponse(200, {"definition": definition()}),
        ]
    )
    waits = []
    client = FabricClient(TOKEN, opener=opener, sleep=waits.append)
    result = deploy_definition(
        write_definition(tmp_path),
        WORKSPACE_ID,
        TOKEN,
        client=client,
    )

    assert result["service_acceptance"] == "create_and_get_definition_succeeded"
    assert len(opener.requests) == 3
    assert waits == [0.0]


@pytest.mark.parametrize(
    ("edit_parts", "missing", "additional", "changed"),
    [
        (lambda parts: parts.pop("database.tmdl"), ["database.tmdl"], [], []),
        (lambda parts: parts.update({"extra.tmdl": "extra"}), [], ["extra.tmdl"], []),
        (
            lambda parts: parts.update({"database.tmdl": "database\n"}),
            [],
            [],
            ["database.tmdl"],
        ),
    ],
)
def test_deploy_reports_definition_part_differences(
    tmp_path, edit_parts, missing, additional, changed
):
    submitted = definition()
    _, service_parts = decode_definition(submitted, "Definition")
    edit_parts(service_parts)
    returned = envelope(service_parts)
    opener = FakeOpener(
        [
            FakeResponse(
                201,
                {"id": ITEM_ID, "type": "Ontology", "workspaceId": WORKSPACE_ID},
            ),
            FakeResponse(200, {"definition": returned}),
        ]
    )

    result = deploy_definition(
        write_definition(tmp_path),
        WORKSPACE_ID,
        TOKEN,
        client=FabricClient(TOKEN, opener=opener),
    )

    assert result["service_acceptance"] == "create_and_get_definition_succeeded"
    assert result["semantic_equivalence"] == "not_asserted"
    assert result["semantic_comparison"]["status"] == "completed"
    assert result["semantic_comparison"]["supported_fields_match"]
    assert result["definition_part_paths_match"] == (not bool(missing or additional))
    assert not result["definition_parts_textually_identical"]
    assert result["missing_part_paths"] == missing
    assert result["additional_part_paths"] == additional
    assert result["changed_part_paths"] == changed


def test_unsupported_semantics_do_not_change_successful_service_acceptance(tmp_path):
    submitted = definition()
    _, service_parts = decode_definition(submitted, "Definition")
    service_parts["entities/default.Example.tmdl"] = service_parts[
        "entities/default.Example.tmdl"
    ].replace("\tlineageTag: example\n", "\tlineageTag: example\n\tisHidden: true\n")
    opener = FakeOpener(
        [
            FakeResponse(
                201,
                {"id": ITEM_ID, "type": "Ontology", "workspaceId": WORKSPACE_ID},
            ),
            FakeResponse(200, {"definition": envelope(service_parts)}),
        ]
    )

    result = deploy_definition(
        write_definition(tmp_path),
        WORKSPACE_ID,
        TOKEN,
        client=FabricClient(TOKEN, opener=opener),
    )

    assert result["service_acceptance"] == "create_and_get_definition_succeeded"
    assert result["semantic_equivalence"] == "not_asserted"
    assert result["semantic_comparison"]["status"] == "unsupported"
    assert "Unsupported TMDL construct" in result["semantic_comparison"]["error"]


def test_invalid_definition_or_name_is_rejected_before_network(tmp_path):
    path = write_definition(tmp_path)
    opener = FakeOpener([])
    with pytest.raises(ValueError, match="does not match"):
        deploy_definition(
            path,
            WORKSPACE_ID,
            TOKEN,
            expected_name="Different",
            client=FabricClient(TOKEN, opener=opener),
        )
    assert not opener.requests


def test_operation_url_validation_resolves_relative_locations():
    assert (
        FabricClient._validate_operation_url("/v1/operations/operation-id?api-version=v1")
        == "https://api.fabric.microsoft.com/v1/operations/operation-id?api-version=v1"
    )
    with pytest.raises(FabricApiError, match="invalid operation URL"):
        FabricClient._validate_operation_url(
            "https://untrusted.analysis.windows.net/v1/operations/operation-id"
        )


def test_external_lro_location_is_rejected_without_forwarding_authorization(tmp_path):
    response = FakeResponse(202)
    response.headers["Location"] = "https://attacker.example/v1/operations/id"
    opener = FakeOpener([response])
    with pytest.raises(FabricApiError, match="invalid operation URL"):
        deploy_definition(
            write_definition(tmp_path),
            WORKSPACE_ID,
            TOKEN,
            client=FabricClient(TOKEN, opener=opener),
        )
    assert len(opener.requests) == 1


def test_service_errors_never_echo_access_token(tmp_path):
    error = HTTPError(
        "https://api.fabric.microsoft.com/v1/workspaces/test/items",
        403,
        "Forbidden",
        Message(),
        io.BytesIO(f'{{"errorCode":"Forbidden","message":"Denied {TOKEN}"}}'.encode()),
    )
    opener = FakeOpener([error])
    with pytest.raises(FabricApiError, match="Forbidden") as raised:
        deploy_definition(
            write_definition(tmp_path),
            WORKSPACE_ID,
            TOKEN,
            client=FabricClient(TOKEN, opener=opener),
        )
    assert TOKEN not in str(raised.value)


def test_decode_definition_rejects_invalid_base64():
    invalid = {
        "parts": [
            {
                "path": ".platform",
                "payload": "!",
                "payloadType": "InlineBase64",
            }
        ]
    }
    with pytest.raises(ValueError, match="valid UTF-8 Base64"):
        decode_definition(invalid, "Definition")
