# Campus Issue & Complaint Portal (CICP)

A centralized, AI-powered web platform for students to report campus issues and for administrators to track, analyze, and act on them.

## Features

- **AI-Powered Complaint Processing**: Automatically rewrites casual complaints into formal, professional submissions
- **Smart Categorization**: AI classifies complaints into predefined categories
- **Severity Detection**: Automatically detects urgency level (low/medium/high)
- **Intelligent Clustering**: Groups similar complaints using embeddings and similarity detection
- **Admin Dashboard**: Real-time analytics, charts, and insights
- **Anonymous Reporting**: Option to submit complaints anonymously
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (easily upgradeable to PostgreSQL)
- **AI/ML**: Google Gemini API
- **Frontend**: HTML, Tailwind CSS, Chart.js
- **ORM**: Flask-SQLAlchemy

## Project Structure

```
campus-complaint-system/
│
├── app.py                  # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
│
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── submit.html
│   ├── dashboard.html
│   └── cluster_detail.html
│
├── static/              # Static assets
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/
│
├── ai/                  # AI processing modules
│   ├── rewrite.py      # Complaint rewriting
│   ├── classify.py     # Category classification
│   ├── severity.py     # Severity detection
│   ├── embed.py        # Embedding generation
│   └── cluster.py      # Clustering logic
│
├── database/           # Database models
│   └── models.py
│
└── utils/             # Helper functions
    └── helpers.py
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Google Gemini API key

### Setup Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd campus-complaint-system
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your Gemini API key
```

5. **Initialize database**
```bash
python app.py
# Database will be created automatically on first run
```

6. **Run the application**
```bash
python app.py
```

7. **Access the portal**
Open your browser and navigate to: `http://localhost:5000`

## Configuration

### Environment Variables

Edit `.env` file with your settings:

```bash
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URI=sqlite:///complaints.db
GEMINI_API_KEY=your-api-key
```

### Getting Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file

## Usage

### For Students

1. Navigate to "Submit Complaint"
2. Select a category
3. Describe your issue
4. (Optional) Use AI to rewrite your complaint formally
5. Choose to submit anonymously or with your ID
6. Submit the complaint

### For Administrators

1. Navigate to "Dashboard"
2. View overall statistics and charts
3. See top issue clusters (grouped similar complaints)
4. Click on any cluster to view all related complaints
5. Take action based on severity and frequency

## API Endpoints

- `GET /` - Landing page
- `GET /submit` - Complaint submission form
- `POST /submit` - Submit a new complaint
- `GET /dashboard` - Admin dashboard
- `GET /cluster/<id>` - Cluster detail page
- `POST /api/rewrite` - AI rewrite endpoint
- `GET /api/stats` - Dashboard statistics API

## Database Schema

### Complaints Table
- id (Primary Key)
- student_id (Optional)
- raw_text (Original complaint)
- rewritten_text (AI-enhanced)
- category
- severity (low/medium/high)
- embedding (Vector for similarity)
- cluster_id (Foreign Key)
- timestamp

### Issue Clusters Table
- id (Primary Key)
- cluster_name
- category
- severity
- count (Number of complaints)
- last_updated

### Categories Table
- id (Primary Key)
- name

## AI Processing Pipeline

1. **Rewrite**: Transform casual text to formal complaint
2. **Classify**: Assign to appropriate category
3. **Severity**: Detect urgency level
4. **Embed**: Generate vector embedding
5. **Cluster**: Group with similar complaints

## Development

### Adding New Categories

Edit `config.py`:
```python
CATEGORY_KEYWORDS = {
    'New Category': ['keyword1', 'keyword2', ...],
    ...
}
```

### Customizing Severity Thresholds

Edit `config.py`:
```python
SIMILARITY_THRESHOLD = 0.75  # Adjust clustering sensitivity
```

## Deployment

### Production Considerations

1. **Use PostgreSQL** instead of SQLite
2. **Set DEBUG=False** in production
3. **Use a production WSGI server** (Gunicorn, uWSGI)
4. **Set up SSL/HTTPS**
5. **Configure firewall rules**
6. **Set up backup strategy**

### Example with Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Future Enhancements

- [ ] User authentication system
- [ ] Email notifications
- [ ] File upload support
- [ ] Mobile app
- [ ] Weekly PDF reports
- [ ] Department-specific portals
- [ ] Issue status tracking
- [ ] Upvoting system
- [ ] Multi-language support

## Troubleshooting

### Common Issues

**Database errors**: Delete `complaints.db` and restart the app

**API errors**: Check your Gemini API key in `.env`

**Module not found**: Run `pip install -r requirements.txt`

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ for better campus communication**