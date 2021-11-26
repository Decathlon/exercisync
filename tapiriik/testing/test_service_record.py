from tapiriik.database import db
from tapiriik.services import ServiceRecord, service_record
from unittest.case import TestCase
from bson.objectid import ObjectId
from tapiriik.services import UserExceptionType


def create_test_service_record(with_error=False, with_user_exception=False ,blocking=False, requires_intervention=False, auth_user_exception_type=False):
    return ServiceRecord({
        '_id': ObjectId("".join(["1" for x in range(24)])),
        'SyncErrors': [
            {
                'Block': blocking,
                'UserException': {
                    "Type": UserExceptionType.Authorization if auth_user_exception_type else UserExceptionType.DownloadError, 
                    "InterventionRequired": requires_intervention
                }
            } if with_user_exception else {
                'Block': blocking
            }
        ] if with_error else []
    })


class TestHasAuthSyncError(TestCase):

    #
    # No sync errors or empty list
    #
    def test_undefined_sync_errors_return_false(self):
        service_record_dict = {'_id': ObjectId("".join(["1" for x in range(24)]))}
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_empty_sync_errors_return_false(self):
        service_record = create_test_service_record(with_error=False)
        self.assertFalse(service_record.HasAuthSyncError())


    #
    # Non blocking errors
    #
    def test_one_non_blocking_sync_errors_without_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_non_blocking_sync_errors_with_non_auth_and_no_intervention_required_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=False, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_non_blocking_sync_errors_with_auth_and_no_intervention_required_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=False, auth_user_exception_type=True)
        self.assertFalse(service_record.HasAuthSyncError())
    
    def test_one_non_blocking_sync_errors_with_non_auth_and_intervention_required_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=True, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_non_blocking_sync_errors_with_auth_and_intervention_required_user_exception_return_true(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=True, auth_user_exception_type=True)
        self.assertFalse(service_record.HasAuthSyncError())


    #
    # Blocking errors
    #
    def test_one_blocking_sync_errors_without_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_blocking_sync_errors_with_non_auth_and_no_intervention_required_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=False, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_blocking_sync_errors_with_auth_and_no_intervention_required_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=False, auth_user_exception_type=True)
        self.assertFalse(service_record.HasAuthSyncError())
    
    def test_one_blocking_sync_errors_with_non_auth_and_intervention_required_user_exception_return_false(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=True, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_blocking_sync_errors_with_auth_and_intervention_required_user_exception_return_true(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=True, auth_user_exception_type=True)
        self.assertTrue(service_record.HasAuthSyncError())