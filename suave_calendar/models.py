import datetime

from django.db import models
from django.core.urlresolvers import reverse_lazy as reverse

from model_utils.managers import PassThroughManager
from suave.models import Displayable, Ordered, Image, SiteEntityQuerySet



class EventQuerySet(SiteEntityQuerySet):

    def future(self):
        return self.live().filter(start_date__gte=datetime.date.today())

    def past(self):
        return self.live().filter(end_date__lte=datetime.date.today())


class Event(Displayable):
    start_date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)

    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    price = models.DecimalField(max_digits=5, decimal_places=2,
        null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    
    dark_bg = models.BooleanField()
    header_image = models.BooleanField()

    objects = PassThroughManager.for_queryset_class(EventQuerySet)()

    @property
    def url(self):
        return self.get_absolute_url()

    def get_absolute_url(self):
        s = '{:02n}'
        return reverse('suave_calendar:event', kwargs={
            'slug': self.slug,
            'year': self.start_date.year,
            'month': self.start_date.strftime('%B').lower(),
            'day': s.format(self.start_date.day)
        })

    @property
    def image(self):
        try:
            return self.images.all()[0]
        except IndexError:
            return None


class EventLink(Ordered):
    url = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    information = models.TextField(null=True, blank=True)
    event = models.ForeignKey(Event, related_name='links')


class EventImage(Image):
    event = models.ForeignKey(Event, related_name='images')
    gallery = models.BooleanField(default=True)