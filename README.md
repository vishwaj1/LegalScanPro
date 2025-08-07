# LegalScanPro

A comprehensive legal document scanning and analysis platform.

## Project Structure

```
LegalScanPro/
├── frontend/              # Next.js frontend application
├── services/              # Backend microservices
│   └── upload/           # File upload service
├── docker-compose.yml    # Docker orchestration
└── .gitignore           # Git ignore rules
```

## Features

- Document upload and processing
- Legal document analysis
- Modern web interface
- Microservices architecture
- Docker containerization

## Getting Started

### Prerequisites
- Node.js (v18 or higher)
- Python 3.8+
- Docker and Docker Compose

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd LegalScanPro
```

2. Install dependencies:
```bash
# Frontend
cd frontend && npm install

# Backend services
cd ../services/upload && pip install -r requirements.txt
```

3. Run with Docker Compose:
```bash
docker-compose up --build
```

## Development

### Frontend
```bash
cd frontend
npm run dev
```

### Backend Services
```bash
cd services/upload
python main.py
```

## Docker

Build and run all services:
```bash
docker-compose up --build
```

## License

MIT License 