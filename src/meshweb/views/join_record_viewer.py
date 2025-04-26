import logging
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.template import loader

from meshapi.management.commands import replay_join_records
from meshapi.util.join_records import JoinRecordProcessor


@staff_member_required
def join_record_viewer(request: HttpRequest) -> HttpResponse:
    since_param = request.GET.get("since")
    if not since_param:
        since = replay_join_records.Command.past_week()
    else:
        try:
            since = datetime.fromisoformat(since_param + "Z")
        except ValueError:
            status = 400
            m = f"({status}) Bad ISO-formatted string for parameter 'since'"
            logging.exception(m)
            return HttpResponse(m, status=status)

    if since > datetime.now(timezone.utc):
        status = 400
        m = f"({status}) Cannot retrieve records from the future!"
        logging.error(m)
        return HttpResponse(m, status=status)

    all = request.GET.get("all") == "True"

    template = loader.get_template("meshweb/join_record_viewer.html")

    try:
        records = JoinRecordProcessor().ensure_pre_post_consistency(since)
    except ClientError:
        status = 503
        m = f"({status}) Could not retrieve join records. Check bucket credentials."
        logging.exception(m)
        return HttpResponse(m, status=status)

    relevant_records = (
        [r for _, r in records.items() if not replay_join_records.Command.filter_irrelevant_record(r)]
        if not all
        else records.values()
    )

    context = {"records": relevant_records, "all": all, "logo": "meshweb/logo.svg"}
    return HttpResponse(template.render(context, request))
