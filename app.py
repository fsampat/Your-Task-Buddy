import os
import json

#from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, SQL

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    #Ensure responses aren't cached
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # Create a Connection object with SQLITE3 database
    con = SQL(r"taskbuddy.db")
    db = con.cursor()


    # Determine which user is signed in; store full name in variable to be passed to presentation layer
    user_id = session["user_id"]
    user = db.execute("SELECT fname, lname FROM users WHERE user_id = ?", (user_id,)).fetchone()
    fullname = user["fname"] + " " + user["lname"]

    # Determine which group the logged in user is on and then use its group_id to determine the projects it is a part of; to be passed to presentation layer
    group_id = db.execute("SELECT group_id FROM users WHERE user_id=?", (user_id,)).fetchone()["group_id"]
    if request.method == "GET":
        projects = db.execute("SELECT project_id, name, description, start_date, target_date FROM projects WHERE group_id=?", (group_id,)).fetchall()
        for project in projects:
            project["urgent"] = db.execute("SELECT COUNT(id) from tasks WHERE project_id = ? and status='Urgent'", (project["project_id"],)).fetchone()["COUNT(id)"]
            project["high"] = db.execute("SELECT COUNT(id) from tasks WHERE project_id = ? and status='High'", (project["project_id"],)).fetchone()["COUNT(id)"]
            project["med"] = db.execute("SELECT COUNT(id) from tasks WHERE project_id = ? and status='Med'", (project["project_id"],)).fetchone()["COUNT(id)"]
            project["low"]  = db.execute("SELECT COUNT(id) from tasks WHERE project_id = ? and status='Low'", (project["project_id"],)).fetchone()["COUNT(id)"]
            project["completed"] = db.execute("SELECT COUNT(id) from tasks WHERE project_id = ? and status='Complete'", (project["project_id"],)).fetchone()["COUNT(id)"]
        
        # Commit changes and close database connection
        con.close()
        return render_template("index.html", projects=projects, fullname=fullname)

@app.route("/login", methods=["GET", "POST"])
def login():
    #Log user in

    # Create a Connection object with SQLITE3 database
    con = SQL(r"taskbuddy.db")
    db = con.cursor()

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchone()
                
        # Ensure username exists and password is correct
        if not rows or not check_password_hash(rows["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] =  rows["user_id"]

        # Commit changes and close database connection
        con.close()
        
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Commit changes and close database connection
        con.close()
        return render_template("login.html")

@app.route("/modifytask", methods=["GET", "POST"])
def modifytask():
    
    # Create a Connection object with SQLITE3 database
    con = SQL(r"taskbuddy.db")
    db = con.cursor()

    # Modify an existing task
    user_id = session["user_id"]
    group_id = db.execute("SELECT group_id FROM users WHERE user_id = ?", (user_id,)).fetchone()["group_id"]
    
    # Get user's existing task information and pre-populate form on modify page to make it convenient for user to update
    if request.method == "POST":
        task = eval(request.form.get("task"))
        if request.form.get("update") == "modify":
            projects = db.execute("SELECT project_id, name, description, start_date, target_date FROM projects WHERE group_id=?", (group_id,)).fetchall()
            users = db.execute("SELECT fname, lname FROM users WHERE group_id=?", (group_id,)).fetchall()
            for user in users:
                user["fullname"] = user["fname"] + " " + user["lname"]
            date = task["date_due"]
            category = task["category"]
            description = task["description"]
            status = task["status"]
            pname = task["project_name"]
            assignto = task["assignedby"]
            
            # Commit changes and close database connection
            con.commit()
            con.close()
            return render_template("modifytask.html", task=task, projects=projects, users=users, category=category, description=description, status=status, date=date, pname=pname, assignto=assignto)
        
        # If user requested to delete task, update database, redirect back to task summary page
        elif request.form.get("update") == "delete":
            db.execute("DELETE FROM tasks WHERE id = ?", (task["id"],))

        # Get user's updated information and store in database; redirect user back to task summary page
        elif request.form.get("update") == "update":
            name = request.form.get("project")
            description = request.form.get("description")
            category = request.form.get("category")
            date = request.form.get("date")
            status = request.form.get("status")
            assignto = request.form.get("assignto")
            names = assignto.split()
            owner_id = db.execute("SELECT user_id FROM users WHERE fname = ? AND lname = ?", (names[0], names[1],)).fetchone()["user_id"]
            pid = db.execute("SELECT project_id FROM projects WHERE name = ?", (name,)).fetchone()["project_id"]
            db.execute("UPDATE tasks SET project_id = ?, description = ?, date_due = ?, category = ?, status = ?, owner_id = ?, assignee_id = ? WHERE id = ?", (pid, description, date, category, status, owner_id, user_id, task["id"],))

    # Commit changes and close database connection
    con.commit()
    con.close()
    return redirect("/tasks")

@app.route("/newtask", methods=["GET", "POST"])
def newtask():
    
    # Create a Connection object with SQLITE3 database
    con = SQL(r"taskbuddy.db")
    db = con.cursor()


    # Create a new task
    user_id = session["user_id"]
    group_id = db.execute("SELECT group_id FROM users WHERE user_id = ?", (user_id,)).fetchone()["group_id"]
    
    # Get user task information from form and store into database
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        date = request.form.get("date")
        db.execute("INSERT INTO projects (name, description, target_date, group_id) VALUES (?,?,?,?)", (name, description, date, group_id,))
        
        # Commit changes and close database connection
        con.commit()
        con.close()
        return redirect("/tasks")
    
    # Display list of task to user
    elif request.method == "GET":
        projects = db.execute("SELECT project_id, name, description, start_date, target_date FROM projects WHERE group_id = ?", (group_id,)).fetchall()
        users = db.execute("SELECT fname, lname FROM users WHERE group_id = ?", (group_id,)).fetchall()
        for user in users:
            user["fullname"] = user["fname"] + " " + user["lname"]

        # Close database connection
        con.close()
        return render_template("newtask.html", projects=projects, users=users)

@app.route("/projects", methods=["GET", "POST"])
def projects():
    
    # Create a Connection object with SQLITE3 database
    con = SQL(r"taskbuddy.db")
    db = con.cursor()

    # Create new project
    user_id = session["user_id"]
    group_id = db.execute("SELECT group_id FROM users WHERE user_id = ?", (user_id,)).fetchone()["group_id"]
    
    # Store user's provided project details into database and redirect user back to home page to view list of current projects
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        date = request.form.get("date")
        
        # check the username has not already been taken
        check_project_name = db.execute("SELECT name FROM projects where name = ?", (name,)).fetchone()
        if check_project_name:
                con.close()
                return apology("Project name " + check_project_name["name"] + " taken.  Please try again", 403)        
        
        db.execute("INSERT INTO projects (name, description, target_date, group_id) VALUES (?,?,?,?)", (name, description, date, group_id,))
        
        # Commit changes and close database connection
        con.commit()
        con.close()
        return redirect("/")

    elif request.method == "GET":
        return render_template("projects.html")

@app.route("/logout")
def logout():
    # Log out user

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():

    # Register team.  Step 1 of 2 step process.  Collect user info.
    if request.method == "GET":
        return render_template("register.html")

    # Upon form submission, get team name and # of members of users.  Move user to step 2.
    elif request.method == "POST":
        
        # Create a Connection object with SQLITE3 database
        con = SQL(r"taskbuddy.db")
        db = con.cursor()
        
        teamsize = int(request.form.get("size"))
        teamname = request.form.get("team")

        # check the team name has not already been taken
        check_teamname = db.execute("SELECT * FROM groups where name = ?", (teamname,)).fetchone()
        if check_teamname:
                con.close()
                return apology("Team name " + check_teamname["name"] + " taken.  Please try again", 403)

        con.close()
        return render_template("register2.html", teamsize=teamsize, teamname=teamname)

    return apology("Invalid Entry")

@app.route("/register2", methods=["GET", "POST"])
def register2():
    
    # Create a Connection object with SQLITE3 database
    con = SQL(r"taskbuddy.db")
    db = con.cursor()

    # Register team.  Step 2 of 2 step process.  Insert team and user information into database and return user back to login page.  
    if request.method == "POST":
        teamname = request.form.get("teamname")
        db.execute("INSERT INTO groups (name) VALUES (?)", (teamname,))
        teamid = db.execute("SELECT group_id FROM groups WHERE name = ?", (teamname,)).fetchone()["group_id"]
        teamsize = int(request.form.get("teamsize"))
        
        # store each user's provided information into the database
        for x in range(teamsize):
            fname = request.form.get("fname"+str(x))
            lname = request.form.get("lname"+str(x))
            email = request.form.get("email"+str(x))
            username = request.form.get("username"+str(x))
            password = generate_password_hash(request.form.get("password"+str(x)))

            # check the username has not already been taken
            check_username = db.execute("SELECT username FROM users where username = ?", (username,)).fetchone()
            if check_username:
                    con.close()
                    return apology("Username " + username + " taken.  Please try again", 403)

            db.execute("INSERT INTO users (fname, lname, email, username, hash, group_id) VALUES (?,?,?,?,?,?)", (fname, lname, email, username, password, teamid,))

    # Commit changes and close database connection
    con.commit()
    con.close()
    return redirect("/")

@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():

    # Create a Connection object with SQLITE3 database
    con = SQL(r"taskbuddy.db")
    db = con.cursor()

    user_id = session["user_id"]
    group_id = db.execute("SELECT group_id FROM users WHERE user_id=?", (user_id,)).fetchone()["group_id"]
    
    # Get list of tasks the user is associated with in database and pass info to presentation layer
    if request.method == "GET":
        tasks = db.execute("SELECT id, project_id, category, description, status, date_created, date_due, assignee_id FROM tasks WHERE owner_id=? ORDER BY project_id, category", (user_id,)).fetchall()
        for task in tasks:
            pname = db.execute("SELECT name FROM projects WHERE project_id = ?", (task["project_id"],)).fetchone()
            task["project_name"] = pname["name"]
            task["assignedby"] = "myself"
            if user_id != task["assignee_id"]:
                assignee = db.execute("SELECT fname, lname FROM users WHERE user_id=?", (task["assignee_id"],)).fetchone()
                assignedby = assignee["fname"] + " " + assignee["lname"]
                task["assignedby"] = assignedby
        
         # Close database connection
        con.close()
        return render_template("tasks.html", tasks=tasks)
    
    # Update database and redirect user back to task page upon modifying an existing task
    elif request.method == "POST":
        category = request.form.get("category")
        description = request.form.get("description")
        status = request.form.get("status")
        date = request.form.get("date")
        assignto = request.form.get("assignto")
        names = assignto.split()
        owner_id = db.execute("SELECT user_id FROM users WHERE fname = ? AND lname = ?", (names[0], names[1],)).fetchone()["user_id"]
        project = request.form.get("project")
        project_id = db.execute("SELECT project_id FROM projects WHERE name = ?", (project,)).fetchone()["project_id"]
        db.execute("INSERT INTO tasks (assignee_id, owner_id, status, category, description, date_due, project_id) VALUES (?,?,?,?,?,?,?)", (user_id, owner_id, status, category, description, date, project_id,))
        
        # Commit changes and close database connection
        con.commit()
        con.close()
        return redirect("/tasks")

