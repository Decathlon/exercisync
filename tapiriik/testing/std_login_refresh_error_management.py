from unittest import TestCase
from tapiriik.services.Decathlon.decathlon import DecathlonService
from requests import Response
from bson import ObjectId
import json

class StdLoginRefreshErrorManagementTest(TestCase):
    externalID = str(ObjectId())

    def test_200_response_should_return_authentication_refresh_response_without_errors(self):
        # Given
        response = Response()
        response.status_code = 200

        # When
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # Then
        self.assertEquals(auth_refresh_response.ResponseErrorDescription, "")
        self.assertFalse(auth_refresh_response.IsInError)


    def test_response_without_correlation_id_header_should_return_authentication_refresh_response_with_its_correlation_id_attribute_set_to_NULL_string(self):
        # Given
        response = Response()
        response.status_code = 502

        # When
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # Then
        self.assertEquals(auth_refresh_response.ResponseCorrelationId, "NULL")


    def test_200_response_with_json_body_should_return_authentication_refresh_response_with_its_response_body_dict_equals_to_json_body(self):
        # Given
        response_body_dict = {
            "access_token": "not_a_real_token",
            "refresh_token": "not_a_real_refresh_token",
            "expires_in": 600
        }

        response = Response()
        response.status_code = 200
        response._content = json.dumps(response_body_dict).encode("UTF-8")

        # When
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # Then
        self.assertEqual(auth_refresh_response.ResponseBodyDict, response_body_dict)


    def test_non_200_response_with_json_body_and_a_error_description_key_set_should_return_authentication_refresh_response_with_its_response_error_description_equals_to_the_one_provided(self):
        # Given
        error_description = "Invalid refresh token: NOTAJWTTOKENSTRING"
        response_message_dict = {
            "error" : "invalid_grant",
            "error_description" : error_description
        }
        response_message_json_string = json.dumps(response_message_dict)
        response = Response()
        response.status_code = 400
        response._content = response_message_json_string.encode("UTF-8")

        # When
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # Then
        self.assertEqual(auth_refresh_response.ResponseErrorDescription, error_description)


    def test_non_200_response_without_json_body_should_return_authentication_refresh_response_with_empty_string_response_error_description(self):
        response = Response()
        response.status_code = 400
        response._content = b""

        # When
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # Then
        self.assertEqual(auth_refresh_response.ResponseErrorDescription, "")



    def test_authentication_refresh_response_with_HTTP_code_5XX_should_be_non_blocking(self):
        # Given
        response = Response()
        response.status_code = 502
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # When
        is_blocking = auth_refresh_response.is_blocking()

        # Then
        self.assertFalse(is_blocking)


    def test_authentication_refresh_response_with_HTTP_code_4XX_should_be_blocking(self):
        # Given
        response = Response()
        response.status_code = 400
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # When
        is_blocking = auth_refresh_response.is_blocking()

        # Then
        self.assertTrue(is_blocking)


    def test_authentication_refresh_response_with_HTTP_code_3XX_should_be_non_blocking(self):
        # Given
        response = Response()
        response.status_code = 301
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # When
        is_blocking = auth_refresh_response.is_blocking()

        # Then
        self.assertFalse(is_blocking)


    def test_authentication_refresh_response_with_HTTP_code_400_and_a_not_null_correlation_id_should_generate_blocking_api_exception_with_intervention_required_and_a_message_begining_by_400_and_containing_the_same_correlation_id(self):
        # Given
        response_body_dict = {
            "error" : "invalid_grant",
            "error_description" : "User deleted"
        }
        correlation_id = "6a208246-0373-4719-9468-3977c12b4dc1"

        response = Response()
        response.status_code = 400
        response.headers.update([("X-Correlation-Id", correlation_id)])
        response._content = json.dumps(response_body_dict).encode("UTF-8")

        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # When
        login_api_exception = auth_refresh_response.generate_ApiException_instance()

        # Then
        self.assertTrue(login_api_exception.Block)
        self.assertTrue(login_api_exception.UserException.InterventionRequired)
        self.assertRegex(login_api_exception.Message, "400")
        self.assertRegex(login_api_exception.Message, correlation_id)



    def test_authentication_refresh_response_with_HTTP_code_502_and_null_correlation_id_should_generate_non_blocking_api_exception_with_false_intervention_required_and_a_message_begining_by_502_and_containing_NULL(self):
        # Given
        response = Response()
        response.status_code = 502
        auth_refresh_response = DecathlonService.AuthenticationRefreshResponse(response, self.externalID)

        # When
        login_api_exception = auth_refresh_response.generate_ApiException_instance()

        # Then
        self.assertFalse(login_api_exception.Block)
        self.assertFalse(login_api_exception.UserException.InterventionRequired)
        self.assertRegex(login_api_exception.Message, "502")
        self.assertRegex(login_api_exception.Message, "NULL")
