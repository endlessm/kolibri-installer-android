import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from jnius import autoclass
from kolibri.core.content.models import ContentNode
from kolibri.core.logger.models import ContentSummaryLog
from kolibri_android.android_utils import get_activity

# from kolibri.core.logger.models import ContentSessionLog

logger = logging.getLogger(__name__)

Bundle = autoclass("android.os.Bundle")
Event = autoclass("com.google.firebase.analytics.FirebaseAnalytics$Event")
FirebaseAnalytics = autoclass("com.google.firebase.analytics.FirebaseAnalytics")
Param = autoclass("com.google.firebase.analytics.FirebaseAnalytics$Param")


def send_content_event(channel_id, content_id, node_id, kind):
    items = []
    channel = Bundle()
    channel.putString(Param.ITEM_ID, channel_id)
    channel.putString(Param.ITEM_CATEGORY, "channel")
    items.append(channel)
    content = Bundle()
    content.putString(Param.ITEM_ID, content_id)
    content.putString(Param.ITEM_CATEGORY, "content")
    content.putString(Param.ITEM_CATEGORY2, kind)
    items.append(content)
    if node_id:
        node = Bundle()
        node.putString(Param.ITEM_ID, node_id)
        node.putString(Param.ITEM_CATEGORY, "node")
        node.putString(Param.ITEM_CATEGORY2, kind)
        items.append(node)
    params = Bundle()
    params.putParcelableArray(Param.ITEMS, items)

    context = get_activity()
    analytics = FirebaseAnalytics.getInstance(context)
    logger.info(
        "Logging event channel=%s content=%s kind=%s node=%s",
        channel_id,
        content_id,
        kind,
        node_id,
    )
    analytics.logEvent(Event.VIEW_ITEM, params)


# @receiver(post_save, sender=ContentSessionLog)
# def session_log_updated(sender, instance, created, **kwargs):
#     node_id = instance.extra_fields.get("context", {}).get("node_id")
#     logger.debug(
#         "channel_id=%s content_id=%s node_id=%s kind=%s %s progress=%f %s",
#         instance.channel_id,
#         instance.content_id,
#         node_id,
#         instance.kind,
#         instance.extra_fields,
#         instance.progress,
#         "created" if created else "updated",
#     )


@receiver(post_save, sender=ContentSummaryLog)
def summary_log_updated(sender, instance, **kwargs):
    node = ContentNode.objects.filter(
        channel_id=instance.channel_id, content_id=instance.content_id
    ).first()
    node_id = node.id if node else None
    logger.debug(
        "summary channel_id=%s content_id=%s node_id=%s kind=%s %s time_spent=%f progress=%f",
        instance.channel_id,
        instance.content_id,
        node_id,
        instance.kind,
        instance.extra_fields,
        instance.time_spent,
        instance.progress,
    )

    send_content_event(instance.channel_id, instance.content_id, node_id, instance.kind)
