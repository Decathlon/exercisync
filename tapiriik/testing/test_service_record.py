from tapiriik.database import db
from tapiriik.services import ServiceRecord
from unittest.case import TestCase
from bson.objectid import ObjectId
from tapiriik.services import UserExceptionType
from datetime import datetime


std_connection_record_dict_with_400_sync_error = {
    "_id": ObjectId(),
    "ExternalID": 'fake_id',
    "Service": 'decathlon',
    "SynchronizedActivities": [],
    "Authorization": {
        "AccessTokenDecathlonLogin": 'fake_one',
        "AccessTokenDecathlonLoginExpiresAt": 1655374258.9161086,
        "RefreshTokenDecathlonLogin": 'fake_one'
    },
    "ExtendedAuthorization": None,
    "ExcludedActivities": {},
    "SyncErrors": [
        {
            "Step": 'upload',
            "Message": 'Could not upload activity 400',
            "Block": False,
            "Scope": 'service',
            "TriggerExhaustive": False,
            "Timestamp": datetime(2022, 6, 16, 9, 56, 0, 702000)
        }
    ]
}

std_connection_record_dict_with_two_400_sync_error = {
    "_id": ObjectId(),
    "ExternalID": 'fake_id',
    "Service": 'decathlon',
    "SynchronizedActivities": [],
    "Authorization": {
        "AccessTokenDecathlonLogin": 'fake_one',
        "AccessTokenDecathlonLoginExpiresAt": 1655374258.9161086,
        "RefreshTokenDecathlonLogin": 'fake_one'
    },
    "ExtendedAuthorization": None,
    "ExcludedActivities": {},
    "SyncErrors": [
        {
            "Step": 'upload',
            "Message": 'Could not upload activity 400',
            "Block": False,
            "Scope": 'service',
            "TriggerExhaustive": False,
            "Timestamp": datetime(2022, 6, 16, 9, 56, 0, 702000)
        },
        {
            "Step": 'upload',
            "Message": 'Could not upload activity 400',
            "Block": False,
            "Scope": 'service',
            "TriggerExhaustive": False,
            "Timestamp": datetime(2022, 6, 16, 9, 56, 0, 702000)
        }
    ]
}


std_connection_record_dict_with_two_auth_sync_error = {
    "_id": ObjectId(),
    "ExternalID": 'fake_id',
    "Service": 'decathlon',
    "SynchronizedActivities": [],
    "Authorization": {
        "AccessTokenDecathlonLogin": 'fake_one',
        "AccessTokenDecathlonLoginExpiresAt": 1655374258.9161086,
        "RefreshTokenDecathlonLogin": 'fake_one'
    },
    "ExtendedAuthorization": None,
    "ExcludedActivities": {},
    "SyncErrors": [
        {
            "Step": 'upload',
            "Message": 'Could not upload activity 400',
            "Block": True,
            'UserException': {
                "Type": UserExceptionType.Authorization, 
                "InterventionRequired": True
            },
            "Scope": 'service',
            "TriggerExhaustive": False,
            "Timestamp": datetime(2022, 6, 16, 9, 56, 0, 702000)
        },
        {
            "Step": 'upload',
            "Message": 'Could not upload activity 400',
            "Block": True,
            'UserException': {
                "Type": UserExceptionType.Authorization, 
                "InterventionRequired": True
            },
            "Scope": 'service',
            "TriggerExhaustive": False,
            "Timestamp": datetime(2022, 6, 16, 9, 56, 0, 702000)
        },
    ]
}


std_connection_record_dict_with_one_auth_sync_error_and_one_400_sync_error = {
    "_id": ObjectId(),
    "ExternalID": 'fake_id',
    "Service": 'decathlon',
    "SynchronizedActivities": [],
    "Authorization": {
        "AccessTokenDecathlonLogin": 'fake_one',
        "AccessTokenDecathlonLoginExpiresAt": 1655374258.9161086,
        "RefreshTokenDecathlonLogin": 'fake_one'
    },
    "ExtendedAuthorization": None,
    "ExcludedActivities": {},
    "SyncErrors": [
        {
            "Step": 'upload',
            "Message": 'Could not upload activity 400',
            "Block": False,
            "Scope": 'service',
            "TriggerExhaustive": False,
            "Timestamp": datetime(2022, 6, 16, 9, 56, 0, 702000)
        },
        {
            "Step": 'upload',
            "Message": 'Could not upload activity 400',
            "Block": True,
            'UserException': {
                "Type": UserExceptionType.Authorization, 
                "InterventionRequired": True
            },
            "Scope": 'service',
            "TriggerExhaustive": False,
            "Timestamp": datetime(2022, 6, 16, 9, 56, 0, 702000)
        },
    ]
}



def create_test_service_record(with_error=False, with_user_exception=False, blocking=False, requires_intervention=False, auth_user_exception_type=False):
    return ServiceRecord({
        '_id': ObjectId(),
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
    # Production issue test case
    #
    def test_std_connection_with_400_sync_error_is_not_authorization_error(self):
        service_record = ServiceRecord(std_connection_record_dict_with_400_sync_error)
        self.assertFalse(service_record.HasAuthSyncError())
    

    #
    # No sync errors or empty list
    #
    def test_undefined_sync_errors_is_not_authorization_error(self):
        service_record_dict = {'_id': ObjectId()}
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_empty_sync_errors_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_sync_errors_has_one_sync_error_without_block_boolean_is_not_authorization_error(self):
        service_record_dict = {
            '_id': ObjectId(),
            'SyncErrors': [
                {
                    'UserException': {
                        "Type": UserExceptionType.Authorization, 
                        "InterventionRequired": True
                    }
                }
            ]
        }
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_sync_errors_has_one_sync_error_with_non_boolean_block_attribute_is_not_authorization_error(self):
        service_record_dict = {
            '_id': ObjectId(),
            'SyncErrors': [
                {
                    'UserException': {
                        "Type": UserExceptionType.Authorization, 
                        "InterventionRequired": True
                    },
                    'Block': "notaboolean"
                }
            ]
        }
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_sync_errors_has_one_sync_error_with_non_boolean_user_exception_intervention_required_attribute_is_not_authorization_error(self):
        service_record_dict = {
            '_id': ObjectId(),
            'SyncErrors': [
                {
                    'UserException': {
                        "Type": UserExceptionType.Authorization, 
                        "InterventionRequired": "notaboolean"
                    },
                    'Block': True
                }
            ]
        }
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_sync_errors_has_one_sync_error_with_non_string_user_exception_type_attribute_is_not_authorization_error(self):
        service_record_dict = {
            '_id': ObjectId(),
            'SyncErrors': [
                {
                    'UserException': {
                        "Type": 1337, 
                        "InterventionRequired": True
                    },
                    'Block': True
                }
            ]
        }
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_sync_errors_is_not_a_list_is_not_authorization_error(self):
        service_record_dict = {
            '_id': ObjectId(),
            'SyncErrors': 1
        }
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_sync_errors_list_not_composed_of_dict_is_not_authorization_error(self):
        service_record_dict = {
            '_id': ObjectId(),
            'SyncErrors': [1, 2, 3]
        }
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_sync_error_with_not_dict_user_exception_is_not_authorization_error(self):
        service_record_dict = {
            '_id': ObjectId(),
            'SyncErrors': [
                {
                    'UserException': 1
                }
            ]
        }
        service_record = ServiceRecord(service_record_dict)
        self.assertFalse(service_record.HasAuthSyncError())

    #
    # Non blocking errors
    #
    def test_one_non_blocking_sync_errors_without_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_non_blocking_sync_errors_with_non_auth_and_no_intervention_required_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=False, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_non_blocking_sync_errors_with_auth_and_no_intervention_required_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=False, auth_user_exception_type=True)
        self.assertFalse(service_record.HasAuthSyncError())
    
    def test_one_non_blocking_sync_errors_with_non_auth_and_intervention_required_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=True, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_non_blocking_sync_errors_with_auth_and_intervention_required_user_exception_return_true(self):
        service_record = create_test_service_record(with_error=True, blocking=False, with_user_exception=True, requires_intervention=True, auth_user_exception_type=True)
        self.assertFalse(service_record.HasAuthSyncError())


    #
    # Blocking errors
    #
    def test_one_blocking_sync_errors_without_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_blocking_sync_errors_with_non_auth_and_no_intervention_required_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=False, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_blocking_sync_errors_with_auth_and_no_intervention_required_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=False, auth_user_exception_type=True)
        self.assertFalse(service_record.HasAuthSyncError())
    
    def test_one_blocking_sync_errors_with_non_auth_and_intervention_required_user_exception_is_not_authorization_error(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=True, auth_user_exception_type=False)
        self.assertFalse(service_record.HasAuthSyncError())

    def test_one_blocking_sync_errors_with_auth_and_intervention_required_user_exception_return_true(self):
        service_record = create_test_service_record(with_error=True, blocking=True, with_user_exception=True, requires_intervention=True, auth_user_exception_type=True)
        self.assertTrue(service_record.HasAuthSyncError())


    #
    # Multiple sync errors test
    #
    def test_two_not_auth_sync_errors_is_not_authorization_error(self):
        service_record = ServiceRecord(std_connection_record_dict_with_two_400_sync_error)
        self.assertFalse(service_record.HasAuthSyncError())
    
    def test_one_not_auth_sync_errors_and_one_auth_sync_error_return_true(self):
        service_record = ServiceRecord(std_connection_record_dict_with_one_auth_sync_error_and_one_400_sync_error)
        self.assertTrue(service_record.HasAuthSyncError())
    
    def test_two_auth_sync_errors_return_true(self):
        service_record = ServiceRecord(std_connection_record_dict_with_two_auth_sync_error)
        self.assertTrue(service_record.HasAuthSyncError())
