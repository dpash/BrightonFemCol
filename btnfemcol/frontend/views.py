from datetime import datetime

from flask import g, redirect, url_for, abort, render_template, flash, \
    current_app

from btnfemcol.frontend import frontend

from btnfemcol import db, cache

from btnfemcol.models import Article, User, Page, Section, Category, Event

from btnfemcol.frontend.forms import UserRegistrationForm
from btnfemcol.frontend.utils import get, secondary_nav_pages, \
    secondary_nav_categories, q_events_upcoming

from btnfemcol.admin.utils import edit_instance, log_out, logged_in


@frontend.before_request
def before_request():
    key = 'sections'
    sections = cache.get(key)
    if not sections:
        try:
            sections = [{
                'url': s.url,
                'title': s.title,
                'slug': s.slug
            } for s in Section.get_live()]
            cache.set(key, sections, 20)
        except:
            sections = []
            db.session.rollback()
    g.sections = sections
    g.domain_name = current_app.config['DOMAIN_NAME']


# Blitz.io
@frontend.route('/mu-564346ee-4c8fbe62-92480e43-5112ec20')
def blitz():
    return '42'


@frontend.route('/events')
@frontend.route('/events/<string:type>')
@cache.memoize(20)
def show_events(type='upcoming'):
    def inner(type, limit=10):
        q = Event.query.filter_by(status='live')
        if type == 'upcoming':
            q = q_events_upcoming(q)
        else:
            q = q.order_by(Event.start.desc()).filter( \
                Event.start < datetime.utcnow())
        return q[:limit]

    return show_page('events', type, template='event_listing.html',
        events=inner(type))


@frontend.route('/event/<string:slug>')
@cache.memoize(20)
def show_event(slug):
    event = get(Event, slug)
    if not event:
        return abort(404)
    g.canonical_url = event.url
    g.secondary_nav = secondary_nav_pages('events')
    return render_template('event.html',
        page=event,
        selected_section_slug='events',
        selected_secondary_slug='changeme'
    )


@frontend.route('/articles')
@frontend.route('/articles/<string:category_slug>')
@cache.memoize(20)
def show_category(category_slug=None):
    if not category_slug:
        category = Category.query.filter_by(
            status='live').order_by(Category.order.asc()).first()
    else:
        category = get(Category, category_slug)
    if not category:
        return abort(404)

    articles = category.articles.filter_by(status='published').filter( \
                Article.pub_date <= datetime.utcnow()).order_by(
                    Article.pub_date.desc()).all()

    g.canonical_url = category.url
    g.secondary_nav = secondary_nav_categories()
    return render_template('category.html',
        category=category,
        articles=articles,
        selected_section_slug='articles',
        selected_secondary_slug=category_slug
    )


@frontend.route('/articles/<string:category_slug>/<string:article_slug>')
@cache.memoize(60)
def show_article(category_slug, article_slug):
    article = Article.query.filter(
            Article.pub_date <= datetime.now()
        ).filter_by(
            status='published', slug=article_slug
        ).first()
    if not article:
        return abort(404)

    g.secondary_nav = secondary_nav_categories()
    g.canonical_url = article.url
    return render_template('article.html',
        article=article,
        selected_section_slug='articles',
        selected_secondary_slug=category_slug
    )


def post_registration(id, saved, created, form):
    saved.send_activation_email()
    g.secondary_nav = secondary_nav_pages('home')
    return render_template('registered.html', user=saved)


@frontend.route('/register', methods=['GET', 'POST'])
def register():
    if logged_in():
        log_out()
    g.canonical_url = '/registration'
    g.secondary_nav = secondary_nav_pages('home')
    return edit_instance(User, UserRegistrationForm,
        edit_template='registration.html',
        callback=post_registration,
        do_flash=False)


@frontend.route('/activate/<int:user_id>/<string:reg_code>')
def activate(user_id, reg_code):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return abort(404)

    if user.reg_code != reg_code:
        return abort(403)

    if user.status == 'banned':
        return abort(403)

    user.status = 'active'

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.critical(e)
        db.session.rollback()

    flash('Your account has been activated.', 'success')
    return redirect(url_for('frontend.home'))


@frontend.route('/<string:slug>')
@cache.memoize(10)
def show_section(slug):
    section = get(Section, slug)
    if not section:
        return abort(404)
    page = section.pages.filter_by(status='live').first()
    if not page:
        return abort(404)
    else:
        page_slug = page.slug
    return show_page(slug, page_slug)


@frontend.route('/<string:section_slug>/<string:page_slug>')
@cache.memoize(10)
def show_page(section_slug, page_slug, template='page.html',
    **kwargs):

    page = get(Page, page_slug)

    if not page:
        return abort(404)

    g.secondary_nav = secondary_nav_pages(section_slug)
    g.canonical_url = page.url
    return render_template(template,
        page=page,
        selected_section_slug=section_slug,
        selected_secondary_slug=page_slug,
        **kwargs
    )


@frontend.route('/')
@cache.memoize(20)
def home():
    def articles():
        key = 'frontpage:articles'
        fp_arts = cache.get(key)
        if fp_arts:
            arts = []
            for art in fp_arts:
                arts.append(db.session.merge(art))
            fp_arts = arts
        if not fp_arts:
            fp_arts = Article.query.filter_by(
            status='published').filter(
            Article.pub_date <= datetime.now()).order_by(
            Article.pub_date.desc())[:2]
            cache.set(key, fp_arts, 30)
        return fp_arts

    def events():
        key = 'frontpage:events'
        fp_evts = cache.get(key)
        if not fp_evts:
            fp_evts = q_events_upcoming()[:2]
            cache.set(key, fp_evts, 30)
        return fp_evts

    try:
        section_slug = get(Section).slug
    except:
        section_slug = '#'
    try:
        page_slug = get(Page).slug
    except:
        page_slug = '#'

    return show_page(
        section_slug,
        page_slug,
        template='home.html',
        articles=articles(),
        events=events()
    )
