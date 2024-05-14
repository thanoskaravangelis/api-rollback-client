import httpx
import asyncio
import json

HOSTS = [
    '127.0.0.1:5000',
    '127.0.0.1:5001',
    '127.0.0.1:5002',
]

class ClusterClient:
    def __init__(self, hosts):
        self.hosts = hosts

    async def group_exists(self, host, group_id):
        """Check if group exists on a node."""
        url = f"http://{host}/v1/group/{group_id}/"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
        except httpx.RequestError:
            raise Exception(f"Failed to check if group {group_id} exists on {host}")
        return False

    async def create_group(self, group_id):
        """Create group on all nodes."""
        results = []
        for host in self.hosts:
            # send a get request to check if group exists on a node first
            if await self.group_exists(host, group_id):
                results.append((host, True))
                continue
            # if group does not exist, create it
            url = f"http://{host}/v1/group/"
            try:
                # create group on each node with async post request
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json={'groupId': group_id})
                    response.raise_for_status()
                    results.append((host, True))
            except httpx.HTTPStatusError:
                # if the request failed, mark result as False
                results.append((host, False))
        # rollback of group creation if the group was not created on all nodes
        if not all(result[1] for result in results):
            await self.rollback_create(group_id, results)
            raise Exception("Failed to create group on all nodes, rollback completed.")
        print(f"Created group: {group_id} successfully, on all nodes")
        return results

    async def rollback_create(self, group_id, results):
        """Rollback group creation on all nodes."""
        # if group was created on a node, delete it
        for host, success in results:
            if success:
                url = f"http://{host}/v1/group/"
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.request("DELETE", url, content=json.dumps({'groupId': group_id}), headers={'Content-Type': 'application/json'})
                        response.raise_for_status()
                except httpx.HTTPStatusError:
                    print(f"Failed to rollback group creation on {host}, inspect manually.")
    
    async def delete_group(self, group_id):
        """Delete group on all nodes."""
        results = []
        for host in self.hosts:
            url = f"http://{host}/v1/group/"
            try:
                # delete group on each node with async delete request
                async with httpx.AsyncClient() as client:
                    response = await client.request("DELETE", url, content=json.dumps({'groupId': group_id}), headers={'Content-Type': 'application/json'})
                    response.raise_for_status()
                    results.append((host, True))
            except httpx.HTTPStatusError:
                results.append((host, False))
        # rollback of group deletion if the group was not deleted on all nodes
        if not all(result[1] for result in results):
            await self.rollback_delete(group_id, results)
            raise Exception("Failed to delete group on all nodes, rollback completed")
        print(f"Deleted group: {group_id} successfully, from all nodes")
        return results
    
    async def rollback_delete(self, group_id, results):
        """Rollback group deletion on all nodes."""
        for host, success in results:
            if success:
                url = f"http://{host}/v1/group/"
                try:
                    # create group on each node with async post request
                    async with httpx.AsyncClient() as client:
                        response = await client.post(url, json={'groupId': group_id})
                        response.raise_for_status()
                except httpx.HTTPStatusError:
                    print(f"Failed to rollback group deletion on {host}, inspect manually.")

async def main():
    client = ClusterClient(HOSTS)
    group_id = "group-1"
    try:
        await client.create_group(group_id)
    except Exception as e:
        # if group creation failed, print exception and return so that group deletion is not attempted
        print(e)
        return
    
    try:
        await client.delete_group(group_id)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
