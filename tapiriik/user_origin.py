import datetime


class UserOriginMiddleware(object):

    def process_response(self, request, response):
        COOKIE_NAME = "is_user_from_dkt_club"
        MAX_AGE_ONE_YEAR = 31536000
        UTM_SOURCE_QUERY_PARAM = 'utm_source'

        is_user_from_dkt_club = False
        if UTM_SOURCE_QUERY_PARAM in request.GET:
            if request.GET[UTM_SOURCE_QUERY_PARAM] == "decatclub":
                is_user_from_dkt_club = True
                if not request.COOKIES.get(COOKIE_NAME):
                    expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=MAX_AGE_ONE_YEAR)
                    response.set_cookie(COOKIE_NAME, is_user_from_dkt_club,
                                        expires=expires.utctimetuple(), max_age=MAX_AGE_ONE_YEAR)

        return response
