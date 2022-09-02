from unittest import TestCase
from tapiriik.services.Decathlon.decathlon import DecathlonService
from requests import Response
from bson import ObjectId
import json

class StdLoginRefreshErrorManagementTest(TestCase):
    error_builder_function = DecathlonService.LoginRefreshError.build_from_login_response_and_std_external_user_id
    externalID = str(ObjectId())

    def test_login_refresh_error_builder_function_with_non_200_login_response_should_generate_login_refresh_error_instance(self):
        # Given
        response = Response()
        response.status_code = 502
        response.headers.update([("X-Correlation-Id", "6a208246-0373-4719-9468-3977c12b4dc1")])

        # When
        generated_login_error = self.error_builder_function(response, self.externalID)

        # Then
        self.assertIsInstance(generated_login_error, DecathlonService.LoginRefreshError)


    def test_login_refresh_error_builder_function_with_200_login_response_should_raise_Exception(self):
        # Given
        response = Response()
        response.status_code = 200
        expected_exception_message = "No error found : Login has responded 200"
        # response.headers.update([("X-Correlation-Id", "6a208246-0373-4719-9468-3977c12b4dc1")])

        # When
        with self.assertRaises(Exception) as exception_context:
            generated_login_error = self.error_builder_function(response, self.externalID)

        # Then
        exception_message = exception_context.exception.args[0]
        self.assertEqual(expected_exception_message, exception_message)


    def test_login_refresh_error_builder_function_with_non_200_login_response_without_correlation_id_header_should_return_login_refresh_error_with_its_login_response_correlation_id_attribute_set_to_NULL_string(self):
        # Given
        response = Response()
        response.status_code = 502

        # When
        generated_login_error = self.error_builder_function(response, self.externalID)

        # Then
        self.assertEquals(generated_login_error.LoginResponseCorrelationId, "NULL")


    def test_login_refresh_error_builder_function_with_json_body_in_login_response_should_return_login_refresh_error_with_its_login_error_description_in_login_response_error_description(self):
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
        generated_login_error = self.error_builder_function(response, self.externalID)

        # Then
        self.assertEqual(generated_login_error.LoginResponseErrorDescription, error_description)


    def test_login_refresh_error_builder_function_without_json_body_in_login_response_should_return_login_refresh_error_with_empty_string_in_login_response_error_description(self):
        response = Response()
        response.status_code = 400
        response._content = b""

        # When
        generated_login_error = self.error_builder_function(response, self.externalID)

        # Then
        self.assertEqual(generated_login_error.LoginResponseErrorDescription, "")


    
    def test_login_refresh_error_with_HTTP_code_5XX_should_be_non_blocking(self):
        # Given
        code = 502
        correlation_id = ""
        error_description = ""
        login_error = DecathlonService.LoginRefreshError(code, correlation_id, error_description, self.externalID)

        # When
        is_blocking = login_error.is_blocking()

        # Then
        self.assertFalse(is_blocking)


    def test_login_refresh_error_with_HTTP_code_400_and_invalid_refresh_token_error_description_should_be_blocking(self):
        # Given
        code = 400
        correlation_id = ""
        error_description = "Invalid refresh token: NOTAJWTTOKENSTRING"
        login_error = DecathlonService.LoginRefreshError(code, correlation_id, error_description, self.externalID)

        # When
        is_blocking = login_error.is_blocking()

        # Then
        self.assertTrue(is_blocking)


    def test_login_refresh_error_with_HTTP_code_400_and_not_invalid_refresh_token_error_description_should_be_blocking(self):
        # Given
        code = 400
        correlation_id = ""
        error_description = "User deleted"
        login_error = DecathlonService.LoginRefreshError(code, correlation_id, error_description, self.externalID)

        # When
        is_blocking = login_error.is_blocking()

        # Then
        self.assertTrue(is_blocking)

    
    def test_login_refresh_error_with_HTTP_code_401_should_be_blocking(self):
        # Given
        code = 401
        correlation_id = ""
        error_description = "User deleted"
        login_error = DecathlonService.LoginRefreshError(code, correlation_id, error_description, self.externalID)

        # When
        is_blocking = login_error.is_blocking()

        # Then
        self.assertTrue(is_blocking)


    def test_login_refresh_error_with_HTTP_code_400_and_a_not_null_correlation_id_should_generate_blocking_api_exception_with_intervention_required_and_a_message_begining_by_400_and_containing_the_same_correlation_id(self):
        # Given
        # Given
        code = 400
        correlation_id = "7e0456c3-7e44-4d8e-a31b-663d337c1d20"
        error_description = "User deleted"
        login_error = DecathlonService.LoginRefreshError(code, correlation_id, error_description, self.externalID)

        # When
        login_api_exception = login_error.generate_ApiException_instance()

        # Then
        self.assertTrue(login_api_exception.Block)
        self.assertTrue(login_api_exception.UserException.InterventionRequired)
        self.assertRegex(login_api_exception.Message, "400")
        self.assertRegex(login_api_exception.Message, correlation_id)



    def test_login_refresh_error_with_HTTP_code_502_and_null_correlation_id_should_generate_non_blocking_api_exception_with_false_intervention_required_and_a_message_begining_by_502_and_containing_NULL(self):
        # Given
        code = 502
        correlation_id = "NULL"
        error_description = ""
        login_error = DecathlonService.LoginRefreshError(code, correlation_id, error_description, self.externalID)

        # When
        login_api_exception = login_error.generate_ApiException_instance()

        # Then
        self.assertFalse(login_api_exception.Block)
        self.assertFalse(login_api_exception.UserException.InterventionRequired)
        self.assertRegex(login_api_exception.Message, "502")
        self.assertRegex(login_api_exception.Message, "NULL")