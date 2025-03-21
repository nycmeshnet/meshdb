from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAdminUser])
def crawl_uisp_for_nn(request, network_number, format=None):
    print("hello!")
    content = {
        'status': 'request was permitted'
    }
    return Response(content)

"""
if not network_number:
    status = 400
    m = f"({status}) Please provide a network number."
    logging.error(m)
    return HttpResponse(m, status=status)

try:
    if int(network_number) > NETWORK_NUMBER_MAX:
        status = 400
        m = f"({status}) Network number is beyond the max."
        logging.error(m)
        return HttpResponse(m, status=status)
except ValueError:
    status = 400
    m = f"({status}) invalid Network Number."
    return HttpResponse(m, status=status)

import_and_sync_uisp_devices(get_uisp_devices(), network_number)
import_and_sync_uisp_links(get_uisp_links(), network_number)
sync_link_table_into_los_objects()
"""
