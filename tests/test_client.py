import pytest, httpx, json
from pytest_mock import MockerFixture
from src.client import ClusterClient, main

class MockResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code
        
    def raise_for_status(self):
        if self.status_code not in [200, 201]:
            raise httpx.HTTPStatusError("Error", request=None, response=self)

@pytest.mark.asyncio
async def test_create_group_is_successful(mocker):
    """Test when all create requests are successful. The result should be a list of tuples with the hosts and True values."""
    mock_get = mocker.AsyncMock(return_value=MockResponse(status_code=404))
    mocker.patch("httpx.AsyncClient.get", new=mock_get)
    mock_post = mocker.AsyncMock(return_value=MockResponse(status_code=201))
    mocker.patch("httpx.AsyncClient.post", new=mock_post)
    client = ClusterClient(["host1", "host2"])
    result = await client.create_group("group1")
    assert result == [("host1", True), ("host2", True)]
    mock_get.assert_any_call("http://host1/v1/group/group1/")
    mock_get.assert_any_call("http://host2/v1/group/group1/")
    mock_post.assert_any_call("http://host1/v1/group/", json={"groupId": "group1"})
    mock_post.assert_any_call("http://host2/v1/group/", json={"groupId": "group1"})

@pytest.mark.asyncio
async def test_create_group_is_unsuccessful_one(mocker):
    """Test when one create request fails. We assume that group does not already exist in any of the nodes.
    Rollback should be called on the node that the group was created in."""
    mock_get = mocker.AsyncMock(return_value=MockResponse(status_code=404))
    mocker.patch("httpx.AsyncClient.get", new=mock_get)
    mock_post = mocker.AsyncMock(side_effect=[MockResponse(status_code=201), MockResponse(status_code=500)])
    mocker.patch("httpx.AsyncClient.post", new=mock_post)
    mock_delete = mocker.AsyncMock(side_effect=[MockResponse(status_code=200)])
    mocker.patch("httpx.AsyncClient.request", new=mock_delete)
    client = ClusterClient(["host1", "host2"])
    with pytest.raises(Exception) as exc:
        await client.create_group("group1")
    assert str(exc.value) == "Failed to create group on all nodes, rollback completed."
    mock_get.assert_any_call("http://host1/v1/group/group1/")
    mock_get.assert_any_call("http://host2/v1/group/group1/")
    mock_post.assert_any_call("http://host1/v1/group/", json={"groupId": "group1"})
    mock_post.assert_any_call("http://host2/v1/group/", json={"groupId": "group1"})
    mock_delete.assert_any_call("DELETE", "http://host1/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})

@pytest.mark.asyncio
async def test_create_group_is_unsuccessful_all(mocker):
    """Test when all create requests fail. We assume that group does not already exist in any of the nodes.
    Rollback should be called on all nodes but in this case, none of the nodes will need to rollback."""
    mock_get = mocker.AsyncMock(return_value=MockResponse(status_code=404))
    mocker.patch("httpx.AsyncClient.get", new=mock_get)
    # mock two failed responses for the post request
    mock_post = mocker.AsyncMock(side_effect=[MockResponse(status_code=500), MockResponse(status_code=500)])
    mocker.patch("httpx.AsyncClient.post", new=mock_post)
    client = ClusterClient(["host1", "host2"])
    with pytest.raises(Exception) as exc:
        await client.create_group("group1")
    assert str(exc.value) == "Failed to create group on all nodes, rollback completed."
    mock_get.assert_any_call("http://host1/v1/group/group1/")
    mock_get.assert_any_call("http://host2/v1/group/group1/")
    mock_post.assert_any_call("http://host1/v1/group/", json={"groupId": "group1"})
    mock_post.assert_any_call("http://host2/v1/group/", json={"groupId": "group1"})

@pytest.mark.asyncio
async def test_rollback_create_is_successful(mocker):
    """Test when the rollback is successful on all nodes."""
    # mock only one OK response for the delete request on the second host
    mock_delete = mocker.AsyncMock(side_effect=[MockResponse(status_code=200)])
    mocker.patch("httpx.AsyncClient.request", new=mock_delete)
    client = ClusterClient(["host1", "host2"])
    await client.rollback_create("group1", [("host1", False), ("host2", True)])
    # assert delete request was made only on second host
    mock_delete.assert_any_call("DELETE", "http://host2/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})

@pytest.mark.asyncio
async def test_rollback_create_is_unsuccessful_httpx_error(mocker: MockerFixture, capfd):
    """Test when the rollback fails with an HTTP error."""
    mock_delete = mocker.AsyncMock(side_effect=[MockResponse(status_code=500)])
    mocker.patch("httpx.AsyncClient.request", new=mock_delete)
    client = ClusterClient(["host1", "host2"])
    await client.rollback_create("group1", [("host1", False), ("host2", True)])
    # capture the output and assert printed message
    captured = capfd.readouterr()
    assert "Failed to rollback group creation on host2, inspect manually." in captured.out
    # assert delete requests was made only to the first host with an error
    mock_delete.assert_any_call("DELETE", "http://host2/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})

@pytest.mark.asyncio
async def test_delete_group_is_successful(mocker):
    mock_delete = mocker.AsyncMock(return_value=MockResponse(status_code=200))
    mocker.patch("httpx.AsyncClient.request", new=mock_delete)
    client = ClusterClient(["host1", "host2"])
    result = await client.delete_group("group1")
    assert result == [("host1", True), ("host2", True)]
    mock_delete.assert_any_call("DELETE", "http://host1/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})
    mock_delete.assert_any_call("DELETE", "http://host2/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})

@pytest.mark.asyncio
async def test_delete_group_is_unsuccessful_one(mocker):
    """Test when one delete request fails. Rollback should be called on the node that the group was deleted from."""
    mock_delete = mocker.AsyncMock(side_effect=[MockResponse(status_code=200), MockResponse(status_code=500)])
    mocker.patch("httpx.AsyncClient.request", new=mock_delete)
    mock_post = mocker.AsyncMock(side_effect=[MockResponse(status_code=201)])
    mocker.patch("httpx.AsyncClient.post", new=mock_post)
    client = ClusterClient(["host1", "host2"])
    with pytest.raises(Exception) as exc:
        await client.delete_group("group1")
    assert str(exc.value) == "Failed to delete group on all nodes, rollback completed"
    mock_delete.assert_any_call("DELETE", "http://host1/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})
    mock_delete.assert_any_call("DELETE", "http://host2/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})
    mock_post.assert_any_call("http://host1/v1/group/", json={"groupId": "group1"})

@pytest.mark.asyncio
async def test_delete_group_is_unsuccessful_all(mocker):
    """Test when all delete requests fail. Rollback should be called on all nodes but in this case, none of the nodes will need to rollback."""
    mock_delete = mocker.AsyncMock(side_effect=[MockResponse(status_code=500), MockResponse(status_code=500)])
    mocker.patch("httpx.AsyncClient.request", new=mock_delete)
    client = ClusterClient(["host1", "host2"])
    with pytest.raises(Exception) as exc:
        await client.delete_group("group1")
    assert str(exc.value) == "Failed to delete group on all nodes, rollback completed"
    mock_delete.assert_any_call("DELETE", "http://host1/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})
    mock_delete.assert_any_call("DELETE", "http://host2/v1/group/", content=json.dumps({"groupId": "group1"}), headers={'Content-Type': 'application/json'})

@pytest.mark.asyncio
async def test_rollback_delete_is_successful(mocker):
    """Test when the rollback is successful on all nodes."""
    mock_post = mocker.AsyncMock(side_effect=[MockResponse(status_code=201)])
    mocker.patch("httpx.AsyncClient.post", new=mock_post)
    client = ClusterClient(["host1", "host2"])
    await client.rollback_delete("group1", [("host1", False), ("host2", True)])
    # assert post request was made only on second host
    mock_post.assert_any_call("http://host2/v1/group/", json={"groupId": "group1"})

@pytest.mark.asyncio
async def test_rollback_delete_is_unsuccessful_httpx_error(mocker: MockerFixture, capfd):
    """Test when the rollback fails with an HTTP error."""
    mock_post = mocker.AsyncMock(side_effect=[MockResponse(status_code=500)])
    mocker.patch("httpx.AsyncClient.post", new=mock_post)
    client = ClusterClient(["host1", "host2"])
    await client.rollback_delete("group1", [("host1", False), ("host2", True)])
    # capture the output and assert printed message
    captured = capfd.readouterr()
    assert "Failed to rollback group deletion on host2, inspect manually." in captured.out
    # assert post requests was made only to the first host with an error
    mock_post.assert_any_call("http://host2/v1/group/", json={"groupId": "group1"})

@pytest.mark.asyncio
async def test_main(mocker: MockerFixture):
    mock_create_group = mocker.AsyncMock(return_value=[("host1", True), ("host2", True)],  )
    mocker.patch("src.client.ClusterClient.create_group", new=mock_create_group)
    mock_delete_group = mocker.AsyncMock(return_value=[("host1", True), ("host2", True)], )
    mocker.patch("src.client.ClusterClient.delete_group", new=mock_delete_group)
    await main()
    mock_create_group.assert_called_once_with("group-1")
    mock_delete_group.assert_called_once_with("group-1")

@pytest.mark.asyncio
async def test_main_create_group_fails(mocker: MockerFixture, capfd):
    """Test when create group fails. There is an Exception thrown after the rollback for the creation has run. After that,
    the delete group should be called on all nodes."""
    mock_create_group = mocker.AsyncMock(side_effect=Exception("Failed to create group on all nodes, rollback completed."))
    mocker.patch("src.client.ClusterClient.create_group", new=mock_create_group)
    mock_delete_group = mocker.AsyncMock(return_value=[("host1", False), ("host2", False)], )
    mocker.patch("src.client.ClusterClient.delete_group", new=mock_delete_group)
    await main()
    captured = capfd.readouterr()
    assert "Failed to create group on all nodes, rollback completed." in captured.out
    mock_create_group.assert_called_once_with("group-1")
    mock_delete_group.assert_not_called()

if __name__ == "__main__":
    pytest.main()