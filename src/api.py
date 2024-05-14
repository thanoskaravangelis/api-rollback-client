from flask import Flask, request, jsonify
import sys

app = Flask(__name__)

groups = {}

@app.route('/v1/group/<group_id>/', methods=['GET'])
async def get_group(group_id):
    """Get group by id"""
    if group_id in groups:
        return jsonify({'groupId': group_id}), 200
    else:
        return jsonify({'error': 'Group not found'}), 404

@app.route('/v1/group/', methods=['POST'])
async def create_group():
    """Create group by specifying group id in the request body."""
    data = request.get_json()
    group_id = data.get('groupId')
    if not group_id:
        return jsonify({'error': 'Bad request'}), 400
    if group_id in groups:
        return jsonify({'error': 'Group already exists'}), 400
    groups[group_id] = data
    return '', 201

@app.route('/v1/group/', methods=['DELETE'])
async def delete_group():
    """Delete group by specifying group id in the request body."""
    data = request.get_json()
    group_id = data.get('groupId')
    if not group_id:
        return jsonify({'error': 'Bad request'}), 400
    if group_id not in groups:
        return jsonify({'error': 'Group not found'}), 404
    del groups[group_id]
    return '', 200

if __name__ == '__main__':
    # run the app on port 5000 by default, unless specified otherwise
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(host='127.0.0.1', port=port)
