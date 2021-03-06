from django.conf.urls.defaults import *

urlpatterns = patterns('',
  url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<object_id>\d+)/$',
    view    = 'basic.bookmarks.views.bookmark_detail',
    name    = 'bookmark_detail',
  ),
  url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 
    view    = 'basic.bookmarks.views.bookmark_archive_day',
    name    = 'bookmark_archive_day',
  ),
  url(r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$',
    view    = 'basic.bookmarks.views.bookmark_archive_month',
    name    = 'bookmark_archive_month',
  ),
  url(r'^(?P<year>\d{4})/$',
    view    = 'basic.bookmarks.views.bookmark_archive_year',
    name    = 'bookmark_archive_year',
  ),
  url(r'^$',
    view    = 'basic.bookmarks.views.bookmark_index',
    name    = 'bookmark_index',
  ),
)