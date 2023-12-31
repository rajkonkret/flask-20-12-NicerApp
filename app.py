import binascii
import hashlib
import random
import string

from flask import Flask, render_template, request, flash, g, redirect, url_for, session
import sqlite3
from datetime import date

app_info = {
    'db_file': 'data/cantor.db'
}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SomethingWhatICantQGuess2'


class Currency:

    def __init__(self, code, name, flag):
        self.code = code
        self.name = name
        self.flag = flag

    def __repr__(self):
        return f'<Currency {self.code}>'


class CantorOffer:

    def __init__(self):
        self.currencies = []
        self.denied_codes = []

    def load_offer(self):
        """
        łąduje znane nam waluty do systemu
        :return:
        """
        self.currencies.append(Currency('USD', 'Dollar', 'usd.png'))
        self.currencies.append(Currency('EUR', 'Euro', 'euro.png'))
        self.currencies.append(Currency('JPY', 'Yen', 'yen.png'))
        self.currencies.append(Currency('GBP', 'Pound', 'pound.png'))
        self.denied_codes.append('USD')

    def get_by_code(self, code):
        for currency in self.currencies:
            if currency.code == code:
                return currency
        return Currency('unknown', 'unknown', 'flag_pirat.png')


class UserPass:
    def __init__(self, user='', password=''):
        self.user = user
        self.password = password

    def hash_password(self):
        os_urandom_static = b'|\x0c\xaf:\xf4\xa8\xf9\x04\xf4_\x18\xb2Za;Hf9cv\x98(\xe6IG\x068\x13-\xe2\x08\x93\xe5D\xac\xd0e>\xd3\xf9B\xfcf\x13\x95j`\xf0\x19\xdf\xe3f9tO\x9a *\xfc\xe0'
        salt = hashlib.sha256(os_urandom_static).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', self.password.encode('utf-8'), salt, 100000)
        pwdhash = binascii.hexlify(pwdhash)
        return (salt + pwdhash).decode('ascii')

    def verify_password(self, stored_password, provided_password):
        salt = stored_password[:64]
        stored_password = stored_password[64:]
        pwdhash = hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt.encode('utf-8'),
                                      100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == stored_password

    def get_random_user_password(self):
        random_user = ''.join(random.choice(string.ascii_lowercase) for i in range(3))
        self.user = random_user

        password_characters = string.ascii_letters
        random_password = ''.join(random.choice(password_characters) for i in range(3))
        self.password = random_password

    def login_user(self):
        db = get_db()
        sql_statement = 'select id, name, email, password, is_active, is_admin from users where name=?;'
        cur = db.execute(sql_statement, [self.user])
        user_record = cur.fetchone()

        if user_record != None and self.verify_password(user_record['password'], self.password):
            return user_record
        else:
            self.user = None
            self.password = None
            return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', active_menu='login')
    else:
        user_name = '' if "user_name" not in request.form else request.form['user_name']
        user_pass = '' if "user_pass" not in request.form else request.form['user_pass']

    login = UserPass(user_name, user_pass)
    login_record = login.login_user()

    if login_record != None:
        session['user'] = user_name
        # flash("Login succesfull, welcome {}".format(user_name))
        flash(f"Login succesfull, welcome {user_name}")
        return redirect(url_for('index'))
    else:
        flash("Logon failed, try again")
        return render_template('login.html', active_menu='login')


@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user', None)
        flash("You are logged out")
    return redirect(url_for('login'))


@app.route("/new_user", methods=['GET', 'POST'])
def new_user():
    if not 'user' in session:
        return redirect(url_for('login'))

    login = session['user']

    db = get_db()
    message = None
    user = {}
    if request.method == 'GET':
        return render_template('new_user.html', active_menu='users', user=user)
    else:
        user['user_name'] = '' if not 'user_name' in request.form else request.form['user_name']
        user['email'] = '' if not 'email' in request.form else request.form['email']
        user['user_pass'] = '' if not 'user_pass' in request.form else request.form['user_pass']

        cursor = db.execute('select count(*) as cnt from users where name=?;',
                            [user['user_name']])
        record = cursor.fetchone()
        is_user_name_unique = (record['cnt'] == 0)

        cursor = db.execute('select count(*) as cnt from users where email=?;',
                            [user['email']])
        record = cursor.fetchone()
        is_user_email_unique = (record['cnt'] == 0)

        if user['user_name'] == '':
            message = "Name cannot be empty"
        elif user['email'] == '':
            message = "Email cannot be empty"
        elif user['user_pass'] == '':
            message = "Password cannot be empty"
        elif not is_user_name_unique:
            message = f"User with the name {user['user_name']} already exist"
        elif not is_user_email_unique:
            message = f"User with the email {user['email']} already exist"

        if not message:
            user_pass = UserPass(user['user_name'], user['user_pass'])
            password_hash = user_pass.hash_password()
            sql_statement = '''insert into users(name,email,password,is_active,is_admin)
            values(?,?,?,True,False);'''
            db.execute(sql_statement, [user['user_name'], user['email'], password_hash])
            db.commit()
            flash(f"User {user['user_name']} created")
            return redirect(url_for('users'))
        else:
            flash(f"Correct error: {message}")
            return render_template('new_user.html', active_menu='users', user=user)


@app.route('/users')
def users():
    if not 'user' in session:
        return redirect(url_for('login'))

    db = get_db()
    sql_command = 'select id, name, email,is_admin,is_active from users;'
    cur = db.execute(sql_command)
    users = cur.fetchall()

    return render_template('users.html', active_menu='users', users=users)


@app.route("/delete_user/<user_name>")
def delete_user(user_name):
    if not 'user' in session:
        return redirect(url_for('login'))
    login = session['user']

    db = get_db()
    # <> - rożne
    sql_statement = 'delete from users where name=? and name <> ?;'
    db.execute(sql_statement, [user_name, login])
    db.commit()

    return redirect(url_for('users'))


@app.route('/edit_user/<user_name>', methods=['GET', 'POST'])
def edit_user(user_name):
    if not 'user' in session:
        return redirect(url_for('login'))

    db = get_db()
    cur = db.execute('select name, email from users where name=?', [user_name])
    user = cur.fetchone()
    message = None

    if user == None:
        flash("No such user")
        return redirect(url_for('users'))

    if request.method == 'GET':
        return render_template('edit_user.html', active_menu='users', user=user)

    else:
        new_email = '' if 'email' not in request.form else request.form['email']
        new_password = '' if 'user_pass' not in request.form else request.form['user_pass']

        if new_email != user['email']:
            sql_statement = 'update users set email=? where name=?;'
            db.execute(sql_statement, [new_email, user_name])
            db.commit()
            flash("Email was changed")

        if new_password != '':
            user_pass = UserPass(user_name, new_password)
            sql_statement = 'update users set password=? where name=?;'
            db.execute(sql_statement, [user_pass.hash_password(), user_name])
            db.commit()
            flash("Password was changed")

        return redirect(url_for('users'))


@app.route('/init_app')
def init_app():
    db = get_db()
    sql_statement = 'select count(*) as cnt from users where is_active and is_admin;'
    cur = db.execute(sql_statement)
    active_admins = cur.fetchone()

    if active_admins != None and active_admins['cnt'] > 0:
        flash("Application is already set-up. Nothing to do")
        return redirect(url_for('index'))

    user_pass = UserPass()
    user_pass.get_random_user_password()
    db.execute('''insert into users(name, email, password,is_active,is_admin)
    values(?,?,?,True,True);''',
               [user_pass.user, 'none@nowhere.no', user_pass.hash_password()])
    db.commit()
    flash('User {} with password {} has been added'.format(user_pass.user, user_pass.password))
    return redirect(url_for('index'))


@app.route('/history')
def history():
    db = get_db()
    sql_command = 'select id, currency, amount, trans_date from transactions;'
    cur = db.execute(sql_command)
    transactions = cur.fetchall()

    return render_template('history.html', active_menu='history', transactions=transactions)


@app.route("/delete_transaction/<int:transaction_id>")
def delete_transaction(transaction_id):
    db = get_db()
    sql_statement = 'delete from transactions where id = ?;'
    db.execute(sql_statement, [transaction_id])
    db.commit()

    return redirect(url_for('history'))


@app.route("/edit_transaction/<int:transaction_id>", methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    offer = CantorOffer()
    offer.load_offer()
    db = get_db()

    if request.method == 'GET':
        sql_statement = 'select id, currency, amount from transactions where id=?;'
        cur = db.execute(sql_statement, [transaction_id])
        transaction = cur.fetchone()

        if transaction == None:
            flash('No such transaction!')
            return redirect(url_for('history'))
        else:
            return render_template('edit_transaction.html', transaction=transaction,
                                   active_menu='history', offer=offer)
    else:

        amount = 100
        if 'amount' in request.form:
            amount = request.form['amount']

        currency = 'EUR'
        if 'currency' in request.form:
            currency = request.form['currency']

        if currency in offer.denied_codes:
            flash(f"The currency {currency} cannot be accepted")
        elif offer.get_by_code(currency) == 'unknown':
            flash(f"The selected currency is unknown and cannot be accepted")
        else:
            sql_command = '''update transactions set
                currency=?,
                amount=?,
                user=?,
                trans_date=?
            where id=?'''
            db.execute(sql_command, [currency, amount, 'admin', date.today(), transaction_id])
            db.commit()
            flash(f"Transaction was updated")

        return redirect(url_for('history'))


def get_db():
    if not hasattr(g, 'sqlite_db'):
        conn = sqlite3.connect(app_info['db_file'])
        conn.row_factory = sqlite3.Row
        g.sqlite_db = conn
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()
        print(error)


@app.route("/")
def index():
    return render_template("index.html", active_menu='home')


@app.route("/exchange", methods=['GET', 'POST'])
def exchange():
    offer = CantorOffer()
    offer.load_offer()

    if request.method == 'GET':
        return render_template('exchange.html', active_menu='exchange', offer=offer)
    else:
        flash("Debug mode in method POST")

        amount = 100
        if 'amount' in request.form:
            amount = request.form['amount']

        currency = 'EUR'
        if 'currency' in request.form:
            currency = request.form['currency']
        if currency in offer.denied_codes:
            flash(f"The currency {currency} cannot be accepted")
        elif offer.get_by_code(currency) == 'unknown':
            flash(f"The selected currency is unknown and cannot be accepted")
        else:
            db = get_db()
            # sql_command = "insert into transactions(currency, amount, user) values('USD', 300, 'admin');"
            sql_command = "insert into transactions(currency, amount, user) values(?, ?, ?);"
            # db.execute(sql_command)
            db.execute(sql_command, [currency, amount, 'admin'])
            db.commit()

            flash(f"Request to change {currency} was accepted")

        return render_template('exchange_results.html', active_menu='exchange',
                               currency=currency, amount=amount,
                               currency_info=offer.get_by_code(currency))


if __name__ == '__main__':
    app.run(debug=True)
