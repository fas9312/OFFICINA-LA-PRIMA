# LA PRIMA Garage Manager 0.1.1

Hotfix focused on two regressions found in 0.1:

1. The official OFFICINA LA PRIMA logo must be visible both in the sidebar and behind the dashboard.
2. Single-record PDF actions must remain available for client/vehicle/job/appointment/service/quote records.

The UI logo is embedded through Qt resources (`resources.qrc`) instead of relying only on a runtime filesystem path.
