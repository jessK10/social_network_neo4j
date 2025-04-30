from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from neo4j import GraphDatabase
from typing import List, Optional

# ======================
# Database Access Layer (Neo4j AuraDB)
# ======================
class Database:
    def __init__(self, uri='neo4j+s://62a775a2.databases.neo4j.io', user='neo4j', password='o7p1ooE0ZJhX0-veHd44Y6FCF4b5Auk2juNrRaKDDeM'):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def test_connection(self):
        with self.driver.session() as session:
            result = session.run("RETURN 'Neo4j connected' AS message")
            return result.single()["message"]

    def create_user(self, username: str, name: str) -> str:
        with self.driver.session() as session:
            result = session.run(
                "CREATE (u:User {username: $username, name: $name}) RETURN elementId(u) AS id",
                username=username, name=name
            )
            return result.single()["id"]

    def get_user(self, user_id: str) -> Optional[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User) WHERE elementId(u) = $user_id "
                "RETURN elementId(u) AS id, u.username AS username, u.name AS name",
                user_id=user_id
            )
            record = result.single()
            return dict(record) if record else None

    def get_all_users(self) -> List[dict]:
        with self.driver.session() as session:
            result = session.run("MATCH (u:User) RETURN elementId(u) AS id, u.username AS username, u.name AS name")
            return [dict(record) for record in result]

    def create_post(self, user_id: str, content: str) -> str:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User) WHERE elementId(u) = $user_id "
                "CREATE (p:Post {content: $content, timestamp: datetime()}) "
                "MERGE (u)-[:POSTED]->(p) "
                "RETURN elementId(p) AS id",
                user_id=user_id, content=content
            )
            return result.single()["id"]

    def get_posts_by_user(self, user_id: str) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User)-[:POSTED]->(p:Post) "
                "WHERE elementId(u) = $user_id "
                "RETURN elementId(p) AS id, p.content AS content, p.timestamp AS timestamp, u.username AS username, u.name AS name "
                "ORDER BY p.timestamp DESC",
                user_id=user_id
            )
            return [dict(record) for record in result]

    def get_feed(self, user_id: str) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (me:User)-[:FOLLOWS]->(other:User)-[:POSTED]->(p:Post) "
                "WHERE elementId(me) = $user_id "
                "RETURN elementId(p) AS id, p.content AS content, p.timestamp AS timestamp, other.username AS username, other.name AS name "
                "ORDER BY p.timestamp DESC",
                user_id=user_id
            )
            return [dict(record) for record in result]

    def follow_user(self, follower_id: str, followee_id: str) -> bool:
        with self.driver.session() as session:
            session.run(
                "MATCH (a:User), (b:User) "
                "WHERE elementId(a) = $follower_id AND elementId(b) = $followee_id "
                "MERGE (a)-[:FOLLOWS]->(b)",
                follower_id=follower_id, followee_id=followee_id
            )
            return True

    def unfollow_user(self, follower_id: str, followee_id: str) -> bool:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (a:User)-[r:FOLLOWS]->(b:User) "
                "WHERE elementId(a) = $follower_id AND elementId(b) = $followee_id "
                "DELETE r RETURN COUNT(r) AS count",
                follower_id=follower_id, followee_id=followee_id
            )
            return result.single()["count"] > 0

    def get_followers(self, user_id: str) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (f:User)-[:FOLLOWS]->(u:User) "
                "WHERE elementId(u) = $user_id "
                "RETURN elementId(f) AS id, f.username AS username, f.name AS name",
                user_id=user_id
            )
            return [dict(record) for record in result]

    def get_following(self, user_id: str) -> List[dict]:
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User)-[:FOLLOWS]->(f:User) "
                "WHERE elementId(u) = $user_id "
                "RETURN elementId(f) AS id, f.username AS username, f.name AS name",
                user_id=user_id
            )
            return [dict(record) for record in result]

# ======================
# Web Application
# ======================
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
db = Database()

@app.route('/')
def home():
    users = db.get_all_users()
    current_user = db.get_user(session['user_id']) if 'user_id' in session else None
    return render_template('index.html', users=users, current_user=current_user)

@app.route('/user/<user_id>')
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

@app.route('/user/<user_id>/feed')
def user_feed(user_id):
    # Step 7: Feed Generation with login check and graceful error
    if 'user_id' not in session:
        return redirect(url_for('login', user_id=user_id))

    user = db.get_user(user_id)
    if not user:
        return "User not found", 404

    current_user = db.get_user(session['user_id'])
    feed = db.get_feed(user_id)

    return render_template('feed.html', user=user, current_user=current_user, feed=feed)

@app.route('/create_post', methods=['POST'])
def create_post():
    user_id = request.form['user_id']
    content = request.form['content']
    db.create_post(user_id, content)
    return redirect(url_for('user_profile', user_id=user_id))

@app.route('/login/<user_id>')
def login(user_id):
    session['user_id'] = user_id
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/follow', methods=['POST'])
def follow():
    follower_id = request.form['follower_id']
    followee_id = request.form['followee_id']

    following = db.get_following(follower_id)
    is_following = any(f['id'] == followee_id for f in following)

    if is_following:
        db.unfollow_user(follower_id, followee_id)
    else:
        db.follow_user(follower_id, followee_id)

    return redirect(url_for('user_profile', user_id=followee_id))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
