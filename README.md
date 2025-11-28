# Football Score Pro 2.0

A comprehensive football match management application built with PySide6 and a clean, modular architecture.

## Features

- **Team Management**: Import and manage team data with player information
- **Match Configuration**: Set up matches with customizable rules and settings
- **Officials Assignment**: Assign referees, assistants, and VAR officials
- **Event-Driven Architecture**: Clean separation of concerns with event-based communication
- **Modern UI**: Professional interface with responsive design
- **Data Persistence**: JSON-based data storage for teams, matches, and tournaments

## Architecture

The application follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│ UI Layer (PySide6)                                         │
├─────────────────────────────────────────────────────────────┤
│ Service Container (Dependency Injection)                   │
├─────────────────────────────────────────────────────────────┤
│ Service Layer (Business Logic)                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ TeamService │ │MatchService │ │TournamentSvc│           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Cross-Cutting Concerns                                     │
│ ┌─────────────┐ ┌─────────────┐                           │
│ │ValidationSvc│ │ EventBus    │                           │
│ └─────────────┘ └─────────────┘                           │
├─────────────────────────────────────────────────────────────┤
│ Domain Models                                              │
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                   │
│ │Team │ │Match│ │Player│ │Config│ │Result│                   │
│ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                   │
├─────────────────────────────────────────────────────────────┤
│ Data Persistence (JSON Files)                              │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
FSP/
├── src/                    # Source code
│   ├── models/            # Domain models
│   ├── services/          # Business logic services
│   └── events/            # Event system
├── ui/                    # User interface
│   ├── widgets/           # UI components
│   └── styles/            # UI styling
├── data/                  # Data storage
│   ├── teams/            # Team data
│   ├── tournaments/      # Tournament data
│   └── matches/          # Match data
├── tests/                # Test files
├── resources/            # Images and assets
├── main.py              # Application entry point
├── test_app.py          # Test script
└── requirements.txt     # Dependencies
```

## Installation

1. **Clone or download the project**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start (Windows)
- **UI Application**: Double-click `run_ui.bat` (or run `python main.py`)
- **Backend Demo**: Double-click `run_demo.bat` (or run `python main.py --demo`)
- **Run Tests**: Double-click `run_tests.bat`

### Command Line Usage

#### UI Application (default)
Launch the full UI (also works on macOS/Linux):
```bash
cd FSP
python main.py
```

#### Backend Demo
Run the backend demonstration to see the services in action:
```bash
cd FSP
python main.py --demo
```

#### Testing
Run the test suite to verify everything works:
```bash
cd FSP
python test_app.py
```

## Web Control Room & FastAPI Backend

A React frontend (`pitchcontrol-pro/`) and a FastAPI backend (`backend/`) are included for browser-based match operations.

1. **Backend**
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn backend.main:app --reload --port 8000
   ```
2. **Frontend**
   ```bash
   cd pitchcontrol-pro
   npm install
   echo VITE_API_BASE_URL=http://localhost:8000 > .env.local
   npm run dev
   ```
3. Open `http://localhost:5173` and create a match. The desktop Qt app can POST snapshots to `http://localhost:8000/matches/{id}/sync` to stay synchronized.

## Key Components

### Domain Models
- **Team**: Represents a football team with players and metadata
- **Player**: Individual player information and statistics
- **Match**: Match configuration, teams, officials, and status
- **Tournament**: Tournament rules and configuration
- **MatchConfiguration**: Match rules and settings

### Services
- **TeamService**: Manages team data import and validation
- **MatchService**: Handles match creation and management
- **TournamentService**: Manages tournament data and rules
- **ValidationService**: Validates business rules and data integrity
- **EventBus**: Handles inter-service communication

### UI Components
- **MatchSetupTab**: Main interface for setting up matches
- **TeamPanel**: Team selection and player management
- **OfficialsTab**: Officials assignment interface
- **BackendService**: Bridges UI and backend services

### Menu Structure
- **File Menu**:
  - New Match (Ctrl+N)
  - Load Match (Ctrl+O)
  - Load Team Data (Ctrl+T)
  - Exit (Ctrl+Q)
- **Help Menu**:
  - About

### Sample Data
- **`data/sample_teams.json`**: 5 Premier League teams with complete squads (100 players)
- **`data/sample_teams_small.json`**: 2 Premier League teams with starting XI (22 players)
- **Teams included**: Manchester United, Liverpool FC, Arsenal FC, Chelsea FC, Manchester City
- **Automatic Loading**: First team becomes Team A, second team becomes Team B
- **Radio Button Labels**: Show actual team names (e.g., "MUFC Data", "LFC Data")

## Design Patterns

- **Dependency Injection**: Services are injected through the service container
- **Event-Driven Architecture**: Loose coupling through event publishing/subscription
- **Repository Pattern**: Data access abstraction
- **Result Pattern**: Structured error handling and validation
- **Interface Segregation**: Clean service contracts

## Development

### Adding New Features
1. Create domain models in `src/models/`
2. Define service interfaces in `src/services/interfaces.py`
3. Implement services in `src/services/`
4. Create UI components in `ui/widgets/`
5. Add tests in `tests/`

### Event System
The application uses an event-driven architecture for loose coupling:
- Services publish events when data changes
- UI components subscribe to relevant events
- Events are typed and contain structured data

### Data Validation
All data goes through comprehensive validation:
- Business rule validation
- Data type and format validation
- Cross-service consistency checks
- Structured error reporting

## Contributing

1. Follow the established architecture patterns
2. Add comprehensive tests for new features
3. Use the event system for inter-component communication
4. Maintain clean separation between UI and business logic
5. Document new services and components

## License

This project is part of the Football Score Pro application suite.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
