import datetime
import geojson
import json
import logging
import os
from slacker import Slacker

logger = logging.getLogger(__name__)


def cleanup_datetime(d):
    """Represent timestamps as strings, not datetime.date objects."""
    return {
        k: cleanup_datetime(v) if isinstance(v, dict)
        else str(v) if isinstance(v, datetime.date) else v
        for k, v in d.items()
    }


def announce_on_slack(config=None, process_area=None):
    if config['mapchete_config'].get("mhub_announce_on_slack", False):
        logger.info("announce on slack")
        Slacker(
            "",
            incoming_webhook_url=os.environ["SLACK_WEBHOOK_URL"]
        ).incomingwebhook.post(
            {
                "username": "Mapchete",
                "icon_url": "https://a2.memecaptain.com/src_thumbs/24132.jpg",
                "channel": "#mapchete_hub",
                "text": "%s#zoom=8&lon=%s&lat=%s" % (
                    os.environ.get("PREVIEW_PERMALINK"),
                    process_area.centroid.y,
                    process_area.centroid.x
                )
            }
        )


def format_as_geojson(inp, indent=4):
    space = " " * indent
    out_gj = (
        '{\n'
        '%s"type": "FeatureCollection",\n'
        '%s"features": [\n'
    ) % (space, space)
    features = (i for i in ([inp] if isinstance(inp, dict) else inp))
    try:
        feature = next(features)
        level = 2
        while True:
            feature_gj = (space * level).join(
                json.dumps(
                    json.loads('%s' % geojson.Feature(**feature)),
                    indent=indent,
                    sort_keys=True
                ).splitlines(True)
            )
            try:
                feature = next(features)
                out_gj += "%s%s,\n" % (space * level, feature_gj)
            except StopIteration:
                out_gj += "%s%s\n" % (space * level, feature_gj)
                break
    except StopIteration:
        pass
    out_gj += '%s]\n}' % space
    return out_gj
