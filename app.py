from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from neo4j import GraphDatabase
from typing import List, Optional

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "neo4j+s://62a775a2.databases.neo4j.io"
AUTH = ("neo4j", "o7p1ooE0ZJhX0-veHd44Y6FCF4b5Auk2juNrRaKDDeM"
)

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()
class Database:
    def __init__(self, uri='neo4j+s://62a775a2.databases.neo4j.io', user='neo4j', password="o7p1ooE0ZJhX0-veHd44Y6FCF4b5Auk2juNrRaKDDeM"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def test_connection(self):
        with self.driver.session() as session:
            result = session.run("RETURN 'Neo4j connected' AS message")
            return result.single()["message"]

    # ==============================
    # User operations (Neo4j Cypher)
    # ==============================

    def create_user(self, username: str, name: str) -> int:
        with self.driver.session() as session:
            result = session.run(
                """
                CREATE (u:User {username: $username, name: $name})
                RETURN id(u) AS id
                """,
                username=username,
                name=name
            )
            return result.single()["id"]

    def get_user(self, user_id: int) -> Optional[dict]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (u:User)
                WHERE id(u) = $user_id
                RETURN id(u) AS id, u.username AS username, u.name AS name
                """,
                user_id=user_id
            )
            record = result.single()
            return dict(record) if record else None

    def get_all_users(self) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (u:User)
                RETURN id(u) AS id, u.username AS username, u.name AS name
                """
            )
            return [dict(record) for record in result]


    # User operations
    def create_user(self, username: str, name: str) -> int:
        with self.driver.session() as session:
            result = session.run(
                "CREATE (u:User {username: $username, name: $name}) RETURN id(u) AS id",
                username=username, name=name
            )
            return result.single()["id"]

    def get_user(self, user_id: int) -> Optional[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User) WHERE id(u) = $user_id "
                "RETURN id(u) AS id, u.username AS username, u.name AS name",
                user_id=user_id
            )
            record = result.single()
            return dict(record) if record else None

    def get_all_users(self) -> List[dict]:
        with self.driver.session() as session:
            result = session.run("MATCH (u:User) RETURN id(u) AS id, u.username AS username, u.name AS name")
            return [dict(record) for record in result]

    # Post operations
    def create_post(self, user_id: int, content: str) -> int:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User) WHERE id(u) = $user_id "
                "CREATE (p:Post {content: $content, timestamp: datetime()}) "
                "MERGE (u)-[:POSTED]->(p) "
                "RETURN id(p) AS id",
                user_id=user_id, content=content
            )
            return result.single()["id"]

    def get_posts_by_user(self, user_id: int) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User)-[:POSTED]->(p:Post) "
                "WHERE id(u) = $user_id "
                "RETURN id(p) AS id, p.content AS content, p.timestamp AS timestamp, u.username AS username, u.name AS name "
                "ORDER BY p.timestamp DESC",
                user_id=user_id
            )
            return [dict(record) for record in result]

    def get_feed(self, user_id: int) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (me:User)-[:FOLLOWS]->(other:User)-[:POSTED]->(p:Post) "
                "WHERE id(me) = $user_id "
                "RETURN id(p) AS id, p.content AS content, p.timestamp AS timestamp, other.username AS username, other.name AS name "
                "ORDER BY p.timestamp DESC",
                user_id=user_id
            )
            return [dict(record) for record in result]

    # Follow system
    def follow_user(self, follower_id: int, followee_id: int) -> bool:
        with self.driver.session() as session:
            session.run(
                "MATCH (a:User), (b:User) "
                "WHERE id(a) = $follower_id AND id(b) = $followee_id "
                "MERGE (a)-[:FOLLOWS]->(b)",
                follower_id=follower_id, followee_id=followee_id
            )
            return True

    def unfollow_user(self, follower_id: int, followee_id: int) -> bool:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (a:User)-[r:FOLLOWS]->(b:User) "
                "WHERE id(a) = $follower_id AND id(b) = $followee_id "
                "DELETE r RETURN COUNT(r) AS count",
                follower_id=follower_id, followee_id=followee_id
            )
            return result.single()["count"] > 0

    def get_followers(self, user_id: int) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (f:User)-[:FOLLOWS]->(u:User) "
                "WHERE id(u) = $user_id "
                "RETURN id(f) AS id, f.username AS username, f.name AS name",
                user_id=user_id
            )
            return [dict(record) for record in result]

    def get_following(self, user_id: int) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User)-[:FOLLOWS]->(f:User) "
                "WHERE id(u) = $user_id "
                "RETURN id(f) AS id, f.username AS username, f.name AS name",
                user_id=user_id
            )
            return [dict(record) for record in result]


# ======================
# Web Application
# ======================
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
db = Database(
    uri="neo4j+s://62a775a2.databases.neo4j.io",
    user="neo4j",
    password="o7p1ooE0ZJhX0-veHd44Y6FCF4b5Auk2juNrRaKDDeM"
)

    

# Sample data initialization
with app.app_context():
    if not db.get_all_users():
        db.create_user('alice', 'Alice Smith')
        db.create_user('bob', 'Bob Johnson')
        db.create_user('charlie', 'Charlie Brown')

# ======================
# API Endpoints
# ======================
@app.route('/api/users', methods=['GET'])
def api_get_users():
    return jsonify(db.get_all_users())

@app.route('/api/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    user = db.get_user(user_id)
    return jsonify(user) if user else ('User not found', 404)

@app.route('/api/users/<int:user_id>/posts', methods=['GET'])
def api_get_user_posts(user_id):
    return jsonify(db.get_posts_by_user(user_id))

@app.route('/api/users/<int:user_id>/feed', methods=['GET'])
def api_get_user_feed(user_id):
    return jsonify(db.get_feed(user_id))

@app.route('/api/users/<int:user_id>/followers', methods=['GET'])
def api_get_user_followers(user_id):
    return jsonify(db.get_followers(user_id))

@app.route('/api/users/<int:user_id>/following', methods=['GET'])
def api_get_user_following(user_id):
    return jsonify(db.get_following(user_id))

@app.route('/api/posts', methods=['POST'])
def api_create_post():
    data = request.get_json()
    post_id = db.create_post(data['user_id'], data['content'])
    return jsonify({'post_id': post_id}), 201

@app.route('/api/follow', methods=['POST'])
def api_follow_user():
    data = request.get_json()
    success = db.follow_user(data['follower_id'], data['followee_id'])
    return jsonify({'success': success}), 201 if success else 200

# ======================
# Frontend Routes
# ======================
@app.route('/')
def home():
    users = db.get_all_users()
    current_user = db.get_user(session['user_id']) if 'user_id' in session else None
    return render_template('index.html', users=users, current_user=current_user)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = db.get_user(user_id)
    if not user:
        return "User not found", 404

    current_user = db.get_user(session['user_id']) if 'user_id' in session else None
    is_following = False

    if current_user and current_user['id'] != user_id:
        following = db.get_following(current_user['id'])
        is_following = any(f['id'] == user_id for f in following)

    posts = db.get_posts_by_user(user_id)
    followers = db.get_followers(user_id)
    following = db.get_following(user_id)

    return render_template('profile.html',
                           user=user,
                           posts=posts,
                           followers=followers,
                           following=following,
                           current_user=current_user,
                           is_following=is_following)

@app.route('/user/<int:user_id>/feed')
def user_feed(user_id):
    user = db.get_user(user_id)
    feed = db.get_feed(user_id)
    return render_template('feed.html', user=user, feed=feed)

@app.route('/create_post', methods=['POST'])
def create_post():
    user_id = int(request.form['user_id'])
    content = request.form['content']
    db.create_post(user_id, content)
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/login/<int:user_id>')
def login(user_id):
    session['user_id'] = user_id
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/follow', methods=['POST'])
def follow():
    follower_id = int(request.form['follower_id'])
    followee_id = int(request.form['followee_id'])

    following = db.get_following(follower_id)
    is_following = any(f['id'] == followee_id for f in following)

    if is_following:
        db.unfollow_user(follower_id, followee_id)
    else:
        db.follow_user(follower_id, followee_id)

    return redirect(url_for('user_profile', user_id=followee_id))

# ======================
# Run the app on port 5000
# ======================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
