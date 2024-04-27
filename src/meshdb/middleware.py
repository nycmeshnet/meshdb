from django.http import HttpResponseServerError

class HandleServerErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        print("MiddleWare loaded her")

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code >= 500:
            print("hello world")
            pass
        elif response.status_code == 200:
            print("Well that loaded")
            pass
        return response

