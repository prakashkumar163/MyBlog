import os
import boto
from datetime import datetime
from itertools import chain
from operator import itemgetter

from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from boto.s3.key import Key
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from main import util


class Tag(models.Model):
  name = models.CharField(max_length=30, unique=True)

  def __unicode__(self):
    return self.name


class Article(models.Model):
  title_image = models.CharField(max_length=300, null=True, blank=True)
  thumbnail = models.CharField(max_length=300, null=True)
  slug = models.CharField(max_length=100, blank=True)
  title = models.CharField(max_length=300)
  sub_title = models.CharField(max_length=300, null=True, blank=True)
  body = models.TextField(null=True)
  working_draft = models.TextField(null=True)
  pub_date = models.DateTimeField('date published', null=True, blank=True)
  last_modified = models.DateTimeField('last modified', default=datetime.now())
  views = models.IntegerField(default=0)
  should_display_comments = models.BooleanField(default=True)
  published = models.BooleanField(default=False)
  tags = models.ManyToManyField(Tag, null=True, blank=True)
  related = models.ManyToManyField('self', null=True, blank=True)
  generate_related = models.BooleanField(default=True)

  stale = models.BooleanField(default=False)

  content_out_of_date = False
  __original_instance = None


  class Meta(object):
    ordering = ('last_modified',)

  @classmethod
  def create(cls, title, **kwargs):
    return cls(
      title_image=kwargs.get('title_image', ''),
      thumbnail=kwargs.get('thumbnail', ''),
      title=title,
      sub_title=kwargs.get('sub_title', ''),
      slug=kwargs.get('slug', ''),
      body=kwargs.get('body', ''),
    )

  def __init__(self, *args, **kwargs):
    super(Article, self).__init__(*args, **kwargs)
    self.__original_instance = self.__dict__

  def __unicode__(self):
    return "Article titled: {0}".format(self.title)

  def save(self, *args, **kwargs):
    if self.title_image and not self.thumbnail:
        self.thumbnail = self.create_thumbnail()

    if self.pk:
      instance = Article.objects.get(pk=self.pk)

      if self.title_image_changed(instance):
        self.thumbnail = self.create_thumbnail()

      if self.publishing(instance):
        self.pub_date = datetime.now()

    else:
      if self.published:
        self.pub_date = datetime.now()

    if not self.slug:
      self.slug = self.title.replace(' ', '-')

    self.body = self.strip_padding(self.body)
    self.stale = True
    Article.content_out_of_date = True

    super(Article, self).save()

  def _build_related_list(self):
    tags = set(self.tags.all())
    semi_related = Article.objects.filter(tags__in=self.tags.all()).exclude(id=self.id).distinct()
    with_match_level = [(self.count_similar_tags(article, tags), article) for article in semi_related]
    closest_related = sorted(with_match_level, key=itemgetter(0), reverse=True)
    return [article for (rating, article) in closest_related[:3]]


  def count_similar_tags(self, article, tags):
    return len(set(article.tags.all()).intersection(tags))


  def create_thumbnail(self):
    thumbnail = util.create_thumbnail(self.title_image)
    thumbnail_name = self.generate_thumbnail_filename(self.title_image)

    s3 = boto.connect_s3(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    k = Key(s3.get_bucket(settings.AWS_STORAGE_BUCKET_NAME, validate=False))

    k.content_type='image/jpeg'
    k.key = thumbnail_name

    headers = {
      'Cache-Control': 'max-age=31556926',
    }
    k.set_contents_from_file(thumbnail, policy='public-read', reduced_redundancy=True)

    thumbnail_url = k.generate_url(expires_in=0, query_auth=False)
    return thumbnail_url

  def strip_padding(self, body):
    if body:
      padded_line = '<p>&nbsp;</p>'
      return '\n'.join(line for line in body.split('\n') if padded_line not in line)
    return ''

  def generate_thumbnail_filename(self, source_url):
    filename, ext = os.path.splitext(os.path.split(source_url)[-1])
    return 'main/images/{0}-thumb{1}'.format(filename, ext)

  def title_image_changed(self, instance):
    return instance.title_image != self.title_image

  def publishing(self, instance):
    not_previously_published = instance.published == False
    # if we're checking the published box to ON
    return not_previously_published and self.published



class CommentManager(models.Manager):
  def get_queryset(self):
    return self.model.MyQuerySet(self.model)


class Node(object):
  def __init__(self, comment):
    self.comment = comment
    self.id = comment.id
    self.pid = comment.parent.id if comment.parent else None
    self.children = []

    def __str__(self):
      return self.comment.author

    def __repr__(self):
      return self.__str__()


class Comment(models.Model):
  article = models.ForeignKey('Article', related_name='comments')
  parent = models.ForeignKey('Comment', null=True, blank=True)
  author = models.CharField(max_length=50)
  body = models.TextField()
  post_date = models.DateField(default=datetime.now())
  deleted = models.BooleanField(default=False)
  admin_comment = models.BooleanField(default=False)
  objects = CommentManager()

  def __unicode__(self):
    return "Comment by: {0}".format(self.author)

  def __repr__(self):
    return self.__unicode__()



  @classmethod
  def create(cls, article, parent, author, body):
    return cls(
      article=article,
      parent=parent,
      author=author,
      body=body,
    )

  class MyQuerySet(QuerySet):

    def as_tree(self):
      if not self.exists():
        return iter([])
      comment_nodes = [Node(comment) for comment in self]
      lookup_table = {node.id: node for node in comment_nodes}

      # populate children
      for node in comment_nodes:
        current = node
        try:
          lookup_table[current.pid].children.append(current)
        except:
          pass

      fake_root_comment = Comment(article=comment_nodes[0].comment.article, parent_id=None, author="", body="")
      root_id = 9999294999
      root_node = Node(fake_root_comment)
      for node in comment_nodes:
        if not node.pid:
          root_node.children.append(node)

      return self.build_tree(root_node, 0)

    def build_tree(self, node, depth):
      if not node.children:
        yield (depth, node.comment,)
      else:
        output = [(depth, node.comment,)]
        for n in node.children:
          output = chain(output, self.build_tree(n, depth + 1))
        for result in output:
          yield result


def model_builder():
  Article.objects.create(
    title="How I use Python for Windows Automation",
    sub_title="or how to make Adobe Premiere less painful",
    thumbnail="https://awsblogstore.s3.amazonaws.com/main/images/Untitled-1%2520copy-thumb.jpg",
    title_image="https://awsblogstore.s3.amazonaws.com/main/images/Untitled-1%20copy.jpg",
    body="A bit of preface: I currently work in a small shop that provides recording services for conferences. The needs of a talking head at a podium are pretty basic from an editing stand point, so the way I organize my Premiere projects has adapted accordingly. After a bunch of iterations, I ended up with a folder hierarchy that is almost completely flat. Namely, one audio folder, one video folder, and then individual sequences for each talk.",
    slug="How-I-Use-Python-for-Windows-Automation",
    views=10,
    should_display_comments = True,
    published = True
  )

  Article.objects.create(
    title="Parallelism in one line",
    sub_title="A Better Model for Day to Day Threading Tasks",
    thumbnail="https://awsblogstore.s3.amazonaws.com/main/images/parallel-thumb.jpg",
    title_image="https://awsblogstore.s3.amazonaws.com/main/images/parallel.jpg",
    body="lorem ipsum loren impsum.",
    slug="parallelism-in-one-line/",
    views=20,
    shouldDisplayComments = True,
    published = True
  )

  Article.objects.create(
    title="The Great White Space Debate",
    sub_title="lorem ipsum loren impsum.",
    thumbnail="https://awsblogstore.s3.amazonaws.com/main/images/whitespace2-thumb.jpg",
    title_image="https://awsblogstore.s3.amazonaws.com/main/images/whitespace2.jpg",
    body="lorem ipsum loren impsum.",
    slug="How-I-Use-Python-for-Windows-Automation",
    views=5,
    should_display_comments = True,
    published = True
  )

  Article.objects.create(
    title="Cleaner Code Through Partial Function Application",
    sub_title="",
    thumbnail="https://awsblogstore.s3.amazonaws.com/main/images/hahahahaha-thumb.jpg",
    title_image="https://awsblogstore.s3.amazonaws.com/main/images/hahahahaha.jpg",
    body="lorem ipsum loren impsum.",
    slug="Cleaner-coding-through-partially-applied-functions",
    views=50,
    should_display_comments = True,
    published = True
  )


@receiver(post_save, sender=Comment)
def comment_post_save(sender, instance, *args, **kwargs):
  # mark the article for updates
  article = instance.article
  article.stale = True
  Article.content_out_of_date = True
  article.save()







