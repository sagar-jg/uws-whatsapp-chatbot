# UWS WhatsApp AI Chatbot

An intelligent WhatsApp-based chatbot for the University of the West of Scotland (UWS) that provides comprehensive student support with advanced AI capabilities.

## 🚀 Features

- **Academic Focus**: Strictly limited to UWS academic topics, courses, and university information
- **Vector Search**: Contextually relevant answers using Pinecone vector database
- **Conversation Memory**: Multi-turn context retention with PostgreSQL
- **MCP Integrations**: HubSpot MCP for personalized responses and meeting scheduling
- **Real-time Updates**: Web search fallback for outdated information
- **Robust Architecture**: LangGraph/CrewAI orchestration with comprehensive guardrails

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WhatsApp      │────│  FastAPI Server  │────│   LangGraph     │
│   Business API  │    │   (Webhook)      │    │  Orchestrator   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              │                         │
                    ┌─────────┴─────────┐              │
                    │                   │              │
            ┌───────▼────────┐ ┌────────▼──────┐      │
            │  Guardrails    │ │ Conversation  │      │
            │   Engine       │ │   Manager     │      │
            └────────────────┘ └───────────────┘      │
                                       │              │
                                       │              │
              ┌────────────────────────┴──────────────▼──────────────┐
              │                  Context Engine                      │
              └────────┬────────────────────────────────────┬────────┘
                       │                                    │
         ┌─────────────▼─────────────┐           ┌─────────▼─────────┐
         │     Vector Search         │           │   MCP Manager     │
         │    (Pinecone DB)          │           │  (HubSpot MCP)    │
         └─────────────┬─────────────┘           └───────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │     Web Search           │
         │   (Fallback Engine)      │
         └───────────────────────────┘
```

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL database
- Pinecone account and API key
- HubSpot account and API credentials
- WhatsApp Business API access
- OpenAI API key

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/sagar-jg/uws-whatsapp-chatbot.git
cd uws-whatsapp-chatbot
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python scripts/init_db.py
```

6. Start the application:
```bash
python main.py
```

## 🔧 Configuration

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/uws_chatbot

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=uws-knowledge-base

# WhatsApp Business API
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_verify_token

# HubSpot MCP
HUBSPOT_API_KEY=your_hubspot_api_key
HUBSPOT_PORTAL_ID=your_portal_id

# Web Search
SERPER_API_KEY=your_serper_api_key

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

## 📚 Documentation

- [Architecture Guide](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [MCP Integration Guide](docs/mcp-integration.md)
- [Guardrails Documentation](docs/guardrails.md)

## 🚀 Deployment

### Docker Deployment

```bash
docker-compose up -d
```

### Manual Deployment

1. Set up production environment
2. Configure reverse proxy (nginx)
3. Set up SSL certificates
4. Configure monitoring and logging

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v --cov=src
```

## 📈 Monitoring

The application includes comprehensive monitoring:

- Application metrics via Prometheus
- Request logging and error tracking
- Conversation analytics
- Performance monitoring

## 🔒 Security

- Input validation and sanitization
- Rate limiting
- Conversation history encryption
- Secure API key management
- GDPR compliance features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Support

For technical support or questions:
- Create an issue in this repository
- Contact: [your-email@uws.ac.uk]

## 🔄 Version History

- v1.0.0 - Initial release with core features
- v1.1.0 - Added MCP integrations
- v1.2.0 - Enhanced guardrails and monitoring