from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import hashlib
from functools import wraps
import time

app = Flask(__name__)

conn = pymysql.connect(host='localhost', port=3308, user='root', password='',
                       db='finstagram', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)


def login_required(f):
    @wraps(f)
    def dec(*args,**kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

# Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')


# Define route for login
@app.route('/login')
def login():
    return render_template('login.html')


# Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/follow')
@login_required
def follow():
    return render_template('follow.html')

@app.route('/follow_request', methods=['GET','POST'])
@login_required
def follow_request():
    user=session['username']
    cursor=conn.cursor()
    query = 'SELECT * FROM follow WHERE followee=%s AND followStatus=FALSE'
    cursor.execute(query, (user))
    data=cursor.fetchall()
    cursor.close()
    return render_template('follow_request.html', request=data)

@app.route('/friendgroup')
@login_required
def friendgroup():
    return render_template('friendgroup.html')

@app.route('/post')
@login_required
def post():
    return render_template('post.html')

@app.route('/view', methods=['GET','POST'])
@login_required
def view():
    pID=request.form["pID"]
    cursor=conn.cursor()
    query="SELECT * FROM photo JOIN person ON (poster=username) WHERE pID=%s"
    cursor.execute(query, (pID))
    photo=cursor.fetchone()
    query="SELECT * FROM reactto WHERE pID=%s"
    cursor.execute(query, (pID))
    react=cursor.fetchall()
    query="SELECT * FROM tag NATURAL JOIN person WHERE pID=%s AND tagStatus=1"
    cursor.execute(query, (pID))
    tag=cursor.fetchall()
    cursor.close()
    return render_template('view.html', photo=photo, react=react, tag=tag)



# Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    # grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()

    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashed))
    # stores the results in a variable
    data = cursor.fetchone()
    # use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if (data):
        # creates a session for the the user
        # session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        # returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)


# Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
@login_required
def registerAuth():
    # grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    fname = request.form['fname']
    lname = request.form['lname']
    email = request.form['email']
    hashed=hashlib.sha256(password.encode("utf-8")).hexdigest()

    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    query = 'SELECT * FROM person WHERE username = %s'
    cursor.execute(query, (username))
    # stores the results in a variable
    data = cursor.fetchone()
    # use fetchall() if you are expecting more than 1 data row
    error = None
    if (data):
        # If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error=error)
    else:
        ins = 'INSERT INTO person (username, password, firstName, lastName, email) VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, hashed, fname, lname, email))
        conn.commit()
        cursor.close()
        return render_template('index.html')


@app.route('/home', methods=['GET'])
@login_required
def home():
    user = session['username']
    cursor = conn.cursor();
    query = "SELECT pID FROM photo WHERE poster IN (SELECT poster FROM follow JOIN photo on(poster=followee) WHERE allFollowers=1 AND follower=%s AND followStatus=1) OR pID IN (SELECT pID FROM sharedwith WHERE (groupCreator,groupName) IN (SELECT groupCreator, groupName from belongto where username=%s)) OR poster=%s"
    cursor.execute(query, (user, user, user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('home.html', username=user, photos=data)

@app.route('/followAuth', methods=['GET', 'POST'])
@login_required
def followAuth():
    follower=session['username']
    followee=request.form['username']
    cursor=conn.cursor();
    query = 'SELECT username FROM person WHERE username=%s'
    cursor.execute(query,(followee))
    exist=cursor.fetchone()
    if(exist):
        query = 'SELECT follower FROM follow WHERE follower=%s AND followee=%s'
        cursor.execute(query, (follower, followee))
        data=cursor.fetchone()
        if(data):
            error = "You already sent follow request"
            return render_template('follow.html', error=error)
        else:
            ins = 'INSERT INTO follow (follower, followee, followStatus) VALUES(%s, %s, FALSE)'
            cursor.execute(ins, (follower, followee))
            conn.commit()
            cursor.close()
            return redirect(url_for('home'))
    else:
        error = "user not exist"
        return render_template('follow.html', error=error)

@app.route("/accept", methods=['GET','POST'])
@login_required
def accept():
    followee = session["username"]
    follower = request.args['follower']
    ac = request.args['choice']
    cursor = conn.cursor();
    if ac == "TRUE":
        up = 'UPDATE follow SET followStatus=TRUE WHERE follower=%s AND followee=%s'
        cursor.execute(up, (follower, followee))
        conn.commit()
        cursor.close()
    else:
        dele = 'DELETE FROM follow WHERE follower=%s AND followee=%s'
        cursor.execute(dele, (follower, followee))
        conn.commit()
        cursor.close()
    cursor = conn.cursor();
    query = 'SELECT * FROM follow WHERE followee=%s AND followStatus=FALSE'
    cursor.execute(query, (followee))
    data = cursor.fetchall()
    cursor.close()
    return render_template('follow_request.html', request=data)




@app.route('/posting', methods=['GET', 'POST'])
@login_required
def posting():
    username = session['username']
    filePath = request.form['filePath']
    choice = request.form['allFollowers']
    cursor = conn.cursor();
    postingtime = time.strftime('%y-%m-%d %H:%M:%S')
    if choice=="TRUE":
        query = 'INSERT INTO photo (filePath, postingDate, allFollowers, poster) VALUES(%s, %s, 1, %s)'
    else:
        query = 'INSERT INTO photo (filePath, postingDate, allFollowers, poster) VALUES(%s, %s, 0, %s)'
    cursor.execute(query, (filePath, postingtime, username))
    conn.commit()
    if choice=="FALSE":
        query = 'SELECT pID FROM photo WHERE postingDate=%s AND poster=%s'
        cursor.execute(query, (postingtime, username))
        pID = cursor.fetchall()
        query = 'SELECT groupName FROM friendgroup WHERE groupCreator=%s'
        cursor.execute(query, (username))
        friendgroup = cursor.fetchall()
        cursor.close()
        return render_template("select_friendgroup.html", friendgroup=friendgroup, pID=pID)
    cursor.close()
    return redirect(url_for('home'))

@app.route("/sharedwith", methods=['GET','POST'])
@login_required
def sharedwith():
    username=session["username"]
    groupname = request.form['groupname']
    pID=request.form['pID']
    cursor=conn.cursor()
    query = 'INSERT INTO sharedwith (pID, groupName, groupCreator) VALUES(%s, %s, %s)'
    cursor.execute(query, (pID, groupname, username))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/newgroup', methods=['GET','POST'])
@login_required
def newgroup():
    username=session['username']
    groupname=request.form['name']
    description=request.form['description']
    cursor=conn.cursor();
    query = "SELECT * FROM friendgroup WHERE groupName=%s AND groupCreator=%s"
    cursor.execute(query,(groupname, username))
    data=cursor.fetchone()
    if(data):
        error = "You already have that group"
        return render_template('friendgroup.html', error=error)
    else:
        ins = 'INSERT INTO friendgroup (groupName, groupCreator, description) VALUES (%s,%s,%s)'
        cursor.execute(ins,(groupname, username, description))
        conn.commit()
        ins = 'INSERT INTO belongTo (username,groupName,groupCreator) VALUES (%s,%s,%s)'
        cursor.execute(ins, (username, groupname, username))
        conn.commit()
        cursor.close()
        return redirect(url_for('home'))




@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')


app.secret_key = 'some key that you will never guess'
# Run the app on localhost port 5000
# debug = True -> you don't have to restart flask
# for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)
