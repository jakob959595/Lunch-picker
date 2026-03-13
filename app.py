from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta
import random
from sqlalchemy import and_, or_

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-change-this"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    sent_requests = db.relationship(
        "Friendship",
        foreign_keys="Friendship.requester_id",
        backref="requester",
        lazy=True
    )
    received_requests = db.relationship(
        "Friendship",
        foreign_keys="Friendship.addressee_id",
        backref="addressee",
        lazy=True
    )

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    addressee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Space(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default="default space", unique=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    number_of_members = db.Column(db.Integer, default=1)
    owner = db.relationship("User", backref="spaces_owned")
    last_reset_week = db.Column(db.Integer)

class MemberShip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    space_id = db.Column(db.Integer, db.ForeignKey("space.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    asigned_day = db.Column(db.Integer)
class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey("space.id"), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.Enum("pending", "accepted", "rejected"), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Food_places(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class WeeklyMalca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey("space.id"), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    place_name = db.Column(db.String(200), default="") 
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    user = db.relationship("User", backref="weekly_malca")

def check_and_reset_schedule(space):
    current_week = datetime.now().isocalendar()[1]
    
    if space.last_reset_week != current_week:
        WeeklyMalca.query.filter_by(space_id=space.id).delete()

        members = MemberShip.query.filter_by(space_id=space.id).all()
        
        if not members:
            return 

        dnevi = [0, 1, 2, 3, 4]
        random.shuffle(members)

        for i in range(len(dnevi)):
            izbran_member = members[i % len(members)]
            trenutni_dan = dnevi[i]

            nova_malca = WeeklyMalca(
                space_id=space.id, 
                day_of_week=trenutni_dan, 
                user_id=izbran_member.user_id,
                place_name=""
            )
            db.session.add(nova_malca)

        space.last_reset_week = current_week
        db.session.commit()
def shuffle_if_new_members(space):
    WeeklyMalca.query.filter_by(space_id=space.id).delete()

    members = MemberShip.query.filter_by(space_id=space.id).all()
    if not members:
        return 
    dnevi = [0, 1, 2, 3, 4] 
    random.shuffle(members) 
    
    for i in range(len(dnevi)):
        izbran_member = members[i % len(members)]
        nova_malca = WeeklyMalca(
            space_id=space.id,
            day_of_week=i,
            user_id=izbran_member.user_id,
            place_name="" 
        )
        db.session.add(nova_malca)
    
    db.session.commit()
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/home")
def home_page():
    if "user_id" not in session:
        return redirect(url_for("login")) 
    return render_template("home.html", username=session["username"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/add_user", methods=["POST"])
def add_user():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    

    if not username or not email or not password:
        return "All fields are required", 400

    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return "Username or email already exists", 400

    new_user = User(username=username, email=email, password_hash=password)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == password:
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("home_page"))
        else:
            return "Invalid username or password", 400

    return render_template("login.html")

def getspaces():
    user_id = session["user_id"]
    memberships = MemberShip.query.filter_by(user_id=user_id).all()

    spaces = []
    for membership in memberships:
        space = Space.query.get(membership.space_id)
        spaces.append(space)

    return spaces

@app.route("/spaces")
def spaces():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    spaces = getspaces()
    return render_template("spaces.html", spaces=spaces)
@app.route("/create_space", methods=["GET", "POST"])
def create_space():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        space_name = request.form.get("space_name")
        space_description = request.form.get("space_description")

        if not space_name:
            return "Space name is required", 400

        existing_space = Space.query.filter_by(name=space_name).first()
        if existing_space:
            return "Space name already exists", 400

        new_space = Space(name=space_name, description=space_description, owner_id=session["user_id"])
        db.session.add(new_space)
        db.session.flush()

        new_membership = MemberShip(user_id=session["user_id"], space_id=new_space.id)
        db.session.add(new_membership)
        db.session.commit()

        return redirect(url_for("spaces"))

    return render_template("space_creator.html")

@app.route("/menu")
def menu():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    return render_template("home.html")
def get_all_users():
    logged_in_user_id = session["user_id"]
    users = User.query.filter(
        User.id != logged_in_user_id,
        ~Friendship.query.filter(
            or_(
                and_(Friendship.requester_id == logged_in_user_id,
                     Friendship.addressee_id == User.id,
                     Friendship.status == "accepted"),

                and_(Friendship.addressee_id == logged_in_user_id,
                     Friendship.requester_id == User.id,
                     Friendship.status == "accepted"),
                and_(Friendship.requester_id == logged_in_user_id,
                     Friendship.addressee_id == User.id,
                     Friendship.status == "pending"),
            )
        ).exists()
    ).all()
    people = [] 
    for user in users:
        user_info  = User.query.get(user.id)
        people.append(user_info)
    return people
@app.route("/add_to_space/<int:space_id>/<int:user_id>")
def add_to_space(space_id, user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    space = Space.query.get(space_id)
    if not space:
        return redirect(url_for("spaces"))
    new_membership = MemberShip(user_id=user_id, space_id=space_id)
    db.session.add(new_membership)
    db.session.commit()
    shuffle_if_new_members(space)
    return redirect(url_for("space_detail", space_id=space_id))
@app.route("/people")
def people():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    users = get_all_users()
    return render_template("people.html", people=users)
@app.route("/find_person", methods=["POST", "GET"])
def find_person():
    if "user_id" not in session:
        return redirect(url_for("login"))
    person = request.args.get("query", "")
    all_users = get_all_users()
    for person1 in all_users:
        if person1["username"] == person:
            return render_template("people.html", people=[person1])
    return render_template("people.html", people=all_users)
@app.route("/add_friend/<int:person_id>")
def add_friend(person_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    requester_id = session["user_id"]

    existing_friendship = Friendship.query.filter(
        or_(
            and_(Friendship.requester_id == requester_id, Friendship.addressee_id == person_id),
            and_(Friendship.requester_id == person_id, Friendship.addressee_id == requester_id)
        )
    ).first()

    if existing_friendship:
        if existing_friendship.status == "pending" and existing_friendship.addressee_id == requester_id:
            existing_friendship.status = "accepted"
    else:
        new_friendship = Friendship(requester_id=requester_id, addressee_id=person_id, status="pending")
        db.session.add(new_friendship)
    
    db.session.commit()
    return render_template("people.html", people=get_all_users())

def get_all_friend_requests():
    if "user_id" not in session:
        return []
    user_id = session["user_id"]
    requests = Friendship.query.filter_by(addressee_id=user_id, status="pending").all()
    requesters = []
    for req in requests:
        requester = User.query.get(req.requester_id)
        requesters.append(requester)
    return requesters

@app.route("/friend_requests")
def friend_requests():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    return render_template("friend_requests.html", requesters=get_all_friend_requests())
@app.route("/accept_friend_request/<int:requester_id>")
def accept_friend_request(requester_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    friendship = Friendship.query.filter_by(requester_id=requester_id, addressee_id=user_id, status="pending").first()
    if friendship:
        friendship.status = "accepted"
        db.session.commit()
    return render_template("friend_requests.html", requesters=get_all_friend_requests())
@app.route("/decline_friend_request/<int:requester_id>")
def decline_friend_request(requester_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    friendship = Friendship.query.filter_by(requester_id=requester_id, addressee_id=user_id, status="pending").first()
    if friendship:
        db.session.delete(friendship)
        db.session.commit()
    return render_template("friend_requests.html", requesters=get_all_friend_requests())
def get_all_friends():
    user_id = session["user_id"]
    friendships = Friendship.query.filter(
        ((Friendship.requester_id == user_id) | (Friendship.addressee_id == user_id)) & (Friendship.status == "accepted")
    ).all()
    friends = []
    for friendship in friendships:
        if friendship.requester_id == user_id:
            friend = User.query.get(friendship.addressee_id)
        else:
            friend = User.query.get(friendship.requester_id)
        friends.append(friend)
    return friends
@app.route("/friends")
def friends():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    friends_list = get_all_friends()
    return render_template("friends.html", friends=friends_list)
@app.route("/space_detail/<int:space_id>")
def space_detail(space_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    space = Space.query.get(space_id)
    if not space:
        return redirect(url_for("spaces"))
    check_and_reset_schedule(space)
    urnik = WeeklyMalca.query.filter_by(space_id=space_id).order_by(WeeklyMalca.day_of_week).all()
    members = MemberShip.query.filter_by(space_id=space_id).all()
    members_info = []
    for member in members:
        user_info = User.query.get(member.user_id)
        members_info.append(user_info)

    return render_template("space_detail.html", space=space, members=members_info, current_user_id=session["user_id"], urnik=urnik)
@app.route("/invite_to_space/<int:space_id>")
def invite_to_space(space_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    space = Space.query.get(space_id)
    if not space:
        return redirect(url_for("spaces"))
    user_id = session["user_id"]
    friendships = Friendship.query.filter(
        and_(
            or_(
                Friendship.requester_id == user_id,
                Friendship.addressee_id == user_id
            ),
            Friendship.status == "accepted"
        )
    ).all()

    friend_ids = []
    for f in friendships:
        if f.requester_id == user_id:
            friend_ids.append(f.addressee_id)
        else:
            friend_ids.append(f.requester_id)

    if not friend_ids:
        return redirect(url_for("spaces"))
    member_subquery = db.session.query(MemberShip.user_id).filter(
        MemberShip.space_id == space_id
    ).subquery()

    friends_to_invite = User.query.filter(
        User.id.in_(friend_ids),
        ~User.id.in_(member_subquery)
    ).all()

    new_number_of_members = space.number_of_members + 1
    space.number_of_members = new_number_of_members
    db.session.commit()

    return render_template("invite_to_space.html", space=space, friends=friends_to_invite)
@app.route("/remove_user/<int:space_id>/<int:user_id>")
def remove_user(space_id, user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    space = Space.query.get(space_id)
    if not space:
        return redirect(url_for("spaces"))
    
    if space.owner_id != session["user_id"]:
        return redirect(url_for("space_detail", space_id=space_id, user_id=session["user_id"]))
    
    membership = MemberShip.query.filter_by(space_id=space_id, user_id=user_id).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()

    return redirect(url_for("space_detail", space_id=space_id))
@app.route("/leave_space/<int:space_id>")
def leave_space(space_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    space = Space.query.get(space_id)
    if not space:
        return redirect(url_for("spaces"))
    
    membership = MemberShip.query.filter_by(space_id=space_id, user_id=session["user_id"]).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()

    return redirect(url_for("spaces"))
@app.route("/add_food_place/<int:vnos_id>", methods=["POST"])
def add_food_place(vnos_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    vnos = WeeklyMalca.query.get(vnos_id)
    space = Space.query.get(vnos.space_id)
    if not space:
        return redirect(url_for("spaces"))
    place_name = request.form.get("place_name")
    malca_entry = WeeklyMalca.query.get(vnos_id)
    if place_name is not None:
        malca_entry.place_name = place_name
        db.session.commit()
    return redirect(url_for("space_detail", space_id=vnos.space_id))
@app.route("/remove_friend/<int:friend_id>")
def remove_friend(friend_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user_id = session["user_id"]
    friendship = Friendship.query.filter(
        or_(
            and_(Friendship.requester_id == user_id, Friendship.addressee_id == friend_id),
            and_(Friendship.requester_id == friend_id, Friendship.addressee_id == user_id)
        ),
        Friendship.status == "accepted"
    ).first()

    if friendship:
        db.session.delete(friendship)
        db.session.commit()
    
    return redirect(url_for("friends"))
if __name__ == "__main__":
    with app.app_context():
        db.create_all()


        if not User.query.first():
            from werkzeug.security import generate_password_hash
            from datetime import datetime

            user1 = User(username="jakob", email="princeska@test.com",
                         password_hash="1234",
                         created_at=datetime.utcnow())
            user2 = User(username="jakob95", email="alpha@test.com",
                         password_hash="1234",
                         created_at=datetime.utcnow())
            user3 = User(username="jakob59", email="beta@test.com",
                         password_hash="1234",
                         created_at=datetime.utcnow())
            user4 = User(username="jakob55", email="beta1@test.com",
                         password_hash="1234",
                         created_at=datetime.utcnow())
            user5 = User(username="jakob99", email="beta2@test.com",
                         password_hash="1234",
                         created_at=datetime.utcnow())

            db.session.add_all([user1, user2, user3, user4, user5])
            db.session.commit()
    app.run(debug=True)
