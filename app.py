from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime, timedelta, time
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import plotly.graph_objs as go
import plotly.io as pio
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import Base, Member, SignIn, User

# --- Flask App ---
app = Flask(__name__)
app.secret_key = 'attendance_secret_key'

# --- Database session ---
engine = create_engine('sqlite:///attendance.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# --- Flask-Login setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# --- User loader ---
class UserLogin(UserMixin, User):
    pass

@login_manager.user_loader
def load_user(user_id):
    user = session.query(User).get(int(user_id))
    if user:
        u = UserLogin()
        u.id = user.id
        u.username = user.username
        u.is_admin = user.is_admin
        return u
    return None

# --- Homepage (Login/Register selection) ---
@app.route('/')
def index():
    return render_template("index.html")

# --- Login / Logout ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(UserLogin(id=user.id, username=user.username, is_admin=user.is_admin))
            flash("Logged in successfully!", "success")
            return redirect(url_for("admin_dashboard") if user.is_admin else url_for("sign_in"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))

# --- Registration ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        is_admin = True if request.form.get("is_admin") == "on" else False

        if not username or not password:
            flash("Username and password are required!", "warning")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        existing_user = session.query(User).filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.", "warning")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, is_admin=is_admin)
        session.add(new_user)
        session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# --- Members ---
@app.route('/members', methods=['GET', 'POST'])
@login_required
def members():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form.get('category')
        session.add(Member(name=name, category=category))
        session.commit()
        flash("Member added successfully!", "success")
        return redirect(url_for('members'))
    members = session.query(Member).all()
    return render_template('members.html', members=members)

# --- Sign-in Page ---
@app.route("/sign-in", methods=["GET", "POST"])
@login_required
def sign_in():
    if request.method == "POST":
        member_id = request.form.get("member_id")
        today = date.today()
        now = datetime.now().time()

        allowed_days = ["Tuesday", "Wednesday", "Saturday"]
        today_name = today.strftime("%A")
        start_time = time(16, 30)
        end_time = time(17, 30)

        if today_name not in allowed_days:
            flash(f"Today is {today_name}. Sign-in is only allowed on Tuesday, Wednesday, and Saturday.", "warning")
            return redirect(url_for("sign_in"))

        if not (start_time <= now <= end_time):
            flash("Sign-in is allowed only between 4:30 PM and 5:30 PM.", "danger")
            return redirect(url_for("sign_in"))

        existing_sign = session.query(SignIn).filter_by(member_id=member_id, sign_date=today).first()
        if existing_sign:
            flash("You have already signed in today.", "info")
            return redirect(url_for("sign_in"))

        new_signin = SignIn(member_id=member_id, sign_date=today, sign_time=datetime.now().time())
        session.add(new_signin)
        session.commit()
        flash("Sign-in successful!", "success")
        return redirect(url_for("sign_in"))

    members = session.query(Member).order_by(Member.name).all()
    return render_template("sign_in.html", members=members)

# --- Today’s Sign-ins Page ---
@app.route("/today")
@login_required
def today():
    today_signins = session.query(SignIn).filter(SignIn.sign_date == date.today()).all()
    return render_template("today.html", signins=today_signins)

# --- Dashboard (analytics) ---
@app.route("/dashboard")
@login_required
def dashboard():
    members = session.query(Member).all()
    data = []
    for member in members:
        count = session.query(func.count(SignIn.id)).filter(SignIn.member_id == member.id).scalar()
        data.append({"name": member.name, "signins": count})

    # Plotly bar chart
    fig = go.Figure([go.Bar(x=[d["name"] for d in data], y=[d["signins"] for d in data])])
    fig.update_layout(title="Total Sign-ins per Member", xaxis_title="Member", yaxis_title="Sign-ins")
    chart_html = pio.to_html(fig, full_html=False)

    return render_template("dashboard.html", chart_html=chart_html, data=data)

# --- PDF Export ---
@app.route("/dashboard/pdf")
@login_required
def dashboard_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Attendance Report", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    data = [["Member Name", "Total Sign-ins"]]
    members = session.query(Member).all()
    for member in members:
        count = session.query(func.count(SignIn.id)).filter(SignIn.member_id == member.id).scalar()
        data.append([member.name, str(count)])

    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="attendance_report.pdf", mimetype="application/pdf")

# --- Admin Dashboard ---
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("sign_in"))

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    total_members = session.query(func.count(Member.id)).scalar()
    total_signins = session.query(func.count(SignIn.id)).scalar()
    weekly_signins = session.query(func.count(SignIn.id)).filter(SignIn.sign_date.between(week_start, week_end)).scalar()
    today_signins = session.query(func.count(SignIn.id)).filter(SignIn.sign_date == today).scalar()

    total_allowed_signins = session.query(func.count(SignIn.id)) \
        .filter(func.strftime('%w', SignIn.sign_date).in_(['2', '3', '6'])).scalar()
    avg_signins = round(total_allowed_signins / total_members, 2) if total_members > 0 else 0

    return render_template('admin_dashboard.html',
                           total_members=total_members,
                           total_signins=total_signins,
                           weekly_signins=weekly_signins,
                           today_signins=today_signins,
                           avg_signins=avg_signins,
                           week_start=week_start,
                           week_end=week_end)

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True)
