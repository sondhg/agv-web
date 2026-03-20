# AGV Fleet Management System (VDA5050)

A comprehensive AGV fleet management system implementing the VDA5050 standard for automated guided vehicle communication and control.

## 🏗️ Architecture

- **Backend**: Django REST Framework
- **Database**: PostgreSQL
- **Message Broker**: Eclipse Mosquitto (MQTT)
- **Pathfinding**: NetworkX
- **Containerization**: Docker & Docker Compose

## 📂 Project Structure

```
agv_project/
├── backend/                 # Django application
│   ├── server/              # Django project settings
│   └── vda5050/             # Main VDA5050 app
│       ├── models.py        # AGV, Order, State models
│       ├── views.py         # REST API endpoints
│       ├── signals.py       # MQTT auto-publish
│       ├── graph_engine.py  # Pathfinding logic
│       ├── modules/         # Core business logic
│       │   ├── scheduler.py         # Order creation
│       │   └── bidding/            # Auction system
│       │       ├── engine.py       # Bidding engine
│       │       ├── auction.py      # Auction coordinator
│       │       └── calculators/    # Cost calculations
│       └── management/
│           └── commands/
│               ├── run_mqtt_listener.py  # MQTT worker
│               ├── setup_test_agvs.py    # AGV setup
│               └── setup_test_graph.py   # Graph setup
├── tests/                   # Testing framework
│   ├── README.md            # Testing guide
│   ├── simulators/
│   │   ├── mock_agv.py              # Single AGV simulator
│   │   └── multi_mock_agv.py        # Multi-AGV fleet
│   └── load_balancing/
│       └── test_agv_load_balancing.py  # Load balance tests
├── docs/                    # Documentation
│   ├── MULTI_AGV_GUIDE.md   # Multi-AGV simulator guide
│   └── BIDDING_SYSTEM.md    # Bidding algorithm docs
├── mosquitto/               # MQTT broker config
└── docker-compose.yml       # Service orchestration
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for mock AGV)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/means19/agv-system.git
cd agv-system
```

2. Start all services:
```bash
docker-compose up -d
```

3. Run database migrations:
```bash
docker-compose exec web python manage.py migrate
```

4. Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

5. Access the system:
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- MQTT Broker: localhost:1884

### Testing with Mock AGV

```bash
# Install dependencies
pip install paho-mqtt

# Run mock AGV
python mock_agv.py
```

## 📡 VDA5050 Topics

- `uagv/v2/{manufacturer}/{serialNumber}/order` - Send orders to AGV
- `uagv/v2/{manufacturer}/{serialNumber}/state` - Receive AGV state
- `uagv/v2/{manufacturer}/{serialNumber}/connection` - Connection status

## 🔌 API Endpoints

- `GET/POST /api/agvs/` - AGV fleet management
- `GET/POST /api/orders/` - Order management
- `GET /api/agvs/{serial}/states/` - AGV state history
- `POST /api/orders/{id}/send/` - Dispatch order to AGV

## 🧪 Features

- ✅ VDA5050 standard compliance
- ✅ Real-time AGV state monitoring
- ✅ Automated pathfinding with NetworkX
- ✅ Order queue system with chaining
- ✅ MQTT integration for AGV communication
- ✅ REST API for external integrations
- ✅ Django Admin interface

## 📝 Development

### Technology Stack
- Django 4.2+
- Django REST Framework 3.14+
- PostgreSQL 15
- Paho MQTT 1.6+
- NetworkX (graph algorithms)
- Docker

## 📄 License

MIT License

## 👥 Contributors

- Project developed as part of University coursework (2025.1)
