# Cluster Client API

## Overview
This project implements a client module that reliably creates and deletes groups across a cluster of nodes with an unstable API. It ensures that all nodes are updated consistently, with rollback mechanisms in place for error scenarios.

## Assumptions and Interpretations

This implementation assumes that the API endpoints for creating and deleting groups across the cluster nodes are prone to instability, potentially resulting in connection timeouts or 500 errors. To address this, error handling mechanisms are implemented, including rollback procedures to maintain consistency across all nodes. Specifically, if creating or deleting a group fails on any node, the operation is reversed on nodes where it was successful to prevent partial updates and ensure a consistent state amongst all hosts.

The implementation also assumes a predefined list of nodes (hosts) forming the cluster, specified in the `HOSTS` list within the code. It is assumed that all nodes expose the same RESTful API for managing groups. I also created an `api.py` file which reflects how that could API would look like and do some tests with my code. Before attempting to create a group, the client first checks if the group already exists on each node to avoid duplicate creation attempts and unnecessary errors. Similarly, during deletion, the client ensures that the group is removed from all nodes, and if any deletion fails, it triggers a rollback on nodes where the deletion succeeded.

Also, the code uses asynchronous programming with async and await to handle long-running I/O operations like network requests efficiently. This ensures that operations run concurrently without blocking each other, which is crucial for managing multiple nodes in a cluster. For example, the `create_group` and `delete_group` methods make concurrent HTTP requests to nodes, reducing overall execution time and improving reliability and performance in a distributed system.


## File Structure
```css
manifests/
├── deployment.yaml
├── service.yaml
src/
├── client.py
├── api.py
tests/
├── test_client.py
Dockerfile
requirements.txt
.gitignore
```

## Code Explanation

An overview of the methods covered in each file, you can also find more detailed comments in the code files.

**src/client.py**:

Defines the ClusterClient class with the following methods:

```group_exists(host, group_id)```: Checks if a group exists on a specified node. Returns True if a group exists on a node, otherwise False if it does not.

```create_group(group_id)```: Creates a group on all nodes and rolls back if creation fails on any node. Returns a lists of tuples containg the host and True/False depending on if the group was created successfully on the host.

```delete_group(group_id)```: Deletes a group on all nodes and rolls back if deletion fails on any node. Returns a lists of tuples containg the host and True/False depending on if the group was deleted successfully on the host.

```rollback_create(group_id, results)```: Rolls back group creation if it fails on any node.

```rollback_delete(group_id, results)```: Rolls back group deletion if it fails on any node.

**tests/test_client.py**

Contains 12 unit tests for the ClusterClient class methods using pytest and pytest-mock.

Tests successful and unsuccessful group creation and deletion.
Tests the rollback mechanisms for both create and delete operations.
Tests the main function which creates and then deletes a group.

Running Tests
To run the tests:

```bash
pytest
```

**manifests/deployment.yaml**

* apiVersion: Defines the API version used for the Deployment resource.
* kind: Indicates that the resource is a Deployment.
* metadata: Provides metadata about the Deployment, such as its name.
* spec: 
    * replicas: Specifies the number of pod replicas to maintain. (1)
    * selector: Defines how to match pods using labels.
    * template: Describes the pod configuration, including metadata and the specification for the containers.
        * containers: Lists the containers to run in each pod, their image,which is `client:latest` (the one we create locally), pull policies (Never, as we are using a local image), and exposed ports.

## Installation
Clone the repository:

```bash
git clone https://github.com/thanoskaravangelis/api-rollback-client
cd api-rollback-client
```
Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip3 install -r requirements.txt
```

Usage
To run the client:

```bash
python3 src/client.py
```

Build and run the Docker image:

```bash
docker build -t client:latest -f .
```

Load Docker Images into Minikube:

```bash
eval $(minikube docker-env)
minikube image load client:latest
```

Apply Kubernetes Manifests:

```bash
kubectl apply -f manifests/deployment.yaml
kubectl apply -f manifests/service.yaml
```

Verify Deployments:

```bash
kubectl get pods
```

Check Logs for Issues:

```bash
kubectl logs <pod-name>
```
