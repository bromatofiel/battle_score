import logging
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.utils import enum

logger = logging.getLogger()


class BaseModel(models.Model):
    class Meta:
        abstract = True

    date_created = models.DateTimeField("Creation Date", auto_now_add=True, db_index=True)
    date_updated = models.DateTimeField("Update Date", auto_now=True, db_index=True)


class CommandRun(BaseModel):
    STATUSES = enum(
        CREATED="Créée",
        SUCCESS="Terminée",
        FAILED="Echec",
        RUNNING="En cours",
    )

    date_end = models.DateTimeField(null=True, blank=True)
    date_start = models.DateTimeField(null=True, blank=True)
    env = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=dict, blank=True)
    keep_it = models.BooleanField(default=False)
    name = models.CharField(max_length=64)
    stats = models.JSONField(default=dict, blank=True)
    status = models.CharField(help_text=_("Etat de la commande"), max_length=20, choices=STATUSES, default=STATUSES.CREATED)
    request_id = models.CharField(help_text=_("Id used in logs"), max_length=36, blank=True, default=uuid.uuid4, editable=False)

    @property
    def duration(self):
        if None in (self.date_end, self.date_start):
            return None
        return self.date_end - self.date_start
