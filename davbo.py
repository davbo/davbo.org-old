import json, markdown

from datetime import datetime
from flask import Flask, request, url_for, render_template, jsonify
from flaskext.sqlalchemy import SQLAlchemy
from utils import slugify, requires_auth
from werkzeug.contrib.atom import AtomFeed


app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/davbo.db',
    SQLALCHEMY_ECHO = False,
    DEBUG = True,
    SECRET_KEY = 'dfghgq8$#3443jkT#$TsgdlsLSDvsdv',
)
db = SQLAlchemy(app)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column('post_id', db.Integer, primary_key=True)
    title = db.Column(db.String(120))
    slug = db.Column(db.String(120))
    text = db.Column(db.Text)
    pub_date = db.Column(db.DateTime)

    def __init__(self, title, text):
        self.title = title
        self.text = text
        self.slug = slugify(title)
        self.done = False
        self.pub_date = datetime.utcnow()


@app.route('/')
def blog():
    return render_template('blog.html',
        posts=Post.query.order_by(Post.pub_date.desc()).all()
    )

@requires_auth
@app.route('/api/make_post', methods=['POST'])
def make_post():
    post = json.loads(request.form['post'])
    response = dict()
    try:
        existing_post = Post.query.filter(Post.title == post['title']).one()
        if 'confirm' in request.form:
            existing_post.text = repr(post['text'])
            db.session.add(existing_post)
            db.session.commit()
            response['success'] = url_for('show_post', slug=existing_post.slug)
        else: response['error'] = "post exists"
    except Exception as e:
        print e
        new_post = Post(title=post['title'], text=repr(post['text']))
        db.session.add(new_post)
        db.session.commit()
        response['success'] = url_for('show_post', slug=new_post.slug)
    return jsonify(response)

@app.route('/api/get_titles')
def get_titles():
    posts=Post.query.order_by(Post.pub_date.desc()).all()
    titles = dict()
    for post in posts:
        titles[post.title] = post.slug
    return jsonify(titles)

@app.route('/api/get_post/<slug>')
def get_post(slug):
    post = Post.query.filter(Post.slug == slug).one()
    return post.text

@app.route('/api/delete_post/<slug>')
def delete_post(slug):
    try:
        post = Post.query.filter(Post.slug == slug).one()
        db.session.delete(post)
        db.session.commit()
        return "true"
    except:
        return "false"

@app.route('/p/<slug>')
def show_post(slug):
    return render_template('show_post.html',
        post=Post.query.filter(Post.slug == slug).one()
    )

@app.template_filter('markdown')
def format_post(post):
    """
    Posts are stored as pickled list of strings
    formatted in markdown. Bit of a cludge but hey
    nobody is perfect :)
    """
    post = eval(post)
    article = markdown.markdown(post)
    return article

@app.route('/recent.atom')
def recent_feed():
    feed = AtomFeed('Recent Articles',
                    feed_url=request.url, url=request.url_root)
    articles = Post.query.order_by(Post.pub_date.desc()) \
                      .limit(15).all()
    for article in articles:
        feed.add(article.title, unicode(format_post(article.text)),
                 content_type='html',
                 url=url_for('show_post', slug=article.slug),
                 author='Dave King',
                 updated=article.pub_date,
                 published=article.pub_date)
    return feed.get_response()

if __name__ == '__main__':
    app.run()
