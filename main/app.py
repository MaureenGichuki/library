from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import datetime
from flask_migrate import Migrate, migrate
from datetime import date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    fee = db.Column(db.Integer, nullable=False)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20))
    outstanding_debt = db.Column(db.Float, nullable=False, default=0.0)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    date_issued = db.Column(db.Date, nullable=False, default=datetime.date.today)
    date_returned = db.Column(db.Date, default=None)
    rent_fee = db.Column(db.Float, default=0.0)
    days = db.Column(db.Integer)  # Add the 'days' field
    
    book = db.relationship('Book', backref='transactions')
    member = db.relationship('Member', backref='transactions')


@app.route('/')
def home():
    books = Book.query.all()
    members = Member.query.all()
    transactions = Transaction.query.filter_by(date_returned=None).all()
    return render_template('index.html', books=books, members=members, transactions=transactions, member_debt=member_debt)

@app.route('/books')
def books():
    books = Book.query.all()
    return render_template('books.html', books=books)

@app.route('/members')
def members():
    members = Member.query.all()
    return render_template('members.html', members=members)


@app.route('/add_book', methods=['POST', 'GET'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        stock = int(request.form['stock'])
        fee = int(request.form['fee'])
        book = Book(title=title, author=author, stock=stock, fee=fee)
        db.session.add(book)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_book.html')


@app.route('/add_member', methods=['POST', 'GET'])
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        member = Member(name=name, email=email, phone=phone)
        db.session.add(member)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add_member.html')

@app.route('/delete_book/<int:book_id>', methods=['POST', 'GET'])
def delete_book(book_id):
    book = Book.query.get(book_id)
    if book:
        # Set book_id to NULL for all related transactions
        Transaction.query.filter_by(book_id=book.id).update({"book_id": None})
        db.session.delete(book)
        db.session.commit()
    return redirect(url_for('books'))


@app.route('/delete_member/<int:member_id>', methods=['POST', 'GET'])
def delete_member(member_id):
    member = Member.query.get(member_id)
    if member:
        db.session.delete(member)
        db.session.commit()
    return redirect(url_for('home'))


@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    if request.method == 'POST':
        book_id = int(request.form['book_id'])
        member_id = int(request.form['member_id'])
        days = int(request.form['days'])

        book = Book.query.get(book_id)
        member = Member.query.get(member_id)

        if book.stock > 0 and member.outstanding_debt <= 500:
            book.stock -= 1

            transaction = Transaction(
                book_id=book_id,
                member_id=member_id,
                date_issued=datetime.date.today(),
                days=days
            )

            db.session.add(transaction)
            db.session.commit()

        return redirect(url_for('home'))
    else:
        books = Book.query.all()
        members = Member.query.all()
        return render_template('issue_book.html', books=books, members=members)



def member_debt(member, date_issued):
    total_days = (date.today() - date_issued).days
    transactions = Transaction.query.filter_by(member_id=member.id, date_returned=None).all()
    debt = 0.0
    for transaction in transactions:
        book = transaction.book
        fee_per_day = book.fee
        debt += fee_per_day * total_days
    return debt


@app.route('/return_book', methods=['POST'])
def return_book():
    transaction_id = int(request.form['transaction_id'])
    transaction = Transaction.query.get(transaction_id)
    if transaction.date_returned is None:
        transaction.date_returned = datetime.date.today()
        book = Book.query.get(transaction.book_id)
        book.stock += 1
        member = Member.query.get(transaction.member_id)
        days_rented = (transaction.date_returned - transaction.date_issued).days
        rent_fee = book.fee * days_rented
        member.outstanding_debt += rent_fee
        transaction.rent_fee = rent_fee
        db.session.commit()
    return redirect(url_for('home'))


def calculate_rent_fee(date_issued, date_returned, book_fee):
    days_rented = (date_returned - date_issued).days
    return days_rented * book_fee


@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    book = Book.query.get(book_id)
    if book:
        if request.method == 'POST':
            book.title = request.form['title']
            book.author = request.form['author']
            book.stock = int(request.form['stock'])
            book.fee = int(request.form['fee'])
            db.session.commit()
            return redirect(url_for('home'))
        return render_template('edit_book.html', book=book)
    return redirect(url_for('home'))


@app.route('/edit_member/<int:member_id>', methods=['POST', 'GET'])
def edit_member(member_id):
    member = Member.query.get(member_id)
    if member:
        if request.method == 'POST':
            member.name = request.form['name']
            member.email = request.form['email']
            member.phone = request.form['phone']
            db.session.commit()
            return redirect(url_for('home'))
        return render_template('edit_member.html', member=member)
    return redirect(url_for('members')) 



@app.route('/search', methods=['POST', 'GET'])
def search():
    keyword = request.form['keyword']
    books = Book.query.filter((Book.title.contains(keyword)) | (Book.author.contains(keyword))).all()
    return render_template('search.html', books=books)

if __name__ == '__main__':
     with app.app_context():
        db.create_all()
        app.run(debug=True)
