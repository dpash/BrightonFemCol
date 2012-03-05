import inspect
import json

from flask import Blueprint, request, session, g, redirect, url_for, abort, \
     render_template, flash, current_app

from flaskext.uploads import (UploadSet, configure_uploads, IMAGES,
                              UploadNotAllowed)

import btnfemcol

from btnfemcol.admin import admin

from btnfemcol import uploaded_images, uploaded_avatars
from btnfemcol import db
from btnfemcol import cache

from btnfemcol.models import User, Article, Page, Event, Section, Category, \
    Group
from btnfemcol.admin.forms import UserEditForm, UserRegistrationForm, \
    ArticleEditForm, LoginForm, PageEditForm, EventEditForm

from btnfemcol.utils import Auth, AuthError

from btnfemcol.admin.utils import auth_logged_in, auth_allowed_to, section, \
    edit_instance, save_instance, calc_pages, json_inner

# Article Views
@admin.route('/articles')
@auth_logged_in
@auth_allowed_to('write_articles')
@section('articles')
def list_articles():
    return render_template('articles.html')


@admin.route('/article/<int:id>', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('write_articles')
@section('articles')
def edit_article(id=None):
    if id:
        article = Article.query.filter_by(id=id).first()
        if not article:
            return abort(404)
        submit = 'Update'

        if g.user != article.author and not g.user.allowed_to('manage_articles'):
            return abort(403)
    else:
        article = Article()
        submit = 'Create'
    
    form = ArticleEditForm(request.form, article)

    if not g.user.allowed_to('change_authors'):
        if article.id:
            form.author_id.data = article.author.id
        else:
            form.author_id.data = g.user.id
    
    created = save_instance(form, article)
    if created:
        return redirect(url_for('admin.edit_article', id=created))
    return render_template('edit_article.html', form=form, submit=submit)

@admin.route('/article/new', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('write_articles')
def create_article():
    return edit_article()

@admin.route('/async/user_articles')
@admin.route('/async/user_articles/<string:username>')
@auth_logged_in
@auth_allowed_to('write_articles')
@section('articles')
def json_user_articles(username=None, *args, **kwargs):
    if username:
        user = User.query.filter_by(username=username).first()
        if not user:
            return abort(404)
    else:
        user = g.user
    
    if g.user != user and not g.user.allowed_to('manage_articles'):
        return abort(403)

    return json_inner(user.articles)


@admin.route('/async/articles')
@auth_logged_in
@auth_allowed_to('manage_articles')
@section('articles')
def json_articles():
    return json_inner(Article.query)


# Page Views
@admin.route('/pages')
@auth_logged_in
@auth_allowed_to('manage_pages')
@section('pages')
def list_pages():
    return render_template('pages.html')

@admin.route('/page/<int:id>', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('manage_pages')
@section('pages')
def edit_page(id=None):
    return edit_instance(Page, PageEditForm, 'edit_page.html', id)


@admin.route('/async/pages')
@auth_logged_in
@auth_allowed_to('manage_pages')
@section('pages')
def json_pages():
    return json_inner(Page.query,
        order=[Page.section_id.asc(), Page.order.asc()])


@admin.route('/page/new', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('manage_pages')
def create_page():
    return edit_page()


# Event Views
@admin.route('/events')
@auth_logged_in
@auth_allowed_to('manage_events')
@section('events')
def list_events():
    return render_template('events.html')

@admin.route('/event/<int:id>', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('manage_events')
@section('event')
def edit_event(id=None):
    return edit_instance(Event, EventEditForm, id=id)


@admin.route('/async/events')
@auth_logged_in
@auth_allowed_to('manage_events')
@section('events')
def json_events():
    return json_inner(Event.query, order=[Event.start.desc()])


@admin.route('/event/new', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('manage_events')
def create_event():
    return edit_event()



# User Views
@admin.route('/users')
@auth_logged_in
@auth_allowed_to('manage_users')
@section('users')
def list_users():
    return render_template('users.html')

@admin.route('/user/new', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('manage_users')
@section('users')
def create_user():
    return edit_user()

@admin.route('/user/<int:id>', methods=['GET', 'POST'])
@auth_logged_in
@auth_allowed_to('manage_users')
@section('users')
def edit_user(id=None):
    group = Group.query.filter_by(name='Writer').first()
    default = User(group)
    return edit_instance(User, UserEditForm, id=id, default=default)


@admin.route('/async/users')
@auth_logged_in
@auth_allowed_to('manage_users')
@section('users')
def json_users():
    return json_inner(User.query)



# Dashboards
@section('articles')
@auth_allowed_to('write_articles')
def dashboard_writer():
    """This is the dashboard for the writer group type, it just returns the
    article list because that's all writers really need to do.
    """
    return list_articles()

@admin.route('/editor')
@section('editor')
@auth_allowed_to('manage_articles')
def dashboard_editor():
    """Editor dashboard has things for proof-reading and accepting submitted
    articles, and also writing one's own."""
    return render_template('dashboard_editor.html')

@section('pages')
@auth_allowed_to('manage_pages')
def dashboard_administrator():
    """Administrator dashboard will cover page editing, event uploading, user
    management."""
    return render_template('dashboard_administrator.html')

@section('users')
@auth_allowed_to('manage_site')
def dashboard_superuser():
    """Superuser can anything an admin can, but with the ability to change site
    settings, manage permissions, etc."""
    return render_template('dashboard_superuser.html')


# Generic Views
@admin.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        a = Auth(session, db, User)
        try:
            g.user = a.log_in(form.username.data, form.password.data)
            session['logged_in'] = g.user.id
            flash("Successfully logged in.", 'success')
            return redirect(url_for('admin.home'))
        except AuthError:
            flash('Invalid username or password.', 'error')
    return render_template('login.html', form=form, submit='Login')


@admin.route('/logout')
def logout():
    g.user = None
    del session['logged_in']
    flash('Logged out.')
    return redirect(url_for('admin.login'))


@admin.route('/')
@auth_logged_in
def home():
    # Do some logic to get the right dashboard for the person
    if g.user.group.name == 'Writer':
        return dashboard_writer()
    if g.user.group.name == 'Editor':
        return dashboard_editor()
    if g.user.group.name == 'Moderator':
        return dashboard_moderator()
    if g.user.group.name == 'Administrator' \
        or g.user.group.name == 'Super User':
        return dashboard_administrator()
    else:
        return g.user.group.name