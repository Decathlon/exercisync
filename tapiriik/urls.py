from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView
import os

from tapiriik.web import views

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^auth/redirect/(?P<service>[^/]+)$', views.oauth.authredirect, {}, name='oauth_redirect', ),
    url(r'^auth/redirect/(?P<service>[^/]+)/(?P<level>.+)$', views.oauth.authredirect, {}, name='oauth_redirect', ),
    url(r'^auth/return/(?P<service>[^/]+)$', views.oauth.authreturn, {}, name='oauth_return', ),
    url(r'^auth/return/(?P<service>[^/]+)/(?P<level>.+)$', views.oauth.authreturn, {}, name='oauth_return', ),  # django's URL magic couldn't handle the equivalent regex
    url(r'^auth/login/(?P<service>.+)$', views.auth_login, {}, name='auth_simple', ),
    url(r'^auth/login-ajax/(?P<service>.+)$', views.auth_login_ajax, {}, name='auth_simple_ajax', ),
    url(r'^auth/persist-ajax/(?P<service>.+)$', views.auth_persist_extended_auth_ajax, {}, name='auth_persist_extended_auth_ajax', ),
    url(r'^auth/disconnect/(?P<service>.+)$', views.auth_disconnect, {}, name='auth_disconnect', ),
    url(r'^auth/disconnect-ajax/(?P<service>.+)$', views.auth_disconnect_ajax, {}, name='auth_disconnect_ajax', ),
    url(r'^auth/disconnect-do/(?P<service>.+)$', views.auth_disconnect_do, {}, name='auth_disconnect_do', ),
    url(r'^auth/auth_disconnect_garmin_health$', views.auth_disconnect_garmin_health, {}, name='auth_disconnect_garmin_health', ),
    url(r'^auth/logout$', views.auth_logout, {}, name='auth_logout', ),

    url(r'^account/setemail$', views.account_setemail, {}, name='account_set_email', ),
    url(r'^account/settz$', views.account_settimezone, {}, name='account_set_timezone', ),
    url(r'^account/configure$', views.account_setconfig, {}, name='account_set_config', ),

    url(r'^account/rollback/?$', views.account_rollback_initiate, {}, name='account_rollback_initiate', ),
    url(r'^account/rollback/(?P<task_id>.+)$', views.account_rollback_status, {}, name='account_rollback_status', ),

    url(r'^rollback$', views.rollback_dashboard, {}, name='rollback_dashboard', ),

    url(r'^configure/save/(?P<service>.+)?$', views.config.config_save, {}, name='config_save', ),
    url(r'^configure/dropbox$', views.config.dropbox, {}, name='dropbox_config', ),
    url(r'^configure/flow/save/(?P<service>.+)?$', views.config.config_flow_save, {}, name='config_flow_save', ),
    url(r'^settings/?$', views.settings, {}, name='settings_panel', ),

    # url(r'^dropbox/browse-ajax/?$', views.dropbox.browse, {}, name='dropbox_browse_ajax', ),

    url(r'^sync/status$', views.sync_status, {}, name='sync_status'),
    url(r'^sync/activity$', views.sync_recent_activity, {}, name='sync_recent_activity'),
    url(r'^sync/schedule/now$', views.sync_schedule_immediate, {}, name='sync_schedule_immediate'),
    url(r'^sync/errors/(?P<service>[^/]+)/clear/(?P<group>.+)$', views.sync_clear_errorgroup, {}, name='sync_clear_errorgroup'),

    url(r'^activities$', views.activities_dashboard, {}, name='activities_dashboard'),
    url(r'^activities/fetch$', views.activities_fetch_json, {}, name='activities_fetch_json'),

    url(r'^sync/remote_callback/trigger_partial_sync/(?P<service>.+)$', views.sync_trigger_partial_sync_callback, {}, name='sync_trigger_partial_sync_callback'),


    url(r'^status/$', views.server_status, {}, name='server_status'),
    url(r'^status_elb/$', views.server_status_elb, {}, name='server_status_elb'),

    url(".well-known/security.txt", views.server_securitytxt, {}, name='server_securitytxt'),

    url(r'^supported-activities$', views.supported_activities, {}, name='supported_activities'),
    # url(r'^supported-services-poll$', 'tapiriik.web.views.supported_services_poll', {}, name='supported_services_poll'),

    # url(r'^payments/claim$', 'tapiriik.web.views.payments_claim', {}, name='payments_claim'),
    # url(r'^payments/claim-ajax$', 'tapiriik.web.views.payments_claim_ajax', {}, name='payments_claim_ajax'),
    # url(r'^payments/promo-claim-ajax$', 'tapiriik.web.views.payments_promo_claim_ajax', {}, name='payments_promo_claim_ajax'),
    # url(r'^payments/claim-wait-ajax$', 'tapiriik.web.views.payments_claim_wait_ajax', {}, name='payments_claim_wait_ajax'),
    # url(r'^payments/claim/(?P<code>[a-f0-9]+)$', 'tapiriik.web.views.payments_claim_return', {}, name='payments_claim_return'),
    # url(r'^payments/return$', 'tapiriik.web.views.payments_return', {}, name='payments_return'),
    # url(r'^payments/confirmed$', 'tapiriik.web.views.payments_confirmed', {}, name='payments_confirmed'),
    # url(r'^payments/ipn$', 'tapiriik.web.views.payments_ipn', {}, name='payments_ipn'),
    # url(r'^payments/external/(?P<provider>[^/]+)/refresh$', 'tapiriik.web.views.payments_external_refresh', {}, name='payments_external_refresh'),

    url(r'^ab/begin/(?P<key>[^/]+)$', views.ab_web_experiment_begin, {}, name='ab_web_experiment_begin'),

    url(r'^privacy$', TemplateView.as_view(template_name='static/privacy.html'), name='privacy'),
    url(r'^faq$', TemplateView.as_view(template_name='static/faq.html'), name='faq'),
    url(r'^credits$', TemplateView.as_view(template_name='static/credits.html'), name='credits'),
    url(r'^contact$', TemplateView.as_view(template_name='static/contact.html'), name='contact'),
    # Examples:
    # url(r'^$', 'tapiriik.views.home', name='home'),
    # url(r'^tapiriik/', include('tapiriik.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),



    #########################
    # API Related
    #########################
    url(r'^api/providers$', views.providers, {}, name='providers'),

    #########################
    # Error management
    #########################
    url(r'^fail_to_disconnect_svc$', TemplateView.as_view(template_name='service_disconnect_failure.html'), name='fail_to_disconnect_svc')
]

if os.getenv("HUB_IS_IN_MAINTENANCE", "False").lower() in ("true", "1"):
    urlpatterns =  [url(r'^(?!(diagnostics)|(sync\/remote_callback\/trigger_partial_sync\/)).*$', views.maintenance, name='maintenance')] + urlpatterns



if 'DIAG_ENABLED' in os.environ and os.environ['DIAG_ENABLED'] == 'True':
    urlpatterns_diag = [
        url(r'^diagnostics/$', views.diag_dashboard, {}, name='diagnostics_dashboard'),
        url(r'^diagnostics/queue$', views.diag_queue_dashboard, {}, name='diagnostics_queue_dashboard'),
        url(r'^diagnostics/errors$', views.diag_errors, {}, name='diagnostics_errors'),
        url(r'^diagnostics/error/(?P<error>.+)$', views.diag_error, {}, name='diagnostics_error'),
        url(r'^diagnostics/graphs$', views.diag_graphs, {}, name='diagnostics_graphs'),
        url(r'^diagnostics/user/unsu$', views.diag_unsu, {}, name='diagnostics_unsu'),
        url(r'^diagnostics/userlookup/$', views.diag_user_lookup, {}, name='diagnostics_user_lookup'),
        url(r'^diagnostics/connection/$', views.diag_connection, {}, name='diagnostics_connection'),
        url(r'^diagnostics/api/connections/search$', views.diag_api_search_connection, {}, name='diagnostics_search_connections'),
        url(r'^diagnostics/api/connections/(?P<connection_id>[\da-zA-Z]*)$', views.diag_api_connection_by_id, {}, name='diagnostics_get_connection_by_id'),
        url(r'^diagnostics/api/user_activities$', views.diag_api_user_activities, {}, name='diagnostics_dashboard'),
        url(r'^diagnostics/user/(?P<user>[\da-zA-Z]+)/activities$', views.diag_user_activities, {}, name='diagnostics_user_activities'),
        url(r'^diagnostics/user/(?P<user>.+)$', views.diag_user, {}, name='diagnostics_user'),
        url(r'^diagnostics/payments/$', views.diag_payments, {}, name='diagnostics_payments'),
        url(r'^diagnostics/ip$', views.diag_ip, {}, name='diagnostics_ip'),
        url(r'^diagnostics/stats$', views.diag_stats, {}, name='diagnostics_stats'),
        url(r'^diagnostics/login$', views.diag_login, {}, name='diagnostics_login'),
    ]

    urlpatterns += urlpatterns_diag



urlpatterns += staticfiles_urlpatterns()
