### Broker

a simple broker app

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app broker_app
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/broker_app
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
http://127.0.0.1:8006/api/method/broker_app.mobile_api.broker.create_broker
http://127.0.0.1:8006/api/method/broker_app.mobile_api.auth.login

{"broker_name": "Abhishek Singh" , "item_name": "Test", "item_rate": "10", "taxes":"5", "vehicle_number": "OB202022"}