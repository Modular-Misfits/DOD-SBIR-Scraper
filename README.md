# DOD SBIR/STTR Scraper

A web application for searching and downloading DOD SBIR/STTR topics.

## Features

- Search DOD SBIR/STTR topics
- Download individual PDFs directly to your browser
- Download multiple PDFs as a ZIP file
- Pagination support

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dodsbirsttr-scraper.git
cd dodsbirsttr-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
uvicorn src.main:app --reload
```

4. Open http://localhost:8000 in your browser

## Deployment

This application is configured to deploy automatically to Render when changes are pushed to the main branch.

### Manual Deployment to Render

1. Create a Render account at https://render.com
2. Create a new Web Service
3. Connect your GitHub repository
4. Use the following settings:
   - Environment: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

### Automatic Deployment

1. Get your Render API key from your Render dashboard
2. Add the API key to your GitHub repository secrets:
   - Go to your repository settings
   - Navigate to Secrets and Variables > Actions
   - Add a new secret named `RENDER_API_KEY` with your Render API key
3. Update the service ID in `.github/workflows/deploy.yml` with your Render service ID
4. Push to main branch to trigger deployment

## License

MIT