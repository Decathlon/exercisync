import datetime


class DeviceSupportMiddleware(object):

    def process_response(self, request, response):

        support = "web"
        if 'mobile' in request.GET:
            if request.GET['mobile'] is True or request.GET['mobile'] is 1 or request.GET['mobile'] is '1' or request.GET['mobile'] is 'true':
                support = 'mobile'
                if not request.COOKIES.get('device_support'):

                    max_age = 365 * 24 * 60 * 60  # 1 years
                    expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=max_age)
                    response.set_cookie('device_support', support, expires=expires.utctimetuple(), max_age=max_age)

        return response
