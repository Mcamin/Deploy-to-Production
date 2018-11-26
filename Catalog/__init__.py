#!/usr/bin/env python3
# Server Code


from flask import Flask, render_template, request, redirect
from sqlalchemy import create_engine, asc
from flask import url_for, jsonify, flash
from sqlalchemy.orm import sessionmaker, scoped_session
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
from Config import Base, Product, Category, User
import requests
import os 


app = Flask(__name__)

#Fix loading files from  FlaskApps instrad of current Directory 
os.chdir("/var/www/FlaskApps/Catalog")

"""Read the clients_secrets.json file and ger the client id"""
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"

engine = create_engine('sqlite:///Shop.db')
Base.metadata.bind = engine

session = scoped_session(sessionmaker(bind=engine, expire_on_commit=True))

# Fix Reload Errors


@app.teardown_request
def remove_session(ex=None):
    session.remove()


# Display The Diffrent Categories

@app.route('/')
def category_show():
    session.expire_all()
    items = session.query(Category).all()
    return render_template('home.html', items=items)


# Login page
@app.route('/login')
def showLogin():
    """Create Anti forgery state token"""
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template("login.html", STATE=state)

# Facebook Connect


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print("access token received %s " % access_token)

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = "https://graph.facebook.com/oauth/access_token?grant_type=" \
          "fb_exchange_token&client_id=%s&client_secret=%s" \
          "&fb_exchange_token=%s"\
          % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v3.2/me"
    '''
        Due to the formatting for the result from the server token exchange
        we have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then
        we split it on colons to pull out the actual token value and replace
        the remaining quotes with nothing so that it can be used directly in
        the graph api calls
    '''
    print(result)
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = "https://graph.facebook.com/v2.8/me?" \
          "access_token=%s&fields=name,id,email" % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = "https://graph.facebook.com/v2.8/me/picture?" \
          "access_token=%s&redirect=0&height=200&width=200" % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = width: 150px; height: 150px;border-radius: 75px;'\
              '-webkit-border-radius: 75px;-moz-border-radius: 75px;">'

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"

# Google Connect


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Currentuser is already '
                                            'connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    login_session['provider'] = 'google'

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 150px; height: 150px;border-radius: 75px;'\
              '-webkit-border-radius: 75px;-moz-border-radius: 75px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print("done!")
    return output

# google disconnect


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    print('In gdisconnect access token is %s', access_token)
    print('User name is: ')
    print(login_session['username'])
    if access_token is None:
        print('Access Token is None')
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/' \
          'revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result)
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# Categories dashboard
    """Check if the user is logged in and load the categories from the DB and
       display them in the table where the user can edit/delete and add
       categories"""


@app.route('/categories')
def categories_dashboard():
    if 'username' not in login_session:
        return redirect('/login')
    session.expire_all()
    items = session.query(Category).all()
    return render_template('categories_dashboard.html', items=items)


# Add Category
    """Check if the user is logged in and Display the add Form /
       Add the new category to the Database by handling the
       post request"""


@app.route('/categories/new', methods=['GET', 'POST'])
def categories_new():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        UserTest = session.query(User).filter_by(
            email=login_session['email']).one()
        newItem = Category(name=request.form['name'], user_id=UserTest.id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('categories_dashboard'))
    else:
        return render_template('Add_category.html')


# Edit Category
"""Check if the user is logged in and is the creator of the category and
   Display the edit Form / Edit the new category in the Database by
   handling the post request"""


@app.route('/categories/<int:category_id>/edit',
           methods=['GET', 'POST'])
def categories_edit(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Category).filter_by(id=category_id).one()
    UserTest = session.query(User).filter_by(id=editedItem.user_id).one()
    if UserTest.email != login_session['email']:
        return "<script>function myFunction() {alert('You are not authorized "\
               "to edit this category. Please create your own category.');"\
               "history.go(-1);}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('categories_dashboard'))
    else:
        return render_template('Edit_Category.html', category_id=category_id,
                               item=editedItem)

# Delete Category
    """Check if the user is logged in and is the creator of the category and
       Display the delete Form / delete the selected category from the Database
       by handling the post request"""


@app.route('/categories/<int:category_id>/delete',
           methods=['GET', 'POST'])
def categories_delete(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Category).filter_by(id=category_id).one()
    Productstodelete = session.query(
        Product).filter_by(category_id=itemToDelete.id)
    UserTest = session.query(User).filter_by(id=itemToDelete.user_id).one()
    if UserTest.email != login_session['email']:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to delete this category.');history.go(-1);}</script>" \
               "<body onload='myFunction()'>"
    if request.method == 'POST':
        for i in Productstodelete:
            session.delete(i)
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('categories_dashboard'))
    else:
        return render_template('Delete_Category.html', category_id=category_id,
                               item=itemToDelete)


# Category products
"""Display all the products within the selected category and add a brand Filter
    by loading the distinct brands in the products table that
    matched with the category id"""


@app.route('/<int:category_id>/products')
def categoryProducts(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Product).filter_by(category_id=category_id)
    brands = session.query(Product.brand).filter_by(
        category_id=category_id).distinct()
    return render_template(
        'products.html', category=category, items=items,
        category_id=category_id,
        brands=brands)

# Category Prodcuts Dashboard
    """Check if the user is logged in and display all the products within the
      selected category in the dashboard, add a brand Filter by loading the
      distinct brands in the products table that matched with the category
      itself. The user is able here to create, modify and delete products
      within the category"""


@app.route('/categories/<int:category_id>/products')
def categoryProducts_dashboard(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Product).filter_by(category_id=category_id)
    brands = session.query(Product.brand).filter_by(
        category_id=category_id).distinct()
    return render_template(
        'Products_Dashboard.html', category=category, items=items,
        category_id=category_id, brands=brands)

# Delete Prodcut from Category
    """Check if the user is logged in and is the creator of the product and
       Display the delete Form / delete the selected product from the Database
       by handling the post request"""


@app.route('/categories/<int:category_id>/products/'
           '<int:productItem_id>/delete',
           methods=['GET', 'POST'])
def productItem_delete(category_id, productItem_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Product).filter_by(id=productItem_id).one()
    UserTest = session.query(User).filter_by(id=itemToDelete.user_id).one()
    if UserTest.email != login_session['email']:
        return "<script>function myFunction() {alert('You are not authorized" \
               "to delete the products in this category.');" \
               "history.go(-1);}" \
               "</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('categoryProducts_dashboard',
                                category_id=category_id))
    else:
        return render_template('Delete_Product.html',
                               category_id=category_id, item=itemToDelete)

# Add Product to Category
    """Check if the user is logged in and is the creator of the category
       he is trying to add product in and  display the add Form /
       Add the new Product to the Database by handling the
       post request"""


@app.route('/categories/<int:category_id>/products/add',
           methods=['GET', 'POST'])
def productItem_add(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    UserTest = session.query(User).filter_by(id=category.user_id).one()
    if UserTest.email != login_session['email']:
        return "<script>function myFunction() {alert('You are not authorized" \
               " to add products to this category. " \
               "Please create your own category " \
               "in order to add items.');history.go(-1);}</script>"\
               "<body onload='myFunction()'>"
    if request.method == 'POST':
        newItem = Product(name=request.form['name'], description=request.form[
            'description'], price=request.form['price'],
            brand=request.form['brand'],
            category_id=category_id, user_id=UserTest.id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('categoryProducts_dashboard',
                                category_id=category_id))
    else:
        return render_template('Add_Product.html',
                               category_id=category_id)


# Edit Prodcut to Category
"""Check if the user is logged in and is the creator of the product and
   Display the edit Form / Edit the new product in the Database by
   handling the post request"""


@app.route('/categories/<int:category_id>/products/<int:product_id>/edit',
           methods=['GET', 'POST'])
def productItem_edit(category_id, product_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Product).filter_by(id=product_id).one()
    UserTest = session.query(User).filter_by(id=editedItem.user_id).one()
    if UserTest.email != login_session['email']:
        return "<script>function myFunction() {alert('You are not authorized"\
               " to edit prodcut items to this category. " \
               "Please create your own "\
               "category in order to edit items.');history.go(-1);}"\
               "</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['brand']:
            editedItem.brand = request.form['brand']
        session.add(editedItem)
        session.commit()
        return redirect(url_for('categoryProducts_dashboard',
                                category_id=category_id))
    else:
        return render_template(
            'Edit_Product.html', category_id=category_id,
            product_id=product_id, item=editedItem)

# Category Products JSON


@app.route('/categories/<int:category_id>/products/JSON')
def categoryProductsJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Product).filter_by(
        category_id=category_id).all()
    return jsonify(Products=[i.serialize for i in items])


# Product JSON
@app.route('/products/<int:product_id>/JSON')
def productItemJSON(product_id):
    productItem = session.query(Product).filter_by(id=product_id).one()
    return jsonify(Product=productItem.serialize)

# Category JSON


@app.route('/categories/<int:category_id>/JSON')
def CategoryJSON(category_id):
    res = session.query(Category).filter_by(id=category_id).one()
    return jsonify(Category=res.serialize)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
#            del login_session['gplus_id']
#            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
            del login_session['username']
            del login_session['email']
            del login_session['picture']
            del login_session['user_id']
            del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('category_show'))
    else:
        flash("You were not logged in")
        return redirect(url_for('category_show'))


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


if __name__ == '__main__':
    app.debug = True   
    app.secret_key = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
    app.run(host='0.0.0.0', port=8080)

