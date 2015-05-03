import json
from django.conf.urls import patterns
from django.contrib import admin
from django import forms
from django.http import HttpResponse
from django.http.response import Http404

from main.models import Article, Tag

JsonResponse = lambda d: HttpResponse(json.dumps(d), content_type="application/json")

def save_article(request, article_id):
  body = request.POST.get('body', None)
  if body:
    try:
      article = Article.objects.get(id=article_id)
      article.body = body
      article.save()
      return JsonResponse({'success': 'Saved!'})
    except Article.DoesNotExist:
      pass
  return JsonResponse({'error': 'Invalid Request'})


def get_admin_urls(urls):
    def get_urls():
        my_urls = patterns('', (r'^main/show_article/(?P<article_id>\d+)/save-show_article/$', admin.site.admin_view(save_article)))
        return my_urls + urls
    return get_urls


class TagAdmin(forms.ModelForm):
  model = Article.tags.through


class RelatedAdminForm(forms.ModelForm):
  class Meta:
    model = Article
    fields = [
      'body',
      'title_image',
      'title',
      'sub_title',
      'slug',
      'pub_date',
      'last_modified',
      'views',
      'should_display_comments',
      'published',
      'tags',
      'generate_related',
      'related'
    ]

  def __init__(self, *args, **kwargs):
    super(RelatedAdminForm, self).__init__(*args, **kwargs)
    if self.instance.id:
      self.fields['related'].queryset = Article.objects.filter(tags__in=self.instance.tags.all()).distinct()


  def clean(self):
    super(RelatedAdminForm, self).clean()

class ArticleForm(forms.ModelForm):
  class Meta:
    model = Article
    fields = '__all__'


class ArticleAdmin(admin.ModelAdmin):
  form = RelatedAdminForm

  def get_readonly_fields(self, request, obj=None):
    return self.readonly_fields + ('views', 'last_modified',)

  def save_related(self, request, form, formsets, change):
    article = form.instance
    generate_related = form.cleaned_data.get('generate_related')
    has_related = form.cleaned_data.get('related')

    if generate_related and (self.tags_changed(article, form) or not has_related):
      article.related = article._build_related_list()
      article.save()

    form.save_m2m()
    for formset in formsets:
        self.save_formset(request, form, formset, change=change)

  def tags_changed(self, instance, form):
    old_tags = list(instance.tags.all())
    new_tags = list(form.cleaned_data.get('tags'))
    return old_tags != new_tags





admin.site.register(Article, ArticleAdmin)
admin.site.register(Tag)
admin_urls = get_admin_urls(admin.site.get_urls())
admin.site.get_urls = admin_urls
